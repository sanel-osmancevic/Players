# Provere računa pre upisa liste. Greška zaustavlja osvežavanje (lista ostaje ista), a upozorenje se samo ispisuje.
# Proveravaju se samo utakmice dana za koji se radi; ostali dani se računaju ponovo kad dođu na red.
import math
from statistics import mean

ODSTUPANJE_ZBIRA = 0.25      # zbir poena sveden na 400 minuta prema kvotama (sirov zbir zavisi od broja igrača u sastavu): stop
MINUTI_UTAKMICE = 400
ZBIR_UPOZORENJE = 0.10       # isti zbir: iznad ovoga samo upozorenje
ZBIR_KORAK = 0.15            # koliko jedan korak sme da pomeri zbir poena na utakmici (stop)
ZBIR_KORAK_UPOZORENJE = 0.05
ODSTUPANJE_KORAKA = 0.20     # koraci posle pomeraja (sudije, faulovi) smeju malo da pomere projekciju
OPSEG_PREMA_PROSEKU = (0.3, 3.5)   # projekcija prema učinku po minuti × projektovani minuti
MINIMUM_ZA_PROSEK = 3.0      # ispod ovoga skupljanje ka proseku lige prirodno daje velike odnose
NAJVISE_MINUTA = 42
MINUTI_TIMA = (170, 240)     # van ovoga samo upozorenje: raspodela minuta još nije svedena na 200
ISKOSENOST_MODELA = 0.15     # prosečna razlika modela i tržišta za „više“ na poenima
NAJMANJE_LINIJA = 10
BIAS = {'pts': 0.2, 'reb': 0.0, 'ast': 0.0}


def igraci(rows, kvote_utakmica, dan, bias=None):
    """Vraća (greške, upozorenja) za igraci2.json posle svih koraka modela."""
    bias = bias or BIAS
    greske, upozorenja = [], []
    danas = [r for r in rows if r['termin'].startswith(dan) and r['status'] != 'Ne igra']
    zbir, minuti, min_ut = {}, {}, {}
    for r in danas:
        zbir[r['utakmica']] = zbir.get(r['utakmica'], 0) + (r.get('pts_proj') or 0)
        minuti[r['tim']] = minuti.get(r['tim'], 0) + (r.get('minuti_proj') or 0)
        min_ut[r['utakmica']] = min_ut.get(r['utakmica'], 0) + (r.get('minuti_proj') or 0)
        if (r.get('minuti_proj') or 0) > NAJVISE_MINUTA:
            greske.append(f"{r['igrac']}: {r['minuti_proj']} projektovanih minuta")
        for k in ('pts', 'reb', 'ast'):
            p = r.get(f'{k}_proj'); sd = r.get(f'{k}_sd'); s = r.get(f'{k}_proj_sirovo')
            if p is None or sd is None or not math.isfinite(p) or p < 0 or sd <= 0:
                greske.append(f"{r['igrac']} {k}: neispravna projekcija {p} ili širina {sd}")
                continue
            if s is not None and s + bias.get(k, 0) >= MINIMUM_ZA_PROSEK and abs(p / (s + bias.get(k, 0)) - 1) > ODSTUPANJE_KORAKA:
                greske.append(f"{r['igrac']} {k}: poslednji koraci menjaju projekciju sa {s + bias.get(k, 0):.1f} na {p}")
            v = [float(x) for x in str(r.get(f'{k}_sve', '')).split(',') if x != '']
            if len(v) >= 3 and r.get('minuti') and r.get('minuti_proj'):
                ocek = mean(v) / r['minuti'] * r['minuti_proj']
                if ocek >= MINIMUM_ZA_PROSEK and not OPSEG_PREMA_PROSEKU[0] <= p / ocek <= OPSEG_PREMA_PROSEKU[1]:
                    greske.append(f"{r['igrac']} {k}: projekcija {p} prema učinku {ocek:.1f}")
    for u, s in zbir.items():
        g = kvote_utakmica.get(u)
        if not g:
            upozorenja.append(f'{u}: nema ukupnog broja poena iz kvota')
            continue
        z400 = s / min_ut[u] * MINUTI_UTAKMICE if min_ut.get(u) else s
        if abs(z400 / g[0] - 1) > ODSTUPANJE_ZBIRA:
            greske.append(f'{u}: zbir poena na {MINUTI_UTAKMICE} minuta {z400:.0f}, a kvote očekuju {g[0]}')
        elif abs(z400 / g[0] - 1) > ZBIR_UPOZORENJE:
            upozorenja.append(f'{u}: zbir poena na {MINUTI_UTAKMICE} minuta {z400:.0f}, a kvote očekuju {g[0]} ({z400 / g[0] - 1:+.0%})')
    for t, m in minuti.items():
        if not MINUTI_TIMA[0] <= m <= MINUTI_TIMA[1]:
            upozorenja.append(f'{t}: raspoređeno {m:.0f} minuta')
    return greske, upozorenja


def zbir_po_utakmici(rows, dan):
    z = {}
    for r in rows:
        if r['termin'].startswith(dan) and r['status'] != 'Ne igra': z[r['utakmica']] = z.get(r['utakmica'], 0) + (r.get('pts_proj') or 0)
    return z


class TragZbira:
    """Pamti zbir poena po utakmici posle svakog koraka modela i traži korak koji ga previše pomeri."""
    def __init__(self, rows, dan):
        self.dan = dan; self.koraci = [('osnova', zbir_po_utakmici(rows, dan))]

    def posle(self, naziv, rows):
        pre = self.koraci[-1][1]; sad = zbir_po_utakmici(rows, self.dan); self.koraci.append((naziv, sad))
        greske, upozorenja = [], []
        for u, s in sad.items():
            if not pre.get(u): continue
            d = s / pre[u] - 1; t = f'{u}: {naziv} menja zbir poena sa {pre[u]:.0f} na {s:.0f} ({d:+.0%})'
            if abs(d) > ZBIR_KORAK: greske.append(t)
            elif abs(d) > ZBIR_KORAK_UPOZORENJE: upozorenja.append(t)
        return greske, upozorenja


def zbir_stanje(rows, kvote_utakmica, dan, trag):
    """Za zbir_utakmica.json: zbir prema kvotama i po koracima, da se posle kola izmeri da li model sistematski greši."""
    izlaz = []
    for u, s in zbir_po_utakmici(rows, dan).items():
        m = sum(r.get('minuti_proj') or 0 for r in rows if r['utakmica'] == u and r['termin'].startswith(dan) and r['status'] != 'Ne igra')
        izlaz.append(dict(utakmica=u, dan=dan, zbir=round(s, 1), minuti=round(m, 1), zbir_400=round(s / m * MINUTI_UTAKMICE, 1) if m else None,
                          kvote=(kvote_utakmica.get(u) or [None])[0], koraci={n: round(z.get(u, 0), 1) for n, z in trag.koraci}))
    return izlaz


def kvote(redovi, igr, dan):
    """Vraća (greške, upozorenja) za kvote_pet.json posle tržišta: tržište u granicama i model bez velike iskošenosti."""
    greske, upozorenja = [], []
    pi = {r['igrac']: r for r in igr if r['termin'].startswith(dan)}
    Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
    razlike = []
    for o in redovi:
        t = o.get('trz_vise')
        if t is None or not o.get('kvota_manje'): continue
        if not 0 <= t <= 1:
            greske.append(f"{o['igrac']} {o['kategorija']} {o['linija']}: tržište {t}")
        p = pi.get(o['igrac'])
        if p and o['kategorija'] == 'Poeni' and p['status'] != 'Ne igra':
            razlike.append(1 - Phi((math.floor(o['linija']) + 0.5 - p['pts_proj']) / p['pts_sd']) - t)
    if len(razlike) >= NAJMANJE_LINIJA and abs(mean(razlike)) > ISKOSENOST_MODELA:
        greske.append(f'poeni: model je prosečno {mean(razlike):+.2f} od tržišta na {len(razlike)} linija')
    return greske, upozorenja


def obradi(naziv, greske, upozorenja, tiho=False):
    """Ispisuje upozorenja, a kod grešaka zaustavlja osvežavanje."""
    import sys
    for u in upozorenja: print(f'Provera {naziv}, upozorenje: {u}')
    if greske:
        sys.exit(f'Provera {naziv} nije prošla, lista nije menjana: ' + '; '.join(greske[:6]) + (f' (još {len(greske) - 6})' if len(greske) > 6 else ''))
    if not tiho: print(f'Provera {naziv}: u redu')
