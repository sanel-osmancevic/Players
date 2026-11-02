# Tačka 5: minute. (a) rizik ubedljivog ishoda po timu: verovatnoća razlike 15+ iz kvota utakmice x koliko
# taj trener skraćuje startere u rešenim utakmicama (iz zapisnika, skupljeno ka proseku lige);
# (b) kratak odmor: 1 dan između utakmica -> igrači sa 26+ minuta -2%.
# Primenjuje se na minute i projekcije (poeni/skokovi/asistencije srazmerno minutima).
import json, math, os
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from kolo import DAN, KOD as CODE
from statistics import NormalDist
N = NormalDist()
M = citaj('minute_timovi.json'); G = citaj('kvote_utakmica.json')
SD_MARGIN = 12.5
r_all = [b / c for n, b, c in M['rasturi'].values() if n and b and c]
R_LG = sum(r_all) / len(r_all)
def ratio(tc):
    n, b, c = M['rasturi'].get(tc, [0, None, None])
    r = b / c if n and b and c else R_LG
    return (n * r + 3 * R_LG) / (n + 3)
rows = citaj('igraci2.json'); log = []
for r in rows:
    g = G.get(r['utakmica'])
    if not g or r['status'] == 'Ne igra' or not r['termin'].startswith(DAN): continue
    tot, oh, oa = g; ph = (1 / oh) / (1 / oh + 1 / oa)
    mu = SD_MARGIN * N.inv_cdf(min(max(ph, 0.02), 0.98))
    p_blow = (1 - N.cdf((15 - mu) / SD_MARGIN)) + N.cdf((-15 - mu) / SD_MARGIN)
    tc = CODE[r['tim']]; f = 1.0
    if r['minuti_proj'] >= 24: f *= 1 - p_blow * (1 - ratio(tc))
    if M['odmor_dana'].get(tc, 2) <= 1 and r['minuti_proj'] >= 26: f *= 0.98
    f = round(f, 3)
    r['minuti_faktor'] = f; r['rizik_rasturi'] = round(p_blow, 2)
    if f != 1.0:
        r['minuti_proj'] = round(r['minuti_proj'] * f, 1)
        for k in ('pts', 'reb', 'ast'): r[f'{k}_proj'] = round(r[f'{k}_proj'] * f, 1)
        log.append((r['igrac'], r['tim'], f, round(p_blow, 2)))
pisi(rows, 'igraci2.json', ensure_ascii=False)
print('minute korigovane za', len(log), 'igrača; prosek lige skraćenja startera', round(R_LG, 3))
