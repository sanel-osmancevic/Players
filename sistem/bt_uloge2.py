# Provera preraspodele uloge (uloge.py) "vraćanjem vremena": za kolo R on/off samo iz kola pre R, a odsutni su igrači sa 15+ min koji nisu igrali to kolo.
# Upotreba: py -X utf8 bt_uloge2.py FOLDER, gde su o{kolo}.json iz: node onoff_kes.js KOLO FOLDER/o{KOLO}.json. Ništa ne upisuje.
import os, sys
FOLDER = sys.argv[1]
exec(open('bt_minuti.py', encoding='utf8').read().split("SA_VAN = [u for u")[0])
K_MIN, KE, CAP = 60.0, 10.0, 0.15
usage = lambda v: v[2] + 0.44 * v[3]
GET = {'pts': usage, 'reb': lambda v: v[4], 'ast': lambda v: v[5]}
D = {R: citaj(os.path.join(FOLDER, f'o{R - 1}.json')) for R in range(3, max(KOLA) + 1)}
def udeo(i, t, j, R):
    h = LOG.get((i, t)); played = {r for r in LOG.get((j, t), {}) if r < R}
    if not h: return 1.0
    rr = [r for r in h if r < R]; w = {r: 0.85 ** (R - 1 - r) for r in rr}; mm = {r: h[r]['min'] for r in rr}
    sw = sum(w[r] * mm[r] for r in rr if r in played) / max(1e-9, sum(w[r] * mm[r] for r in rr))
    su = sum(mm[r] for r in rr if r in played) / max(1e-9, sum(mm.values()))
    return sw / su if su > 0 else 1.0
def faktor(i, t, R):
    d = D[R].get(t); outs = van(t, R)
    if not d or not outs or i not in d['tot'] or d['tot'][i][0] < 40: return None
    tot = d['tot'][i]; f = {'pts': 1.0, 'reb': 1.0, 'ast': 1.0}
    for j in outs:
        on = d['on'].get(j, {}).get(i) or [0, 0, 0, 0, 0, 0]; moff = tot[0] - on[0]
        if moff <= 0: continue
        for k, get in GET.items():
            rt = get(tot) / tot[0]
            if rt <= 0: continue
            kk = max(K_MIN, KE / rt); off = (get(tot) - get(on) + rt * kk) / (moff + kk)
            f[k] *= off / (off + (rt - off) * udeo(i, t, j, R))
    return {k: max(1 - CAP, min(1 + CAP, v)) for k, v in f.items()}
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
F = {u: faktor(*u) for u in UZ}; IM = [u for u in UZ if F[u] and any(abs(v - 1) >= 0.01 for v in F[u].values())]
print(f'uzorak: {len(IM)} igrač-utakmica sa korekcijom uloge; prosečna veličina poeni {sum(abs(F[u]["pts"] - 1) for u in IM) / len(IM) * 100:.1f}%')
for naz, jac in (('puna jačina (sadašnje)', 1.0), ('pola jačine', 0.5), ('četvrtina', 0.25)):
    red = f'{naz:<24}'
    for k in K3:
        g = {}
        for u in IM:
            p = proj(*u, SVE[u[2]], PUNI); a = LOG[(u[0], u[1])][u[2]]; mu = p[k][0]
            g.setdefault(a['kod'], []).append(abs(a[k] - mu * (1 + jac * (F[u][k] - 1))) - abs(a[k] - mu))
        m, lo, hi = boot(g); red += f"{k} {m:+.3f} [{lo:+.3f},{hi:+.3f}]{'*' if lo > 0 or hi < 0 else ' '}  "
    print(red)
print('(minus = uloga popravlja procenu; * = interval ne obuhvata nulu)')
for naz, RR in (('kola 3-6', range(3, 7)), ('kola 7-9', range(7, 10))):
    red = f'{naz} puna jačina:      '
    for k in K3:
        e = [abs(LOG[(u[0], u[1])][u[2]][k] - proj(*u, SVE[u[2]], PUNI)[k][0] * F[u][k]) - abs(LOG[(u[0], u[1])][u[2]][k] - proj(*u, SVE[u[2]], PUNI)[k][0]) for u in IM if u[2] in RR]
        red += f'{k} {sum(e) / len(e):+.3f}   '
    print(red)
