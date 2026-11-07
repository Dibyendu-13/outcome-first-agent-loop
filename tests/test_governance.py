import copy
import json

import httpx
import pytest

from controller.engine import Engine
from controller.store import Store


def make(tmp_path,status='pending'):
    s=Store(tmp_path/'db')
    body={'workflow_id':'w','proposal_id':'p','base_version':1,'proposed_config':{}}
    with s.db:s.db.execute('INSERT INTO proposals VALUES (?,?,?,?,?,?,?)',('p','w',status,'a',json.dumps(body),'{}','2027-01-04T10:00:00+05:30'))
    return s,body


@pytest.mark.parametrize('terminal',['rejected','expired','lapsed'])
def test_terminal_approval_closes_without_replaying(tmp_path,terminal):
    s,_=make(tmp_path)
    calls=[]
    def handler(r):
        calls.append(r.method)
        if r.url.path=='/approvals':return httpx.Response(200,json=[{'proposal_id':'p','approval_id':'a','status':terminal,'reasons':['test']}])
        if r.url.path.endswith('/history'):return httpx.Response(200,json=[])
        return httpx.Response(200,json={'version':1})
    client=httpx.Client(base_url='http://fixture',transport=httpx.MockTransport(handler))
    Engine('http://fixture',s,client).reconcile([{'workflow_id':'w'}],'2027-01-04T11:00:00+05:30')
    assert s.db.execute('SELECT status FROM proposals').fetchone()[0]==terminal
    assert set(calls)=={'GET'}
    client.close();s.db.close()


def test_stale_pending_work_does_not_block_incidents_until_human_response(tmp_path):
    s,_=make(tmp_path)
    def handler(r):
        assert r.method=='GET'
        if r.url.path=='/approvals':return httpx.Response(200,json=[{'proposal_id':'p','approval_id':'a','status':'pending'}])
        if r.url.path.endswith('/history'):return httpx.Response(200,json=[])
        return httpx.Response(200,json={'version':2,'actor':'supervisor'})
    client=httpx.Client(base_url='http://fixture',transport=httpx.MockTransport(handler))
    Engine('http://fixture',s,client).reconcile([{'workflow_id':'w'}],'2027-01-04T11:00:00+05:30')
    assert s.db.execute('SELECT status FROM proposals').fetchone()[0]=='stale'
    client.close();s.db.close()


def test_apply_lapse_closes_and_requires_fresh_decision(tmp_path):
    s,_=make(tmp_path,'approved')
    def handler(r):
        if r.method=='POST':return httpx.Response(410,json={'error':'approval_lapsed'})
        if r.url.path=='/approvals':return httpx.Response(200,json=[{'proposal_id':'p','approval_id':'a','status':'approved'}])
        if r.url.path.endswith('/history'):return httpx.Response(200,json=[])
        return httpx.Response(200,json={'version':1})
    client=httpx.Client(base_url='http://fixture',transport=httpx.MockTransport(handler))
    Engine('http://fixture',s,client).reconcile([{'workflow_id':'w'}],'2027-01-04T11:00:00+05:30')
    assert s.db.execute('SELECT status FROM proposals').fetchone()[0]=='lapsed'
    client.close();s.db.close()


def test_503_after_remote_apply_is_reconciled_without_second_apply(tmp_path):
    s,_=make(tmp_path,'approved');applies=0;applied=False
    def handler(r):
        nonlocal applies,applied
        if r.method=='POST':
            applies+=1;applied=True
            return httpx.Response(503,json={'error':'response lost after commit'})
        if r.url.path=='/approvals':return httpx.Response(200,json=[{'proposal_id':'p','approval_id':'a','status':'applied' if applied else 'approved'}])
        if r.url.path.endswith('/history'):return httpx.Response(200,json=[{'proposal_id':'p','applied_at':'2027-01-04T11:00:00+05:30'}] if applied else [])
        return httpx.Response(200,json={'version':1})
    client=httpx.Client(base_url='http://fixture',transport=httpx.MockTransport(handler));e=Engine('http://fixture',s,client)
    with pytest.raises(httpx.HTTPStatusError):e.reconcile([{'workflow_id':'w'}],'2027-01-04T11:00:00+05:30')
    e.reconcile([{'workflow_id':'w'}],'2027-01-04T11:15:00+05:30')
    assert applies==1 and s.db.execute('SELECT status FROM proposals').fetchone()[0]=='applied'
    client.close();s.db.close()


def test_rejection_retires_fixed_look_and_pending_snapshot(tmp_path):
    s,_=make(tmp_path)
    with s.db:s.set('learning:w',{'tested':{'c:V2:promotion:200':{'p':.0001}},'pending':{'config':{}}})
    e=Engine('http://fixture',s)
    with s.db:e.close_learning_snapshot('w')
    trial=s.get('learning:w')
    assert 'pending' not in trial
    assert 'c:V2:promotion:200' in trial['rejected_looks']
    e.c.close();s.db.close()


def test_incident_look_rolls_back_if_audit_write_fails(tmp_path, monkeypatch):
    s, _ = make(tmp_path)
    e = Engine('http://fixture', s)
    ts = '2027-01-04T11:00:00+05:30'
    current = {'config': {'prompt_version': 'P1'}, 'applied_at': ts}
    state = {'ts': ts, 'sim_minute': 660}
    monkeypatch.setattr(s, 'stats', lambda *args, **kwargs: {
        'all': {'dials': 200, 'connected': 200, 'engaged': 0, 'hallucinations': 200}
    })
    with s.db:
        s.db.executemany(
            'INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            [(i, 'w', str(i), str(i), ts, 1, 'default', 'P1', 'V1', 'W1', 'D1', 1, 0, 1)
             for i in range(200)],
        )
    audit = s.audit

    def fail_audit(*args):
        raise RuntimeError('interrupted incident commit')

    monkeypatch.setattr(s, 'audit', fail_audit)
    with pytest.raises(RuntimeError, match='interrupted incident commit'):
        e.incident({'workflow_id': 'w'}, current, state, detect_only=True)
    assert s.get('incident:w') is None
    assert not s.get('prompt_episode:w').get('tested')
    monkeypatch.setattr(s, 'audit', audit)
    assert e.incident({'workflow_id': 'w'}, current, state, detect_only=True)
    assert s.get('incident:w')['fixed_sample'] == 200
    assert s.get('prompt_episode:w')['tested'] == [200]
    e.c.close()
    s.db.close()


def test_open_incident_holds_an_approved_ordinary_change(tmp_path):
    s, _ = make(tmp_path, 'approved')
    with s.db:
        s.set('incident:w', {'prompt': 'P1'})

    def handler(request):
        assert request.method == 'GET'
        if request.url.path == '/approvals':
            return httpx.Response(200, json=[{
                'proposal_id': 'p', 'approval_id': 'a', 'status': 'approved',
            }])
        if request.url.path.endswith('/history'):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={'version': 1, 'config': {'prompt_version': 'P1'}})

    with httpx.Client(base_url='http://fixture', transport=httpx.MockTransport(handler)) as client:
        Engine('http://fixture', s, client).reconcile([{'workflow_id': 'w'}], '2027-01-04T11:00:00+05:30')
    assert s.db.execute('SELECT status FROM proposals').fetchone() == ('approved',)
    s.db.close()


def test_harmful_verification_survives_closed_approval_window(tmp_path, monkeypatch):
    s, _ = make(tmp_path)
    e = Engine('http://fixture', s)
    config = {'prompt_version': 'P1'}
    applied = '2027-01-04T10:00:00+05:30'
    with s.db:
        s.set('monitor:w', {
            'version': 2, 'baseline_version': 1, 'applied': applied,
            'previous': config, 'proposal_id': 'p',
        })
    monkeypatch.setattr(s, 'stats', lambda *args, version, **kwargs: {
        'all': {'dials': 1200, 'connected': 800, 'engaged': 700 if version == 1 else 100}
    })
    decisions = []

    def propose(workflow, current, proposed, ts, summary, evidence, plan):
        decisions.append(evidence)
        return len(decisions) == 2

    monkeypatch.setattr(e, 'propose', propose)
    workflow = {'workflow_id': 'w', 'objective': {'primary': 'engagement_rate', 'guardrail': {}}}
    current = {'version': 2, 'actor': 'controller_approved', 'config': config}
    assert not e.verify(workflow, current, {'ts': '2027-01-04T11:15:00+05:30'})
    assert e.verify(workflow, current, {'ts': '2027-01-04T12:00:00+05:30'})
    assert decisions[0] == decisions[1]
    assert decisions[1]['rollback_of'] == 'p'
    e.c.close()
    s.db.close()


def test_caller_rotation_only_changes_cohort_with_evidence(tmp_path, monkeypatch):
    s, _ = make(tmp_path)
    e = Engine('http://fixture', s)
    allocation = {'D1': .6, 'D2': .4}
    config = {
        'cohorts': [{'id': 'other', 'where': {'lang': ['ta']}}],
        'allocations': {'default': {'caller_id': allocation}},
    }

    def stats(*args, cohort, version=None, **kwargs):
        if cohort == 'other':
            return {}
        return {
            'D1': {'dials': 1000, 'connected': 20 if version else 700},
            'D2': {'dials': 1000, 'connected': 700},
        }

    monkeypatch.setattr(s, 'stats', stats)
    proposals = []
    monkeypatch.setattr(e, 'propose', lambda *args: proposals.append(args) or True)
    workflow = {'workflow_id': 'w', 'options': {'caller_id': ['D1', 'D2']}}
    assert e.caller_health(workflow, {'version': 2, 'config': config},
                           {'ts': '2027-01-04T11:00:00+05:30'})
    proposed = proposals[0][2]['allocations']
    assert proposed['default']['caller_id'] == {'D2': 1.0}
    assert proposed['other']['caller_id'] == allocation
    e.c.close()
    s.db.close()


def test_tenant_credit_hold_blocks_second_workflow(tmp_path, monkeypatch):
    s, _ = make(tmp_path)
    e = Engine('http://fixture', s)
    ts = '2027-01-04T11:00:00+05:30'
    with s.db:
        s.set('credit_reservation:other', {'incident': 'older', 'tenant': 't', 'maximum': 15})
        s.set('incident:w', {'detected': ts, 'prompt': 'P1'})
    paid = []
    monkeypatch.setattr(e, 'paid', lambda *args: paid.append(args))
    assert e.incident({'workflow_id': 'w', 'tenant_id': 't'},
                      {'config': {'prompt_version': 'P1'}},
                      {'ts': ts, 'credits_remaining': 200})
    assert not paid
    assert s.get('credit_reservation:w') is None
    e.c.close()
    s.db.close()
