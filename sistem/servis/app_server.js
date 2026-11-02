// Lokalna aplikacija: služi dashboard na http://localhost:8765 i na dugme Osveži redom povlači kvote i povrede, preračunava i šalje na GitHub.
// Sluša samo na ovom računaru; telefon samo gleda objavljeni sajt. API prima zahteve samo sa ove stranice. Fajlovi van sajta (profil pregledača, .git) se ne služe.
// Upotreba: node app_server.js   (pokreni_aplikaciju.vbs ga diže u pozadini i otvara pregledač)
const http = require('http'), fs = require('fs'), path = require('path'), { osvezi, posaljiPodatke } = require('./tok');

const ROOT = path.resolve(__dirname, '..', '..'), SISTEM = path.join(ROOT, 'sistem'), PRIK = path.join(SISTEM, 'prikupljeno');
const ZAP = path.join(SISTEM, 'zapamceno.json');
const PORT = +process.env.PORT || 8765, MIN = 60000;
const DNEVNIK = path.join(PRIK, 'app.log');
const STARI_STATUSI = 6 * 60 * MIN, PRAZAN_HOD = 6 * 60 * MIN;
const TIP = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
const SAJT = /^\/(index\.html|manifest\.webmanifest|ikona[-\w]*\.(svg|png)|data\/[\w-]+\.json)$/;
const DOZVOLJEN = new Set([`localhost:${PORT}`, `127.0.0.1:${PORT}`]);

const POSLE_KLIKA = 30000;   // više klikova zaredom ide na sajt zajedno
let posao = null, zadnjiZahtev = Date.now(), tajmerSlanja = null;
const log = m => { try { fs.mkdirSync(PRIK, { recursive: true }); fs.appendFileSync(DNEVNIK, `${new Date().toISOString()} ${m}\n`); } catch {} };
const citaj = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };

function informacije() {
  const sada = Date.now(), s = path.join(SISTEM, 'statusi.json');
  const statusi = fs.existsSync(s) ? fs.statSync(s).mtimeMs : null;
  const k = citaj(path.join(SISTEM, 'kolo.json'), { games: [] });
  const uskoro = k.games.filter(g => { const t = Date.parse(g[3]); return t > sada && t - sada <= 60 * MIN; }).map(g => g[2]);
  return { statusiStari: !statusi || sada - statusi > STARI_STATUSI, statusiVreme: statusi, uskoro, auto: citaj(path.join(PRIK, 'auto.json'), null) };
}

// Dugme Odigrano: opklada zadržava granicu i kvotu pri svakom sledećem preračunu (osvezi.py), a oznaka ide na sajt, da se vidi i na telefonu.
function zakaziSlanje() {
  clearTimeout(tajmerSlanja);
  tajmerSlanja = setTimeout(async () => {
    tajmerSlanja = null;
    if (posao?.radi || fs.existsSync(path.join(PRIK, '.osvezi_traje'))) return zakaziSlanje();   // tok će svakako poslati ili oslobađa git
    const g = await posaljiPodatke('Odigrano').catch(e => ({ status: 'greska', poruka: String(e.message) }));
    log(`slanje oznaka: ${g.status} ${g.poruka}`);
  }, POSLE_KLIKA);
}
function odigrano({ kolo, kljuc, opklada, odigrano: da }) {
  if (posao?.radi || fs.existsSync(path.join(PRIK, '.osvezi_traje'))) return [409, 'Osvežavanje je u toku, pokušaj za minut.'];
  const redovi = JSON.parse(fs.readFileSync(ZAP, 'utf8'));
  const r = redovi.find(x => x.igrac && +x.kolo === +kolo && x.kljuc === kljuc && x.opklada === opklada);
  if (!r) return [404, 'Opklada nije u zapamćenoj listi.'];
  if (r.ishod) return [409, 'Opklada je već završena.'];
  if (da) r.odigrano = true; else delete r.odigrano;
  const s = JSON.stringify(redovi);
  fs.writeFileSync(ZAP + '.tmp', s); fs.renameSync(ZAP + '.tmp', ZAP);
  fs.writeFileSync(path.join(ROOT, 'data', 'zapamceno.json'), s);
  // novo v: telefon inače može da zadrži staru kopiju podataka
  const m = path.join(ROOT, 'data', 'meta.json');
  fs.writeFileSync(m, JSON.stringify({ ...citaj(m, {}), v: Math.floor(Date.now() / 1000) }));
  zakaziSlanje();
  log(`odigrano ${da ? 'da' : 'ne'}: ${kljuc} ${opklada}`);
  return [200, 'ok'];
}
function posalji(res, kod, tip, telo) { res.writeHead(kod, { 'content-type': tip, 'cache-control': 'no-store' }); res.end(telo); }
const json = (res, kod, o) => posalji(res, kod, 'application/json', JSON.stringify(o));

function obrada(q, res) {
  zadnjiZahtev = Date.now();
  let u; try { u = decodeURIComponent(q.url.split('?')[0]); } catch { return posalji(res, 400, 'text/plain', 'loš zahtev'); }
  if (u === '/') u = '/index.html';
  if (u.startsWith('/api/')) {
    // druga stranica ne sme da pokrene osvežavanje ili čita stanje preko pregledača
    const izvor = q.headers.origin;
    if (!DOZVOLJEN.has(q.headers.host) || (izvor && !DOZVOLJEN.has(izvor.replace(/^http:\/\//, '')))) return json(res, 403, { greska: 'nije dozvoljeno' });
    if (u === '/api/stanje' && q.method === 'GET') return json(res, 200, { posao, ...informacije() });
    if (u === '/api/osvezi' && q.method === 'POST') {
      if (!izvor) return json(res, 403, { greska: 'nije dozvoljeno' });
      if (posao?.radi) return json(res, 409, { greska: 'osvežavanje već traje' });
      posao = { radi: true, pocetak: Date.now(), koraci: [], ishod: null, greska: null };
      osvezi(posao).catch(e => { posao.greska = String(e.message); posao.radi = false; });
      return json(res, 202, { posao });
    }
    if (u === '/api/odigrano' && q.method === 'POST') {
      if (!izvor) return json(res, 403, { greska: 'nije dozvoljeno' });
      let telo = '';
      q.on('data', d => { telo += d; if (telo.length > 2000) q.destroy(); });
      q.on('end', () => {
        try { const [kod, poruka] = odigrano(JSON.parse(telo)); json(res, kod, kod === 200 ? { ok: true } : { greska: poruka }); }
        catch (e) { json(res, 400, { greska: 'loš zahtev' }); }
      });
      return;
    }
    return json(res, 404, { greska: 'nema' });
  }
  if (q.method !== 'GET' || !SAJT.test(u)) return posalji(res, 404, 'text/plain', 'nema');
  fs.readFile(path.join(ROOT, u), (e, d) => e ? posalji(res, 404, 'text/plain', 'nema') : posalji(res, 200, TIP[path.extname(u)] || 'application/octet-stream', d));
}
if (require.main === module) {
  const server = http.createServer(obrada);
  server.on('error', e => { if (e.code === 'EADDRINUSE') process.exit(0); throw e; });   // već radi
  server.listen(PORT, '127.0.0.1', () => log('server pokrenut'));
  // bez otvorene aplikacije server se sam gasi
  setInterval(() => { if (!posao?.radi && !tajmerSlanja && Date.now() - zadnjiZahtev > PRAZAN_HOD) process.exit(0); }, MIN);
}
