# Preraspodela šuteva, poena, skokova i asistencija prema sastavu (zamena za uloge.py).
# Ulaz: uloge_faktori.json = {"PREZIME, IME": [pts%, reb%, ast%, fga%, "objašnjenje"]} iz snippets/onoff.js + snippets/uloge_faktori.js
#   (pokriva: igrači van stroja, upitni, i povratak igrača koji je propustio poslednje kolo).
# Primenjuje se sa težinom TEZ (provera na kolu 9: učinak po minuti se nije merljivo popravio, pa je težina umerena;
# asistencije se ne primenjuju dok podaci ne pokažu da pomažu). Težine se preispituju posle svakog kola.
import json, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
TEZ = {'pts': 0.5, 'reb': 0.5, 'ast': 0.0}
F = json.load(open('uloge_faktori.json'))
rows = json.load(open('igraci2.json')); out = []
for r in rows:
    if r['status'] == 'Ne igra': continue
    f = F.get(r['api'])
    pre, sast = r.get('minuti_pre_sastava'), r.get('minuti_sastav')
    rast = ((sast / pre) if pre and sast else 1.0) * (1 + (f[0] if f else 0) / 100) - 1   # očekivani poeni zbog sastava
    if rast >= 0.08:   # zbog izostanaka saigrača igrač dobija 8%+ više poena (minuti x šutevi): ne igramo "poeni manje"
        r['veca_uloga'] = f"Veća uloga zbog izostanaka: očekivano {100*rast:+.0f}% poena (minuti {(sast or 0)-(pre or 0):+.1f}, šutevi {(f[3] if f else 0):+d}%)"
    if not f: continue
    for idx, k in enumerate(('pts', 'reb', 'ast')):
        p = f[idx] * TEZ[k]
        r[f'uloga_{k}'] = round(p, 1)
        r[f'{k}_proj'] = round(r[f'{k}_proj'] * (1 + p / 100), 1)
    r['sutevi_promena'] = f[3]
    r['uloga_zbog'] = f[4] if len(f) > 4 else ''
    if max(abs(f[0]), abs(f[1]), abs(f[3])) >= 8:
        out.append(dict(igrac=r['igrac'], tim=r['tim'], pts=f[0], reb=f[1], ast=f[2], sutevi=f[3], zbog=r['uloga_zbog']))
json.dump(rows, open('igraci2.json', 'w'), ensure_ascii=False)
json.dump(out, open('uloge.json', 'w'), ensure_ascii=False)
print('uloge (sastav): korigovano', len(out), 'igrača sa većom promenom šuteva/poena/skokova')
if '-v' in sys.argv:
    for o in out: print(f"{o['igrac'][:22]:22s} šutevi {o['sutevi']:+d}% poeni {o['pts']:+d}% skok {o['reb']:+d}% ast {o['ast']:+d}% | {o['zbog'][:100]}")
