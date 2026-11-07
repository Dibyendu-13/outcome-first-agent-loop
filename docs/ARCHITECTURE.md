# Proposed architecture

One process runs bounded ingestion, pure evaluators, arbitration and an effect dispatcher. SQLite is the durable boundary. The read-only UI is a separate local process. The simulator owns assignments, time, policy and approvals.

```mermaid
flowchart LR
    S[Simulator HTTP API] --> I[Ingestion]
    I --> D[(SQLite)]
    D --> E[Deterministic evaluators]
    E --> A[Arbiter]
    A --> D
    D --> G[Governance and effect dispatcher]
    G --> S
    D --> U[Read-only supervisor UI]
```

```mermaid
flowchart LR
    M[Ordered manifests] --> N[Bounded NDJSON stream]
    N --> V[Validate IDs and references]
    V --> T[Single chunk transaction]
    T --> F[Persist facts and update projections]
    F --> C[Commit chunk receipt and cursor]
    C --> R[Publish evaluation watermark]
```

```mermaid
stateDiagram-v2
    [*] --> Planned
    Planned --> AwaitingApproval
    AwaitingApproval --> Exploring: applied
    AwaitingApproval --> Suspended: closed or stale
    Exploring --> PromotionPending: primary and guardrail pass
    Exploring --> Suspended: version changes
    PromotionPending --> Monitoring: applied
    PromotionPending --> Exploring: declined with fresh look required
    Monitoring --> RollbackPending: material deterioration
    RollbackPending --> RolledBack: approved and applied
    RollbackPending --> Suspended: supervisor edit
```

```mermaid
sequenceDiagram
    participant D as Dispatcher
    participant DB as SQLite
    participant S as Simulator
    D->>DB: Commit proposal intent and base version
    D->>S: POST /approvals with proposal ID
    S-->>D: Approval ID
    D->>S: Read approval and current version
    alt Approved, within deadline and same version
        D->>S: POST apply with approval ID
        D->>S: Verify config history on uncertain reply
        D->>DB: Commit application receipt and monitor
    else Stale, expired or lapsed
        D->>DB: Close intent and require fresh evidence
    end
```

```mermaid
flowchart LR
    F[QA flags for fixed population] --> D[Persist significant look and incident]
    D --> B[Reserve bounded credits]
    B --> S[Suggest candidates]
    S --> V[Validate safety]
    V --> A[Request approval]
    A --> P[Apply and observe KPIs and flags]
    V --> X[Escalate when no safe candidate]
    P --> R[Governed rollback or escalate]
```

```mermaid
flowchart LR
    B[Restart and acquire owner lock] --> R[Read durable cursor and intents]
    R --> I[Replay uncommitted chunks]
    I --> H[Read approvals and version history]
    H --> M[Resolve known mutations]
    H --> U[Hold unknown paid operations]
    M --> E[Resume evaluation]
```

```mermaid
flowchart LR
    O[Observed calls] --> K[Versioned cohort and separate KPI windows]
    K --> L[Predeclared population test]
    L --> A[Arbitrate safety and policy]
    A --> Q[Commit recommendation and rationale]
    Q --> G[Governance dispatch]
    G --> V[Verify actual exposure]
    V --> K
```

The [entity diagram](DATA_MODEL.md) completes the eight views.
