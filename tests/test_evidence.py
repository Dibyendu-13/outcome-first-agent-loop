import copy
import json

import pytest

from controller.evidence import population,replay
from controller.observability import metrics
from controller.store import Store


def test_allocation_replay_uses_exposure_weights_not_arm_lift():
    old={'allocations':{'default':{'voice':{'V1':.8,'V2':.2}}}}
    new={'allocations':{'default':{'voice':{'V1':.2,'V2':.8}}}}
    rows=[{'cohort':'default','arm_observations':{'V1':{'n':100,'successes':50},'V2':{'n':100,'successes':80}}}]
    result=replay(old,new,rows,{'default':1000},'voice')
    assert result['cohorts'][0]['before']==pytest.approx(.56)
    assert result['cohorts'][0]['after']==pytest.approx(.74)
    assert result['weighted_estimated_lift']==pytest.approx(.18)
    new['allocations']['default']['voice']={'V1':.5,'unrun':.5}
    result=replay(old,new,rows,{'default':1000},'voice')
    assert result['weighted_estimated_lift'] is None
    assert result['cohorts'][0]['after_coverage']==.5


def test_active_population_excludes_expired_campaigns_and_respects_locks(tmp_path):
    store=Store(tmp_path/'db')
    old={'cohorts':[],'allocations':{'default':{'voice':{'V1':1}}},'prompt_version':'P1'}
    new=copy.deepcopy(old);new['allocations']['default']['voice']={'V2':1}
    with store.db:
        for i,day in enumerate((1,4)):
            event={'campaign_id':'c'+str(i),'ts':f'2027-01-0{day}T08:00:00+05:30'}
            store.db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(i,event['ts'],'w','campaign_created',json.dumps(event)))
            store.db.execute('INSERT INTO leads VALUES (?,?,?,?,?,0)',('l'+str(i),'w','p'+str(i),event['campaign_id'],'{"lang":"hi"}'))
    w={'workflow_id':'w','cadence':[2,3,3],'mid_flight':'next_campaign_only','daily_batch':{'size':10}}
    counts,detail=population(store,w,old,new,'2027-01-04T11:00:00+05:30',['voice'])
    assert sum(counts.values())==1
    assert detail['existing_campaigns_affected']==0 and detail['next_campaign_forecast']==10
    store.db.close()


def test_metrics_export_counts_measured_cycles_and_unknown_paid_state(tmp_path):
    path=tmp_path/'db';store=Store(path)
    with store.db:
        store.set('state',{'last_event_id':10,'credits_remaining':197})
        store.set('event_id',8)
        store.audit('time','w','decision_latency',{'seconds':.2})
        store.db.execute('INSERT INTO charges VALUES (?,?,NULL)',('k','unknown'))
    text=metrics(path)
    assert 'outcome_loop_event_backlog 2' in text
    assert 'outcome_loop_credits_remaining 197' in text
    assert 'outcome_loop_paid_operations{status="unknown"} 1' in text
    assert 'outcome_loop_decision_cycle_seconds_count 1' in text
    store.db.close()
