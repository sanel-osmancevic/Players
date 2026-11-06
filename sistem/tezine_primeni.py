# Primena naučenog (tezine.json).
#  python3 tezine_primeni.py igraci  -> pomeraj projekcije i širina (čuva sirove vrednosti u *_sirovo)
#  python3 tezine_primeni.py kvote   -> težine model/istorija/tržište u svaki red kvota (tez_m, tez_h, tez_t)
import json, sys, os
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
T = citaj('tezine.json') if os.path.exists('tezine.json') else {'bias': {}, 'c': 1.0, 'w': [1/3, 1/3, 1/3]}
# Tržište je stalnih 60%: na 9. kolu je bilo najbolja procena (bt_faktori.py), a model je precenjivao svoje opklade.
# Odnos modela i istorije u preostalih 40% i dalje se uči iz rezultata.
TEZ_TRZISTE = 0.6
_m, _h = T['w'][0], T['w'][1]
# Od 6.11.2026. istorija nema težinu: kad se zna tržište, ne predviđa ništa (bt_formula.py, kola 9-10), pa je ostatak modelu.
TEZ = [round(1 - TEZ_TRZISTE, 3), 0.0, TEZ_TRZISTE]
mode = sys.argv[1]
if mode == 'igraci':
    rows = citaj('igraci2.json')
    for r in rows:
        if r.get('status') == 'Ne igra': continue
        for k in ('pts', 'reb', 'ast'):
            if f'{k}_proj_sirovo' not in r:
                r[f'{k}_proj_sirovo'] = r[f'{k}_proj']; r[f'{k}_sd_sirovo'] = r[f'{k}_sd']
            r[f'{k}_proj'] = round(r[f'{k}_proj_sirovo'] + T['bias'].get(k, 0.0), 1)
            r[f'{k}_sd'] = round(r[f'{k}_sd_sirovo'] * T.get('c', 1.0), 2)
    pisi(rows, 'igraci2.json', ensure_ascii=False)
    print('primenjen pomeraj', T['bias'], 'širina x', T.get('c'))
elif mode == 'kvote':
    for fn in ('kvote.json', 'kvote_pet.json'):
        rows = citaj(fn)
        for x in rows:
            if x.get('igrac'): x['tez_m'], x['tez_h'], x['tez_t'] = TEZ; x['tez_ls'] = T.get('w_ls', 0.2)
        pisi(rows, fn, ensure_ascii=False)
    print('težine model/istorija/tržište', TEZ)
