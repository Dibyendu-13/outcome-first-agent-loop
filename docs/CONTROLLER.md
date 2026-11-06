# Running and operating the controller

Python 3.10+ is required. No external API keys, hosted database, or calling provider is needed.
The controller imports no simulator code and reads neither scenario YAML nor simulator run directories.

## Setup and first run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q tests
```

Terminal 1:

```bash
.venv/bin/python -m sim serve --scenario scenarios/public_01_dev.yaml --run-dir runs/my-first-run
```

Terminal 2:

```bash
CONTROLLER_DB=controller-data/my-first-run.sqlite ./run.sh http://127.0.0.1:8700
```

The command runs until the scenario finishes. Restart the same command with the same database to resume
against the **same running simulator**. Use a new database and run directory for a new simulator world.
The controller rejects a detected simulator reset. The API exposes no unique run ID, so a replacement
world with the same scenario and larger time/event counters cannot be reliably distinguished.

## Supervisor view

```bash
.venv/bin/python -m controller serve --db controller-data/my-first-run.sqlite --port 8800
```

Open http://127.0.0.1:8800. The responsive console shows campaign outcomes, separate call KPIs, daily trends, experiment samples, proposal details and a decision timeline. See [UI.md](UI.md) for measurement definitions and interaction details.
The structured presentation API is `/api/dashboard`; raw backwards-compatible JSON is available at `/api/status`. This read-only local tool has no authentication and must remain bound
to loopback; production access control is outside this submission.

For terminal use:

```bash
.venv/bin/python -m controller status --db controller-data/my-first-run.sqlite
.venv/bin/python -m controller why --db controller-data/my-first-run.sqlite --workflow ks_cancel --since 2027-01-07
```

The `why` command reads only the controller's database. It includes proposal evidence, approval decision
events, applied configuration events, post-apply observations and supervisor edits. For an individual call:

```sql
SELECT c.ts,c.lead,c.person,c.version,c.cohort,c.prompt,c.voice,c.welcome,c.caller,
       l.features,c.connected,c.engaged
FROM calls c JOIN leads l ON l.id=c.lead
WHERE c.lead='THE_LEAD_ID' ORDER BY c.id;
```

Join `calls.version` to the `config_changed` records in `events`, then its proposal/approval IDs to
`proposals` and `audit`. Configuration snapshots are also retained in proposal bodies and supervisor
reassessment audit entries. The initial config is in the first experiment's previous_config, or the meta
config snapshot for a workflow that never changes. Call receipts are retained even after aggregate updates.

## Repeatable evaluation

Use fresh names; the harness refuses to overwrite existing evidence:

```bash
.venv/bin/python scripts/evaluate.py --name my01 --scenario scenarios/public_01_dev.yaml --port 8701
.venv/bin/python scripts/evaluate.py --name my02 --scenario scenarios/public_02_incidents.yaml --port 8702 --crash
.venv/bin/python scripts/evaluate.py --name myload --scenario scenarios/public_03_load.yaml --port 8703
```

The harness starts a separate simulator, runs a no-op baseline, launches the real controller over TCP,
grades the run, and writes reports, timing metrics, logs and optional recovery evidence under `reports/`.
Its access to run files is evaluation-only: the controller process is never passed those paths.
Load evaluation creates several GB of simulator event files and can take tens of minutes. Its CPU/memory
measurements describe the actual host, not a certified 4-vCPU Linux benchmark.

## State and recovery

- SQLite WAL with FULL synchronization; each event chunk, aggregates and cursor commit together.
- Global monotonic event IDs suppress overlap; the chunk table suppresses replay.
- Pending proposals are durable before HTTP mutation. Content-derived proposal IDs provide remote identity.
- Restart lists remote approvals and config history before attempting another mutation. A successful remote
  apply with a lost response is recovered by proposal ID, without applying again.
- One advisory file lock prevents two controllers using one database. Two databases must not drive one world.
- GET/5xx/transport errors trigger bounded exponential backoff in the outer reconciliation loop. Eight
  consecutive failures stop the process for an operator/process supervisor to investigate.
- A failed advance response is reconciled through `/sim/state`, never blindly replayed.
- Paid operations are marked uncertain before transmission. Their API has no idempotency or retrieval
  capability. An uncertain call is never charged again automatically; the associated incident remains
  visible and may require operator recovery. A response lost before persistence can lose that paid result.
- 4xx mutations are recorded and closed. Stale proposals are recomputed from current configuration and
  current evidence; expired/rejected proposals do not replay their old body automatically.

## Decision policy

One shared decision cohort, `default`, avoids fragmentation. Language features are joined for diagnostics
and retained for future cohort work. Existing non-default client cohorts are respected; automated variant
experiments abstain when custom cohorts exist rather than modifying their definitions.

At 11:00 daily, one dimension is explored at a time: voice, then welcome, then caller ID for engagement
workflows; caller ID for pickup workflows. New exploration mixes 70% current allocation and 30% uniform
allocation over allowed options. An unresolved experiment blocks the next dimension. There is no forced
winner when evidence remains inconclusive. Human approval is required for voice/welcome experiments.

A winner needs >=400 connected calls per observed arm and nonoverlapping 3.5-z Wilson intervals on the
relevant KPI. Seven daily looks are allowed per experiment epoch. Promotions retain 20% sentinel traffic.
A separate one-sided noninferiority check uses the workflow's absolute guardrail drop. Repeated people,
multiple epochs and historical comparisons mean these are conservative heuristics, not a proven global
false-winner guarantee. See SUBMISSION.md for limitations.

Caller health compares recent four-hour DID pickup against its earlier 72-hour history (excluding those
four hours). Require >=300 recent dials, >=600 historic dials, nonoverlapping intervals plus 5pp decline,
and a demonstrably healthier contemporaneous DID. Healthy alternatives receive the removed share.

Hallucination incidents require >=200 connected calls, >=4% flagged calls, and a four-sigma score against
max(2.5%, pre-change flag rate + 1.5pp). A persistent incident blocks unrelated experimentation even outside
approver hours. Candidates are safety-validated on 400 conversations. Among passing candidates, prefer
observed engagement evidence; validation pass rate alone never establishes an engagement winner.

Current-version post-apply observations are compared with the prior version over the previous 48 hours.
After >=400 connections on both sides, substantial separated-interval degradation proposes a rollback.
Prompt rollback also needs fresh passing validation. A failed safety rollback emits an actionable audit
alert. Temporal comparisons can be confounded and are deliberately not described as randomized evidence.

## Governance and operator actions

At most two proposals per rolling 24 hours per workflow, further bounded by API policy. Kestrel requests
start no earlier than 11:00 despite its policy permitting 10:00. Submit only within approver hours with at
least one hour left. Approvals are polled every simulated hour; a policy with a shorter apply window could
lapse, and needs a shorter tick before production. TTL/latency are enforced remotely and reconciled locally.

Only pure caller-ID changes within allowed dimensions and total-variation max_shift can auto-apply.
Customer-facing experiments and prompts always use human approval. Supervisor edits invalidate pending
base versions, reset experiment records and pause new experiments for 24 hours. A dimension explicitly
edited by the supervisor is protected from future automated experiments for this run. Prompt safety fixes
still require a fresh human approval.

Actionable conditions in the audit view:

| Condition | Action |
|---|---|
| Repeated HTTP failures | Check simulator reachability and error response; restart with same DB |
| Open hallucination incident | Review pending proposal, candidate validation, approver availability |
| Credit reserve reached | Prioritize unresolved incidents; do not blindly retry paid operations |
| Unsafe rollback | Review alternate fix; rollback candidate failed required safety evidence |
| No validated fix | Escalate to supervisor; do not apply an unsafe prompt |
| SQLite integrity/disk error | Stop writes, preserve DB/WAL, restore storage and reconcile |
| Insufficient experiment evidence | No page; continue collecting or review scope in business hours |
| Expired/rejected/stale proposal | No page by itself; inspect fresh proposal and approval queue |

No pager delivery or messages to stakeholders are wired up. Alert records and local status are the
observability interface. Operational production deployment needs metrics export and notification routing.

`requirements.lock` records the Python 3.13 evaluation environment; use `requirements.txt` for dependency resolution on other supported Python versions. Monitoring evaluations are hourly and experiment looks daily; neither interval includes evidence accumulation or governance delays.
