# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.282 | +19.6% | 0.198 | +9.1% | 0.500 | +7.0% | 30% | 92 (348) |
| nw_kyc | 0.451 | +20.6% | 0.278 | +18.6% | 0.608 | -0.1% | 0% | 29 (29) |
| nw_renewal | 0.422 | -2.6% | 0.263 | +0.2% | 0.537 | -3.1% | -1% | 56 (54) |
| ALL | 0.364 | +10.1% | 0.236 | +7.3% | 0.539 | +1.2% | 11% | 177 (431) |

## Changes applied by the controller

7 applied — neutral: 3, beneficial: 4

- ks_cancel v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['cohorts', 'voice'] engageΔ=-0.009 didΔ=+0.000 → **neutral**
- nw_kyc v2 (controller_approved) dims=['cohorts', 'caller_id'] engageΔ=+0.000 didΔ=+0.110 → **beneficial**
- ks_cancel v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.484 → **beneficial**
- ks_cancel v5 (controller_approved) dims=['prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**
- ks_cancel v6 (controller_approved) dims=['voice'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- nw_renewal v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.030 didΔ=+0.000 → **beneficial**

## Governance

```
{
  "approval_requests": 7,
  "decisions": {
    "approved": 7,
    "expired": 0
  },
  "rejection_reasons": {},
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
      "2": 0.271,
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
    "mttr_minutes": 405,
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
{
  "nw_renewal:welcome_message=W3": {
    "9": 0.165
  }
}
```

Credits used: 15 · validation runs: 3 · LLM fix calls: 1