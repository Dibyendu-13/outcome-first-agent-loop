# Outcome-First Agent Loop — Submission

**Name:** Repository owner; implementation prepared with Codex assistance. **Date:** 2026-11-06.
**Hours actually spent:** One automated implementation/evaluation session; human effort is not claimed.
Recorded benchmark wall times are in `reports/*-metrics.json`. **Language / storage:** Python / SQLite WAL.

## 0. TL;DR

HTTP-only controller with atomic event ingestion, durable governance, bounded exploration and incident response.
Public_01: +2.7% relative conclusion-rate lift; three changes, none graded harmful.
Public_02: +9.9% relative conclusion-rate lift; seven changes, none graded harmful; 15 credits spent.
Public_02 hallucinated calls fell from 431 to 196; prompt incident MTTR remained 1,530 simulated minutes.
Scope prioritizes reliability and traceable decisions; personalized timing and feature-specific experiments are deferred.

## 1. Assumptions

1. The HTTP contract and per-workflow policies override stakeholder recollection. No controller code imports
   `sim`, reads scenarios, or reads simulator run files. Evaluation scripts may invoke the official grader.
2. One controller process drives one simulator world. A database file belongs to exactly one world. There is
   no unique run identifier in the API; time/scenario/event regression catches many, but not all, world resets.
3. Events/chunks obey the documented globally increasing event-ID ordering. Replay/overlap is possible
   during recovery and is deduplicated. Out-of-order chunks are sorted before ingestion.
4. SQLite is appropriate for one-machine evaluation. It is not the eventual shared production database.
5. Guardrail drop values represent absolute rate differences, not relative percentages.
6. Historical data provides context, not proof of current causal effects. Prompt validation measures safety,
   never engagement. Returning people can create correlation between observations.
7. A supervisor edit expresses current client intent. We pause experiments for 24 hours and protect any
   allocation dimension they explicitly changed. Approved incident remediation can still change a prompt.
8. Insufficient evidence means abstain. Neither elapsed time nor an LLM response is sufficient to promote.
9. An unconcluded historical enrollment may already have exhausted cadence. Affected-lead count is therefore
   an explicit upper bound, not a claim that every counted lead remains dialable.
10. A paid request with a lost acknowledgement cannot be made exactly-once with this API. We persist an
    uncertain intent and never repeat it blindly; an unavailable result remains a visible limitation.
11. Scenarios end when the simulator says finished. Pending approvals at that boundary can remain unresolved;
    neither advancing past the end nor applying new experiments without future observations is useful.

## 2. Scope decisions

| # | Capability | Built / Partial / Cut | Why | What it would take to finish |
|---|---|---|---|---|
| C1 | Event ingestion | Built | Transactional chunks, deduplication, history and restart | Partition ingestion for production |
| C2 | Features/shared cohorts | Partial | Durable lead joins, one shared default cohort, language diagnostics | Feature-specific cohort registry and traffic budgets |
| C3 | Historical bootstrap | Built | Every history chunk is consumed before decisions | Formal drift-weighted priors |
| C4 | Call-time optimization | Cut | Observational hour effects and sparse personal samples risk false confidence | Randomized cohort schedules and returning-person evidence |
| C5 | Caller-ID health | Built | Thresholded temporal degradation plus healthy contemporaneous alternative | Calibrated detector and safe exploration of previously unseen DIDs |
| C6 | Welcome/voice experiments | Partial | One dimension at a time, bounded exposure, sample minimum and deterministic tests | Interactions, clustering and family-wide error calibration |
| C7 | Promotion/decay/rollback | Partial | 20% sentinel traffic, recent comparisons and approved rollback code | More evidence on decay scenarios; attribution across multiple simultaneous changes |
| C8 | Prompt incidents | Built | Persistent detection, suggestions, validation, approval and post-apply verification | Faster low-volume detection and engagement-aware canary prompts when API supports them |
| C9 | Governance | Partial | Durable lifecycle, policy checks, request budgets, stale-base reconciliation | Dynamic tick sizing, optimal batching/TTL scheduling |
| C10 | Impact/dry run | Partial | Explicit uncertainty, aggregate evidence, affected enrollment upper bound | A true historical replay engine and calibrated queue-value scores |
| C11 | Supervisor view | Built | One local screen plus JSON endpoint and CLI | Authentication and hosted deployment |
| C12 | Audit | Built | Decisions, proposals, approval events and individual call receipts | Retention/access controls and richer query UI |
| C13 | Crash recovery | Built | Real SIGKILL while approval pending, restart and integrity checks | Exhaustive fault injection at every external boundary |
| C14 | Observability | Partial | Ingestion metrics, state, audit alerts and benchmark evidence | Prometheus/pager integration and wall-clock lag histogram |
| C15 | Fair resource allocation | Partial | Rotating workflow order, credit reserve, two-request cap | Tenant-weighted reservations and attention scheduling |

The selection principle is to make a small autonomous loop inspectable and recoverable before expanding its
optimization surface. A local UI and historical evidence are valuable; per-person timing without credible
samples is not. Partial capabilities are intentionally identified rather than represented as complete.

## 3. Stakeholders

### 01 — Sales

Accepted: clear client outcomes, fewer requests, and fast use of evidence. Declined blended KPI and automatic
rollout based on another account's demo. API policy disproves both auto-apply claims: Kestrel permits schedule,
caller ID, welcome and voice with max_shift 0.2; it does not permit prompts. Northwind KYC auto-apply is disabled.

**Reply:** We can show conclusion-rate lift alongside separate pickup and engagement rates. We will not blend
those KPIs. Kestrel's auto-apply excludes prompts and limits allocation movement; Northwind KYC requires
approval. We batch attention through a two-request daily cap and a consolidated view. A demo prompt from
another account is a hypothesis, not evidence. We will promote only what this workflow's calls support.

### 02 — Client Compliance

Accepted: human approval for customer-facing changes, validated scripts, per-call traceability and approver
hours. Operational caller changes may use the signed auto policy. The memo's hours match the observed public
API. No requirement is interpreted as a promise that exploration can never temporarily underperform.

**Reply:** Every voice, opening-message and prompt change requests your approval. Prompt changes attach a
validation run. Caller-ID changes can use your explicit operational policy and remain in the audit view.
We retain each call's configuration version and variants, and connect changes to their proposal and approval.
We limit exploration exposure and verify outcomes after changes. Evidence and uncertainty are visible; we
cannot honestly promise zero temporary underperformance while learning.

### 03 — Platform/SRE

Accepted: recovery test, durable identities, actionable conditions, measured load and no new stateful service.
SQLite adds a local file, not a cluster to operate. The production database would be the existing Postgres.
Simulator clock control does not establish real-time production performance.

**Reply:** State is in SQLite WAL with atomic ingestion and durable proposal intent. The recovery harness
kills the process while an approval is pending, restarts it and checks completion, duplicates and database
integrity. There is no new hosted infrastructure. Load reports include actual-host throughput and memory;
we do not claim a certified 4-vCPU Linux result. Production migration would use Postgres and partition by
workflow. Unknown paid requests are visible rather than blindly charged again.

### 04 — Client Operations Supervisor

Accepted: no silent overwrite, two proposals per rolling day, no requests before 11:00, consolidated view,
and engagement checks after safety fixes. The actual policy permits four requests and begins at 10:00; our
controller voluntarily uses the stricter requested limits. Policy also permits mid-flight changes, so a
proposal explicitly explains the change before approval; no out-of-band notification is sent.

**Reply:** You get one local view of experiments, approvals, changes and evidence. Requests start at 11:00
and are capped at two per rolling day. Your allocation edits are protected from future automated experiments;
other experiments pause for 24 hours after an edit. A safety incident may still produce a new prompt proposal
for your approval. Validation alone does not establish engagement: observed engagement helps select among
safe candidates, and post-change verification can propose rollback.

### 05 — Product

Accepted: distinct KPIs, common cohort ID, evidence from actual calls, proposal fields and workflow-local
promotion. An expired approval is technically an `expired` state, not a `rejected` state; both close that
proposal and require a fresh decision. Declined all three wishlist items as P0: caller health and a view
were built, personalized timing was cut.

**Reply:** Pickup and engagement remain separate throughout. The shared decision cohort is currently default;
language slices are diagnostics, not separate experiments. Unrun arms contribute no observations. Proposals
show evidence and explicitly label unknown benefit; impact is a measured absolute rate lift when available,
otherwise zero. Expired proposals close and need refreshed evidence. Caller health and one supervisor view
are included. Personalized scheduling needs its own randomized design and is deferred.

### 06 — CTO

Accepted: outcome accountability, low credit spend, deliberate scope and operational documentation. No claims
of production readiness or hidden-scenario performance are made from public results alone.

**Reply:** We prioritized persistence, governance, caller health and prompt incident response over personalized
scheduling and feature-specific optimization. Each applied change is explainable from our own store. Credits
are reserved for sustained incidents and validated candidates, not routine variant selection. Public results,
harm classifications and machine-specific load metrics are included with their limitations. Before production
we would calibrate statistical error under repeated callers, test more crash boundaries, and migrate state to
existing Postgres with per-tenant scheduling and operational monitoring.

## 4. Architecture

```text
HTTP history/events -> streamed chunks -> atomic SQLite transaction
                           |              leads + calls + hourly sufficient statistics
                           v
                   population detectors / experiment evaluator
                           |
                   durable proposal intent + evidence
                           |
                  governance policy + human approval
                           |
                  apply / reconcile remote history
                           |
                 post-change verification / rollback
                           |
                 audit CLI + supervisor HTML/JSON
```

`controller/store.py` owns persistence and feature joins. `controller/statistics.py` contains deterministic
rate/interval/winner functions. `controller/engine.py` owns HTTP orchestration and policy decisions.
`controller/__main__.py` provides execution and views. The external `scripts/evaluate.py` launches separate
processes and official evaluation; it is not imported by the controller.

Restart first checks world identity regressions, ingests outstanding chunks, lists remote approvals and
config history, then reconciles local proposal intent. A process lock protects the database from a second
writer. Individual call receipts support customer-level traceability after aggregates are updated.

## 5. The learning loop

- **Cohorts:** `default` is the single shared decision object. The lead join retains language, age, value
  and city features. Language diagnostics do not pretend to be independently powered experiments.
  Existing custom cohorts are left intact and variant experimentation abstains for those workflows.
- **Experiment design:** one dimension at a time. 70% of allocation retains the incumbent mixture; 30%
  is uniform across permitted options. Engagement workflows try voice, welcome and caller ID in order.
  Pickup workflows focus on caller ID. Winner allocation is 80%, with 20% distributed over alternatives.
  No welcome×voice interaction model is claimed.
- **Winner:** >=400 connected calls per observed arm, at most seven daily looks per experiment epoch,
  and nonoverlapping 3.5-z Wilson intervals. The primary metric is used for voice/welcome; caller ID uses
  pickup. One-sided guardrail noninferiority must pass before a non-control winner is promoted.
  A single interval's nominal tail coverage is approximately 99.95%; this is NOT a calibrated whole-run
  false-winner rate. Multiple epochs, correlated callers and selection invalidate such a simple claim.
- **Decay:** promoted arms are reevaluated using recent 48-hour evidence with sentinel alternatives.
  Separate post-apply checks compare actual current-version outcomes with the previous version.
  Substantial separated-interval degradation proposes rollback through governance; prompt rollback needs
  validation too. Public_02 did not demonstrate a promoted winner's decay rollback. Coverage is code/tests,
  not proof that this policy catches every hidden decay incident.
- **Call time / caller ID:** call-time optimization is deferred. DID health requires >=300 recent dials,
  >=600 prior dials, separated intervals with at least 5pp degradation, and a healthier concurrent option.
- **Guardrail:** uses the workflow's absolute maximum drop, with a one-sided 1.645-z difference bound for
  winner promotion. Exploration is an explicitly approved risk; post-apply monitoring is not a guarantee
  that no temporary cohort harm can occur.

## 6. Governance

```text
prepared -> pending -> approved -> applied
                  |           -> stale / lapsed
                  -> rejected / expired
prepared -> failed / stale
unknown response -> remote approval/config-history reconciliation
```

The body and content-derived ID commit before submission. A response lost after apply is recovered from
configuration history by proposal ID. Stale proposals close; fresh proposals use the current config and
current evidence. Rejections and expiry never cause blind replay of the same old proposal.

Requests are limited to min(policy limit, 2) per rolling 24h and to approver hours with one hour remaining;
Kestrel starts no earlier than 11:00. The implementation sends one decision at a time rather than an optimal
multi-change batch. Approval polling is hourly. Very short policy apply windows are a known weakness.

Only pure caller-ID changes that satisfy enabled/allowed_dims/max_shift can auto-apply. Customer-facing
changes always request approval, even where the API permits more latitude. All public changes used approval.

Impact score is observed absolute primary-rate improvement, clipped to [0,1], when measured; exploration
and incident safety changes score zero because their conversion value is unknown. Affected leads count is
unconcluded enrollments, explicitly an upper bound including cadence-expired leads. Dry-run fields include
historical aggregates and uncertainty. They are not a full counterfactual replay, hence C10 is partial.

Supervisor edits invalidate base versions. The controller resets experiments, pauses for 24h, and protects
edited allocation dimensions. It preserves the latest full configuration when preparing any new proposal.

## 7. Incidents

Hallucination detection requires >=200 connected calls in a four-hour window, >=4% flag rate, and a four-sigma
score against max(2.5%, historical pre-change flag rate + 1.5pp). The detector is imperfect and repeated windows
are correlated. A nominal one-sided normal tail at z=4 is about 0.0032% per look; the actual incident false
positive rate has not been empirically calibrated and should not be advertised as that number.

Incident state persists overnight and blocks unrelated experiments. A suggestion costs 3 credits; up to
three validations of 400 conversations cost 4 credits each. At least 20 credits must remain before starting
an incident response. Unknown paid responses are never automatically repeated. Among safety-passing
candidates, observed engagement lower bounds take precedence over small validation-score differences.
Post-apply verification records both KPIs; an unsafe rollback is escalated, not applied.

Public_02: DID flagged D2 10:00; degraded share reached zero on D3. Bad prompt supervisor edit D3 11:30;
fix applied D4 13:00 (1,530 minutes later), with intervening evidence accumulation and approver closure.
Three validations and one suggestion cost 15 credits. This MTTR is too slow for a serious live incident;
a persistent incident was essential, but earlier low-volume detection and approver escalation remain work.
See `reports/audit-example.json` for actual timestamp, approval and subsequent outcomes from our own store.

## 8. Scale

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

Measured public_03 results are recorded in `reports/public_03_load-metrics.json` and summarized in
`reports/LOAD.md`. Measurements include historical ingestion. Controller wall time includes startup history
and waiting for simulator `/advance`; ingestion time includes JSON decoding and SQLite writes but excludes
HTTP transfer. Peak RSS is for the controller process only; on crash runs it covers the final restarted process, not a sampled maximum across all segments. Simulator memory and disk are separate.

The machine is an 8-logical-CPU macOS host running Python 3.13.2. This is not evidence of compliance on the
specified 4-vCPU / 8GB Linux box. The baseline CLI log reports 1,420.5 seconds using time.time; controller and harness use time.monotonic.
Those clocks can disagree across host suspension or time adjustment; durations must not be added or their
difference treated as controller overhead.
Monitoring evaluations run every 60 simulated minutes after startup ingestion; experiment looks run daily
(every 1,440 minutes). Sample-size, approver-hour and quota delays are additional. These are scheduling
intervals, not a measured end-to-end latency distribution. Wall-clock p95 decision lag is not instrumented.

At 10×, random lead/call index I/O, one SQLite writer, feature-cache misses and retained call storage become
bottlenecks. Use existing Postgres partitioned by tenant/workflow and date, bulk writes, immutable event
cursors, per-workflow ownership and materialized aggregates. In production ingestion and decisions must run
independently of the dialler clock; prioritize incidents without starving event consumption. Archived call
receipts need explicit retention and access policies.

## 9. Reliability

`--crash` in the evaluation harness waits for a pending approval, sends real SIGKILL, restarts with the same
database and simulator, and checks integrity and event uniqueness. Evidence is in
`reports/public_02-recovery.json`. The pending proposal reconciled to applied; no duplicate calls were stored,
no pending proposals remained, and `PRAGMA integrity_check` returned `ok`.

A chunk is all-or-nothing. Content-derived proposal IDs survive response loss. Remote config history is the
source for reconciling applied mutations, not for replacing the controller's audit evidence. Paid result
loss remains unavoidable without a stronger API. GET/transport/5xx failures use bounded exponential backoff;
mutation retries occur only after reconciliation. 4xx responses are audited; stale/lapsed requests close.
Eight consecutive transport/5xx errors stop execution for operator investigation. SQLite/disk errors stop
rather than advancing time and discarding data. No production process supervisor is bundled.

Tests cover transactional rollback, replay/restart, nullable QA, statistical abstention, lost apply responses,
stale approval after supervisor edit, uncertain paid calls, overnight incidents, and safety/engagement separation.

## 10. Audit & observability

A real query using only controller-owned records:

```bash
.venv/bin/python scripts/audit_change.py --db controller-data/release_02.sqlite --workflow ks_cancel
```

Full output: `reports/audit-example.json`. The output links a prompt diff and rationale to `controller_approved`,
an approval event and subsequent per-version calls. Supervisors see the same records at local port 8800;
`controller status` exposes JSON. Individual lead receipts can be joined to their features and config events.

Page-worthy audit conditions: sustained hallucination incident without a usable fix, repeated HTTP failure,
unsafe rollback, exhausted incident credit reserve, and database/disk failure. A page should name workflow,
incident/proposal, current version and the failed operation. Routine insufficient evidence, judgement-call
rejection and expiry remain in the view and do not page by themselves. This implementation records alert
conditions; actual pager delivery and metric export are not wired up.

## 11. Results

The tables below are copied from the official grade reports; deltas are relative unless the report says
otherwise. See `reports/public_01.md` and `reports/public_02.md` for full changes, governance and incidents.

**Public_01**

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.355 | +3.9% | 0.246 | +0.4% | 0.504 | +2.5% | 4% | 46 (57) |
| nw_kyc | 0.405 | +10.4% | 0.268 | +10.6% | 0.595 | -0.3% | 0% | 30 (21) |
| nw_renewal | 0.404 | -2.9% | 0.259 | -2.0% | 0.538 | -0.7% | 0% | 39 (54) |
| ALL | 0.382 | +2.7% | 0.254 | +1.4% | 0.534 | +0.9% | 2% | 115 (132) |

**Public_02**

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.282 | +19.6% | 0.201 | +10.9% | 0.493 | +5.4% | 26% | 103 (348) |
| nw_kyc | 0.424 | +13.4% | 0.266 | +13.4% | 0.603 | -0.9% | 0% | 23 (29) |
| nw_renewal | 0.437 | +0.8% | 0.264 | +0.8% | 0.553 | -0.2% | 6% | 70 (54) |
| ALL | 0.363 | +9.9% | 0.235 | +7.2% | 0.540 | +1.5% | 13% | 196 (431) |

Public_01's aggregate lift is modest and Northwind renewal conclusion rate falls despite a neutral hidden-truth
change classification. Public_02 improves all three workflows' conclusion rates; no applied change is graded
harmful in the final run. These are single seeded public runs, not confidence intervals for causal lift.
Kestrel still suffers exposure before the incident fix; 196 hallucinated calls remain across the platform.
No global KPI is presented as a replacement for per-workflow primary and guardrail checks.

Development evidence exposed two concrete failures: uniform exploration caused harmful changes, and choosing
by validation score alone could pick a strict prompt with worse engagement. The final policy limits new-arm
exposure and uses engagement evidence among safety-passing candidates. Earlier reports remain under
`reports/development/` so these outcomes are not hidden. Further work should prioritize calibrated cohort-level
learning and faster incidents rather than tuning to these public truth tables.

## 12. Trade-offs & rejected alternatives

| Option | Why considered | Why rejected / what instead |
|---|---|---|
| New Kafka/Redis services | Event throughput | Avoid infrastructure overhead; streaming HTTP and SQLite first |
| LLM winner selection | Flexible explanations | Deterministic statistics; model only suggests prompt candidates |
| Uniform full exploration | Faster evidence | Public development harm; retain 70% incumbent allocation |
| Highest validation score wins | Simple safety ranking | Does not measure engagement; prefer observed engagement among safe candidates |
| Per-person timing | Summit headline | Sparse observations and scheduling confounding; defer |
| Cross-client transfer | Faster cold start | Policy/population mismatch; learning stays within workflow |
| Immediate automatic prompt rollback | Fast incident recovery | Prompt validation and human approval still apply |
| Fifty alerts | Easy implementation | One consolidated view with evidence and actionable audit conditions |

## 13. Known weaknesses

- Coarse shared default cohort cannot reliably capture heterogeneous language/age winners or protect every subgroup.
- Winner tests use approximate independent-Bernoulli intervals on potentially correlated returning callers.
  Whole-run false-winner probability is not calibrated. Not every allowed option is guaranteed enough exposure.
- Explorations can remain inconclusive for the scenario duration and block the next dimension.
- Sentinel and post-apply temporal comparisons may miss gradual decay or confound it with population changes.
- The latest-change monitor can be superseded by a later change; it is not a complete causal change graph.
- Incident latency is slow at low volumes and outside approver hours. No outbound escalation is implemented.
- Affected leads and dry-run estimates are explicitly approximate. Queue scores undervalue safety incidents
  because their conversion benefit is unknown; operational incident priority is handled separately.
- Hourly polling can lapse short apply windows; batching/fairness are simple limits rather than optimal scheduling.
- Exactly-once paid operations are impossible with the exposed API; uncertain results may require intervention.
- SQLite single-writer behavior and retained per-call data constrain sustained growth. No authenticated hosted UI.
- The API exposes approval IDs and actors, not a named human approver identity; we cannot fabricate that name.
- 4-vCPU Linux certification, hidden scenarios, exhaustive fault injection and personalized call-time optimization
  are not claimed as completed.

## 14. If this went to production at Formi next month

1. Days 1–2: shadow production events, reconcile definitions and consent/policy ownership, establish authenticated
   audit access, retention and exact run/workflow identity. No autonomous configuration writes yet.
2. Days 3–4: move durable state to existing Postgres, partition ingestion, add event lag/credit/quota dashboards,
   actionable incident routing and an operator playbook. Verify throughput on the actual 4-vCPU environment.
3. Days 5–7: fault-inject every external boundary, require idempotency/retrieval for paid APIs, calibrate clustered
   statistical error and drift detectors on replayed data. Make apply cadence policy-aware.
4. Days 8–10: supervised canary on one tenant, verify subgroup guardrails and dry-run accuracy, exercise rollback
   with compliance and operations, then expand only after an operational review. Personalized timing comes later.
