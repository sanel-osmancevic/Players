// Lokalna aplikacija: služi dashboard na http://localhost:8765 i na dugme Osveži redom povlači kvote, preračunava i šalje na GitHub.
// Sluša samo na ovom računaru, a API prima zahteve samo sa ove stranice. Fajlovi van sajta (profil pregledača, .git) se ne služe.
// Upotreba: node app_server.js   (pokreni_aplikaciju.vbs ga diže u pozadini i otvara pregledač)
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..'), SISTEM = path.join(ROOT, 'sistem'), PRIK = path.join(SISTEM, 'prikupljeno');
const PORT = +process.env.PORT || 8765, MIN = 60000;
const BRAVA = path.join(PRIK, '.osvezi_traje'), DNEVNIK = path.join(PRIK, 'app.log');
const SVEZ_SNIMAK = 15 * MIN, STARI_STATUSI = 6 * 60 * MIN, PRAZAN_HOD = 6 * 60 * MIN;
const NAZIV = { mb: 'Maxbet', sb: 'Soccer', mk: 'Merkur', mz: 'Mozzart', md: 'Meridian', sx: 'Stoiximan' };
const TIP = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
const SAJT = /^\/(index\.html|manifest\.webmanifest|ikona[-\w]*\.(svg|png)|data\/[\w-]+\.json)$/;
const DOZVOLJEN = new Set([`localhost:${PORT}`, `127.0.0.1:${PORT}`]);

let posao = null, zadnjiZahtev = Date.now();
const log = m => { try { fs.mkdirSync(PRIK, { recursive: true }); fs.appendFileSync(DNEVNIK, `${new Date().toISOString()} ${m}\n`); } catch {} };
const citaj = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };

function pokreni(cmd, args, cwd, rok) {
  return new Promise(res => {
    let izlaz = '', gotovo = false;
    const p = spawn(cmd, args, { cwd, windowsHide: true, env: { ...process.env, GIT_TERMINAL_PROMPT: '0', PYTHONUTF8: '1' } });
    const t = setTimeout(() => { izlaz += '\nisteklo vreme'; p.kill(); }, rok);
    const kraj = code => { if (gotovo) return; gotovo = true; clearTimeout(t); res({ code, izlaz }); };
    p.stdout.on('data', d => izlaz += d); p.stderr.on('data', d => izlaz += d);
    p.on('error', e => { izlaz += String(e.message); kraj(-1); }); p.on('close', kraj);
  });
}
const posl = (s, n = 3) => s.trim().split('\n').slice(-n).join(' | ').slice(0, 400);

// Najnoviji Maxbet snimak servisa: da li je svež i ima li igrače
function maxbetSnimak(od) {
  let naj = null;
  for (const d of fs.existsSync(PRIK) ? fs.readdirSync(PRIK) : []) {
    if (!/^\d{4}-\d\d-\d\d$/.test(d)) continue;
    for (const f of fs.readdirSync(path.join(PRIK, d))) {
      if (!/^mb_.*\.json$/.test(f)) continue;
      const s = citaj(path.join(PRIK, d, f), null);
      if (s && (!naj || s.t > naj.t)) naj = s;
    }
  }
  if (!naj || Date.parse(naj.t) < od - SVEZ_SNIMAK) return { ima: false, igraca: 0 };
  return { ima: true, igraca: Object.keys(naj.raw || {}).length };
}

function informacije() {
  const sada = Date.now(), s = path.join(SISTEM, 'statusi.json');
  const statusi = fs.existsSync(s) ? fs.statSync(s).mtimeMs : null;
  const k = citaj(path.join(SISTEM, 'kolo.json'), { games: [] });
  const uskoro = k.games.filter(g => { const t = Date.parse(g[3]); return t > sada && t - sada <= 60 * MIN; }).map(g => g[2]);
  return { statusiStari: !statusi || sada - statusi > STARI_STATUSI, statusiVreme: statusi, uskoro };
}

async function osvezi() {
  const start = Date.now();
  posao = { radi: true, pocetak: start, koraci: [], ishod: null, greska: null };
  const korak = naziv => { const k = { naziv, status: 'radi', poruka: '' }; posao.koraci.push(k); return k; };
  const zavrsi = (k, status, poruka = '') => { k.status = status; k.poruka = poruka; log(`${k.naziv}: ${status} ${poruka}`); };
  try {
    fs.mkdirSync(PRIK, { recursive: true }); fs.writeFileSync(BRAVA, String(process.pid));
    // 1) kvote
    if (!process.env.EVRO_BEZ_KVOTA) {   // samo za probe
      const k = korak('Kvote');
      const r = await pokreni(process.execPath, ['kvote_servis.js', '--klik'], __dirname, 15 * MIN);
      const st = citaj(path.join(PRIK, 'stanje.json'), { knjige: {} }).knjige;
      const opis = Object.entries(NAZIV).map(([q, n]) => { const b = st[q] || {};
        return b.pokusano >= start ? `${n}: ${b.greske ? 'nije uspelo' : (b.n || 0) + ' igrača'}` : `${n}: ${(b.greske || 0) >= 3 ? 'preskočeno (blokira)' : 'nedavno osveženo'}`; }).join(', ');
      if (r.code) zavrsi(k, 'greska', posl(r.izlaz)); else zavrsi(k, 'ok', opis);
    }
    // 2) preračun
    const k2 = korak('Preračun');
    const mb = maxbetSnimak(start);
    if (!mb.ima || !mb.igraca) zavrsi(k2, 'preskoceno', 'Maxbet još nema igrače u ponudi, pa preporuke ostaju iste');
    else {
      const r = await pokreni('py', ['-X', 'utf8', 'osvezi.py'], SISTEM, 10 * MIN);
      if (r.code) { zavrsi(k2, 'greska', posl(r.izlaz)); posao.greska = 'Preračun nije uspeo, pa ništa nije poslato na GitHub.'; return; }
      zavrsi(k2, 'ok', r.izlaz.split('\n').find(l => l.startsWith('Zapamćena')) || 'gotovo');
    }
    // 3) GitHub: samo podaci; izmene koda idu posebno, sa svojim opisom
    const k3 = korak('GitHub');
    await pokreni('git', ['add', '-A', '--', 'data', 'sistem', ...['py', 'js', 'html', 'md', 'vbs', 'ps1'].map(e => `:(exclude,glob)**/*.${e}`)], ROOT, 2 * MIN);
    const bez = await pokreni('git', ['diff', '--cached', '--quiet'], ROOT, MIN);
    if (bez.code !== 0) {
      const d = new Date(), t = new Intl.DateTimeFormat('sr-RS', { timeZone: 'Europe/Belgrade', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(d);
      const c = await pokreni('git', ['commit', '-q', '-m', `Podaci ${t}`], ROOT, 2 * MIN);
      if (c.code) { zavrsi(k3, 'greska', posl(c.izlaz)); posao.greska = 'Podaci su osveženi lokalno, ali commit nije uspeo.'; return; }
    }
    // šalje se i ono što je ranije ostalo neposlato (npr. kad veza nije radila)
    const ceka = await pokreni('git', ['rev-list', '--count', 'origin/main..HEAD'], ROOT, MIN);
    if (ceka.code === 0 && ceka.izlaz.trim() === '0') zavrsi(k3, 'preskoceno', 'nema novih podataka za slanje');
    else {
      let p;
      for (let i = 0; i < 3; i++) { p = await pokreni('git', ['push', 'origin', 'main'], ROOT, 2 * MIN); if (!p.code) break; await new Promise(r => setTimeout(r, 15000)); }
      if (p.code) { zavrsi(k3, 'greska', posl(p.izlaz, 2)); posao.greska = 'Podaci su osveženi lokalno, ali slanje na GitHub nije uspelo.'; return; }
      zavrsi(k3, 'ok', 'poslato, sajt se ažurira za oko minut');
    }
    posao.ishod = 'gotovo';
  } catch (e) {
    posao.greska = String(e.message); log('PAD ' + e.message);
  } finally {
    posao.radi = false; posao.kraj = Date.now();
    fs.rmSync(BRAVA, { force: true });
  }
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
      osvezi();
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
