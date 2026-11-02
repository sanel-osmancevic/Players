// Upis rezultata po utakmici: kad zvanični API označi utakmicu kao odigranu, iz zapisnika se upisuju rezultat i ishod
// u zapamceno.json (i data/ za sajt) samo za opklade sa te utakmice; ostale čekaju svoju. Već ocenjene opklade se ne diraju.
// Učenje modela (evidencija.py, uci2.py, kalibracija.py) i dalje se pokreće posle kola.
// Upotreba: node rezultati_servis.js [--proba=KOLO]
//   --proba: ponovo oceni već ocenjeno kolo i uporedi sa upisanim, bez ikakvog upisa
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');

const SISTEM = path.resolve(__dirname, '..');
const API = 'https://api-live.euroleague.net', SEZONA = 'E2026';
const NAZIV = { VIR: 'Virtus', BES: 'Beşiktaş', BAR: 'Barcelona', PAM: 'Valencia', OLY: 'Olympiacos', MIL: 'Olimpia Milano', ASV: 'ASVEL', BAS: 'Baskonia',
  ZAL: 'Žalgiris', PAR: 'Partizan', IST: 'Anadolu Efes', PAN: 'Panathinaikos', DUB: 'Dubai', HTA: 'Hapoel TA', MAD: 'Real Madrid', ULK: 'Fenerbahče',
  TEL: 'Maccabi TA', PRS: 'Paris', RED: 'Crvena zvezda', MUN: 'Bayern' };
const STAT = { Poeni: 'points', Skokovi: 'totalRebounds', Asistencije: 'assistances' };
const PRE_PROVERE = 90;   // minuta od početka utakmice pre prve provere zapisnika

// curl kao u osvezi.py: Node TLS na ovom računaru puca kad je postavljen NODE_USE_SYSTEM_CA
const json = u => JSON.parse(execFileSync('curl', ['-s', '-f', '--max-time', '20', API + u], { encoding: 'utf8', maxBuffer: 2e7 }));
const kljuc = n => n.normalize('NFKD').replace(/[^\x00-\x7f]/g, '').toLowerCase().replace(/'/g, '')
  .replace(/\b(iv|iii|jr)\b/g, '').replace(/\b[a-z]\b/g, '').replace(/[^a-z]/g, '');   // isto kao key() u evidencija.py
const ime = n => { const [l, f = ''] = n.split(/,\s*/); return kljuc(f + ' ' + l); };
const terminMs = (t, sada) => {
  const m = String(t).match(/(\d+)\.(\d+)\.\s+(\d+):(\d+)/); if (!m) return null;
  const n = new Date(sada), d = new Date(n.getFullYear(), +m[2] - 1, +m[1], +m[3], +m[4]);
  if (d - n > 180 * 864e5) d.setFullYear(d.getFullYear() - 1);
  return +d;
};
const pisi = (f, s) => { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f + '.tmp', s); fs.renameSync(f + '.tmp', f); };

// Zapisnici odigranih utakmica datih kola: { "Domaćin – Gost": { igrači po ključu imena, sirovi red za results format } }
function zapisnici(kola, log) {
  const out = {};
  for (const k of kola) {
    for (const g of json(`/v2/competitions/E/seasons/${SEZONA}/games?roundNumber=${k}`).data) {
      if (!g.played) continue;
      const h = NAZIV[g.local.club.code], a = NAZIV[g.road.club.code];
      if (!h || !a) { log(`UPOZORENJE: nepoznat kod tima ${g.local.club.code}/${g.road.club.code}`); continue; }
      const s = json(`/v3/competitions/E/seasons/${SEZONA}/games/${g.gameCode}/stats`), ig = {};
      for (const p of [...s.local.players, ...s.road.players]) ig[ime(p.player.person.name)] = p;
      out[k + '|' + h + ' – ' + a] = { gameCode: g.gameCode, ig };
    }
  }
  return out;
}

function oceni(r, z) {
  const p = z.ig[kljuc(r.igrac)];
  if (!p) return null;   // nema ga u zapisniku: moguće da se ime razlikuje, ne nagađamo
  if (!p.stats.timePlayed) return { rezultat: null, ishod: 'nije igrao' };
  const v = p.stats[STAT[r.kategorija]], L = Number(r.linija);
  if (v == null || !(r.smer === 'više' || r.smer === 'manje')) return null;
  return { rezultat: v, ishod: (r.smer === 'više' ? v > L : v < L) ? 'prošlo' : 'palo' };
}

function azuriraj({ zap = path.join(SISTEM, 'zapamceno.json'), web = path.join(SISTEM, '..', 'data'), izlaz = path.join(SISTEM, 'prikupljeno', 'rezultati'), log = console.log, sada = Date.now() } = {}) {
  const redovi = JSON.parse(fs.readFileSync(zap, 'utf8'));
  const ceka = redovi.filter(r => r.igrac && !r.ishod && (t => t !== null && t + PRE_PROVERE * 6e4 <= sada)(terminMs(r.termin, sada)));
  if (!ceka.length) return 0;
  const Z = zapisnici([...new Set(ceka.map(r => r.kolo))], log);
  let n = 0;
  for (const r of ceka) {
    const z = Z[r.kolo + '|' + r.utakmica]; if (!z) continue;   // utakmica još nije odigrana
    const o = oceni(r, z);
    if (!o) { log(`rezultati UPOZORENJE: ${r.igrac} (${r.opklada}) nije u zapisniku za ${r.utakmica}, ostaje neocenjen`); continue; }
    Object.assign(r, o); n++;
  }
  if (!n) return 0;
  pisi(zap, JSON.stringify(redovi));
  // zapisnik u obliku results_DAN.json, za evidencija.py posle kola
  for (const [k, z] of Object.entries(Z)) {
    const f = path.join(izlaz, `kolo${k.split('|')[0]}_${z.gameCode}.json`);
    if (!fs.existsSync(f)) pisi(f, JSON.stringify(Object.values(z.ig).map(p => [p.player.person.name, Math.round(p.stats.timePlayed / 6) / 10, p.stats.points, p.stats.totalRebounds, p.stats.assistances])));
  }
  if (fs.existsSync(web)) {   // isto što i objavi_web.py, samo za ovaj fajl
    fs.copyFileSync(zap, path.join(web, 'zapamceno.json'));
    const l = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Belgrade', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date(sada)).map(p => [p.type, p.value]));
    const stara = (() => { try { return JSON.parse(fs.readFileSync(path.join(web, 'meta.json'), 'utf8')); } catch { return {}; } })();
    pisi(path.join(web, 'meta.json'), JSON.stringify({ ...stara, v: Math.floor(sada / 1000), azurirano: `${l.day}.${l.month}.${l.year}. ${l.hour}:${l.minute}` }));
  }
  log(`rezultati: upisano ${n}, još čeka ${redovi.filter(r => r.igrac && !r.ishod).length}`);
  return n;
}

function proba(k) {
  const red = JSON.parse(fs.readFileSync(path.join(SISTEM, 'zapamceno.json'), 'utf8')).filter(r => r.igrac && +r.kolo === k && r.ishod);
  const Z = zapisnici([k], console.log);
  let ok = 0; const raz = [];
  for (const r of red) {
    const z = Z[k + '|' + r.utakmica], o = z && oceni(r, z);
    if (o && o.ishod === r.ishod && o.rezultat === r.rezultat) ok++;
    else raz.push(`${r.igrac} | ${r.utakmica} | ${r.opklada} | upisano ${r.rezultat}/${r.ishod} | izračunato ${o ? o.rezultat + '/' + o.ishod : (z ? 'nema u zapisniku' : 'nema utakmice')}`);
  }
  console.log(`kolo ${k}: poklapa se ${ok} od ${red.length}`); raz.forEach(x => console.log(' ', x));
  return raz.length;
}

if (require.main === module) {
  const a = process.argv.find(x => x.startsWith('--proba='));
  if (a) process.exitCode = proba(+a.slice(8)) ? 1 : 0; else azuriraj();
}
module.exports = { azuriraj };
