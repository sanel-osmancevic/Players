# Da li model precenjuje niske strelce? Projekcija poena samo iz ranijih kola prema stvarnim poenima, kola 3-9, samo igrači koji su igrali (kao opklada).
# Ništa ne upisuje. Upotreba: py -X utf8 bt_niski.py
exec(open('bt_minuti2.py', encoding='utf8').read().split("def dopuna(")[0])
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
BIAS = 0.2   # pomeraj koji model sada dodaje
GR = (('ispod 4', 0, 4), ('4-8', 4, 8), ('8-12', 8, 12), ('12+', 12, 99))
red = []
for u in UZ:
    h = [v for r, v in LOG[(u[0], u[1])].items() if r < u[2]]; a = LOG[(u[0], u[1])][u[2]]
    pm = sum(v['pts'] for v in h) / len(h)
    red.append(dict(u=u, pros=pm, proj=proj(*u, SVE[u[2]], PUNI)['pts'][0], st=a['pts'], kod=a['kod'], R=u[2], min=a['min'], mpros=sum(v['min'] for v in h) / len(h)))
print(f'uzorak {len(red)} igrač-kola, utakmica {len({x["kod"] for x in red})}\n')
print(f"{'prosek pre kola':<16}{'n':>5}{'prosek':>8}{'proj':>7}{'proj+.2':>8}{'stvarno':>8}{'greška (proj-stv)':>26}{'kola 3-6':>10}{'7-9':>8}{'|greška| proj':>15}{'|greška| prosek':>16}")
for ime, lo, hi in GR:
    q = [x for x in red if lo <= x['pros'] < hi]
    g = {}
    for x in q: g.setdefault(x['kod'], []).append(x['proj'] + BIAS - x['st'])
    m, l, h_ = boot(g)
    d = lambda S: sum(x['proj'] + BIAS - x['st'] for x in S) / max(1, len(S))
    print(f"{ime:<16}{len(q):>5}{sum(x['pros'] for x in q) / len(q):>8.2f}{sum(x['proj'] for x in q) / len(q):>7.2f}{sum(x['proj'] + BIAS for x in q) / len(q):>8.2f}{sum(x['st'] for x in q) / len(q):>8.2f}"
          f"{m:>+10.2f} [{l:+.2f},{h_:+.2f}]{'*' if l > 0 or h_ < 0 else ' ':<2}{d([x for x in q if x['R'] <= 6]):>+10.2f}{d([x for x in q if x['R'] > 6]):>+8.2f}"
          f"{sum(abs(x['proj'] + BIAS - x['st']) for x in q) / len(q):>15.2f}{sum(abs(x['pros'] - x['st']) for x in q) / len(q):>16.2f}")
print('\nIsti igrači bez onih čije uloge rastu: minuti u kolu prema proseku')
for ime, lo, hi in GR:
    q = [x for x in red if lo <= x['pros'] < hi]
    print(f"{ime:<16} minuti prosek {sum(x['mpros'] for x in q) / len(q):5.1f} stvarno {sum(x['min'] for x in q) / len(q):5.1f}")
