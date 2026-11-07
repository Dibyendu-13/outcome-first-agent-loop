"""Reproducible statistical calibration; never a source of controller decisions."""
import json
from pathlib import Path
import sys
from math import ceil
from functools import lru_cache
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from controller.statistics import MILESTONES,binomial_bounds,comparison_alpha,fisher_greater,noninferiority


def main():
    rng=np.random.default_rng(20261107)
    families=1000;false=0;powered=0
    @lru_cache(maxsize=50000)
    def pvalue(a,b,n):return fisher_greater(a,n,b,n)
    for _ in range(families):
        discovered=False
        # Multiple cohorts, epochs, candidates and nested fixed-prefix looks under the global null.
        for epoch in (1,2):
            for cohort in range(2):
                control=rng.binomial(1,.5,800)
                for candidate in range(2):
                    arm=rng.binomial(1,.5,800)
                    alpha=comparison_alpha(epoch,2,2)
                    if any(pvalue(int(arm[:n].sum()),int(control[:n].sum()),n)<=alpha for n in (200,400,800)):
                        discovered=True
        false+=discovered
        a=rng.binomial(1,.7,800);b=rng.binomial(1,.5,800)
        powered+=any(pvalue(int(a[:n].sum()),int(b[:n].sum()),n)<=comparison_alpha(1,2,2) for n in (200,400,800))
    upper=binomial_bounds(false,families,.1)[1] # 95% one-sided upper bound.
    power=[]
    for n in (400,1600,6400,25600,51200):
        primary_p=fisher_greater(round(.65*n),n,round(.5*n),n)
        guard_pass,lower=noninferiority(round(.25*n),n,round(.25*n),n,.02,.5*comparison_alpha(1,3,3,'guardrail'))
        power.append(dict(n_per_arm=n,primary_p_for_15pp_lift=primary_p,primary_pass=primary_p<=comparison_alpha(1,3,3),
            guardrail_equal_rates_pass=guard_pass,guardrail_lower_difference=lower))
    report=dict(seed=20261107,null_families=families,cohorts=2,epochs=2,alternatives=2,
        tested_milestones=[200,400,800],declared_milestones=list(MILESTONES),false_primary_discovery_families=false,
        empirical_false_primary_family_rate=false/families,one_sided_95pct_upper_bound=upper,
        primary_power_for_20pp_lift_by_800=powered/families,power_grid=power,
        analytical_budget_per_workflow=dict(promotion=.02,guardrail=.02,decay=.01,total=.05),
        assumptions=['First observation per independent person within an epoch','Stationary exchangeable Bernoulli marginal within each compared epoch/cohort',
        'Fixed event-ID sample prefixes at predeclared sizes','No between-epoch independence needed for the union bound'],
        limitations=['The measured false-discovery count is for the primary test family before guardrails, not an observed unsafe-configuration rate.',
        'Calibration exercises the first three of nine looks and two epochs; the analytic union bound covers the declared family.',
        'It is not evidence of model-free validity under arbitrary within-epoch temporal or selection drift.',
        'The exact guardrail is intentionally conservative: unchanged 2pp guardrails need many observations.'])
    Path('reports/statistical-calibration.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
