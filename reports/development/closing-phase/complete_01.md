# Grade report — public_01_dev

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.349 | +2.1% | 0.244 | -0.4% | 0.500 | +1.6% | 7% | 69 (57) |
| nw_kyc | 0.439 | +19.8% | 0.288 | +18.9% | 0.595 | -0.4% | 0% | 30 (21) |
| nw_renewal | 0.423 | +1.7% | 0.266 | +0.7% | 0.543 | +0.2% | 0% | 62 (54) |
| ALL | 0.393 | +5.7% | 0.260 | +3.6% | 0.535 | +1.1% | 2% | 161 (132) |

## Changes applied by the controller

3 applied — beneficial: 2, neutral: 1

- ks_cancel v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.011 didΔ=+0.000 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['cohorts', 'caller_id'] engageΔ=+0.000 didΔ=+0.150 → **beneficial**
- nw_renewal v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 4,
  "decisions": {
    "approved": 3,
    "rejected": 1,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 1
  },
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