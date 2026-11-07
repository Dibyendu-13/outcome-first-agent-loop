# Outcome-First Agent Loop — architecture review

## 1. Executive assessment

Keep one Python controller and one SQLite writer for evaluation. The public evidence supports the design at the assignment envelope. The main redesign is to make decisions and external effects independently recoverable. Prioritize durable incident and rollback intent, then repair experiment exposure and monitoring before adding services. The first safety changes are now implemented. Incident evidence and detection commit atomically, open prompt incidents hold ordinary approvals, deferred rollback evidence survives later evaluations, and promotions reserve the full 20% sentinel allocation for the designated control. The evaluation controller also forecasts monitor duration, scopes caller-ID rotation to affected cohorts, and persists tenant incident credit holds. The review below records baseline findings and the remaining production design. See the [implementation and verification status](TEST_STRATEGY.md).

## 2. Current inventory

| Surface | Components and responsibilities |
|---|---|
| Runtime | `run.sh` invokes `controller.__main__.main`; `lifecycle.state_path` selects a DB, and a file lock protects a single DB writer. `Engine.cycle` drives HTTP reads, decisions, reconciliation and simulated time. |
| Data | `Store` owns SQLite WAL, meta, chunks, leads, calls, events, metrics, audit, proposals, experiments and charges. Cohort rules are in `cohorts.py`. `evidence.py` estimates population and replay effects. |
| Decisions | `learning.py` and `statistics.py` implement governed trials and exact tests. `engine.py` owns caller health, prompt incidents, paid calls, approval and rollback. |
| Operator | CLI status and why, read-only `dashboard.py`, `observability.py` and static browser assets. No production identity service. |
| Fixtures | `sim/` contains CLI, scenario loader, world, FastAPI server and grader. Public 01 covers ordinary learning, 02 adds incidents and supervisor edits, 03 stresses five days at load. Harnesses alone access scenario and grader files. |
| Build and test | `requirements.txt` and lock file, Makefile, Dockerfile and Linux harness. httpx is the controller HTTP dependency. NumPy and PyYAML support simulator generation, FastAPI and Uvicorn serve it, pytest runs seven test modules. Scripts evaluate, inject faults, audit, calibrate, prove lifecycle and package evidence. |

Sources: [assignment](../README.md), [HTTP contract](SIMULATOR.md), [template](../SUBMISSION_TEMPLATE.md), [six stakeholder memos](../stakeholders/), [existing results](../reports/FINAL.md).

## 3. Requirements and gaps

Functional requirements are continuous ingest, history bootstrap, per-workflow objectives, controlled experimentation, drift detection, compliant actions and operator explanations. Keep business cadence and capacity untouched. The simulator is the controller's only world input. Nonfunctional requirements are bounded memory, durable single ownership, safe restarts, tenant isolation, reproducible decisions, auditable receipts and 4-vCPU/8-GB Linux execution. Proposed production targets are p95 source-to-eligible-evaluation under five minutes in normal operation, 99.9% monthly ingest availability, zero loss of committed decisions on process failure, and 15-minute owner recovery. Provider approval and evidence accumulation have separate clocks. Regional recovery targets require backups and drills.

| Capability | Assessment | Evidence or gap |
|---|---|---|
| C1 ingest | Verified for contract | Load and kill/restart. Strictly ordered IDs are required. |
| C2 shared cohorts | Partial | Learning and UI share IDs, but caller and prompt detection pool cohorts. |
| C3 history | Verified | Bootstrap commits before decisions and is included in load timing. |
| C4 call-time | Missing by design | Observational hour effects are confounded. |
| C5 caller ID | Potentially incorrect | Aggregate rotation can select an ineligible or differently composed alternative. |
| C6 experimentation | Partial | Versioned first-person samples and fixed looks exist. Fixed start time, traffic breadth, and practical effect threshold need work. |
| C7 promotion/decay | Potentially incorrect | Fixture demonstrates rollback. Sentinel dilution and lost deferred rollback remain. |
| C8 prompt incidents | Potentially incorrect | Public fix verified, but detection persistence and pending approval priority have gaps. |
| C9 governance | Partial | Durable proposals and remote stale checks. Deadline scheduling and unknown response classification need work. |
| C10 impact | Partial | Replay withholds unsupported estimates. No sampling uncertainty or standardized DID comparison. |
| C11 reporting | Verified locally | Dashboard and audit projections. Production access controls deferred. |
| C12 audit | Partial | Real audit reconstruction demonstrated. Some skipped actions and paid intents lack complete causal receipts. |
| C13 recovery | Verified at tested boundaries | Five kill cases. Incident look-to-intent crash remains untested. |
| C14 observability | Partial | Latency, backlog, credits and alerts exist. Need SLOs, throttled alerts and actionable dimensions. |
| C15 fairness | Partial | Rotation and reserves, no durable tenant allocation. |

Mandatory floor is supported by historical public 01/02, audit receipts and the completed submission. Hidden performance and invariants outside tested scenarios require verification.

## 4–10. Proposed system

Read in order: [architecture and diagrams](ARCHITECTURE.md), [module contracts](COMPONENT_DESIGN.md), [persistence](DATA_MODEL.md), [experimentation](DECISION_ENGINE.md), [governance and incidents](GOVERNANCE.md), [recovery](FAILURE_RECOVERY.md), [capacity](SCALABILITY.md).

## 11. Existing problems and fixes

| Severity and code | Failure mechanism | Change, benefit and complexity |
|---|---|---|
| High — `Engine.incident` | Saves tested prefix before incident in another transaction. A kill can permanently consume the only significant look. | One transaction for detection, durable incident and audit. Prevents lost intervention. Small. |
| High — `Engine.decide`, `reconcile` | Pending ordinary proposal blocks safety detection, and approved ordinary work can apply before new evidence is evaluated. | Ingest and run read-only safety detection before dispatch, hold ordinary apply, preserve remote pending record. Reduces time-to-fix. Medium. |
| High — `Learner.step` | Clears pending rollback at a fresh monitor window. Noncritical approval delay or an intervening closed window can erase an observed breach. | Persist a rollback recommendation keyed by epoch and affected cohorts. Recheck live version and current recovery evidence before submit. Medium. |
| High — `Engine.verify` | Writes daily verification marker before validating/submitting rollback. A failed credit or approval gate prevents reconsideration until next day. | Persist decision separate from dispatch. Restore only changed dimensions with current base and fresh validation when needed. Medium. |
| High — `Learner.step` | Promoted 20% residual split across all losers; actual control may receive ~2.2% with ten options. Three-hour reset may never reach 200 control observations. | Reserve sentinel for known control, forecast required traffic, use longer preregistered windows. Medium. |
| Medium — `Engine.caller_health` | Pools versions, cohorts and times and uses any healthy alternative; changed default may leave affected explicit cohort allocations untouched. | Compare contemporaneous strata and current legal options, cap changes and monitor engagement. Medium. |
| Medium — `Store.ingest` | High-watermark skips earlier IDs after a gap under a changed feed. Network reads occur while writer holds a chunk transaction. | Validate feed order and manifest, spool bounded chunks where necessary, halt on mismatch. Preserve strict-contract fast path. Medium. |
| Medium — `Engine.cycle`, `reconcile` | Two full histories per workflow per cycle. Empty workflow list causes modulo/min failure. | Handle empty world, use event-driven invalidation and targeted lookups with bounded refresh. Medium. |
| Medium — `Learner.units` | Hourly repeated raw scan; person sets grow with unique exposure despite bounded per-arm arrays. | Materialize first-person observations incrementally and compare deterministic prefixes. Medium. |
| Medium — `Engine.paid` | An unsent operation and a lost reply both become unknown; repeated reserve alerts and no durable tenant allocation. | Keep conservative no-retry behavior, record intent and reserve atomically, deduplicate alerts, request upstream receipt lookup. Medium. |
| Medium — `state_path`, CLI lock | World identity heuristic cannot distinguish replacements with equal counters; separate DB paths can target same URL. | Require external world UUID or run ID in production, lock stable owner identity before state selection. Small locally, provider-dependent for strong identity. |
| Low — `statistics.winner`, `Engine` imports and legacy experiment projection | Multiple paths for reasoning about winners and experiment state obscure the source of truth. | Confirm callers and remove unused helpers only after migration. Small. |

## 12. Scope and evaluation tradeoffs

Fully implement C1/C3/C9/C12/C13 and safe C5–C8. Keep C2/C10/C11/C14/C15 focused on shared IDs, transparent estimates, local reporting and starvation resistance. Defer C4, factorial interactions and cross-tenant winner transfer. Hidden outcomes (25%) favor timely incidents and valid rollback. Reasoning (25%) favors calibrated looks and explicit assumptions. Scope (20%) favors rejecting Sales' blended KPI and broad auto-apply, distinguishing compliance validation from engagement, preserving supervisor edits and fatigue limits, keeping Product's shared cohort, using existing storage for SRE and prioritizing defendable outcomes for the CTO. Engineering (20%) favors fault tests and measured load. Communication (10%) favors a fresh-checkout runbook and one real audit example.

## 13. Implementation roadmap

| Priority | Task and files | Dependencies | Acceptance test and risk |
|---|---|---|---|
| P0 | Make incident look and durable intent atomic in `engine.py`, `store.py` | Existing audit and fault hooks | Kill before/after commit, one incident and one paid intent. Risk: duplicate effects if backfill emits a new ID. |
| P0 | Separate detection, arbitration and dispatch in `engine.py`; persist rollback across windows in `learning.py` | Atomic intent | Ordinary pending approval, supervisor edit and next-day rollback tests. Risk: held approvals lapse, expose reason. |
| P0 | Centralize CAS, 409/410 and uncertain-send handling, world lock in `__main__.py` and `lifecycle.py` | Contract fixtures | Concurrent owner and delayed reply tests. Risk: provider has no durable world identity. |
| P1 | Predeclare traffic, controls and monitoring duration in `learning.py`; stratify health in `engine.py` | Safe dispatch | Synthetic low-rate cohorts, unequal allocation, drift, power and guardrail tests. Risk: lower exposure slows learning. |
| P1 | Add incident reservations, severity and fair queue in `store.py`, `engine.py` | Durable intents | Multiple tenants with insufficient credits, deterministic allocation. Risk: reservation can strand unused credits without expiry. |
| P2 | Materialize first observations, narrow reconciliation, add freshness and alert metrics | Stable epoch and effect model | Replay equivalence, reader contention, load regression on capped Linux. Risk: index/write costs. |
| P3 | PostgreSQL partitioned writers, authenticated reporting and optional scheduling experiments | Production API guarantees and measured need | Shadow compare, failover, tenant isolation and rollback drills. Risk: distributed ownership and migration drift. |

## 14–15. Verification and decisions

[Executable test strategy](TEST_STRATEGY.md) and [architecture decision records](ARCHITECTURE_DECISIONS.md).

## 16. Interview walkthrough

Start with the client outcome and separate KPIs. Trace one chunk into an atomic SQLite commit, then one Kestrel approval from a fixed population look to its validation receipt and later call observations. Explain what is recovered if a response is lost and why paid operations are different. Show the observed Linux timing and the projected 10× load separately. Close with what you would fix first, why personalized scheduling was deferred, and the provider guarantees you need before running multiple workers.
