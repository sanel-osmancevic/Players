# Provera pred meč (svako osvežavanje na dan utakmice)

Redosled pri osvežavanju (pregledač na korisnikovom računaru):

1. **Kvote** — servis ih sam snima u prikupljeno/ (Maxbet, Soccer, Merkur, Meridian; odmah: `node servis/kvote_servis.js --odmah`).
   Kladionice koje servis ne može da čita (Mozzart, Stoiximan): ručno snippets/mozzart.js → books/mz_, snippets/stoiximan.js → books/sx_.
2. **Nestanak iz ponude** — automatski (nestanak.py u osvezi.py): igrač nestao u poslednja dva snimka kod 2+ kladionice → statusi_auto.json "Upitan",
   kod svih → "Ne igra".
3. **Zvaničan izveštaj o povredama** — automatski (servis/povrede_servis.js uz dugme Osveži i automatiku; članak "Injury report, Round N" i Rotowire).
   Ručni unos u statusi.json ima prednost: "PREZIME, IME|KOD": ["Ne igra" | "Upitan" | "Igra", "Zvaničan izveštaj DD.MM. HH:MM"].
   Pažnja: "ruled out" = Ne igra; "questionable"/"game-time decision"/"GTD" = Upitan; "available"/"returns"/"full roster" = Igra.
   Ako klub još nije poslao izveštaj, ostaje prethodno stanje.
4. **Vesti** — WebSearch za timove dana (Eurohoops, Basketnews, Rotowire "EuroLeague Primer: Round N", domaći sajtovi klubova:
   grčki za OLY/PAN, turski za ULK/IST/BES, španski za MAD/BAR/BAS/PAM, srpski za RED/PAR, litvanski za ZAL, izraelski za TEL/HTA).
   Novije od zvaničnog izveštaja ima prednost; upisati u statusi.json sa izvorom.
5. **Sudije** — automatski uz Osveži (posle objave sudija na dan meča; sudije.json se osvežava preko snippets/sudije.js): sudije_kolo.json
   {"Domaćin – Gost": [["SUDIJA 1", "SUDIJA 2", "SUDIJA 3"], indeks_faulova, indeks_FT]} (indeksi iz sudije.json, prosek trojke).
6. **`py -X utf8 osvezi.py`** — preračun; utakmice u poslednjih 60 min se zaključavaju.

7. **Arhiva** — osvezi.py na kraju sam beleži sve igrače u ponudi (arhiva/kolo{K}_ponuda.jsonl); posle utakmica evidencija.py sa
   fajlom rezultata upisuje puni zapisnik u arhiva/kolo{K}_rezultati.json. Za rezultate koristiti puni zapisnik (box format:
   {'polja': [...], 'p': [[ime, tim, min, pts, reb, ast, fga, fta, faulovi, starter, ...]]}), a za evidenciju results format.
