# Probna lista u senci (od 6.11.2026): pravilo iz bt_formula.py, prati se pored prave liste, bez uloga i bez uticaja na preporuke.
# Pravilo: glavna Maxbet linija (obe kvote), model 3-15 procentnih poena iznad tržišta (ostale kladionice bez marže), bez filtera istorije.
#   Model je sadašnji: šansa oko medijane (pomocno.MEDIJANA). Na kolima 9-10 ta grupa je prolazila 5.7 poena češće od tržišta
#   [+0.3, +11.4], a razlika preko 15 je bez prednosti (bt_pravila.py). Do 6.11.2026. 11:30 pravilo je bilo 3-10 na modelu oko proseka
#   (stara lista: prikupljeno/2026-11-06/proba_lista_stari_model.json). Granice su izabrane gledajući ta dva kola, pa lista služi
#   da se pravilo potvrdi ili odbaci na kolima koja tek dolaze.
# Igrač: jedna opklada (najveća razlika u opsegu); bez igrača koji ne igraju, upitnih i onih sa manje od 3 utakmice.
# Upis: proba_lista.json. Red se pamti kad prvi put uđe u opseg; do početka utakmice osvežava kvotu i razliku, a ako izađe iz opsega
# dobija ispala=True (ostaje zbog analize). Posle početka se ne menja, a rezultat se upisuje iz zapisnika (prikupljeno/rezultati/).
# Pravilo B (od 7.11.2026, korisnik): samo strana „manje“, Maxbet kvota bar 1.95 (sve linije sa obe kvote, i sporedne), model 3-15
#   poena iznad tržišta. Na kolima 9-10 (bt analiza 7.11.): 142 linije, prošlo 58.5% naspram tržišta 42.7%, profit +29% (oba kola
#   +28/+30). Pravilo je izvedeno iz tih kola, pa unazad (10. kolo) nije dokaz; prati se od 11. kola. Redovi imaju pravilo='B',
#   redovi bez polja su pravilo A. Od 7.11. B uključuje i „manje“ na povišenim linijama (kvota ispod 1.60): na kolima 9-10
#   „manje“ po kvoti ispod 1.60 prošlo 74% naspram 67% (+10%, oba kola), sporedne „manje“ uz model 3-15 iznad +27.5% (bt_sistem.py).
# Za praćenje (bez uticaja na pravila) redovi pamte poziciju (poz) i odstupanje minuta (minuti_sd): „manje“ kod centara (−12%)
#   i kod nestalnih minuta (sd 6+, −9%) bili su slabiji na kolima 9-10, uzorak mali.
# Pravilo C (od 7.11.2026, kontrola bez modela): „manje“ na svakoj sporednoj Maxbet liniji sa obe kvote (van 1.65-2.20), bez obzira
#   na model; po igraču sporedna linija najbliža glavnoj. Na kolima 9-10: 273 linije, +9.9%. Pokazuje da li prednost B dolazi od
#   modela ili samo od Maxbet cena sporednih linija. Redovi imaju pravilo='C'. Unazad: py -X utf8 proba.py --unazad-C=10
# Upotreba: py -X utf8 proba.py   (poziva ga osvezi.py posle preporuka)
#           py -X utf8 proba.py --unazad-B=10   (jednom: rekonstrukcija pravila B za kolo iz evidencija.json)
import math, os, re, glob, datetime, unicodedata
from pomocno import citaj, pisi, beograd
os.chdir(os.path.dirname(os.path.abspath(__file__)))
OD, DO = 0.03, 0.15
FAJL = 'proba_lista.json'
Phi = lambda z: .5 * (1 + math.erf(z / math.sqrt(2)))
K = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}
def kljuc(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower().replace("'", '')
    n = re.sub(r'\b(iv|iii|jr)\b', '', n); n = re.sub(r'\b[a-z]\b', '', n); return re.sub(r'[^a-z]', '', n)

KV_B, KV_B_NISKA = 1.95, 1.60   # B: kvota za „manje“ bar 1.95 (snižene linije) ili ispod 1.60 (povišene linije); od 7.11. i povišene
glavna = lambda kvv, kvm: 1.65 <= kvv <= 2.2 and 1.65 <= kvm <= 2.2
def prolazi(pravilo, smer, d, kv, kvv=None, kvm=None):
    if pravilo == 'C': return smer == 'manje' and not glavna(kvv, kvm)   # C: bez modela, svaka sporedna linija sa obe kvote
    if not (OD <= d < DO): return False
    return pravilo == 'A' or (smer == 'manje' and (kv >= KV_B or kv < KV_B_NISKA))
# izbor jedne opklade po igraču: A i B najveća razlika model − tržište; C sporedna linija najbliža glavnoj (kvota za „manje“ najbliža 1.90)
ocena = lambda pravilo, d, kv: -abs(kv - 1.9) if pravilo == 'C' else d

def kandidati(kvote, igraci, pravilo='A'):
    ig = {r['igrac']: r for r in igraci}; najb = {}; oc = {}
    for x in kvote:
        r = ig.get(x['igrac'])
        if not r or not x.get('kvota_vise') or not x.get('kvota_manje') or x.get('trz_vise') is None: continue
        if r['status'] != 'Igra' or r.get('utakmice', 9) < 3: continue
        k = K[x['kategorija']]; L = float(x['linija'])
        pm = 1 - Phi((math.floor(L) + .5 - r.get(f'{k}_med', r[f'{k}_proj'])) / r[f'{k}_sd'])   # oko medijane, kao u preporukama
        for smer, m, t, kv in (('više', pm, x['trz_vise'], x['kvota_vise']), ('manje', 1 - pm, 1 - x['trz_vise'], x['kvota_manje'])):
            d = m - t
            o = ocena(pravilo, d, kv)
            if prolazi(pravilo, smer, d, kv, x['kvota_vise'], x['kvota_manje']) and (x['igrac'] not in najb or o > oc[x['igrac']]):
                oc[x['igrac']] = o
                najb[x['igrac']] = dict(**({'pravilo': pravilo} if pravilo != 'A' else {}), kolo=x['kolo'], termin=r['termin'], utakmica=r['utakmica'], igrac=x['igrac'], tim=r['tim'], kategorija=x['kategorija'],
                    linija=L, smer=smer, opklada=f"{x['kategorija'].lower()} {smer} {L:g}", kvota=kv, model=round(m, 3), trziste=round(t, 3), razlika=round(d, 3),
                    knjige=x.get('trz_knjige'), rizik=r.get('iskljuci'), poz=r.get('poz'), minuti_sd=r.get('minuti_sd'))
    return list(najb.values())

def azuriraj(sada=None):
    sada = sada or beograd()
    lista = citaj(FAJL) if os.path.exists(FAJL) else []
    kolo = citaj('kolo.json'); IME = {}
    start = {}
    for h, a, t, u in kolo['games']: start[t] = datetime.datetime.fromisoformat(u.replace('Z', '+00:00'))
    pocela = lambda r: (s := start.get(r['termin'])) is not None and s <= sada
    kv, ig = citaj('kvote_pet.json'), citaj('igraci2.json')
    sad = {(p, c['igrac'], c['kategorija'], c['linija'], c['smer']): c for p in 'ABC' for c in kandidati(kv, ig, p)}
    vreme = sada.strftime('%d.%m. %H:%M'); po_kljucu = {(r.get('pravilo', 'A'), r['kolo'], r['igrac'], r['kategorija'], r['linija'], r['smer']): r for r in lista}
    for r in lista:   # postojeći, nepočeti: osveži ili označi da su ispali
        if r.get('unazad') or pocela(r) or r['kolo'] != kolo['kolo']: continue
        c = sad.get((r.get('pravilo', 'A'), r['igrac'], r['kategorija'], r['linija'], r['smer']))
        if c: r.update(kvota=c['kvota'], model=c['model'], trziste=c['trziste'], razlika=c['razlika'], rizik=c['rizik'], poz=c['poz'], minuti_sd=c['minuti_sd'], ispala=False, poslednje=vreme)
        else: r['ispala'] = True
    for c in sad.values():
        if (c.get('pravilo', 'A'), c['kolo'], c['igrac'], c['kategorija'], c['linija'], c['smer']) in po_kljucu or pocela(c): continue
        lista.append(dict(c, kvota_prva=c['kvota'], zapamceno=vreme, poslednje=vreme, ispala=False, rezultat=None, ishod=None))
    oceni(lista)
    pisi(lista, FAJL, ensure_ascii=False)
    return lista

def oceni(lista):
    R = {}
    for f in glob.glob(os.path.join('prikupljeno', 'rezultati', 'kolo*_*.json')):
        k = int(os.path.basename(f)[4:].split('_')[0])
        for n, mn, p, rb, a in citaj(f):
            l, fn = (n.split(', ', 1) + [''])[:2]; R[(k, kljuc(fn + ' ' + l))] = dict(min=mn, Poeni=p, Skokovi=rb, Asistencije=a)
    for r in lista:
        if r.get('ishod'): continue
        x = R.get((r['kolo'], kljuc(r['igrac'])))
        if not x: continue
        if not x['min']: r.update(rezultat=None, ishod='nije igrao'); continue
        v = x[r['kategorija']]; r['rezultat'] = v
        r['ishod'] = 'prošlo' if (v > r['linija'] if r['smer'] == 'više' else v < r['linija']) else 'palo'

def unazad(kolo, P='B'):
    # iz evidencija.json (poslednje stanje linija pred utakmicu), šansa oko medijane kao u bt analizi; samo igrači sa statusom Igra
    from pomocno import MEDIJANA
    C = citaj('tezine.json')['c']; lista = citaj(FAJL)
    lista = [r for r in lista if not (r.get('pravilo') == P and r['kolo'] == kolo and r.get('unazad'))]   # ponovo, po sadašnjem pravilu
    ter = {}
    for r in citaj('zapamceno.json'):
        if r.get('kolo') == kolo and r.get('utakmica'): ter[r['utakmica']] = r['termin']
    for r in citaj('igraci2.json'):
        if r.get('kolo') == kolo: ter.setdefault(r['utakmica'], r['termin'])
    najb = {}; oc = {}
    for e in citaj('evidencija.json'):
        if e['kolo'] != kolo or e.get('status') != 'Igra' or not e.get('kvota_manje') or e.get('trz_vise') is None: continue
        L = e['linija']; pm = 1 - Phi((math.floor(L) + .5 - (e['proj'] + MEDIJANA[K[e['kategorija']]])) / (e['sd'] * C))
        m, t, kv = 1 - pm, 1 - e['trz_vise'], e['kvota_manje']; d = m - t; k = (e['dan'], e['igrac'])
        o = ocena(P, d, kv)
        if prolazi(P, 'manje', d, kv, e['kvota_vise'], kv) and (k not in najb or o > oc[k]):
            oc[k] = o
            najb[k] = dict(pravilo=P, kolo=kolo, termin=ter.get(e['utakmica'], e['dan']), utakmica=e['utakmica'], igrac=e['igrac'], tim=e['tim'], kategorija=e['kategorija'],
                linija=L, smer='manje', opklada=f"{e['kategorija'].lower()} manje {L:g}", kvota=kv, model=round(m, 3), trziste=round(t, 3), razlika=round(d, 3),
                knjige=None, rizik=None, poz=e.get('poz'), minuti_sd=e.get('minuti_sd'), kvota_prva=kv, zapamceno='unazad', poslednje='unazad', ispala=False, rezultat=None, ishod=None, unazad=True)
    lista += najb.values(); oceni(lista); pisi(lista, FAJL, ensure_ascii=False)
    print(f'Pravilo {P} unazad za {kolo}. kolo: {len(najb)} opklada')

if __name__ == '__main__':
    import sys
    a = [x for x in sys.argv if x.startswith('--unazad-')]
    for x in a: unazad(int(x.split('=')[1]), x[len('--unazad-')])
    L = citaj(FAJL) if a else azuriraj()
    for p in 'ABC':
        M = [r for r in L if r.get('pravilo', 'A') == p and not r.get('ispala')]
        otv = [r for r in M if not r.get('ishod')]; gotove = [r for r in M if r.get('ishod') in ('prošlo', 'palo')]
        pr = sum(r['kvota'] - 1 if r['ishod'] == 'prošlo' else -1 for r in gotove)
        print(f"Probna lista {p}: otvoreno {len(otv)}, završeno {len(gotove)}, prošlo {sum(r['ishod'] == 'prošlo' for r in gotove)}, profit uz 1 po opkladi {pr:+.2f}")
