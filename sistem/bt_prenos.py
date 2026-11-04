# Prenos minuta i učinka odsutnih na saigrače. Ništa ne upisuje. Upotreba: py -X utf8 bt_prenos.py
# Rezultat 04.11.2026, kola 3-9: veći prenos minuta (0.5 i više) povećava grešku, a lični prenos takođe. Asistencije po minutu rastu
# oko 15-30% kad ode organizator, ali interval obuhvata nulu (samo 9 slučajeva sa 25%+ izgubljenih asistencija). Ništa nije ugrađeno.
import os
exec(open('bt_minuti2.py', encoding='utf8').read().split("def dopuna(")[0])
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
OSN = {u: abs(LOG[(u[0], u[1])][u[2]]['min'] - sad(*u)) for u in UZ}

def udeo_sa(n, x, t, R):
    """Težinski deo n-ove istorije u kojoj je x igrao: ako x već dugo ne igra, n-ovi minuti to već sadrže."""
    h = [r for r in LOG[(n, t)] if r < R]
    w = {r: 0.9 ** (R - 1 - r) for r in h}
    return sum(w[r] for r in h if r in LOG[(x, t)]) / sum(w.values())

def prenos(s, cap, samo_novo=True, ista=True):
    kes = {}
    def f(n, t, R):
        k = (n, t, R)
        if k in kes: return kes[k]
        base = pros(n, t, R); b = 0.0; ig = igraju(t, R)
        for x in van(t, R, 10.0):
            if ista and grp(POS[(x, t)]) != grp(POS[(n, t)]): continue
            tot = sum(pros(m, t, R) for m in ig if not ista or grp(POS[(m, t)]) == grp(POS[(x, t)]))
            if tot: b += pros(x, t, R) * s * base / tot * (udeo_sa(n, x, t, R) if samo_novo else 1.0)
        kes[k] = base + min(cap, b)
        return kes[k]
    return f

def lican(k_sh, cap):
    """Lično: n-ovi minuti bez x minus sa x, skupljeno ka nuli po broju utakmica bez x."""
    kes = {}
    def f(n, t, R):
        k = (n, t, R)
        if k in kes: return kes[k]
        h = {r: v['min'] for r, v in LOG[(n, t)].items() if r < R}; b = 0.0
        for x in van(t, R, 10.0):
            sa = [m for r, m in h.items() if r in LOG[(x, t)]]; bez = [m for r, m in h.items() if r not in LOG[(x, t)]]
            if sa and bez: b += (sum(bez) / len(bez) - sum(sa) / len(sa)) * len(bez) / (len(bez) + k_sh)
        kes[k] = sad(n, t, R) + max(-cap, min(cap, b))
        return kes[k]
    return f

SV = [u for u in UZ if van(u[1], u[2], 10.0)]
NOV = [u for u in SV if any(udeo_sa(u[0], x, u[1], u[2]) > 0.7 and grp(POS[(x, u[1])]) == grp(POS[(u[0], u[1])]) for x in van(u[1], u[2], 10.0))]
print(f'uzorak svi {len(UZ)}, tim bez nekog {len(SV)}, nov izostanak iz iste grupe {len(NOV)}')
def red(ime, fn, S):
    g = {}
    for u in S: g.setdefault(LOG[(u[0], u[1])][u[2]]['kod'], []).append(abs(LOG[(u[0], u[1])][u[2]]['min'] - fn(*u)) - OSN[u])
    m, lo, hi = boot(g)
    return f"{m:+.3f}[{lo:+.3f},{hi:+.3f}]{'*' if lo > 0 or hi < 0 else ' '}"
print(f"\n{'MINUTI (minus = bolje od sadašnjeg)':<40}{'nov izostanak':<28}{'svi igrači':<28}")
VAR = {}
for s, cap in ((.3, 4), (.5, 4), (.5, 6), (.5, 8), (.7, 6), (.7, 8), (1.0, 8)):
    VAR[f'prenos {s} do +{cap}, samo novo'] = prenos(s, cap)
VAR['prenos .5 do +6, i staro'] = prenos(.5, 6, False)
VAR['prenos .5 do +6, svi u timu'] = prenos(.5, 6, True, False)
for ksh, cap in ((2, 4), (2, 8), (4, 8)):
    VAR[f'lično, skupljanje {ksh}, do {cap}'] = lican(ksh, cap)
for ime, fn in VAR.items(): print(f"{ime:<40}{red(ime, fn, NOV):<28}{red(ime, fn, UZ):<28}")

# Učinak po minutu: glavni izgubljeni organizator / strelac / skakač
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
def po_ut(x, t, R, k):
    h = [v[k] for r, v in LOG[(x, t)].items() if r < R]
    return sum(h) / len(h) if h else 0.0
def izgubljeno(n, t, R, k, ista=True):
    """Deo tima u statistici k koji odlazi sa odsutnima (nov izostanak), iz iste grupe."""
    ek = sum(po_ut(m, t, R, k) for m in igraju(t, R)); iz = 0.0
    for x in van(t, R, 10.0):
        if ista and grp(POS[(x, t)]) != grp(POS[(n, t)]): continue
        iz += po_ut(x, t, R, k) * udeo_sa(n, x, t, R)
    return iz / (ek + iz) if ek + iz else 0.0
print('\nUČINAK PO MINUTU kad ode organizator/strelac/skakač iz iste grupe')
print('uzorak: igrač koji igra 15+ min, izgubljeno bar 15% tima u toj statistici; odnos = stvarno po minutu / procena po minutu')
for k in K3:
    S = [u for u in UZ if izgubljeno(*u, k) >= .15 and sad(*u) >= 15]
    pr = st = 0.0; mn = 0.0
    for u in S:
        p = proj(*u, SVE[u[2]], PUNI)[k][0]; b = pros(*u); a = LOG[(u[0], u[1])][u[2]]
        pr += p / b * a['min']; st += a[k]; mn += a['min']
    print(f'  {k}: n={len(S)} stvarno {st / max(1, len(S)):.2f} procena za iste minute {pr / max(1, len(S)):.2f} odnos {st / max(pr, 1e-9):.3f}')
    for a_ in (.25, .5, 1.0):
        g = {}
        for u in UZ:
            iz = izgubljeno(*u, k)
            if iz <= 0 or sad(*u) < 10: continue
            p = proj(*u, SVE[u[2]], PUNI)[k][0]; a = LOG[(u[0], u[1])][u[2]]
            g.setdefault(a['kod'], []).append(abs(a[k] - p * (1 + a_ * iz)) - abs(a[k] - p))
        if g:
            m, lo, hi = boot(g); print(f"     pojačanje {a_} × izgubljeni deo: {m:+.3f} [{lo:+.3f},{hi:+.3f}]{'*' if lo > 0 or hi < 0 else ''} (n={sum(map(len, g.values()))})")
# Uticaj na učinak najboljeg prenosa minuta
print('\nUČINAK kad se primene minuti iz varijante (nov izostanak, minus = bolje)')
for ime in ('prenos 0.5 do +6, samo novo', 'prenos 0.7 do +8, samo novo', 'lično, skupljanje 2, do 8'):
    fn = VAR[ime]; red_ = f'{ime:<34}'
    for k in K3:
        g = {}
        for u in NOV:
            p = proj(*u, SVE[u[2]], PUNI)[k][0]; b = pros(*u); a = LOG[(u[0], u[1])][u[2]]
            if not b: continue
            g.setdefault(a['kod'], []).append(abs(a[k] - p * fn(*u) / b) - abs(a[k] - p * sad(*u) / b))
        m, lo, hi = boot(g); red_ += f" {k} {m:+.3f}[{lo:+.3f},{hi:+.3f}]{'*' if lo > 0 or hi < 0 else ''}"
    print(red_)
