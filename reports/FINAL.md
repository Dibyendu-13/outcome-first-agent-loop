# Submission readiness evidence

All selected-scope technical checks passed. This is an acceptance checklist, not an evaluator score.

| Check | Result |
|---|---|
| Official public_01 through run.sh | Finished, +4.9% relative conclusion rate, no changes graded harmful |
| Official public_02 through run.sh | Finished, +10.1%, no changes graded harmful, 405-minute prompt fix, 15 credits |
| Real-HTTP lifecycle | Approved exploration, promotion, measured deterioration, and approved rollback |
| Subgroup guardrail regression | Rolls back a breaching cohort even while its primary KPI wins |
| Statistical calibration | 3/1,000 primary false-signal families; 0.77% upper bound under stated model |
| Fault matrix | All five SIGKILL cases finished, zero duplicate calls, zero stranded proposals |
| Linux tests | 37 passed under four CPU quota / 8 GiB cap |
| Full official Linux load | 9,737,615 events, 393.3 s/day, integrity ok |
| Controller source boundary | No simulator imports; fixture/grade tooling is separate |
| Read-only console and audit | Shared cohort evidence, proposal receipts, and metrics endpoint |

See `SUBMISSION.md`, `docs/VALIDATION.md`, `reports/LINUX.md`, and the canonical grade reports. Exact
source fingerprints verify the benchmarked algorithms. The non-idempotent paid API cannot recover a lost
receipt; the tested safe behavior is to preserve the uncertainty and alert rather than repeat the charge.

Deliberate cuts: per-person scheduling, factorial interaction models, optimized cross-tenant allocation,
and production authentication/paging. Candidate name and actual human effort should be confirmed before
hand-in. The candidate still owns interview defense; no external submission or grading was performed.
