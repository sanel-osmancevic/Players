# Tačka 3: u svaki red kvota upisuje koliko puta bi linija prošla prošle sezone (samo utakmice sa sličnom ulogom: minuti ±30%).
import json, os
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from kolo import DAN
LS = citaj('prosla_sezona.json'); PAY = citaj('ls_payload.json')
ig = {r['igrac']: r for r in citaj('igraci2.json') if r['termin'].startswith(DAN)}
C = {'Poeni': 'P', 'Skokovi': 'S', 'Asistencije': 'A'}
for fn in ('kvote.json', 'kvote_pet.json'):
    rows = citaj(fn); n = 0
    for x in rows:
        r = ig.get(x.get('igrac')); 
        if not r: continue
        a = r.get('api'); ls = LS.get(a); pay = PAY.get(a)
        if not ls or not pay: continue
        c = C[x['kategorija']]
        if c not in ls or c not in pay or x['linija'] not in pay[c]: continue
        h = ls[c][pay[c].index(x['linija'])]
        x['ls_vise'] = h; x['ls_n'] = ls['nc']; n += 1
    pisi(rows, fn, ensure_ascii=False)
print('linije sa prošlom sezonom:', n)
