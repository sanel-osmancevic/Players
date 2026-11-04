# Dopuna minuta kad je zbir tima nizak. Radi kao bt_minuti.py, ništa ne upisuje. Upotreba: py -X utf8 bt_minuti2.py
# Rezultat 04.11.2026, kola 3-9: dopuna ne smanjuje grešku ni na jednom pragu, pa nije ugrađena (tim sa zbirom ispod 170 stvarno ima oko 165).
import sys
exec(open('bt_minuti.py', encoding='utf8').read().split("V = {\n")[0])
exec("def boot(gr):\n    g = list(gr.values()); rng = random.Random(7); m = sum(map(sum, g)) / sum(map(len, g)); b = []\n    for _ in range(1500):\n        u = [g[rng.randrange(len(g))] for _ in g]; b.append(sum(map(sum, u)) / sum(map(len, u)))\n    b.sort(); return m, b[37], b[1462]\n")
grp = lambda p: 'G' if p == 'G' else 'FC'
def igraju(t, R): return [m for m in EKIPA[t] if R in LOG[(m, t)] and sum(1 for r in LOG[(m, t)] if r < R) >= 2]
_b = {}
def sad(n, t, R):   # kao build5 danas: zaborav i dodatak 0.3 do +2 min
    k = (n, t, R)
    if k in _b: return _b[k]
    base = pros(n, t, R); b = 0.0
    ig = igraju(t, R)
    for x in van(t, R, 10.0):
        if grp(POS[(x, t)]) != grp(POS[(n, t)]): continue
        tot = sum(pros(m, t, R) for m in ig if grp(POS[(m, t)]) == grp(POS[(x, t)]))
        if tot: b = min(2.0, b + pros(x, t, R) * 0.3 * base / tot)
    _b[k] = base + b
    return _b[k]
def dopuna(T, hi=1.35, mx=36.0, jac=1.0):
    def f(n, t, R):
        ig = igraju(t, R); s = sum(sad(m, t, R) for m in ig)
        if s >= T or n not in ig: return sad(n, t, R)
        fk = min(hi, T / s)
        return min(max(mx, sad(n, t, R)), sad(n, t, R) * (1 + jac * (fk - 1)))
    return f
def zbir(t, R): return sum(sad(m, t, R) for m in igraju(t, R))
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
T_R = sorted({(t, R) for _, t, R in UZ})
zz = sorted(zbir(t, R) for t, R in T_R)
stv = lambda t, R: sum(LOG[(m, t)][R]['min'] for m in igraju(t, R))
print('timova-kola', len(T_R), 'zbir modela: min', round(zz[0]), 'p10', round(zz[len(zz) // 10]), 'med', round(zz[len(zz) // 2]), 'p90', round(zz[len(zz) * 9 // 10]), 'max', round(zz[-1]))
for gran in (170, 180, 190):
    L = [(t, R) for t, R in T_R if zbir(t, R) < gran]
    if L: print(f'zbir < {gran}: {len(L)} tim-kola, model {sum(zbir(*x) for x in L) / len(L):.0f}, stvarni minuti istih igrača {sum(stv(*x) for x in L) / len(L):.0f}')
print(f"\n{'varijanta':<26}{'svi igrači: min':>16}  {'podskup zbir<T':>16} {'n':>5} {'greška min':>11} {'95% interval':<18}")
OSN = {u: abs(LOG[(u[0], u[1])][u[2]]['min'] - sad(*u)) for u in UZ}
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
def ucinak(fn, S):
    izl = {}
    for k in K3:
        g = {}
        for u in S:
            p = proj(*u, SVE[u[2]], PUNI); a = LOG[(u[0], u[1])][u[2]]; b = sad(*u)
            mu = p[k][0] * (pros(*u) and b / pros(*u)); g.setdefault(a['kod'], []).append(abs(a[k] - mu * fn(*u) / b) - abs(a[k] - mu))
        m, lo, hi = boot(g); izl[k] = f"{m:+.3f}[{lo:+.3f},{hi:+.3f}]{'*' if lo > 0 or hi < 0 else ''}"
    return izl
for T in (175, 180, 185, 190, 195, 200):
    for hi, jac in ((1.35, 1.0), (1.35, 0.5)):
        fn = dopuna(T, hi, 36.0, jac)
        S = [u for u in UZ if zbir(u[1], u[2]) < T]
        g = {}
        for u in S: g.setdefault(LOG[(u[0], u[1])][u[2]]['kod'], []).append(abs(LOG[(u[0], u[1])][u[2]]['min'] - fn(*u)) - OSN[u])
        svi = sum(abs(LOG[(u[0], u[1])][u[2]]['min'] - fn(*u)) for u in UZ) / len(UZ)
        if not S: continue
        m, lo, h2 = boot(g)
        print(f"T={T} jačina {jac:<12}{svi:>16.3f}  {sum(OSN[u] for u in S) / len(S):>16.3f} {len(S):>5} {m:>+11.3f} [{lo:+.3f},{h2:+.3f}]{'*' if lo > 0 or h2 < 0 else ' '}")
        if jac == 1.0: print('   učinak u podskupu:', ucinak(fn, S))
print('\nbaza svi:', round(sum(OSN.values()) / len(OSN), 3))
