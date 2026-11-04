# Prenos minuta odsutnog po ulozi: tri pravila prema sadašnjem (0.3 do +2 po grupi). Ništa ne upisuje. Upotreba: py -X utf8 bt_uloga.py
# A: starter ide na prvu rezervu i startere iz grupe, rezerva na rezerve iz grupe. B: po mestu u rotaciji (sledeća tri ispod odsutnog).
# Rezultat 04.11.2026, kola 3-9 (9 varijanti, 850 redova): samo C 0.3 do +4 smanjuje grešku sa intervalom bez nule, za oko 0.05 min (3 sekunde), a učinak se praktično ne menja. Nije ugrađeno.
# C: po izmenama iz ranijih utakmica (ko ulazi umesto odsutnog ili on umesto njega).
import unicodedata, re, math
exec(open('bt_minuti2.py', encoding='utf8').read().split("def dopuna(")[0])
UZ = [(n, t, R) for (n, t), h in LOG.items() for R in h if R >= 3 and sum(1 for r in h if r < R) >= 2]
OSN = {u: abs(LOG[(u[0], u[1])][u[2]]['min'] - sad(*u)) for u in UZ}
def udeo_sa(n, x, t, R):
    h = [r for r in LOG[(n, t)] if r < R]; w = {r: 0.9 ** (R - 1 - r) for r in h}
    return sum(w[r] for r in h if r in LOG[(x, t)]) / sum(w.values())
# starteri po utakmici
ST = {}
for g in G:
    for st, t in (('local', g.get('h')), ('road', g.get('a'))):
        for pl in g['s'][st]['players']:
            if pl['stats'].get('startFive'): ST.setdefault((pl['player']['person']['name'], t), set()).add(g['kolo'])
print('startera upisano', sum(map(len, ST.values())), 'na utakmica', len(G))
def starter(n, t, R):
    h = [r for r in LOG[(n, t)] if r < R]
    return bool(h) and sum(r in ST.get((n, t), ()) for r in h) * 2 > len(h)
# parovi izmena: (ko izlazi, ko ulazi, kolo)
IZM = {}
for g in G:
    d = citaj(f"api_kes/b{g['kod']}.json")
    for q in ('FirstQuarter', 'SecondQuarter', 'ThirdQuarter', 'ForthQuarter', 'ExtraTime'):
        tren = {}
        for e in d.get(q) or []:
            if e.get('PLAYTYPE') in ('IN', 'OUT'): tren.setdefault((e['CODETEAM'], e['MINUTE'], e['MARKERTIME']), {'IN': [], 'OUT': []})[e['PLAYTYPE']].append(e['PLAYER'].strip())
        for z in tren.values():
            for o in z['OUT']:
                for i in z['IN']: IZM.setdefault((o, i), []).append(g['kolo'])
def t_a(n, x, t, R, ig):
    g = grp(POS[(x, t)]); iste = [m for m in ig if grp(POS[(m, t)]) == g]
    klupa = sorted((m for m in iste if not starter(m, t, R)), key=lambda m: -pros(m, t, R)); pet = [m for m in iste if starter(m, t, R)]
    if starter(x, t, R):
        w = {}
        if klupa: w[klupa[0]] = .6
        for m in pet: w[m] = w.get(m, 0) + .4 / len(pet)
    else: w = {m: 1 / len(klupa) for m in klupa}
    return w.get(n, 0.0) / (sum(w.values()) or 1)
def t_b(n, x, t, R, ig):
    r = sorted(ig + [x], key=lambda m: -pros(m, t, R)); i = r.index(x); nize = r[i + 1:i + 4] or r[max(0, i - 3):i]
    w = dict(zip(nize, (3, 2, 1))); return w.get(n, 0) / (sum(w.values()) or 1)
def t_c(n, x, t, R, ig):
    br = {m: sum(r < R for r in IZM.get((x, m), [])) + sum(r < R for r in IZM.get((m, x), [])) for m in ig}
    return br.get(n, 0) / (sum(br.values()) or 1)
PR = {'A starter/rezerva': t_a, 'B rotacija': t_b, 'C izmene': t_c}
def pravilo(tez, s, cap):
    kes = {}
    def f(n, t, R):
        k = (n, t, R)
        if k not in kes:
            ig = igraju(t, R); b = 0.0
            for x in van(t, R, 10.0):
                if n in ig: b += pros(x, t, R) * s * udeo_sa(n, x, t, R) * tez(n, x, t, R, ig)
            kes[k] = pros(n, t, R) + min(cap, b)
        return kes[k]
    return f
SV = [u for u in UZ if van(u[1], u[2], 10.0)]
NOV = [u for u in SV if any(udeo_sa(u[0], x, u[1], u[2]) > 0.7 for x in van(u[1], u[2], 10.0))]
print(f'uzorak: svi {len(UZ)}, tim bez nekog {len(SV)}, nov izostanak {len(NOV)}')
print('zbir minuta sadašnje', round(sum(sum(sad(m, t, R) for m in igraju(t, R)) for t, R in sorted({u[1:] for u in UZ})) / len({u[1:] for u in UZ}), 1))
def raz(fn, S, greska=None):
    g = {}
    for u in S:
        a = LOG[(u[0], u[1])][u[2]]; g.setdefault(a['kod'], []).append(abs(a['min'] - fn(*u)) - OSN[u])
    if not g: return 'nema'
    m, lo, hi = boot(g); return f"{m:+.3f}[{lo:+.3f},{hi:+.3f}]{'*' if lo > 0 or hi < 0 else ' '}"
SVE = {R: pre_kola(R) for R in KOLA if R >= 3}
def ucinak(fn, k, S):
    g = {}
    for u in S:
        p = proj(*u, SVE[u[2]], PUNI)[k][0]; b = sad(*u); o = pros(*u); a = LOG[(u[0], u[1])][u[2]]
        if not o: continue
        mu = p * b / o; g.setdefault(a['kod'], []).append(abs(a[k] - mu * fn(*u) / b) - abs(a[k] - mu))
    m, lo, hi = boot(g); return f"{m:+.3f}[{lo:+.3f},{hi:+.3f}]{'*' if lo > 0 or hi < 0 else ''}"
VAR = {f'{i} {s} do +{c}': pravilo(t, s, c) for i, t in PR.items() for s, c in ((.3, 2), (.3, 4), (.5, 6))}
print(f"\nMINUTI, minus = bolje od sadašnjeg\n{'varijanta':<28}{'nov izostanak':<26}{'kola 3-6':<26}{'kola 7-9':<26}{'svi':<26}")
for i, f in VAR.items():
    print(f"{i:<28}{raz(f, NOV):<26}{raz(f, [u for u in NOV if u[2] <= 6]):<26}{raz(f, [u for u in NOV if u[2] > 6]):<26}{raz(f, UZ):<26}")
print('\nUČINAK na novim izostancima (minus = bolje)')
for i, f in VAR.items(): print(f'{i:<28}', *[f'{k} {ucinak(f, k, NOV)}' for k in K3])
# 9. kolo na Maxbet linijama
def kl(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower().replace("'", '')
    n = re.sub(r'\b(iv|iii|jr)\b', '', n); n = re.sub(r'\b[a-z]\b', '', n); return re.sub(r'[^a-z]', '', n)
IM = {}
for (n, t) in LOG:
    l, f = n.split(', ', 1) if ', ' in n else (n, ''); IM[kl(f + ' ' + l)] = (n, t)
E = [e for e in citaj('evidencija.json') if e['kolo'] == 9 and e.get('proslo_vise') in (True, False) and e.get('rezultat') is not None and e.get('trz_vise') is not None and e.get('kvota_manje') and e.get('kvota_vise') and kl(e['igrac']) in IM and 9 in LOG[IM[kl(e['igrac'])]]]
Phi = lambda z: .5 * (1 + math.erf(z / math.sqrt(2)))
def ll(rows, fn=None):
    Lm = Lb = 0.0
    for e in rows:
        n, t = IM[kl(e['igrac'])]; mu = e['proj'] * (fn(n, t, 9) / sad(n, t, 9) if fn else 1)
        pm = 1 - Phi((math.floor(e['linija']) + .5 - mu) / e['sd']); h, c = map(int, e['ist_vise'].split('/'))
        pb = .216 * pm + .184 * (h + 1) / (c + 2) + .6 * e['trz_vise']; y = 1 if e['proslo_vise'] else 0
        for v in (pm,):
            v = min(max(v, .01), .99); Lm += -(y * math.log(v) + (1 - y) * math.log(1 - v))
        pb = min(max(pb, .01), .99); Lb += -(y * math.log(pb) + (1 - y) * math.log(1 - pb))
    return Lm / max(1, len(rows)), Lb / max(1, len(rows))
print(f'\n9. KOLO NA LINIJAMA (svih {len(E)}): sadašnje model/spoj {ll(E)[0]:.4f}/{ll(E)[1]:.4f}')
for i, f in VAR.items():
    A = [e for e in E if abs(f(*IM[kl(e['igrac'])], 9) - sad(*IM[kl(e['igrac'])], 9)) > .3]
    if A: print(f'{i:<28} svi {ll(E, f)[0]:.4f}/{ll(E, f)[1]:.4f}  menja se {len(A)} redova: sada {ll(A)[0]:.4f}/{ll(A)[1]:.4f} novo {ll(A, f)[0]:.4f}/{ll(A, f)[1]:.4f}')
