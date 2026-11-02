// Prikupljanje kvota u pozadini (faza 1): pokreće snippets/*.js u Chrome-u (poseban profil) i snima u prikupljeno/DATUM/, a NE u books/,
// pa model i preporuke ostaju netaknuti. Bez prijave na naloge i bez opklada; blokiran sajt se samo beleži i ređe proverava.
// Upotreba: node kvote_servis.js [--odmah] [--samo=mb,sb] [--stanje]
//   bez argumenata: poziva ga Task Scheduler na 10 min, a skripta sama odlučuje da li je vreme za novi snimak
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright-core');
const { azuriraj } = require('./rezultati_servis');

const SISTEM = path.resolve(__dirname, '..'), IZLAZ = path.join(SISTEM, 'prikupljeno');
const STANJE = path.join(IZLAZ, 'stanje.json'), DNEVNIK = path.join(IZLAZ, 'servis.log'), BRAVA = path.join(IZLAZ, '.brava');
const PROFIL = path.join(__dirname, 'profil');
const KNJIGE = [   // Maxbet prvi: on daje raspored utakmica za izbor učestalosti
  ['mb', 'maxbet.js', 'https://www.maxbet.rs/sr/'],
  ['sb', 'soccer.js', 'https://www.soccerbet.rs/sr/'],
  ['mk', 'merkur.js', 'https://www.merkurxtip.rs/sr/'],
  ['mz', 'mozzart.js', 'https://www.mozzartbet.com/sr'],
  ['md', 'meridian.js', 'https://meridianbet.rs/sr/'],
  ['sx', 'stoiximan.js', 'https://www.stoiximan.gr/'],
];
const MIN = 60000, TAKT = 10;              // Task Scheduler okida na TAKT minuta
const ROK_SKRIPTE = 3 * MIN, ROK_BRAVE = 25 * MIN;
const POSLE_GRESAKA = 3, PAUZA_GRESKE = 6 * 60;   // posle 3 uzastopne greške kladionica se proverava na 6 h
const MIN_UDEO = 0.5;                      // snimak ispod pola prethodnog (bez započete utakmice u međuvremenu) je sumnjiv
const POZIV_PRAZNO = 6 * 60;               // upozorenje ako kladionica nema igrače manje od 6 h pred meč

const log = m => { const l = `${new Date().toISOString()} ${m}`; console.log(l); fs.appendFileSync(DNEVNIK, l + '\n'); };
const citaj = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const pisi = (f, s) => { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f + '.tmp', s); fs.renameSync(f + '.tmp', f); };
const lokalno = d => Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Belgrade', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(d).map(p => [p.type, p.value]));

// Razmak između snimaka (min) prema sledećoj utakmici
function razmak(pocetci, sada) {
  const sled = pocetci.filter(t => t > sada).sort((a, b) => a - b)[0];
  if (!sled) return 360;                   // raspored nepoznat ili kolo završeno
  const do_ = (sled - sada) / MIN;
  if (do_ <= 90) return 10;
  const a = lokalno(new Date(sada)), b = lokalno(new Date(sled));
  if (a.year === b.year && a.month === b.month && a.day === b.day) return 30;
  return do_ <= 36 * 60 ? 120 : 360;
}

function brojIgraca(p) { return Object.keys(p.raw || p.out || {}).length; }

// Ocena snimka: 'ok' se upisuje, 'prazno' je normalno pre objave ponude, 'sumnjivo' ide u poseban folder
function oceni(k, p, st, pocetci, sada) {
  const n = brojIgraca(p), pre = st[k]?.n, tPre = st[k]?.t;
  if (!n) return p.games?.length ? 'ok' : 'prazno';   // Maxbet kvote utakmica vrede i pre nego što se pojave igrači
  if (pre && n < pre * MIN_UDEO && !pocetci.some(t => t > tPre && t <= sada)) return 'sumnjivo';
  return 'ok';
}

async function pokreni(ctx, url, skripta) {
  const page = await ctx.newPage();
  try {
    const r = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: MIN });
    if (r && r.status() >= 400) throw new Error('HTTP ' + r.status());
    await page.waitForTimeout(4000);       // sajt postavlja svoje kolačiće
    const cdp = await ctx.newCDPSession(page);
    // replMode dozvoljava await na vrhu i vraća poslednji izraz, pa snippeti ostaju isti kao za ručno pokretanje
    const e = await Promise.race([
      cdp.send('Runtime.evaluate', { expression: skripta, replMode: true, awaitPromise: true, returnByValue: true }),
      new Promise((_, n) => setTimeout(() => n(new Error('isteklo vreme skripte')), ROK_SKRIPTE)),
    ]);
    if (e.exceptionDetails) throw new Error((e.exceptionDetails.exception?.description || e.exceptionDetails.text).split('\n')[0]);
    if (typeof e.result.value !== 'string') throw new Error('skripta nije vratila JSON');
    return JSON.parse(e.result.value);
  } finally { await page.close().catch(() => {}); }
}

async function main() {
  const arg = process.argv.slice(2), ODMAH = arg.includes('--odmah');
  const samo = (arg.find(a => a.startsWith('--samo=')) || '').slice(7).split(',').filter(Boolean);
  fs.mkdirSync(IZLAZ, { recursive: true });
  const st = citaj(STANJE, { knjige: {}, pocetci: [] });
  const sada = Date.now();
  if (arg.includes('--stanje')) {
    console.log(`razmak sada: ${razmak(st.pocetci, sada)} min`);
    for (const [k, v] of Object.entries(st.knjige)) console.log(k, JSON.stringify(v));
    return;
  }
  try { azuriraj({ log }); } catch (e) { log('rezultati GREŠKA: ' + String(e.message).split('\n')[0]); }   // greška kod rezultata ne sme da zaustavi kvote
  const razmakMin = razmak(st.pocetci, sada);
  const vremeJe = (k) => {
    const b = st.knjige[k] || {};
    if (samo.length) return samo.includes(k);
    if (ODMAH) return true;
    const cekaj = (b.greske || 0) >= POSLE_GRESAKA ? PAUZA_GRESKE : razmakMin;
    return !b.pokusano || sada - b.pokusano >= (cekaj - 2) * MIN;   // 2 min rezerve da kašnjenje okidača ne preskoči takt
  };
  const red = KNJIGE.filter(([k]) => vremeJe(k));
  if (!red.length) return;

  if (fs.existsSync(BRAVA) && sada - fs.statSync(BRAVA).mtimeMs < ROK_BRAVE) return log('prethodno pokretanje još traje, preskačem');
  fs.writeFileSync(BRAVA, String(process.pid));
  let ctx;
  try {
    // Playwright 1.48 sam traži --headless=old, koji noviji Chrome više nema; Edge se na ovom računaru gasi pri pokretanju
    ctx = await chromium.launchPersistentContext(PROFIL, { channel: 'chrome', headless: false, args: ['--headless=new'] });
    for (const [k, fajl, url] of red) {
      const b = st.knjige[k] = st.knjige[k] || {}, t0 = Date.now();
      b.pokusano = t0;
      try {
        const p = await pokreni(ctx, url, fs.readFileSync(path.join(SISTEM, 'snippets', fajl), 'utf8'));
        if (k === 'mb' && p.games?.length) st.pocetci = p.games.map(g => g[2]).filter(Boolean);
        const ocena = oceni(k, p, st.knjige, st.pocetci, t0), n = brojIgraca(p), l = lokalno(new Date(t0));
        const dan = `${l.year}-${l.month}-${l.day}`, ime = `${k}_${l.hour}${l.minute}.json`;
        if (ocena !== 'prazno') pisi(path.join(IZLAZ, dan, ocena === 'sumnjivo' ? 'sumnjivo' : '', ime), JSON.stringify(p));
        b.greske = 0; b.ocena = ocena; delete b.poruka;
        if (ocena === 'ok') { b.n = n; b.t = t0; }
        // pred meč prazna ponuda više nije normalna: verovatno zastareo ID lige ili promenjen API
        const skoro = st.pocetci.some(t => t > t0 && t - t0 <= POZIV_PRAZNO * MIN);
        const upoz = !n && skoro ? ' UPOZORENJE: nema igrača, a utakmica uskoro počinje' : '';
        log(`${k} ${ocena} igrača=${n} ${Math.round((Date.now() - t0) / 1000)}s${upoz}`);
      } catch (e) {
        b.greske = (b.greske || 0) + 1; b.poruka = String(e.message).slice(0, 200);
        log(`${k} GREŠKA #${b.greske}: ${b.poruka}`);
      }
      pisi(STANJE, JSON.stringify(st, null, 1));
    }
  } finally {
    if (ctx) await ctx.close().catch(() => {});
    fs.rmSync(BRAVA, { force: true });
  }
}

if (require.main === module) main().catch(e => { log('PAD: ' + e.message.split('\n')[0]); process.exitCode = 1; });
module.exports = { razmak, oceni };
