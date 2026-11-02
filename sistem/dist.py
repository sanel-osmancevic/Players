import math
def nb_cdf(n, mu, sd):
    """P(X <= n) za broj (poeni/skokovi/asistencije) sa prosekom mu i st. devijacijom sd.
    Negativna binomna kad je varijansa > proseka, inače Poisson."""
    if n < 0: return 0.0
    mu = max(mu, 0.05); v = max(sd * sd, mu * 1.0001)
    if v <= mu * 1.02:
        p = math.exp(-mu); c = p
        for k in range(int(n)): p *= mu / (k + 1); c += p
        return min(c, 1.0)
    r = mu * mu / (v - mu); q = r / (r + mu)
    p = q ** r; c = p
    for k in range(int(n)): p *= (k + r) / (k + 1) * (1 - q); c += p
    return min(c, 1.0)
def p_over(L, mu, sd):  # P(X > L) za liniju L (x.5)
    return 1 - nb_cdf(math.floor(L), mu, sd)
