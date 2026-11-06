#!/usr/bin/env python3
"""Explain one applied change solely from controller-owned records."""
import argparse
import json
import sqlite3

ap = argparse.ArgumentParser()
ap.add_argument('--db',required=True)
ap.add_argument('--workflow',required=True)
ap.add_argument('--dimension',default='prompt_version')
a = ap.parse_args()
c = sqlite3.connect(a.db)
for pid,status,approval,body_text in c.execute('SELECT id,status,approval,body FROM proposals WHERE workflow=? AND status="applied" ORDER BY created',(a.workflow,)):
    body = json.loads(body_text)
    if a.dimension not in body['diff']:
        continue
    change = next((json.loads(r[0]) for r in c.execute('SELECT payload FROM events WHERE workflow=? AND type="config_changed"',(a.workflow,)) if json.loads(r[0]).get('proposal_id')==pid),None)
    if change is None:
        continue
    approval_event = next((json.loads(r[0]) for r in c.execute('SELECT payload FROM events WHERE type="approval_decided"') if json.loads(r[0]).get('approval_id')==approval),None)
    totals = c.execute('SELECT count(*),sum(connected),sum(engaged),sum(hallucination) FROM calls WHERE workflow=? AND version=?',(a.workflow,change['version'])).fetchone()
    print(json.dumps({'workflow':a.workflow,'changed_at':change['ts'],'version':change['version'],
        'actor':change['actor'],'approval_id':approval,'approval_event':approval_event,
        'proposal_id':pid,'summary':body['change_summary'],'diff':body['diff'],'rationale':body['rationale'],
        'evidence':body['dry_run'],'subsequent_calls_on_version':dict(zip(('dials','connected','engaged','hallucination_flags'),totals))},indent=2))
