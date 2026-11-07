"""Prometheus exposition from controller-owned records; no external service required."""
from .store import Store


def metrics(path):
    store=Store(path,read_only=True)
    try:
        db=store.db;db.execute('BEGIN');state=store.get('state') or {}
        events,seconds=db.execute('SELECT coalesce(sum(events),0),coalesce(sum(seconds),0) FROM chunks').fetchone()
        values={'outcome_loop_ingested_events_total':events,'outcome_loop_ingest_work_seconds_total':seconds,
            'outcome_loop_event_backlog':max(0,state.get('last_event_id',0)-store.get('event_id',0)),
            'outcome_loop_credits_remaining':state.get('credits_remaining',0)}
        out=[]
        for name,value in values.items():
            out.extend(['# TYPE '+name+(' counter' if name.endswith('_total') else ' gauge'),f'{name} {value}'])
        out.append('# TYPE outcome_loop_proposals gauge')
        for status,count in db.execute('SELECT status,count(*) FROM proposals GROUP BY status'):
            out.append(f'outcome_loop_proposals{{status="{status}"}} {count}')
        out.append('# TYPE outcome_loop_paid_operations gauge')
        for status,count in db.execute('SELECT status,count(*) FROM charges GROUP BY status'):
            out.append(f'outcome_loop_paid_operations{{status="{status}"}} {count}')
        samples=[row[0] for row in db.execute('SELECT json_extract(payload,"$.seconds") FROM audit WHERE kind="decision_latency"')]
        out.append('# TYPE outcome_loop_decision_cycle_seconds histogram')
        for bound in (.01,.05,.1,.5,1,5,30,120):
            out.append(f'outcome_loop_decision_cycle_seconds_bucket{{le="{bound}"}} {sum(v<=bound for v in samples)}')
        out.extend([f'outcome_loop_decision_cycle_seconds_bucket{{le="+Inf"}} {len(samples)}',
            f'outcome_loop_decision_cycle_seconds_count {len(samples)}',f'outcome_loop_decision_cycle_seconds_sum {sum(samples)}'])
        return '\n'.join(out)+'\n'
    finally:
        store.db.close()
