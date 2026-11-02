# Provera na sezoni (kola 3–9; parametri birani na 3–7, provera na 8–9):
#  A) prilike za skok (promašaji oba tima) i za asistenciju (pogođeni šutevi tima) u odnosu na prosek igračevih utakmica
#  B) nemirne rotacije (koliko trener menja minute) i sigurni starteri vs klupa -> širina raspodele
import json, math, statistics as S
from statistics import NormalDist
exec(open('backtest.py').read().split('# 1) zaboravljanje')[0])
N = NormalDist()
DM, DR, PW = 0.9, 0.9, 30
TIM = {p[0]: p[2] for p in P}
OPP = {}
for r, h, a in json.load(open('raspored.json')): OPP[(h, r)] = a; OPP[(a, r)] = h
T = {}
for r, t, a2, m2, a3, m3, fa, fm, orb, drb, ast, tov in json.load(open('timovi_utakmice.json'))['r']:
    T[(t, r)] = dict(mis=(a2 - m2) + (a3 - m3), fgm=m2 + m3)
def prilike(t, r):   # stvarne prilike u utakmici tima t u kolu r
    o = OPP[(t, r)]; return T[(t, r)]['mis'] + T[(o, r)]['mis'], T[(t, r)]['fgm']
def ocek(t, o, R):   # očekivane prilike za utakmicu t–o u kolu R iz kola pre R
    def avg(f): v = [f(r) for r in range(1, R) if (t, r) in T and (o, r) in T or False]; return v
    tm = [T[(t, r)]['mis'] for r in range(1, R) if (t, r) in T]; om = [T[(o, r)]['mis'] for r in range(1, R) if (o, r) in T]
    t_dop = [T[(OPP[(t, r)], r)]['mis'] for r in range(1, R) if (t, r) in T]   # koliko protivnici promašuju protiv t
    o_dop = [T[(OPP[(o, r)], r)]['mis'] for r in range(1, R) if (o, r) in T]
    tf = [T[(t, r)]['fgm'] for r in range(1, R) if (t, r) in T]; of_ = [T[(OPP[(o, r)], r)]['fgm'] for r in range(1, R) if (o, r) in T]
    reb = (S.mean(tm) + S.mean(o_dop)) / 2 + (S.mean(om) + S.mean(t_dop)) / 2
    return reb, (S.mean(tf) + S.mean(of_)) / 2
# protivnik: koliko dozvoljava po poziciji (po minuti), iz kola pre R — kao u modelu
def dozvoljeno(R):
    A = {}
    for n in G:
        for r, v in G[n].items():
            if r >= R: continue
            o = OPP.get((TIM[n], r))
            if not o: continue
            a = A.setdefault((o, POZ[n]), [0, 0, 0, 0]); a[0] += v[0]
            for i in range(3): a[1 + i] += v[2 + i]
    return A
DOZ = {R: dozvoljeno(R) for R in range(3, 10)}
def lg_rate(R, pos, i):
    m = sum(a[0] for (o, p), a in DOZ[R].items() if p == pos); s = sum(a[1 + i] for (o, p), a in DOZ[R].items() if p == pos)
    return s / m
U = []
for n, R in cilj():
    p = projekcija(n, R, DM, DR, PW)
    t = TIM[n]; o = OPP.get((t, R))
    if not p or not o: continue
    hist = [r for r in G[n] if r < R and (t, r) in T]
    if len(hist) < 2: continue
    hr = S.mean(prilike(t, r)[0] for r in hist); ha = S.mean(prilike(t, r)[1] for r in hist)
    er, ea = ocek(t, o, R)
    of = []
    for i in range(3):
        a = DOZ[R].get((o, POZ[n]))
        if a and a[0] > 100:
            rt = a[1 + i] / a[0]; lr = lg_rate(R, POZ[n], i); w = a[0] / (a[0] + 600)
            of.append(1 + (rt / lr - 1) * w)
        else: of.append(1.0)
    U.append(dict(n=n, R=R, p=p, fr=er / hr, fa=ea / ha, of=of))
def mae(sel, k, i, alpha_of, alpha_ch):
    e = []
    for u in sel:
        mu = u['p'][k] * u['of'][i] ** alpha_of
        if k == 'reb': mu *= u['fr'] ** alpha_ch
        if k == 'ast': mu *= u['fa'] ** alpha_ch
        e.append(abs(G[u['n']][u['R']][2 + i] - mu))
    return S.mean(e)
tr = [u for u in U if u['R'] <= 7]; te = [u for u in U if u['R'] >= 8]
print('uzorak', len(U), '(trening', len(tr), ', provera', len(te), ')')
REZ = {}
for i, k in enumerate(K3):
    b_of = min((mae(tr, k, i, a, 0), a) for a in (0, 0.5, 1.0))[1]
    print(f"{k}: bez protivnika {mae(te, k, i, 0, 0):.3f} | sa protivnikom (a={b_of}) {mae(te, k, i, b_of, 0):.3f}", end='')
    if k in ('reb', 'ast'):
        b_ch = min((mae(tr, k, i, b_of, a), a) for a in (0, 0.5, 1.0, 1.5))[1]
        print(f" | + prilike (b={b_ch}) {mae(te, k, i, b_of, b_ch):.3f}")
        REZ[k] = b_ch
    else: print()

# B) širina: nemirna rotacija tima i klupa
def sd_f(mu, v, c, W):
    av = sum(v) / len(v); sdE = math.sqrt(sum((a - av) ** 2 for a in v) / max(1, len(v) - 1)) if len(v) > 1 else 0
    return math.sqrt((sdE ** 2 * len(v) + (math.sqrt(max(mu, .5)) * c) ** 2 * W) / (len(v) + W))
C = {'pts': 2.2, 'reb': 1.35, 'ast': 1.35}
def nemir(t, R):
    sds = []
    for n in G:
        if TIM[n] != t: continue
        m = [v[0] for r, v in G[n].items() if r < R]
        if len(m) >= 2 and S.mean(m) >= 10: sds.append(S.stdev(m) / S.mean(m))
    return S.mean(sds) if sds else None
NEM = {(t, R): nemir(t, R) for t in set(TIM.values()) for R in range(3, 10)}
LGN = {R: S.mean(v for (t, r), v in NEM.items() if r == R and v) for R in range(3, 10)}
def start_udeo(n, R): s = [v[1] for r, v in G[n].items() if r < R]; return sum(s) / len(s)
def ll(p, y): p = min(max(p, .02), .98); return -math.log(p if y else 1 - p)
OFF = {'pts': (-3, -1, 1, 3), 'reb': (-1, 0, 1), 'ast': (-1, 0, 1)}
def ocena(sel, beta, gam):
    s = m = 0
    for u in sel:
        nm = NEM.get((TIM[u['n']], u['R'])); f = (nm / LGN[u['R']]) ** beta if nm else 1
        if start_udeo(u['n'], u['R']) < 0.5: f *= gam
        for i, k in enumerate(K3):
            mu = u['p'][k]; sd = sd_f(mu, u['p'][k + '_v'], C[k], 16) * f; y = G[u['n']][u['R']][2 + i]
            for o in OFF[k]:
                L = math.floor(mu) + .5 + o
                if L < .5: continue
                s += ll(1 - N.cdf((L - mu) / sd), y > L); m += 1
    return s / m
b = min((ocena(tr, be, ga), be, ga) for be in (0, 0.25, 0.5, 1.0) for ga in (0.95, 1.0, 1.05, 1.1, 1.2))
print(f"širina: bez {ocena(te, 0, 1):.4f} | nemir^{b[1]} i klupa x{b[2]}: {ocena(te, b[1], b[2]):.4f} (provera 8–9)")
json.dump({'prilike': REZ, 'nemir_beta': b[1], 'klupa_sd': b[2]}, open('prilike_param.json', 'w'))
