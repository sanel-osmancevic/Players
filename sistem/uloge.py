# Preraspodela uloge kad saigrač ne igra (tačka 2).
# Iz play-by-play (onoff_k8.json): za igrača i i odsutnog saigrača j -> učinak po minuti kad je j van terena
# naspram ukupnog proseka. Poeni preko šuteva (FGA + 0.44*FTA), skokovi i asistencije direktno.
# Skupljanje ka proseku (K minuta), više odsutnih se množi, ukupna korekcija ograničena na ±20%.
# Upisuje faktore u igraci2.json (pts/reb/ast_proj) i uloge.json (objašnjenje).
import json, re, unicodedata, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))

OUT = {  # sigurno ne igraju danas (izveštaj o povredama 30.10.)
    'PAR': ['JEKIRI, TONYE'], 'PAM': ['MIROTIC, NIKOLA', 'REUVERS, NATHAN'],
    'BAS': ['KURUCS, RODIONS', 'SEDEKERSKIS, TADAS', 'DUARTE, CHRIS'],
    'OLY': ['FOURNIER, EVAN', 'MONTERO, JEAN', 'DORSEY, TYLER'], 'MIL': ['PETERS, ALEC'],
    'IST': ['JAMES, MIKE', 'DOZIER, PJ'], 'DUB': ['WALKUP, THOMAS'], 'BES': ['KORKMAZ, FURKAN']}
TEAM = {'DUB': 'Dubai', 'HTA': 'Hapoel TA', 'IST': 'Anadolu Efes', 'PAN': 'Panathinaikos', 'ZAL': 'Žalgiris', 'PAR': 'Partizan',
        'ASV': 'ASVEL', 'BAS': 'Baskonia', 'OLY': 'Olympiacos', 'MIL': 'Olimpia Milano', 'BAR': 'Barcelona', 'PAM': 'Valencia',
        'VIR': 'Virtus', 'BES': 'Beşiktaş'}
K = 60.0      # minuta "prior" uzorka
KE = 10.0     # i bar 10 događaja (šuteva, skokova, asistencija)
CAP = 0.15    # najviše ±15% ukupno
DAMP = 1.0
# kola u kojima je odsutni igrao (kola 1–8), da bi se korekcija računala prema težinama modela (0.85^(8-kolo))
IGRAO = {'JEKIRI, TONYE': [1,2,3,4,5,6], 'MIROTIC, NIKOLA': [1,2,3,4,5,6,7,8], 'REUVERS, NATHAN': [1,2,3,4,5,6,7],
         'KURUCS, RODIONS': [1,2,3,4,5,6,7], 'SEDEKERSKIS, TADAS': [1,2,3,4,5,6,7], 'DUARTE, CHRIS': [1,2,3,4,5,6],
         'FOURNIER, EVAN': [1,2,3,4,5,6], 'MONTERO, JEAN': [1,2,3,4,5,6], 'DORSEY, TYLER': [1,2,3,4,5],
         'PETERS, ALEC': [1,2,3,4,5,6,7], 'JAMES, MIKE': [1,2,3], 'DOZIER, PJ': [1,2,3,4,5,6],
         'WALKUP, THOMAS': [1,2,3,4,5,6], 'KORKMAZ, FURKAN': [2,3,4,5,6]}
LOG = {}
def _log():
    if not LOG:
        for f_ in ('data9.json', 'data9b.json', 'data9c.json'):
            for n, pos, t, rr, mm, *_ in json.load(open(f_))['P']:
                LOG[(sur(n), t)] = ([int(x) for x in rr.split(',')], [float(x) for x in mm.split(',')])
    return LOG
def udeo(i_sur, tc, j):
    """odnos: (težinski udeo minuta igrača i u kolima gde je j igrao) / (obični udeo)"""
    lg = _log().get((i_sur, tc)); played = set(IGRAO.get(j, range(1, 9)))
    if not lg: return 1.0
    rr, mm = lg; w = [0.85 ** (8 - r) for r in rr]
    sw = sum(wi * m for wi, m, r in zip(w, mm, rr) if r in played) / max(1e-9, sum(wi * m for wi, m in zip(w, mm)))
    su = sum(m for m, r in zip(mm, rr) if r in played) / max(1e-9, sum(mm))
    return sw / su if su > 0 else 1.0

def norm(s): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
def sur(name):  # "HAYES, KEVARRIUS" -> hayes ; "Kevarrius Hayes" -> hayes
    if ',' in name: return norm(name.split(',')[0].replace(' IV', '').replace(' JR.', '').replace(' JR', ''))
    t = [w for w in name.split() if w.lower().strip('.') not in ('iv', 'iii', 'jr', 'ii')]
    return norm(t[-1])

D = json.load(open('onoff_k8.json'))

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
    rows = json.load(open('igraci2.json')); out = []
    for r in rows:
        if not r['termin'].startswith('pet'): continue
        f = fakt.get((sur(r['igrac']), r['tim']))
        if not f: continue
        for k in ('pts', 'reb', 'ast'):
            r[f'{k}_proj'] = round(r[f'{k}_proj'] * f[k], 1)
            r[f'uloga_{k}'] = round((f[k] - 1) * 100, 1)
        r['uloga_zbog'] = '; '.join(f['zbog'])
        if any(abs(f[k] - 1) >= 0.03 for k in ('pts', 'reb', 'ast')):
            out.append(dict(igrac=r['igrac'], tim=r['tim'], **{k: round((f[k] - 1) * 100, 1) for k in ('pts', 'reb', 'ast')}, zbog=r['uloga_zbog']))
    json.dump(rows, open('igraci2.json', 'w'), ensure_ascii=False)
    json.dump(out, open('uloge.json', 'w'), ensure_ascii=False)
    if '-v' in sys.argv:
        for o in sorted(out, key=lambda o: -max(abs(o['pts']), abs(o['reb']), abs(o['ast']))):
            print(f"{o['igrac'][:22]:22s} {o['tim'][:12]:12s} poeni {o['pts']:+5.1f}% skok {o['reb']:+5.1f}% ast {o['ast']:+5.1f}%  | {o['zbog'][:110]}")
    print('korigovano igrača:', len(out))
