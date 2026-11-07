# Supervisor console

Run from the repository root:

```bash
.venv/bin/python -m controller serve --db controller-data/final_public_02.sqlite --port 8800
```

Open http://127.0.0.1:8800. If an older server is already running, stop it with Ctrl+C before restarting.
The browser automatically refreshes data every 15 seconds; refresh the page after frontend source changes.
The console is local and read-only. It displays controller decisions and client approval receipts; it does
not impersonate an approver or provide an unauthenticated configuration-write endpoint.

## Pages and interactions

- **Overview:** campaign conclusion rate, separate call KPIs, daily pickup/engagement trends, exceptions,
  workflow cards and recent applied changes. Select a tenant or workflow to update the analytics scope.
- **Experiments:** actual independent-person per-arm observations for new runs, current recorded allocation, the minimum sample,
  evaluation look count and last-evaluation explanation. A completed simulation does not leave experiments
  labelled as receiving traffic. No promotion is invented from final observations arriving after a look.
- **Approvals:** searchable proposal register with status filtering. The detail drawer links the actual
  diff, estimated impact, affected enrollment bound, validation, approval decision and subsequent verification.
- **Decision history:** important events in simulated timestamp order, with routine evaluations hidden
  initially. Expand technical evidence when needed. Proposal links connect decisions to their supporting record.
- Search filters workflow cards and decision lists. KPI and chart scope follows the explicit tenant/workflow
  selectors; the search tooltip explains the distinction.
- CSV export uses the selected tenant/workflow scope. Rate columns are explicitly percentages. Download
  delivery depends on browser permissions; it is not an alternative route for applying configuration changes.
- Drawers support keyboard focus containment, Escape dismissal and backdrop dismissal. Reduced-motion
  preferences and phone layouts are supported. Empty and unavailable-data states contain no substituted data.

## Data provenance

`GET /api/dashboard` reads a transactionally consistent SQLite snapshot using mode=ro and query_only.
It does not import the simulator, read grader truth, or load scenario YAML. Static HTML/CSS/JS live in
`controller/web/`; `controller/dashboard.py` owns the presentation projection. `GET /api/status` remains
available for backwards-compatible raw controller status.

| Display | Controller source | Definition |
|---|---|---|
| Lead conclusion rate | campaign_created events + leads.concluded | Concluded enrollments from campaigns uploaded during the run / uploaded leads in those campaigns |
| Pickup rate | metrics where dim=all | Connected calls / dials during the run |
| Engagement rate | metrics where dim=all | Engaged calls / connected calls during the run |
| Hallucination flag rate | metrics.hallucinations where dim=all | Automated QA flags / connected calls; not confirmed hallucinations |
| Historical movement | metrics before run start | Absolute percentage-point difference from before-run call history; not causal lift or a no-op baseline |
| Daily trend | hourly metrics grouped by local day | Weighted daily rate, recomputed from counts across selected workflows |
| Arm observations | metrics for actual cohort/dimension/epoch/prompt | Actual calls only; unobserved arms retain zero observations and unknown rates |
| Current allocation | reconciled config snapshot / confirmed proposal receipt | Last recorded configuration; not an estimate of past traffic exposure |
| Approval and application | approval_decided and config_changed events | Remote receipts, including ID and timestamp; a human name is not exposed by this API |
| Post-change evidence | post_apply_verification audit records | Temporal comparison with its uncertainty retained |
| Credits remaining | persisted simulator state | Last ingested balance; uncertain paid operations are highlighted separately |
| Event backlog | persisted state.last_event_id minus committed event checkpoint | Unknown until state exists; never a guessed wall-clock latency |

The new experiment view uses the same cohort ID and evidence snapshot as learning and decay monitoring. Legacy run databases retain their original call-level experiment display. `/metrics` exposes operational counters and the measured cycle latency histogram.

The run start is derived from state.ts minus sim_minute, not a hardcoded calendar date. The displayed finished
period excludes the terminal midnight boundary. Historical-campaign conclusions during the run remain in
call KPIs but are excluded from the uploaded-cohort outcome numerator. This distinction is covered by tests.

Snapshots are cached by committed metadata, audit position and proposal-state counts. A new chunk or decision
invalidates the cache. The load database projection was measured at 8.5 seconds cold and about 3 milliseconds
cached on the development host; these are UI query timings, not controller throughput measurements.
The recent activity response is capped at 1,000 records and the timeline shows up to 100 matching records.
Approval/application detail receipts are fetched independently and are not lost to that display cap.

## Verification

`tests/test_dashboard.py` covers historical-versus-current campaign populations, cohort/dimension deduplication,
unknown rates, unrun arms, cache invalidation, remote receipts outside the recent window, latest confirmed
configuration reconstruction and read-only access. Run all checks with:

```bash
.venv/bin/python -m pytest -q tests
node --check controller/web/dashboard.js
```

Browser QA checked navigation, tenant scoping, chart switching, proposal filtering/details, timeline and
phone overflow. Export download verification was blocked by a declined browser download permission;
no alternate download method was attempted. This is a verification limitation, not a completed export test.
