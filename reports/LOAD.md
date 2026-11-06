# Full-scale evaluation

| Measurement | Result |
|---|---|
| Events ingested, including history | 9,737,615 |
| Ingestion work throughput | 9,938 events/s |
| End-to-end controller throughput, including simulator waits | 7,409 events/s |
| Controller wall time, including startup history | 1,314.2 s |
| Wall time per simulated day, startup amortized | 262.8 s |
| Peak controller RSS | 112.6 MiB |
| Controller database size | 1.59 GiB |
| Health / experiment evaluation intervals | 60 / 1,440 simulated minutes |
| Duplicate call IDs / pending proposals | 0 / 0 |
| SQLite integrity | ok |

The run completed 5 simulated days. The database retains 7,433,447 call receipts
and 2,304,000 lead enrollments, including historical data. No rows are sampled away.

## What the numbers mean

Ingestion throughput measures JSON decoding, feature joins, call/lead writes and aggregate updates inside
chunk transactions **before their final commit**. HTTP transfer and final commit latency are excluded from
that numerator/denominator. The end-to-end figure divides all ingested events by total controller wall time,
including historical bootstrap, remote simulation, HTTP round trips and decisions.

The machine was darwin with 8 logical CPUs and Python
3.13.2. No CPU affinity or 8GB memory limit was imposed. The controller
met the 600-seconds-per-simulated-day
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
| events | 4,200,084 | 577.6 s | 7,271/s |
| history | 5,537,531 | 402.2 s | 13,769/s |

## At 10×

A single SQLite writer and random lead/call index access become bottlenecks, followed by retained-call disk
volume. The feature cache is bounded to 100,000 leads but misses require indexed lookups. Move state to the
existing Postgres, bulk ingest and partition by workflow/date, assign one decision owner per workflow, and
archive immutable call receipts with audited retention. Decouple ingestion from learning and use a tenant
scheduler with explicit credit/approval reservations. The simulator's own advance cost is an evaluation
constraint and must not be mistaken for the production dialler's latency.

No linear 10× throughput claim is made. See the full grade report for outcome quality independently of speed.
