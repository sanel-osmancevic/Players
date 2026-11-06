# Provera pravila izbora na novoj formuli (od 6.11.2026: šansa oko medijane, istorija bez težine). Ništa ne upisuje.
# Linije 9. i 10. kola iz evidencija.json; forma (poslednjih 5) iz zapisnika pre tog kola. Upotreba: py -X utf8 bt_pravila.py
# Za svaku grupu: koliko prolazi u odnosu na tržište (interval: bootstrap po utakmicama) i profit uz ulog 1 po Maxbet kvoti.
import math, random
from pomocno import citaj, MEDIJANA
exec(open('bt_faktori.py', encoding='utf8').read().split('# --- zapisnici')[1].split('SVE = {R')[0]) if False else None
Phi = lambda z: .5 * (1 + math.erf(z / math.sqrt(2)))
T = citaj('tezine.json'); C = T['c']; K = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}
SV = citaj('evidencija.json')
# forma: vrednosti igrača po kolu iz statistika.json (kola do 9) i zapisnika 10. kola nisu potrebne (linije su 9. i 10. kola)
ST = {}
import unicodedata, re
def kl(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower().replace("'", ''); n = re.sub(r'\b(iv|iii|jr)\b', '', n); n = re.sub(r'\b[a-z]\b', '', n); return re.sub(r'[^a-z]', '', n)
for n, pos, t, rr, mm, ss, vp, vr, va in citaj('statistika.json')['P']:
    l, f = (n.split(', ', 1) + [''])[:2]
    ST[kl(f + ' ' + l)] = {'kola': [int(x) for x in rr.split(',')], 'pts': [int(x) for x in vp.split(',')], 'reb': [int(x) for x in vr.split(',')], 'ast': [int(x) for x in va.split(',')]}
def forma(e, smer):
    s = ST.get(kl(e['igrac']))
    if not s: return None
    v = [x for r, x in zip(s['kola'], s[K[e['kategorija']]]) if r < e['kolo']][-5:]
    if len(v) < 3: return None
    return sum((x > e['linija']) if smer == 'više' else (x < e['linija']) for x in v), len(v)
O = []; ALT = []
for e in SV:
    if e.get('proslo_vise') not in (True, False) or e.get('trz_vise') is None: continue
    pm = 1 - Phi((math.floor(e['linija']) + .5 - (e['proj'] + MEDIJANA[K[e['kategorija']]])) / (e['sd'] * C))
    strane = [('više', pm, e['trz_vise'], e['kvota_vise'], e['proslo_vise'])]
    if e.get('kvota_manje'): strane.append(('manje', 1 - pm, 1 - e['trz_vise'], e['kvota_manje'], (not e['proslo_vise']) and e['rezultat'] != e['linija']))
    for smer, m, t, kv, ok in strane:
        x = dict(e=e, smer=smer, m=m, t=t, kv=kv, ok=bool(ok), s=.4 * m + .6 * t, f=forma(e, smer))
        x['ev'] = x['s'] * kv - 1; x['raz'] = m - t
        (O if e.get('kvota_manje') else ALT).append(x)
def rez(ime, L):
    if len(L) < 5: print(f'  {ime:<52} n={len(L)}'); return
    g = {}
    for x in L: g.setdefault((x['e']['kolo'], x['e']['utakmica']), []).append(x['ok'] - x['t'])
    G = list(g.values()); r = random.Random(4); b = []
    for _ in range(1500):
        u = [G[r.randrange(len(G))] for _ in G]; b.append(sum(map(sum, u)) / sum(map(len, u)))
    b.sort(); pr = sum(x['kv'] - 1 if x['ok'] else -1 for x in L) / len(L)
    k9 = [x for x in L if x['e']['kolo'] == 9]; k10 = [x for x in L if x['e']['kolo'] == 10]
    f = lambda S: f"{sum(x['ok'] - x['t'] for x in S) / len(S):+.1%}" if S else '  —  '
    print(f"  {ime:<52} n={len(L):>3} prolazi {sum(x['ok'] for x in L) / len(L):5.1%} −tržište {f(L)} [{b[37]:+.1%},{b[1462]:+.1%}] k9 {f(k9)} k10 {f(k10)} profit {pr:+.1%}")
OSN = [x for x in O if x['m'] >= .55 and x['ev'] >= .03 and x['raz'] <= .15]
print('== Sadašnje pravilo (model 55%+, vrednost 3%+, razlika do 15) i njegovi delovi; sve glavne linije, obe strane')
rez('sve strane', O); rez('sadašnje osnovno pravilo', OSN)
for sm in ('više', 'manje'): rez(f'  samo {sm}', [x for x in OSN if x['smer'] == sm])
for k in K: rez(f'  {k}', [x for x in OSN if x['e']['kategorija'] == k])
print('\n== Forma (poslednjih 5 pre kola): sada se traži bar 3 od 5')
rez('pravilo, forma 3+ od 5', [x for x in OSN if x['f'] and x['f'][0] >= 3]); rez('pravilo, forma ispod 3', [x for x in OSN if x['f'] and x['f'][0] < 3])
rez('sve strane, forma 4-5 od 5', [x for x in O if x['f'] and x['f'][0] >= 4]); rez('sve strane, forma 0-1 od 5', [x for x in O if x['f'] and x['f'][0] <= 1])
print('\n== Prag vrednosti i razlika model − tržište (unutar model 55%+)')
B = [x for x in O if x['m'] >= .55]
for lo, hi in ((-1, 0), (0, .03), (.03, .06), (.06, .1), (.1, 1)): rez(f'vrednost {lo:+.0%} do {hi:+.0%}', [x for x in B if lo <= x['ev'] < hi and x['raz'] <= .15])
for lo, hi in ((0, .05), (.05, .1), (.1, .15), (.15, 1)): rez(f'razlika {lo:.2f}-{hi:.2f}, vrednost 3%+', [x for x in B if lo <= x['raz'] < hi and x['ev'] >= .03])
print('\n== Bez uslova model 55% (samo vrednost 3%+ i razlika do 15)')
rez('vrednost 3%+, razlika 0-15', [x for x in O if x['ev'] >= .03 and 0 <= x['raz'] <= .15])
rez('razlika 3-15, bez uslova vrednosti', [x for x in O if .03 <= x['raz'] <= .15])
rez('razlika 3-15 i Maxbet kvota bar fer po tržištu', [x for x in O if .03 <= x['raz'] <= .15 and x['t'] * x['kv'] >= 1])
print('\n== Raskorak kladionica i minuti (pravilo)')
rez('raskorak mali (< pola praga)', [x for x in OSN if x['e'].get('trz_raskorak') is not None and x['e']['trz_raskorak'] < (.75 if x['e']['kategorija'] == 'Poeni' else .4)])
rez('raskorak veći', [x for x in OSN if x['e'].get('trz_raskorak') is not None and x['e']['trz_raskorak'] >= (.75 if x['e']['kategorija'] == 'Poeni' else .4)])
rez('minuti 25+', [x for x in OSN if x['e']['minuti_proj'] >= 25]); rez('minuti 15-25', [x for x in OSN if 15 <= x['e']['minuti_proj'] < 25]); rez('minuti < 15', [x for x in OSN if x['e']['minuti_proj'] < 15])
rez('nestalni minuti (sd 6+)', [x for x in OSN if (x['e'].get('minuti_sd') or 0) >= 6]); rez('stalni minuti (sd < 4)', [x for x in OSN if (x['e'].get('minuti_sd') or 9) < 4])
rez('kvota < 1.75', [x for x in OSN if x['kv'] < 1.75]); rez('kvota 1.75-2.05', [x for x in OSN if 1.75 <= x['kv'] < 2.05]); rez('kvota 2.05+', [x for x in OSN if x['kv'] >= 2.05])
print('\n== Sporedne linije (samo "više", bez kvote za manje)')
rez('sve sporedne', ALT); rez('sporedne, vrednost 3%+ i model 55%+', [x for x in ALT if x['m'] >= .55 and x['ev'] >= .03])
rez('sporedne, kvota 2.5+ i vrednost 3%+', [x for x in ALT if x['kv'] >= 2.5 and x['ev'] >= .03])
print('\n== Težina modela u šansi: uči na jednom kolu, meri na drugom (logloss)')
ll = lambda p, y: -(y * math.log(p) + (1 - y) * math.log(1 - p))
V = [x for x in O if x['smer'] == 'više']
def L_(w, S): return sum(ll(min(.99, max(.01, w * x['m'] + (1 - w) * x['t'])), x['ok']) for x in S) / len(S)
for uci, meri in ((9, 10), (10, 9)):
    U = [x for x in V if x['e']['kolo'] == uci]; M = [x for x in V if x['e']['kolo'] == meri]
    w = min((i / 20 for i in range(21)), key=lambda w: L_(w, U))
    print(f'  uči {uci} meri {meri}: najbolja težina modela {w:.2f} -> {L_(w, M):.4f} | sada 0.40 -> {L_(.4, M):.4f} | samo tržište {L_(0, M):.4f}')
