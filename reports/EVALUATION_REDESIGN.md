# Evaluation redesign verification

The evaluation controller keeps one HTTP-driven Python process and SQLite writer. The redesigned flow now saves prompt incident detection atomically, holds ordinary approved changes during active prompt incidents, retains deferred rollback evidence, reserves the full sentinel allocation for the original control, forecasts monitoring windows from observed traffic, scopes caller-ID rotation to cohorts with evidence, and persists bounded tenant incident credit reservations.

| Check | Fresh evidence |
|---|---|
| Local and capped Linux tests | 42 passed in each environment |
| Official public_01 | +4.9% relative conclusion rate, three applied, none graded harmful |
| Official public_02 | +10.2% relative conclusion rate, seven applied, none graded harmful, prompt fix in 270 simulated minutes, 169 hallucinated calls versus 431 baseline |
| Public_02 restart | SIGKILL with an approval pending, finished with clean integrity and no duplicate calls or pending approvals |
| Five crash boundaries | All completed and reconciled, with one uncertain paid receipt and one operator alert in the paid case |
| HTTP learning fixture | Approved exploration, promotion and guardrail rollback |
| Capped Linux public_03 | Passed. 9,737,615 events at 492.3 seconds per simulated day against a 600-second target. +5.3% relative conclusion rate, zero changes graded harmful, clean integrity, zero duplicate calls and zero pending approvals. |

[Public 01](parity-01.md) · [Public 02](parity-02.md) · [Restart](parity-02-recovery.json) · [Fault matrix](parity-fault-matrix.json) · [Learning fixture](parity-learning.json) · [Linux grade](parity_load.md) · [Linux metrics](parity_load-metrics.json) · [Linux validation log](parity-linux-validation.log)

The monitor duration is a forecast, bounded to 3–24 hours. Quiet cohorts can still abstain. The credit allocator uses oldest detected incident first, rotating ties and one outstanding hold per tenant. It does not assign production quotas. Caller-ID screening uses observed cohort IDs and current-version recent exposure. Historical and current population composition may still differ.
