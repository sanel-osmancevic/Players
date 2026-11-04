# Da li ukupan broj poena i hendikep iz kvota pomažu projekcijama poena?
# Samo 9. kolo: jedino ima sačuvane kvote utakmica i rezultate, pa je ovo gruba provera. Ništa ne upisuje.
import json, random, subprocess, statistics as st
from statistics import NormalDist
A = {}
for l in open('arhiva/kolo9_ponuda.jsonl', encoding='utf8'):
    r = json.loads(l)
    if r.get('igrac'): A[r['igrac']] = r   # poslednji zapis pred meč
R = json.load(open('arhiva/kolo9_rezultati.json', encoding='utf8'))
R = {k: v for k, v in R.items() if isinstance(v, dict) and 'ime' in v}
n_ime = lambda s: ''.join(str(s).upper().split())
RI = {n_ime(k.split('|')[0]): v for k, v in R.items()}
SVI = json.loads(subprocess.run(['git', 'show', 'feb93b0:./igraci2.json'], capture_output=True).stdout.decode('utf8'))
SVI = [r for r in SVI if int(r.get('kolo') or 0) == 9] or SVI
print('ceo sastav iz git-a: kolo', {r.get('kolo') for r in SVI}, 'igrača', len(SVI), '| ponuda 9. kola:', len(A), '| sa sudijama:', sum(1 for r in A.values() if r.get('sudije_ft')))

def tim_ocekivano(r):
    """Očekivani poeni tima iz ukupnog broja poena i šanse za pobedu (razlika = 12 × z)."""
    p = min(max(float(r['sansa_pobede']), .02), .98)
    return r['total_kladionica'] / 2 + 12 * NormalDist().inv_cdf(p) / 2
# Zbir modela po timu iz celog sastava, stvarni poeni tima iz zapisnika
ZM = {}
for r in SVI:
    if r.get('status') != 'Ne igra': ZM[r['tim']] = ZM.get(r['tim'], 0) + float(r.get('pts_proj') or 0)
KOD = {}
for r in A.values():
    v = RI.get(n_ime(r.get('api')))
    if v and v.get('tim'): KOD[r['tim']] = v['tim']
ST = {}   # konačan rezultat iz play-by-play zapisa 9. kola
for i in range(81, 91):
    b = json.load(open(f'api_kes/b{i}.json', encoding='utf8'))
    d = [x for q in ('FirstQuarter', 'SecondQuarter', 'ThirdQuarter', 'ForthQuarter', 'ExtraTime') for x in (b.get(q) or []) if x.get('POINTS_A') is not None]
    ST[b['CodeTeamA'].strip()] = d[-1]['POINTS_A']; ST[b['CodeTeamB'].strip()] = d[-1]['POINTS_B']
print('rezultati:', ST)
A = {k: r for k, r in A.items() if k}
TIMOVI = {}
for r in A.values():
    if r['tim'] in KOD and KOD[r['tim']] in ST and r.get('total_kladionica') and r.get('sansa_pobede') is not None and r['tim'] in ZM:
        TIMOVI[r['tim']] = dict(ut=r['utakmica'], ocek=tim_ocekivano(r), model=ZM[r['tim']], stvarno=ST[KOD[r['tim']]], total=r['total_kladionica'])
print(f"timova {len(TIMOVI)}, utakmica {len({t['ut'] for t in TIMOVI.values()})}")
T = list(TIMOVI.values())
mae = lambda x: sum(map(abs, x)) / len(x)
print(f"Greška poena tima: kvote {mae([t['stvarno'] - t['ocek'] for t in T]):.1f}, zbir modela {mae([t['stvarno'] - t['model'] for t in T]):.1f}, prosečan tim {mae([t['stvarno'] - st.mean(x['stvarno'] for x in T) for t in T]):.1f}")
print(f"Prosek: stvarno {st.mean(t['stvarno'] for t in T):.1f}, kvote {st.mean(t['ocek'] for t in T):.1f}, zbir modela {st.mean(t['model'] for t in T):.1f}")
print(f"Povezanost sa stvarnim: kvote {st.correlation([t['ocek'] for t in T], [t['stvarno'] for t in T]):.2f}, model {st.correlation([t['model'] for t in T], [t['stvarno'] for t in T]):.2f}")
m_od = st.mean(t['ocek'] / t['model'] for t in T)

U = []
for r in A.values():
    v = RI.get(n_ime(r.get('api')))
    if not v or not (v['min'] or 0) or r['tim'] not in TIMOVI or r.get('status') == 'Ne igra': continue
    U.append((r, v['pts'], TIMOVI[r['tim']]))
print('igrača u uzorku', len(U))
def var(ime, f):
    g = {}
    for r, a, t in U:
        p = float(r['pts_proj'])
        g.setdefault(t['ut'], []).append(abs(a - f(p, r, t)) - abs(a - p))
    sv = [x for v in g.values() for x in v]
    random.seed(1); K = list(g); B = []
    for _ in range(4000):
        s = [x for k in random.choices(K, k=len(K)) for x in g[k]]; B.append(sum(s) / len(s))
    B.sort(); print(f"{ime:<52}{sum(sv) / len(sv):+.3f} [{B[100]:+.3f}, {B[3899]:+.3f}]")
print(f"\nGreška poena po igraču, trenutno {mae([a - float(r['pts_proj']) for r, a, t in U]):.2f}; razlika (minus = bolje):")
var('bez faktora ukupnog broja poena', lambda p, r, t: p / float(r.get('faktor_utakmica') or 1))
var('pun faktor umesto polovine', lambda p, r, t: p * float(r.get('faktor_utakmica') or 1))
for w in (.25, .5, 1):
    var(f'hendikep: očekivano za tim / pola totala, težina {w}', lambda p, r, t, w=w: p * (t['ocek'] / (t['total'] / 2)) ** w)
for w in (.25, .5, 1):
    var(f'zbir modela ka očekivanju za tim, težina {w}', lambda p, r, t, w=w: p * ((t['ocek'] / t['model']) / m_od) ** w)
