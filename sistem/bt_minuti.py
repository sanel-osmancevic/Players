# Provera modela minuta "vraćanjem vremena" (kola 3 i dalje). Ko je van znamo iz samog kola: igrač sa 15+ minuta prosečno koji tog kola nije igrao.
# To je približno izveštaju o povredama, ali malo optimistično, jer uključuje i odluke trenera. Ništa ne upisuje. Upotreba: py -X utf8 bt_minuti.py
import random, sys
exec(open('bt_faktori.py', encoding='utf8').read().split('SVE = {R')[0])
STV = {(n, t): h for (n, t), h in LOG.items()}
EKIPA = {}
for (n, t) in LOG: EKIPA.setdefault(t, []).append(n)
KOLA_TIMA = {}
for (t, r) in TEAM_R: KOLA_TIMA.setdefault(t, set()).add(r)

def pros(n, t, R, dec=0.9):
    h = {r: v for r, v in LOG[(n, t)].items() if r < R}
    if not h: return None
    rr = sorted(h); w = [dec ** (R - 1 - r) for r in rr]
    return sum(a * h[r]['min'] for a, r in zip(w, rr)) / sum(w)

def van(t, R, prag=15.0):
    """Ključni igrači tima koji nisu igrali kolo R (i igrali su bar 2 puta ranije)."""
    out = []
    for n in EKIPA[t]:
        h = {r: v for r, v in LOG[(n, t)].items() if r < R}
        if len(h) >= 2 and R not in LOG[(n, t)] and sum(v['min'] for v in h.values()) / len(h) >= prag: out.append(n)
    return out
def kljucni(t, R, prag=15.0):
    out = []
    for n in EKIPA[t]:
        h = {r: v for r, v in LOG[(n, t)].items() if r < R}
        if len(h) >= 2 and sum(v['min'] for v in h.values()) / len(h) >= prag: out.append(n)
    return out

# --- varijante; svaka vraća minute za (n, t, R)
def v_osnovno(n, t, R): return pros(n, t, R, 0.9)
def v_dec(d): return lambda n, t, R: pros(n, t, R, d)
def v_posl(k, tez):
    def f(n, t, R):
        rr = sorted(r for r in LOG[(n, t)] if r < R)[-k:]
        return tez * sum(LOG[(n, t)][r]['min'] for r in rr) / len(rr) + (1 - tez) * pros(n, t, R, 1.0)
    return f
def v_sastav(mis=0.5, shr=0.5, cap_abs=7.0, cap_rel=0.30):
    """Kao dostupnost.py: kola sa drugačijim sastavom dobijaju manju težinu."""
    def f(n, t, R):
        base = pros(n, t, R); h = {r: v for r, v in LOG[(n, t)].items() if r < R}
        ostali = [j for j in kljucni(t, R) if j != n]
        sada = {j: R in LOG[(j, t)] for j in ostali}
        # samo igrači čije se prisustvo menjalo ili su sada van
        kola = {r for r in KOLA_TIMA[t] if r < R}
        kr = {j: sada[j] for j in ostali if not sada[j] or any(r not in LOG[(j, t)] for r in kola if r >= R - 3)}
        num = den = 0.0
        for r, v in h.items():
            w = 0.9 ** (R - 1 - r)
            for j, igra in kr.items():
                if (r in LOG[(j, t)]) != igra: w *= mis
            num += w * v['min']; den += w
        novi = base + shr * (num / den - base)
        novi = max(base - cap_abs, min(base + cap_abs, novi)); return max(base * (1 - cap_rel), min(base * (1 + cap_rel), novi))
    return f
def v_bonus(n, t, R):
    """Kao build5.py: minuti odsutnog se dele saigračima iste grupe (najviše +4)."""
    base = pros(n, t, R); grp = lambda p: 'G' if p == 'G' else 'FC'; b = 0.0
    igraju = [m for m in EKIPA[t] if R in LOG[(m, t)] and sum(1 for r in LOG[(m, t)] if r < R) >= 2]
    for x in van(t, R, 10.0):
        if grp(POS[(x, t)]) != grp(POS[(n, t)]): continue
        tot = sum(pros(m, t, R) for m in igraju if grp(POS[(m, t)]) == grp(POS[(x, t)]))
        if tot: b = min(4.0, b + pros(x, t, R) * 0.7 * base / tot)
    return base + b
def v_tim(baza, cilj=200.0, lo=0.85, hi=1.20, jacina=1.0):
    """Zbir minuta tima mora da bude oko 200: projekcije se srazmerno skaliraju, uz poznate odsutne."""
    def f(n, t, R):
        ig = [m for m in EKIPA[t] if R in LOG[(m, t)] and sum(1 for r in LOG[(m, t)] if r < R) >= 2]
        mn = [m for m in EKIPA[t] if R in LOG[(m, t)] and sum(1 for r in LOG[(m, t)] if r < R) < 2]
        s = sum(baza(m, t, R) for m in ig) + 8.0 * len(mn)   # nov igrač bez istorije: oko 8 min
        fk = max(lo, min(hi, cilj / s)) if s else 1.0
        return baza(n, t, R) * (1 + jacina * (fk - 1))
    return f
_kes = {}
def memo(ime, fn):
    def f(n, t, R):
        k = (ime, n, t, R)
        if k not in _kes: _kes[k] = fn(n, t, R)
        return _kes[k]
    return f
V = {
 'osnovno (zaborav 0.9)': memo('o', v_osnovno),
 'zaborav 0.8': memo('d8', v_dec(0.8)), 'zaborav 0.7': memo('d7', v_dec(0.7)),
 'posl. 3 + sezona 50/50': memo('p3', v_posl(3, 0.5)), 'posl. 5 + sezona 50/50': memo('p5', v_posl(5, 0.5)),
 'sastav (sadašnji)': memo('s', v_sastav()), 'sastav jači (mis .3, shr 1)': memo('s2', v_sastav(0.3, 1.0)),
 'dodatak odsutnih (build5)': memo('b', v_bonus),
 'zbir tima = 200': None, 'zbir + sastav': None, 'zbir pola jačine': None,
}
V['zbir tima = 200'] = memo('t', v_tim(V['osnovno (zaborav 0.9)']))
V['zbir + sastav'] = memo('ts', v_tim(V['sastav (sadašnji)']))
V['zbir pola jačine'] = memo('th', v_tim(V['osnovno (zaborav 0.9)'], jacina=0.5))
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
OSN = {u: abs(LOG[(u[0], u[1])][u[2]]['min'] - V['osnovno (zaborav 0.9)'](*u)) for u in UZ}
def boot(gr):
    g = list(gr.values()); rng = random.Random(7); m = sum(map(sum, g)) / sum(map(len, g)); b = []
    for _ in range(1500):
        u = [g[rng.randrange(len(g))] for _ in g]; b.append(sum(map(sum, u)) / sum(map(len, u)))
    b.sort(); return m, b[37], b[1462]
SA_VAN = [u for u in UZ if van(u[1], u[2])]
print(f'Uzorak {len(UZ)} igrač-utakmica; od toga {len(SA_VAN)} kad timu fali ključni igrač\n')
print(f"{'varijanta':<30}{'greška':>8}{'razlika':>9} {'95% interval':<18}{'kola 8-9':>9}{'kad fali igrač':>16}")
for ime, fn in V.items():
    gr = {}; e8 = []; e0 = []; ev = []; e0v = []
    for u in UZ:
        a = LOG[(u[0], u[1])][u[2]]; x = abs(a['min'] - fn(*u)); gr.setdefault(a['kod'], []).append(x - OSN[u])
        if u[2] >= 8: e8.append(x - OSN[u])
    for u in SA_VAN: ev.append(abs(LOG[(u[0], u[1])][u[2]]['min'] - fn(*u)) - OSN[u])
    m, lo, hi = boot(gr); z = '*' if lo > 0 or hi < 0 else ' '
    print(f"{ime:<30}{sum(OSN.values()) / len(OSN) + m:>8.3f}{m:>+9.3f} [{lo:+.3f},{hi:+.3f}]{z} {sum(e8) / len(e8):>+8.3f}{sum(ev) / len(ev):>+16.3f}")
print('\nminus = manja greška od osnovnog; * = interval ne obuhvata nulu')
# isti izbor preko projekcije učinka: rate iz build5, minuti iz varijante
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
print('\nEfekat na učinak (greška poena/skokova/asistencija, minuti iz varijante):')
def uc(fn, ime):
    e = {k: {} for k in K3}; s = {k: 0 for k in K3}
    for u in UZ:
        p = proj(*u, SVE[u[2]], PUNI); a = LOG[(u[0], u[1])][u[2]]; b = pros(u[0], u[1], u[2]); m = fn(*u)
        for k in K3:
            er = abs(a[k] - p[k][0] * (m / b if b else 1)); er0 = abs(a[k] - p[k][0])
            s[k] += er; e[k].setdefault(a['kod'], []).append(er - er0)
    print(f'{ime:<30}' + ''.join(f"{k} {s[k] / len(UZ):.3f} ({boot(e[k])[0]:+.3f}{'*' if boot(e[k])[1] > 0 or boot(e[k])[2] < 0 else ''})   " for k in K3))
for ime in ('osnovno (zaborav 0.9)', 'sastav (sadašnji)', 'dodatak odsutnih (build5)', 'zbir tima = 200', 'zbir + sastav', 'zbir pola jačine'): uc(V[ime], ime)
