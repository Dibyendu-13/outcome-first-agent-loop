# Evaluation evidence

- `FINAL.md`: technical acceptance checklist and its limits.
- `public_01.md` and `public_02.md`: final official grade reports from `final_public_01` and `final_public_02`. The corresponding metrics and original run transcripts are included.
- `public_02-recovery.json`: SIGKILL and restart while an official public_02 proposal was pending.
- `public_03_load.md`, `public_03_load-metrics.json`, and `LINUX.md`: final five-day load evaluation, timing definitions, and machine limits. `linux-environment.json` records the source hashes and cgroup limits.
- `complete-tests.txt` and `linux-submission-validation.log`: final test output on macOS and Linux.
- `fault-matrix.json` and `fault_*`: the five actual crash and restart cases.
- `learning-cycle-proof.json`: real HTTP contract fixture showing exploration, promotion, and rollback. It does not represent an official scenario score.
- `statistical-calibration.json`: empirical primary-test calibration under the documented model.
- `audit-example.json` and `supervisor-example.json`: evidence and console data from final public_02.
- `development/`: earlier iterations, including failed or interrupted runs. `release_01-*` and `release_02-*` are earlier public runs.

The grader reads simulator output for external evaluation. The controller consumes only HTTP.
Raw run directories and databases are kept locally and ignored by git. See `docs/VALIDATION.md`
for reproduction commands. Relative KPI changes in official grade tables are distinct from
percentage-point changes.

`ui-verification.md`, `ui-overview.jpg`, and `ui-mobile.jpg` document the original browser checks
and screenshots on the earlier release_02 dataset. See `docs/UI.md` for final launch and data definitions.
