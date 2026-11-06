# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.291 | +23.5% | 0.201 | +10.7% | 0.508 | +8.6% | 44% | 67 (348) |
| nw_kyc | 0.491 | +31.4% | 0.306 | +30.6% | 0.600 | -1.4% | 0% | 37 (29) |
| nw_renewal | 0.430 | -0.6% | 0.265 | +0.9% | 0.545 | -1.7% | -2% | 68 (54) |
| ALL | 0.380 | +14.9% | 0.243 | +10.8% | 0.544 | +2.2% | 16% | 172 (431) |

## Changes applied by the controller

7 applied — neutral: 1, harmful: 2, beneficial: 4

- ks_cancel v2 (controller_approved) dims=['voice'] engageΔ=+0.007 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['voice'] engageΔ=-0.018 didΔ=+0.000 → **harmful**
- nw_kyc v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.266 → **beneficial**
- ks_cancel v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.480 → **beneficial**
- ks_cancel v5 (controller_approved) dims=['prompt_version'] engageΔ=+0.137 didΔ=+0.000 → **beneficial**
- ks_cancel v6 (controller_approved) dims=['welcome_message'] engageΔ=+0.016 didΔ=+0.000 → **beneficial**
- nw_renewal v4 (controller_approved) dims=['voice'] engageΔ=-0.043 didΔ=+0.000 → **harmful**

## Governance

```
{
  "approval_requests": 9,
  "decisions": {
    "approved": 7,
    "rejected": 2,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 2
  },
  "applied_via_approval": 7,
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
    "mttr_minutes": 270,
    "fixed_by": "controller_approved"
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

Credits used: 15 · validation runs: 3 · LLM fix calls: 1