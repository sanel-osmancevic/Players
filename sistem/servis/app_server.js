// Lokalna aplikacija: služi dashboard na http://localhost:8765 i na dugme Osveži redom povlači kvote i povrede, preračunava i šalje na GitHub.
// Sluša samo na ovom računaru, a API prima zahteve samo sa ove stranice. Fajlovi van sajta (profil pregledača, .git) se ne služe.
// Upotreba: node app_server.js   (pokreni_aplikaciju.vbs ga diže u pozadini i otvara pregledač)
const http = require('http'), fs = require('fs'), path = require('path'), { osvezi } = require('./tok');

const ROOT = path.resolve(__dirname, '..', '..'), SISTEM = path.join(ROOT, 'sistem'), PRIK = path.join(SISTEM, 'prikupljeno');
const PORT = +process.env.PORT || 8765, MIN = 60000;
const DNEVNIK = path.join(PRIK, 'app.log');
const STARI_STATUSI = 6 * 60 * MIN, PRAZAN_HOD = 6 * 60 * MIN;
const TIP = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
const SAJT = /^\/(index\.html|manifest\.webmanifest|ikona[-\w]*\.(svg|png)|data\/[\w-]+\.json)$/;
const DOZVOLJEN = new Set([`localhost:${PORT}`, `127.0.0.1:${PORT}`]);

let posao = null, zadnjiZahtev = Date.now();
const log = m => { try { fs.mkdirSync(PRIK, { recursive: true }); fs.appendFileSync(DNEVNIK, `${new Date().toISOString()} ${m}\n`); } catch {} };
const citaj = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };

function informacije() {
  const sada = Date.now(), s = path.join(SISTEM, 'statusi.json');
  const statusi = fs.existsSync(s) ? fs.statSync(s).mtimeMs : null;
  const k = citaj(path.join(SISTEM, 'kolo.json'), { games: [] });
  const uskoro = k.games.filter(g => { const t = Date.parse(g[3]); return t > sada && t - sada <= 60 * MIN; }).map(g => g[2]);
  return { statusiStari: !statusi || sada - statusi > STARI_STATUSI, statusiVreme: statusi, uskoro, auto: citaj(path.join(PRIK, 'auto.json'), null) };
}

function posalji(res, kod, tip, telo) { res.writeHead(kod, { 'content-type': tip, 'cache-control': 'no-store' }); res.end(telo); }
const json = (res, kod, o) => posalji(res, kod, 'application/json', JSON.stringify(o));

const server = http.createServer((q, res) => {
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
    return json(res, 404, { greska: 'nema' });
  }
  if (q.method !== 'GET' || !SAJT.test(u)) return posalji(res, 404, 'text/plain', 'nema');
  fs.readFile(path.join(ROOT, u), (e, d) => e ? posalji(res, 404, 'text/plain', 'nema') : posalji(res, 200, TIP[path.extname(u)] || 'application/octet-stream', d));
});
server.on('error', e => { if (e.code === 'EADDRINUSE') process.exit(0); throw e; });   // već radi
server.listen(PORT, '127.0.0.1', () => log('server pokrenut'));
// bez otvorene aplikacije server se sam gasi
setInterval(() => { if (!posao?.radi && Date.now() - zadnjiZahtev > PRAZAN_HOD) process.exit(0); }, MIN).unref?.();
