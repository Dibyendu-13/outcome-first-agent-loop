"""Policy-aware controller. All knowledge of the world comes from HTTP."""
import copy
import hashlib
import json
import time
from datetime import datetime, timedelta

import httpx

from .statistics import interval, rate, winner


def shifted(ts, hours):
    return (datetime.fromisoformat(ts)+timedelta(hours=hours)).isoformat()


def metric(name):
    return 'pickup' if name.startswith('pickup') else 'engagement'


class Engine:
    def __init__(self, url, store, client=None):
        self.url, self.s = url.rstrip('/'), store
        self.c = client or httpx.Client(base_url=self.url,timeout=180,trust_env=False)

    def request(self, method, path, body=None):
        # Mutations are deliberately not retried here: reconcile first on the next loop.
        response = self.c.request(method,path,json=body)
        if response.status_code>=500:
            response.raise_for_status()
        return response

    def get(self, path, **params):
        r = self.c.get(path,params=params)
        r.raise_for_status()
        return r.json()

    def ingest(self):
        chunks = []
        for kind in ('history','events'):
            chunks.extend(self.get('/events/chunks',kind=kind,after=self.s.get('chunk:'+kind,-1)))
        for ch in sorted(chunks,key=lambda c:c['chunk']):
            with self.c.stream('GET',f"/events/chunks/{ch['chunk']}") as r:
                r.raise_for_status()
                self.s.ingest(ch,r.iter_lines())

    def record_applied(self, pid, body, reason, ts):
        self.s.db.execute('UPDATE proposals SET status="applied" WHERE id=?',(pid,))
        plan = json.loads(reason)
        dim = plan.get('dimension')
        if dim:
            self.s.db.execute('INSERT OR REPLACE INTO experiments VALUES (?,?,?,?,?)',
                (body['workflow_id'],dim,shifted(ts,1)[:13],plan['stage'],json.dumps(plan['baseline'])))
        self.s.audit(ts,body['workflow_id'],'applied',{'proposal_id':pid,'plan':plan})
        if plan.get('previous_config'):
            self.s.set('monitor:'+body['workflow_id'],{'proposal_id':pid,'version':body['base_version']+1,
                'applied':ts,'previous':plan['previous_config'],'baseline_version':body['base_version']})

    def reconcile(self, workflows, ts):
        remote = {a['proposal_id']:a for a in self.get('/approvals')}
        histories = {w['workflow_id']:self.get(f"/workflows/{w['workflow_id']}/config/history") for w in workflows}
        rows = self.s.db.execute('SELECT id,workflow,status,approval,body,reason FROM proposals WHERE status IN ("prepared","pending","approved","unknown")').fetchall()
        for pid,wid,status,aid,body_text,reason in rows:
            body = json.loads(body_text)
            applied = next((h for h in histories[wid] if h.get('proposal_id')==pid),None)
            if applied:
                with self.s.db:
                    self.record_applied(pid,body,reason,applied.get('applied_at') or ts)
                continue
            approval = remote.get(pid)
            if approval:
                aid,status = approval['approval_id'],approval['status']
                with self.s.db:
                    self.s.db.execute('UPDATE proposals SET status=?,approval=? WHERE id=?',(status,aid,pid))
            cur = self.get(f'/workflows/{wid}/config')
            if status in ('prepared','unknown') and not approval:
                if cur['version']!=body['base_version']:
                    with self.s.db:
                        self.s.db.execute('UPDATE proposals SET status="stale" WHERE id=?',(pid,))
                    continue
                auto = json.loads(reason).get('auto',False)
                r = self.request('PUT' if auto else 'POST',f'/workflows/{wid}/config' if auto else '/approvals',body)
                with self.s.db:
                    if r.is_success:
                        if auto:
                            self.record_applied(pid,body,reason,ts)
                        else:
                            self.s.db.execute('UPDATE proposals SET status="pending",approval=? WHERE id=?',(r.json()['approval_id'],pid))
                    else:
                        self.s.db.execute('UPDATE proposals SET status="failed" WHERE id=?',(pid,))
                        self.s.audit(ts,wid,'proposal_failed',{'proposal_id':pid,'response':r.json()})
                continue
            if status=='approved':
                if cur['version']!=body['base_version']:
                    with self.s.db:
                        self.s.db.execute('UPDATE proposals SET status="stale" WHERE id=?',(pid,))
                        self.s.audit(ts,wid,'stale_proposal',{'proposal_id':pid,'current_version':cur['version']})
                    continue
                r = self.request('POST',f'/workflows/{wid}/apply',{'approval_id':aid})
                with self.s.db:
                    if r.is_success:
                        self.record_applied(pid,body,reason,ts)
                    else:
                        self.s.db.execute('UPDATE proposals SET status=? WHERE id=?',('stale' if r.status_code==409 else 'lapsed' if r.status_code==410 else 'failed',pid))
                        self.s.audit(ts,wid,'apply_failed',{'proposal_id':pid,'response':r.json()})

    def propose(self, w, cur, cfg, ts, summary, evidence, plan):
        wid = w['workflow_id']
        if cfg==cur['config']:
            return False
        dims = [d for d in ('voice','welcome_message','caller_id') if cfg['allocations']['default'].get(d)!=cur['config']['allocations']['default'].get(d)]
        if cfg['prompt_version']!=cur['config']['prompt_version']:
            dims.append('prompt_version')
        pol = w['governance']
        # Only operational caller-ID changes auto-apply. Human review for customer-facing experiments.
        auto_pol = pol['auto_apply']
        shift = max([sum(abs(cfg['allocations']['default'].get(d,{}).get(k,0)-cur['config']['allocations']['default'].get(d,{}).get(k,0)) for k in set(cfg['allocations']['default'].get(d,{}))|set(cur['config']['allocations']['default'].get(d,{})))/2 for d in dims if d!='prompt_version'] or [0])
        auto = dims==['caller_id'] and auto_pol['enabled'] and 'caller_id' in auto_pol['allowed_dims'] and shift<=auto_pol['max_shift']+1e-9
        if not auto:
            hour = int(ts[11:13])
            start,end = pol['approver_hours']
            if w['tenant_id']=='kestrel_finance':
                start = max(start,11)
            if not start<=hour<end-1:
                return False
        limit = min(2,pol['max_requests_per_24h'])
        requests = self.s.db.execute('SELECT count(*) FROM proposals WHERE workflow=? AND created>?',(wid,shifted(ts,-24))).fetchone()[0]
        if requests>=limit:
            return False
        affected = self.s.db.execute('SELECT count(*) FROM leads WHERE workflow=? AND concluded=0',(wid,)).fetchone()[0]
        # Upper bound of remaining enrolled leads: unreachable old enrollments may be included.
        expected = evidence.get('estimated_lift',0)
        body = {'workflow_id':wid,'base_version':cur['version'],'proposed_config':cfg,
            'change_summary':summary,'diff':{d:cfg['prompt_version'] if d=='prompt_version' else cfg['allocations']['default'][d] for d in dims},
            'affected_leads':affected,'dry_run':{'method':'observed aggregate replay; no causal guarantee','evidence':evidence,'affected_leads_method':'upper bound: unconcluded enrollments; includes expired cadence'},
            'impact_score':round(min(1,max(0,expected)),4),'rationale':summary+'; '+json.dumps(evidence,sort_keys=True),
            'evidence':evidence.get('validation',{})}
        # Content-derived identity survives crash between local intent and remote acknowledgement.
        identity = json.dumps([body,ts[:13]],sort_keys=True)
        pid = hashlib.sha256(identity.encode()).hexdigest()[:32]
        body['proposal_id'] = pid
        plan['auto'] = auto
        plan['previous_config'] = cur['config']
        with self.s.db:
            self.s.db.execute('INSERT OR IGNORE INTO proposals VALUES (?,?,"prepared",NULL,?,?,?)',
                (pid,wid,json.dumps(body),json.dumps(plan),ts))
            self.s.audit(ts,wid,'proposal_prepared',{'proposal_id':pid,'summary':summary,'evidence':evidence,'auto':auto})
        return True

    def paid(self, key, endpoint, body, ts, wid):
        row = self.s.db.execute('SELECT status,result FROM charges WHERE key=?',(key,)).fetchone()
        if row:
            return json.loads(row[1]) if row[0]=='complete' else None
        # The API has no idempotency/retrieval for paid operations. Never blindly repeat an unknown charge.
        with self.s.db:
            self.s.db.execute('INSERT INTO charges VALUES (?,"unknown",NULL)',(key,))
        r = self.request('POST',endpoint,body)
        with self.s.db:
            self.s.db.execute('UPDATE charges SET status=?,result=? WHERE key=?',('complete' if r.is_success else 'failed',json.dumps(r.json()),key))
            self.s.audit(ts,wid,'credit_operation',{'key':key,'status':r.status_code,'result':r.json()})
        return r.json() if r.is_success else None

    def incident(self,w,cur,state):
        wid,ts = w['workflow_id'],state['ts']
        prompt = cur['config']['prompt_version']
        incident = self.s.get('incident:'+wid)
        if incident and incident['prompt']!=prompt:
            with self.s.db:
                self.s.audit(ts,wid,'incident_prompt_replaced',{'incident':incident,'new_prompt':prompt})
                self.s.set('incident:'+wid,None)
            incident = None
        if not incident:
            recent = self.s.stats(wid,since=shifted(ts,-4),until=ts,prompt=prompt).get('all')
            if not recent or recent['connected']<200:
                return False
            baseline = self.s.stats(wid,until=cur.get('applied_at') or shifted(ts,-4)).get('all')
            base = baseline['hallucinations']/baseline['connected'] if baseline and baseline['connected']>=400 else .01
            p = recent['hallucinations']/recent['connected']
            null = max(.025,base+.015)
            score = (p-null)/(null*(1-null)/recent['connected'])**.5
            if score<4 or p<.04:
                return False
            incident = {'prompt':prompt,'detected':ts,'recent':recent,'baseline':baseline,'threshold':null,'z_score':score}
            with self.s.db:
                self.s.set('incident:'+wid,incident)
                self.s.audit(ts,wid,'hallucination_incident',incident)
        key = f'incident:{wid}:{incident["detected"]}'
        if not incident.get('candidate'):
            if state['credits_remaining']<20:
                with self.s.db:
                    self.s.audit(ts,wid,'alert_credit_reserve',{'credits_remaining':state['credits_remaining']})
                return True
            suggestions = self.paid(key,'/llm/suggest-fixes',{'workflow_id':wid,'problem':'Sustained hallucination increase: '+json.dumps(incident)},ts,wid)
            if not suggestions:
                return True
            options = suggestions.get('suggestions',suggestions.get('candidates',suggestions.get('alternatives',[]))) if isinstance(suggestions,dict) else suggestions
            safe = []
            for item in options[:3]:
                candidate = item['prompt_version'] if isinstance(item,dict) else item
                if candidate==prompt:
                    continue
                validation = self.paid(key+':'+candidate,'/validation/runs',{'workflow_id':wid,'prompt_version':candidate,'n':400},ts,wid)
                if validation and validation['pass_rate']>=w['governance']['min_validation_pass_rate']:
                    # Validation measures safety only. Prefer demonstrated engagement over unobserved promises.
                    observed = self.s.stats(wid,until=incident['detected'],prompt=candidate).get('all')
                    engagement_lower = interval(observed,'engagement')[0] if observed and observed['connected']>=400 else 0
                    safe.append((engagement_lower,validation['pass_rate'],candidate,validation))
            if not safe:
                with self.s.db:
                    self.s.audit(ts,wid,'alert_no_validated_fix',{'incident':incident})
                return True
            _,_,candidate,val = max(safe,key=lambda x:(x[0],x[1],x[2]))
            incident.update(candidate=candidate,validation=val)
            with self.s.db:
                self.s.set('incident:'+wid,incident)
        cfg = copy.deepcopy(cur['config'])
        cfg['prompt_version'] = incident['candidate']
        evidence = {'recent':incident['recent'],'baseline':incident['baseline'],
            'validation':{'validation_run_id':incident['validation']['validation_run_id']},'estimated_lift':0,
            'safety_only':True,'candidate_selection':'prefer observed engagement lower bound among safety-passing candidates'}
        self.propose(w,cur,cfg,ts,'Validate and replace prompt after sustained hallucination increase',evidence,{})
        # An open incident stays open outside approver hours and blocks unrelated experiments.
        return True

    def verify(self,w,cur,state):
        wid,ts = w['workflow_id'],state['ts']
        monitor = self.s.get('monitor:'+wid)
        if not monitor or cur['version']!=monitor['version'] or cur['actor']=='supervisor':
            return False
        after = self.s.stats(wid,since=shifted(monitor['applied'],1),until=ts,version=cur['version']).get('all')
        before = self.s.stats(wid,since=shifted(monitor['applied'],-48),until=monitor['applied'],version=monitor['baseline_version']).get('all')
        if not before or not after or min(before['connected'],after['connected'])<400:
            return False
        key = 'verify:'+monitor['proposal_id']+':'+ts[:10]
        if self.s.get(key):
            return False
        primary = metric(w['objective']['primary'])
        other = 'pickup' if primary=='engagement' else 'engagement'
        drop = w['objective']['guardrail'].get(other+'_rate_max_drop',.02)
        harmful = interval(after,primary)[1]<interval(before,primary)[0]-.03 or interval(after,other)[1]<interval(before,other)[0]-drop
        with self.s.db:
            self.s.set(key,True)
            self.s.audit(ts,wid,'post_apply_verification',{'proposal_id':monitor['proposal_id'],'before':before,'after':after,'harmful':harmful,'method':'temporal comparison; confounding possible'})
        if not harmful:
            return False
        cfg = copy.deepcopy(monitor['previous'])
        evidence = {'before':before,'after':after,'estimated_lift':0,'rollback_of':monitor['proposal_id']}
        if cfg['prompt_version']!=cur['config']['prompt_version']:
            if state['credits_remaining']<24:
                return False
            val = self.paid('rollback:'+monitor['proposal_id'],'/validation/runs',{'workflow_id':wid,'prompt_version':cfg['prompt_version'],'n':400},ts,wid)
            if not val or val['pass_rate']<w['governance']['min_validation_pass_rate']:
                with self.s.db:
                    self.s.audit(ts,wid,'alert_unsafe_rollback',{'proposal_id':monitor['proposal_id'],'validation':val})
                return False
            evidence['validation'] = {'validation_run_id':val['validation_run_id']}
        return self.propose(w,cur,cfg,ts,'Rollback after sustained primary or guardrail degradation',evidence,{})

    def caller_health(self,w,cur,state):
        wid,ts = w['workflow_id'],state['ts']
        recent = self.s.stats(wid,'caller_id',since=shifted(ts,-4),until=ts)
        past = self.s.stats(wid,'caller_id',since=shifted(ts,-72),until=shifted(ts,-4))
        bad = []
        for option,now in recent.items():
            before = past.get(option)
            if not before or now['dials']<300 or before['dials']<600:
                continue
            if interval(now,'pickup')[1] < interval(before,'pickup')[0]-.05:
                bad.append(option)
        if not bad:
            return False
        healthy = [o for o,v in recent.items() if o not in bad and v['dials']>=300]
        if not healthy:
            return False
        # A healthy contemporaneous alternative is necessary; never blame a DID for a platform-wide drop.
        if max(interval(recent[o],'pickup')[0] for o in healthy)<=max(interval(recent[o],'pickup')[1] for o in bad):
            return False
        cfg = copy.deepcopy(cur['config'])
        old = cfg['allocations']['default']['caller_id']
        new = dict(old)
        removed = 0
        for o in bad:
            removed += new.pop(o,0)
        if not removed:
            return False
        for o in healthy:
            new[o] = new.get(o,0)+removed/len(healthy)
        cfg['allocations']['default']['caller_id'] = new
        return self.propose(w,cur,cfg,ts,'Rotate degraded caller IDs: '+', '.join(bad),
            {'recent':recent,'historical':past,'bad':bad,'estimated_lift':0,'detector':'3.5 sigma intervals; 5pp minimum degradation'}, {})

    def decide(self,w,cur,state):
        wid,ts = w['workflow_id'],state['ts']
        old = self.s.get('config:'+wid)
        if old and old['version']!=cur['version'] and cur['actor']=='supervisor':
            with self.s.db:
                self.s.db.execute('DELETE FROM experiments WHERE workflow=?',(wid,))
                self.s.set('supervisor_pause:'+wid,shifted(ts,24))
                protected = self.s.get('protected:'+wid,[])
                for d in ('voice','welcome_message','caller_id'):
                    if old['config']['allocations']!=cur['config']['allocations'] and old['config']['allocations']['default'].get(d)!=cur['config']['allocations']['default'].get(d):
                        protected.append(d)
                self.s.set('protected:'+wid,sorted(set(protected)))
                self.s.audit(ts,wid,'supervisor_reassessment',{'before':old,'after':cur,'pause_until':shifted(ts,24)})
        with self.s.db:
            self.s.set('config:'+wid,cur)
        if self.s.db.execute('SELECT 1 FROM proposals WHERE workflow=? AND status IN ("prepared","pending","approved","unknown")',(wid,)).fetchone():
            return
        if self.incident(w,cur,state):
            return
        if self.caller_health(w,cur,state):
            return
        if self.verify(w,cur,state):
            return
        if ts<self.s.get('supervisor_pause:'+wid,''):
            return
        # One fixed daily look, persisted before any decision, at most seven looks per dimension.
        if int(ts[11:13])!=11 or ts[14:16]!='00':
            return
        primary = metric(w['objective']['primary'])
        dims = ['caller_id'] if primary=='pickup' else ['voice','welcome_message','caller_id']
        for dim in dims:
            opts = w['options'][dim]
            if dim in self.s.get('protected:'+wid,[]) or len(opts)<2 or len(opts)>10 or cur['config'].get('cohorts'):
                continue
            exp = self.s.db.execute('SELECT started,stage,baseline FROM experiments WHERE workflow=? AND dim=?',(wid,dim)).fetchone()
            cfg = copy.deepcopy(cur['config'])
            if not exp:
                old_dist = cfg['allocations']['default'][dim]
                cfg['allocations']['default'][dim] = {v:.7*old_dist.get(v,0)+.3/len(opts) for v in opts}
                if self.propose(w,cur,cfg,ts,'Measure '+dim+' alternatives with 30% exploration traffic',{'estimated_lift':0,'uncertainty':'exploration; benefit unknown'},
                    {'dimension':dim,'stage':'exploring','baseline':cur['config']['allocations']['default'][dim]}):
                    return
                continue
            start,stage,baseline_text = exp
            baseline = json.loads(baseline_text)
            look_key = f'look:{wid}:{dim}:{start}'
            looks = self.s.get(look_key,[])
            if ts[:10] in looks or len(looks)>=7 or ts[:13]<=start:
                continue
            with self.s.db:
                self.s.set(look_key,looks+[ts[:10]])
            stats = self.s.stats(wid,dim,since=max(start,shifted(ts,-48)[:13]) if stage=='promoted' else start,until=ts,prompt=cfg['prompt_version'])
            target = 'pickup' if dim=='caller_id' else primary
            best = winner(stats,target)
            control = max(baseline,key=baseline.get)
            if not best or control not in stats:
                with self.s.db:
                    self.s.audit(ts,wid,'insufficient_evidence',{'dimension':dim,'stage':stage,'stats':stats,'look':len(looks)+1})
                if stage=='exploring':
                    return
                continue
            other = 'engagement' if primary=='pickup' else 'pickup'
            allowed_drop = w['objective']['guardrail'].get(other+'_rate_max_drop',.02)
            # Conservative unpooled noninferiority interval against original control.
            a,b = stats[best],stats[control]
            n1 = a['dials'] if other=='pickup' else a['connected']
            n0 = b['dials'] if other=='pickup' else b['connected']
            pa,pb = rate(a,other),rate(b,other)
            lower = pa-pb-1.645*(pa*(1-pa)/n1+pb*(1-pb)/n0)**.5
            if best!=control and lower < -allowed_drop:
                with self.s.db:
                    self.s.audit(ts,wid,'guardrail_blocked',{'dimension':dim,'lower_difference':lower,'allowed_drop':allowed_drop,'stats':stats})
                return
            allocation = {v:.2/(len(opts)-1) for v in opts if v!=best}
            allocation[best] = .8
            if stage=='promoted':
                current_best = max(cfg['allocations']['default'][dim],key=cfg['allocations']['default'][dim].get)
                if current_best==best:
                    continue
            cfg['allocations']['default'][dim] = allocation
            lift = max(0,rate(a,target)-rate(b,target))
            if self.propose(w,cur,cfg,ts,('Reallocate after winner decay: ' if stage=='promoted' else 'Promote measured winner: ')+dim+' '+best,
                {'stats':stats,'winner':best,'control':control,'primary':target,'guardrail_lower_difference':lower,'estimated_lift':lift,'z':3.5,'look':len(looks)+1},
                {'dimension':dim,'stage':'promoted','baseline':baseline}):
                return

    def cycle(self):
        state = self.get('/sim/state')
        previous = self.s.get('state')
        if previous and (state['sim_minute']<previous['sim_minute'] or state['scenario']!=previous['scenario'] or state['last_event_id']<self.s.get('event_id',0)):
            raise RuntimeError('Simulator changed or reset: use a fresh controller database for a new run')
        self.ingest()
        workflows = self.get('/workflows')
        with self.s.db:
            self.s.set('state',state)
            self.s.set('workflows',workflows)
        self.reconcile(workflows,state['ts'])
        if state['finished']:
            return False
        # Stable rotating order prevents the same tenant always spending incident credits first.
        offset = (state['sim_minute']//60)%len(workflows)
        for w in workflows[offset:]+workflows[:offset]:
            self.decide(w,self.get(f'/workflows/{w["workflow_id"]}/config'),self.get('/sim/state'))
        self.reconcile(workflows,state['ts'])
        before = state['sim_minute']
        r = self.request('POST','/sim/advance',{'minutes':60})
        if not r.is_success and r.status_code!=409:
            r.raise_for_status()
        with self.s.db:
            self.s.set('last_advance',before)
        print(json.dumps({'ts':state['ts'],'events':self.s.get('event_id'),'credits':self.get('/sim/state')['credits_remaining']}),flush=True)
        return True
