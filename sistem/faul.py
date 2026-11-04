# Tačka 2: sklonost faulovima. Iz zapisnika kola 1–8: faulovi po 40 minuta (skupljeni ka proseku)
# i udeo utakmica sa 4+ faula. Igrač sa visokim rizikom: manje očekivanih minuta i veće rasipanje.
#   višak = stopa po 40 − prosek;  minuti i projekcije × (1 − 1,5% po višku, najviše −6%);  sd × (1 + 3% po višku, najviše +12%)
import json, re, unicodedata, os
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from kolo import DAN, IME as TEAM
F = citaj('faulovi.json')
tot_f = sum(v[2] for v in F.values()); tot_m = sum(v[1] for v in F.values())
AVG = tot_f / tot_m * 40  # prosek lige po 40 minuta
K = 60  # minuta skupljanja ka proseku
idx = {}
for k, (g, m, f, g4) in F.items():
    n, t = k.split('|')
    rate = (f + AVG / 40 * K) / (m + K) * 40
    idx[(n, TEAM[t])] = (round(rate, 2), g4, g)
# sudije: sudije_kolo.json {"Domaćin – Gost": [["SUDIJA 1", ...], indeks_faulova, indeks_slobodnih_bacanja]} (dan utakmice, sa zvaničnog sajta)
SK = citaj('sudije_kolo.json') if os.path.exists('sudije_kolo.json') else {}
rows = citaj('igraci2.json'); n_adj = 0
for r in rows:
    if not r['termin'].startswith(DAN) or r['status'] == 'Ne igra': continue
    v = idx.get((r.get('api'), r['tim']))
    if not v: continue
    rate, g4, g = v
    sk = SK.get(r['utakmica'])
    if sk and sk[1]:
        rate = round(rate * sk[1], 2); r['sudije'] = ', '.join(sk[0]); r['sudije_faul'] = sk[1]; r['sudije_ft'] = sk[2]
        # više/manje slobodnih bacanja -> poeni srazmerno udelu poena iz slobodnih bacanja
        uft = float(r.get('udeo_ft') or 18) / 100   # udeo_ft je u procentima
        if sk[2]: r['pts_proj'] = round(r['pts_proj'] * (1 + (sk[2] - 1) * uft), 1)
    r['faul_40'] = rate; r['faul_4plus'] = f'{g4}/{g}'
    visak = rate - AVG
    if visak <= 0.5: continue
    mf = max(0.94, 1 - 0.015 * visak); sf = min(1.12, 1 + 0.03 * visak)
    r['faul_faktor'] = round(mf, 3)
    r['minuti_proj'] = round(r['minuti_proj'] * mf, 1)
    for k in ('pts', 'reb', 'ast'):
        r[f'{k}_proj'] = round(r[f'{k}_proj'] * mf, 1)
        r[f'{k}_sd'] = round(r[f'{k}_sd'] * sf, 2)
        if f'{k}_proj_sirovo' in r:
            r[f'{k}_proj_sirovo'] = round(r[f'{k}_proj_sirovo'] * mf, 1); r[f'{k}_sd_sirovo'] = round(r[f'{k}_sd_sirovo'] * sf, 2)
    n_adj += 1
pisi(rows, 'igraci2.json', ensure_ascii=False)
print(f'faulovi: prosek {AVG:.2f} po 40 min; korigovano {n_adj} igrača')
