# Architecture decision records

| ADR | Decision | Rejected alternative and consequence | Revisit trigger |
|---|---|---|---|
| 01 | Python modular controller with SQLite WAL on one evaluation host | Broker and independent services increase operational burden. One writer simplifies checkpoint and audit atomicity. | Measured write or ownership bottleneck in production. |
| 02 | Ordered HTTP contract, durable cursor and idempotent effects | Reading simulator files leaks implementation and makes the controller unusable on hidden worlds. | Contract expands to partitioned or unordered feeds. |
| 03 | Persist effect intent, reconcile remote receipts and enforce base-version CAS | Blind retry can double charge or overwrite supervisor changes. Paid ambiguity can require operator action. | Provider exposes idempotency and receipt lookup. |
| 04 | First-person fixed looks, separate guardrail and designated sentinel | Adaptive unbudgeted comparisons reward noise. Conservative gates reduce power. | Controlled evidence supports a better calibrated method. |
| 05 | Reserve safety attention and keep client controls | Immediate broad auto-apply conflicts with policy and stakeholder constraints. Ordinary changes may wait or lapse. | Evidence of sustained approval backlog and client-approved policy change. |
| 06 | Keep reporting local for evaluation | Hosting adds identity, exposure and availability work. | Operator access requires a tenant-authenticated production surface. |
| 07 | Defer call-time optimization and factorial tests | Sparse and confounded samples make personalization hard to defend. | Enough randomized within-window traffic and measured support. |
