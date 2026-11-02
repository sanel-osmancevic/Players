# Usklađivanje šansi sa stvarnošću (Platt): p' = 1/(1+exp(-(a·logit(p)+b))), naučeno iz svih ocenjenih Maxbet linija
# (evidencija.json: obe strane linije, igrač igrao). Skupljeno ka "bez promene" (a=1, b=0) dok je uzorak mali.
import json, math
E = [e for e in json.load(open('evidencija.json')) if e.get('rezultat') is not None and e.get('kvota_manje')
     and (e.get('minuti_stvarno') or 0) > 0 and e.get('sansa_vise') is not None]
X = []
for e in E:
    p = min(max(float(e['sansa_vise']), 0.02), 0.98); X.append((math.log(p / (1 - p)), 1 if e['proslo_vise'] else 0))
def nll(a, b, lam=None):
    s = 0
    for x, y in X:
        q = 1 / (1 + math.exp(-(a * x + b))); q = min(max(q, 1e-6), 1 - 1e-6); s -= math.log(q if y else 1 - q)
    return s
best = min(((nll(a / 100, b / 100), a / 100, b / 100) for a in range(20, 151, 5) for b in range(-30, 31, 2)))
n = len(X); K = 1000   # prior: 1000 linija bez promene (uzorak od 2 dana je mali; izabrane opklade su prolazile bolje od svih linija)
a = (n * best[1] + K * 1.0) / (n + K); b = (n * best[2]) / (n + K)
ll0 = nll(1, 0) / n; ll1 = nll(a, b) / n
json.dump({'a': round(a, 3), 'b': round(b, 3), 'n': n, 'a_sirovo': best[1], 'b_sirovo': best[2],
           'logloss_pre': round(ll0, 4), 'logloss_posle': round(ll1, 4)}, open('kalibracija.json', 'w'))
f = lambda p: 1 / (1 + math.exp(-(a * math.log(p / (1 - p)) + b)))
print(f"kalibracija na {n} linija: a={a:.3f} b={b:.3f} (sirovo {best[1]}, {best[2]}); log-loss {ll0:.4f} -> {ll1:.4f};",
      'primer 60%->', f"{f(0.6):.3f}", '70%->', f"{f(0.7):.3f}", '75%->', f"{f(0.75):.3f}")
