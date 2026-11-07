# Recovery and consistency

With strictly ordered chunk manifests, a single owner and atomic checkpoint commits, replay has effectively-once local effects. Delivery may repeat. Persist immutable receipts, reject ambiguous ordering or missing lead references, and preserve an event-time watermark separately from source sequence. Future late events with newer IDs update their event-time bucket, without rewriting consumed experiment looks. If the API contract permits out-of-order IDs, replace the high-watermark shortcut with an event-ID dedup ledger and acknowledged contiguous chunk order.

| Failure | Recovery | Regression |
|---|---|---|
| Ingest crash | Roll back chunk transaction and fetch again from committed cursor | Kill before commit and compare aggregates |
| Proposal submit crash | Look up stable proposal ID before resending | Kill after accepted submit |
| Apply crash | Read history and approval, commit local receipt once | Kill after remote apply |
| Uncertain timeout | Reconcile by operation type. Read time before advance, hold paid work where no receipt lookup exists | 503 after side effect, disconnect before reply |
| Duplicate event | Unique receipt and no double rollup | Overlapping chunk and replay |
| Late approval | Check remote state and apply deadline, retire expired or lapsed | Approve just outside deadline |
| Supervisor edit | CAS fails or preflight suspends stale intent | Edit between approval and apply |
| Credit exhaustion | Preserve incident and alert, release unspent reservations | Two incidents with one funded budget |
| Database lock | Bounded busy timeout, retry whole transaction, report lag | Hold read snapshot and contend for writer lock |
| Backlog | Bound work per cycle, pause simulation advance until caught up, avoid stale action | Burst manifests, slow network and old watermark |
| Variant degradation | Durable rollback recommendation, revalidate version and route through governance | Primary still wins while guardrail breaches |
| Simultaneous incidents | Severity/deadline queue plus aging and per-tenant caps | Sustained high-priority tenant and waiting second tenant |
| Detection commit crash | One transaction for look, incident and evidence | Kill between detection and dispatch |

At boot acquire ownership before opening write state, verify world identity, validate cursor, replay and reconcile before dispatch. Preserve SQLite and WAL on disk failure. For production use verified backups and restore drills. Remote exactly-once charge recovery requires provider idempotency plus lookup. With the present contract a lost response remains uncertain.
