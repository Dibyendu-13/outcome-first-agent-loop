import copy
import json
import math
from fractions import Fraction

import pytest

from controller.cohorts import Cohort,classify,definitions
from controller.engine import Engine
from controller.learning import Learner
from controller.statistics import MILESTONES,binomial_bounds,comparison_alpha,fisher_greater,noninferiority
from controller.store import Store


def test_exact_test_matches_enumerated_hypergeometric():
    expected=sum(Fraction(math.comb(10,k)*math.comb(10,10-k),math.comb(20,10)) for k in range(8,11))
    assert fisher_greater(8,10,2,10)==pytest.approx(float(expected))
    assert fisher_greater(0,0,0,0)==1
    assert fisher_greater(10,10,0,10)<.00001


def test_exact_bounds_and_spending():
    assert binomial_bounds(0,0,.05)==(0,1)
    assert binomial_bounds(1,1,.05)[0]==pytest.approx(.025)
    assert binomial_bounds(0,1,.05)[1]==pytest.approx(.975)
    assert noninferiority(180,200,40,200,.02,.00001)[0]
    assert not noninferiority(100,200,100,200,.02,.00001)[0]
    # All purposes, all epochs, cohorts, comparisons and milestones fit 5% per workflow.
    spent=sum(comparison_alpha(j,3,3,p)*3*3*len(MILESTONES) for j in range(1,10000) for p in ('promotion','guardrail','decay'))
    assert .049<spent<.05


def test_ordered_cohorts_use_and_and_or():
    cfg={'cohorts':[{'id':'senior','where':{'age_band':['60+'],'lang':['ta','hi']}},{'id':'ta','where':{'lang':['ta']}}]}
    assert classify(cfg,{'age_band':'60+','lang':'ta'})=='senior'
    assert classify(cfg,{'age_band':'18-30','lang':'ta'})=='ta'
    assert classify(cfg,{'age_band':'18-30','lang':'en'})=='default'


def setup(tmp_path):
    s=Store(tmp_path/'test.sqlite')
    cfg={'cohorts':[],'allocations':{'default':{'voice':{'V1':.5,'V2':.5},'caller_id':{'D1':1},'welcome_message':{'W1':1}}},'prompt_version':'P1','schedule':{}}
    trial=dict(epoch=1,dimension='voice',version=2,started='2027-01-04T12:00:00+05:30',controls={'default':'V1'},options=['V1','V2'],baseline=copy.deepcopy(cfg),stage='exploring',tested={},promoted={},cohorts=[{'id':'default','where':{}}])
    cur={'version':2,'actor':'controller_approved','config':cfg}
    w={'workflow_id':'w','tenant_id':'t','options':{'voice':['V1','V2']},'objective':{'primary':'engagement_rate','guardrail':{'pickup_rate_max_drop':.02}}}
    e=Engine('http://unused',s)
    with s.db:s.set('learning:w',trial)
    return s,e,w,cur,trial


def rows(s,version,start_id,n=1200,reverse=False,repeat=False,ts='2027-01-05T10:00:00+05:30'):
    vals=[]
    for arm in ('V1','V2'):
        good=(arm=='V2')!=reverse
        import random
        order=list(range(n));random.Random(113+version+(arm=='V2')).shuffle(order)
        for i in order:
            # Both primary and guardrail improve, permitting an exact noninferiority proof.
            conn=i<int(n*(.9 if good else .3))
            engaged=conn and i<int(n*(.8 if good else .05))
            person=f'{version}:{arm}:{i if not repeat else 0}'
            vals.append((start_id+len(vals),'w',person,person,ts,version,'default','P1',arm,'W1','D1',int(conn),int(engaged),0))
    with s.db:s.db.executemany('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',vals)


def test_repeated_people_and_unapproved_versions_do_not_create_sample(tmp_path):
    s,e,w,cur,trial=setup(tmp_path)
    rows(s,1,1) # wrong campaign-locked version, never evidence for this experiment
    rows(s,2,10000,repeat=True)
    units=Learner(e).units('w',trial,cur)
    assert len(units['default']['pickup']['V1'])==1
    assert len(units['default']['engagement']['V2'])==1
    e.c.close();s.db.close()


def test_promotion_then_governed_decay_rollback(tmp_path,monkeypatch):
    s,e,w,cur,trial=setup(tmp_path)
    rows(s,2,1,n=4000)
    proposed=[]
    def propose(w,cur,cfg,ts,summary,evidence,plan):
        proposed.append((copy.deepcopy(cfg),summary,copy.deepcopy(evidence),copy.deepcopy(plan)))
        return True
    monkeypatch.setattr(e,'propose',propose)
    assert Learner(e).step(w,cur,{'ts':'2027-01-05T11:00:00+05:30'})
    cfg,summary,evidence,plan=proposed[-1]
    assert 'Promote' in summary and cfg['allocations']['default']['voice']['V2']==.8
    assert evidence['cohort_comparisons'][0]['p_value']<evidence['cohort_comparisons'][0]['alpha']
    next_trial=plan['learning'];next_trial.update(version=3,started='2027-01-05T00:00:00+05:30')
    with s.db:s.set('learning:w',next_trial)
    rows(s,3,20000,n=20000,reverse=True,ts='2027-01-06T10:00:00+05:30')
    assert Learner(e).step(w,{'version':3,'config':cfg}, {'ts':'2027-01-06T11:00:00+05:30'})
    rollback,summary,evidence,plan=proposed[-1]
    assert 'Rollback' in summary
    assert rollback['allocations']['default']['voice']==trial['baseline']['allocations']['default']['voice']
    assert plan['learning']['stage']=='rolled_back'
    e.c.close();s.db.close()


def test_guardrail_breach_rolls_back_even_when_primary_still_wins(tmp_path,monkeypatch):
    s,e,w,cur,trial=setup(tmp_path)
    trial.update(stage='promoted',promoted={'default':'V2'},version=3,started='2027-01-06T09:00:00+05:30')
    with s.db:s.set('learning:w',trial)
    # V2 still engages everyone who connects, but pickup collapses. Restore the guardrail.
    vals=[]
    for arm in ['V1','V2']:
        for i in range(10000):
            connected=i<(3000 if arm=='V1' else 500)
            engaged=connected and (i<500 if arm=='V1' else True)
            vals.append((len(vals)+1,'w',f'{arm}:{i}',f'{arm}:{i}','2027-01-06T10:00:00+05:30',3,'default','P1',arm,'W1','D1',int(connected),int(engaged),0))
    with s.db:s.db.executemany('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',vals)
    proposals=[]
    monkeypatch.setattr(e,'propose',lambda *args:proposals.append(args) or True)
    assert Learner(e).step(w,dict(cur,version=3),{'ts':'2027-01-06T11:00:00+05:30'})
    assert 'guardrail breach' in proposals[-1][4]
    assert proposals[-1][5]['cohort_comparisons'][0]['guardrail_breach']
    e.c.close();s.db.close()
