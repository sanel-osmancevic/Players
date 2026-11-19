# Preporuke iz probnih lista (od 19.11.2026, korisnik: „za preporuke stavi ono što misliš da dolazi na osnovu probnih lista“).
# Pravilo: opklada liste F (poeni „manje“ na glavnoj Maxbet liniji, kvota za „manje“ najbliža 1.85 u opsegu 1.40-2.30, igrač sa
#   22+ projektovanih minuta) za igrača koji je istog dana i na listi E (model daje 60%+ za „manje“ na povišenoj liniji, bez centara).
#   Na kolima 9-12 (proba_lista.json, 19.11.): 118 opklada, prošlo 65%, +24% po kvoti, u plusu u svakom kolu (+5.7, +7.2, +5.8, +9.9);
#   sama lista F 63% (+20%), F bez potvrde liste E 60% (+14%). Pravilo je izabrano gledajući ta kola, pa je prava provera od 19.11.
# Iz starih preporuka ostaje: bez igrača sa rizikom uloge (iskljuci) i bez „poeni manje“ kad igraču raste uloga (veca_uloga).
# Ulog je ravan (ULOG j. po opkladi; osvezi.py), jer šansa pravila nije po opkladi nego za celu grupu.
# Upis: picks_pet3.json (zamenjuje izlaz t28.js), poziva ga osvezi.py posle proba.py.
import os
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
GRUPA = 'Probne E+F'
SANSA = 0.58   # za prikaz i CLV: 65% iz kola 9-12 skupljeno ka 50%, jer je pravilo izvedeno iz tih kola
ULOG = 0.5

def napravi(dan=None):
    from kolo import KOLO, DAN
    dan = dan or DAN
    L = [r for r in citaj('proba_lista.json') if r['kolo'] == KOLO and not r.get('unazad') and not r.get('ispala') and not r.get('ishod')
         and str(r['termin']).startswith(dan)]
    u_E = {r['igrac'] for r in L if r.get('pravilo') == 'E'}
    ig = {r['igrac']: r for r in citaj('igraci2.json') if r.get('kolo') == KOLO}
    out = []
    for r in L:
        if r.get('pravilo') != 'F' or r['igrac'] not in u_E: continue
        p = ig.get(r['igrac'])
        if not p or p.get('status') != 'Igra' or p.get('iskljuci') or p.get('veca_uloga'): continue
        kv = float(r['kvota']); L = float(r['linija'])
        vals = [int(v) for v in str(p.get('pts_sve') or '').split(',') if v != '']
        ist = f"{sum(v < L for v in vals)}/{len(vals)}" if vals else None
        f5 = f"{sum(v < L for v in vals[-5:])}/{len(vals[-5:])}" if vals else None
        out.append(dict(kljuc=f"K{KOLO} {r['igrac']} {r['kategorija']}", kolo=KOLO, termin=r['termin'], red=p.get('red'), igrac=r['igrac'],
            utakmica=r['utakmica'], kategorija=r['kategorija'], smer=r['smer'], linija=r['linija'], opklada=r['opklada'], kvota=kv,
            sansa=SANSA, vrednost=round(SANSA * kv - 1, 3), model=r.get('model'), trziste=r.get('trziste'), minuti=r.get('minuti'),
            razmak=None, stabilan=None, istorija=ist, forma5=f5, klupa=False, kretanje=None, grupa=GRUPA))
    out.sort(key=lambda x: (-(x['minuti'] or 0)))
    for i, x in enumerate(out): x['rang'] = i + 1
    pisi(out, 'picks_pet3.json', ensure_ascii=False)
    return out

if __name__ == '__main__':
    for x in napravi(): print(x['igrac'], '|', x['utakmica'], '|', x['opklada'], x['kvota'], '| min', x['minuti'])
