# Grade report — public_01_dev

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.355 | +4.1% | 0.244 | -0.4% | 0.512 | +4.0% | 7% | 64 (57) |
| nw_kyc | 0.424 | +15.6% | 0.283 | +17.0% | 0.586 | -1.9% | 0% | 25 (21) |
| nw_renewal | 0.416 | -0.1% | 0.262 | -0.9% | 0.544 | +0.5% | 0% | 50 (54) |
| ALL | 0.390 | +4.9% | 0.257 | +2.6% | 0.539 | +1.7% | 2% | 139 (132) |

## Changes applied by the controller

3 applied — beneficial: 2, neutral: 1

- ks_cancel v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.011 didΔ=+0.000 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['cohorts', 'caller_id'] engageΔ=+0.000 didΔ=+0.141 → **beneficial**
- nw_renewal v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**

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