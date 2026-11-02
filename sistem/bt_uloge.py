# poređenje: stara preraspodela (uloge.py, samo van stroja) vs nova (sastav, povratci, upitni) — po stvarnom minutu
import json, os, subprocess, sys
# Jednokratna provera 9. kola: ulaz f8.json nije sačuvan, a skripta bi inače prepisala igraci2.json podacima sledećeg kola.
if not os.path.exists('f8.json'): sys.exit('bt_uloge: nema f8.json (ulaz jednokratne provere 9. kola), pa provera ne može da se ponovi')
F = json.load(open('f8.json')); SC = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
A = {}
for f in ('results_cet.json', 'results_pet.json'):
    for n, m, p, r, a in json.load(open(f)): A[n] = (m, p, r, a)
def load():
    return {x['api']: x for x in json.load(open('igraci2.json'))}
subprocess.run([sys.executable, 'build5.py'], capture_output=True); subprocess.run([sys.executable, 'dostupnost.py'], capture_output=True)
base = load()
subprocess.run([sys.executable, 'uloge.py'], capture_output=True); old = load()
res = {k: [0, 0, 0, 0] for k in ('pts', 'reb', 'ast')}; n = 0
for api, b in base.items():
    if api not in A or A[api][0] < 5 or not b.get('minuti_proj') or b['status'] == 'Ne igra': continue
    m = A[api][0]; n += 1
    f = F.get(api, [0, 0, 0, 0])
    for idx, k in enumerate(('pts', 'reb', 'ast')):
        y = A[api][1 + idx]; rate0 = b[f'{k}_proj'] / b['minuti_proj']; rateo = old[api][f'{k}_proj'] / old[api]['minuti_proj']
        raten = rate0 * (1 + SC * f[idx] / 100)
        res[k][0] += abs(y - rate0 * m); res[k][1] += abs(y - rateo * m); res[k][2] += abs(y - raten * m)
print('n', n, 'MAE (bez / stara / nova):', {k: [round(v[i] / n, 3) for i in range(3)] for k, v in res.items()})
