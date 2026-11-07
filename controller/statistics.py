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

# Precommitted independent-person sample milestones. No extra look is gained by restarting.
MILESTONES = (200,400,800,1600,3200,6400,12800,25600,51200)


def fisher_greater(success_a,n_a,success_b,n_b):
    """Exact one-sided Fisher tail for H0: p_a <= p_b, using stable log probabilities."""
    from math import exp,lgamma,log
    if not n_a or not n_b:
        return 1.
    total = n_a+n_b
    successes = success_a+success_b
    low,high = max(success_a,successes-n_b),min(n_a,successes)
    def logchoose(n,k):
        return lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1)
    logs = [logchoose(n_a,k)+logchoose(n_b,successes-k)-logchoose(total,successes) for k in range(low,high+1)]
    if not logs:
        return 1.
    peak = max(logs)
    return min(1.,exp(peak)*sum(exp(x-peak) for x in logs))


def comparison_alpha(epoch, cohorts, alternatives, purpose='promotion'):
    """Per-workflow family budget: 2% promotion + 2% guardrail + 1% decay.

    Epoch spending 6/(pi^2*j^2) sums to one. Union bound covers cohorts,
    candidate/control comparisons and the finite sample milestones. Between-look
    and between-epoch independence is NOT needed by that union bound.
    """
    from math import pi
    budget = {'promotion':.02,'guardrail':.02,'decay':.01}[purpose]
    return budget*6/(pi*pi*epoch*epoch)/max(1,cohorts)/max(1,alternatives)/len(MILESTONES)


def binomial_bounds(successes,n,alpha):
    """Conservative exact Clopper-Pearson bounds, inverted binomial tails.

    Beta CDF via a continued fraction avoids a SciPy runtime dependency. Bounds
    are for independent people with a stationary Bernoulli marginal in an epoch.
    """
    from math import exp,log,log1p,lgamma
    if not n:
        return 0.,1.
    def fraction(a,b,x):
        qab,qap,qam = a+b,a+1,a-1
        c,d = 1.,1-qab*x/qap
        d = 1/max(1e-300,d)
        h = d
        for m in range(1,301):
            m2 = 2*m
            aa = m*(b-m)*x/((qam+m2)*(a+m2))
            d = 1+aa*d
            if abs(d)<1e-300:d=1e-300
            c = 1+aa/c
            if abs(c)<1e-300:c=1e-300
            d=1/d;h*=d*c
            aa = -(a+m)*(qab+m)*x/((a+m2)*(qap+m2))
            d = 1+aa*d
            if abs(d)<1e-300:d=1e-300
            c = 1+aa/c
            if abs(c)<1e-300:c=1e-300
            d=1/d;delta=d*c;h*=delta
            if abs(delta-1)<1e-12:break
        return h
    def cdf(x,a,b):
        if x<=0:return 0.
        if x>=1:return 1.
        front=exp(lgamma(a+b)-lgamma(a)-lgamma(b)+a*log(x)+b*log1p(-x))
        return front*fraction(a,b,x)/a if x<(a+1)/(a+b+2) else 1-front*fraction(b,a,1-x)/b
    def quantile(p,a,b):
        lo,hi=0.,1.
        for _ in range(60):
            mid=(lo+hi)/2
            if cdf(mid,a,b)<p:lo=mid
            else:hi=mid
        return (lo+hi)/2
    lo=quantile(alpha/2,successes,n-successes+1) if successes else 0.
    hi=quantile(1-alpha/2,successes+1,n-successes) if successes<n else 1.
    return lo,hi


def noninferiority(a,n_a,b,n_b,margin,alpha):
    # Simultaneous bounds on both rates make a lower bound for their difference.
    lo,_=binomial_bounds(a,n_a,alpha/2)
    _,hi=binomial_bounds(b,n_b,alpha/2)
    return lo-hi>=-margin,lo-hi


def binomial_greater(k,n,p):
    """Exact upper binomial tail, stable for the population incident tests."""
    from math import lgamma,log,log1p,exp
    if k<=0:return 1.
    if k>n:return 0.
    logs=[lgamma(n+1)-lgamma(i+1)-lgamma(n-i+1)+i*log(p)+(n-i)*log1p(-p) for i in range(k,n+1)]
    peak=max(logs)
    return min(1.,exp(peak)*sum(exp(v-peak) for v in logs))
