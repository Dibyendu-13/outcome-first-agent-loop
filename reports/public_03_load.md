# Grade report — public_03_load

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.341 | +1.1% | 0.245 | +0.9% | 0.498 | +0.4% | 4% | 391 (409) |
| arav_kyc_1 | 0.386 | +7.5% | 0.229 | +6.3% | 0.597 | -0.6% | 0% | 370 (352) |
| arav_renewal_0 | 0.406 | +0.1% | 0.265 | +0.3% | 0.548 | -0.0% | 0% | 419 (408) |
| kest_cancel_2 | 0.342 | +1.7% | 0.245 | +1.0% | 0.501 | +0.4% | 4% | 392 (418) |
| kest_kyc_1 | 0.405 | +14.0% | 0.239 | +11.7% | 0.598 | +0.2% | 0% | 411 (370) |
| kest_renewal_0 | 0.404 | +0.4% | 0.263 | -0.7% | 0.548 | +0.6% | 0% | 431 (403) |
| nort_cancel_2 | 0.339 | +0.0% | 0.242 | -0.8% | 0.500 | +0.3% | 4% | 357 (368) |
| nort_kyc_1 | 0.405 | +14.0% | 0.240 | +11.5% | 0.596 | +0.1% | 0% | 413 (318) |
| nort_renewal_0 | 0.407 | +0.4% | 0.264 | -0.1% | 0.549 | +0.2% | 0% | 402 (419) |
| tide_cancel_2 | 0.341 | -0.6% | 0.243 | -0.7% | 0.502 | +0.2% | 4% | 388 (401) |
| tide_kyc_1 | 0.403 | +13.1% | 0.238 | +11.0% | 0.596 | -0.3% | 0% | 347 (376) |
| tide_renewal_0 | 0.403 | -0.3% | 0.263 | -0.3% | 0.547 | +0.1% | 0% | 427 (425) |
| ALL | 0.382 | +4.2% | 0.248 | +3.0% | 0.548 | +0.4% | 1% | 4748 (4667) |

## Changes applied by the controller

12 applied — neutral: 8, beneficial: 4

- tide_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- nort_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- kest_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- arav_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- tide_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.110 → **beneficial**
- nort_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- arav_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- tide_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- kest_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- nort_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.131 → **beneficial**
- kest_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.142 → **beneficial**
- arav_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.103 → **beneficial**

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