# Verification strategy

See the [evaluation redesign verification](../reports/EVALUATION_REDESIGN.md) for the latest results. Earlier baseline results remain in FINAL.md and LINUX.md. The architecture roadmap distinguishes evaluation behavior from the deferred production migration.

From the project root after installing requirements:

```bash
.venv/bin/python -m pytest -q tests
.venv/bin/python scripts/evaluate.py --name review-01 --scenario scenarios/public_01_dev.yaml --port 8710
.venv/bin/python scripts/evaluate.py --name review-02 --scenario scenarios/public_02_incidents.yaml --port 8711 --crash
.venv/bin/python scripts/evaluate.py --name review-fault-apply --scenario scenarios/public_01_dev.yaml --port 8712 --fault-point apply_after_send
.venv/bin/python scripts/prove_learning_cycle.py --name review-learning
.venv/bin/python scripts/calibrate.py
.venv/bin/python scripts/audit_change.py --db controller-data/review-02.sqlite --workflow ks_cancel
.venv/bin/python -m sim baseline --scenario scenarios/public_03_load.yaml --run-dir runs/review-load-baseline
./scripts/validate_linux.sh review-load "$PWD/runs/review-load-baseline"
```

Use fresh run names. Calibration regenerates its report. Evaluation invokes the normal run.sh entry point. For manual entrypoint verification start the simulator in one terminal, then run the controller in another:

```bash
.venv/bin/python -m sim serve --scenario scenarios/public_01_dev.yaml --run-dir runs/review-entry --port 8700
./run.sh http://127.0.0.1:8700
```

Acceptance requires completed worlds and clean integrity, policy-compatible changes with approval receipts, one application per intent, no duplicate call facts or stranded proposals, traceable audit evidence and under 600 seconds per simulated day at four CPU quota and 8 GiB cap. Capture wall runtime, decision cycle percentiles, simulated call freshness, backlog, controller RSS and cgroup peak separately. Track active and bootstrap workloads separately. Compare reruns against baseline and review harmful grades, approval outcomes and pending state.

Extend unit tests with order and duplicate replay, eligibility and fallback behavior, epoch invalidation and alpha spending. Add seeded synthetic null, power and nonstationarity studies with per-KPI denominators. Add contract fixtures for accepted-then-503, stale CAS, deadline expiry, forbidden auto-apply and credit exhaustion. Use the failure matrix to place kill hooks before and after each commit and send. Assert local application count and remote history agree, and reconstruct an audit chain from exposure back to configuration and policy. Use varied synthetic policies and traffic rather than public scenario truth. Run fresh-checkout and read-only dashboard checks before hand-in.

[Public grades and test evidence](../reports/FINAL.md) · [Linux report](../reports/LINUX.md) · [Failure matrix](FAILURE_RECOVERY.md)
