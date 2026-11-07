"""Policy-aware controller. All knowledge of the world comes from HTTP."""
import copy
import hashlib
import json
import time
from datetime import datetime, timedelta

import httpx

from .statistics import interval, rate, winner,binomial_greater
from .learning import Learner
from .faults import hit
from .evidence import population,replay


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
        learning = plan.get('learning')
        if learning:
            learning = copy.deepcopy(learning)
            learning.update(version=body['base_version']+1,started=shifted(ts,.25))
            self.s.set('learning:'+body['workflow_id'],learning)
            self.s.set('learning_epoch:'+body['workflow_id'],learning['epoch'])
            self.s.set('cohorts:'+body['workflow_id'],learning['cohorts'])
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
                    if status in ('rejected','expired','lapsed'):
                        self.s.audit(ts,wid,'proposal_closed',{'proposal_id':pid,'status':status,'reasons':approval.get('reasons',[])})
                        self.close_learning_snapshot(wid)
            cur = self.get(f'/workflows/{wid}/config')
            if status in ('pending','approved') and cur['version']!=body['base_version']:
                with self.s.db:
                    self.s.db.execute('UPDATE proposals SET status="stale" WHERE id=?',(pid,))
                    self.close_learning_snapshot(wid)
                    self.s.audit(ts,wid,'stale_proposal',{'proposal_id':pid,'current_version':cur['version'],'previous_status':status})
                continue
            if status in ('prepared','unknown') and not approval:
                if cur['version']!=body['base_version']:
                    with self.s.db:
                        self.s.db.execute('UPDATE proposals SET status="stale" WHERE id=?',(pid,))
                        self.close_learning_snapshot(wid)
                    continue
                auto = json.loads(reason).get('auto',False)
                r = self.request('PUT' if auto else 'POST',f'/workflows/{wid}/config' if auto else '/approvals',body)
                hit('proposal_after_send')
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
                        self.close_learning_snapshot(wid)
                        self.s.audit(ts,wid,'stale_proposal',{'proposal_id':pid,'current_version':cur['version']})
                    continue
                r = self.request('POST',f'/workflows/{wid}/apply',{'approval_id':aid})
                hit('apply_after_send')
                with self.s.db:
                    if r.is_success:
                        self.record_applied(pid,body,reason,ts)
                    else:
                        self.s.db.execute('UPDATE proposals SET status=? WHERE id=?',('stale' if r.status_code==409 else 'lapsed' if r.status_code==410 else 'failed',pid))
                        self.close_learning_snapshot(wid)
                        self.s.audit(ts,wid,'apply_failed',{'proposal_id':pid,'response':r.json()})

    def close_learning_snapshot(self,wid):
        trial=self.s.get('learning:'+wid)
        if trial and trial.get('pending'):
            trial.pop('pending',None)
            trial['rejected_looks']=list(set(trial.get('rejected_looks',[]))|set(trial['tested']))
            self.s.set('learning:'+wid,trial)

    def propose(self, w, cur, cfg, ts, summary, evidence, plan):
        wid = w['workflow_id']
        if cfg==cur['config']:
            return False
        dims = []
        for d in ('voice','welcome_message','caller_id'):
            groups=set(cfg['allocations'])|set(cur['config']['allocations'])
            if any(cfg['allocations'].get(c,{}).get(d,cfg['allocations']['default'].get(d))!=cur['config']['allocations'].get(c,{}).get(d,cur['config']['allocations']['default'].get(d)) for c in groups):
                dims.append(d)
        for d in ('prompt_version','cohorts','schedule'):
            if cfg.get(d)!=cur['config'].get(d):dims.append(d)
        pol = w['governance']
        auto_pol = pol['auto_apply']
        shifts=[]
        for d in ('voice','welcome_message','caller_id'):
            for c in set(cfg['allocations'])|set(cur['config']['allocations']):
                new=cfg['allocations'].get(c,{}).get(d,cfg['allocations']['default'].get(d,{}))
                old=cur['config']['allocations'].get(c,{}).get(d,cur['config']['allocations']['default'].get(d,{}))
                shifts.append(sum(abs(new.get(k,0)-old.get(k,0)) for k in set(new)|set(old))/2)
        shift=max(shifts or [0])
        auto = dims==['caller_id'] and auto_pol['enabled'] and 'caller_id' in auto_pol['allowed_dims'] and shift<=auto_pol['max_shift']+1e-9
        critical=bool(evidence.get('safety_only') or evidence.get('rollback_of') or evidence.get('rollback_requested') or evidence.get('bad'))
        if not auto:
            hour = int(ts[11:13])
            start,end = pol['approver_hours']
            if w['tenant_id']=='kestrel_finance':
                start = max(start,11)
            # Critical fixes may use the final working hour; policy TTL still governs overnight waiting.
            if not start<=hour<end-(0 if critical else 1):
                return False
        limit = min(2,pol['max_requests_per_24h'])
        requests = self.s.db.execute('SELECT count(*) FROM proposals WHERE workflow=? AND created>?',(wid,shifted(ts,-24))).fetchone()[0]
        attention_limit=limit if critical or limit==1 else limit-1
        if requests>=attention_limit:return False
        populations,population_evidence=population(self.s,w,cur['config'],cfg,ts,dims)
        affected=population_evidence.get('existing_campaigns_affected',sum(populations.values()))
        replay_evidence=replay(cur['config'],cfg,evidence.get('cohort_comparisons',[]),populations,plan.get('dimension','voice'))
        expected=replay_evidence['weighted_estimated_lift']
        evidence=dict(evidence,population=population_evidence,replay=replay_evidence)
        # An unknown estimate remains unknown; zero is the API-required queue score, not a claimed zero effect.
        expected=expected if expected is not None else 0
        body = {'workflow_id':wid,'base_version':cur['version'],'proposed_config':cfg,
            'change_summary':summary,'diff':{d:cfg.get(d) if d in ('prompt_version','cohorts','schedule') else {c:v[d] for c,v in cfg['allocations'].items() if d in v} for d in dims},
            'affected_leads':affected,'dry_run':{'method':'historical cohort evidence and proposed-allocation replay; causal assumptions stated in evidence','evidence':evidence,'affected_leads_method':'upper bound: active-cadence unconcluded enrollments; excludes expired campaigns; may include exhausted attempts'},
            'impact_score':round(min(1,max(0,expected)),4),'rationale':summary+'; '+json.dumps(evidence,sort_keys=True),
            'evidence':evidence.get('validation',{})}
        # Content-derived identity survives crash between local intent and remote acknowledgement.
        identity = json.dumps([body,ts[:16]],sort_keys=True)
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
            if row[0]=='unknown' and not self.s.get('alerted_paid:'+key):
                with self.s.db:
                    self.s.set('alerted_paid:'+key,True)
                    self.s.audit(ts,wid,'alert_unknown_paid_operation',{'key':key,'action':'Inspect the provider receipt; do not retry without reconciliation. API has no retrieval/idempotency support.'})
            return json.loads(row[1]) if row[0]=='complete' else None
        # The API has no idempotency/retrieval for paid operations. Never blindly repeat an unknown charge.
        with self.s.db:
            self.s.db.execute('INSERT INTO charges VALUES (?,"unknown",NULL)',(key,))
        r = self.request('POST',endpoint,body)
        hit('paid_after_send')
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
            from math import log,exp,pi
            episode=self.s.get('prompt_episode:'+wid)
            if not episode or episode['prompt']!=prompt:
                started=cur.get('applied_at') or shifted(ts,-state['sim_minute']/60)
                baseline=self.s.stats(wid,until=started).get('all')
                base=baseline['hallucinations']/baseline['connected'] if baseline and baseline['connected']>=400 else .01
                prefix={'dials':0,'connected':0,'engaged':0,'hallucinations':0}
                if started[14:16]!='00':
                    values=self.s.db.execute('SELECT count(*),coalesce(sum(connected),0),coalesce(sum(engaged),0),coalesce(sum(hallucination),0) FROM calls WHERE workflow=? AND prompt=? AND ts>=? AND ts<?',(wid,prompt,started[:13]+':00:00'+started[19:],started)).fetchone()
                    prefix=dict(zip(prefix,values))
                episode=dict(prompt=prompt,started=started,baseline=baseline,prefix=prefix,null_rate=min(.05,max(.02,base+.002)),
                    number=(episode or {}).get('number',0)+1)
                with self.s.db:self.s.set('prompt_episode:'+wid,episode)
            recent=self.s.stats(wid,since=episode['started'],until=ts,prompt=prompt).get('all')
            if not recent:return False
            recent={k:max(0,v-episode.get('prefix',{}).get(k,0)) for k,v in recent.items()}
            if recent['connected']<200:return False
            # Fixed doubling sample prefixes; geometric look spending and summable prompt-episode
            # spending give a 5% per-workflow false-alert budget under the stated conditional null.
            tested=episode.setdefault('tested',[])
            detection=None
            for look in range(16):
                n=200*2**look
                if n>recent['connected']:break
                if n in tested:continue
                flags=[r[0] for r in self.s.db.execute('SELECT hallucination FROM calls WHERE workflow=? AND prompt=? AND ts>=? AND connected=1 ORDER BY id LIMIT ?',
                    (wid,prompt,episode['started'],n))]
                if len(flags)<n:continue
                k=sum(flags);p=k/n;null=episode['null_rate']
                alpha=.05*6/(pi*pi*episode['number']**2)*.5**(look+1)
                p_value=binomial_greater(k,n,null)
                tested.append(n)
                if p_value<=alpha and p>=.04:
                    detection=dict(prompt=prompt,detected=ts,recent=recent,baseline=episode['baseline'],threshold=null,
                        fixed_sample=n,flagged=k,p_value=p_value,alpha=alpha,
                        method='exact binomial tail at fixed doubling sample prefixes; 5% per-workflow alert budget; assumes conditional flag probability <= reference bound')
                    break
            with self.s.db:self.s.set('prompt_episode:'+wid,episode)
            if detection is None:return False
            incident=detection
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
            'safety_only':True,'candidate_selection':'prefer observed engagement lower bound among safety-passing candidates',
            'latest_recent':self.s.stats(wid,since=shifted(ts,-4),until=ts,prompt=prompt).get('all'),
            'evidence_as_of':ts,'event_checkpoint':self.s.get('event_id',0)}
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
                    groups=set(old['config']['allocations'])|set(cur['config']['allocations'])
                    if any(old['config']['allocations'].get(c,{}).get(d,old['config']['allocations']['default'].get(d))!=cur['config']['allocations'].get(c,{}).get(d,cur['config']['allocations']['default'].get(d)) for c in groups):
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
        return Learner(self).step(w,cur,state)

    def cycle(self):
        cycle_started=time.monotonic()
        previous_checkpoint=self.s.get('event_id',0)
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
        with self.s.db:
            run_start=shifted(state['ts'],-state['sim_minute']/60)
            lag=list(self.s.db.execute('SELECT round((strftime("%s",?)-strftime("%s",ts))/60.0,3),count(*) FROM calls WHERE id>? AND ts>=? GROUP BY 1',(state['ts'],previous_checkpoint,run_start)))
            self.s.audit(state['ts'],'','decision_latency',{'seconds':time.monotonic()-cycle_started,'event_checkpoint':self.s.get('event_id',0),'sim_minute':state['sim_minute'],'simulated_lag_histogram':lag})
        before = state['sim_minute']
        windows=[max(15,int(w['governance'].get('apply_window_hours',1)*60/2)//15*15) for w in workflows]
        pending=self.s.db.execute('SELECT 1 FROM proposals WHERE status IN ("prepared","pending","approved","unknown")').fetchone()
        minutes=15 if pending or any(self.s.get('incident:'+w['workflow_id']) for w in workflows) else min(60,min(windows))
        # During dialling hours check quarter-hour prompt incidents before approvers close.
        if any(w['dialling_window'][0]<=int(state['ts'][11:13])<w['dialling_window'][1] for w in workflows):minutes=15
        advance_started=time.monotonic()
        r = self.request('POST','/sim/advance',{'minutes':minutes})
        hit('advance_after_send')
        with self.s.db:
            self.s.set('last_tick_minutes',minutes)
            self.s.audit(state['ts'],'','loop_timing',{'advance_seconds':time.monotonic()-advance_started,'tick_minutes':minutes})
        if not r.is_success and r.status_code!=409:
            r.raise_for_status()
        with self.s.db:
            self.s.set('last_advance',before)
        print(json.dumps({'ts':state['ts'],'events':self.s.get('event_id'),'credits':self.get('/sim/state')['credits_remaining']}),flush=True)
        return True
