# Grade report — public_01_dev

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.355 | +3.9% | 0.246 | +0.4% | 0.504 | +2.5% | 4% | 46 (57) |
| nw_kyc | 0.405 | +10.4% | 0.268 | +10.6% | 0.595 | -0.3% | 0% | 30 (21) |
| nw_renewal | 0.404 | -2.9% | 0.259 | -2.0% | 0.538 | -0.7% | 0% | 39 (54) |
| ALL | 0.382 | +2.7% | 0.254 | +1.4% | 0.534 | +0.9% | 2% | 115 (132) |

## Changes applied by the controller

3 applied — neutral: 2, beneficial: 1

- ks_cancel v2 (controller_approved) dims=['voice'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- nw_kyc v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.080 → **beneficial**

## Governance

```
{
  "approval_requests": 3,
  "decisions": {
    "approved": 3,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 3,
  "auto_applied": 0,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "ks_cancel": 1,
    "nw_renewal": 1,
    "nw_kyc": 1
  }
}
```

## Incidents

```
[]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0