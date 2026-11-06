# Zajedničko čitanje i pisanje fajlova i vreme u Beogradu. Fajlovi su uvek UTF-8, a upis ne ostavlja napola zapisan fajl.
import json, os, datetime

def citaj(f):
    with open(f, encoding='utf8') as h: return json.load(h)

def pisi(d, f, **kw):
    with open(f + '.tmp', 'w', encoding='utf8') as h: json.dump(d, h, **kw)
    os.replace(f + '.tmp', f)

def citaj_tekst(f):
    with open(f, encoding='utf8') as h: return h.read()

def pisi_tekst(s, f):
    with open(f, 'w', encoding='utf8') as h: h.write(s)

def beograd(d=None):
    """Trenutak u vremenu Beograda: letnje vreme od poslednje nedelje marta do poslednje nedelje oktobra u 01:00 UTC."""
    d = (d or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)
    pn = lambda m: max(datetime.datetime(d.year, m, x, 1, tzinfo=datetime.timezone.utc) for x in range(25, 32) if datetime.date(d.year, m, x).weekday() == 6)
    return d.astimezone(datetime.timezone(datetime.timedelta(hours=2 if pn(3) <= d < pn(10) else 1)))

# Učenje čeka bar ovoliko ocenjenih utakmica u kolu, da jedna utakmica (npr. sa produžetkom) ne pomera težine za sve ostale
NAJMANJE_UTAKMICA_ZA_UCENJE = 4
def redovi_za_ucenje(redovi):
    ut = {}
    for e in redovi:
        if e.get('rezultat') is not None: ut.setdefault(e['kolo'], set()).add(e['utakmica'])
    return [e for e in redovi if len(ut.get(e['kolo'], ())) >= NAJMANJE_UTAKMICA_ZA_UCENJE]

# Šansa na liniji računa se oko medijane, ne oko proseka: učinak je iskošen udesno (retke velike večeri), pa igrač prelazi
# svoju projekciju u 43-46% utakmica. Pomak medijane od sirove projekcije (prosek), kola 3-9 (bt_projekcija.py, 6.11.2026);
# na linijama 9. i 10. kola prosečna šansa za "više" je 45.6% naspram stvarnih 45.9% (oko proseka 50.9%).
MEDIJANA = {'pts': -0.67, 'reb': -0.21, 'ast': -0.25}
