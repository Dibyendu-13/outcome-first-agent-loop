"""Real SIGKILL/restart at each durable boundary against the official HTTP simulator."""
import json
from pathlib import Path
import sqlite3
import argparse

from evaluate import run,ROOT


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--prefix", default="fault")
    args=parser.parse_args()
    rows=[]
    for i,point in enumerate(['ingest_before_commit','proposal_after_send','apply_after_send','advance_after_send','paid_after_send']):
        incident=point=='paid_after_send'
        scenario='scenarios/public_02_incidents.yaml' if incident else 'scenarios/public_01_dev.yaml'
        name=args.prefix+'_'+point
        baseline='runs/release_02/baseline' if incident else 'runs/release_01/baseline'
        run(name,scenario,8720+i,False,baseline,point)
        metrics=json.loads((ROOT/'reports'/(name+'-metrics.json')).read_text())
        recovery=json.loads((ROOT/'reports'/(name+'-recovery.json')).read_text())
        c=sqlite3.connect(ROOT/'controller-data'/(name+'.sqlite'))
        unresolved=c.execute('SELECT count(*) FROM charges WHERE status="unknown"').fetchone()[0]
        alert=c.execute('SELECT count(*) FROM audit WHERE kind="alert_unknown_paid_operation"').fetchone()[0]
        assert metrics['finished'] and metrics['duplicate_calls']==0 and metrics['integrity']=='ok'
        assert metrics['pending_at_end']==0
        if incident:assert unresolved==1 and alert>=1
        c.close()
        rows.append(dict(point=point,finished=metrics['finished'],duplicates=metrics['duplicate_calls'],integrity=metrics['integrity'],
            pending=metrics['pending_at_end'],unknown_paid=unresolved,operator_alerts=alert,recovery=recovery))
        (ROOT/f'reports/{args.prefix}-matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('All five real-process crash boundaries completed and reconciled.')


if __name__=='__main__':main()
