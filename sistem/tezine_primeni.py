# Primena naučenog (tezine.json).
#  python3 tezine_primeni.py igraci  -> pomeraj projekcije i širina (čuva sirove vrednosti u *_sirovo)
#  python3 tezine_primeni.py kvote   -> težine model/istorija/tržište u svaki red kvota (tez_m, tez_h, tez_t)
import json, sys, os
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
T = citaj('tezine.json') if os.path.exists('tezine.json') else {'bias': {}, 'c': 1.0, 'w': [1/3, 1/3, 1/3]}
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
            if x.get('igrac'): x['tez_m'], x['tez_h'], x['tez_t'] = T['w']; x['tez_ls'] = T.get('w_ls', 0.2)
        pisi(rows, fn, ensure_ascii=False)
    print('težine model/istorija/tržište', T['w'])
