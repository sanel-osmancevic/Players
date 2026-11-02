// Windows zadatak ovo poziva na 10 min. Danima sa utakmicama, od 8:00 do 1:30 sledećeg jutra, jednom na sat radi ceo tok
// (kvote, preračun, GitHub); inače samo snima kvote i upisuje rezultate po svom rasporedu. Kad se kolo završi, sam priprema sledeće.
// SADA zadaje trenutno vreme samo za probe.
const fs = require('fs'), path = require('path');
const { osvezi, pokreni } = require('./tok');

const SISTEM = path.resolve(__dirname, '..'), PRIK = path.join(SISTEM, 'prikupljeno'), AUTO = path.join(PRIK, 'auto.json');
const MIN = 60000, SAT = 60 * MIN;
const OD_SATA = 8, DO_MINUTA = 90;          // sledećeg jutra, da stignu i rezultati kasnih utakmica
const NA_SAT = 58 * MIN;                    // 2 min rezerve da kašnjenje okidača ne preskoči sat
const POSLE_KOLA = 12 * SAT, PONOVO_PRIPREMA = 6 * SAT;
const citaj = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const log = m => { fs.mkdirSync(PRIK, { recursive: true }); fs.appendFileSync(path.join(PRIK, 'app.log'), `${new Date().toISOString()} ${m}\n`); };

function beograd(ms) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Belgrade', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date(ms)).map(x => [x.type, x.value]));
  return { dan: `${p.year}-${p.month}-${p.day}`, min: +p.hour * 60 + +p.minute };
}
function danUtakmice(games, sada) {
  const dani = new Set(games.map(g => beograd(Date.parse(g[3])).dan)), b = beograd(sada);
  if (dani.has(b.dan) && b.min >= OD_SATA * 60) return true;
  return b.min <= DO_MINUTA && dani.has(beograd(sada - 24 * SAT).dan);
}
const kraj = games => Math.max(...games.map(g => Date.parse(g[3])));

async function main() {
  const sada = process.env.SADA ? Date.parse(process.env.SADA) : Date.now();
  const k = citaj(path.join(SISTEM, 'kolo.json'), { kolo: 0, games: [] }), a = citaj(AUTO, {});
  fs.mkdirSync(PRIK, { recursive: true });
  // kolo završeno: statistika i raspored sledećeg
  if (k.games.length && sada - kraj(k.games) > POSLE_KOLA && (!a.priprema || sada - a.priprema > PONOVO_PRIPREMA)) {
    a.priprema = sada; fs.writeFileSync(AUTO, JSON.stringify(a));
    const r = await pokreni('py', ['-X', 'utf8', 'pripremi_kolo.py', String(k.kolo + 1)], SISTEM, 20 * MIN);
    log(`priprema ${k.kolo + 1}. kola: ${r.code ? 'GREŠKA ' + r.izlaz.trim().slice(-200) : 'gotovo'}`);
    return;
  }
  if (danUtakmice(k.games, sada) && (!a.pokrenuto || sada - a.pokrenuto >= NA_SAT)) {
    a.pokrenuto = sada; fs.writeFileSync(AUTO, JSON.stringify(a));
    log('automatsko osvežavanje');
    const p = await osvezi({ radi: true, pocetak: Date.now(), koraci: [], ishod: null, greska: null });
    Object.assign(a, { kraj: Date.now(), greska: p.greska, koraci: p.koraci.map(x => `${x.naziv}: ${x.status}`) });
    fs.writeFileSync(AUTO, JSON.stringify(a));
    return;
  }
  if (process.env.EVRO_BEZ_KVOTA) return;   // samo za probe
  const r = await pokreni(process.execPath, ['kvote_servis.js'], __dirname, 20 * MIN);
  if (r.code) log('kvote: GREŠKA ' + r.izlaz.trim().slice(-200));
}

if (require.main === module) main().catch(e => { log('tik PAD: ' + e.message); process.exitCode = 1; });
module.exports = { danUtakmice };
