# Provera formule šanse na linijama sa rezultatom (evidencija.json, glavne linije sa obe kvote). Ništa ne upisuje.
# Upotreba: py -X utf8 bt_formula.py
# Delovi: model (sa naučenim pomerajem i širinom), istorija (ova sezona), tržište (ostale kladionice bez marže) i spoj kao u preporukama.
import math, random, json
from pomocno import citaj
Phi = lambda z: .5 * (1 + math.erf(z / math.sqrt(2)))
T = citaj('tezine.json'); BIAS = T['bias']; C = T.get('c', 1.0); K = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}
W0 = (.272, .128, .6)
E = [e for e in citaj('evidencija.json') if e.get('proslo_vise') in (True, False) and e.get('kvota_manje') and e.get('kvota_vise') and e.get('trz_vise') is not None]
def pm(e, bias=True, c=C):
    mu = e['proj'] + (BIAS.get(K[e['kategorija']], 0) if bias else 0)
    return min(.999, max(.001, 1 - Phi((math.floor(e['linija']) + .5 - mu) / (e['sd'] * c))))
def ph(e):
    h, n = map(int, e['ist_vise'].split('/')); return (h + 1) / (n + 2)
def pt(e): return min(.999, max(.001, e['trz_vise']))
def mb(e):   # Maxbet bez marže
    a, b = 1 / e['kvota_vise'], 1 / e['kvota_manje']; return a / (a + b)
def spoj(e, w=W0): return w[0] * pm(e) + w[1] * ph(e) + w[2] * pt(e)
y = lambda e: 1.0 if e['proslo_vise'] else 0.0
ll = lambda p, o: -(o * math.log(p) + (1 - o) * math.log(1 - p))
def ocena(ime, f, S):
    p = [f(e) for e in S]; o = [y(e) for e in S]
    L = sum(ll(a, b) for a, b in zip(p, o)) / len(S); B = sum((a - b) ** 2 for a, b in zip(p, o)) / len(S)
    # nagib kalibracije: logistička regresija ishoda na logit(p) (1 = dobro, < 1 = previše samouveren, > 1 = previše oprezan)
    x = [math.log(a / (1 - a)) for a in p]; a0, a1 = 0.0, 1.0
    for _ in range(300):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for xi, oi in zip(x, o):
            q = 1 / (1 + math.exp(-(a0 + a1 * xi))); r = oi - q; w = q * (1 - q)
            g0 += r; g1 += r * xi; h00 += w; h01 += w * xi; h11 += w * xi * xi
        d = h00 * h11 - h01 ** 2
        if d <= 1e-12: break
        a0 += (h11 * g0 - h01 * g1) / d; a1 += (h00 * g1 - h01 * g0) / d
    print(f'  {ime:<34} logloss {L:.4f}  Brier {B:.4f}  nagib {a1:.2f}  pomak {a0:+.2f}')
for ime, S in (('9. kolo', [e for e in E if e['kolo'] == 9]), ('10. kolo', [e for e in E if e['kolo'] == 10]), ('oba', E)):
    print(f'\n== {ime}: {len(S)} linija, više prošlo {sum(map(y, S)) / len(S):.1%}')
    ocena('model (pomeraj+širina)', pm, S); ocena('model sirov', lambda e: pm(e, False, 1.0), S)
    ocena('istorija', ph, S); ocena('tržište (ostale)', pt, S); ocena('Maxbet bez marže', mb, S)
    ocena('spoj .27/.13/.60', spoj, S); ocena('samo tržište+model 0.3/0.7', lambda e: .3 * pm(e) + .7 * pt(e), S)
# najbolje težine (mreža), proveravane van uzorka: uči na jednom kolu, meri na drugom
print('\n== težine: uči na jednom kolu, meri na drugom (logloss)')
mreza = [(a / 20, b / 20, 1 - a / 20 - b / 20) for a in range(0, 21) for b in range(0, 21 - a)]
for uci, meri in ((9, 10), (10, 9)):
    U = [e for e in E if e['kolo'] == uci]; M = [e for e in E if e['kolo'] == meri]
    best = min(mreza, key=lambda w: sum(ll(spoj(e, w), y(e)) for e in U))
    f = lambda w, S: sum(ll(spoj(e, w), y(e)) for e in S) / len(S)
    print(f'  uči {uci}, meri {meri}: najbolje {best}  -> {f(best, M):.4f}  | sadašnje {f(W0, M):.4f} | samo tržište {f((0, 0, 1), M):.4f}')
# vrednost: kako prolaze opklade koje formula označi
print('\n== opklade po pravilu (model i istorija 55%+, vrednost 3%+), obe strane')
def opklade(S, sansa):
    out = []
    for e in S:
        for smer in ('više', 'manje'):
            s = sansa(e) if smer == 'više' else 1 - sansa(e); m = pm(e) if smer == 'više' else 1 - pm(e); h = ph(e) if smer == 'više' else 1 - ph(e) + 0  # približno
            kv = e['kvota_vise'] if smer == 'više' else e['kvota_manje']
            if smer == 'manje': h = (int(e['ist_manje'].split('/')[0]) + 1) / (int(e['ist_manje'].split('/')[1]) + 2)
            prosao = e['proslo_vise'] if smer == 'više' else (not e['proslo_vise'] and e['rezultat'] != e['linija'])
            out.append(dict(e=e, smer=smer, s=s, m=m, h=h, kv=kv, ok=prosao, t=pt(e) if smer == 'više' else 1 - pt(e)))
    return out
def rez(ime, L):
    if not L: print(f'  {ime:<46} n=0'); return
    n = len(L); w = sum(x['ok'] for x in L); pr = sum(x['kv'] - 1 if x['ok'] else -1 for x in L)
    print(f"  {ime:<46} n={n:>4} prošlo {w / n:5.1%} očekivano {sum(x['s'] for x in L) / n:5.1%} tržište {sum(x['t'] for x in L) / n:5.1%}  profit {pr:+6.2f} ({pr / n:+.1%})")
O = opklade(E, spoj)
rez('sve strane', O)
P = [x for x in O if x['m'] >= .55 and x['h'] >= .55 and x['s'] * x['kv'] - 1 >= .03]; rez('prolaze pravilo', P)
for k in ('Poeni', 'Skokovi', 'Asistencije'):
    for sm in ('više', 'manje'): rez(f'  {k} {sm}', [x for x in P if x['e']['kategorija'] == k and x['smer'] == sm])
rez('vrednost 3%+ samo po tržištu (t*kv-1)', [x for x in O if x['t'] * x['kv'] - 1 >= .03])
rez('vrednost 3%+ po spoju, tržište protiv (<50%)', [x for x in O if x['s'] * x['kv'] - 1 >= .03 and x['t'] < .5])
rez('vrednost 3%+ po spoju, tržište za (50%+)', [x for x in O if x['s'] * x['kv'] - 1 >= .03 and x['t'] >= .5])
rez('model i tržište oba 55%+', [x for x in O if x['m'] >= .55 and x['t'] >= .55])
rez('model 55%+, tržište < 50%', [x for x in O if x['m'] >= .55 and x['t'] < .5])
# Maxbet marža
mar = [1 / e['kvota_vise'] + 1 / e['kvota_manje'] - 1 for e in E]; print(f"\nMaxbet marža na glavnim linijama: prosek {sum(mar) / len(mar):.1%}")
# pristrasnost ka "više": stvarno naspram tržišta i Maxbeta, po kategoriji, sa intervalom (bootstrap po utakmicama)
print('\n== "više": koliko prolazi naspram onoga što kvote kažu')
def boot(S, f, n=2000):
    g = {}
    for e in S: g.setdefault((e['kolo'], e['utakmica']), []).append(f(e))
    G = list(g.values()); rng = random.Random(3); b = []
    for _ in range(n):
        u = [G[rng.randrange(len(G))] for _ in G]; b.append(sum(map(sum, u)) / sum(map(len, u)))
    b.sort(); return b[int(.025 * n)], b[int(.975 * n)]
for k in ('Poeni', 'Skokovi', 'Asistencije', None):
    S = [e for e in E if k is None or e['kategorija'] == k]
    d = lambda e: y(e) - pt(e); lo, hi = boot(S, d)
    print(f"  {k or 'sve':<12} n={len(S):>3} prošlo više {sum(map(y, S)) / len(S):5.1%}  tržište {sum(map(pt, S)) / len(S):5.1%}  Maxbet {sum(map(mb, S)) / len(S):5.1%}  razlika {sum(map(d, S)) / len(S):+.1%} [{lo:+.1%},{hi:+.1%}]")
# istorija: da li 55%+ istorije išta znači kad se zna tržište
print('\n== istorija kao filter (obe strane, sve linije)')
for lo_, hi_ in ((0, .45), (.45, .55), (.55, .65), (.65, 1.01)):
    L = [x for x in O if lo_ <= x['h'] < hi_]
    if L: print(f"  istorija {lo_:.0%}-{min(hi_, 1):.0%}: n={len(L):>4} prošlo {sum(x['ok'] for x in L) / len(L):5.1%}  tržište {sum(x['t'] for x in L) / len(L):5.1%}  razlika {sum(x['ok'] - x['t'] for x in L) / len(L):+.1%}")
print('\n== model kao signal preko tržišta: razlika model − tržište')
for lo_, hi_ in ((-1, -.1), (-.1, -.03), (-.03, .03), (.03, .1), (.1, 1)):
    L = [x for x in O if lo_ <= x['m'] - x['t'] < hi_]
    if L: print(f"  model−tržište {lo_:+.2f} do {hi_:+.2f}: n={len(L):>4} prošlo {sum(x['ok'] for x in L) / len(L):5.1%}  tržište {sum(x['t'] for x in L) / len(L):5.1%}  razlika {sum(x['ok'] - x['t'] for x in L) / len(L):+.1%}")
print('\n== isto, po kolu i sa intervalom (samo strana gde je model iznad tržišta)')
for lo_, hi_ in ((.03, .1), (.1, 1), (.03, 1), (.05, .1)):
    for kolo in (9, 10, None):
        L = [x for x in O if lo_ <= x['m'] - x['t'] < hi_ and (kolo is None or x['e']['kolo'] == kolo)]
        g = {}
        for x in L: g.setdefault((x['e']['kolo'], x['e']['utakmica']), []).append(x['ok'] - x['t'])
        G = list(g.values()); rng = random.Random(5); b = []
        for _ in range(2000):
            u = [G[rng.randrange(len(G))] for _ in G]; b.append(sum(map(sum, u)) / sum(map(len, u)))
        b.sort(); pr = sum(x['kv'] - 1 if x['ok'] else -1 for x in L)
        print(f"  {lo_:+.2f} do {hi_:+.2f} kolo {kolo or 'oba'}: n={len(L):>3} razlika {sum(x['ok'] - x['t'] for x in L) / len(L):+.1%} [{b[50]:+.1%},{b[1950]:+.1%}]  profit po Maxbet kvoti {pr / len(L):+.1%}")
