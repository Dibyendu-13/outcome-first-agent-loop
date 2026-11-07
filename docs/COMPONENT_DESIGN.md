# Component contracts

These are module boundaries inside the controller unless indicated. Interfaces name intended inputs and outputs. Persisted outputs cross module boundaries by identifier and event watermark.

| Module | Responsibility, inputs → outputs | Ownership, dependencies and recovery |
|---|---|---|
| Orchestrator | HTTP state and watermark → bounded cycle | Owns run identity and advance intent. Depends on ingest and dispatcher. Reread remote time after uncertain advance. |
| HTTP client | Typed operation and payload → receipt or classified error | Owns connection pool and timeouts. Retries reads with jitter. Mutations reconcile through dispatcher. |
| Ingest | Manifest and NDJSON → committed watermark | Owns chunk receipt with store. Replays on disconnect, stops on invalid order or unresolved references. |
| State store | Transaction and expected versions → commit | Owns migrations, WAL and snapshot reads. Short busy timeout and bounded retries. Disk failure stops mutations and advance. |
| Feature and cohort | Lead features and ordered definitions → cohort ID | Owns versioned rules. Call receipts preserve remote attribution. Missing dimensions go to validated fallback or quarantine. |
| KPI and drift | Call receipts → numerator, denominator and time windows | Owns rebuildable rollups. Reprocess late events by event time under explicit watermark rules. |
| Experiment planner | Config, eligible population and exposure budget → plan | Owns epoch and legal allocation. Simulator assigns per dial. Wait on approval or low eligible volume. |
| Statistics | Epoch-specific first observations → immutable look | Owns test version, alpha and effect estimate. Replaying same prefix yields same decision. |
| Caller health | DID, cohort, time and version strata → candidate rotation | Owns health evidence. Insufficient alternatives yields observation and escalation. |
| Call-time optimization | Eligible hours and randomized cohort outcomes → schedule recommendation | Deferred. Preserve all business hours and capacity. Reject schedules lacking support or that zero eligible capacity. |
| Incident handler | QA evidence → severity, durable incident and remediation | Owns incident episode. Detector stays active during pending approvals. Reconcile edits and verify afterward. |
| Suggestion and validation | Incident and reserved credits → candidate receipts | Owns provider adapter. Unknown paid reply is held and escalated. Safety receipts describe their sample. |
| Governance | Recommendation and policy → proposal or deferred reason | Owns TTL, request count and approval status. Reconcile by stable proposal ID. |
| Application and rollback | Approval or legal auto-apply plus base version → applied receipt | Owns effect dispatch and version CAS. Recover from history. A rollback is a new governed patch. |
| Audit | Evidence, policy and receipts → immutable timeline | Owns linkable IDs and decision versions. Written in the same transaction as the corresponding local transition. |
| Supervisor | Snapshot queries → status and why views | Separate localhost reader. Production tenant authorization and redaction sit here. On contention return last-known freshness or 503. |
| Observability and budget | Queue, lag and provider balance → metrics and reservation | Owns reservations, severity and alert dedup. Reconcile balance before spending and preserve uncertain charges. |
