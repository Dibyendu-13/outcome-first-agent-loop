"""Auditable active-population estimates and observed-arm allocation replay."""
import json
from datetime import datetime

from .cohorts import registry


def population(store,w,old,new,ts,dims):
    active=[]
    cadence=w.get('cadence',[])
    for payload, in store.db.execute('SELECT payload FROM events WHERE workflow=? AND type="campaign_created"',(w['workflow_id'],)):
        event=json.loads(payload)
        age=(datetime.fromisoformat(ts).date()-datetime.fromisoformat(event['ts']).date()).days
        if 0<=age<len(cadence):active.append(event['campaign_id'])
    counts={c.id:0 for c in registry(new)}
    if not active:return counts,{'active_enrollments':0,'method':'unconcluded enrollments within campaign cadence; exhausted attempts may still be included'}
    groups=registry(new);before_groups=registry(old);affected=0
    marks=','.join('?' for _ in active)
    rows=store.db.execute(f'SELECT features FROM leads WHERE workflow=? AND concluded=0 AND campaign IN ({marks})',[w['workflow_id']]+active)
    for payload, in rows:
        features=json.loads(payload)
        cohort=next(c.id for c in groups if c.matches(features))
        previous=next(c.id for c in before_groups if c.matches(features))
        changed='prompt_version' in dims or 'schedule' in dims
        for d in ('voice','welcome_message','caller_id'):
            if d in dims:
                a=new['allocations'].get(cohort,{}).get(d,new['allocations']['default'].get(d))
                b=old['allocations'].get(previous,{}).get(d,old['allocations']['default'].get(d))
                changed |= a!=b
        if changed:counts[cohort]+=1;affected+=1
    details={'active_enrollments':affected,'method':'unconcluded enrollments within campaign cadence; exhausted attempts may still be included'}
    if w.get('mid_flight')=='next_campaign_only' and not any(d in dims for d in ('prompt_version','schedule')):
        details.update(existing_campaigns_affected=0,next_campaign_forecast=w.get('daily_batch',{}).get('size',0),forecast_is_not_observed=True)
    return counts,details


def replay(old,new,comparisons,populations,dimension):
    results=[]
    for row in comparisons:
        cohort=row['cohort'];observed=row.get('arm_observations',{})
        before=old['allocations'].get(cohort,{}).get(dimension,old['allocations']['default'].get(dimension,{}))
        after=new['allocations'].get(cohort,{}).get(dimension,new['allocations']['default'].get(dimension,{}))
        rates={arm:v['successes']/v['n'] for arm,v in observed.items() if v['n']}
        def estimate(weights):
            covered=sum(weight for arm,weight in weights.items() if arm in rates)
            return (sum(weight*rates[arm] for arm,weight in weights.items()) if covered>=1-1e-9 else None),covered
        b,bcoverage=estimate(before);a,acoverage=estimate(after)
        results.append({'cohort':cohort,'before':b,'after':a,'before_coverage':bcoverage,'after_coverage':acoverage,
            'active_population':populations.get(cohort,0),'estimated_lift':a-b if a is not None and b is not None else None})
    supported=[r for r in results if r['estimated_lift'] is not None]
    weight=sum(r['active_population'] for r in supported)
    lift=sum(r['active_population']*r['estimated_lift'] for r in supported)/weight if weight else None
    return {'method':'reweight observed randomized-arm means within shared cohorts; assumes epoch stationarity and unchanged population',
        'cohorts':results,'weighted_estimated_lift':lift,'unsupported_arms_withhold_estimate':True}
