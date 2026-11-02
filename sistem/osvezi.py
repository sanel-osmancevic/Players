# Osvežavanje Maxbet liste u jednom koraku.
# Upotreba: py -X utf8 osvezi.py [mb_snapshot.json]
#   bez argumenta: najnoviji Maxbet snimak servisa sa igračima (prikupljeno/), a ako ga nema, direktno povlačenje
#   sa argumentom: koristi {raw, games} koji je vratio pregledač
import json, sys, subprocess, re, os, datetime
os.chdir(os.path.dirname(os.path.abspath(__file__)))
if not sys.flags.utf8_mode:   # na Windowsu open() inače ne čita fajlove kao UTF-8
    sys.exit(subprocess.run([sys.executable, '-X', 'utf8', *sys.argv], env=dict(os.environ, PYTHONUTF8='1')).returncode)
from kolo import KOLO, DAN, tim
os.environ['DAN'] = DAN; os.environ['PYTHONUTF8'] = '1'   # i za skripte koje se pozivaju odavde
Q = '?annex=3&mobileVersion=1.21.18&locale=sr'
BASE = 'https://www.maxbet.rs/restapi/offer/sr'

def get(path):
    out = subprocess.run(['curl', '-s', '--max-time', '20', BASE + path + Q], capture_output=True, text=True)
    if out.returncode or not out.stdout.startswith('{'): raise RuntimeError('Maxbet nije dostupan iz clouda')
    return json.loads(out.stdout)

def fetch_direct():
    from concurrent.futures import ThreadPoolExecutor
    lst = get('/sport/SK/league/194042/mob').get('esMatches', [])
    with ThreadPoolExecutor(12) as ex: det = list(ex.map(lambda m: get(f"/match/{m['id']}"), lst))
    raw = {}
    for d in det:
        o, p = d.get('odds') or {}, d.get('params') or {}
        a = raw.setdefault(d['home'] + '|' + d['away'], [])
        def add(c, L, ov, un=None, two=True):
            if L is None or (ov is None and un is None): return
            a.append([c, float(L), ov, un] if two else [c, float(L), ov])
        add('P', p.get('ouPlPoints'), o.get('51679'), o.get('51681'))
        add('P', p.get('ouPlP2'), o.get('55253'), o.get('55255'))
        add('P', p.get('ouPlP3'), o.get('55256'), o.get('55258'))
        for c, x in [(54096, 5), (54101, 10), (54106, 15), (54111, 20), (54116, 25), (54121, 30), (54126, 35)]:
            if o.get(str(c)): add('P', x - 0.5, o[str(c)], two=False)
        add('S', p.get('ouPlRebounds'), o.get('51685'), o.get('51687'))
        add('A', p.get('ouPlAssists'), o.get('51682'), o.get('51684'))
    gl = get('/sport/B/league/131600/mob').get('esMatches', [])
    with ThreadPoolExecutor(8) as ex: gm = list(ex.map(lambda m: get(f"/match/{m['id']}"), gl))
    games = [[d['home'], d['away'], d.get('kickOffTime'), (d.get('params') or {}).get('hdp'), (d.get('params') or {}).get('overUnder'),
              (d.get('odds') or {}).get('1'), (d.get('odds') or {}).get('3')] for d in gm]
    return dict(raw=raw, games=games)

def najnoviji_snimak():
    import glob
    sn = [s for s in (json.load(open(f)) for f in glob.glob('prikupljeno/*/mb_*.json')) if s.get('raw')]
    if not sn: return None
    s = max(sn, key=lambda x: x['t'])
    print('Maxbet snimak servisa:', s['t'])
    return s
_arg = [a for a in sys.argv[1:] if not a.startswith('--')]
snap = json.load(open(_arg[0])) if _arg else (najnoviji_snimak() or fetch_direct())
raw = snap['raw']
for k, ls in raw.items():  # uskladi oblik: milestone linije imaju 3 polja
    raw[k] = [l[:3] if len(l) == 4 and l[3] is None else l for l in ls]

# pomeranja linija u odnosu na prethodno stanje
prev = json.load(open('mb_pet_raw2.json')) if os.path.exists('mb_pet_raw2.json') else {}
moves = []
for k in raw:
    A = {(l[0], l[1], len(l)): l for l in prev.get(k, [])}; B = {(l[0], l[1], len(l)): l for l in raw[k]}
    for kk in set(A) | set(B):
        if A.get(kk) != B.get(kk) and len(kk) and kk[2] == 4: moves.append((k.split('|')[0], A.get(kk), B.get(kk)))
novi = [k for k in raw if k not in prev]; nestali = [k for k in prev if k not in raw]
json.dump(raw, open('mb_pet_raw2.json', 'w'), ensure_ascii=False)

# snimak glavnih Maxbet linija za praćenje kretanja (books/mb_HHMM.json); Soccer i Merkur snimke
# upisuju snippets/soccer.js i snippets/merkur.js u books/sb_HHMM.json i books/mk_HHMM.json
t_snap = snap.get('t') or datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
glavne = {}
for k, ls in raw.items():
    d = {}
    for l in ls:
        if len(l) == 4 and l[2] and l[3] and l[0] not in d: d[l[0]] = [l[1], l[2], l[3]]
    glavne[k] = d
os.makedirs('books', exist_ok=True)
lok = datetime.datetime.fromisoformat(t_snap.replace('Z', '+00:00')).astimezone(datetime.timezone(datetime.timedelta(hours=1)))
json.dump({'t': t_snap, 'out': glavne}, open(f"books/mb_{lok.strftime('%m%d_%H%M')}.json", 'w'), ensure_ascii=False)

# kvote utakmica -> adjust
G = {}
for h, a, t, hdp, ou, oh, oa in snap['games']:
    if ou and oh and oa: G[f"{tim(h) or h} – {tim(a) or a}"] = (float(ou), float(oh), float(oa))
adj = open('adjust2.py').read()
adj = re.sub(r"G=\{.*?\}\nLG", "G=" + repr(G) + "\nLG", adj, flags=re.S)
open('adjust3.py', 'w').write(adj)

run = lambda *c: subprocess.run([sys.executable if c[0] == 'python3' else c[0], *c[1:]], check=True, capture_output=True, text=True).stdout
print(run('python3', 'nestanak.py').strip()); run('python3', 'build5.py'); print(run('python3', 'dostupnost.py').strip()); run('python3', 'adjust3.py'); print(run('python3', 'minute.py').strip()); print(run('python3', 'uloge2.py' if os.path.exists('uloge_faktori.json') else 'uloge.py').strip()); run('python3', 'uci2.py'); print(run('python3', 'tezine_primeni.py', 'igraci').strip()); print(run('python3', 'faul.py').strip())
# ručna isključenja (rizik) iz iskljuci.json
ex = json.load(open('iskljuci.json')) if os.path.exists('iskljuci.json') else {}
rows = json.load(open('igraci2.json'))
for r in rows:
    if r['igrac'] in ex and r['termin'].startswith(DAN): r['iskljuci'] = ex[r['igrac']]
    elif r.get('rizik_uloge'): r['iskljuci'] = 'Rizik uloge: ' + r['rizik_uloge']   # upitan saigrač ili izgubljen start
json.dump(rows, open('igraci2.json', 'w'), ensure_ascii=False)
print(run('python3', 'kv_pet2.py').strip())
print(run('python3', 'market.py').strip().splitlines()[0]); print(run('python3', 'kalibracija.py').strip()); print(run('python3', 'tezine_primeni.py', 'kvote').strip()); print(run('python3', 'prosla_kvote.py').strip())
run('python3', 'evidencija.py', 'kvote_pet.json', DAN)
run('node', 't28.js')

# zaključaj nove preporuke samo za utakmice koje još nisu počele
picks = [dict(p, vrsta='sigurnije') for p in json.load(open('picks_pet3.json'))] + json.load(open('glavne_pet.json'))
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))
if os.environ.get('SADA'): now = datetime.datetime.fromisoformat(os.environ['SADA'])  # samo za probe
start = {}
for h, a, t, *_ in snap['games']:
    if t: start[f"{tim(h) or h} – {tim(a) or a}"] = datetime.datetime.fromtimestamp(t / 1000, now.tzinfo)
z = json.load(open('zapamceno.json'))
KS = ['konacno','vrsta','kljuc','kolo','termin','red','igrac','utakmica','kategorija','smer','linija','opklada','kvota','sansa','razmak','stabilan','istorija','forma5','vrednost','minuti','rang','grupa','zapamceno','rezultat','ishod','kvota_prva','zapamceno_prvo','kvota_zavrsna','clv','brzo','zaostatak','klupa','ulog','sansa_kor','prednost','povezano','trz_prva','trz_zavrsna','clv_trz','sansa_sirova','model','trziste','kretanje']
def pocela(u): return start.get(u) is not None and start[u] <= now
# trenutna Maxbet kvota za svaku opkladu (za završnu kvotu / CLV)
KV = {}
for x in json.load(open('kvote_pet.json')):
    for smer, q in (('više', x.get('kvota_vise')), ('manje', x.get('kvota_manje'))):
        if q: KV[(x['igrac'], x['kategorija'], float(x['linija']), smer)] = q
stari = [r for r in z if r['kolo'] == KOLO and r['termin'].startswith(DAN)]
prvi = {(r['kljuc'], r['opklada']): (r.get('kvota_prva') or r['kvota'], r.get('zapamceno_prvo') or r['zapamceno']) for r in stari}
ts = now.strftime('%d.%m. %H:%M')
PRED_MEC = 60      # minuta pre početka: opklade za tu utakmicu se konačno zaključavaju (poslednji talas)
ZAKLJUCAJ_SVE = '--zakljucaj' in sys.argv
# Maxbet zaostaje za Soccerom i Merkurom -> "igraj odmah" (⚡): medijana Soccer/Merkur je za 0.5+ poena
# (skokovi/asistencije 0.25+) na strani opklade u odnosu na Maxbet (provera petak: 8/11 u 13h, 7/7 u 15h)
ODST = {(x['igrac'], x['kategorija'], float(x['linija'])): x.get('mb_odstupanje') for x in json.load(open('kvote_pet.json'))}
def brzo(p):
    o = ODST.get((p['igrac'], p['kategorija'], float(p['linija'])))
    if o is None: return None, None
    lag = (-o if p['smer'] == 'više' else o)
    jed = 1 if p['kategorija'] == 'Poeni' else 0.5
    return (lag / jed >= 0.5), f"Soccer/Merkur {lag:+.1f} u odnosu na Maxbet"
KAL = json.load(open('kalibracija.json')) if os.path.exists('kalibracija.json') else {'a': 1, 'b': 0}
def kal(p):   # usklađena šansa (kalibracija.py); prikaz, tiketi i ulozi koriste nju, izbor opklada ostaje isti
    import math
    p = min(max(float(p), 0.02), 0.98); return round(1 / (1 + math.exp(-(KAL['a'] * math.log(p / (1 - p)) + KAL['b']))), 3)
def red(p):
    d = {k: p.get(k) for k in KS}; d.update(zapamceno=ts, rezultat=None, ishod=None)
    d['sansa_sirova'] = p.get('sansa'); d['sansa'] = kal(p['sansa'])
    d['kvota_prva'], d['zapamceno_prvo'] = prvi.get((p['kljuc'], p['opklada']), (p['kvota'], ts))
    d['brzo'], d['zaostatak'] = brzo(p)
    return d
# 1) zadržavamo: utakmice koje su počele, i one koje su već konačno zaključane (60 min pred meč ili ručno)
# Odigrane opklade (dugme Odigrano) ostaju sa svojom granicom i kvotom, a da to ne zaključava ostatak utakmice
zadrzani = [r for r in stari if pocela(r['utakmica']) or r.get('konacno') or r.get('odigrano')]
zakl = {r['utakmica'] for r in stari if pocela(r['utakmica']) or r.get('konacno')}
igrani = {r['kljuc'] for r in zadrzani if r.get('odigrano')}
# 2) ostatak liste popunjavamo svežim preporukama za utakmice koje još nisu zaključane, do 10 po vrsti
novi_red = list(zadrzani)
for vr in ('sigurnije', 'glavne'):
    ima = sum(1 for r in zadrzani if r.get('vrsta') == vr)
    for p in [p for p in picks if p['vrsta'] == vr and p['utakmica'] not in zakl and not pocela(p['utakmica']) and p['kljuc'] not in igrani]:
        if ima >= 10: break
        novi_red.append(red(p)); ima += 1
# 3) konačno zaključavanje: utakmice koje počinju za 60 min ili manje (ili sve, uz --zakljucaj)
for d in novi_red:
    u = d['utakmica']
    if not d.get('konacno') and (ZAKLJUCAJ_SVE or (start.get(u) and (start[u] - now).total_seconds() <= PRED_MEC * 60)):
        d['konacno'] = ts
n_z = len({r['utakmica'] for r in novi_red if r.get('konacno')})
print(f"Zapamćena lista ažurirana {ts}: konačno zaključanih utakmica {n_z}, ⚡ igraj odmah: {[r['igrac'] for r in novi_red if r.get('brzo') and not r.get('ishod')]}")
# završna kvota: poslednja Maxbet kvota pre početka utakmice; CLV = prva / završna − 1 (plus = kvota je pala posle naše preporuke)
# CLV prema tržištu: verovatnoća konsenzusa (Soccer, Merkur, Mozzart, Meridian, Stoiximan, bez marže) za našu stranu pred početak;
# clv_trz = prva Maxbet kvota × ta verovatnoća − 1 = koliko je naša kvota vredela prema "pravoj" završnoj ceni tržišta
TRZ = {(x['igrac'], x['kategorija'], float(x['linija'])): x.get('trz_vise') for x in json.load(open('kvote_pet.json'))}
for d in novi_red:
    if pocela(d['utakmica']): continue
    q = KV.get((d['igrac'], d['kategorija'], float(d['linija']), d['smer']))
    if q:
        d['kvota_zavrsna'] = q; d['clv'] = round(float(d.get('kvota_prva') or d['kvota']) / q - 1, 4)
    tv = TRZ.get((d['igrac'], d['kategorija'], float(d['linija'])))
    if tv is not None:
        pt = tv if d['smer'] == 'više' else 1 - tv
        if d.get('trz_prva') is None: d['trz_prva'] = round(pt, 3)
        d['trz_zavrsna'] = round(pt, 3); d['clv_trz'] = round(float(d.get('kvota_prva') or d['kvota']) * pt - 1, 4)

# ULOG (jedinica = 1% kase): četvrtina Kelly kriterijuma na šansu korigovanu prema stvarnom učinku.
#   k = koliko se naše šanse obistinjuju: (prolaznost − 0.5) / (prosečna šansa − 0.5) iz svih završenih opklada, skupljeno ka 0.85
#   p = 0.5 + k·(šansa − 0.5);  prednost = p·kvota − 1;  ulog = 100 · ¼ · prednost / (kvota − 1), zaokruženo na 0.25
#   bez prednosti posle korekcije -> ulog 0 (opklada ostaje na listi samo za praćenje). Najviše 2 j. (glavne 0.5 j.), ukupno dnevno najviše 10 j.
# Povezanost: dve opklade na isti tim u istom smeru (obe više / obe manje) -> manja dobija ×0.7; po utakmici ukupno najviše 3 j.
gotove = [r for r in z if r.get('ishod') in ('prošlo', 'palo') and r.get('sansa')]
if gotove:
    hr = sum(r['ishod'] == 'prošlo' for r in gotove) / len(gotove); mp = sum(kal(r.get('sansa_sirova') or r['sansa']) for r in gotove) / len(gotove)
    k_raw = (hr - 0.5) / (mp - 0.5) if mp > 0.5 else 0.85
    K_KAL = max(0.5, min(1.0, (len(gotove) * k_raw + 30 * 1.0) / (len(gotove) + 30)))   # šanse su već usklađene: polazno bez dodatne korekcije
else: K_KAL = 1.0
IG_TIM = {r['igrac']: r['tim'] for r in json.load(open('igraci2.json'))}
def ulog(d):
    kv, p = float(d['kvota']), 0.5 + K_KAL * (float(d['sansa']) - 0.5)
    pr = p * kv - 1
    if pr <= 0: return 0.0, round(p, 3), round(pr, 3)
    u = 100 * 0.25 * pr / (kv - 1)
    return min(2.0 if d.get('vrsta') != 'glavne' else 0.5, round(u * 4) / 4 or 0.25), round(p, 3), round(pr, 3)
otvorene = [d for d in novi_red if not d.get('konacno') and not d.get('odigrano') and not pocela(d['utakmica'])]
for d in otvorene: d['ulog'], d['sansa_kor'], d['prednost'] = ulog(d)
for d in sorted(otvorene, key=lambda d: -d['ulog']):
    if not d['ulog']: continue
    isti = [x for x in novi_red if x is not d and x.get('ulog') and IG_TIM.get(x['igrac']) == IG_TIM.get(d['igrac'])
            and x['smer'] == d['smer'] and x['utakmica'] == d['utakmica'] and x['ulog'] >= d['ulog'] and x['igrac'] != d['igrac']]
    if isti: d['ulog'] = round(d['ulog'] * 0.7 * 4) / 4 or 0.25; d['povezano'] = isti[0]['igrac']
for u in {d['utakmica'] for d in novi_red}:
    L = [d for d in novi_red if d['utakmica'] == u and d.get('ulog')]
    tot = sum(d['ulog'] for d in L)
    if tot > 3:
        for d in L:
            if d in otvorene: d['ulog'] = max(0.25, round(d['ulog'] * 3 / tot * 4) / 4)
dn = sum(d.get('ulog') or 0 for d in novi_red)
if dn > 10:
    for d in otvorene:
        if d.get('ulog'): d['ulog'] = max(0.25, round(d['ulog'] * 10 / dn * 4) / 4)
print(f"Ulozi: kalibracija k={K_KAL:.2f}; ukupno {sum(d.get('ulog') or 0 for d in otvorene):.2f} j. na {sum(1 for d in otvorene if d.get('ulog'))} opklada")
keep = [r for r in z if not (r['kolo'] == KOLO and r['termin'].startswith(DAN))] + novi_red
json.dump(keep, open('zapamceno.json', 'w'), ensure_ascii=False)

print('Novi igrači:', [k.split('|')[0] for k in novi], 'Nestali:', [k.split('|')[0] for k in nestali])
print('Pomeranja osnovnih linija (staro -> novo):')
for n, a, b in moves[:40]: print(' ', n, a, '->', b)
for p in picks: print(p['grupa'], '|', p['igrac'], '|', p['utakmica'], '|', p['opklada'], p['kvota'], p['sansa'], p['istorija'])

# pozadinska arhiva svih igrača u ponudi (sve kladionice, sve granice, stanje modela) — arhiva/kolo{K}_ponuda.jsonl
import arhiva
print('Arhiva:', arhiva.zabelezi(t_snap))

# podaci za web aplikaciju (GitHub Pages)
print(subprocess.run([sys.executable, 'objavi_web.py'], capture_output=True, text=True).stdout.strip())
