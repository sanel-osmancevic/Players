# Da li najbolji strelci daju više u izjednačenim utakmicama? Kola 3-9, projekcija samo iz ranijih kola. Ništa ne upisuje. Upotreba: py -X utf8 bt_gusto.py
# Pre utakmice: razlika u kvaliteti timova iz ranijih kola (poen razlike po utakmici, domaći +3). Posle utakmice: stvarna razlika, samo kao objašnjenje, to se ne zna unapred.
exec(open('bt_minuti2.py', encoding='utf8').read().split("def dopuna(")[0])
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
BIAS = 0.2
UT = {}
for g in G:
    if not g.get('h') or not g.get('a'): continue
    a, b = g['s']['local']['total']['points'], g['s']['road']['total']['points']
    UT[g['kod']] = dict(R=g['kolo'], h=g['h'], a=g['a'], ph=a, pa=b)
def snaga(t, R):
    x = [(u['ph'] - u['pa']) if u['h'] == t else (u['pa'] - u['ph']) for u in UT.values() if u['R'] < R and t in (u['h'], u['a'])]
    return sum(x) / len(x) if x else 0.0
def razlika_pre(k):
    u = UT[k]; return abs(snaga(u['h'], u['R']) - snaga(u['a'], u['R']) + 3)
red = []
for u in UZ:
    a = LOG[(u[0], u[1])][u[2]]
    if a['kod'] not in UT: continue
    h = [v for r, v in LOG[(u[0], u[1])].items() if r < u[2]]; z = UT[a['kod']]
    red.append(dict(pros=sum(v['pts'] for v in h) / len(h), mpros=sum(v['min'] for v in h) / len(h), proj=proj(*u, SVE[u[2]], PUNI)['pts'][0] + BIAS, st=a['pts'], min=a['min'], kod=a['kod'],
                    pre=razlika_pre(a['kod']), posle=abs(z['ph'] - z['pa']), zbir=z['ph'] + z['pa']))
def tabela(naslov, grupe):
    print(f"\n{naslov}\n{'grupa':<34}{'n':>5}{'proj':>7}{'stvarno':>8}{'razlika':>9}  {'interval':<18}{'minuti prema proseku':>21}")
    for ime, q in grupe:
        if not q: continue
        g = {}
        for x in q: g.setdefault(x['kod'], []).append(x['st'] - x['proj'])
        m, l, h = boot(g)
        print(f"{ime:<34}{len(q):>5}{sum(x['proj'] for x in q) / len(q):>7.2f}{sum(x['st'] for x in q) / len(q):>8.2f}{m:>+9.2f}  [{l:+.2f},{h:+.2f}]{'*' if l > 0 or h < 0 else ' ':<2}{sum(x['min'] - x['mpros'] for x in q) / len(q):>+15.2f}")
ST = [x for x in red if x['pros'] >= 12]; OS = [x for x in red if x['pros'] < 12]
pre = sorted(UT, key=razlika_pre); tr = len(pre) // 3
GR = {k: i for i, s in enumerate((pre[:tr], pre[tr:2 * tr], pre[2 * tr:])) for k in s}
print('utakmica', len(UT), 'granice razlike pre utakmice', round(razlika_pre(pre[tr]), 1), round(razlika_pre(pre[2 * tr]), 1))
NAZ = ('izjednačena', 'srednja', 'neravna')
tabela('PRE UTAKMICE (može da se koristi): strelci 12+', [(NAZ[i], [x for x in ST if GR[x['kod']] == i]) for i in range(3)])
tabela('PRE UTAKMICE: ostali', [(NAZ[i], [x for x in OS if GR[x['kod']] == i]) for i in range(3)])
tabela('POSLE UTAKMICE (ne zna se unapred): strelci 12+', [('razlika do 5', [x for x in ST if x['posle'] <= 5]), ('6-14', [x for x in ST if 5 < x['posle'] < 15]), ('15+', [x for x in ST if x['posle'] >= 15])])
tabela('POSLE UTAKMICE: ostali', [('razlika do 5', [x for x in OS if x['posle'] <= 5]), ('6-14', [x for x in OS if 5 < x['posle'] < 15]), ('15+', [x for x in OS if x['posle'] >= 15])])
zz = sorted(x['zbir'] for x in red); a, b = zz[len(zz) // 3], zz[2 * len(zz) // 3]
tabela(f'POSLE UTAKMICE, po ukupnom zbiru (granice {a}, {b}): strelci 12+', [('nizak', [x for x in ST if x['zbir'] <= a]), ('srednji', [x for x in ST if a < x['zbir'] <= b]), ('visok', [x for x in ST if x['zbir'] > b])])
tabela('POSLE UTAKMICE, po ukupnom zbiru: ostali', [('nizak', [x for x in OS if x['zbir'] <= a]), ('srednji', [x for x in OS if a < x['zbir'] <= b]), ('visok', [x for x in OS if x['zbir'] > b])])
