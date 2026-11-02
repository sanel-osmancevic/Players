// Lokalna aplikacija: služi dashboard na http://localhost:8765 i na dugme Osveži redom povlači kvote i povrede, preračunava i šalje na GitHub.
// Sluša na ovom računaru i, ako je Tailscale uključen, na njegovoj privatnoj adresi, da aplikacija radi i sa telefona. Nikad na ostaloj mreži.
// API prima zahteve samo sa ove stranice. Fajlovi van sajta (profil pregledača, .git) se ne služe.
// Upotreba: node app_server.js   (pokreni_aplikaciju.vbs ga diže u pozadini i otvara pregledač)
const http = require('http'), fs = require('fs'), os = require('os'), path = require('path'), { osvezi } = require('./tok');

const ROOT = path.resolve(__dirname, '..', '..'), SISTEM = path.join(ROOT, 'sistem'), PRIK = path.join(SISTEM, 'prikupljeno');
const ZAP = path.join(SISTEM, 'zapamceno.json');
const PORT = +process.env.PORT || 8765, MIN = 60000;
const DNEVNIK = path.join(PRIK, 'app.log');
const STARI_STATUSI = 6 * 60 * MIN, PRAZAN_HOD = 6 * 60 * MIN;
const TIP = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
const SAJT = /^\/(index\.html|manifest\.webmanifest|ikona[-\w]*\.(svg|png)|data\/[\w-]+\.json)$/;
const DOZVOLJEN = new Set([`localhost:${PORT}`, `127.0.0.1:${PORT}`]);

const MAGICDNS = new RegExp(`^[a-z0-9-]+(\\.[a-z0-9-]+)*\\.ts\\.net:${PORT}$`, 'i');
let posao = null, zadnjiZahtev = Date.now(), privatna = null, drugiServer = null;
const dozvoljen = h => DOZVOLJEN.has(h) || (privatna && MAGICDNS.test(h || ''));
// Samo adapter koji se zove Tailscale: slične adrese (100.64.0.0/10) dodeljuju i mobilni operateri, a na toj mreži aplikacija ne sme da se vidi
function tailscaleIP(ifs = os.networkInterfaces()) {
  if (process.env.EVRO_PROBNA_IP) return process.env.EVRO_PROBNA_IP;   // samo za probe
  for (const [ime, adrese] of Object.entries(ifs)) {
    if (!/tailscale/i.test(ime)) continue;
    const a = (adrese || []).find(x => x.family === 'IPv4' && /^100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\./.test(x.address));
    if (a) return a.address;
  }
  return null;
}
const log = m => { try { fs.mkdirSync(PRIK, { recursive: true }); fs.appendFileSync(DNEVNIK, `${new Date().toISOString()} ${m}\n`); } catch {} };
const citaj = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };

function informacije() {
  const sada = Date.now(), s = path.join(SISTEM, 'statusi.json');
  const statusi = fs.existsSync(s) ? fs.statSync(s).mtimeMs : null;
  const k = citaj(path.join(SISTEM, 'kolo.json'), { games: [] });
  const uskoro = k.games.filter(g => { const t = Date.parse(g[3]); return t > sada && t - sada <= 60 * MIN; }).map(g => g[2]);
  return { statusiStari: !statusi || sada - statusi > STARI_STATUSI, statusiVreme: statusi, uskoro, auto: citaj(path.join(PRIK, 'auto.json'), null), telefon: privatna ? `http://${privatna}:${PORT}/` : null };
}

// Dugme Odigrano: opklada zadržava granicu i kvotu pri svakom sledećem preračunu (osvezi.py). Na GitHub ide sa sledećim osvežavanjem.
function odigrano({ kolo, kljuc, opklada, odigrano: da }) {
  if (posao?.radi || fs.existsSync(path.join(PRIK, '.osvezi_traje'))) return [409, 'Osvežavanje je u toku, pokušaj za minut.'];
  const redovi = JSON.parse(fs.readFileSync(ZAP, 'utf8'));
  const r = redovi.find(x => x.igrac && +x.kolo === +kolo && x.kljuc === kljuc && x.opklada === opklada);
  if (!r) return [404, 'Opklada nije u zapamćenoj listi.'];
  if (r.ishod) return [409, 'Opklada je već završena.'];
  if (da) { r.odigrano = true; r.odigrano_kada = new Date().toISOString(); } else { delete r.odigrano; delete r.odigrano_kada; }
  const s = JSON.stringify(redovi);
  fs.writeFileSync(ZAP + '.tmp', s); fs.renameSync(ZAP + '.tmp', ZAP);
  fs.writeFileSync(path.join(ROOT, 'data', 'zapamceno.json'), s);
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
    if (!dozvoljen(q.headers.host) || (izvor && !dozvoljen(izvor.replace(/^http:\/\//, '')))) return json(res, 403, { greska: 'nije dozvoljeno' });
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
// Tailscale može da se uključi i ugasi dok server radi, pa se adresa proverava svakog minuta
function proveriPrivatnu() {
  const ip = tailscaleIP();
  if (ip === privatna) return;
  if (drugiServer) { drugiServer.close(); DOZVOLJEN.delete(`${privatna}:${PORT}`); drugiServer = null; privatna = null; log('privatna adresa ugašena'); }
  if (!ip) return;
  const s = http.createServer(obrada);
  s.on('error', e => log('privatna adresa: ' + e.message));
  s.listen(PORT, ip, () => { drugiServer = s; privatna = ip; DOZVOLJEN.add(`${ip}:${PORT}`); log('privatna adresa ' + ip); });
}
if (require.main === module) {
  const server = http.createServer(obrada);
  server.on('error', e => { if (e.code === 'EADDRINUSE') process.exit(0); throw e; });   // već radi
  server.listen(PORT, '127.0.0.1', () => { log('server pokrenut'); proveriPrivatnu(); setInterval(proveriPrivatnu, MIN); });
  // bez otvorene aplikacije server se sam gasi; Windows zadatak ga ponovo diže
  setInterval(() => { if (!posao?.radi && Date.now() - zadnjiZahtev > PRAZAN_HOD) process.exit(0); }, MIN);
}
module.exports = { tailscaleIP };
