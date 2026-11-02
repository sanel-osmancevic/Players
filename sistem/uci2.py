# Tačka 6: učenje iz rezultata. Iz evidencije sa rezultatima uči:
#  - pomeraj projekcije po kategoriji (sistematska greška),
#  - širinu raspodele (množilac sd),
#  - raspodelu (normalna ili negativna binomna),
#  - težine za šansu: model / istorija sezone / tržište.
# Sve se skuplja ka podrazumevanim vrednostima dok je uzorak mali (efektivno n = broj različitih igrač-kategorija).
# Piše tezine.json koji primenjuje tezine_primeni.py.
import json, math, os
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from dist import p_over as nb_over
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
K = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}
DEF = dict(bias={'pts': 0.0, 'reb': 0.0, 'ast': 0.0}, c=1.0, raspodela='normal', w=[1/3, 1/3, 1/3])
PRIOR_N = 300  # koliko "efektivnih" primera vredi podrazumevano podešavanje

ev = [e for e in citaj('evidencija.json') if e.get('proslo_vise') in (True, False) and e.get('rezultat') is not None]
eff = {}
for e in ev: eff.setdefault(e['kategorija'], set()).add((e['kolo'], e['igrac']))
n_eff = {k: len(v) for k, v in eff.items()}
N = sum(n_eff.values())

def p_model(e, bias=0.0, c=1.0, dist='normal'):
    mu = e['proj'] + bias; sd = e['sd'] * c
    if dist == 'nb': return nb_over(e['linija'], max(mu, 0.1), sd)
    return 1 - Phi((math.floor(e['linija']) + 0.5 - mu) / sd)
def p_hist(e, side='v'):
    h, n = map(int, e['ist_vise'].split('/'))
    return (h + 1) / (n + 2)
def logloss(ps, ys):
    return sum(-(y * math.log(min(max(p, .01), .99)) + (1 - y) * math.log(1 - min(max(p, .01), .99))) for p, y in zip(ps, ys)) / len(ys)

out = dict(DEF); out['n'] = N; out['n_po_kategoriji'] = n_eff; out['dijagnostika'] = {}
if N:
    ys = [1 if e['proslo_vise'] else 0 for e in ev]
    # 1) pomeraj po kategoriji: prosečna greška, skupljena ka 0
    bias = {}
    for kat, k in K.items():
        d = [e['rezultat'] - e['proj'] for e in ev if e['kategorija'] == kat]
        if d:
            lam = n_eff[kat] / (n_eff[kat] + PRIOR_N / 3)
            bias[k] = round(lam * sum(d) / len(d), 2)
        else: bias[k] = 0.0
    # 2) širina i raspodela (sa naučenim pomerajem)
    best = None
    for dist in ('normal', 'nb'):
        for c in (0.8, 0.9, 1.0, 1.1, 1.2, 1.3):
            ps = [p_model(e, bias[K[e['kategorija']]], c, dist) for e in ev]
            l = logloss(ps, ys)
            if best is None or l < best[0]: best = (l, dist, c)
    lam = N / (N + PRIOR_N)
    c = round(1 + lam * (best[2] - 1), 3)
    # raspodela se menja samo ako je bolja i uzorak dovoljan
    l_norm = logloss([p_model(e, bias[K[e['kategorija']]], best[2], 'normal') for e in ev], ys)
    l_nb = logloss([p_model(e, bias[K[e['kategorija']]], best[2], 'nb') for e in ev], ys)
    dist = 'nb' if (l_nb < l_norm - 0.005 and N >= 200) else 'normal'
    # 3) težine model / istorija / tržište
    have_t = [e for e in ev if e.get('trz_vise') is not None]
    grid = []
    for wm in [i / 10 for i in range(11)]:
        for wt in ([i / 10 for i in range(0, 11 - int(wm * 10))] if have_t else [0.0]):
            wh = round(1 - wm - wt, 2)
            if wh < 0: continue
            sub = have_t if have_t else ev
            ps = [wm * p_model(e, bias[K[e['kategorija']]], c, dist) + wh * p_hist(e) + wt * (e.get('trz_vise') or 0) for e in sub]
            grid.append((logloss(ps, [1 if e['proslo_vise'] else 0 for e in sub]), wm, wh, wt))
    l, wm, wh, wt = min(grid)
    nw = len({(e['kolo'], e['igrac'], e['kategorija']) for e in (have_t or ev)})
    lam_w = nw / (nw + PRIOR_N)
    w0 = DEF['w'] if have_t else [0.5, 0.5, 0.0]
    w = [w0[0] + lam_w * (wm - w0[0]), w0[1] + lam_w * (wh - w0[1]), w0[2] + lam_w * (wt - w0[2])]
    if not have_t: w = [w[0] * 2 / 3 / (w[0] + w[1]) * (w[0] + w[1]), w[1], w[2]]
    out.update(bias=bias, c=c, raspodela=dist, w_naucene_bez_trzista=None if have_t else [wm, wh])
    # težine: dok tržište nema rezultata, model/istorija odnos se uči, a tržište zadržava trećinu
    if not have_t:
        m_share = 0.5 + lam_w * (wm - 0.5)
        out['w'] = [round(2 / 3 * m_share, 3), round(2 / 3 * (1 - m_share), 3), round(1 / 3, 3)]
    else:
        out['w'] = [round(x, 3) for x in w]
    out['dijagnostika'] = dict(logloss_normal=round(l_norm, 4), logloss_nb=round(l_nb, 4), najbolja_sirina=best[2],
                               tezine_sirovo=dict(model=wm, istorija=wh, trziste=wt), n_tezine=nw)
# 4) težina prošle sezone u istoriji linije (skuplja se ka 0,2 dok nema dovoljno primera)
W_LS0 = 0.2
ls_rows = [e for e in ev if e.get('ls_n')]
out['w_ls'] = W_LS0
if ls_rows:
    def ph_ls(e, w):
        h, n = map(int, e['ist_vise'].split('/'))
        return (h + w * e['ls_vise'] + 1) / (n + w * e['ls_n'] + 2)
    ys2 = [1 if e['proslo_vise'] else 0 for e in ls_rows]
    best_w = min((logloss([ph_ls(e, w) for e in ls_rows], ys2), w) for w in (0, 0.1, 0.2, 0.3, 0.5, 0.8))[1]
    nls = len({(e['kolo'], e['igrac'], e['kategorija']) for e in ls_rows})
    lam = nls / (nls + PRIOR_N)
    out['w_ls'] = round(W_LS0 + lam * (best_w - W_LS0), 3)
    out['dijagnostika']['w_ls_sirovo'] = best_w; out['dijagnostika']['n_ls'] = nls
pisi(out, 'tezine.json', ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
