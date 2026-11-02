# Evroliga – analiza igrača za Maxbet

Sistem koji za svako kolo Evrolige procenjuje poene, skokove i asistencije igrača, poredi ih sa Maxbet granicama
i kvotama pet drugih kladionica i pravi preporuke, tikete i predloge uloga. Rezultati se prate posle svakog dana,
a model uči iz njih.

## Struktura

| Folder | Sadržaj |
|---|---|
| `sistem/` | Ceo sistem: Python skripte, podaci, snimci kvota, arhiva. Sve skripte se pokreću iz ovog foldera. |
| `sistem/snippets/` | Skripte koje se pokreću u pregledaču (povlačenje kvota i podataka sa sajtova). |
| `sistem/books/` | Snimci kvota po kladionici i vremenu (mb = Maxbet, sb = Soccer, mk = Merkur, mz = Mozzart, md = Meridian, sx = Stoiximan). |
| `sistem/arhiva/` | Pozadinska arhiva: svi igrači iz ponude pri svakom osvežavanju i pun zapisnik posle utakmica. |
| `sistem/servis/` | Automatsko prikupljanje kvota u pozadini (vidi dole). |
| `sistem/prikupljeno/` | Snimci servisa po danima, `stanje.json` i `servis.log`. `market.py` ih čita zajedno sa `books/`. |
| `dashboard/index.html` | Stranica dashboarda: Preporuke (sa upisanim rezultatima i učinkom) i Tiketi. Isti sadržaj je u `index.html` i `sistem/index32.html`. |
| `index.html`, `data/`, `ikona*`, `manifest.webmanifest` | Web aplikacija u korenu repozitorijuma, koju objavljuje GitHub Pages. |

## Tok osvežavanja (`sistem/osvezi.py`)

1. Pregledač: kvote Maxbeta (`snap_HHMM.json`) i ostalih kladionica (`snippets/*.js` → `books/`),
   zvaničan izveštaj o povredama (`snippets/povrede.js`) i vesti → `statusi.json`, sudije (`snippets/sudije.js`) → `sudije_kolo.json`.
2. `python3 osvezi.py snap_HHMM.json` redom pokreće:
   - `nestanak.py` – igrači koji nestanu iz ponude → automatski status
   - `build5.py` – osnovne projekcije (minuti, učinak po minuti, protivnik, tempo, raspodela)
   - `dostupnost.py` – minuti prema sastavu (povrede, povratci, upitni), rizik uloge, status startera, nemir rotacije
   - `adjust3.py`, `minute.py` – kvote utakmice, ubedljiv ishod, odmor
   - `uloge2.py` – preraspodela šuteva/poena/skokova kad fale igrači, „veća uloga“
   - `uci2.py`, `tezine_primeni.py` – naučene težine (model / istorija / tržište), pomeraj, širina
   - `faul.py` – sklonost faulovima i sudije
   - `kv_pet2.py`, `market.py` – Maxbet linije, konsenzus 5 kladionica, raskorak, ⚡ (Maxbet kasni)
   - `kalibracija.py` – usklađivanje šansi sa stvarnošću
   - `evidencija.py` – evidencija svih linija
   - `t28.js` – pravila preporuka (isti kod kao dashboard)
   - zaključavanje (60 min pred meč), ulozi (¼ Kelly, ograničenja), CLV prema tržištu
   - `arhiva.py` – pozadinska arhiva
3. Slanje `igraci`, `kvote`, `zapamceno`, `evidencija` na dashboard.

Posle utakmica: ocena `zapamceno.json` radi se sama po utakmici (`servis/rezultati_servis.js`, vidi Servis). Posle kola ručno:
zapisnik → `results_DAN.json` (zapisnici po utakmici su u `prikupljeno/rezultati/`), `evidencija.py kvote_pet.json DAN results_DAN.json`,
`uci2.py`, `kalibracija.py`.

Detaljan postupak pred meč: `sistem/provera_pred_mec.md`.

## Servis za kvote (`sistem/servis/`)

Pokreće `snippets/*.js` u Chrome-u bez prozora (poseban profil, bez prijave na naloge) i snima u `prikupljeno/DATUM/`. Model koristi te snimke kad se pokrene
`py -X utf8 osvezi.py` (bez argumenta uzima najnoviji Maxbet snimak sa igračima); preračun se i dalje pokreće ručno. Windows zadatak ga okida na 10 min, a on sam bira učestalost prema rasporedu sa Maxbeta:
na 10 min u poslednjih 90 min pred meč, na 30 min na dan meča, na 2 h do 36 h pred meč, inače na 6 h.

- Prva postavka: `npm install` u `sistem/servis/`, pa `powershell -ExecutionPolicy Bypass -File instaliraj_zadatak.ps1`.
  Ako `npm install` pukne na `X509_STORE_add_cert`, pokrenuti ga bez promenljive `NODE_USE_SYSTEM_CA`.
- Ručno: `node kvote_servis.js --odmah`, `--samo=mb,sb`, `--stanje`.
- Aplikacija: prečica `Evroliga` na desktopu (`napravi_precicu.ps1`) diže `app_server.js` na http://localhost:8765. Dugme **Osveži** povlači kvote, pokreće `osvezi.py` i šalje podatke (bez koda) na GitHub; postoji samo lokalno. Povrede osvežava posebno, po `provera_pred_mec.md`. Dnevnik: `prikupljeno/app.log`.
- Rezultati: isti zadatak na svakih 10 min pokreće `rezultati_servis.js`. Od 90 min posle početka proverava zvanični API i, kad je utakmica
  odigrana, upisuje rezultat i ishod u `zapamceno.json` i `data/` samo za opklade sa te utakmice. Igrač kog nema u zapisniku ostaje neocenjen,
  uz upozorenje u `servis.log`. Provera bez upisa: `node rezultati_servis.js --proba=9`.
- Ocene u `servis.log`: `ok`; `prazno` (nema ponude, ne snima se; `UPOZORENJE` ako je manje od 6 h do meča);
  `sumnjivo` (ispod pola igrača prethodnog snimka, ide u `sumnjivo/`); `GREŠKA` (posle 3 uzastopne ta kladionica se proverava na 6 h).
- Blokade se ne zaobilaze. Stanje 2.11.2026: Mozzart vraća 429, a Stoiximan 403, pa za njih servis zasad nema snimke.

## Provere modela

- `backtest.py` – provera projekcija na celoj sezoni (vraćanje vremena kolo po kolo), podešavanje parametara
- `bt_*.py`, `korel.py` – posebne provere (raspodela, uloge, prilike za skok/asistenciju, rotacije, povezanost opklada)

## Napomene

- Kvote se mogu povući samo preko pregledača (sajtovi blokiraju direktan pristup iz oblaka).
- Pre svakog kola: `py -X utf8 pripremi_kolo.py KOLO` (statistika iz zvaničnog API-ja, raspored, odmor). Kolo i dan drže se u `kolo.json` i `kolo.py`;
  dan je prvi dan sa utakmicom koja još nije počela. Na Windowsu se sistem pokreće sa `py -X utf8 osvezi.py SNIMAK.json`.
- `KEYOUT` i `MINFIX` u `build5.py` su ručne izmene po kolu. Poslednji poznati statusi su u `extras.json`, a novi se upisuju u `statusi.json`.
- `onoff_k8.json` (uloge kad saigrač ne igra) je i dalje iz prvih 8 kola; osvežava se preko `snippets/onoff.js`.
- Python 3.10+, Node 18+ (za `t28.js`); bez dodatnih paketa, osim Playwright-a za servis.
