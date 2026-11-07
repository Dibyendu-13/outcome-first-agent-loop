# Supervisor console verification

## Automated checks

- 20 tests pass: six existing simulator tests, eight controller tests, six UI projection tests.
- JavaScript syntax verified with `node --check controller/web/dashboard.js`.
- Projection tests verify campaign-cohort conclusion denominators, inclusion of all actual call cohorts,
  exclusion of diagnostic double counting, unknown rates, unrun arms, cache invalidation, remote approval
  receipts outside the recent-activity cap, current configuration reconstruction, and read-only DB access.

## Browser checks against the actual release_02 database

- Overview displayed 11,994 concluded / 33,000 uploaded (36.3%).
- Kestrel-only scope displayed 4,225 / 15,000 (28.2%); trend and workflow cards followed the same selection.
- Pickup and engagement chart toggle switched actual daily observations.
- Rejected proposal filter showed apr_00004, its real judgement-call rejection, and the D1/D2 distribution diff.
- Proposal drawer showed actual approval/application receipts and evidence, with keyboard dismissal.
- Completed-run experiments displayed 'Ended · no promotion' and actual sample counts; unrun arms were not
  assigned invented observations or winners.
- Timeline sorted by simulated timestamp, initially hid routine evaluations, and linked proposals.
- Phone viewport at 390 × 844 had document width 390 (no horizontal page overflow). The temporary viewport
  was reset afterward. Mobile navigation labels fit the available width.
- Desktop overview and phone screenshots are saved as ui-overview.jpg and ui-mobile.jpg.
- No page JavaScript errors were reported in the final desktop browser check.

## Verification limit

The browser declined permission for the export download during QA. It was not retried and no alternative
method was used to obtain the same exported file. The export control and percent-labelled CSV serialization
are implemented, but successful delivery of the downloaded CSV has not been verified in this browser.

## Data provenance and scope

All presentation data comes from the controller SQLite database through /api/dashboard. No scenario truth,
grader baseline, fabricated time series, synthetic lift, or inferred human approver name is used. Historical
comparisons are explicitly before-run references, not no-op control results. QA flags are not represented
as confirmed hallucinations. The console remains read-only and does not bypass controller governance.

The separate 12-workflow load database projection was measured at 8.5 seconds cold and approximately 3ms
cached on this host. This measures the UI projection, not controller event-ingestion throughput.

## Final data and metrics smoke check

The latest local server was started against `controller-data/final_public_02.sqlite`. The page,
`GET /api/dashboard`, and `GET /metrics` each returned HTTP 200. The dashboard response included
workflow, experiment, incident, proposal, and ingestion records. The metrics response exposed
the decision-cycle histogram, remaining credits, and ingestion backlog. The updated JavaScript
passed `node --check`. The screenshots above remain from the earlier release dataset.
