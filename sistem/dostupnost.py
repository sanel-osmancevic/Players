# Minuti prema sastavu: povrede i povratci ključnih igrača.
# Za svakog igrača minuti se računaju iz kola u kojima je sastav tima ličio na današnji
# (ko od ključnih saigrača je igrao / nije igrao). Kola sa drugačijim sastavom dobijaju manju težinu.
#  - Ključni igrač ne igra danas  -> više težine kolima kad ga nije bilo (npr. Olympiacos bez bekova: više minuta za Miller-McIntyrea i Warda)
#  - Ključni igrač se vratio      -> kola dok ga nije bilo gube težinu (npr. Nebo se vratio: manje minuta za Balcerowskog)
#  - Ključni igrač je upitan      -> računaju se oba scenarija; ako se minuti nekog saigrača razlikuju 3+ min (ili 15%+),
#                                   igrač dobija oznaku "rizik uloge" i ne ulazi u preporuke
# Pokreće se posle build5.py, pre adjust3.py. Menja minuti_proj i srazmerno pts/reb/ast_proj u igraci2.json.
import json, os, re, sys
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from uloge import OUT, IGRAO

MIS = float(os.environ.get('MIS',0.5))        # težina kola u kojem je stanje ključnog saigrača bilo drugačije od današnjeg
KEY_MIN = 15.0    # ključni igrač: prosek 15+ minuta
P_UPITAN = 0.5    # verovatnoća da igra kad je "Upitan"
P_VEROVATNO_NE = 0.3
RIZIK_MIN, RIZIK_REL = 3.0, 0.15
CAP_REL, CAP_ABS = 0.30, 7.0
SHR = float(os.environ.get('SHR',0.5))   # koliko verujemo razlici (ostatak ide ka osnovnim minutima)
RECENT = int(os.environ.get('RECENT',3))  # izostanak u poslednja 3 kola čini igrača bitnim za sastav
P_POVRATAK = float(os.environ.get('PPOV',0.65))  # prvi meč posle izostanka: minuti obično ograničeni

# ručno umanjenje minuta iz rucno_kolo.json (npr. povratak posle pauze) mora da preživi ovaj preračun (od 11.11.2026)
_rk = citaj('rucno_kolo.json') if os.path.exists('rucno_kolo.json') else {}
from kolo import KOLO as _KOLO
MINUS = {k.split('|')[0]: v for k, v in (_rk.get('minuti', {}) if _rk.get('kolo') == _KOLO else {}).items() if v < 0}
P = [p for f in ('statistika.json',) for p in citaj(f)['P']]
LOG = {}
for n, pos, t, rr, mm, *_ in P:
    LOG[n] = dict(t=t, r=[int(x) for x in rr.split(',')], m=[float(x) for x in mm.split(',')])
TEAMR = {}
for n, x in LOG.items(): TEAMR.setdefault(x['t'], set()).update(x['r'])
LAST = max(max(v) for v in TEAMR.values())

rows = citaj('igraci2.json')
CODE = {}
for r in rows:
    if r['api'] in LOG: CODE[r['tim']] = LOG[r['api']]['t']

# današnja verovatnoća da igra
def p_igra(r):
    s, note = r['status'], (r.get('napomena') or '').lower()
    if s == 'Ne igra': return P_VEROVATNO_NE if 'upitan' in note else 0.0
    if s == 'Upitan': return P_UPITAN
    return 1.0
PI = {}
for r in rows: PI[r['api']] = p_igra(r)
for tc, outs in OUT.items():
    for j in outs: PI.setdefault(j, 0.0)

# kola u kojima je igrač igrao
def odigrao(j):
    if j in LOG: return set(LOG[j]['r'])
    return set(IGRAO.get(j, []))
def tim(j):
    if j in LOG: return LOG[j]['t']
    for tc, outs in OUT.items():
        if j in outs: return tc

# ključni igrači po timu (čije se prisustvo menjalo kroz kola ili su danas van/upitni)
KEY = {}
for j in sorted(set(LOG) | set(IGRAO)):   # stalan redosled, da se objašnjenja ne menjaju bez razloga
    tc = tim(j)
    if not tc: continue
    pl = odigrao(j); avg = (sum(LOG[j]['m']) / len(LOG[j]['m'])) if j in LOG else 20.0
    skoro = any(r not in pl for r in TEAMR.get(tc, ()) if r > LAST - RECENT)
    menja = skoro or PI.get(j, 1.0) < 1
    if avg >= KEY_MIN and len(pl) >= 2 and menja: KEY.setdefault(tc, []).append(j)

def minuti(i, stanje):
    """ponderisani minuti igrača i; stanje: {j: True/False igra danas}"""
    x = LOG[i]; tc = x['t']; num = den = 0.0
    for r, m in zip(x['r'], x['m']):
        w = 0.9 ** (LAST - r)
        for j, igra in stanje.items():
            if j == i: continue
            if (r in odigrao(j)) != igra: w *= MIS
        num += w * m; den += w
    return num / den if den else None
def osnovno(i):
    x = LOG[i]; w = [0.9 ** (LAST - r) for r in x['r']]
    return sum(a * b for a, b in zip(w, x['m'])) / sum(w)

out = []; POV = {}
for r in rows:
    i = r['api']
    if i not in LOG or r['status'] == 'Ne igra' or not r.get('minuti_proj'): continue
    tc = LOG[i]['t']; keys = [j for j in KEY.get(tc, []) if j != i]
    if not keys: continue
    sig = {j: PI.get(j, 1.0) >= 0.999 for j in keys if PI.get(j, 1.0) in (0.0, 1.0) or PI.get(j, 1.0) >= 0.999}
    for j in keys:
        if PI.get(j, 1.0) >= 0.999 and LAST in TEAMR[tc] and LAST not in odigrao(j): sig.pop(j, None); POV[j] = True
    unc = [j for j in keys if 0 < PI.get(j, 1.0) < 0.999 or POV.get(j)]
    # danas van, a nikad ranije nije izostao -> nema uporedivih kola, ostaje strukturni dodatak iz build5
    nevidjeno = [j for j in keys if PI.get(j, 1.0) == 0 and not (TEAMR[tc] - odigrao(j))]
    for j in nevidjeno: sig.pop(j, None)
    # scenariji za upitne
    scen = [({}, 1.0)]
    for j in unc:
        p = P_POVRATAK if POV.get(j) else PI[j]; scen = [(dict(s, **{j: True}), w * p) for s, w in scen] + [(dict(s, **{j: False}), w * (1 - p)) for s, w in scen]
    vals = [(minuti(i, dict(sig, **s)), w) for s, w in scen]
    m_new = sum(v * w for v, w in vals); base = osnovno(i)
    stari = r['minuti_proj']
    bonus = max(0.0, stari - base) if (nevidjeno or os.environ.get("KEEPB")) else 0.0
    novi = base + SHR * (m_new - base) + bonus + MINUS.get(i, 0.0)
    novi = max(stari - CAP_ABS, min(stari + CAP_ABS, novi))
    novi = max(stari * (1 - CAP_REL), min(stari * (1 + CAP_REL), novi))
    zbog = []
    for j in keys:
        if j in nevidjeno: continue
        sa, bez = minuti(i, dict(sig, **{j: True})), minuti(i, dict(sig, **{j: False}))
        if abs(sa - bez) >= 2.5:
            ime = j.split(',')[0].title()
            stanje = 'van' if PI.get(j, 1) == 0 else ('upitan' if PI.get(j, 1) < 1 else 'igra')
            zbog.append(f"{ime} ({stanje}): sa njim {sa:.0f} min, bez njega {bez:.0f}")
    # povratak: j je propustio kola pa se vratio u poslednja 2 kola ili se vraća danas
    for j in keys:
        pl = odigrao(j); izost = sorted(TEAMR[tc] - pl)
        if izost and PI.get(j, 1) == 1 and max(izost) >= LAST - 3 and max(izost) < LAST or (izost and max(izost) == LAST and PI.get(j, 1) == 1):
            sa, bez = minuti(i, dict(sig, **{j: True})), minuti(i, dict(sig, **{j: False}))
            if bez - sa >= 2.5: r['povratak'] = f"{j.split(',')[0].title()} se vratio: {i.split(',')[0].title()} sa njim {sa:.0f} min, bez njega {bez:.0f}"
    rizik = None
    if len([j for j in unc if not POV.get(j)]) and len(vals) > 1:
        lo, hi = min(v for v, _ in vals), max(v for v, _ in vals)
        if hi - lo >= max(RIZIK_MIN, RIZIK_REL * hi):
            rizik = 'Uloga zavisi od ' + ', '.join(j.split(',')[0].title() for j in unc) + f" (upitan): {lo:.0f}–{hi:.0f} min"
    f = novi / stari if stari else 1.0
    r['minuti_sastav'] = round(novi, 1); r['minuti_pre_sastava'] = stari; r['sastav_zbog'] = '; '.join(zbog)
    if rizik: r['rizik_uloge'] = rizik
    if abs(f - 1) >= 0.01:
        r['minuti_proj'] = round(novi, 1)
        for k in ('pts', 'reb', 'ast'): r[f'{k}_proj'] = round(r[f'{k}_proj'] * f, 1)
    if abs(f - 1) >= 0.05 or rizik or r.get('povratak'):
        out.append((r['igrac'], r['tim'], stari, round(novi, 1), rizik or '', r.get('povratak', ''), '; '.join(zbog)[:120]))
# izgubio startnu poziciju: startovao većinu ranijih kola, a u poslednjem kolu nije (npr. Balcerowski kad je Nebo vraćen u start)
for n, pos, t, rr, mm, ss, *_ in P:
    LOG[n]['s'] = [int(c) for c in ss]
for r in rows:
    x = LOG.get(r['api'])
    if not x or r['status'] == 'Ne igra' or len(x['s']) < 4 or x['r'][-1] != LAST: continue
    ranije = x['s'][:-1]
    if sum(ranije) / len(ranije) >= 0.6 and x['s'][-1] == 0:
        mr = [m for m, s in zip(x['m'][:-1], ranije) if s]; pad = (sum(mr) / len(mr)) - x['m'][-1]
        if pad >= 3:
            msg = f"Izgubio start u {LAST}. kolu: {x['m'][-1]:.0f} min naspram {sum(mr)/len(mr):.0f} kao starter"
            r['rizik_uloge'] = (r.get('rizik_uloge', '') + '; ' if r.get('rizik_uloge') else '') + msg
            out.append((r['igrac'], r['tim'], r['minuti_proj'], r['minuti_proj'], msg, '', ''))
# Stabilnost: status startera (poslednjih 5) i "nemir" rotacije tima (prosečno relativno kolebanje minuta igrača sa 10+ min).
# Provera na sezoni (kola 3–9): greška minuta — mirni timovi 21%, nemirni 29%; sigurni starteri 19%, klupa 29%.
# Koristi se u pravilu za Najsigurnije (stranica): bez klupe i bez najnemirnijih timova (gornja trećina).
import statistics as _S
NEM = {}
for n, x in LOG.items():
    if len(x['m']) >= 2 and _S.mean(x['m']) >= 10: NEM.setdefault(x['t'], []).append(_S.stdev(x['m']) / _S.mean(x['m']))
NEM = {t: _S.mean(v) for t, v in NEM.items()}
LGN = _S.mean(NEM.values()); NEMR = {t: v / LGN for t, v in NEM.items()}
PRAG = sorted(NEMR.values())[int(len(NEMR) * 2 / 3)]
for r in rows:
    x = LOG.get(r['api'])
    if not x: continue
    s5 = x.get('s', [])[-5:]
    r['starter_status'] = ('siguran starter' if s5 and sum(s5) == len(s5) and x['r'][-1] == LAST else
                           'pretežno starter' if s5 and sum(s5) / len(s5) >= 0.6 else 'klupa')
    r['nemir_tim'] = round(NEMR.get(x['t'], 1.0), 2); r['nemir_tim_visok'] = NEMR.get(x['t'], 1.0) >= PRAG
pisi(rows, 'igraci2.json', ensure_ascii=False)
print('sastav: korigovano', len(out), 'igrača; rizik uloge:', sum(1 for o in out if o[4]))
if '-v' in sys.argv:
    for o in sorted(out, key=lambda o: -abs(o[3] - o[2])): print(f"{o[0][:22]:22s} {o[1][:12]:12s} {o[2]:5.1f} -> {o[3]:5.1f}  {o[4]} {o[5]} | {o[6]}")
