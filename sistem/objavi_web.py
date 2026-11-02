# Priprema podataka za web aplikaciju (GitHub Pages): kopira trenutne podatke u data/ i upisuje vreme ažuriranja.
# Posle ovoga se koren projekta objavljuje (git push u repozitorijum sa GitHub Pages).
import json, os, shutil
from pomocno import citaj, pisi, beograd
os.chdir(os.path.dirname(os.path.abspath(__file__)))
WEB = os.environ.get('WEB_DIR') or '..'   # sajt je u korenu repozitorijuma
os.makedirs(f'{WEB}/data', exist_ok=True)
for src, dst in (('zapamceno.json', 'zapamceno.json'), ('igraci2.json', 'igraci.json'), ('kvote.json', 'kvote.json'), ('utakmice.json', 'utakmice.json'), ('zakljucano.json', 'zakljucano.json')):
    if os.path.exists(src): shutil.copy(src, f'{WEB}/data/{dst}')
now = beograd()
_m = f'{WEB}/data/meta.json'
stara = citaj(_m) if os.path.exists(_m) else {}   # čuva vreme osvežavanja koje upisuje servis
pisi({**stara, 'v': int(now.timestamp()), 'azurirano': now.strftime('%d.%m.%Y. %H:%M')}, _m)
print('web podaci spremni:', WEB, now.strftime('%H:%M'))
