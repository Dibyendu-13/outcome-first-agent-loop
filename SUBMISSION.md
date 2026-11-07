# Outcome-First Agent Loop — Submission

**Name:** Dibyendu-13 (repository Git identity). **Date:** 2026-11-07.
**Hours actually spent:** Automated implementation and evaluation; measured run durations are recorded below. Human review time is not recorded and is not claimed. **Language / storage:** Python / SQLite WAL.

## 0. TL;DR

HTTP-only controller with durable event ingestion, shared language cohorts, governed experiments and incident response.
Public_01: +4.9% relative conclusion-rate lift; three applied changes, none graded harmful.
Public_02: +10.1% relative conclusion-rate lift; seven applied changes, none graded harmful; 15 credits spent.
Public_02 prompt fix: 405 simulated minutes versus 1,530 in the previous implementation; 177 hallucinated calls versus 431 baseline.
Exact cohort tests, a real-HTTP promotion/rollback proof, five SIGKILL recovery cases, and a read-only supervisor console.
Personalized call-time optimization and factorial experiments are deliberately out of scope.

## 1. Assumptions

1. The HTTP contract and workflow policies govern behavior. The controller never imports the simulator or reads scenario files, grader truth, or simulator output directories.
2. One controller owns one world. Default `run.sh` selects a durable world database from public scenario/progress, preserves older runs, and resumes a known world. Explicit DB reuse rejects detected resets. The API does not expose a unique world ID; indistinguishable replacements cannot be detected reliably.
3. Chunk and event IDs obey the documented increasing order. Entire chunks and their checkpoints commit atomically; overlapping event IDs are ignored.
4. Guardrail drops are absolute percentage-point margins. Pickup and engagement are never blended. Campaign conclusion rate tracks the uploaded cohort, not all call conclusions occurring that day.
5. Experiment inference assumes stable, exchangeable Bernoulli observations within a cohort and configuration epoch. An independent person is counted once per KPI stream. This removes repeated-call pseudoreplication, not every source of population drift.
6. First dial measures pickup. First connected call measures conditional engagement. A DID can change who connects; conditional engagement remains the required guardrail, not a population-invariant causal quantity.
7. Historical observations provide priors and contextual comparisons. No historical-only winner, no model-selected winner, and no estimate for an unobserved arm.
8. Supervisor edits are authoritative. We protect edited allocation dimensions, suspend stale experiments, and require fresh evidence and approval for any subsequent relevant change.
9. Affected enrollment counts exclude expired campaign cadence and concluded leads, but may include leads that exhausted today's attempts. Locked existing campaigns are unaffected by allocation-only changes; next batch size is a forecast.
10. Paid requests have no idempotency key or result retrieval. A lost acknowledgement remains uncertain and is never blindly repeated. This is an API limitation, not a claimed successful recovery of the missing response.
11. A terminal scenario stops time advancement. A healthy completed run can have inconclusive experiments. There is no obligation to force a winner.

## 2. Scope decisions

| # | Capability | Status | Evidence / remaining boundary |
|---|---|---|---|
| C1 | Event ingestion | Built | Transactional streamed chunks, overlap suppression, indexed calls, public_03 and SIGKILL evidence |
| C2 | Shared cohorts | Built | Ordered feature rules, language groups with sufficient historical people, actual cohort IDs in evaluation, monitoring and console |
| C3 | Historical bootstrap | Built | All history ingested before the first decision; population and prior flag references |
| C4 | Call-time optimization | Cut | Observational time-of-day comparisons and sparse personal histories cannot justify changes within this scope |
| C5 | Caller-ID health | Built | Population thresholds, historical degradation plus a contemporaneous healthier alternative; public_02 rotation |
| C6 | Variant experimentation | Built for selected scope | One dimension at a time, independent-person fixed prefixes, exact tests, multiple-comparison budget and null calibration; factorial interactions cut |
| C7 | Promotion, decay, rollback | Built | Governed 80% promotion, 20% sentinel traffic, fresh 3-hour monitoring windows, cohort guardrail rollback; HTTP proof and tests |
| C8 | Prompt incidents | Built | Fixed sample detection, durable incident, candidates, validation, human approval and post-apply evidence |
| C9 | Governance | Built for selected scope | Durable lifecycle, short-window polling, batched cohort changes, approval reserve, stale/expired/lapsed tests; no optimal global queue scheduler |
| C10 | Impact and dry run | Built for selected scope | Cohort reweighting of observed arm means, coverage and uncertainty, active-cadence population bounds; unsupported effects withheld |
| C11 | Supervisor console | Built | Live SQLite projection, workflow/cohort evidence, approvals, incident history and read-only details |
| C12 | Audit | Built | Decision, proposal, approval, configuration and per-call receipts in controller-owned SQLite |
| C13 | Crash recovery | Built within protocol limits | Five real SIGKILL boundaries plus pending-approval restart; unknown paid receipt escalates without retry |
| C14 | Observability | Built for selected scope | Measured cycle latency, call freshness, ingestion/credit health, alert records and `/metrics`; no production paging integration |
| C15 | Resource fairness | Partial | Rotated workflow service, hard request caps and reserved critical slot; no strict tenant credit allocation |

Prioritize reliable, explainable changes and incident recovery over feature count. Personal timing, factorial welcome × voice experiments, a production identity layer, and tenant-wide optimal scheduling are deliberate cuts. They are not prerequisites for running the delivered scope.

## 3. Stakeholders

### 01 — Sales

Accepted a client-level outcome with the separate KPIs alongside it. Declined blended KPI, instant promotion, and broad auto-apply. The Kestrel policy allows only certain dimensions and a 0.2 shift; it excludes prompts. Northwind KYC auto-apply is disabled. A prompt that looked good elsewhere is not evidence here.

**Reply:** We can report concluded leads over uploaded leads and show pickup and engagement separately. Kestrel's policy does not allow automatic prompt changes; Northwind KYC requires review. A variant earns promotion after its observed improvement and guardrail checks, within the client's approval window. We reserve reviewer capacity for critical fixes. A prompt from another tenant's demo remains a candidate for validation, not a proven winner.

### 02 — Client Compliance

Accepted named-review expectations where supported, human approval for customer-facing experiments, script validation and per-call traceability. The API provides approval IDs and actors, not a named human identity. The observed approval hours match the memo. Exploration carries bounded risk, even when authorized.

**Reply:** Every welcome, voice, and prompt change uses client review. A prompt change includes a passing validation receipt. Only explicitly permitted caller-ID shifts can use auto-apply. We can trace each call to its actual variant and version, then to the recorded proposal and approval. The simulator exposes an approval ID rather than a human name. Evidence limits and any rollback are visible in the supervisor console.

### 03 — Platform/SRE

Accepted crash proof, idempotency, measured capacity and actionable alerts. SQLite adds no hosted service. Production would move partitioned state to the existing Postgres and use an external monitoring stack. The paid API cannot provide exactly-once results without a stronger protocol.

**Reply:** The controller commits event data and cursors together and reconciles remote proposal IDs before repeating a mutation. Five real kill/restart cases cover ingestion and external calls. A lost paid result remains uncertain and is not charged again. We record ingestion throughput, observed call freshness, processing latency and peak memory, with Linux resource limits visible in the report. The console exposes metrics; production can scrape them and route actionable alerts.

### 04 — Client Operations Supervisor

Accepted no silent overwrite, two requests per rolling day, no pre-11:00 Kestrel requests, one console and engagement-aware safety remediation. The public API permits four requests and starts at 10:00; the controller honors the stricter memo. Existing approval records cannot be withdrawn via the documented API, but stale ones never apply.

**Reply:** You can see live experiment evidence, what changed, the approval receipt, and what happened next in one console. Kestrel requests start at 11:00 and never exceed two per rolling day; ordinary changes leave a slot for critical fixes. Your edits invalidate stale proposals, and the controller protects the dimensions you edited. Safety validation is not engagement evidence, so we prefer previously observed safe candidates and monitor both KPIs afterward.

### 05 — Product

Accepted separate KPIs, actual-call evidence, shared cohort definitions, local promotion, and honest proposal estimates. Expiry is a distinct API terminal state, with the same practical requirement for fresh evidence. Per-person timing is deferred; cohort voice/welcome and caller health are included.

**Reply:** The same ordered cohort rules govern exposure, evaluation, and the console. People count once per KPI stream in an experiment; unrun arms add no evidence. A proposal shows an active-enrollment bound and a replay estimate only where observed arms support it. Closed proposals require fresh evidence and the current configuration. We built caller health and the supervisor view; personalized scheduling is outside this submission.

### 06 — CTO

Accepted calibrated conservative autonomy, credit discipline, explainability and honest scaling limits. Outcomes on public runs are evidence, not proof of hidden-scenario or production performance. A synthetic lifecycle proof exercises branches the short public workloads do not reliably power.

**Reply:** We prioritized governed learning, rollback, and recovery over per-person scheduling. Each promotion needs exact evidence and a separate guardrail pass; the approved change is traceable to actual observations. Prompt fixes spend credits only after population evidence. The reports distinguish official public outcomes, controlled lifecycle proof, statistical calibration, and Linux measurements. The remaining production work is authentication, partitioning, alert routing, and calibrating drift on live data.

## 4. Architecture

```text
HTTP history/events -> streamed NDJSON -> SQLite atomic chunks + event cursor
                             |          leads, call receipts, hourly cohort metrics
                             v
               incident / caller health / shared cohort learner
                             |
               fixed independent-person observations + evidence replay
                             |
              durable intent -> policy / approval -> reconcile -> apply
                             |
             fresh cohort monitoring -> governed rollback when justified
                             |
                   audit CLI + read-only console + metrics
```

`controller/store.py` owns durability. `cohorts.py` implements ordered AND/OR membership. `learning.py` owns epochs, fixed looks and rollback. `statistics.py` provides exact tests and bounds. `engine.py` owns the HTTP boundary, approvals and incident priority. `dashboard.py` projects actual stored observations. The default entrypoint preserves old world databases and locks the selected writer. Test harnesses and grading live outside the controller.

## 5. The learning loop

**Cohorts.** Keep existing client definitions. If absent, form disjoint language cohorts only for languages with at least 400 observed distinct people, including history, with a default fallback. Use actual event cohort IDs and version. Old campaign-locked exposure and mismatched prompts are never credited to the active epoch.

**Experiment design.** One workflow dimension at a time. Initial allocation is a 50% incumbent mixture plus 50% uniform exploration across allowed options, approved with its uncertainty visible. Pickup-focused workflows use caller ID; engagement workflows start with voice, then welcome as scope permits. Candidate versus incumbent comparisons use the first dial per person for pickup, and first connected call per person for engagement. No welcome × voice interaction estimate is claimed.

**Decision rule.** Use event-ID prefixes of 200, 400, 800, 1,600, 3,200, 6,400, 12,800, 25,600, and 51,200 independent units per arm. Test one-sided Fisher exact primary improvement, followed by a separate exact Clopper–Pearson difference lower bound above the negative guardrail margin. Select the strongest eligible observed candidate deterministically; do not claim superiority over every alternative. Each look persists before an external mutation. Fresh evidence is needed after a declined, expired, or lapsed recommendation.

**Error allocation.** The learner family spends at most 2% on false primary improvement, 2% on incorrect guardrail noninferiority, and 1% on erroneous decay/breach signals per workflow under its stationary independent-person model. Epoch weight `6/(π² j²)` sums to one. Divide by cohort count, candidate comparisons, and fixed looks. Half the guardrail budget is for promotion; the remainder is spread over fresh decay windows with `1/(r(r+1))` spending. Decay budget splits between primary reversal and guardrail breach. Between-epoch independence is not needed for the union bound. These budgets do not cover separate observational caller health, QA incidents or temporal post-apply checks.

**Calibration and power.** `reports/statistical-calibration.json`: 3 of 1,000 simulated null families had a false *primary* signal (0.3%; one-sided 95% upper bound 0.77%). This exercises two epochs and the first three declared looks, before guardrails. The analytic spending covers all declared looks under the stated model. The simulated primary test found a 20 pp effect by 800 units in all 1,000 examples; that is not full promotion power. Exact 2 pp noninferiority with unchanged pickup needs tens of thousands of units. Low-volume cohorts therefore often remain inconclusive. The power grid shows where a 15 pp effect passes primary testing but the guardrail does not.

**Promotion and decay.** Promote to 80%, retain 20% sentinel alternatives, and restore baseline for unpromoted cohorts. Evaluate fresh disjoint 3-hour windows to avoid burying decay beneath old successes. A significant reversal can restore the prior cohort allocation. A proven cohort guardrail breach can do so even if primary still wins. Other cohorts keep their promoted allocations and remaining monitoring budget. Changes require approval and the current base version. The real-HTTP fixture demonstrates the full sequence; public grades are separate.

**Call time and caller ID.** Timing remains business-owned. Caller-ID health uses >=300 recent and >=600 earlier dials, separated pickup intervals, a 5 pp decline and a healthier simultaneous alternative. It can act independently of the learner and invalidates the affected experiment epoch if configuration changes.

## 6. Governance

```text
prepared -> pending -> approved -> applied
                  |           -> stale / lapsed
                  -> rejected / expired
prepared -> stale / failed
unknown response -> reconcile remote approval / configuration history
```

Proposal ID and body commit before the request. Apply recovery finds the actual remote version and proposal ID; it does not repeat a completed apply. A stale pending or approved base is closed immediately, so it cannot block a safety incident until human response. Expiry, lapse and rejection retire that learning snapshot and require a later fixed look or a fresh operational assessment. No API withdrawal endpoint is assumed.

Batch related cohort allocations in one proposal, never combine unrelated experiments. Cap requests at min(policy limit, 2) per workflow over 24 hours, with the last slot reserved for critical work where the limit allows it. Kestrel starts at 11:00. Ordinary requests leave one hour before close; critical fixes can use the last working hour. Poll every 15 minutes with pending work, active incidents, or dialling, and cap other steps by the shortest apply window. Policy expiry still governs; the 15-minute API tick prevents universal guarantees for sub-tick windows.

Only pure caller-ID changes within enabled dimensions and total-variation shift can auto-apply. Cohort creation, prompts, voice and welcome remain reviewed. Scope never changes business cadence, capacity or dialling windows. Supervisor changes protect edited allocation dimensions, suspend the old epoch, and pause experiments for 24 hours.

The dry run reweights actual observed arm means under old and proposed allocations within each cohort. It withholds an estimate if a positive-weight arm is unobserved, reports coverage, and weights supported effects by active enrollment counts. A zero queue score can represent unknown benefit; the evidence retains a signed estimate when available. Existing campaign locks and forecast batch size are explicit. Temporal comparisons and population assumptions are not disguised as causal guarantees.

## 7. Incidents

Require at least 200 connected calls and a 4% automated flag rate. Within each prompt episode, compare fixed doubling call prefixes against a bounded historical reference (floor 2%, historical rate +0.2 pp, cap 5%). Exact binomial upper tails use a 5% per-workflow alert budget across episodes and looks; validity assumes the conditional flag probability under the null does not exceed that reference. This is a flag-based decision, not a true-hallucination diagnosis. A longstanding prompt episode can dilute a late change; no universal change-point guarantee is made.

A durable incident blocks unrelated experiments. Spend 3 credits on suggestions and up to 12 on three 400-conversation validations. Start only with at least 20 remaining credits. Passing safety alone does not prove engagement. Prefer passing candidates with observed engagement evidence, then attach the validation ID and request human review. Post-apply observations record pickup, engagement and flag counts; unsafe prompt rollback requires a new passing validation and otherwise raises an alert.

Final public_02: supervisor prompt edit D3 11:30; a 400-call prefix met the exact threshold while reviewers were open; approved fix applied 405 minutes after the edit. The run used 15 credits and graded 177 hallucinated calls versus 431 baseline. See the actual approval and post-change rows in `reports/audit-example.json`. The earlier implementation took 1,530 minutes; permission and sample accumulation still dominate elapsed incident response.

## 8. Scale

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

`reports/LINUX.md` explains the final run, actual cgroup limits, physical VM memory, baseline provenance, and timing definitions. Native Linux volumes avoid benchmarking Mac shared-filesystem SQLite behavior. The 4-CPU quota and 8 GiB cap apply to the entire test container; the Docker VM physically exposes less than 8 GiB and hosts other services. No global Docker settings or other containers were changed. This is constrained Linux evidence, not a hardware-independent performance guarantee.

At 10×, single-writer SQLite, random lead/index I/O, and per-person cohort sampling dominate. Partition by tenant/workflow/date using the existing Postgres, bulk writes and bounded feature caches. Decouple production ingestion and decision workers, allocate a workflow owner, and archive immutable receipts with retention controls. Simulation generation and permission wait are separate from processing latency.

## 9. Reliability

`reports/fault-matrix.json` records real SIGKILL after a chunk transaction began, after proposal send, after apply send, after advance response, and after a paid response. Every restarted run finished; SQLite integrity was `ok`, call IDs were unique, and no proposal was stranded. The paid case preserved the open incident and uncertain charge, emitted one operator alert, and did not issue the same charge again. Missing paid evidence cannot be reconstructed from the documented API. The independent public_02 pending-approval recovery is in `reports/public_02-recovery.json`.

Atomic chunk replay protects lead/call/aggregate/checkpoint consistency. Record proposal intent before network mutation; reconcile by remote IDs and history. Re-read state after an uncertain advance rather than repeating the same advance blindly. GET/transport/5xx use bounded exponential backoff; 4xx terminal states are recorded with reasons. Eight consecutive infrastructure failures stop the process for investigation. On disk failure, stop writes and preserve DB/WAL; do not advance and lose data.

## 10. Audit & observability

```bash
.venv/bin/python scripts/audit_change.py --db controller-data/final_public_02.sqlite --workflow ks_cancel
```

The output shows `ks_cancel` changed to prompt P1 at 18:15 IST on Jan 7 (version 5,
`controller_approved`). Approval `apr_00005` was recorded at 17:51 IST and the proposal referenced
validation `val_00001`. Subsequent calls on v5: 7,600 dials, 1,472 connections, 731 engaged calls, and
22 automated hallucination flags. `reports/audit-example.json` has the full output. The API does not
identify a named human. The console shows the same controller records and actual per-cohort samples; raw evidence is expandable. `GET /metrics` exposes ingested events, event backlog, credits, proposal/paid states and a measured cycle latency histogram. `GET /api/dashboard` is read-only.

Page for sustained unresolved QA incidents, repeated simulator errors, unsafe rollback, uncertain paid work blocking incident recovery, and storage failure. Include workflow, current version, proposal/operation ID and next action. Routine insufficiency, judgement-call rejection and terminal expiry do not page alone. Production pager delivery is outside this submission.

## 11. Results

**Public_01**

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.355 | +4.1% | 0.244 | -0.4% | 0.512 | +4.0% | 7% | 64 (57) |
| nw_kyc | 0.424 | +15.6% | 0.283 | +17.0% | 0.586 | -1.9% | 0% | 25 (21) |
| nw_renewal | 0.416 | -0.1% | 0.262 | -0.9% | 0.544 | +0.5% | 0% | 50 (54) |
| ALL | 0.390 | +4.9% | 0.257 | +2.6% | 0.539 | +1.7% | 2% | 139 (132) |

**Public_02**

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.282 | +19.6% | 0.198 | +9.1% | 0.500 | +7.0% | 30% | 92 (348) |
| nw_kyc | 0.451 | +20.6% | 0.278 | +18.6% | 0.608 | -0.1% | 0% | 29 (29) |
| nw_renewal | 0.422 | -2.6% | 0.263 | +0.2% | 0.537 | -3.1% | -1% | 56 (54) |
| ALL | 0.364 | +10.1% | 0.236 | +7.3% | 0.539 | +1.2% | 11% | 177 (431) |

These are seeded public runs, not confidence intervals or hidden-scenario predictions. The final public runs had no applied changes graded harmful. Short public trials still seldom satisfy the strict exact guardrail, so their lift comes largely from bounded exploration and operational fixes. Earlier development runs with harmful changes remain in `reports/development/`; they motivated exposure limits and separating safety evidence from engagement. The lifecycle proof uses synthetic signals deliberately strong enough to exercise promotion and rollback, not an official scenario score.

## 12. Trade-offs & rejected alternatives

| Option | Why considered | Why rejected / chosen approach |
|---|---|---|
| Call-level repeated z-tests | Fast results | Return-person correlation and repeated selection; fixed independent-person prefixes with exact spending |
| Declare winner by observed mean | Easy to communicate | Insufficient sample and guardrail uncertainty; abstain until tests pass |
| Cumulative decay monitoring forever | Reuses evidence | Early successes bury later damage; use fresh windows with a bounded budget |
| Roll back only on primary reversal | Clear metric signal | Secondary KPI can breach while primary wins; monitor both |
| Highest validation score wins | Convenient safety ranking | Safety is not engagement; prefer known engagement among safety-passing candidates |
| Automatic retry after unknown paid acknowledgement | Faster recovery | Duplicate spend risk; mark uncertain, alert, and request API idempotency/result retrieval in production |
| Per-person scheduling | Potential lift | Sparse observations and timing confounding; defer |
| New Kafka/Redis cluster | Scale | Extra operations; SQLite first, existing Postgres for production |

## 13. Known weaknesses

- Model-dependent statistical guarantees do not survive arbitrary within-epoch temporal or selection drift. Calibration is synthetic, not empirical coverage for every tenant.
- Exact guardrails sacrifice speed and power. Some low-volume cohorts do not earn a promotion before the run ends.
- Temporal post-apply comparisons can be confounded. Subgroup decay detection still needs enough sentinel observations in a fresh window.
- Broad language cohorts leave residual heterogeneity. Factorial interactions, personalized timing, tenant-wide quota optimization, authenticated hosting, and paging are cut.
- The API lacks named approvers, unique world IDs, and paid-result retrieval. Sub-tick approval windows and lost paid results are protocol boundaries.
- No claim about hidden-scenario outcomes or production certification. Personal review and interview defense remain the candidate's responsibility.

## 14. If this went to production at Formi next month

1. Shadow live ingestion, reconcile consent/policy ownership and the business denominators, and set retention and audit access before any write.
2. Partition state in existing Postgres. Add a real world/run ID, durable paid idempotency and receipt lookup, and active-workflow scheduling. Install metrics scrape and actionable routing.
3. Calibrate clustered inference and drift behavior on real randomized exposure. Stress test governance, expiry and every crash boundary with the actual provider.
4. Canary one tenant with human review, inspect subgroup guardrails, rehearse rollback and expand only after operational evidence. Revisit personalization later.
