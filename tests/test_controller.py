import json

import httpx
import pytest

from controller.engine import Engine
from controller.statistics import interval, winner
from controller.store import Store


def events():
    return [
      {'event_id':1,'type':'lead','workflow_id':'w','lead_id':'l','person_id':'p','campaign_id':'c','features':{'lang':'hi'}},
      {'event_id':2,'type':'call','workflow_id':'w','lead_id':'l','ts':'2027-01-04T10:15:00+05:30','config_version':1,'cohort_id':'default',
       'variant':{'prompt_version':'P1','voice':'V1','welcome_message':'W1','caller_id':'D1'},'connected':False,'engaged':False,'qa':None}]


def test_atomic_replay_and_restart(tmp_path):
    path = tmp_path/'db'
    s = Store(path)
    ev = events()
    with pytest.raises(json.JSONDecodeError):
        s.ingest({'chunk':0,'kind':'history'},[json.dumps(ev[0]),'bad json'])
    assert s.get('event_id') is None
    assert s.db.execute('SELECT count(*) FROM leads').fetchone()[0]==0
    assert s.ingest({'chunk':0,'kind':'history'},map(json.dumps,ev))==2
    s.db.close()
    s = Store(path)
    assert s.ingest({'chunk':0,'kind':'history'},map(json.dumps,ev))==0
    # Even an overlapping chunk must not duplicate the event.
    assert s.ingest({'chunk':1,'kind':'events'},map(json.dumps,ev))==0
    assert s.stats('w')['all']['dials']==1


def test_statistical_abstention_and_strong_winner():
    small = {'dials':100,'connected':30,'engaged':29}
    assert winner({'a':small,'b':small},'engagement') is None
    a = {'dials':20000,'connected':10000,'engaged':8000}
    b = {'dials':20000,'connected':10000,'engaged':5000}
    assert winner({'a':a,'b':b},'engagement')=='a'
    assert winner({'a':a,'b':a},'engagement') is None
    assert interval({'dials':0,'connected':0,'engaged':0},'pickup')==(0,1)


def test_lost_apply_response_reconciles_without_reapply(tmp_path):
    s = Store(tmp_path/'db')
    body = {'proposal_id':'pid','workflow_id':'w','base_version':1}
    with s.db:
        s.db.execute('INSERT INTO proposals VALUES (?,?,?, ?,?,?,?)',('pid','w','approved','apr',json.dumps(body),'{}','2027-01-04T10:00:00+05:30'))
    calls = []
    def handler(request):
        calls.append(request.method+' '+request.url.path)
        if request.url.path=='/approvals':
            return httpx.Response(200,json=[{'proposal_id':'pid','approval_id':'apr','status':'applied'}])
        if request.url.path.endswith('/config/history'):
            return httpx.Response(200,json=[{'proposal_id':'pid','version':2,'applied_at':'2027-01-04T11:00:00+05:30'}])
        raise AssertionError('must not reapply')
    client = httpx.Client(base_url='http://test',transport=httpx.MockTransport(handler))
    Engine('http://test',s,client).reconcile([{'workflow_id':'w'}],'2027-01-04T12:00:00+05:30')
    assert s.db.execute('SELECT status FROM proposals').fetchone()[0]=='applied'
    assert all(c.startswith('GET') for c in calls)


def test_paid_unknown_never_double_charges(tmp_path):
    s = Store(tmp_path/'db')
    with s.db:
        s.db.execute('INSERT INTO charges VALUES (?,?,NULL)',('k','unknown'))
    def handler(request):
        raise AssertionError('must not charge again')
    client = httpx.Client(base_url='http://test',transport=httpx.MockTransport(handler))
    assert Engine('http://test',s,client).paid('k','/validation/runs',{},'now','w') is None


def test_supervisor_edit_makes_approved_proposal_stale(tmp_path):
    s = Store(tmp_path/'db')
    body = {'proposal_id':'pid','workflow_id':'w','base_version':1}
    with s.db:
        s.db.execute('INSERT INTO proposals VALUES (?,?,?, ?,?,?,?)',('pid','w','pending','apr',json.dumps(body),'{}','2027-01-04T10:00:00+05:30'))
    def handler(request):
        assert request.method=='GET'
        if request.url.path=='/approvals':
            return httpx.Response(200,json=[{'proposal_id':'pid','approval_id':'apr','status':'approved'}])
        if request.url.path.endswith('/history'):
            return httpx.Response(200,json=[])
        return httpx.Response(200,json={'version':2,'actor':'supervisor'})
    client = httpx.Client(base_url='http://test',transport=httpx.MockTransport(handler))
    Engine('http://test',s,client).reconcile([{'workflow_id':'w'}],'2027-01-04T12:00:00+05:30')
    assert s.db.execute('SELECT status FROM proposals').fetchone()[0]=='stale'


def policy():
    return {'workflow_id':'w','tenant_id':'t','governance':{'auto_apply':{'enabled':False,'allowed_dims':[],'max_shift':0},
        'approver_hours':[10,19],'max_requests_per_24h':3,'min_validation_pass_rate':.97}}


def configuration():
    return {'version':2,'actor':'supervisor','config':{'cohorts':[],'allocations':{'default':{'voice':{'V1':1},'welcome_message':{'W1':1},'caller_id':{'D1':1}}},'prompt_version':'P2','schedule':{}}}


def test_incident_survives_closed_approver_hours(tmp_path):
    s = Store(tmp_path/'db')
    incident = {'prompt':'P2','detected':'2027-01-04T19:00:00+05:30','recent':{},'baseline':{},
                'candidate':'P1','validation':{'validation_run_id':'val'}}
    with s.db:
        s.set('incident:w',incident)
    engine = Engine('http://test',s)
    assert engine.incident(policy(),configuration(),{'ts':'2027-01-04T19:00:00+05:30','credits_remaining':200})
    assert s.db.execute('SELECT count(*) FROM proposals').fetchone()[0]==0
    assert s.get('incident:w')==incident
    assert engine.incident(policy(),configuration(),{'ts':'2027-01-05T11:00:00+05:30','credits_remaining':200})
    body = json.loads(s.db.execute('SELECT body FROM proposals').fetchone()[0])
    assert body['proposed_config']['prompt_version']=='P1'
    assert body['evidence']['validation_run_id']=='val'
    engine.c.close()


def test_safety_validation_is_not_an_engagement_winner(tmp_path,monkeypatch):
    s = Store(tmp_path/'db')
    with s.db:
        s.set('incident:w',{'prompt':'P2','detected':'2027-01-04T19:00:00+05:30','recent':{},'baseline':{}})
    engine = Engine('http://test',s)
    def paid(key,endpoint,body,ts,wid):
        if endpoint=='/llm/suggest-fixes':
            return {'suggestions':[{'prompt_version':'known'},{'prompt_version':'unknown'}]}
        return {'pass_rate':.98 if body['prompt_version']=='known' else 1.,'validation_run_id':'val'}
    monkeypatch.setattr(engine,'paid',paid)
    monkeypatch.setattr(s,'stats',lambda *a,**kw: {'all':{'dials':2000,'connected':1000,'engaged':600,'hallucinations':10}} if kw.get('prompt')=='known' else {})
    engine.incident(policy(),configuration(),{'ts':'2027-01-05T11:00:00+05:30','credits_remaining':200})
    assert s.get('incident:w')['candidate']=='known'
    engine.c.close()


def test_reset_detected_before_database_ingestion(tmp_path,monkeypatch):
    s = Store(tmp_path/'db')
    with s.db:
        s.set('state',{'sim_minute':60,'scenario':'s'})
        s.set('event_id',100)
    engine = Engine('http://test',s)
    monkeypatch.setattr(engine,'get',lambda *a,**kw:{'sim_minute':0,'scenario':'s','last_event_id':10})
    monkeypatch.setattr(engine,'ingest',lambda:pytest.fail('must detect reset before touching ingestion'))
    with pytest.raises(RuntimeError,match='reset'):
        engine.cycle()
    assert s.get('event_id')==100
    engine.c.close()
