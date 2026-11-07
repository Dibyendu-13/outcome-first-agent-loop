# Final constrained Linux load evaluation

| Linux measurement | Result |
|---|---|
| Events ingested, including history | 9,737,615 |
| Ingestion work throughput | 12,980 events/sec |
| End-to-end throughput including simulator waits | 4,952 events/sec |
| Controller wall time | 1,966.4 seconds |
| Wall time per simulated day, startup history amortized | 393.3 seconds |
| Simulator startup before controller | 98.0 seconds |
| Peak controller RSS | 221.5 MiB |
| SQLite size | 1.99 GiB |
| Decision-cycle processing p50 / p95 | 2.647 / 7.088 seconds |
| Observed call freshness p95 at first evaluation cycle | 15 simulated minutes |
| Duplicate calls / stranded proposals | 0 / 0 |
| Integrity | ok |

The full five-day official public_03 run used the submitted controller algorithms and `run.sh`. The
resource envelope is cgroup `cpu.max=400000 100000` (four CPU quota) and `memory.max=8589934592`
(8 GiB). Host Linux VM physical memory was `MemTotal:        4013480 kB`; this is a stricter physical limit
and shared with other services. No unrelated services were stopped. Architecture: aarch64.
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
