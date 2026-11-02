// On/off iz sačuvanih play-by-play zapisa (api_kes/b{kod}.json), istim kodom kao snippets/onoff.js, bez ponovnog povlačenja.
// Upotreba: node onoff_kes.js [POSLEDNJE_KOLO] [IZLAZ.json]; bez argumenata uzima kola pre aktuelnog i piše onoff.json.
const fs = require('fs'), path = require('path');
const DIR = __dirname, K = path.join(DIR, 'api_kes');
const kolo = +process.argv[2] || JSON.parse(fs.readFileSync(path.join(DIR, 'kolo.json'), 'utf8')).kolo - 1;
const izlaz = process.argv[3] || path.join(DIR, 'onoff.json');
// svi igrači, a ne samo oni koji su već izostali: i prvi izostanak mora da ima podatke
let src = fs.readFileSync(path.join(DIR, 'snippets', 'onoff.js'), 'utf8').replace(/const MAXR = \d+, EXTRA = \[\];/, `const MAXR = ${kolo}, EXTRA = {includes: () => true};`);
const kraj = 'JSON.stringify({nG, bad, MAXR, d: OUT});';
if (!src.includes(kraj)) throw new Error('promenjen snippets/onoff.js');
src = src.replace(kraj, 'return {nG, bad, MAXR, d: OUT};');
const stub = async u => {
  let m = /roundNumber=(\d+)/.exec(u), v;
  if (m) { const d = (+m[1] - 1) * 10; v = { data: Array.from({ length: 10 }, (_, i) => d + i + 1).filter(c => fs.existsSync(path.join(K, `b${c}.json`))).map(gameCode => ({ played: true, gameCode })) }; }
  else { m = /gamecode=(\d+)/.exec(u); v = JSON.parse(fs.readFileSync(path.join(K, `b${m[1]}.json`), 'utf8')); }
  return { json: async () => v };
};
new (Object.getPrototypeOf(async function () {}).constructor)('fetch', 'window', src)(stub, {}).then(r => {
  fs.writeFileSync(izlaz, JSON.stringify(r.d));
  console.log(`on/off: ${r.nG} utakmica, kola do ${r.MAXR}, grešaka ${r.bad.length}, timova ${Object.keys(r.d).length}`);
  if (r.bad.length) process.exitCode = 1;
}).catch(e => { console.error('GREŠKA ' + e.message); process.exitCode = 1; });
