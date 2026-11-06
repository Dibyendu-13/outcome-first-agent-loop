"""Read-only, transactionally consistent supervisor projections over controller records."""
import json
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from .statistics import interval


def decode(value, default=None):
    if value is None:
        return default
    return json.loads(value)


def rates(counts):
    result = dict(counts)
    result['pickup_rate'] = counts['connected']/counts['dials'] if counts['dials'] else None
    result['engagement_rate'] = counts['engaged']/counts['connected'] if counts['connected'] else None
    result['flag_rate'] = counts['flags']/counts['connected'] if counts['connected'] else None
    return result


def blank():
    return dict(dials=0,connected=0,engaged=0,flags=0)


class Dashboard:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.lock = threading.Lock()
        self.cached_key = None
        self.cached = None

    def snapshot(self):
        # Opening an unknown path must never create a misleading empty controller database.
        with self.lock:
            with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
                db.execute('PRAGMA query_only=ON')
                db.execute('BEGIN')
                meta = {k:decode(v) for k,v in db.execute('SELECT key,value FROM meta')}
                last_audit = db.execute('SELECT coalesce(max(id),0),count(*) FROM audit').fetchone()
                key = (json.dumps(meta,sort_keys=True),last_audit,
                       tuple(db.execute('SELECT status,count(*) FROM proposals GROUP BY status')))
                if key==self.cached_key:
                    return self.cached
                result = self._build(db,meta,last_audit[1])
                self.cached_key,self.cached = key,result
                return result

    def _build(self, db, meta, audit_count):
        state = meta.get('state')
        start = (datetime.fromisoformat(state['ts'])-timedelta(minutes=state['sim_minute'])).isoformat() if state else None
        finish = bool(state and state['finished'])
        workflow_specs = meta.get('workflows',[])
        ids = [w['workflow_id'] for w in workflow_specs]
        live = {w:blank() for w in ids}
        historical = {w:blank() for w in ids}
        daily = {}
        # Aggregate every actual cohort exactly once; diagnostic dimensions never enter KPI sums.
        for wf,hour,dials,connected,engaged,flags in db.execute('SELECT workflow,hour,sum(dials),sum(connected),sum(engaged),sum(hallucinations) FROM metrics WHERE dim="all" GROUP BY workflow,hour'):
            counts = dict(zip(('dials','connected','engaged','flags'),(dials,connected,engaged,flags)))
            dest = live if start and hour>=start[:13] else historical
            dest.setdefault(wf,blank())
            for k,v in counts.items():
                dest[wf][k]+=v
            if start and hour>=start[:13]:
                day = daily.setdefault((wf,hour[:10]),blank())
                for k,v in counts.items():
                    day[k]+=v
        campaigns,uploaded = {},{w:0 for w in ids}
        if start:
            for wf,payload in db.execute('SELECT workflow,payload FROM events WHERE type="campaign_created" AND ts>=?',(start,)):
                event = decode(payload)
                campaigns[event['campaign_id']] = wf
                uploaded[wf] = uploaded.get(wf,0)+event['leads']
        enrolled,concluded = {w:0 for w in ids},{w:0 for w in ids}
        # Concluded calls during D0 may belong to historical campaigns. Business outcomes instead
        # follow the leads enrolled in campaigns uploaded during the selected run.
        if campaigns:
            for wf,campaign,n,done in db.execute('SELECT workflow,campaign,count(*),sum(concluded) FROM leads GROUP BY workflow,campaign'):
                if campaign in campaigns:
                    enrolled[wf] = enrolled.get(wf,0)+n
                    concluded[wf] = concluded.get(wf,0)+done
        ingestion = dict(zip(('events','seconds','chunks'),db.execute('SELECT coalesce(sum(events),0),coalesce(sum(seconds),0),count(*) FROM chunks').fetchone()))
        ingestion['events_per_second'] = ingestion['events']/ingestion['seconds'] if ingestion['seconds'] else None
        ingestion['event_lag'] = max(0,state.get('last_event_id',0)-meta.get('event_id',0)) if state else None
        incidents = {k.split(':',1)[1]:v for k,v in meta.items() if k.startswith('incident:') and v}
        charges = [dict(key=k,status=s,result=decode(r)) for k,s,r in db.execute('SELECT key,status,result FROM charges')]
        proposals = []
        for pid,wf,status,approval,body,reason,created in db.execute('SELECT * FROM proposals ORDER BY created DESC,id'):
            body,plan = decode(body,{}),decode(reason,{})
            proposals.append(dict(id=pid,workflow=wf,status=status,approval=approval,created=created,
                summary=body.get('change_summary','Configuration proposal'),diff=body.get('diff',{}),
                affected_leads=body.get('affected_leads'),impact_score=body.get('impact_score'),
                rationale=body.get('rationale',''),dry_run=body.get('dry_run',{}),evidence=body.get('evidence',{}),
                base_version=body.get('base_version'),config=body.get('proposed_config',{}),plan=plan))
        audits = [dict(id=i,ts=ts,workflow=wf,kind=kind,evidence=decode(payload,{})) for i,ts,wf,kind,payload in db.execute('SELECT id,ts,workflow,kind,payload FROM audit ORDER BY ts DESC,id DESC LIMIT 1000')]
        # Detail receipts are not limited by the recent-activity window.
        decisions,applied,latest_configs = {},{},{}
        for event_id,ts,wf,kind,payload in db.execute('SELECT id,ts,workflow,type,payload FROM events WHERE type IN ("approval_decided","config_changed")'):
            ev = decode(payload,{})
            receipt = dict(id=event_id,ts=ts,workflow=wf,kind=kind,evidence=ev)
            if kind=='approval_decided':
                decisions[ev['approval_id']] = receipt
            elif kind=='config_changed':
                if wf not in latest_configs or ev['version']>latest_configs[wf]['evidence']['version']:
                    latest_configs[wf] = receipt
                if ev.get('proposal_id'):
                    applied[ev['proposal_id']] = receipt
        for p in proposals:
            p['decision'] = decisions.get(p['approval'])
            p['applied_event'] = applied.get(p['id'])
        workflows = []
        for w in workflow_specs:
            wf = w['workflow_id']
            kpi = rates(live.get(wf,blank()))
            reference = rates(historical.get(wf,blank()))
            kpi.update(uploaded=uploaded.get(wf,0),enrolled=enrolled.get(wf,0),concluded=concluded.get(wf,0))
            kpi['conclusion_rate'] = kpi['concluded']/kpi['uploaded'] if kpi['uploaded'] else None
            config = meta.get('config:'+wf)
            receipt = latest_configs.get(wf)
            if receipt and receipt['evidence']['version']>(config or {}).get('version',0):
                proposal = next((p for p in proposals if p['id']==receipt['evidence'].get('proposal_id')),None)
                config = dict(version=receipt['evidence']['version'],actor=receipt['evidence']['actor'],
                    config=proposal['config'] if proposal else {},available=bool(proposal))
            workflows.append(dict(**w,kpis=kpi,history=reference,incident=incidents.get(wf),
                config=config,daily=[dict(date=day,**rates(counts)) for (wid,day),counts in sorted(daily.items()) if wid==wf]))
        experiments = []
        for wf,dim,started,stage,baseline in db.execute('SELECT * FROM experiments ORDER BY workflow,dim'):
            w = next((w for w in workflows if w['workflow_id']==wf),{})
            config = (w.get('config') or {}).get('config',{})
            prompt = config.get('prompt_version')
            since = max(started,(datetime.fromisoformat(state['ts'])-timedelta(hours=48)).isoformat()[:13]) if stage=='promoted' and state else started
            sql = 'SELECT option,sum(dials),sum(connected),sum(engaged),sum(hallucinations) FROM metrics WHERE workflow=? AND dim=? AND cohort="default" AND hour>=?'
            args = [wf,dim,since]
            if prompt:
                sql += ' AND prompt=?'
                args.append(prompt)
            observed = {r[0]:dict(zip(('dials','connected','engaged','flags'),r[1:])) for r in db.execute(sql+' GROUP BY option',args)}
            options = w.get('options',{}).get(dim,list(observed))
            primary = 'pickup' if dim=='caller_id' or w.get('objective',{}).get('primary')=='pickup_rate' else 'engagement'
            allocation = config.get('allocations',{}).get('default',{}).get(dim)
            allocation_known = allocation is not None
            arms = []
            for opt in options:
                counts = observed.get(opt,blank())
                arms.append(dict(option=opt,**rates(counts),allocation=allocation.get(opt,0) if allocation_known else None,
                    minimum_connected=400,sample_ready=counts['connected']>=400,
                    interval=list(interval(counts,primary))))
            enough = bool(arms) and all(a['sample_ready'] for a in arms)
            status = ('completed' if stage=='promoted' else 'ended_inconclusive') if finish else stage
            last_evaluation = next((a for a in audits if a['workflow']==wf and a['evidence'].get('dimension')==dim and a['kind'] in ('insufficient_evidence','guardrail_blocked') and a['ts'][:13]>=started),None)
            if finish and stage=='promoted':
                explanation = 'Promotion recorded; the run has finished.'
            elif finish:
                explanation = 'No promotion was recorded before the run ended.'
                if last_evaluation:
                    last_stats = last_evaluation['evidence'].get('stats',{})
                    if last_evaluation['kind']=='guardrail_blocked':
                        explanation += ' The last candidate did not pass the guardrail check.'
                    elif last_stats and any(v.get('connected',0)<400 for v in last_stats.values()):
                        explanation += ' The last evaluation lacked the required sample. Final observations below may include later calls.'
                    else:
                        explanation += ' The last evaluation did not establish a statistically separated winner.'
            else:
                explanation = ('Monitoring the promoted allocation and sentinel alternatives.' if stage=='promoted' else
                    'Collecting at least 400 connected calls per arm.' if not enough else 'Minimum sample reached; awaiting a deterministic evaluation.')
            experiments.append(dict(workflow=wf,dimension=dim,started=started,stage=stage,status=status,
                explanation=explanation,last_evaluation=last_evaluation,baseline=decode(baseline,{}),metric=primary,arms=arms,
                looks=len(meta.get(f'look:{wf}:{dim}:{started}',[])),maximum_looks=7))
        total = blank()
        for counts in live.values():
            for k in total:
                total[k]+=counts[k]
        total = rates(total)
        total.update(uploaded=sum(uploaded.values()),enrolled=sum(enrolled.values()),concluded=sum(concluded.values()))
        total['conclusion_rate'] = total['concluded']/total['uploaded'] if total['uploaded'] else None
        return dict(state=state,period=dict(start=start,end=(state or {}).get('ts')),
            summary=total,ingestion=ingestion,workflows=workflows,experiments=experiments,
            proposals=proposals,incidents=incidents,paid_operations=charges,activity=audits,
            activity_total=audit_count,activity_limit=1000,
            definitions=dict(reference='Before-run call history, not a no-op control or causal lift estimate.',
                outcome='Concluded leads from campaigns uploaded during this run / leads uploaded during this run.',
                flags='Automated QA flags on connected calls; not confirmed hallucinations.',
                impact='Measured absolute rate lift when available; zero means benefit not estimated.',
                affected='Upper bound of unconcluded enrollments; may include leads that exhausted cadence.'))
