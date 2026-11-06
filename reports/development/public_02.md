# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.273 | +15.7% | 0.202 | +11.6% | 0.476 | +1.7% | 6% | 377 (348) |
| nw_kyc | 0.476 | +27.3% | 0.303 | +29.4% | 0.588 | -3.4% | 0% | 38 (29) |
| nw_renewal | 0.422 | -2.4% | 0.261 | -0.6% | 0.544 | -1.9% | -4% | 59 (54) |
| ALL | 0.366 | +10.6% | 0.242 | +10.2% | 0.528 | -0.8% | 0% | 474 (431) |

## Changes applied by the controller

6 applied — neutral: 1, harmful: 2, beneficial: 3

- ks_cancel v2 (controller_approved) dims=['voice'] engageΔ=+0.007 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['voice'] engageΔ=-0.018 didΔ=+0.000 → **harmful**
- nw_kyc v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.266 → **beneficial**
- ks_cancel v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.480 → **beneficial**
- ks_cancel v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.016 didΔ=+0.000 → **beneficial**
- nw_renewal v4 (controller_approved) dims=['voice'] engageΔ=-0.043 didΔ=+0.000 → **harmful**

## Governance

```
{
  "approval_requests": 6,
  "decisions": {
    "approved": 6,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 6,
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
[
  {
    "type": "did_flagged",
    "workflow": "ks_cancel",
    "at": "D2 10:00",
    "flagged_did_share_by_day": {
      "2": 0.284,
      "3": 0.0,
      "4": 0.0,
      "5": 0.0,
      "6": 0.0,
      "7": 0.0,
      "8": 0.0,
      "9": 0.0
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D3 11:30",
    "mttr_minutes": null,
    "fixed_by": null
  },
  {
    "type": "supervisor_edit",
    "workflow": "nw_renewal",
    "at": "D5 15:00"
  }
]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0