"""Deterministic fixed-horizon tests; no model participates in winner selection."""
from math import sqrt


def rate(s, metric):
    if metric == 'pickup':
        return s['connected']/s['dials'] if s['dials'] else 0
    return s['engaged']/s['connected'] if s['connected'] else 0


def interval(s, metric, z=3.5):
    n = s['dials'] if metric=='pickup' else s['connected']
    if not n:
        return 0.,1.
    p = rate(s,metric)
    den = 1+z*z/n
    center = (p+z*z/(2*n))/den
    half = z*sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0,center-half),min(1,center+half)


def winner(stats, primary, minimum=400):
    """Simultaneous Wilson intervals, conservative z=3.5 (<=10 arms)."""
    if len(stats)<2 or any(s['connected']<minimum for s in stats.values()):
        return None
    best = max(sorted(stats),key=lambda k:rate(stats[k],primary))
    lo,_ = interval(stats[best],primary)
    if all(lo>interval(s,primary)[1] for k,s in stats.items() if k!=best):
        return best
    return None


def guardrail_ok(candidate, baseline, metric, floor):
    lo,_ = interval(candidate,metric)
    return lo>=floor and lo>=rate(baseline,metric)-.03
