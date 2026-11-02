# Zajedničko podešavanje kola: koje je kolo i dan i kako se timovi zovu. kolo.json pravi pripremi_kolo.py.
# DAN je prvi dan sa utakmicom koja još nije počela; može se zadati promenljivom DAN, a SADA menja trenutno vreme (za probe).
import os, re, datetime, unicodedata
from pomocno import citaj
_d = citaj(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kolo.json'))
KOLO, OD, GAMES = _d['kolo'], _d['od'], _d['games']

def _sada():
    if os.environ.get('SADA'): return datetime.datetime.fromisoformat(os.environ['SADA']).astimezone(datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc)
def _dan():
    sada = _sada()
    for h, a, t, u in GAMES:
        if datetime.datetime.fromisoformat(u.replace('Z', '+00:00')) > sada: return t.split()[0]
    return GAMES[-1][2].split()[0]
DAN = os.environ.get('DAN') or _dan()

IME = {'RED': 'Crvena zvezda', 'MUN': 'Bayern', 'TEL': 'Maccabi TA', 'PRS': 'Paris', 'MAD': 'Real Madrid', 'ULK': 'Fenerbahče', 'DUB': 'Dubai', 'HTA': 'Hapoel TA',
       'IST': 'Anadolu Efes', 'PAN': 'Panathinaikos', 'ZAL': 'Žalgiris', 'PAR': 'Partizan', 'ASV': 'ASVEL', 'BAS': 'Baskonia', 'OLY': 'Olympiacos', 'MIL': 'Olimpia Milano',
       'BAR': 'Barcelona', 'PAM': 'Valencia', 'VIR': 'Virtus', 'BES': 'Beşiktaş'}
KOD = {v: k for k, v in IME.items()}
# nazivi timova kod raznih kladionica (uključujući grčku latinicu u Stoiximan adresama, npr. "olybiakos", "bartselona")
ALIAS = {'Real Madrid': ['real'], 'Panathinaikos': ['panathinaikos', 'panatinaikos'], 'Anadolu Efes': ['efes'], 'Paris': ['paris', 'pari'],
         'Crvena zvezda': ['zvezda', 'crvena', 'redstar', 'erythros'], 'Žalgiris': ['zalgiris'], 'Fenerbahče': ['fener'], 'Maccabi TA': ['maccabi', 'makabi'],
         'Hapoel TA': ['hapoel', 'xapoel'], 'Beşiktaş': ['besiktas'], 'Olimpia Milano': ['milan', 'olimpia', 'olibia'], 'Bayern': ['bayern', 'munchen', 'bagern'],
         'ASVEL': ['asvel', 'villeurb', 'lyon', 'vilerban'], 'Virtus': ['virtus', 'virtous'], 'Valencia': ['valencia', 'valenthia'], 'Dubai': ['dubai', 'doubai'],
         'Partizan': ['partizan'], 'Barcelona': ['barcelona', 'barca', 'bartselona'], 'Baskonia': ['baskonia', 'vitoria'],
         'Olympiacos': ['olympiacos', 'olimpijakos', 'olybiakos'], 'Monaco': ['monaco']}
TAČNO = {'H. Tel Aviv': 'Hapoel TA', 'Hapoel T.A.': 'Hapoel TA', 'M. Tel Aviv': 'Maccabi TA', 'Maccabi T.A.': 'Maccabi TA', 'C. Zvezda': 'Crvena zvezda'}
def tim(naziv):
    """Naziv tima sa kladionice -> naziv u modelu; None ako je nepoznat."""
    if naziv in TAČNO: return TAČNO[naziv]
    g = re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', naziv).encode('ascii', 'ignore').decode().lower())
    return next((t for t, a in ALIAS.items() if any(x in g for x in a)), None)
