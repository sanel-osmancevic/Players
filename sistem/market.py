# Tržišna procena iz glavnih linija tri kladionice (Maxbet, Soccer, Merkur).
# Za svaku kladionicu: verovatnoća bez marže na njenoj glavnoj liniji -> implicirana medijana
# (normalna raspodela sa sd iz modela). Prosek medijana = konsenzus tržišta.
# Upisuje u kvote_pet.json i kvote.json polje trz_vise (verovatnoća da linija prođe na više po tržištu).
import json, math, re, unicodedata, sys, glob, os
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from statistics import NormalDist
from datetime import datetime as _dt
from kolo import KOLO, OD, DAN, ALIAS, tim
N = NormalDist()

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z]', '', s)

SUF = {'iv', 'iii', 'ii', 'jr', 'jr.', 'sr'}
def surname_full(name):
    t = [w for w in name.replace('.', '. ').split() if w.lower().strip('.') not in SUF]
    return norm(t[-1]) if t else ''
def surname_merkur(name):
    t = name.split()
    return norm(' '.join(t[:-1]) if len(t) > 1 else t[0])

CAT = {'P': 'Poeni', 'S': 'Skokovi', 'A': 'Asistencije'}
KEY = {'Poeni': 'pts', 'Skokovi': 'reb', 'Asistencije': 'ast'}

def glavne_mb(raw):   # Maxbet snimak servisa ima sve linije: za konsenzus se uzima prva dvostrana po igraču i kategoriji
    out = {}
    for k, ls in raw.items():
        d = out.setdefault(k, {})
        for l in ls:
            if len(l) == 4 and l[2] and l[3] and l[0] not in d: d[l[0]] = [l[1], l[2], l[3]]
    return out

def snaps(prefix):
    # ručni snimci (books/) i snimci servisa (prikupljeno/DATUM/, bez foldera sumnjivo); snimci iz prošlih kola se ne računaju
    po_vremenu = {}
    for f in glob.glob(f'books/{prefix}_*.json') + glob.glob(f'prikupljeno/*/{prefix}_*.json'):
        s = citaj(f)
        if 'out' not in s: s = dict(t=s['t'], out=glavne_mb(s.get('raw') or {}))
        if s['out'] and s['t'].replace('Z', '') >= OD.replace('Z', ''): po_vremenu[s['t']] = s
    return [po_vremenu[t] for t in sorted(po_vremenu)]

def surname_md(name):   # Meridian "da Silva, Tristan", "Carter Jr., Wendell"
    return surname_full(name.split(',')[0])
def index(snap, kind):
    out = {}
    for k, d in snap['out'].items():
        n, t = k.split('|')
        if kind == 'meridian':
            sn = surname_md(n)
            g = norm(t)
            kand = {r['tim'] for i, r in ig.items() if surname_full(i) == sn and any(a in g for a in ALIAS.get(r['tim'], [norm(r['tim'])]))}
            if len(kand) == 1: out[(sn, kand.pop())] = d
            continue
        sn = surname_merkur(n) if kind == 'merkur' else surname_full(n)
        if tim(t): out[(sn, tim(t))] = d
    return out

ig = {r['igrac']: r for r in citaj('igraci2.json') if r['termin'].startswith(DAN)}
# istorija snimaka po kladionici: lista (vreme, indeks)
HIST = {'maxbet': [(s['t'], index(s, 'maxbet')) for s in snaps('mb')],
        'soccer': [(s['t'], index(s, 'soccer')) for s in snaps('sb')],
        'merkur': [(s['t'], index(s, 'merkur')) for s in snaps('mk')],
        'meridian': [(s['t'], index(s, 'meridian')) for s in snaps('md')]}
# težine u konsenzusu: Soccer deli izvor kvota sa Maxbetom pa vredi pola; ostali su nezavisni (uče se iz rezultata)
TEZ_K = {'soccer': 0.5, 'merkur': 1.0, 'meridian': 1.0}
if os.path.exists('tezine_kladionica.json'): TEZ_K.update(citaj('tezine_kladionica.json'))
# kladionica čiji je poslednji snimak stariji 6 h od najnovijeg ne ulazi u konsenzus (zastarele kvote bi dale lažan ⚡)
_t = lambda s: _dt.fromisoformat(s.replace('Z', '+00:00')).timestamp()
_najnoviji = max((_t(h[-1][0]) for h in HIST.values() if h), default=0)
books = {b: h[-1][1] for b, h in HIST.items() if h and _najnoviji - _t(h[-1][0]) <= 6 * 3600}


def median_from(L, ov, un, sd):
    po = (1 / ov) / (1 / ov + 1 / un)
    po = min(max(po, 0.03), 0.97)
    return math.floor(L) + 0.5 + sd * N.inv_cdf(po)

def mu_of(idx, key, c, sd):
    d = idx.get(key, {}).get(c)
    return median_from(d[0], d[1], d[2], sd) if d else None

def market(igrac, tim, kat):
    """Konsenzus = težinski prosek Soccera (pola težine, isti izvor kao Maxbet) i nezavisnih kladionica.
    Maxbet ulazi samo kad nema nijedne nezavisne. Vraća medijanu, sd, medijane po kladionici,
    kretanje konsenzusa od prvog snimka i odstupanje Maxbeta od konsenzusa."""
    r = ig.get(igrac)
    if not r: return None
    sd = float(r[KEY[kat] + '_sd']); c = [x for x, v in CAT.items() if v == kat][0]
    key = (surname_full(igrac), tim)
    now = {b: mu_of(books[b], key, c, sd) for b in books}
    now = {b: v for b, v in now.items() if v is not None}
    nez = [b for b in TEZ_K if b in now and TEZ_K[b] > 0]
    if nez == ['soccer']: nez = []   # Soccer deli izvor sa Maxbetom i često ga prati sa zakašnjenjem, pa sam ne vredi kao tržište
    src = [now[b] for b in nez] or ([now['maxbet']] if 'maxbet' in now else [])
    if not src: return None
    mu = sum(now[b] * TEZ_K[b] for b in nez) / sum(TEZ_K[b] for b in nez) if nez else src[0]
    # kretanje: pomeranje medijane od prvog do poslednjeg snimka, po kladionici, sa težinom = dužina istorije u minutima
    from datetime import datetime
    ts = lambda t: datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp() / 60
    num = den = 0.0
    for b, h in HIST.items():
        pts = [(ts(t), mu_of(ix, key, c, sd)) for t, ix in h]
        pts = [x for x in pts if x[1] is not None]
        if len(pts) < 2: continue
        span = pts[-1][0] - pts[0][0]
        if span <= 0: continue
        num += (pts[-1][1] - pts[0][1]) * span; den += span
    kret = num / den if den else 0.0
    pravi = [b for b in nez if b != 'soccer']   # ⚡: Maxbet prema kladionicama sa drugim izvorom
    odst = now['maxbet'] - sum(now[b] * TEZ_K[b] for b in pravi) / sum(TEZ_K[b] for b in pravi) if 'maxbet' in now and pravi else 0.0
    return mu, sd, now, kret, odst

def apply(fn):
    rows = citaj(fn); n = 0
    for x in rows:
        if x.get('kolo') != KOLO or x.get('igrac') not in ig: continue
        m = market(x['igrac'], x['tim'], x['kategorija'])
        if not m: continue
        mu, sd, mus, kret, odst = m
        L = float(x['linija'])
        x['trz_vise'] = round(1 - N.cdf((math.floor(L) + 0.5 - mu) / sd), 3)
        x['trz_medijana'] = round(mu, 2); x['trz_knjige'] = len(mus)
        # raskorak = razlika najviše i najniže procene među kladionicama bez Maxbeta (treba bar 2); velik raskorak = tržište nije sigurno
        nz = [v for b, v in mus.items() if b != 'maxbet']
        x['trz_raskorak'] = round(max(nz) - min(nz), 2) if len(nz) >= 2 else None
        x['trz_knjige_nez'] = len(nz)
        x['trz_kretanje'] = round(kret, 2); x['mb_odstupanje'] = round(odst, 2)
        n += 1
    pisi(rows, fn, ensure_ascii=False)
    return n

if __name__ == '__main__':
    print('kvote_pet', apply('kvote_pet.json'), 'kvote', apply('kvote.json'))
    cov = {b: len(m) for b, m in books.items()}; print('igrača po kladionici', cov)
    print('snimci', {b: [t[11:16] for t, _ in h] for b, h in HIST.items()})
    keys = {(surname_full(i), r['tim']) for i, r in ig.items()}
    for b, m in books.items():
        miss = [k for k in m if k not in keys]
        if miss: print('nepovezano', b, miss[:10])
