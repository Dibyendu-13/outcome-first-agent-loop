# Run and operate the controller

Python 3.10+; no external API keys or new hosted services. The controller learns only from simulator HTTP.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q tests
```

Terminal 1:

```bash
.venv/bin/python -m sim serve --scenario scenarios/public_01_dev.yaml --run-dir runs/new-run
```

Terminal 2:

```bash
CONTROLLER_DB=controller-data/new-run.sqlite ./run.sh http://127.0.0.1:8700
```

Without `CONTROLLER_DB`, `run.sh` prints its selected database, resumes a matching world, and preserves the
old database when a public time/event regression indicates a new world. Use an explicit DB for reproducible
runs. Restart with that same DB and the same simulator process. The API has no unique world ID; an
indistinguishable replacement with non-regressing counters cannot be recognized automatically.

## Supervisor view and audit

```bash
.venv/bin/python -m controller serve --db controller-data/final_public_02.sqlite --port 8800
.venv/bin/python -m controller status --db controller-data/final_public_02.sqlite
.venv/bin/python scripts/audit_change.py --db controller-data/final_public_02.sqlite --workflow ks_cancel
```

Open http://127.0.0.1:8800. See [UI.md](UI.md) for metric definitions. `/api/dashboard` is the presentation
projection, `/api/status` is legacy raw state, and `/metrics` provides Prometheus exposition. The server is
read-only on loopback. No configuration-write route exists in the UI.

Individual call receipts can be inspected without simulator logs:

```sql
SELECT c.ts,c.lead,c.person,c.version,c.cohort,c.prompt,c.voice,c.welcome,c.caller,
       l.features,c.connected,c.engaged,c.hallucination
FROM calls c JOIN leads l ON l.id=c.lead WHERE c.lead='THE_LEAD_ID' ORDER BY c.id;
```

Join the recorded version and change event to `proposals` and `audit` for rationale, approval ID, and later
measurements. A campaign-locked agent version can coexist with an immediately changed prompt; the call
receipt stores the actual prompt and arm, not a guessed configuration.

## Reproduce evidence

Use fresh run names; the harness does not overwrite evidence:

```bash
.venv/bin/python scripts/evaluate.py --name my01 --scenario scenarios/public_01_dev.yaml --port 8701
.venv/bin/python scripts/evaluate.py --name my02 --scenario scenarios/public_02_incidents.yaml --port 8702 --crash
.venv/bin/python scripts/prove_learning_cycle.py --name my-learning-proof
.venv/bin/python scripts/calibrate.py
.venv/bin/python scripts/fault_matrix.py
./scripts/validate_linux.sh my-linux-run "$PWD/runs/public_03_load/baseline"
```

The fault matrix uses the stored release_01/02 baselines and fresh `fault_*` names in a fresh checkout/state
workspace. Individual replays can use `scripts/evaluate.py --name fresh-name --fault-point ...` and an
existing official baseline with `--reuse-baseline`. Baselines are read by the **evaluation harness**, not the
controller. The Linux script uses native Docker volumes, four CPU quota, 8 GiB memory cap and no additional
swap allowance. It preserves existing other containers and does not edit Docker Desktop settings. See
[VALIDATION.md](VALIDATION.md) and `reports/FINAL.md`.

## Decision and recovery policy

- Ordered shared cohorts preserve client rules; otherwise use sufficiently populated language groups.
- One dimension per workflow trial. Use actual cohort/version/prompt receipts, one observation per person per
  KPI, fixed sample milestones, exact primary tests and a separate exact guardrail. No forced winners.
- 80% promoted allocation retains sentinel traffic. Disjoint three-hour windows test decay and guardrail
  breach. Rollback changes only affected cohorts and remains governed. Configuration edits suspend old trials.
- Caller health uses recent vs earlier and contemporaneous populations. QA incidents use fixed exact flag
  tests, durable open state, validated prompt candidates, human approval and post-apply verification.
- Mark pending proposals stale as soon as base changes. Expiry/rejection/lapse closes the snapshot. Poll at
  quarter-hour steps around dialling or pending work. Keep a critical request slot within actual policy caps.
- SQLite WAL/FULL transactions commit chunk evidence and cursor together. Reconcile remote approval/config
  history before repeating an uncertain mutation. Paid unknowns are persisted before the call; the API cannot
  retrieve the lost result. Do not retry that charge automatically.
- A repeated infrastructure failure stops the controller after bounded backoff. Restart against the same world
  and DB. On storage errors preserve DB and WAL; use a SQLite backup rather than copying a live DB alone.

## Operator actions

| Condition | Action |
|---|---|
| Repeated HTTP failure | Check simulator reachability/error; restart with the same DB |
| Open QA incident | Review sample evidence, candidate validation, and approver hours |
| Unknown paid operation | Inspect provider receipt; do not repeat blindly; request idempotency/retrieval support |
| Unsafe rollback | Escalate the blocked candidate and validation evidence for review |
| Approval expired/lapsed/stale | Check time/base; wait for fresh evidence rather than applying old body |
| Disk/integrity failure | Stop writes, preserve DB/WAL, restore storage and reconcile |
| Insufficient sample | No page; continue collecting or defer |

`requirements.lock` records the original Python 3.13 environment. The Linux image uses Python 3.12 and
resolves the compatible provided requirements. No pager or public hosting is bundled. Old Mac load raw
files are recoverable from `runs/mac-load-evidence.zip`; the official baseline remains in place.
