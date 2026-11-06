"""Generate the load summary from completed evaluation evidence, never estimates."""
import json
from pathlib import Path
import runpy
import sqlite3

root = Path(__file__).resolve().parents[1]
runpy.run_path(str(root/'scripts/normalize_metrics.py'))
path = root/'reports/public_03_load-metrics.json'
m = json.loads(path.read_text())
assert m['finished'] and m['integrity']=='ok'
c = sqlite3.connect(root/'controller-data/public_03_load.sqlite')
kinds = c.execute('SELECT kind,sum(events),sum(seconds) FROM chunks GROUP BY kind').fetchall()
state = json.loads(c.execute('SELECT value FROM meta WHERE key="state"').fetchone()[0])
call_count = c.execute('SELECT count(*) FROM calls').fetchone()[0]
lead_count = c.execute('SELECT count(*) FROM leads').fetchone()[0]
c.close()
m['controller_end_to_end_events_per_second'] = m['events']/m['controller_wall_seconds']
m['ingest_measurement_scope'] = 'JSON decoding and transaction work before final commit; excludes HTTP transfer and final commit latency'
path.write_text(json.dumps(m,indent=2)+'\n')
rows = [
 ('Events ingested, including history',f"{m['events']:,}"),
 ('Ingestion work throughput',f"{m['ingest_events_per_second']:,.0f} events/s"),
 ('End-to-end controller throughput, including simulator waits',f"{m['controller_end_to_end_events_per_second']:,.0f} events/s"),
 ('Controller wall time, including startup history',f"{m['controller_wall_seconds']:,.1f} s"),
 ('Wall time per simulated day, startup amortized',f"{m['wall_seconds_per_simulated_day']:,.1f} s"),
 ('Peak controller RSS',f"{m['peak_controller_rss_bytes']/1024**2:,.1f} MiB"),
 ('Controller database size',f"{m['database_bytes']/1024**3:,.2f} GiB"),
 ('Health / experiment evaluation intervals','60 / 1,440 simulated minutes'),
 ('Duplicate call IDs / pending proposals',f"{m['duplicate_calls']} / {m['pending_at_end']}"),
 ('SQLite integrity',m['integrity'])]
table = '| Measurement | Result |\n|---|---|\n'+'\n'.join('| '+k+' | '+v+' |' for k,v in rows)
text = '''# Full-scale evaluation

'''+table+f'''

The run completed {state['end_minute']/1440:g} simulated days. The database retains {call_count:,} call receipts
and {lead_count:,} lead enrollments, including historical data. No rows are sampled away.

## What the numbers mean

Ingestion throughput measures JSON decoding, feature joins, call/lead writes and aggregate updates inside
chunk transactions **before their final commit**. HTTP transfer and final commit latency are excluded from
that numerator/denominator. The end-to-end figure divides all ingested events by total controller wall time,
including historical bootstrap, remote simulation, HTTP round trips and decisions.

The machine was {m['environment']['platform']} with {m['environment']['cpu_count']} logical CPUs and Python
{m['environment']['python'].split()[0]}. No CPU affinity or 8GB memory limit was imposed. The controller
'''+('met' if m['wall_seconds_per_simulated_day']<600 else 'did not meet')+''' the 600-seconds-per-simulated-day
threshold on this host. This is **not** certification on the assignment's 4-vCPU / 8GB Linux environment.
The baseline CLI log reports 1,420.5 seconds using time.time; controller/harness timing uses time.monotonic.
Those clocks can differ across host suspension or clock adjustment, so these durations must not be added
or their difference attributed to controller overhead. Simulator memory is not included in controller RSS.
Evaluation raw run files consume multiple GB and are intentionally ignored by git.

The loop checks health hourly after startup and evaluates experiments daily. These are scheduling intervals,
not an observed wall-clock p95 decision lag. Evidence accumulation, approval hours, latency, request quotas
and lapses can dominate actual time to action. A wall-clock lag histogram remains to be instrumented.

## History versus live ingestion

| Event kind | Events | Measured ingestion work | Throughput |
|---|---:|---:|---:|
'''+''.join(f'| {kind} | {events:,} | {seconds:,.1f} s | {events/seconds:,.0f}/s |\n' for kind,events,seconds in kinds)+'''
## At 10×

A single SQLite writer and random lead/call index access become bottlenecks, followed by retained-call disk
volume. The feature cache is bounded to 100,000 leads but misses require indexed lookups. Move state to the
existing Postgres, bulk ingest and partition by workflow/date, assign one decision owner per workflow, and
archive immutable call receipts with audited retention. Decouple ingestion from learning and use a tenant
scheduler with explicit credit/approval reservations. The simulator's own advance cost is an evaluation
constraint and must not be mistaken for the production dialler's latency.

No linear 10× throughput claim is made. See the full grade report for outcome quality independently of speed.
'''
(root/'reports/LOAD.md').write_text(text)
p = root/'SUBMISSION.md'
s = p.read_text()
marker = 'Measured public_03 results are recorded'
if table not in s:
    s = s.replace(marker,table+'\n\n'+marker)
p.write_text(s)
print(text)
