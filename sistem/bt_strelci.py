# Da li su najbolji strelci precenjeni i da li tržište to već zna? Ništa ne upisuje. Upotreba: py -X utf8 bt_strelci.py
# Prvi deo: Maxbet linije na poene iz evidencije (9. kolo i Real - Panathinaikos): model, tržište i stvarni poeni.
# Drugi deo: umanjenje projekcije za strelce, podešeno na kolima 3-6 i provereno na kolima 7-9, pa na linijama 9. kola.
import math, unicodedata, re
exec(open('bt_minuti2.py', encoding='utf8').read().split("def dopuna(")[0])
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
BIAS = 0.2
Phi = lambda z: .5 * (1 + math.erf(z / math.sqrt(2)))
E = [e for e in citaj('evidencija.json') if e['kategorija'] == 'Poeni' and e.get('rezultat') is not None and (e.get('minuti_stvarno') or 0) > 0
     and e.get('proslo_vise') in (True, False) and e.get('kvota_manje') and e.get('kvota_vise') and e.get('trz_vise') is not None and e.get('trz_medijana') is not None]
print(f'linija {len(E)}, igrača {len({(e["kolo"], e["igrac"]) for e in E})}, utakmica {len({(e["kolo"], e["utakmica"]) for e in E})}')
def pm(e, d=0.0): return 1 - Phi((math.floor(e['linija']) + .5 - (e['proj'] + BIAS + d)) / e['sd'])
def ph(e):
    h, n = map(int, e['ist_vise'].split('/')); return (h + 1) / (n + 2)
def spoj(e, d=0.0): return .216 * pm(e, d) + .184 * ph(e) + .6 * e['trz_vise']
def ll(p, y):
    p = min(max(p, .01), .99); return -(y * math.log(p) + (1 - y) * math.log(1 - p))
print(f"\n{'projekcija':<12}{'lin':>5}{'prolazi više':>13}{'model':>7}{'tržište':>9}{'spoj':>6} | {'proj':>6}{'medij.':>8}{'stvarno':>9} | {'ravan ulog više':>16}{'ravan ulog manje':>18}")
for ime, lo, hi in (('ispod 8', 0, 8), ('8-12', 8, 12), ('12+', 12, 99)):
    q = [e for e in E if lo <= e['proj'] + BIAS < hi]
    if not q: continue
    y = [1 if e['proslo_vise'] else 0 for e in q]
    pv = sum((e['kvota_vise'] - 1 if a else -1) for e, a in zip(q, y)) / len(q); pn = sum((-1 if a else e['kvota_manje'] - 1) for e, a in zip(q, y)) / len(q)
    print(f"{ime:<12}{len(q):>5}{sum(y) / len(y):>13.1%}{sum(pm(e) for e in q) / len(q):>7.1%}{sum(e['trz_vise'] for e in q) / len(q):>9.1%}{sum(spoj(e) for e in q) / len(q):>6.1%} | {sum(e['proj'] + BIAS for e in q) / len(q):>6.2f}{sum(e['trz_medijana'] for e in q) / len(q):>8.2f}{sum(e['rezultat'] for e in q) / len(q):>9.2f} | {pv:>+16.1%}{pn:>+18.1%}")
# Umanjenje: raste od proseka 10 do punog c na proseku 14 i više
def uman(p, c): return c * max(0.0, min(1.0, (p - 10) / 4))
red = []
for u in UZ:
    h = [v for r, v in LOG[(u[0], u[1])].items() if r < u[2]]; a = LOG[(u[0], u[1])][u[2]]
    red.append(dict(pros=sum(v['pts'] for v in h) / len(h), proj=proj(*u, SVE[u[2]], PUNI)['pts'][0] + BIAS, st=a['pts'], kod=a['kod'], R=u[2]))
A = [x for x in red if x['R'] <= 6]; B = [x for x in red if x['R'] > 6]
def gr(S, c): return sum(abs(x['proj'] - uman(x['pros'], c) - x['st']) for x in S) / len(S)
print(f"\nUMANJENJE c (svi igrači, prosečna |greška|)\n{'c':<6}{'kola 3-6':>10}{'kola 7-9':>10}")
C = (0, .5, 1, 1.5, 2, 2.5, 3)
for c in C: print(f'{c:<6}{gr(A, c):>10.3f}{gr(B, c):>10.3f}')
naj = min(C, key=lambda c: gr(A, c)); print('najbolje na kolima 3-6: c =', naj)
g = {}
for x in B: g.setdefault(x['kod'], []).append(abs(x['proj'] - uman(x['pros'], naj) - x['st']) - abs(x['proj'] - x['st']))
m, l, h = boot(g); print(f'provera na kolima 7-9 (minus = bolje): {m:+.3f} [{l:+.3f},{h:+.3f}]')
S = [x for x in B if x['pros'] >= 10]; g = {}
for x in S: g.setdefault(x['kod'], []).append(abs(x['proj'] - uman(x['pros'], naj) - x['st']) - abs(x['proj'] - x['st']))
m, l, h = boot(g); print(f'samo prosek 10+ (n={len(S)}): {m:+.3f} [{l:+.3f},{h:+.3f}]')
# Linije 9. kola
def kl(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower().replace("'", '')
    n = re.sub(r'\b(iv|iii|jr)\b', '', n); n = re.sub(r'\b[a-z]\b', '', n); return re.sub(r'[^a-z]', '', n)
PR = {}
for (n, t), hh in LOG.items():
    l_, f = n.split(', ', 1) if ', ' in n else (n, '')
    h = [v for r, v in hh.items() if r < 9]
    if h: PR[kl(f + ' ' + l_)] = sum(v['pts'] for v in h) / len(h)
L9 = [e for e in E if e['kolo'] == 9 and kl(e['igrac']) in PR]
print(f'\nLINIJE 9. KOLA ({len(L9)}), logloss model / spoj')
for c in (0, naj):
    d = lambda e: -uman(PR[kl(e['igrac'])], c)
    Y = [1 if e['proslo_vise'] else 0 for e in L9]
    print(f"c={c}: {sum(ll(pm(e, d(e)), y) for e, y in zip(L9, Y)) / len(L9):.4f} / {sum(ll(spoj(e, d(e)), y) for e, y in zip(L9, Y)) / len(L9):.4f}")
    T = [(e, y) for e, y in zip(L9, Y) if PR[kl(e['igrac'])] >= 10]
    print(f"   prosek 10+ ({len(T)}): {sum(ll(pm(e, d(e)), y) for e, y in T) / max(1, len(T)):.4f} / {sum(ll(spoj(e, d(e)), y) for e, y in T) / max(1, len(T)):.4f}")
