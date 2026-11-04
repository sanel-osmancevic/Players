# Usklađivanje šansi sa stvarnošću (Platt): p' = 1/(1+exp(-(a·logit(p)+b))), naučeno iz svih ocenjenih Maxbet linija
# (evidencija.json: igrač igrao, linija sa obe kvote, poznato tržište), na istoj šansi koja se koristi za preporuke:
# model, istorija i tržište. Uči se za „više“; za „manje“ se primenjuje na suprotnu stranu (kal u osvezi.py).
# Skupljeno ka "bez promene" (a=1, b=0) dok je uzorak mali.
import json, math
from pomocno import citaj, pisi
T = citaj('tezine.json')
TEZ_TRZISTE = 0.6
_m, _h = T['w'][0], T['w'][1]
WM, WH = (1 - TEZ_TRZISTE) * _m / (_m + _h), (1 - TEZ_TRZISTE) * _h / (_m + _h)
KLJ = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
def sansa(e):
    if e.get('sansa_prava_vise') is not None: return float(e['sansa_prava_vise'])
    # stari redovi: iz sačuvanih delova, sa sadašnjim težinama
    wl = T.get('w_ls', 0.2); h, n = map(int, e['ist_vise'].split('/'))
    ph = (h + wl * (e.get('ls_vise') or 0) + 1) / (n + wl * (e.get('ls_n') or 0) + 2)
    pm = 1 - Phi((math.floor(e['linija']) + 0.5 - (e['proj'] + T['bias'].get(KLJ[e['kategorija']], 0))) / (e['sd'] * T.get('c', 1)))
    return WM * pm + WH * ph + TEZ_TRZISTE * float(e['trz_vise'])
E = [e for e in citaj('evidencija.json') if e.get('rezultat') is not None and e.get('kvota_manje')
     and (e.get('minuti_stvarno') or 0) > 0 and e.get('trz_vise') is not None]
X = []
for e in E:
    p = min(max(sansa(e), 0.02), 0.98); X.append((math.log(p / (1 - p)), 1 if e['proslo_vise'] else 0))
if not X: raise SystemExit('kalibracija: još nema ocenjenih linija')
def nll(a, b):
    s = 0
    for x, y in X:
        q = 1 / (1 + math.exp(-(a * x + b))); q = min(max(q, 1e-6), 1 - 1e-6); s -= math.log(q if y else 1 - q)
    return s
best = min(((nll(a / 100, b / 100), a / 100, b / 100) for a in range(20, 151, 5) for b in range(-30, 31, 2)))
n = len(X); K = 1000   # prior: 1000 linija bez promene (linije istog igrača nisu nezavisne, a uzorak je još mali)
# Pomak b daje prednost jednoj strani (više ili manje), a to iz jednog kola ne može da se razlikuje od slučaja: uči se tek od 3 kola
KOLA = len({e['kolo'] for e in E}); NAJMANJE_KOLA_ZA_POMAK = 3
a = (n * best[1] + K * 1.0) / (n + K); b = (n * best[2]) / (n + K) if KOLA >= NAJMANJE_KOLA_ZA_POMAK else 0.0
ll0 = nll(1, 0) / n; ll1 = nll(a, b) / n
pisi({'a': round(a, 3), 'b': round(b, 3), 'n': n, 'a_sirovo': best[1], 'b_sirovo': best[2],
           'logloss_pre': round(ll0, 4), 'logloss_posle': round(ll1, 4)}, 'kalibracija.json')
f = lambda p: 1 / (1 + math.exp(-(a * math.log(p / (1 - p)) + b)))
print(f"kalibracija na {n} linija: a={a:.3f} b={b:.3f} (sirovo {best[1]}, {best[2]}); log-loss {ll0:.4f} -> {ll1:.4f};",
      'primer više 60%->', f"{f(0.6):.3f}", 'manje 60%->', f"{1 - f(0.4):.3f}")
