# Validation and review checklist

This submission completes the selected scope; it does not promise a grading score or implement the
explicitly cut personalized scheduling, factorial interactions or production hosting.

| Requirement | Evidence |
|---|---|
| Official public_01 and public_02 through run.sh | `reports/public_01.md`, `reports/public_02.md`, companion metrics/logs |
| Statistical inference and stopping | `controller/statistics.py`, `controller/learning.py`, `reports/statistical-calibration.json` |
| Shared cohorts and subgroup guardrails | `controller/cohorts.py`, independent-person and guardrail regression tests, supervisor experiment view |
| Promotion → decay → approved rollback | `reports/learning-cycle-proof.json`, real-HTTP contract fixture |
| Approval expiry/lapse/stale and lost response | `tests/test_governance.py`, actual public/fixture approval records |
| Linux load and measured decision latency | `reports/LINUX.md`, `reports/linux_submission_load-metrics.json`, cgroup/source evidence |
| Real crashes at durable boundaries | `reports/fault-matrix.json` plus individual recovery/metrics artifacts |
| User-facing evidence | localhost console, `reports/audit-example.json`, `docs/UI.md` |

The contract fixture deliberately supplies strong synthetic joint-KPI effects to isolate learning logic; it
is not an official simulator score. The final public scenarios often abstain because their guardrail cannot
be proven at the available sample size. That is correct behavior, not a fabricated promotion.

## Local reproduction

Run these from the repository root after installing the dependencies:

```bash
.venv/bin/python -m pytest -q tests
.venv/bin/python scripts/evaluate.py --name review-01 --scenario scenarios/public_01_dev.yaml --port 8710
.venv/bin/python scripts/evaluate.py --name review-02 --scenario scenarios/public_02_incidents.yaml --port 8711
.venv/bin/python scripts/prove_learning_cycle.py --name review-learning
```

Choose new names on each repeat. The public evaluator generates a matching baseline unless you pass
`--reuse-baseline`. To build the baseline required by the Linux harness from a fresh checkout:

```bash
.venv/bin/python -m sim baseline --scenario scenarios/public_03_load.yaml --run-dir runs/review-load-baseline
./scripts/validate_linux.sh review-load "$PWD/runs/review-load-baseline"
```

## Linux reproduction

`./scripts/validate_linux.sh fresh-name /absolute/path/to/official/baseline` builds the provided image, runs
unit tests and evaluates public_03 in a 4-CPU / 8-GiB container. SQLite and simulator output live in
`outcome-loop-state-native` and `outcome-loop-runs-native` Docker volumes. The baseline is mounted read-only
for the grading harness. The controller only sees the local simulator URL. Keep enough disk space for raw
events, SQLite and the baseline. Do not remove these volumes if you want to retain raw evidence.

The host Docker VM reports less than 8 GiB physical memory. The requested cgroup maximum is enforced,
but the host is a stricter physical-memory environment and is shared with unrelated services. No such
service was stopped or reconfigured. `reports/linux-environment.json` records actual Linux limits and
controller algorithm source hashes. Earlier shared-storage and startup-timeout attempts are documented
rather than reported as passes. Generated raw artifacts were archived with CRC verification before
reclaiming space; the completed current Linux run is retained in the native volumes.

To inspect the Linux database after the run:

```bash
docker run --rm -v outcome-loop-state-native:/app/controller-data:ro outcome-loop:validation \
  python -m controller why --db controller-data/linux_submission_load.sqlite --workflow kest_cancel_2
```

## Review rehearsal

1. Explain the business denominator: campaign enrollment versus all conclusions occurring during the run.
2. Follow the Kestrel prompt change from flag sample to validation receipt, approval, application and later observations.
3. Show the lifecycle proof, identify the separate guardrail, and explain why the original successful period must not hide later decay.
4. Explain the 5% learner-family budget, first-person unit, model assumptions, and why an unchanged 2 pp guardrail is hard to prove.
5. Kill a test controller after a remote mutation; show why reconciliation prevents double apply.
6. Explain the one unavoidable paid-result limitation and the first system bottleneck at 10×.
7. Confirm the displayed Git identity and supply any actual human effort you want recorded. No human hours or personal review completion are inferred by the tooling.
