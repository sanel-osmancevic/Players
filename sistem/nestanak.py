# Nestanak iz ponude: igrač koji je danas bio u ponudi kladionice, a u poslednjem snimku je nema (dok su njegovi saigrači
# iz iste utakmice i dalje tu), verovatno ne igra ili je upitan — kladionice to saznaju prve.
# Mora da fali u poslednja dva snimka te kladionice: kladionice povremeno nakratko sklone igrača dok menjaju kvotu.
# Ako je nestao kod bar MIN_KNJIGA kladionica: upisuje se u statusi_auto.json kao "Upitan" (build5 ga onda tretira kao upitnog:
# minuti saigrača se računaju za oba scenarija, a igrači čija uloga zavisi od njega dobijaju "rizik uloge").
# Kod svih kladionica u kojima je bio -> "Ne igra". Ručni statusi (statusi.json, zvaničan izveštaj) imaju prednost.
import json, os, datetime
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import market as M

MIN_KNJIGA = 2
data9 = [p for f in ('statistika.json',) for p in json.load(open(f))['P']]
API = {}
for n, pos, t, *_ in data9:
    l, f = (n.split(', ', 1) + [''])[:2]
    API.setdefault(M.surname_full(f + ' ' + l), []).append((n, t))
CODE_TIM = {r['tim']: None for r in M.ig.values()}

def dan(t): return t[:10]
nestao = {}   # (prezime, tim) -> [kladionice]
bio = {}
for b, h in M.HIST.items():
    if len(h) < 3: continue
    pretposl = h[-2][1]; zadnji_t, zadnji = h[-1]
    danas = [ix for t, ix in h[:-2] if dan(t) == dan(zadnji_t)]
    if not danas: continue
    ranije = set().union(*[set(ix) for ix in danas])
    timovi_sada = {k[1] for k in zadnji} & {k[1] for k in pretposl}
    for k in ranije:
        bio.setdefault(k, set()).add(b)
        if k not in zadnji and k not in pretposl and k[1] in timovi_sada:
            nestao.setdefault(k, []).append(b)
out = {}
for k, knj in nestao.items():
    if len(knj) < MIN_KNJIGA: continue
    sve = len(knj) >= len(bio.get(k, ())) >= 2
    kand = [r for i, r in M.ig.items() if M.surname_full(i) == k[0] and r['tim'] == k[1]]
    if not kand: continue
    api = kand[0].get('api')
    tc = next((t for n, t in API.get(k[0], []) if n == api), None)
    if not api or not tc: continue
    out[f'{api}|{tc}'] = ['Ne igra' if sve else 'Upitan', f"Nestao iz ponude: {', '.join(sorted(knj))} ({datetime.datetime.now():%d.%m. %H:%M})"]
json.dump(out, open('statusi_auto.json', 'w'), ensure_ascii=False, indent=0)
print('nestanak iz ponude:', {k.split('|')[0]: v[0] for k, v in out.items()} or 'nema')
