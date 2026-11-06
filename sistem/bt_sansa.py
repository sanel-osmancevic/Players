# Traženje formule šanse koja se uklapa u dosadašnje rezultate, bez varanja: logistička regresija na linijama 9. i 10. kola,
# učena na jednom kolu (ili danu), a merena na drugom. Ništa ne upisuje. Upotreba: py -X utf8 bt_sansa.py
# Ulazi po liniji (strana "više"): tržište (logit), razlika modela i tržišta (logit, odsečena na ±0.15 u verovatnoći),
# pomak za "više" po kategoriji, forma poslednjih 5. Mala ridge kazna da 500 linija ne bi "naučilo" slučaj.
import math, random, re, unicodedata
from pomocno import citaj, MEDIJANA
Phi = lambda z: .5 * (1 + math.erf(z / math.sqrt(2)))
C = citaj('tezine.json')['c']; K = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}
lg = lambda p: math.log(p / (1 - p)); sg = lambda x: 1 / (1 + math.exp(-x))
def kl(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower().replace("'", ''); n = re.sub(r'\b(iv|iii|jr)\b', '', n); n = re.sub(r'\b[a-z]\b', '', n); return re.sub(r'[^a-z]', '', n)
ST = {}
for n, pos, t, rr, mm, ss, vp, vr, va in citaj('statistika.json')['P']:
    l, f = (n.split(', ', 1) + [''])[:2]
    ST[kl(f + ' ' + l)] = {'kola': [int(x) for x in rr.split(',')], 'pts': [int(x) for x in vp.split(',')], 'reb': [int(x) for x in vr.split(',')], 'ast': [int(x) for x in va.split(',')]}
def forma(e):
    s = ST.get(kl(e['igrac'])); v = [x for r, x in zip(s['kola'], s[K[e['kategorija']]]) if r < e['kolo']][-5:] if s else []
    return (sum(x > e['linija'] for x in v) + 1) / (len(v) + 2)
E = [e for e in citaj('evidencija.json') if e.get('kvota_manje') and e.get('trz_vise') is not None and e.get('proslo_vise') in (True, False)]
cl = lambda p: min(.97, max(.03, p))
for e in E:
    e['_pm'] = cl(1 - Phi((math.floor(e['linija']) + .5 - (e['proj'] + MEDIJANA[K[e['kategorija']]])) / (e['sd'] * C)))
    e['_pms'] = cl(1 - Phi((math.floor(e['linija']) + .5 - e['proj']) / e['sd']))   # stari model, oko proseka, bez širine
    e['_pt'] = cl(e['trz_vise']); e['_y'] = 1.0 if e['proslo_vise'] else 0.0; e['_f'] = forma(e)
    d = max(-.15, min(.15, e['_pm'] - e['_pt'])); e['_d'] = lg(cl(e['_pt'] + d)) - lg(e['_pt'])
    e['_dv'] = lg(e['_pm']) - lg(e['_pt'])   # neodsečena
def X(e, skup):
    v = [1.0]   # pomak za "više" (zajednički)
    if 'trz' in skup: v.append(lg(e['_pt']))
    if 'raz' in skup: v.append(e['_d'])
    if 'razv' in skup: v.append(e['_dv'])
    if 'kat' in skup: v += [1.0 * (e['kategorija'] == 'Skokovi'), 1.0 * (e['kategorija'] == 'Asistencije')]
    if 'forma' in skup: v.append(lg(e['_f']) - lg(e['_pt']))
    return v
def uci(S, skup, lam=2.0):
    Xs = [X(e, skup) for e in S]; y = [e['_y'] for e in S]; p = len(Xs[0]); w = [0.0] * p
    if 'trz' in skup: w[1] = 1.0
    pri = list(w)   # kazna vuče ka "veruj tržištu" (koef. 1 za tržište, 0 za ostalo)
    for _ in range(50):
        g = [0.0] * p; H = [[0.0] * p for _ in range(p)]
        for xi, yi in zip(Xs, y):
            q = sg(sum(a * b for a, b in zip(w, xi))); r = yi - q; s = q * (1 - q)
            for i in range(p):
                g[i] += r * xi[i]
                for j in range(p): H[i][j] += s * xi[i] * xi[j]
        for i in range(p): g[i] -= lam * (w[i] - pri[i]); H[i][i] += lam
        # rešenje H·d = g (Gauss)
        A = [H[i][:] + [g[i]] for i in range(p)]
        for i in range(p):
            m = max(range(i, p), key=lambda r: abs(A[r][i])); A[i], A[m] = A[m], A[i]
            for r in range(p):
                if r != i:
                    f = A[r][i] / A[i][i]; A[r] = [a - f * b for a, b in zip(A[r], A[i])]
        d = [A[i][p] / A[i][i] for i in range(p)]; w = [a + b for a, b in zip(w, d)]
        if max(map(abs, d)) < 1e-6: break
    return w
P = lambda w, e, skup: cl(sg(sum(a * b for a, b in zip(w, X(e, skup)))))
ll = lambda p, y: -(y * math.log(p) + (1 - y) * math.log(1 - p))
DELOVI = [('9', lambda e: e['kolo'] == 9), ('10', lambda e: e['kolo'] == 10)]
DANI = sorted({(e['kolo'], e['dan']) for e in E})
FIKS = {'tržište': lambda e: e['_pt'], 'sadašnja 0.4/0.6': lambda e: .4 * e['_pm'] + .6 * e['_pt'], 'stari model sam': lambda e: e['_pms'], 'novi model sam': lambda e: e['_pm']}
SKUP = {'pomak + tržište': {'trz'}, 'pomak + tržište + razlika(±15)': {'trz', 'raz'}, 'pomak + tržište + razlika (neodsečena)': {'trz', 'razv'},
        '... + kategorija': {'trz', 'raz', 'kat'}, '... + forma': {'trz', 'raz', 'forma'}, 'sve': {'trz', 'raz', 'kat', 'forma'}}
print(f'Linija {len(E)}, dana {DANI}\n== Logloss van uzorka: uči na ostalim danima, meri na izostavljenom (manje je bolje)')
def van(fn_uci):
    tot = 0; n = 0; po = []
    for d in DANI:
        U = [e for e in E if (e['kolo'], e['dan']) != d]; M = [e for e in E if (e['kolo'], e['dan']) == d]
        f = fn_uci(U); s = sum(ll(f(e), e['_y']) for e in M); tot += s; n += len(M); po.append(s / len(M))
    return tot / n, po
for ime, f in FIKS.items():
    L, po = van(lambda U, f=f: f); print(f"  {ime:<42} {L:.4f}   po danima " + ' '.join(f'{x:.3f}' for x in po))
W = {}
for ime, sk in SKUP.items():
    L, po = van(lambda U, sk=sk: (lambda w: (lambda e: P(w, e, sk)))(uci(U, sk))); print(f"  {ime:<42} {L:.4f}   po danima " + ' '.join(f'{x:.3f}' for x in po))
    W[ime] = uci(E, sk)
print('\n== Koeficijenti na svim linijama (pomak, tržište, razlika, ...)')
for ime, w in W.items(): print(f"  {ime:<42} " + ' '.join(f'{x:+.2f}' for x in w))
# simulacija opklada van uzorka: obe strane, Maxbet kvota, vrednost 3%+, jedna opklada po igraču i danu
print('\n== Opklade van uzorka (vrednost 3%+ po toj šansi, Maxbet kvota, ulog 1, jedna po igraču i danu)')
def sim(fn_uci, prag=.03, maks=None):
    out = []
    for d in DANI:
        U = [e for e in E if (e['kolo'], e['dan']) != d]; M = [e for e in E if (e['kolo'], e['dan']) == d]; f = fn_uci(U); naj = {}
        for e in M:
            p = f(e)
            for smer, s, kv, ok, t in (('v', p, e['kvota_vise'], e['_y'] == 1, e['_pt']), ('m', 1 - p, e['kvota_manje'], e['_y'] == 0 and e['rezultat'] != e['linija'], 1 - e['_pt'])):
                ev = s * kv - 1
                if ev >= prag and (maks is None or ev < maks) and (e['igrac'] not in naj or ev > naj[e['igrac']][0]): naj[e['igrac']] = (ev, kv, ok, t, d)
        out += naj.values()
    if not out: return '0'
    pr = sum(kv - 1 if ok else -1 for _, kv, ok, _, _ in out); hit = sum(ok for *_, ok, _, _ in [(a, b, c, t, d) for a, b, c, t, d in out])
    pd = {}
    for ev, kv, ok, t, d in out: pd[d] = pd.get(d, 0) + (kv - 1 if ok else -1)
    return f"n={len(out):>3} prošlo {hit / len(out):.0%} (tržište {sum(t for *_, t, _ in out) / len(out):.0%}) profit {pr:+.2f} ({pr / len(out):+.1%}) | po danima " + ' '.join(f'{v:+.1f}' for v in pd.values())
for ime, f in FIKS.items(): print(f"  {ime:<42} {sim(lambda U, f=f: f)}")
for ime, sk in SKUP.items(): print(f"  {ime:<42} {sim(lambda U, sk=sk: (lambda w: (lambda e: P(w, e, sk)))(uci(U, sk)))}")
print('\n== Sadašnja šansa (0.4 model / 0.6 tržište): koji uslovi pomažu (vrednost 3%+, jedna opklada po igraču i danu)')
def sim2(uslov, top=None):
    out = []
    for d in DANI:
        naj = {}
        for e in [e for e in E if (e['kolo'], e['dan']) == d]:
            for smer, m, t, kv, ok in (('v', e['_pm'], e['_pt'], e['kvota_vise'], e['_y'] == 1), ('m', 1 - e['_pm'], 1 - e['_pt'], e['kvota_manje'], e['_y'] == 0 and e['rezultat'] != e['linija'])):
                s = .4 * m + .6 * t; ev = s * kv - 1
                if ev >= .03 and uslov(m, t, kv, smer) and (e['igrac'] not in naj or s > naj[e['igrac']][0]): naj[e['igrac']] = (s, kv, ok, t, smer)
        L = sorted(naj.values(), reverse=True)[:top] if top else list(naj.values()); out += [(d,) + x for x in L]
    pr = sum(kv - 1 if ok else -1 for _, s, kv, ok, t, sm in out); pd = {}
    for d, s, kv, ok, t, sm in out: pd[d] = pd.get(d, 0) + (kv - 1 if ok else -1)
    return f"n={len(out):>3} prošlo {sum(o[3] for o in out) / len(out):.0%} (tržište {sum(o[4] for o in out) / len(out):.0%}) profit {pr:+.2f} ({pr / len(out):+.1%}) više/manje {sum(o[5] == 'v' for o in out)}/{sum(o[5] == 'm' for o in out)} | po danima " + ' '.join(f'{v:+.1f}' for v in pd.values())
for ime, u in (('samo vrednost 3%+', lambda m, t, kv, s: True), ('+ model 55%+', lambda m, t, kv, s: m >= .55), ('+ razlika do 15', lambda m, t, kv, s: m - t <= .15),
               ('+ model 55%+ i razlika do 15 (sada)', lambda m, t, kv, s: m >= .55 and m - t <= .15), ('+ razlika 3-15', lambda m, t, kv, s: .03 <= m - t <= .15),
               ('+ kvota 1.70-2.30', lambda m, t, kv, s: 1.7 <= kv <= 2.3), ('+ razlika 3-15 i kvota 1.70-2.30', lambda m, t, kv, s: .03 <= m - t <= .15 and 1.7 <= kv <= 2.3)):
    print(f'  {ime:<42} {sim2(u)}')
print(f"  {'sada, ali najviše 10 po danu':<42} {sim2(lambda m, t, kv, s: m >= .55 and m - t <= .15, 10)}")
print('\n== Redosled za 10 po danu (sadašnji uslovi)')
def sim3(kljuc, top=10, uslov=lambda m, t, kv: m >= .55 and m - t <= .15):
    out = []
    for d in DANI:
        naj = {}
        for e in [e for e in E if (e['kolo'], e['dan']) == d]:
            for smer, m, t, kv, ok in (('v', e['_pm'], e['_pt'], e['kvota_vise'], e['_y'] == 1), ('m', 1 - e['_pm'], 1 - e['_pt'], e['kvota_manje'], e['_y'] == 0 and e['rezultat'] != e['linija'])):
                s = .4 * m + .6 * t; ev = s * kv - 1; x = dict(s=s, ev=ev, raz=m - t, kv=kv, ok=ok, t=t)
                if ev >= .03 and uslov(m, t, kv) and (e['igrac'] not in naj or kljuc(x) > kljuc(naj[e['igrac']])): naj[e['igrac']] = x
        out += [(d, x) for x in sorted(naj.values(), key=kljuc, reverse=True)[:top]]
    pr = sum(x['kv'] - 1 if x['ok'] else -1 for _, x in out); pd = {}
    for d, x in out: pd[d] = pd.get(d, 0) + (x['kv'] - 1 if x['ok'] else -1)
    return f"n={len(out):>3} prošlo {sum(x['ok'] for _, x in out) / len(out):.0%} (tržište {sum(x['t'] for _, x in out) / len(out):.0%}) profit {pr:+.2f} ({pr / len(out):+.1%}) | po danima " + ' '.join(f'{v:+.1f}' for v in pd.values())
for ime, k in (('po šansi (sada)', lambda x: x['s']), ('po vrednosti', lambda x: x['ev']), ('po razlici model − tržište', lambda x: x['raz'])):
    print(f'  {ime:<42} {sim3(k)}')
print(f"  {'po vrednosti, razlika 3-15':<42} {sim3(lambda x: x['ev'], 10, lambda m, t, kv: .03 <= m - t <= .15)}")
print(f"  {'bez ograničenja 10, razlika 3-15':<42} {sim3(lambda x: x['ev'], 99, lambda m, t, kv: .03 <= m - t <= .15)}")
