"""Real-HTTP contract fixture proving the controller's promotion/decay/approval loop.

This is NOT an official simulator score. The fixture supplies strong, known signals
on both KPIs to exercise paths the short public scenarios cannot reliably power.
The controller receives only HTTP responses; all assertions read its own audit DB.
"""
import copy
from datetime import datetime,timedelta
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
from pathlib import Path
import random
import sqlite3
import sys
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from controller.engine import Engine
from controller.store import Store

ROOT=Path(__file__).resolve().parents[1]


class Fixture:
    def __init__(self):
        self.now=0;self.end=2880;self.seq=0;self.chunks=[];self.approvals={};self.ids=set();self.rng=random.Random(9321)
        self.config={'cohorts':[],'allocations':{'default':{'caller_id':{'D1':1},'voice':{'V1':1},'welcome_message':{'W1':1}}},'prompt_version':'P1','schedule':{'hour_weights':{},'lead_preferred_hour':{}}}
        self.version=1;self.history=[];self.applied_at=None;self.actor='business';self.promoted_at=None;self.enrollments=[]
        self.w=dict(workflow_id='proof',tenant_id='proof_client',languages=['en'],use_case='Learning lifecycle contract fixture',
            dialling_window=[9,21],dials_per_hour=6000,cadence=[2,3],min_gap_minutes=15,daily_batch={'size':60000,'at_hour':8},mid_flight='allowed',
            options={'caller_id':['D1'],'voice':['V1','V2'],'welcome_message':['W1'],'prompt_version':['P1']},
            objective={'primary':'engagement_rate','guardrail':{'pickup_rate_max_drop':.02}},
            governance={'auto_apply':{'enabled':False,'allowed_dims':[],'max_shift':0},'approver_hours':[10,19],
                'approver_latency_minutes':[15,15],'proposal_ttl_hours':24,'apply_window_hours':1,'max_requests_per_24h':3,'min_validation_pass_rate':.97})
        history=[]
        for i in range(1000):history.append(dict(type='lead',workflow_id='proof',lead_id='h'+str(i),person_id='p'+str(i),campaign_id='history',features={'lang':'en'},ts=self.ts(-1440)))
        self.chunk(history,'history')

    def ts(self,minute=None):return (datetime.fromisoformat('2027-01-04T00:00:00+05:30')+timedelta(minutes=self.now if minute is None else minute)).isoformat()

    def event(self,**payload):
        self.seq+=1;return dict(event_id=self.seq,ts=self.ts(),**payload)

    def chunk(self,events,kind='events'):
        if not events:return
        for ev in events:
            if 'event_id' not in ev:self.seq+=1;ev['event_id']=self.seq
        self.chunks.append(dict(chunk=len(self.chunks),kind=kind,text='\n'.join(json.dumps(ev) for ev in events)))

    def state(self):return dict(scenario='contract_learning_cycle',sim_minute=self.now,ts=self.ts(),end_minute=self.end,finished=self.now>=self.end,credits_remaining=200,last_event_id=self.seq,tick_minutes=15)

    def advance(self,minutes):
        first=len(self.chunks)
        for _ in range(minutes//15):
            self.now+=15;hour=self.now%1440//60;events=[]
            for approval in self.approvals.values():
                if approval['status']=='pending' and self.now>=approval['due'] and 10<=hour<19:
                    approval['status']='approved';events.append(self.event(type='approval_decided',workflow_id='proof',approval_id=approval['approval_id'],status='approved',reasons=[]))
            if self.now%1440==480:
                self.enrollments=[];campaign=f'proof:day{self.now//1440}'
                events.append(self.event(type='campaign_created',workflow_id='proof',campaign_id=campaign,leads=60000,config_version_at_creation=self.version))
                for i in range(60000):
                    lead=f'{campaign}:{i}';self.enrollments.append([lead,'p'+str(i),False,-99999,0])
                    events.append(self.event(type='lead',workflow_id='proof',campaign_id=campaign,lead_id=lead,person_id='p'+str(i),features={'lang':'en'}))
            if 9<=hour<21 and self.enrollments:
                drawn=self.rng.sample(self.enrollments,1500)
                dist=self.config['allocations']['default']['voice']
                for lead in drawn:
                    if lead[2] or self.now-lead[3]<15 or lead[4]>=2:continue
                    arm='V1' if self.rng.random()<dist.get('V1',0) else 'V2'
                    decayed=self.promoted_at is not None and self.now>=self.promoted_at+60
                    pickup,engagement=(.85,.85) if arm=='V2' and not decayed else (.04,.02) if arm=='V2' else (.3,.2)
                    connected=self.rng.random()<pickup;engaged=connected and self.rng.random()<engagement
                    lead[2]=engaged;lead[3]=self.now;lead[4]+=1
                    events.append(self.event(type='call',workflow_id='proof',lead_id=lead[0],person_id=lead[1],campaign_id=lead[0].rsplit(':',1)[0],
                        config_version=self.version,cohort_id='default',variant={'caller_id':'D1','voice':arm,'welcome_message':'W1','prompt_version':'P1'},
                        connected=connected,engaged=engaged,qa={'hallucination_flag':False} if connected else None))
            self.chunk(events)
        return dict(self.state(),new_chunks=[{'chunk':c['chunk'],'kind':c['kind']} for c in self.chunks[first:]])

    def request(self,method,path,body,query):
        if path=='/sim/state':return 200,self.state()
        if path=='/workflows':return 200,[self.w]
        if path=='/workflows/proof/config':return 200,dict(version=self.version,config=self.config,actor=self.actor,applied_at=self.applied_at)
        if path=='/workflows/proof/config/history':return 200,self.history
        if path=='/events/chunks':return 200,[{'chunk':c['chunk'],'kind':c['kind']} for c in self.chunks if c['kind']==query.get('kind',['events'])[0] and c['chunk']>int(query.get('after',[-1])[0])]
        if path.startswith('/events/chunks/'):return 200,self.chunks[int(path.rsplit('/',1)[1])]['text']
        if path=='/sim/advance':return 200,self.advance(body['minutes'])
        if path=='/approvals' and method=='GET':return 200,list(self.approvals.values())
        if path=='/approvals':
            if body['proposal_id'] in self.ids:return 409,{'error':'duplicate_proposal_id'}
            if body['base_version']!=self.version:return 409,{'error':'stale_base_version'}
            assert all(body.get(k) for k in ('change_summary','diff','dry_run','rationale'))
            aid='approval_'+str(len(self.approvals)+1);self.ids.add(body['proposal_id'])
            a=dict(body,approval_id=aid,status='pending',due=self.now+15);self.approvals[aid]=a
            return 200,a
        if path=='/workflows/proof/apply':
            a=self.approvals[body['approval_id']]
            if a['base_version']!=self.version:return 409,{'error':'stale_base_version'}
            assert a['status']=='approved'
            self.version+=1;self.config=copy.deepcopy(a['proposed_config']);self.actor='controller_approved';self.applied_at=self.ts();a['status']='applied'
            self.history.append(dict(version=self.version,proposal_id=a['proposal_id'],approval_id=a['approval_id'],applied_at=self.ts()))
            if 'Promote' in a['change_summary']:self.promoted_at=self.now
            self.chunk([self.event(type='config_changed',workflow_id='proof',version=self.version,actor=self.actor,proposal_id=a['proposal_id'],approval_id=a['approval_id'],changed_dims=['voice'])])
            return 200,{'version':self.version}
        return 404,{'error':'no_such_route'}


def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--name',default='learning-proof');args=ap.parse_args()
    fixture=Fixture()
    from urllib.parse import urlsplit,parse_qs
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):self.dispatch('GET')
        def do_POST(self):self.dispatch('POST')
        def dispatch(self,method):
            url=urlsplit(self.path);body=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))) or b'{}')
            status,payload=fixture.request(method,url.path,body,parse_qs(url.query))
            data=payload.encode() if isinstance(payload,str) else json.dumps(payload).encode()
            self.send_response(status);self.send_header('Content-Type','application/x-ndjson' if isinstance(payload,str) else 'application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def log_message(self,*args):pass
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    path=ROOT/'controller-data'/(args.name+'.sqlite')
    if path.exists():raise SystemExit('Proof database exists; preserve evidence and use a fresh checkout/name')
    store=Store(path);engine=Engine(f'http://127.0.0.1:{server.server_port}',store)
    try:
        while engine.cycle():pass
        rows=[dict(ts=ts,kind=kind,evidence=json.loads(payload)) for ts,kind,payload in store.db.execute('SELECT ts,kind,payload FROM audit WHERE workflow="proof" AND kind IN ("proposal_prepared","applied","post_apply_verification")')]
        applied=[json.loads(body) for body, in store.db.execute('SELECT body FROM proposals WHERE status="applied"')]
        summaries=[p['change_summary'] for p in applied]
        assert any('Measure' in x for x in summaries),summaries
        assert any('Promote' in x for x in summaries),summaries
        assert any('Rollback' in x for x in summaries),summaries
        assert all(p['proposal_id'] in fixture.ids for p in applied)
        report=dict(purpose='HTTP contract fixture, not official simulator scoring',finished=fixture.state()['finished'],applied_summaries=summaries,
            governance='Every apply matched an approved remote proposal and current base version',timeline=rows,
            scope='Synthetic joint-KPI effects intentionally isolate the learner from caller-ID health intervention. These are contract test signals, not a real dialler model or official public score.')
        (ROOT/'reports'/(args.name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'proof_passed':True,'applied_summaries':summaries}))
    finally:
        engine.c.close();store.db.close();server.shutdown();server.server_close()


if __name__=='__main__':main()
