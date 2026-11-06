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
#   redovi bez polja su pravilo A.
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

KV_B = 1.95
def prolazi(pravilo, smer, d, kv):
    if not (OD <= d < DO): return False
    return pravilo == 'A' or (smer == 'manje' and kv >= KV_B)

def kandidati(kvote, igraci, pravilo='A'):
    ig = {r['igrac']: r for r in igraci}; najb = {}
    for x in kvote:
        r = ig.get(x['igrac'])
        if not r or not x.get('kvota_vise') or not x.get('kvota_manje') or x.get('trz_vise') is None: continue
        if r['status'] != 'Igra' or r.get('utakmice', 9) < 3: continue
        k = K[x['kategorija']]; L = float(x['linija'])
        pm = 1 - Phi((math.floor(L) + .5 - r.get(f'{k}_med', r[f'{k}_proj'])) / r[f'{k}_sd'])   # oko medijane, kao u preporukama
        for smer, m, t, kv in (('više', pm, x['trz_vise'], x['kvota_vise']), ('manje', 1 - pm, 1 - x['trz_vise'], x['kvota_manje'])):
            d = m - t
            if prolazi(pravilo, smer, d, kv) and (x['igrac'] not in najb or d > najb[x['igrac']]['razlika']):
                najb[x['igrac']] = dict(**({'pravilo': 'B'} if pravilo == 'B' else {}), kolo=x['kolo'], termin=r['termin'], utakmica=r['utakmica'], igrac=x['igrac'], tim=r['tim'], kategorija=x['kategorija'],
                    linija=L, smer=smer, opklada=f"{x['kategorija'].lower()} {smer} {L:g}", kvota=kv, model=round(m, 3), trziste=round(t, 3), razlika=round(d, 3),
                    knjige=x.get('trz_knjige'), rizik=r.get('iskljuci'))
    return list(najb.values())

def azuriraj(sada=None):
    sada = sada or beograd()
    lista = citaj(FAJL) if os.path.exists(FAJL) else []
    kolo = citaj('kolo.json'); IME = {}
    start = {}
    for h, a, t, u in kolo['games']: start[t] = datetime.datetime.fromisoformat(u.replace('Z', '+00:00'))
    pocela = lambda r: (s := start.get(r['termin'])) is not None and s <= sada
    kv, ig = citaj('kvote_pet.json'), citaj('igraci2.json')
    sad = {(p, c['igrac'], c['kategorija'], c['linija'], c['smer']): c for p in 'AB' for c in kandidati(kv, ig, p)}
    vreme = sada.strftime('%d.%m. %H:%M'); po_kljucu = {(r.get('pravilo', 'A'), r['kolo'], r['igrac'], r['kategorija'], r['linija'], r['smer']): r for r in lista}
    for r in lista:   # postojeći, nepočeti: osveži ili označi da su ispali
        if r.get('unazad') or pocela(r) or r['kolo'] != kolo['kolo']: continue
        c = sad.get((r.get('pravilo', 'A'), r['igrac'], r['kategorija'], r['linija'], r['smer']))
        if c: r.update(kvota=c['kvota'], model=c['model'], trziste=c['trziste'], razlika=c['razlika'], rizik=c['rizik'], ispala=False, poslednje=vreme)
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

def unazad_B(kolo):
    # iz evidencija.json (poslednje stanje linija pred utakmicu), šansa oko medijane kao u bt analizi; samo igrači sa statusom Igra
    from pomocno import MEDIJANA
    C = citaj('tezine.json')['c']; lista = citaj(FAJL)
    if any(r.get('pravilo') == 'B' and r['kolo'] == kolo for r in lista): return print(f'Pravilo B za {kolo}. kolo već postoji')
    ter = {}
    for r in citaj('zapamceno.json'):
        if r.get('kolo') == kolo and r.get('utakmica'): ter[r['utakmica']] = r['termin']
    for r in citaj('igraci2.json'):
        if r.get('kolo') == kolo: ter.setdefault(r['utakmica'], r['termin'])
    najb = {}
    for e in citaj('evidencija.json'):
        if e['kolo'] != kolo or e.get('status') != 'Igra' or not e.get('kvota_manje') or e.get('trz_vise') is None: continue
        L = e['linija']; pm = 1 - Phi((math.floor(L) + .5 - (e['proj'] + MEDIJANA[K[e['kategorija']]])) / (e['sd'] * C))
        m, t, kv = 1 - pm, 1 - e['trz_vise'], e['kvota_manje']; d = m - t; k = (e['dan'], e['igrac'])
        if prolazi('B', 'manje', d, kv) and (k not in najb or d > najb[k]['razlika']):
            najb[k] = dict(pravilo='B', kolo=kolo, termin=ter.get(e['utakmica'], e['dan']), utakmica=e['utakmica'], igrac=e['igrac'], tim=e['tim'], kategorija=e['kategorija'],
                linija=L, smer='manje', opklada=f"{e['kategorija'].lower()} manje {L:g}", kvota=kv, model=round(m, 3), trziste=round(t, 3), razlika=round(d, 3),
                knjige=None, rizik=None, kvota_prva=kv, zapamceno='unazad', poslednje='unazad', ispala=False, rezultat=None, ishod=None, unazad=True)
    lista += najb.values(); oceni(lista); pisi(lista, FAJL, ensure_ascii=False)
    print(f'Pravilo B unazad za {kolo}. kolo: {len(najb)} opklada')

if __name__ == '__main__':
    import sys
    a = [x for x in sys.argv if x.startswith('--unazad-B=')]
    if a: unazad_B(int(a[0].split('=')[1]))
    L = citaj(FAJL) if a else azuriraj()
    for p in 'AB':
        M = [r for r in L if r.get('pravilo', 'A') == p and not r.get('ispala')]
        otv = [r for r in M if not r.get('ishod')]; gotove = [r for r in M if r.get('ishod') in ('prošlo', 'palo')]
        pr = sum(r['kvota'] - 1 if r['ishod'] == 'prošlo' else -1 for r in gotove)
        print(f"Probna lista {p}: otvoreno {len(otv)}, završeno {len(gotove)}, prošlo {sum(r['ishod'] == 'prošlo' for r in gotove)}, profit uz 1 po opkladi {pr:+.2f}")
