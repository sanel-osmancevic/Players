# Provera faktora modela "vraćanjem vremena": za svako kolo R (3 i dalje) projekcija samo iz kola pre R, formula kao u build5.py,
# a zatim stvarni učinak. Svaki faktor se isključuje posebno. Razlika je upareno po igraču, a 95% interval je bootstrap po utakmicama.
# Drugi deo: 9. kolo prema Maxbet kvotama i tržištu (evidencija.json). Ništa ne upisuje. Upotreba: py -X utf8 bt_faktori.py
import glob, math, os, random, re
from statistics import NormalDist
from pomocno import citaj
os.chdir(os.path.dirname(os.path.abspath(__file__)))
N = NormalDist(); K3 = ('pts', 'reb', 'ast'); STAT = {'pts': 'points', 'reb': 'totalRebounds', 'ast': 'assistances'}
POZ = {'Guard': 'G', 'Forward': 'F', 'Center': 'C'}; Z = ('r', 'm', 't'); VAL = {'r': 2, 'm': 2, 't': 3}
DECAY, PW, SD_C, SD_W = 0.9, 30, {'pts': 2.2, 'reb': 1.35, 'ast': 1.35}, 16   # MP iz build5.py
KOLA = range(1, citaj('kolo.json')['kolo'])
LS = citaj('prosla_sezona.json')

# --- zapisnici iz api_kes/
def kola_utakmica():
    out = {}
    for f in glob.glob('api_kes/s*.json'):
        kod = int(re.search(r's(\d+)\.json', f).group(1))
        out[kod] = (kod - 1) // 10 + 1   # kodovi idu redom po kolima: 1-10 prvo kolo, 11-20 drugo...
    return out
K_OF = kola_utakmica()
G = []       # sve utakmice: dict(kolo, kod, h, a, igraci)
for kod, R in sorted(K_OF.items()):
    if R not in KOLA: continue
    G.append(dict(kolo=R, kod=kod, s=citaj(f'api_kes/s{kod}.json'), p=citaj(f'api_kes/p{kod}.json')['Rows']))
def timovi(g):
    # imena iz zapisnika i tim iz Points redova određuju koji tim je domaćin
    ime_tim = {}
    for x in g['p']: ime_tim[x['PLAYER'].strip()] = x['TEAM'].strip()
    def tim(st):
        br = {}
        for pl in g['s'][st]['players']:
            t = ime_tim.get(pl['player']['person']['name'])
            if t: br[t] = br.get(t, 0) + 1
        return max(br, key=br.get) if br else None
    return tim('local'), tim('road')
LOG = {}     # (ime, tim) -> {kolo: dict(min, pts, reb, ast, kod, dom, opp)}
POS = {}
TEAM_R = {}  # (tim, kolo) -> posedi
ZON = {}     # (ime, tim, kolo) -> brojači šuta
DEF = {}     # (tim, kolo) -> šta je protivnik šutirao
for g in G:
    h, a = timovi(g); g['h'], g['a'] = h, a
    if not h or not a: continue
    pos = lambda b: b['fieldGoalsAttemptedTotal'] + 0.44 * b['freeThrowsAttempted'] + b['turnovers'] - b['offensiveRebounds']
    for st, t, o, dom in (('local', h, a, 1), ('road', a, h, 0)):
        tt = g['s'][st]['total']; oo = g['s']['road' if st == 'local' else 'local']['total']
        TEAM_R[(t, g['kolo'])] = pos(tt)
        d = DEF.setdefault((t, g['kolo']), dict(pos=pos(oo), fta=oo['freeThrowsAttempted'], ftm=oo['freeThrowsMade'], ar=0, mr=0, am=0, mm=0, at=0, mt=0))
        for pl in g['s'][st]['players']:
            n = pl['player']['person']['name']; b = pl['stats']; POS[(n, t)] = POZ.get(pl['player'].get('positionName'), 'F')
            if not b['timePlayed']: continue
            LOG.setdefault((n, t), {})[g['kolo']] = dict(min=b['timePlayed'] / 60, kod=g['kod'], dom=dom, opp=o, fta=b['freeThrowsAttempted'], ftm=b['freeThrowsMade'], **{k: b[STAT[k]] for k in K3})
    for x in g['p']:
        ty, zn, n, t = x['ID_ACTION'].strip(), (x['ZONE'] or '').strip(), x['PLAYER'].strip(), x['TEAM'].strip()
        if ty[:1] == '3': v = 't'
        elif ty[:1] == '2': v = 'r' if zn in 'ABC' and zn else 'm'
        else: continue
        o = a if t == h else h
        for c in (ZON.setdefault((n, t, g['kolo']), {}), DEF.setdefault((o, g['kolo']), dict(pos=0, fta=0, ftm=0, ar=0, mr=0, am=0, mm=0, at=0, mt=0))):
            c['a' + v] = c.get('a' + v, 0) + 1
            if ty.endswith('M'): c['m' + v] = c.get('m' + v, 0) + 1

def pre_kola(R):
    """Sve što se znalo pre kola R: dozvoljeno po poziciji, tempo, odbrana po zonama."""
    pa, lg = {}, {}
    for (n, t), h in LOG.items():
        for r, v in h.items():
            if r >= R: continue
            e = pa.setdefault((v['opp'], POS[(n, t)]), [0.0, 0, 0, 0, set()]); e[0] += v['min']; e[1] += v['pts']; e[2] += v['reb']; e[3] += v['ast']; e[4].add(r)
    al = {k: dict(n=len(e[4]), pts=e[1] / e[0] * 40, reb=e[2] / e[0] * 40, ast=e[3] / e[0] * 40) for k, e in pa.items() if e[0]}
    for (t, p), e in al.items():
        for k in K3: lg.setdefault((p, k), []).append(e[k])
    lg = {k: sum(v) / len(v) for k, v in lg.items()}
    tp = {}
    for (t, r), v in TEAM_R.items():
        if r < R: tp.setdefault(t, []).append(v)
    pace = {t: sum(v) / len(v) for t, v in tp.items()}; lp = sum(pace.values()) / len(pace)
    D = {}
    for (t, r), d in DEF.items():
        if r >= R: continue
        c = D.setdefault(t, dict(pos=0, fta=0, ftm=0, ar=0, mr=0, am=0, mm=0, at=0, mt=0))
        for k in c: c[k] += d.get(k, 0)
    LGD = {k: sum(c[k] for c in D.values()) for k in ('pos', 'fta', 'ftm', 'ar', 'mr', 'am', 'mm', 'at', 'mt')}
    return dict(al=al, lg=lg, pace=pace, lp=lp, D=D, LGD=LGD)
def zona(n, t, o, R, S):
    z = {}; ft = [0, 0]; mins = 0
    for r, v in LOG[(n, t)].items():
        if r >= R: continue
        mins += v['min']; ft[0] += v['fta']; ft[1] += v['ftm']
        for k, x in ZON.get((n, t, r), {}).items(): z[k] = z.get(k, 0) + x
    d, L = S['D'].get(o), S['LGD']
    if not d or not mins or not d['pos']: return 1.0
    base = adj = 0.0
    for v in Z:
        a, m = z.get('a' + v, 0), z.get('m' + v, 0); lp = L['m' + v] / L['a' + v]
        pct = (m + lp * 15) / (a + 15)
        fa = (d['a' + v] / d['pos']) / (L['a' + v] / L['pos']); fa = 1 + (fa - 1) * 8 / 14
        dp = (d['m' + v] / d['a' + v]) / lp if d['a' + v] else 1; dp = 1 + (dp - 1) * 0.5 * 8 / 14
        b = a / mins * pct * VAL[v]; base += b; adj += b * fa * dp
    b = ft[0] / mins * (ft[1] + 0.77 * 20) / (ft[0] + 20); ff = (d['fta'] / d['pos']) / (L['fta'] / L['pos']); ff = 1 + (ff - 1) * 8 / 14
    base += b; adj += b * ff
    return adj / base if base else 1.0
PUNI = dict(ls=1, protivnik=1, zona=1, teren=1, tempo=1, zaborav=1)
def proj(n, t, R, S, f, min_tacni=None):
    h = {r: v for r, v in LOG[(n, t)].items() if r < R}
    if len(h) < 2: return None
    rr = sorted(h); dec = DECAY if f['zaborav'] else 1.0; w = [dec ** (R - 1 - r) for r in rr]
    mp = sum(a * h[r]['min'] for a, r in zip(w, rr)) / sum(w); M = sum(a * h[r]['min'] for a, r in zip(w, rr))
    akt = LOG[(n, t)][R]; o, dom = akt['opp'], akt['dom']; pos = POS[(n, t)]
    if min_tacni: mp = akt['min']
    hf = (1.02 if dom else 0.98) if f['teren'] else 1.0
    pf = ((S['pace'].get(t, S['lp']) + S['pace'].get(o, S['lp'])) / 2) / S['lp'] if f['tempo'] else 1.0
    zf = zona(n, t, o, R, S) if f['zona'] else 1.0
    out = {}
    for k in K3:
        pri = S['lg'].get((pos, k), 0) / 40; pw = PW; ls = LS.get(n)
        if f['ls'] and ls and ls.get('min', 0) >= 150: pri = ls[k] / ls['min']; pw = min(20, 0.02 * ls['min'])
        rate = (sum(a * h[r][k] for a, r in zip(w, rr)) + pri * pw) / (M + pw)
        of = 1.0
        al = S['al'].get((o, pos))
        if f['protivnik'] and al and S['lg'].get((pos, k)): of = 1 + (al[k] / S['lg'][(pos, k)] - 1) * al['n'] / (al['n'] + 6)
        if k == 'pts': of = (0.4 * of + 0.6 * zf) if f['protivnik'] or f['zona'] else 1.0
        mu = rate * mp * of * hf * pf
        v = [h[r][k] for r in rr]; av = sum(v) / len(v); sdE2 = sum((x - av) ** 2 for x in v) / max(1, len(v) - 1)
        out[k] = (mu, math.sqrt((sdE2 * len(v) + max(mu, 0.5) * SD_C[k] ** 2 * SD_W) / (len(v) + SD_W)))
    return out
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
def greske(f, min_tacni=False):
    e = {}
    for n, t, R in UZ:
        p = proj(n, t, R, SVE[R], f, min_tacni); a = LOG[(n, t)][R]
        for k in K3:
            mu, sd = p[k]; y = a[k]; ll = s = 0
            for o in (-1, 0, 1):
                L = max(math.floor(mu) + 0.5 + o, 0.5); q = min(max(1 - N.cdf((L - mu) / sd), .02), .98); ll += -math.log(q if y > L else 1 - q); s += 1
            e[(n, t, R, k)] = (abs(y - mu), ll / s, a['kod'], R)
    return e
def interval(osn, nov, k, test=None):
    grupe = {}
    for key, v in nov.items():
        if key[3] != k or (test and key[2] not in test): continue
        grupe.setdefault(v[2], []).append(v[0] - osn[key][0])
    g = list(grupe.values()); rng = random.Random(7); m = sum(map(sum, g)) / sum(map(len, g)); b = []
    for _ in range(1500):
        u = [g[rng.randrange(len(g))] for _ in g]; b.append(sum(map(sum, u)) / sum(map(len, u)))
    b.sort(); return m, b[37], b[1462]
MAE = lambda e, k, test=None: (lambda x: sum(x) / len(x))([v[0] for key, v in e.items() if key[3] == k and (not test or key[2] in test)])
LL = lambda e, k: (lambda x: sum(x) / len(x))([v[1] for key, v in e.items() if key[3] == k])
print(f'Uzorak: {len(UZ)} igrač-utakmica, kola 3-{max(KOLA)}, {len(K_OF)} utakmica u kešu\n')
pun = greske(PUNI)
print('Pun model:', ' | '.join(f"{k} MAE {MAE(pun, k):.3f} logloss {LL(pun, k):.4f}" for k in K3))
print('\nUTICAJ FAKTORA: koliko se greška poveća kad se faktor isključi (plus = faktor pomaže; interval je 95%)')
print(f"{'isključen':<12}" + ''.join(f'{k:>27}' for k in K3))
rez = {}
for fk in ('ls', 'protivnik', 'zona', 'teren', 'tempo', 'zaborav'):
    e = greske({**PUNI, fk: 0}); red = f'{fk:<12}'; rez[fk] = e
    for k in K3:
        m, lo, hi = interval(pun, e, k); red += f'{m:>+9.3f} [{lo:+.3f},{hi:+.3f}] ' + ('*' if lo > 0 or hi < 0 else ' ')
    print(red)
print('(* = interval ne obuhvata nulu; samo tada se može reći da faktor stvarno pomaže ili šteti)')
print('\nSamo kola 8-9, kao provera stabilnosti (plus = pomaže):')
for fk, e in rez.items(): print(f'{fk:<12}' + ''.join(f'{interval(pun, e, k, (8, 9))[0]:>+9.3f}' for k in K3))
print('\nODAKLE DOLAZI GREŠKA: da unapred znamo tačne minute')
tm = greske(PUNI, True)
for k in K3: print(f'  {k}: MAE {MAE(pun, k):.3f} -> {MAE(tm, k):.3f}  ({(1 - MAE(tm, k) / MAE(pun, k)) * 100:.0f}% manje)')
mins = []
for n, t, R in UZ:
    h = {r: v for r, v in LOG[(n, t)].items() if r < R}; rr = sorted(h); w = [DECAY ** (R - 1 - r) for r in rr]
    mins.append(abs(LOG[(n, t)][R]['min'] - sum(a * h[r]['min'] for a, r in zip(w, rr)) / sum(w)))
print(f'  greška minuta: prosečno {sum(mins) / len(mins):.2f} min; preko 8 min u {sum(m > 8 for m in mins) / len(mins) * 100:.0f}% utakmica')
print('\n9. KOLO PREMA KVOTAMA (evidencija.json): manji logloss je bolja procena')
E = [e for e in citaj('evidencija.json') if e.get('proslo_vise') in (True, False) and e.get('kvota_vise') and e.get('kvota_manje') and e.get('trz_vise') is not None]
ll = lambda p, y: -math.log(min(max(p, .02), .98) if y else 1 - min(max(p, .02), .98))
Mx = lambda e: (1 / e['kvota_vise']) / (1 / e['kvota_vise'] + 1 / e['kvota_manje'])
H = lambda e: (lambda a: (int(a[0]) + 1) / (int(a[1]) + 2))(e['ist_vise'].split('/'))
IZ = {'Maxbet bez marže': Mx, 'Tržište (ostale kladionice)': lambda e: e['trz_vise'], 'Model': lambda e: e['p_model_vise'], 'Istorija sezone': H, 'Šansa (model+istorija)': lambda e: e['sansa_vise']}
print(f'  linija {len(E)}, igrača {len({e["igrac"] for e in E})}')
sk = {n: sum(ll(f(e), e['proslo_vise']) for e in E) / len(E) for n, f in IZ.items()}
for n, v in sorted(sk.items(), key=lambda x: x[1]): print(f'  {n:<30} {v:.4f}')
ig = {}
for e in E: ig.setdefault(e['igrac'], []).append(ll(e['p_model_vise'], e['proslo_vise']) - ll(Mx(e), e['proslo_vise']))
g = list(ig.values()); rng = random.Random(7); b = []
for _ in range(1500):
    u = [g[rng.randrange(len(g))] for _ in g]; b.append(sum(map(sum, u)) / sum(map(len, u)))
b.sort(); print(f'  model minus Maxbet: {sum(map(sum, g)) / sum(map(len, g)):+.4f} [{b[37]:+.4f}, {b[1462]:+.4f}]  (minus = model bolji od Maxbeta)')
print('  opklade gde model vidi prednost, ravan ulog (svaka linija, jedno kolo):')
for prag in (0.03, 0.06, 0.10):
    pr = n = 0
    for e in E:
        m, x = e['p_model_vise'], Mx(e)
        if m - x > prag: n += 1; pr += e['kvota_vise'] - 1 if e['proslo_vise'] else -1
        elif x - m > prag: n += 1; pr += e['kvota_manje'] - 1 if not e['proslo_vise'] else -1
    print(f'    razlika preko {prag:.0%}: {n} opklada, povraćaj {pr / n * 100 if n else 0:+.1f}%')
