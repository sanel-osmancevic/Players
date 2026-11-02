# Priprema kola: iz zvaničnog API-ja pravi statistiku svih odigranih kola i raspored kola koje dolazi.
# Upotreba: py -X utf8 pripremi_kolo.py KOLO        -> statistika.json, faulovi.json, kolo.json, odmor u minute_timovi.json
#           py -X utf8 pripremi_kolo.py --provera   -> računa kola 1-8 i poredi sa data9*.json, ništa ne upisuje
# Zapisnici odigranih utakmica čuvaju se u api_kes/, pa se isti zahtev ne šalje dvaput.
import json, os, subprocess, sys, time, datetime, collections
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
A, SEZONA, KES = 'https://api-live.euroleague.net', 'E2026', 'api_kes'
RACKET = 'ABC'                  # zone blizu koša u Points API-ju; H, I, J su trojke
POZ = {'Guard': 'G', 'Forward': 'F', 'Center': 'C'}
MIN_UTAKMICA, MIN_MINUTA = 3, 40   # igrač ulazi u model tek sa ovoliko odigranog
DANI = ['pon', 'uto', 'sre', 'čet', 'pet', 'sub', 'ned']

def preuzmi(u, f=None):
    p = os.path.join(KES, f) if f else None
    if p and os.path.exists(p): return citaj(p)
    for pokusaj in range(8):
        o = subprocess.run(['curl', '-s', '-w', '\n%{http_code}', '--max-time', '30', u], capture_output=True)
        telo, _, kod = o.stdout.rpartition(b'\n')
        if kod == b'200':
            time.sleep(1 if not p else 3)   # server ograničava brzinu
            if p:
                os.makedirs(KES, exist_ok=True)
                with open(p, 'wb') as h: h.write(telo)
            return json.loads(telo)
        print('zahtev', u.split('/')[-1], 'vratio', kod.decode(), '- čekam', flush=True)
        time.sleep(300 if kod == b'429' else 30)
    raise SystemExit('API nije dostupan: ' + u)

def utakmice(k): return preuzmi(f'{A}/v2/competitions/E/seasons/{SEZONA}/games?roundNumber={k}')['data']

def beograd(iso):   # CET/CEST bez zoneinfo baze: letnje vreme od poslednje nedelje marta do poslednje nedelje oktobra u 01:00 UTC
    d = datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))
    pn = lambda m: max(datetime.datetime(d.year, m, x, 1, tzinfo=datetime.timezone.utc) for x in range(25, 32) if datetime.date(d.year, m, x).weekday() == 6)
    return d + datetime.timedelta(hours=2 if pn(3) <= d < pn(10) else 1)

def statistika(do_kola):
    box = {}; sp = collections.defaultdict(lambda: collections.Counter()); D = collections.defaultdict(lambda: collections.Counter())
    pa = collections.defaultdict(lambda: [0.0, 0, 0, 0, set()]); tim = collections.defaultdict(lambda: collections.Counter()); faul = {}; poz = {}
    for k in range(1, do_kola + 1):
        for g in utakmice(k):
            if not g['played']: continue
            c = g['gameCode']; h, a = g['local']['club']['code'], g['road']['club']['code']
            s = preuzmi(f'{A}/v3/competitions/E/seasons/{SEZONA}/games/{c}/stats', f's{c}.json')
            for x in preuzmi(f'https://live.euroleague.net/api/Points?gamecode={c}&seasoncode={SEZONA}', f'p{c}.json')['Rows']:
                t, ty, z, n = x['TEAM'].strip(), x['ID_ACTION'].strip(), (x['ZONE'] or '').strip(), x['PLAYER'].strip()
                if ty[:1] == '3': vr = 't'
                elif ty[:1] == '2': vr = 'r' if z in RACKET else 'm'
                else: continue
                for cil in (sp[(n, t)], D[a if t == h else h]):
                    cil['a' + vr] += 1
                    if ty.endswith('M'): cil['m' + vr] += 1
            for st, t, o in (('local', h, a), ('road', a, h)):
                tt = s[st]['total']; oo = s['road' if st == 'local' else 'local']['total']
                posedi = lambda b: b['fieldGoalsAttemptedTotal'] + 0.44 * b['freeThrowsAttempted'] + b['turnovers'] - b['offensiveRebounds']
                tim[t]['g'] += 1; tim[t]['pos'] += posedi(tt)
                D[t]['posedi'] += posedi(oo); D[t]['ftm'] += oo['freeThrowsMade']; D[t]['fta'] += oo['freeThrowsAttempted']; D[t]['fga'] += oo['fieldGoalsAttemptedTotal']
                for x in s[st]['players']:
                    p, b, n = x['player'], x['stats'], x['player']['person']['name']
                    poz[(n, t)] = POZ.get(p.get('positionName'), 'F')
                    if not b['timePlayed']: continue
                    m = b['timePlayed'] / 60
                    box.setdefault((n, t), []).append((k, m, b))
                    sp[(n, t)]['min'] += m; sp[(n, t)]['ftm'] += b['freeThrowsMade']; sp[(n, t)]['fta'] += b['freeThrowsAttempted']
                    e = pa[(o, poz[(n, t)])]; e[0] += m; e[1] += b['points']; e[2] += b['totalRebounds']; e[3] += b['assistances']; e[4].add(k)
                    f = faul.setdefault(f'{n}|{t}', [0, 0.0, 0, 0]); f[0] += 1; f[1] += m; f[2] += b['foulsCommited']; f[3] += b['foulsCommited'] >= 4
    br = lambda v: str(int(v))
    P, SP = [], []
    for (n, t), v in box.items():
        if len(v) < MIN_UTAKMICA or sum(x[1] for x in v) < MIN_MINUTA: continue
        v.sort(key=lambda x: x[0])
        P.append([n, poz[(n, t)], t, ','.join(str(x[0]) for x in v), ','.join(f'{x[1]:.1f}'.rstrip('0').rstrip('.') for x in v),
                  ''.join('1' if x[2]['startFive'] else '0' for x in v), *[','.join(br(x[2][q]) for x in v) for q in ('points', 'totalRebounds', 'assistances')]])
        s = sp[(n, t)]
        SP.append([n, t, round(s['min'], 1), s['ar'], s['mr'], s['am'], s['mm'], s['at'], s['mt'], int(s['ftm']), int(s['fta'])])
    return dict(P=P, SP=SP,
                D=[[t, round(d['posedi'], 1), d['ar'], d['mr'], d['am'], d['mm'], d['at'], d['mt'], int(d['ftm']), int(d['fta']), int(d['fga'])] for t, d in D.items()],
                posAllow=[[t, q, len(e[4]), round(e[1] / e[0] * 40, 2), round(e[2] / e[0] * 40, 2), round(e[3] / e[0] * 40, 2)] for (t, q), e in pa.items()],
                pace={t: round(c['pos'] / c['g'], 1) for t, c in tim.items()}), {k: [v[0], round(v[1]), int(v[2]), v[3]] for k, v in faul.items()}

def provera():
    novo, fa = statistika(8); st = [citaj(f) for f in ('data9.json', 'data9b.json', 'data9c.json')]
    oP, oS = {(p[0], p[2]): p for d in st for p in d['P']}, {(s[0], s[1]): s for d in st for s in d['SP']}
    nP, nS = {(p[0], p[2]): p for p in novo['P']}, {(s[0], s[1]): s for s in novo['SP']}
    print('igrača staro', len(oP), 'novo', len(nP), 'fale u novom', [k for k in oP if k not in nP])
    print('P različito', [k for k in oP if k in nP and [oP[k][i] for i in (1, 3, 5, 6, 7, 8)] != [nP[k][i] for i in (1, 3, 5, 6, 7, 8)]][:5])
    pog = lambda a, b, ii: sum(abs(a[i] - b[i]) for i in ii)
    print('SP trojke i bacanja, ukupna razlika', sum(pog(oS[k], nS[k], (7, 8, 9, 10)) for k in oS if k in nS), '| reket i srednja', sum(pog(oS[k], nS[k], (3, 4, 5, 6)) for k in oS if k in nS), 'od', sum(sum(oS[k][3:7]) for k in oS))
    oD = {r[0]: r for r in st[0]['D']}
    print('D posedi', round(max(abs(r[1] - oD[r[0]][1]) for r in novo['D']), 2), 'trojke/bacanja/FGA', max(pog(oD[r[0]], r, (6, 7, 8, 9, 10)) for r in novo['D']), 'reket+srednja zbirno', max(abs(sum(oD[r[0]][2:6]) - sum(r[2:6])) for r in novo['D']))
    oA = {(r[0], r[1]): r for r in st[0]['posAllow']}
    print('posAllow najveća razlika', round(max(pog(oA[(r[0], r[1])], r, (2, 3, 4, 5)) for r in novo['posAllow']), 2))
    print('pace najveća razlika', round(max(abs(v - st[0]['pace'][t]) for t, v in novo['pace'].items()), 2))
    oF = citaj('faulovi.json')
    print('faulovi razlika', sum(1 for k, v in oF.items() if fa.get(k) != v), 'od', len(oF), [(k, v, fa.get(k)) for k, v in oF.items() if fa.get(k) != v][:3])

def pripremi(k):
    gs = sorted(utakmice(k), key=lambda g: g['utcDate'])
    if not gs: raise SystemExit(f'nema rasporeda za {k}. kolo')
    pre = utakmice(k - 1)
    novo, fa = statistika(k - 1)
    pisi(novo, 'statistika.json', ensure_ascii=False)
    pisi(fa, 'faulovi.json', ensure_ascii=False)
    games = []
    for g in gs:
        b = beograd(g['utcDate'])
        games.append([g['local']['club']['code'], g['road']['club']['code'], f"{DANI[b.weekday()]} {b:%d.%m. %H:%M}", g['utcDate']])
    od = max(g['utcDate'] for g in pre)    # snimci kvota stariji od ovoga pripadaju prošlom kolu
    pisi(dict(kolo=k, od=od, games=games), 'kolo.json', ensure_ascii=False, indent=0)
    # odmor: dana između prethodne utakmice tima i ove
    posl = {}
    for g in pre:
        for s in ('local', 'road'): posl[g[s]['club']['code']] = beograd(g['utcDate']).date()
    M = citaj('minute_timovi.json')
    M['odmor_dana'] = {t: (beograd(u).date() - posl[t]).days - 1 for h, a, _, u in games for t in (h, a) if t in posl}
    pisi(M, 'minute_timovi.json', ensure_ascii=False)
    print(f"{k}. kolo: {len(games)} utakmica, prva {games[0][2]}, poslednja {games[-1][2]}; statistika {len(novo['P'])} igrača, kola do {k - 1}")

if __name__ == '__main__':
    if sys.argv[1:] == ['--provera']: provera()
    else: pripremi(int(sys.argv[1]))
