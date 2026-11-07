# Grade report — public_03_load

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.345 | +2.4% | 0.244 | +0.4% | 0.504 | +1.6% | 7% | 385 (409) |
| arav_kyc_1 | 0.403 | +12.4% | 0.238 | +10.8% | 0.596 | -0.7% | 0% | 402 (352) |
| arav_renewal_0 | 0.401 | -1.0% | 0.263 | -0.3% | 0.545 | -0.5% | 0% | 403 (408) |
| kest_cancel_2 | 0.340 | +1.0% | 0.243 | +0.4% | 0.500 | +0.1% | 7% | 411 (418) |
| kest_kyc_1 | 0.408 | +14.6% | 0.240 | +12.0% | 0.598 | +0.1% | 0% | 375 (370) |
| kest_renewal_0 | 0.405 | +0.6% | 0.264 | -0.1% | 0.548 | +0.6% | 0% | 406 (403) |
| nort_cancel_2 | 0.341 | +0.6% | 0.243 | -0.6% | 0.502 | +0.8% | 7% | 405 (368) |
| nort_kyc_1 | 0.406 | +14.1% | 0.241 | +11.8% | 0.595 | -0.2% | 0% | 384 (318) |
| nort_renewal_0 | 0.404 | -0.4% | 0.264 | +0.0% | 0.546 | -0.3% | 0% | 430 (419) |
| tide_cancel_2 | 0.342 | -0.3% | 0.244 | -0.1% | 0.501 | +0.0% | 7% | 376 (401) |
| tide_kyc_1 | 0.432 | +21.3% | 0.253 | +17.6% | 0.597 | -0.3% | 0% | 439 (376) |
| tide_renewal_0 | 0.405 | +0.0% | 0.265 | +0.2% | 0.546 | +0.1% | 0% | 421 (425) |
| ALL | 0.386 | +5.3% | 0.250 | +3.9% | 0.548 | +0.5% | 2% | 4837 (4667) |

## Changes applied by the controller

12 applied — beneficial: 8, neutral: 4

- tide_cancel_2 v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.011 didΔ=+0.000 → **beneficial**
- nort_cancel_2 v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.011 didΔ=+0.000 → **beneficial**
- tide_renewal_0 v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- arav_renewal_0 v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- arav_cancel_2 v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.011 didΔ=+0.000 → **beneficial**
- kest_cancel_2 v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.011 didΔ=+0.000 → **beneficial**
- nort_renewal_0 v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- kest_renewal_0 v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- tide_kyc_1 v2 (controller_approved) dims=['cohorts', 'caller_id'] engageΔ=+0.000 didΔ=+0.214 → **beneficial**
- nort_kyc_1 v2 (controller_approved) dims=['cohorts', 'caller_id'] engageΔ=+0.000 didΔ=+0.165 → **beneficial**
- kest_kyc_1 v2 (controller_approved) dims=['cohorts', 'caller_id'] engageΔ=+0.000 didΔ=+0.165 → **beneficial**
- arav_kyc_1 v2 (controller_approved) dims=['cohorts', 'caller_id'] engageΔ=+0.000 didΔ=+0.165 → **beneficial**

## Governance

```
{
  "approval_requests": 12,
  "decisions": {
    "approved": 12,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 12,
  "auto_applied": 0,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "tide_cancel_2": 1,
    "nort_renewal_0": 1,
    "nort_kyc_1": 1,
    "nort_cancel_2": 1,
    "kest_renewal_0": 1,
    "kest_kyc_1": 1,
    "kest_cancel_2": 1,
    "arav_renewal_0": 1,
    "arav_kyc_1": 1,
    "arav_cancel_2": 1,
    "tide_renewal_0": 1,
    "tide_kyc_1": 1
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