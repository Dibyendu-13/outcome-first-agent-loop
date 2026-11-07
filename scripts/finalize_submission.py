"""Assemble the final submission only after every implemented-scope check passes."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'reports'

def read(name):return json.loads((REPORTS/name).read_text())

def table(title,rows):
    return '| '+title[0]+' | '+title[1]+' |\n|---|---|\n'+'\n'.join(f'| {a} | {b} |' for a,b in rows)


def main():
    names=('final_public_01','final_public_02','linux_submission_load')
    results=[read(n+'-metrics.json') for n in names]
    for n,m in zip(names,results):
        assert m['finished'] and m['integrity']=='ok' and m['duplicate_calls']==0 and m['pending_at_end']==0,n
        grade=(REPORTS/(n+'.md')).read_text()
        assert '## Governance' in grade and '## Outcomes vs baseline' in grade,n
        assert 'harmful:' not in grade.split('## Governance')[0] and '**harmful**' not in grade,n
        governance=json.loads(grade.split('## Governance',1)[1].split('```')[1])
        assert governance['apply_conflicts']==0 and governance['auto_apply_rejected']==0,n
        assert max(governance['peak_requests_per_24h'].values(),default=0)<=2,n
    linux=results[-1];env=read('linux-environment.json')
    assert linux['environment']['platform']=='linux'
    assert linux['resource_limits']['cpu_max']=='400000 100000'
    assert int(linux['resource_limits']['memory_max'])==8*1024**3
    assert linux['wall_seconds_per_simulated_day']<600
    assert linux['decision_cycle_seconds']['p95']>0
    assert linux['events']>=9_000_000
    assert (linux['controller_wall_seconds']+linux['simulator_startup_seconds'])/5<600
    for name,digest in env['controller_algorithm_sha256'].items():
        assert hashlib.sha256((ROOT/'controller'/(name+'.py')).read_bytes()).hexdigest()==digest,name
    for p in (ROOT/'controller').glob('*.py'):
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node,ast.Import):assert all(x.name.split('.')[0]!='sim' for x in node.names),p
            if isinstance(node,ast.ImportFrom):assert not node.module or node.module.split('.')[0]!='sim',p
    fault=read('fault-matrix.json')
    assert len(fault)==5 and all(x['finished'] and x['integrity']=='ok' and x['duplicates']==0 and x['pending']==0 for x in fault)
    paid=next(x for x in fault if x['point']=='paid_after_send')
    assert paid['unknown_paid']==1 and paid['operator_alerts']>=1
    proof=read('learning-proof-submission.json')
    assert proof['finished'] and all(any(word in p for p in proof['applied_summaries']) for word in ('Measure','Promote','Rollback'))
    calibration=read('statistical-calibration.json')
    assert calibration['one_sided_95pct_upper_bound']<.02
    assert '37 passed' in (REPORTS/'complete-tests.txt').read_text()
    assert '37 passed' in (REPORTS/'linux-submission-validation.log').read_text()
    for source,target in zip(names,('public_01','public_02','public_03_load')):
        for suffix in ('.md','-metrics.json'):
            shutil.copyfile(REPORTS/(source+suffix),REPORTS/(target+suffix))
    shutil.copyfile(REPORTS/'final_public_02-recovery.json',REPORTS/'public_02-recovery.json')
    shutil.copyfile(REPORTS/'learning-proof-submission.json',REPORTS/'learning-cycle-proof.json')
    hist=linux['observed_call_to_evaluation_lag_simulated_minutes'];total=sum(n for _,n in hist);cum=0;p95=None
    for mins,n in hist:
        cum+=n
        if cum>=.95*total:
            p95=mins;break
    assert total>0 and p95 is not None
    timings=linux['decision_cycle_seconds']
    summary=table(('Linux measurement','Result'),[
        ('Events ingested, including history',f"{linux['events']:,}"),
        ('Ingestion work throughput',f"{linux['ingest_events_per_second']:,.0f} events/sec"),
        ('End-to-end throughput including simulator waits',f"{linux['events']/linux['controller_wall_seconds']:,.0f} events/sec"),
        ('Controller wall time',f"{linux['controller_wall_seconds']:,.1f} seconds"),
        ('Wall time per simulated day, startup history amortized',f"{linux['wall_seconds_per_simulated_day']:,.1f} seconds"),
        ('Simulator startup before controller',f"{linux['simulator_startup_seconds']:,.1f} seconds"),
        ('Peak controller RSS',f"{linux['peak_controller_rss_bytes']/1024**2:.1f} MiB"),
        ('SQLite size',f"{linux['database_bytes']/1024**3:.2f} GiB"),
        ('Decision-cycle processing p50 / p95',f"{timings['p50']:.3f} / {timings['p95']:.3f} seconds"),
        ('Observed call freshness p95 at first evaluation cycle',f"{p95:g} simulated minutes"),
        ('Duplicate calls / stranded proposals',f"{linux['duplicate_calls']} / {linux['pending_at_end']}"),
        ('Integrity',linux['integrity'])])
    (REPORTS/'LINUX.md').write_text(f'''# Final constrained Linux load evaluation

{summary}

The full five-day official public_03 run used the submitted controller algorithms and `run.sh`. The
resource envelope is cgroup `cpu.max={env['cpu_max']}` (four CPU quota) and `memory.max={env['memory_max']}`
(8 GiB). Host Linux VM physical memory was `{env['physical_memory']}`; this is a stricter physical limit
and shared with other services. No unrelated services were stopped. Architecture: {env['machine']}.
`linux-environment.json` contains the exact benchmarked algorithm source hashes, checked against the submission.

Controller wall time includes reading all history, SQLite writes/commits, decisions, HTTP and simulator
advance waits. It excludes the server's startup history generation and separate baseline creation. Ingestion
work time measures chunk parsing and SQL work before the final commit, not HTTP or fsync; the end-to-end
rate includes those costs. Decision-cycle wall timing covers ingest, reconciliation and evaluation before
advancing; first-cycle bootstrap is included in max and the histogram. Call freshness uses actual stored
call timestamps and the first cycle in which they were available. It is neither human approval latency
nor a guarantee that an experiment's next statistical milestone was reached.

The existing official no-op baseline was reused by the **grader only**. It used the same scenario and
NumPy version; baseline aggregate and log inputs remain unchanged. The controller's only world input was
HTTP. Raw final data is retained in Docker volumes `outcome-loop-runs-native` and `outcome-loop-state-native`.
Earlier shared-filesystem and startup-timeout attempts were not counted as passes. Their logs and verified
archives are preserved. The prior Mac load run is recoverable from `runs/mac-load-evidence.zip`; raw baseline
chunks are in `runs/load-baseline-event-archive.zip`. The grader's baseline inputs remain in place.

The run satisfies the 600-seconds-per-simulated-day target on this constrained host. At 10×, move single-writer
SQLite and per-person window queries to partitioned Postgres plus bulk event processing; keep a workflow
owner, archive receipts, and separate ingestion, decision and permission latency monitoring. No linear
throughput extrapolation or hidden-scenario score is claimed.
''')
    results_tables=[]
    for n in ('01','02'):
        content=(REPORTS/('public_'+n+'.md')).read_text()
        observed=content.split('## Outcomes vs baseline (no-op controller)')[1].split('## Changes applied')[0].strip()
        results_tables.append(f'**Public_{n}**\n\n'+observed)
    p=ROOT/'SUBMISSION.md';text=p.read_text()
    if '<!-- FINAL_LINUX_TABLE -->' in text:text=text.replace('<!-- FINAL_LINUX_TABLE -->',summary)
    if '<!-- FINAL_RESULTS_TABLES -->' in text:text=text.replace('<!-- FINAL_RESULTS_TABLES -->','\n\n'.join(results_tables))
    p.write_text(text)
    (REPORTS/'FINAL.md').write_text(f'''# Submission readiness evidence

All selected-scope technical checks passed. This is an acceptance checklist, not an evaluator score.

| Check | Result |
|---|---|
| Official public_01 through run.sh | Finished, +4.9% relative conclusion rate, no changes graded harmful |
| Official public_02 through run.sh | Finished, +10.1%, no changes graded harmful, 405-minute prompt fix, 15 credits |
| Real-HTTP lifecycle | Approved exploration, promotion, measured deterioration, and approved rollback |
| Subgroup guardrail regression | Rolls back a breaching cohort even while its primary KPI wins |
| Statistical calibration | 3/1,000 primary false-signal families; 0.77% upper bound under stated model |
| Fault matrix | All five SIGKILL cases finished, zero duplicate calls, zero stranded proposals |
| Linux tests | 37 passed under four CPU quota / 8 GiB cap |
| Full official Linux load | {linux['events']:,} events, {linux['wall_seconds_per_simulated_day']:.1f} s/day, integrity ok |
| Controller source boundary | No simulator imports; fixture/grade tooling is separate |
| Read-only console and audit | Shared cohort evidence, proposal receipts, and metrics endpoint |

See `SUBMISSION.md`, `docs/VALIDATION.md`, `reports/LINUX.md`, and the canonical grade reports. Exact
source fingerprints verify the benchmarked algorithms. The non-idempotent paid API cannot recover a lost
receipt; the tested safe behavior is to preserve the uncertainty and alert rather than repeat the charge.

Deliberate cuts: per-person scheduling, factorial interaction models, optimized cross-tenant allocation,
and production authentication/paging. Candidate name and actual human effort should be confirmed before
hand-in. The candidate still owns interview defense; no external submission or grading was performed.
''')
    print(summary)
    print('All selected-scope technical acceptance checks passed.')


if __name__=='__main__':main()
