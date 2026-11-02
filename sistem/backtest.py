# Provera modela na celoj sezoni (kola 1–9), "vraćanjem vremena": za svako kolo R (3..9) projekcije samo iz kola pre R,
# pa poređenje sa stvarnim učinkom. Podešava: zaboravljanje starih utakmica (minuti i učinak po minuti), težinu proseka lige,
# i raspodelu (širinu) po kategoriji i po igraču. Piše model_param.json i sd_igraci.json.
import json, math, itertools, statistics as S
from statistics import NormalDist
N = NormalDist()
P = [p for f in ('data9.json', 'data9b.json', 'data9c.json') for p in json.load(open(f))['P']]
D9 = json.load(open('data9.json'))
K3 = ('pts', 'reb', 'ast')
G = {}   # (ime) -> {kolo: (min, start, pts, reb, ast)}
POZ = {}
for n, pos, t, rr, mm, ss, vp, vr, va in P:
    POZ[n] = pos
    for r, m, s, a, b, c in zip(rr.split(','), mm.split(','), ss, vp.split(','), vr.split(','), va.split(',')):
        G.setdefault(n, {})[int(r)] = (float(m), int(s), int(a), int(b), int(c))
for f in ('results_cet.json', 'results_pet.json'):   # kolo 9
    for n, m, p, r, a in json.load(open(f)):
        if n in G and m > 0: G[n][9] = (float(m), 0, p, r, a)
# prosek lige po poziciji (po 40 min) iz kola 1–8 — kao u modelu
lg = {}
for t, pos, n, *v in D9['posAllow']:
    for k, x in zip(K3, v): lg.setdefault((pos, k), []).append(x)
LG = {k: sum(v) / len(v) / 40 for k, v in lg.items()}

def projekcija(n, R, dm, dr, pw):
    h = {r: v for r, v in G[n].items() if r < R}
    if len(h) < 2: return None
    rr = sorted(h)
    wm = [dm ** (R - 1 - r) for r in rr]; wr = [dr ** (R - 1 - r) for r in rr]
    mp = sum(w * h[r][0] for w, r in zip(wm, rr)) / sum(wm)
    M = sum(w * h[r][0] for w, r in zip(wr, rr))
    out = {'min': mp}
    for i, k in enumerate(K3):
        rate = (sum(w * h[r][2 + i] for w, r in zip(wr, rr)) + LG[(POZ[n], k)] * pw) / (M + pw)
        out[k] = rate * mp
        v = [h[r][2 + i] for r in rr]
        out[k + '_v'] = v
    return out

def cilj():
    for n in G:
        for R in range(3, 10):
            if R in G[n]: yield n, R

# 1) zaboravljanje i težina proseka lige: greška minuta i projekcija
rez = []
for dm, dr, pw in itertools.product([0.7, 0.8, 0.85, 0.9, 1.0], [0.7, 0.8, 0.85, 0.9, 1.0], [5, 15, 30, 60]):
    em = []; ek = {k: [] for k in K3}
    for n, R in cilj():
        p = projekcija(n, R, dm, dr, pw)
        if not p: continue
        a = G[n][R]
        em.append(abs(a[0] - p['min']))
        for i, k in enumerate(K3): ek[k].append(abs(a[2 + i] - p[k]))
    rez.append((dm, dr, pw, S.mean(em), {k: S.mean(v) for k, v in ek.items()}, len(em)))
staro = next(r for r in rez if r[0] == 0.85 and r[1] == 0.85 and r[2] == 15)
skor = lambda r: r[4]['pts'] / staro[4]['pts'] + r[4]['reb'] / staro[4]['reb'] + r[4]['ast'] / staro[4]['ast']
best = min(rez, key=skor)
bm = min(rez, key=lambda r: r[3])
print(f"uzorak: {staro[5]} igrač-utakmica (kola 3–9)")
print(f"sadašnje (0.85/0.85/15): minuti {staro[3]:.2f}  poeni {staro[4]['pts']:.2f}  skokovi {staro[4]['reb']:.2f}  asist {staro[4]['ast']:.2f}")
print(f"najbolje za učinak (dm={best[0]}, dr={best[1]}, pw={best[2]}): minuti {best[3]:.2f}  poeni {best[4]['pts']:.2f}  skokovi {best[4]['reb']:.2f}  asist {best[4]['ast']:.2f}")
print(f"najbolje samo za minute: dm={bm[0]} -> {bm[3]:.2f}")
DM, DR, PW = best[0], best[1], best[2]

# 2) raspodela: širina = mešavina rasipanja igrača (sdE) i osnovne sqrt(mu)*c, težina osnovne W; plus ocena po igraču
def sd_f(mu, v, c, W):
    av = sum(v) / len(v); sdE = math.sqrt(sum((a - av) ** 2 for a in v) / max(1, len(v) - 1)) if len(v) > 1 else 0
    sdB = math.sqrt(max(mu, 0.5)) * c
    return math.sqrt((sdE ** 2 * len(v) + sdB ** 2 * W) / (len(v) + W))
def ll(p, y): p = min(max(p, 0.02), 0.98); return -math.log(p if y else 1 - p)
OFF = {'pts': (-3, -1, 1, 3), 'reb': (-1, 0, 1), 'ast': (-1, 0, 1)}
uzorak = []
for n, R in cilj():
    p = projekcija(n, R, DM, DR, PW)
    if p: uzorak.append((n, R, p))
par_sd = {}
for i, k in enumerate(K3):
    def ocena(c, W, mult=None):
        s = 0; m = 0
        for n, R, p in uzorak:
            mu = p[k]; sd = sd_f(mu, p[k + '_v'], c, W) * (mult.get(n, 1) if mult else 1); y = G[n][R][2 + i]
            for o in OFF[k]:
                L = math.floor(mu) + 0.5 + o
                if L < 0.5: continue
                s += ll(1 - N.cdf((L - mu) / sd), y > L); m += 1
        return s / m
    sadasnje = ocena(2.0 if k == 'pts' else 1.35, 4)
    mreza = [(ocena(c, W), c, W) for c in ([1.4, 1.7, 2.0, 2.3, 2.6] if k == 'pts' else [0.9, 1.1, 1.35, 1.6, 1.9]) for W in (2, 4, 8, 16)]
    b = min(mreza)
    par_sd[k] = {'c': b[1], 'W': b[2]}
    print(f"{k}: širina sadašnja {sadasnje:.4f} -> najbolja {b[0]:.4f} (c={b[1]}, W={b[2]})")
# 3) širina po igraču: odnos stvarnih odstupanja i predviđene širine, skupljeno ka 1 (K=6 utakmica)
mult = {}
for n in G:
    z2 = []
    for n2, R, p in uzorak:
        if n2 != n: continue
        for i, k in enumerate(K3):
            sd = sd_f(p[k], p[k + '_v'], par_sd[k]['c'], par_sd[k]['W'])
            z2.append(((G[n][R][2 + i] - p[k]) / sd) ** 2)
    if z2:
        r = math.sqrt((sum(z2) + 6 * 3) / (len(z2) + 6 * 3))   # prior: 6 utakmica x 3 kategorije sa odnosom 1
        mult[n] = round(min(1.3, max(0.8, r)), 3)
tot = {}
for i, k in enumerate(K3):
    s0 = s1 = m = 0
    for n, R, p in uzorak:
        mu = p[k]; y = G[n][R][2 + i]
        sd0 = sd_f(mu, p[k + '_v'], par_sd[k]['c'], par_sd[k]['W']); sd1 = sd0 * mult.get(n, 1)
        for o in OFF[k]:
            L = math.floor(mu) + 0.5 + o
            if L < 0.5: continue
            s0 += ll(1 - N.cdf((L - mu) / sd0), y > L); s1 += ll(1 - N.cdf((L - mu) / sd1), y > L); m += 1
    tot[k] = (s0 / m, s1 / m)
    print(f"{k}: sa širinom po igraču {tot[k][0]:.4f} -> {tot[k][1]:.4f}  (napomena: ocenjeno na istom uzorku, realno manje)")
json.dump({'dm': DM, 'dr': DR, 'pw': PW, 'sd': par_sd, 'uzorak': staro[5],
           'greska_staro': {'min': round(staro[3], 2), **{k: round(v, 2) for k, v in staro[4].items()}},
           'greska_novo': {'min': round(best[3], 2), **{k: round(v, 2) for k, v in best[4].items()}}}, open('model_param.json', 'w'), indent=1)
json.dump(mult, open('sd_igraci.json', 'w'), ensure_ascii=False)
print('upisano model_param.json, sd_igraci.json; igrača sa širinom:', len(mult),
      '| najrasipaniji:', sorted(mult.items(), key=lambda x: -x[1])[:4], '| najstabilniji:', sorted(mult.items(), key=lambda x: x[1])[:4])
