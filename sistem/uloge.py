# Preraspodela uloge kad saigrač ne igra (tačka 2).
# Iz play-by-play (onoff_k8.json): za igrača i i odsutnog saigrača j -> učinak po minuti kad je j van terena
# naspram ukupnog proseka. Poeni preko šuteva (FGA + 0.44*FTA), skokovi i asistencije direktno.
# Skupljanje ka proseku (K minuta), više odsutnih se množi, ukupna korekcija ograničena na ±20%.
# Upisuje faktore u igraci2.json (pts/reb/ast_proj) i uloge.json (objašnjenje).
import json, re, unicodedata, os, sys
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from kolo import DAN, IME as TEAM, KOD

# sigurno ne igraju danas: statusi iz igraci2.json (build5.py), koji uključuju zvaničan izveštaj i ručne izmene
OUT = {}
for _r in citaj('igraci2.json'):
    if _r['status'] == 'Ne igra' and 'upitan' not in (_r.get('napomena') or '').lower(): OUT.setdefault(KOD[_r['tim']], []).append(_r['api'])
K = 60.0      # minuta "prior" uzorka
KE = 10.0     # i bar 10 događaja (šuteva, skokova, asistencija)
CAP = 0.15    # najviše ±15% ukupno
DAMP = 1.0
# kola u kojima je odsutni igrao, da bi se korekcija računala prema težinama modela (0.85^(poslednje kolo - kolo))
_P = citaj('statistika.json')['P']
IGRAO = {p[0]: [int(x) for x in p[3].split(',')] for p in _P}
LASTR = max(r for v in IGRAO.values() for r in v)
LOG = {}
def _log():
    if not LOG:
        for f_ in ('statistika.json',):
            for n, pos, t, rr, mm, *_ in citaj(f_)['P']:
                LOG[(sur(n), t)] = ([int(x) for x in rr.split(',')], [float(x) for x in mm.split(',')])
    return LOG
def udeo(i_sur, tc, j):
    """odnos: (težinski udeo minuta igrača i u kolima gde je j igrao) / (obični udeo)"""
    lg = _log().get((i_sur, tc)); played = set(IGRAO.get(j, range(1, LASTR + 1)))
    if not lg: return 1.0
    rr, mm = lg; w = [0.85 ** (LASTR - r) for r in rr]
    sw = sum(wi * m for wi, m, r in zip(w, mm, rr) if r in played) / max(1e-9, sum(wi * m for wi, m in zip(w, mm)))
    su = sum(m for m, r in zip(mm, rr) if r in played) / max(1e-9, sum(mm))
    return sw / su if su > 0 else 1.0

def norm(s): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
def sur(name):  # "HAYES, KEVARRIUS" -> hayes ; "Kevarrius Hayes" -> hayes
    if ',' in name: return norm(name.split(',')[0].replace(' IV', '').replace(' JR.', '').replace(' JR', ''))
    t = [w for w in name.split() if w.lower().strip('.') not in ('iv', 'iii', 'jr', 'ii')]
    return norm(t[-1])

D = citaj('onoff_k8.json')

def usage(v): return v[2] + 0.44 * v[3]

fakt = {}  # (sur, team) -> {'pts':f,'reb':f,'ast':f,'zbog':[...]}
for tc, outs in OUT.items():
    d = D.get(tc)
    if not d: continue
    for i, tot in d['tot'].items():
        if i in outs or tot[0] < 40: continue
        f = {'pts': 1.0, 'reb': 1.0, 'ast': 1.0}; zbog = []
        for j in outs:
            on = d['on'].get(j, {}).get(i)
            if on is None: on = [0, 0, 0, 0, 0, 0]
            moff = tot[0] - on[0]
            if moff <= 0: continue
            parts = {}
            for k, get in (('pts', usage), ('reb', lambda v: v[4]), ('ast', lambda v: v[5])):
                rt = get(tot) / tot[0]
                if rt <= 0: continue
                kk = max(K, KE / rt)   # bar KE događaja vrednosti u "prioru"
                off = (get(tot) - get(on) + rt * kk) / (moff + kk)
                # model vidi mešavinu: deo sa j je manji kad je j skoro izostajao
                mix = off + (rt - off) * udeo(sur(i), tc, j)
                r = off / mix
                f[k] *= r; parts[k] = r
            if any(abs(v - 1) >= 0.05 for v in parts.values()):
                zbog.append(f"{j.split(',')[0].title()}: " + ', '.join(f"{k} {100*(v-1):+.0f}%" for k, v in parts.items() if abs(v - 1) >= 0.05))
        for k in f:
            f[k] = max(1 - CAP, min(1 + CAP, f[k] ** DAMP))
        fakt[(sur(i), TEAM[tc])] = dict(f, zbog=zbog)

if __name__ == '__main__':
    rows = citaj('igraci2.json'); out = []
    for r in rows:
        if not r['termin'].startswith(DAN): continue
        f = fakt.get((sur(r['igrac']), r['tim']))
        if not f: continue
        for k in ('pts', 'reb', 'ast'):
            r[f'{k}_proj'] = round(r[f'{k}_proj'] * f[k], 1)
            r[f'uloga_{k}'] = round((f[k] - 1) * 100, 1)
        r['uloga_zbog'] = '; '.join(f['zbog'])
        if any(abs(f[k] - 1) >= 0.03 for k in ('pts', 'reb', 'ast')):
            out.append(dict(igrac=r['igrac'], tim=r['tim'], **{k: round((f[k] - 1) * 100, 1) for k in ('pts', 'reb', 'ast')}, zbog=r['uloga_zbog']))
    pisi(rows, 'igraci2.json', ensure_ascii=False)
    pisi(out, 'uloge.json', ensure_ascii=False)
    if '-v' in sys.argv:
        for o in sorted(out, key=lambda o: -max(abs(o['pts']), abs(o['reb']), abs(o['ast']))):
            print(f"{o['igrac'][:22]:22s} {o['tim'][:12]:12s} poeni {o['pts']:+5.1f}% skok {o['reb']:+5.1f}% ast {o['ast']:+5.1f}%  | {o['zbog'][:110]}")
    print('korigovano igrača:', len(out))
