# Šta da se menja u projekciji: spoj sa tržištem, pomeraj, širina, oslonac na prosek lige. Ništa ne upisuje. Upotreba: py -X utf8 bt_projekcija.py
# Prvi deo: linije 9. i 10. kola (evidencija.json): stvarni broj naspram projekcije modela, medijane tržišta i spoja.
# Drugi deo: kola 3-9 (vraćanje vremena): težina proseka lige u stopi po minuti.
import math, random
from pomocno import citaj
Phi = lambda z: .5 * (1 + math.erf(z / math.sqrt(2)))
T = citaj('tezine.json'); B = T['bias']; C = T['c']; K = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}
E = [e for e in citaj('evidencija.json') if e.get('proslo_vise') in (True, False) and e.get('kvota_manje') and e.get('trz_medijana') is not None and e.get('rezultat') is not None]
U = {}
for e in E: U.setdefault((e['kolo'], e['igrac'], e['kategorija']), e)   # jedan red po igraču i kategoriji za grešku projekcije
ll = lambda p, o: -(o * math.log(p) + (1 - o) * math.log(1 - p))
def boot(S, f):
    g = {}
    for e in S: g.setdefault((e['kolo'], e['utakmica']), []).append(f(e))
    G = list(g.values()); r = random.Random(1); b = []
    for _ in range(1500):
        u = [G[r.randrange(len(G))] for _ in G]; b.append(sum(map(sum, u)) / sum(map(len, u)))
    b.sort(); return b[37], b[1462]
print('== 1) Greška projekcije (|stvarno − projekcija|), igrač-kategorija sa linijom, kola 9-10')
for kat in ('Poeni', 'Skokovi', 'Asistencije'):
    S = [e for e in U.values() if e['kategorija'] == kat]; bk = B[K[kat]]
    for ime, f in (('model sirov', lambda e: e['proj']), ('model + pomeraj', lambda e: e['proj'] + bk), ('medijana tržišta', lambda e: e['trz_medijana']),
                   ('spoj 50/50', lambda e: .5 * e['proj'] + .5 * e['trz_medijana']), ('spoj 30 model/70 tržište', lambda e: .3 * e['proj'] + .7 * e['trz_medijana'])):
        print(f"  {kat:<12} {ime:<26} n={len(S):>3} MAE {sum(abs(e['rezultat'] - f(e)) for e in S) / len(S):.3f}  pristrasnost {sum(e['rezultat'] - f(e) for e in S) / len(S):+.2f}")
    d = lambda e: abs(e['rezultat'] - e['proj']) - abs(e['rezultat'] - (.5 * e['proj'] + .5 * e['trz_medijana'])); lo, hi = boot(S, d)
    print(f"  {'':<12} spoj 50/50 bolji od modela za {sum(map(d, S)) / len(S):+.3f} [{lo:+.3f},{hi:+.3f}]")
print('\n== 2) Verovatnoća na liniji (logloss, manje je bolje), sve glavne linije')
def pm(e, mu, c): return min(.999, max(.001, 1 - Phi((math.floor(e['linija']) + .5 - mu) / (e['sd'] * c))))
y = lambda e: 1.0 if e['proslo_vise'] else 0.0
for ime, mu in (('sirov', lambda e: e['proj']), ('pomeraj', lambda e: e['proj'] + B[K[e['kategorija']]]), ('spoj 50/50', lambda e: .5 * e['proj'] + .5 * e['trz_medijana']),
                ('spoj 50/50 + pomeraj', lambda e: .5 * (e['proj'] + B[K[e['kategorija']]]) + .5 * e['trz_medijana'])):
    s = '  '.join(f"c={c}: {sum(ll(pm(e, mu(e), c), y(e)) for e in E) / len(E):.4f}" for c in (1.0, 1.12, 1.3, 1.5))
    print(f"  {ime:<22} {s}")
print(f"  (tržište samo: {sum(ll(min(.999, max(.001, e['trz_vise'])), y(e)) for e in E) / len(E):.4f})")
# 3) kola 3-9: težina proseka lige (pw) u stopi po minuti
exec(open('bt_faktori.py', encoding='utf8').read().split('SVE = {R')[0])
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
print('\n== 3) Težina proseka lige u stopi po minuti (kola 3-9, MAE; sada 30)')
for pw in (10, 20, 30, 45, 60):
    PW = pw; out = []
    for k in K3:
        out.append(f"{k} {sum(abs(LOG[(u[0], u[1])][u[2]][k] - proj(*u, SVE[u[2]], PUNI)[k][0]) for u in UZ) / len(UZ):.3f}")
    print(f'  pw={pw:<3}', '  '.join(out))
PW = 30
# 4) asimetrija: poeni su iskošeni udesno (prosek iznad medijane), a normalna raspodela to ne vidi
import statistics as st
print('\n== 4) Asimetrija: ostatak (stvarno − projekcija), kola 3-9')
P = {u: proj(*u, SVE[u[2]], PUNI) for u in UZ}
for k in K3:
    r = [LOG[(u[0], u[1])][u[2]][k] - P[u][k][0] for u in UZ]
    z = [x / P[u][k][1] for x, u in zip(r, UZ)]
    # koliko često stvarno prelazi projekciju (normalna kaže 50%)
    print(f"  {k}: prosek {st.mean(r):+.2f}  medijana {st.median(r):+.2f}  iznad projekcije {sum(x > 0 for x in r) / len(r):.1%}  iskošenost z {sum(x ** 3 for x in z) / len(z):+.2f}")
print('\n   linije 9-10: koliko često stvarno prelazi projekciju modela')
for kat in ('Poeni', 'Skokovi', 'Asistencije'):
    S = [e for e in U.values() if e['kategorija'] == kat]
    print(f"  {kat}: iznad sirove projekcije {sum(e['rezultat'] > e['proj'] for e in S) / len(S):.1%}, medijana ostatka {st.median([e['rezultat'] - e['proj'] for e in S]):+.2f}")
print('\n== 5) Verovatnoća oko medijane umesto proseka (pomak iz kola 3-9: pts −0.67, reb −0.21, ast −0.25), linije 9-10')
MED = {'Poeni': -.67, 'Skokovi': -.21, 'Asistencije': -.25}
for ime, mu in (('prosek (sada, sirov)', lambda e: e['proj']), ('sada sa pomerajem', lambda e: e['proj'] + B[K[e['kategorija']]]), ('medijana', lambda e: e['proj'] + MED[e['kategorija']])):
    for c in (1.0, 1.12):
        p = [pm(e, mu(e), c) for e in E]
        print(f"  {ime:<22} c={c}: logloss {sum(ll(a, y(e)) for a, e in zip(p, E)) / len(E):.4f}  prosečna P(više) {sum(p) / len(p):.1%} (stvarno {sum(map(y, E)) / len(E):.1%})")
for kolo in (9, 10):
    S = [e for e in E if e['kolo'] == kolo]
    a = sum(ll(pm(e, e['proj'] + B[K[e['kategorija']]], C), y(e)) for e in S) / len(S); b = sum(ll(pm(e, e['proj'] + MED[e['kategorija']], C), y(e)) for e in S) / len(S)
    print(f"  kolo {kolo}: sada {a:.4f} -> medijana {b:.4f}")
d = lambda e: ll(pm(e, e['proj'] + B[K[e['kategorija']]], C), y(e)) - ll(pm(e, e['proj'] + MED[e['kategorija']], C), y(e)); lo, hi = boot(E, d)
print(f"  poboljšanje {sum(map(d, E)) / len(E):+.4f} [{lo:+.4f},{hi:+.4f}] (plus = medijana bolja)")
