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
