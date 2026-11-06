# Pregled celog sistema 7.11.2026 (kola 9-10, linije sa tržištem iz evidencija.json). Ništa ne upisuje.
# A) Maxbet linija naspram medijane ostalih kladionica, B) sporedne linije (samo „više“) po kvoti, C) marža po vrsti linije,
# D) „manje“ po minutima, poziciji i statusu, E) povezanost unutar utakmice (svi igrači iste utakmice istim smerom).
import json, math, random
from collections import defaultdict
from pomocno import citaj, MEDIJANA
Phi = lambda z: .5 * (1 + math.erf(z / math.sqrt(2)))
C = citaj('tezine.json')['c']; K = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}
U = {}
for e in citaj('evidencija.json'):
    if e.get('proslo_vise') in (True, False) and e.get('trz_vise') is not None and e.get('status') != 'Ne igra':
        U[(e['kolo'], e['dan'], e['igrac'], e['kategorija'], e['linija'])] = e
E = list(U.values())
def ok(e, s): return e['proslo_vise'] if s == 'više' else (not e['proslo_vise'] and e['rezultat'] != e['linija'])
def rep(ime, L):   # L: lista (e, smer, kvota)
    if len(L) < 10: print(f'  {ime:<50} n={len(L)}'); return
    n = len(L); w = [ok(e, s) for e, s, _ in L]; pr = [kv - 1 if o else -1 for (e, s, kv), o in zip(L, w)]
    G = defaultdict(list)
    for (e, s, kv), p in zip(L, pr): G[(e['kolo'], e['dan'])].append(p)   # bootstrap po DANIMA (opklade istog dana su povezane)
    D = list(G.values()); r = random.Random(5); b = []
    for _ in range(2000):
        u = [D[r.randrange(len(D))] for _ in D]; b.append(sum(map(sum, u)) / sum(map(len, u)))
    b.sort()
    imp = sum((1 / kv) for e, s, kv in L) / n
    k9 = [p for (e, s, kv), p in zip(L, pr) if e['kolo'] == 9]; k10 = [p for (e, s, kv), p in zip(L, pr) if e['kolo'] == 10]
    f = lambda x: f'{sum(x) / len(x):+.0%}' if x else '—'
    print(f'  {ime:<50} n={n:>4} prošlo {sum(w) / n:5.1%} kvota traži {imp:5.1%} profit {sum(pr) / n:+6.1%} [po danima {b[50]:+.0%},{b[1950]:+.0%}] k9 {f(k9)} k10 {f(k10)}')
G = [e for e in E if e.get('kvota_manje')]   # linije sa obe kvote
S = [e for e in E if not e.get('kvota_manje')]   # sporedne: samo „više“
print(f'Linija sa tržištem: {len(E)}; sa obe kvote {len(G)}; sporedne samo „više“ {len(S)}; dana {len({(e["kolo"], e["dan"]) for e in E})}')

print('\n== A) Maxbet linija naspram medijane ostalih kladionica (linije sa obe kvote, glavne 1.65-2.20)')
GL = [e for e in G if 1.65 <= e['kvota_vise'] <= 2.2 and 1.65 <= e['kvota_manje'] <= 2.2 and e.get('trz_medijana') is not None]
for lo, hi, ime in ((.5, 99, 'Maxbet linija VIŠA za 0.5+ → manje'), (.01, .5, 'Maxbet viša za manje od 0.5 → manje'), (-.01, .01, 'ista → manje'), (-.5, -.01, 'Maxbet niža do 0.5 → više'), (-99, -.5, 'Maxbet linija NIŽA za 0.5+ → više')):
    L = [e for e in GL if lo <= e['linija'] - e['trz_medijana'] < hi]
    s = 'manje' if lo >= -.01 else 'više'
    rep(ime, [(e, s, e['kvota_manje'] if s == 'manje' else e['kvota_vise']) for e in L])
for lo, ime in ((.5, 'Maxbet viša 0.5+ → VIŠE (provera suprotne strane)'),):
    L = [e for e in GL if e['linija'] - e['trz_medijana'] >= lo]; rep(ime, [(e, 'više', e['kvota_vise']) for e in L])
L = [e for e in GL if e['linija'] - e['trz_medijana'] <= -.5]; rep('Maxbet niža 0.5+ → MANJE (provera suprotne strane)', [(e, 'manje', e['kvota_manje']) for e in L])

print('\n== B) Sporedne linije (Maxbet nudi samo „više“) po kvoti')
for lo, hi in ((1, 1.3), (1.3, 1.6), (1.6, 2.2), (2.2, 3), (3, 5), (5, 99)):
    rep(f'sporedna više, kvota {lo}-{hi}', [(e, 'više', e['kvota_vise']) for e in S if lo <= e['kvota_vise'] < hi])
print('   i linije sa obe kvote, strana „više“ po kvoti')
for lo, hi in ((1, 1.6), (1.6, 1.95), (1.95, 2.4), (2.4, 99)):
    rep(f'više, kvota {lo}-{hi}', [(e, 'više', e['kvota_vise']) for e in G if lo <= e['kvota_vise'] < hi])
    rep(f'manje, kvota {lo}-{hi}', [(e, 'manje', e['kvota_manje']) for e in G if lo <= e['kvota_manje'] < hi])

print('\n== C) Maxbet marža (1/kv više + 1/kv manje − 1)')
for ime, L in (('glavne 1.65-2.20', GL), ('ostale sa obe kvote', [e for e in G if e not in GL])):
    for k in K:
        M = [1 / e['kvota_vise'] + 1 / e['kvota_manje'] - 1 for e in L if e['kategorija'] == k]
        if M: print(f'  {ime:<22} {k:<12} n={len(M):>4} marža {sum(M) / len(M):.1%}')

print('\n== D) „Manje“ na glavnim linijama po vrsti igrača')
X = [(e, 'manje', e['kvota_manje']) for e in GL]
for lo, hi in ((0, 15), (15, 22), (22, 28), (28, 99)): rep(f'minuti proj {lo}-{hi}', [x for x in X if lo <= x[0]['minuti_proj'] < hi])
for p in ('G', 'F', 'C'): rep(f'pozicija {p}', [x for x in X if str(x[0].get('poz', '')).startswith(p)])
rep('upitan', [x for x in X if x[0]['status'] == 'Upitan']); rep('nestalni minuti (sd 6+)', [x for x in X if (x[0].get('minuti_sd') or 0) >= 6])
rep('domaćin', [x for x in X if x[0].get('teren') == 'domaćin']); rep('gost', [x for x in X if x[0].get('teren') == 'gost'])
for lo, hi in ((0, 8), (8, 13), (13, 99)): rep(f'poeni, linija {lo}-{hi}', [x for x in X if x[0]['kategorija'] == 'Poeni' and lo <= x[0]['linija'] < hi])

print('\n== E) Koliko je smer vezan za utakmicu: udeo „više“ po utakmici (glavne linije)')
U2 = defaultdict(list)
for e in GL: U2[(e['kolo'], e['utakmica'])].append(e['proslo_vise'])
r = sorted((sum(v) / len(v), len(v), k[1]) for k, v in U2.items() if len(v) >= 6)
for x in r[:4] + r[-4:]: print(f'  {x[2]:<34} više prošlo {x[0]:.0%} od {x[1]} linija')
sd_stv = (sum((x[0] - .45) ** 2 for x in r) / len(r)) ** .5; sd_slucaj = (sum(.45 * .55 / x[1] for x in r) / len(r)) ** .5
print(f'  rasipanje po utakmicama {sd_stv:.2f}, a slučajno bi bilo {sd_slucaj:.2f} → {"utakmica jako vuče sve igrače u isti smer" if sd_stv > 1.3 * sd_slucaj else "nema jake povezanosti"}')
