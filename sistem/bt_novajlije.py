# Minuti saigrača kad igra neko koga model nema (nov ili vraćen igrač sa manje od 2 ranije utakmice) i povlačenje ka sredini. Ništa ne upisuje. Upotreba: py -X utf8 bt_novajlije.py
# Rezultat 06.11.2026, kola 3-9: saigrači su precenjeni oko 1.3 min kad novi igraju 20+ min, ali umanjenje ne smanjuje grešku. Povlačenje ka proseku tima (0.2) smanjuje grešku minuta za 0.09, a poena povećava, pa nije ugrađeno.
# Igrači sa 2 ranije utakmice imaju podjednako tačne projekcije poena, pa ulaze u model (pripremi_kolo.py), ali ne i u preporuke (osvezi.py).
exec(open('bt_minuti2.py', encoding='utf8').read().split("def dopuna(")[0])
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
OSN = {u: abs(LOG[(u[0], u[1])][u[2]]['min'] - sad(*u)) for u in UZ}
def novi(t, R):
    """Igraju u kolu R, a imaju manje od 2 ranije utakmice za tim: (ime, ranije utakmice, procena minuta iz njih)."""
    out = []
    for m in EKIPA[t]:
        if R not in LOG[(m, t)]: continue
        h = [LOG[(m, t)][r]['min'] for r in LOG[(m, t)] if r < R]
        if len(h) < 2: out.append((m, len(h), sum(h) / len(h) if h else None))
    return out
# 1) da li su saigrači precenjeni kad igra novi igrač
print('Ostatak minuta (stvarno − model) modelovanih igrača, prema minutima novih igrača tog kola:')
gr = {'nema novih': [], 'novi 1-10 min': [], 'novi 10-20 min': [], 'novi 20+ min': []}
for u in UZ:
    s = sum(LOG[(m, u[1])][u[2]]['min'] for m, _, _ in novi(u[1], u[2]))
    k = 'nema novih' if s == 0 else 'novi 1-10 min' if s < 10 else 'novi 10-20 min' if s < 20 else 'novi 20+ min'
    gr[k].append(LOG[(u[0], u[1])][u[2]]['min'] - sad(*u))
for k, v in gr.items():
    if v: print(f'  {k:<16} n={len(v):>5}  ostatak {sum(v) / len(v):+.2f} min')
# 2) ispravka: saigrači se umanjuju srazmerno očekivanim minutima novih (samo onih sa bar 1 ranijom utakmicom, jer debitant nema procenu)
def v_novi(jac, sa_debitantima=0.0):
    def f(n, t, R):
        ig = igraju(t, R); S = sum(sad(m, t, R) for m in ig)
        e = sum(p if p is not None else sa_debitantima for _, k, p in novi(t, R))
        return sad(n, t, R) * (1 - jac * e / S) if S else sad(n, t, R)
    return f
# 3) povlačenje ka proseku tima (regresija ka sredini)
def v_sredina(a):
    def f(n, t, R):
        ig = igraju(t, R); sr = sum(sad(m, t, R) for m in ig) / len(ig)
        return sad(n, t, R) + a * (sr - sad(n, t, R))
    return f
def test(ime, fn, S=UZ):
    g = {}
    for u in S: g.setdefault(LOG[(u[0], u[1])][u[2]]['kod'], []).append(abs(LOG[(u[0], u[1])][u[2]]['min'] - fn(*u)) - OSN[u])
    m, lo, hi = boot(g)
    print(f"  {ime:<40} n={len(S):>5} greška {sum(OSN[u] for u in S) / len(S) + m:.3f}  razlika {m:+.3f} [{lo:+.3f},{hi:+.3f}]{'*' if lo > 0 or hi < 0 else ''}")
SA = [u for u in UZ if novi(u[1], u[2])]
print(f'\nbaza: greška {sum(OSN.values()) / len(OSN):.3f} min; tim-kola sa novim igračem: {len(SA)} redova')
for jac in (0.5, 0.75, 1.0):
    test(f'novi, jačina {jac}', v_novi(jac))
    test(f'novi, jačina {jac} (samo pogođeni)', v_novi(jac), SA)
for d in (6, 10):
    test(f'novi + debitant {d} min, jačina 1', v_novi(1.0, d), SA)
for a in (0.05, 0.1, 0.2):
    test(f'ka sredini tima {a}', v_sredina(a))
# 4) ostatak po projektovanim minutima (da li su visoki precenjeni, niski potcenjeni)
print('\nOstatak po projektovanim minutima:')
for lo, hi in ((0, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 45)):
    v = [LOG[(u[0], u[1])][u[2]]['min'] - sad(*u) for u in UZ if lo <= sad(*u) < hi]
    if v: print(f'  {lo:>2}-{hi:<2} n={len(v):>4} ostatak {sum(v) / len(v):+.2f}  |greška| {sum(map(abs, v)) / len(v):.2f}')
# 5) ostatak prema trendu (poslednja utakmica naspram proseka)
print('\nOstatak prema poslednjoj utakmici (posl − prosek):')
for lo, hi in ((-99, -8), (-8, -3), (-3, 3), (3, 8), (8, 99)):
    v = []
    for u in UZ:
        h = [r for r in LOG[(u[0], u[1])] if r < u[2]]; d = LOG[(u[0], u[1])][max(h)]['min'] - sad(*u)
        if lo <= d < hi: v.append(LOG[(u[0], u[1])][u[2]]['min'] - sad(*u))
    if v: print(f'  {lo:>3} do {hi:<3} n={len(v):>4} ostatak {sum(v) / len(v):+.2f}')
