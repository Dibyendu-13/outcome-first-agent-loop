# Evaluation evidence

- `public_01.md`: official grade report, run `release_01`; controller DB `controller-data/release_01.sqlite`.
- `public_02.md`: official grade report, run `release_02`; controller DB `controller-data/release_02.sqlite`.
- `public_02-recovery.json`: real SIGKILL/restart while a proposal was pending in the same public_02 run.
- `public_03_load.md` and `public_03_load-metrics.json`: full load scenario and machine-specific measurements.
- `LOAD.md`: interpretation, throughput definition and production limits.
- `audit-example.json`: why a real prompt changed, approval evidence and subsequent outcomes from our store.
- `supervisor-example.json`: snapshot of the consolidated read-only supervisor API.
- `tests.txt`: simulator and controller regression test output.
- `release_01-*` and `release_02-*`: source logs/metrics for canonical public reports above.
- `development/`: earlier iterations, including harmful changes and missed incidents. These are development
  evidence, not the final result. Differences are discussed in SUBMISSION.md.

The grader reads simulator output solely for external evaluation. The controller itself consumes only HTTP.
Run directories and controller databases are ignored by git because they are large. Reproduce them with
`scripts/evaluate.py` using fresh run names; dependency versions are in `requirements.lock`.
Relative KPI deltas in official grade tables should not be interpreted as percentage-point changes.

## Redesigned supervisor UI

`ui-verification.md` records browser checks and their limits; `ui-tests.txt` contains the 20-test result.
`ui-overview.jpg` and `ui-mobile.jpg` show the actual connected UI. See `docs/UI.md` for data definitions.
