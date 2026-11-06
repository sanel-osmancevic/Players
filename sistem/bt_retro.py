# Šta bi sadašnji model i pravila preporučili ranijih dana i kako bi prošli, naspram liste koja je tada stvarno napravljena.
# Linije iz evidencija.json (poslednje stanje pred utakmicu), projekcija kakva je tada bila, a šansa po sadašnjoj formuli:
# oko medijane (pomocno.MEDIJANA), sadašnja širina, 40% model i 60% tržište, bez istorije. Pravila: model 55%+, vrednost 3%+,
# razlika model − tržište do 15, kvota bar 1.40, raskorak kladionica ispod praga, forma bar 3 od poslednjih 5, jedna opklada po igraču,
# do 10 po danu i 3 po utakmici. Kretanje tržišta i pravila za klupu se ne vide u evidenciji, pa nisu uključena.
# Upozorenje: pomak medijane je izmeren na kolima 3-9, pa je 9. kolo delom u uzorku iz kog je izveden. Ništa ne upisuje.
import math, re, unicodedata
from pomocno import citaj, MEDIJANA
Phi = lambda z: .5 * (1 + math.erf(z / math.sqrt(2)))
C = citaj('tezine.json')['c']; K = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}
def kl(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower().replace("'", ''); n = re.sub(r'\b(iv|iii|jr)\b', '', n); n = re.sub(r'\b[a-z]\b', '', n); return re.sub(r'[^a-z]', '', n)
ST = {}
for n, pos, t, rr, mm, ss, vp, vr, va in citaj('statistika.json')['P']:
    l, f = (n.split(', ', 1) + [''])[:2]
    ST[kl(f + ' ' + l)] = {'kola': [int(x) for x in rr.split(',')], 'pts': [int(x) for x in vp.split(',')], 'reb': [int(x) for x in vr.split(',')], 'ast': [int(x) for x in va.split(',')]}
def forma(e, smer):
    s = ST.get(kl(e['igrac']))
    if not s: return None
    v = [x for r, x in zip(s['kola'], s[K[e['kategorija']]]) if r < e['kolo']][-5:]
    return sum((x > e['linija']) if smer == 'više' else (x < e['linija']) for x in v) if v else None
E = [e for e in citaj('evidencija.json') if e.get('kvota_manje') and e.get('trz_vise') is not None and e.get('proslo_vise') is not None]
kand = {}
for e in E:
    if e.get('status') == 'Ne igra': continue
    pm = 1 - Phi((math.floor(e['linija']) + .5 - (e['proj'] + MEDIJANA[K[e['kategorija']]])) / (e['sd'] * C))
    for smer, m, t, kv in (('više', pm, e['trz_vise'], e['kvota_vise']), ('manje', 1 - pm, 1 - e['trz_vise'], e['kvota_manje'])):
        s = .4 * m + .6 * t; ev = s * kv - 1
        if kv < 1.4 or m < .55 or ev < .03 or m - t > .15: continue
        if e.get('trz_raskorak') is not None and e['trz_raskorak'] >= (1.5 if e['kategorija'] == 'Poeni' else .75): continue
        f = forma(e, smer)
        if f is not None and f < 3: continue
        if e['proslo_vise'] == 'nije igrao': ok = None
        else: ok = e['proslo_vise'] if smer == 'više' else (not e['proslo_vise'] and e['rezultat'] != e['linija'])
        x = dict(kolo=e['kolo'], dan=e['dan'], utakmica=e['utakmica'], igrac=e['igrac'], opklada=f"{e['kategorija'].lower()} {smer} {e['linija']:g}", kvota=kv, sansa=s, model=m, trziste=t, ok=ok, rezultat=e['rezultat'])
        k = (e['kolo'], e['dan'], e['igrac'])
        if k not in kand or s > kand[k]['sansa']: kand[k] = x
novi = {}
for x in sorted(kand.values(), key=lambda x: -x['sansa']):
    d = novi.setdefault((x['kolo'], x['dan']), [])
    if len(d) < 10 and sum(y['utakmica'] == x['utakmica'] for y in d) < 3: d.append(x)
# stvarne liste: zapamćene opklade (iste sa obe stare liste jednom)
Z = {}
for r in citaj('zapamceno.json'):
    if r.get('igrac') and r.get('ishod'): Z.setdefault((r['kolo'], r['termin'].split()[0]), {})[(r['igrac'], r['opklada'])] = r
def zbir(L, kv, ok):
    g = [x for x in L if ok(x) is not None]; return len(g), sum(1 for x in g if ok(x)), sum(kv(x) - 1 if ok(x) else -1 for x in g)
uk = [0, 0, 0.0, 0, 0, 0.0]
TRZ = {(e['kolo'], e['dan']) for e in E}   # dani za koje postoji tržište (9. kolo četvrtak ga nema, pa se ne poredi)
for kd in sorted(set(novi) | {k for k in Z if k in TRZ}):
    N = novi.get(kd, []); S = list(Z.get(kd, {}).values())
    a = zbir(N, lambda x: x['kvota'], lambda x: x['ok']); b = zbir(S, lambda r: float(r['kvota']), lambda r: None if r['ishod'] == 'nije igrao' else r['ishod'] == 'prošlo')
    uk = [uk[0] + a[0], uk[1] + a[1], uk[2] + a[2], uk[3] + b[0], uk[4] + b[1], uk[5] + b[2]]
    print(f'\n== {kd[0]}. kolo, {kd[1]}: sadašnji model {a[1]} od {a[0]} ({a[2]:+.2f} j.) | tada napravljena lista {b[1]} od {b[0]} ({b[2]:+.2f} j.)')
    stari = {(r['igrac'], r['opklada']) for r in S}
    for x in N:
        print(f"   {'isto ' if (x['igrac'], x['opklada']) in stari else 'NOVO '} {x['igrac']:<22} {x['opklada']:<24} {x['kvota']:.2f} šansa {x['sansa']:.0%} model {x['model']:.0%} trž {x['trziste']:.0%} | {x['rezultat']} {'PROŠLO' if x['ok'] else 'palo' if x['ok'] is False else 'nije igrao'}")
    nn = {(x['igrac'], x['opklada']) for x in N}
    for r in S:
        if (r['igrac'], r['opklada']) not in nn: print(f"   ISPALO {r['igrac']:<22} {r['opklada']:<24} {float(r['kvota']):.2f} | {r.get('rezultat')} {r['ishod']}")
print(f'\nUKUPNO (ulog 1 po opkladi): sadašnji model {uk[1]} od {uk[0]} ({uk[2]:+.2f} j., {uk[2] / max(1, uk[0]):+.1%}) | tada napravljene liste {uk[4]} od {uk[3]} ({uk[5]:+.2f} j., {uk[5] / max(1, uk[3]):+.1%})')
