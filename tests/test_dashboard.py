"""Projection tests protect business denominators and evidence provenance."""
import json
import sqlite3

import pytest

from controller.dashboard import Dashboard
from controller.store import Store


def prepare(tmp_path):
    path = tmp_path/'controller.sqlite'
    s = Store(path)
    w = {'workflow_id':'w','tenant_id':'tenant','use_case':'Renewal reminder',
        'options':{'voice':['V1','V2'],'welcome_message':['W1'],'caller_id':['D1']},
        'objective':{'primary':'engagement_rate','guardrail':{'pickup_rate_max_drop':.02}}}
    config = {'prompt_version':'P1','allocations':{'default':{'voice':{'V1':.8,'V2':.2}}}}
    def lead(i,name,campaign):
        return dict(event_id=i,type='lead',ts='2027-01-04T08:00:00+05:30',workflow_id='w',lead_id=name,person_id=name,campaign_id=campaign,features={'lang':'hi'})
    def call(i,name,ts,connected,engaged,cohort='default'):
        return dict(event_id=i,type='call',ts=ts,workflow_id='w',lead_id=name,person_id=name,config_version=1,cohort_id=cohort,
            variant=dict(prompt_version='P1',voice='V1',welcome_message='W1',caller_id='D1'),connected=connected,engaged=engaged,
            qa={'hallucination_flag':True} if connected else None)
    history = [dict(event_id=1,type='campaign_created',workflow_id='w',campaign_id='old',leads=1,ts='2027-01-03T08:00:00+05:30'),
        lead(2,'old-lead','old'),call(3,'old-lead','2027-01-03T09:00:00+05:30',True,False)]
    live = [dict(event_id=4,type='campaign_created',workflow_id='w',campaign_id='new',leads=2,ts='2027-01-04T08:00:00+05:30'),
        lead(5,'new-lead','new'),lead(6,'pending-lead','new'),
        call(7,'old-lead','2027-01-04T09:00:00+05:30',True,True),
        call(8,'new-lead','2027-01-04T09:00:00+05:30',True,True,'custom'),
        call(9,'pending-lead','2027-01-04T10:00:00+05:30',False,False)]
    s.ingest({'chunk':0,'kind':'history'},map(json.dumps,history))
    s.ingest({'chunk':1,'kind':'events'},map(json.dumps,live))
    with s.db:
        s.set('workflows',[w])
        s.set('config:w',{'version':1,'config':config})
        s.set('state',{'scenario':'example','sim_minute':1440,'ts':'2027-01-05T00:00:00+05:30','finished':True,'last_event_id':9,'credits_remaining':100})
        s.db.execute('INSERT INTO experiments VALUES (?,?,?,?,?)',('w','voice','2027-01-04T08','exploring','{"V1":1}'))
    return s,path


def test_campaign_outcomes_exclude_historical_enrollments(tmp_path):
    s,path = prepare(tmp_path)
    d = Dashboard(path).snapshot()
    k = d['summary']
    assert d['period']['start']=='2027-01-04T00:00:00+05:30'
    assert k['engaged']==2  # Includes a follow-up to a historical campaign.
    assert k['concluded']==1  # Outcome population includes only newly uploaded campaigns.
    assert k['uploaded']==k['enrolled']==2
    assert k['conclusion_rate']==.5
    assert k['dials']==3  # Neither diagnostics nor custom cohorts are double-counted.
    assert k['connected']==2 and k['flags']==2
    assert k['pickup_rate']==pytest.approx(2/3)
    assert d['workflows'][0]['history']['dials']==1
    assert d['workflows'][0]['daily'][0]['dials']==3
    assert d['ingestion']['event_lag']==0
    s.db.close()


def test_finished_experiment_never_implies_unrun_arm_evidence(tmp_path):
    s,path = prepare(tmp_path)
    e = Dashboard(path).snapshot()['experiments'][0]
    assert e['status']=='ended_inconclusive'
    assert 'No promotion' in e['explanation']
    arm = next(a for a in e['arms'] if a['option']=='V2')
    assert arm['connected']==arm['dials']==0
    assert arm['engagement_rate'] is None
    assert arm['interval']==[0,1]
    assert not arm['sample_ready']
    s.db.close()


def test_cache_refreshes_after_new_decision_without_sim_time_change(tmp_path):
    s,path = prepare(tmp_path)
    projection = Dashboard(path)
    first = projection.snapshot()
    assert projection.snapshot() is first
    with s.db:
        s.audit('2027-01-04T11:00:00+05:30','w','insufficient_evidence',{'dimension':'voice','stats':{'V1':{'connected':100},'V2':{'connected':10}}})
    second = projection.snapshot()
    assert second is not first
    assert len(second['activity'])==1
    assert 'last evaluation lacked' in second['experiments'][0]['explanation']
    s.db.close()


def test_approval_receipts_are_not_inferred_from_local_status(tmp_path):
    s,path = prepare(tmp_path)
    body = dict(change_summary='Explore voices',diff={'voice':{'V1':.8,'V2':.2}},base_version=1,proposed_config={'prompt_version':'P1','allocations':{'default':{'voice':{'V2':1}}}},affected_leads=2,impact_score=0)
    with s.db:
        s.db.execute('INSERT INTO proposals VALUES (?,?,?,?,?,?,?)',('p','w','applied','a',json.dumps(body),'{}','2027-01-04T10:00:00+05:30'))
        for i in range(1001):
            s.audit('2027-01-05T00:00:00+05:30','w','routine',{'i':i})
        decision=dict(approval_id='a',status='approved',reasons=[])
        change=dict(proposal_id='p',approval_id='a',version=2,actor='controller_approved')
        s.db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(10,'2027-01-04T11:00:00+05:30','w','approval_decided',json.dumps(decision)))
        s.db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(11,'2027-01-04T12:00:00+05:30','w','config_changed',json.dumps(change)))
    d = Dashboard(path).snapshot()
    assert len(d['activity'])==1000 and d['activity_total']==1001
    assert d['proposals'][0]['decision']['evidence']['approval_id']=='a'
    assert d['proposals'][0]['applied_event']['evidence']['version']==2
    assert d['workflows'][0]['config']['version']==2
    assert next(a for a in d['experiments'][0]['arms'] if a['option']=='V2')['allocation']==1
    assert d['proposals'][0]['impact_score']==0  # Unknown benefit stays unknown, never an invented lift.
    s.db.close()


def test_read_only_reader_does_not_create_or_modify_database(tmp_path):
    missing=tmp_path/'missing.sqlite'
    with pytest.raises(sqlite3.OperationalError):
        Dashboard(missing).snapshot()
    assert not missing.exists()
    s,path = prepare(tmp_path)
    reader=Store(path,read_only=True)
    assert reader.view()['state']['finished']
    with pytest.raises(sqlite3.OperationalError):
        reader.audit('now','w','changed',{})
    reader.db.close()
    s.db.close()


def test_empty_snapshot_preserves_unknown_rates(tmp_path):
    path=tmp_path/'empty.sqlite'
    s=Store(path)
    d=Dashboard(path).snapshot()
    assert d['state'] is None
    assert d['summary']['conclusion_rate'] is None
    assert d['summary']['pickup_rate'] is None
    assert not d['proposals'] and not d['workflows']
    s.db.close()
