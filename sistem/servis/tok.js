// Tok osvežavanja: kvote, preračun i slanje podataka na GitHub. Koriste ga dugme Osveži (app_server.js) i automatika (tik.js).
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..'), SISTEM = path.join(ROOT, 'sistem'), PRIK = path.join(SISTEM, 'prikupljeno');
const MIN = 60000, SVEZ_SNIMAK = 15 * MIN, ROK_BRAVE = 25 * MIN;
const BRAVA = path.join(PRIK, '.osvezi_traje'), DNEVNIK = path.join(PRIK, 'app.log');
const NAZIV = { mb: 'Maxbet', sb: 'Soccer', mk: 'Merkur', mz: 'Mozzart', md: 'Meridian', sx: 'Stoiximan' };
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

async function osvezi(posao) {
  const start = Date.now();
  // dugme i automatika ne smeju da rade istovremeno
  if (fs.existsSync(BRAVA) && start - fs.statSync(BRAVA).mtimeMs < ROK_BRAVE) { posao.greska = 'Osvežavanje već traje.'; posao.radi = false; posao.kraj = Date.now(); return posao; }
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
  return posao;
}

module.exports = { osvezi, pokreni };
