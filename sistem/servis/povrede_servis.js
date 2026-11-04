// Povrede i sudije za kolo: zvaničan izveštaj Evrolige (klubovi ga pune do dana utakmice), članci Sportanda po utakmici, lista povreda sa Rotowire-a i sudije iz API-ja.
// Upisuje statusi.json (ručni unosi imaju prednost i ostaju) i sudije_kolo.json. Pravilo:
//   klub potvrdio izveštaj > Sportando > izveštaj bez potvrde kluba > Rotowire. Startne petorke nemaju izvor pre utakmice; model ih procenjuje iz istorije.
// Upotreba: node povrede_servis.js [--proba=KOLO]   (proba samo ispisuje, ništa ne upisuje)
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const { chromium } = require('playwright-core');

const SISTEM = path.resolve(__dirname, '..');
const API = 'https://api-live.euroleague.net', SEZONA = 'E2026';
const IME = { RED: 'Crvena zvezda', MUN: 'Bayern', TEL: 'Maccabi TA', PRS: 'Paris', MAD: 'Real Madrid', ULK: 'Fenerbahče', DUB: 'Dubai', HTA: 'Hapoel TA', IST: 'Anadolu Efes', PAN: 'Panathinaikos',
  ZAL: 'Žalgiris', PAR: 'Partizan', ASV: 'ASVEL', BAS: 'Baskonia', OLY: 'Olympiacos', MIL: 'Olimpia Milano', BAR: 'Barcelona', PAM: 'Valencia', VIR: 'Virtus', BES: 'Beşiktaş' };
const OZNAKE = { RED: ['zvezda'], MUN: ['bayern'], TEL: ['maccabi'], PRS: ['paris'], MAD: ['realmadrid'], ULK: ['fenerbahce'], DUB: ['dubai'], HTA: ['hapoel'], IST: ['efes'], PAN: ['panathinaikos'],
  ZAL: ['zalgiris'], PAR: ['partizan'], ASV: ['asvel', 'villeurbanne'], BAS: ['baskonia'], OLY: ['olympiacos'], MIL: ['milan'], BAR: ['barcelona', 'barca'], PAM: ['valencia'], VIR: ['virtus'], BES: ['besiktas'] };
const IZVOR_IZV = 'Zvaničan izveštaj', IZVOR_RW = 'Rotowire', IZVOR_SP = 'Sportando';
const citaj = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const asc = s => s.normalize('NFKD').replace(/[^\x00-\x7f]/g, '').toLowerCase().replace(/'/g, '');
const kljuc = n => asc(n).replace(/\b(iv|iii|jr)\b/g, '').replace(/\b[a-z]\b/g, '').replace(/[^a-z]/g, '');   // isto kao u evidencija.py
const tim = s => { const g = asc(s).replace(/[^a-z]/g, ''); return Object.keys(OZNAKE).find(k => OZNAKE[k].some(x => g.includes(x))) || null; };

// Igrači po timu: iz statistike i poslednjih poznatih statusa
function igraci() {
  const sta = citaj(path.join(SISTEM, 'statistika.json'), { P: [] }), ex = citaj(path.join(SISTEM, 'extras.json'), { status: {} });
  const po = {}, dodaj = (n, t) => {
    const [l, f = ''] = n.split(/\s*,\s*/); (po[t] = po[t] || new Map()).set(n, { id: `${n}|${t}`, puno: kljuc(f + ' ' + l), prezime: kljuc(l) });
  };
  for (const p of sta.P) dodaj(p[0], p[2]);
  for (const k of Object.keys(ex.status)) { const [n, t] = k.split('|'); dodaj(n, t); }
  return po;
}
// Koji igrači tima se pominju u rečenici: puno ime, pa jedinstveno prezime (npr. "Nate Reuvers" za REUVERS, NATHAN)
function pomenuti(rec, lista) {
  const sve = kljuc(rec), reci = new Set(asc(rec).split(/[^a-z]+/)), nadjeni = [];
  for (const p of lista) if (sve.includes(p.puno)) nadjeni.push(p);
  for (const p of lista) {
    if (nadjeni.includes(p) || p.prezime.length < 4 || !reci.has(p.prezime)) continue;
    if (lista.filter(x => x.prezime === p.prezime).length === 1) nadjeni.push(p);
  }
  return nadjeni;
}
// Šta rečenica kaže o trenutnom stanju igrača; null ako je samo istorija
function oceniRecenicu(r, potvrdio) {
  const s = r.toLowerCase();
  // prošlost nije današnje stanje: kod kluba koji je potvrdio izveštaj ne znači ništa, a bez potvrde je znak da je upitan
  if (/\b(was|were)( both| all)? (questionable|ruled out|doubtful)\b/.test(s)) return potvrdio ? null : 'Upitan';
  if (/game[- ]?time decision|questionable|doubtful|\bdoubt\b|\bgtd\b|day-to-day|uncertain|expected to (be )?(sidelined )?until/.test(s)) return 'Upitan';
  if (/until (early|mid|late)?\s*(january|february|march|april|may|june|july|august|september|october|november|december)/.test(s)) return 'Upitan';
  if (/yet to play.*\bbut\b/.test(s)) return 'Upitan';
  if (/returned|has recovered|made his/.test(s)) return null;
  if (/not available|ruled out|only absentee|absentees?\b|will miss|\b(is|are) out\b|remains? (sidelined|out)|sidelined|yet to play|surgery|out indefinitely|expected to miss|will not play|won't play/.test(s)) return 'Ne igra';
  if (/\bwas available\b/.test(s)) return null;
  if (/\b(is|are) available\b|will play|\bcleared\b|\bis back\b/.test(s)) return 'Igra';
  if (!potvrdio && /did not play|not on the gameday roster|last played|did not make/.test(s)) return 'Upitan';
  // sveža povreda, a klub još nije javio stanje
  if (!potvrdio && /dealing with|suffer|sprain|ruptur|strain|fractur|\binjur|missed round/.test(s)) return 'Upitan';
  return null;
}
function citajIzvestaj(tekst, po) {
  const L = tekst.split('\n').map(x => x.trim()).filter(Boolean), kraj = L.indexOf('Share this');
  const red = kraj > 0 ? L.slice(0, kraj) : L, zag = /\bvs\.\s.+\(\d\d:\d\d\s*CET\)$/;
  const timovi = {};   // kod -> {potvrdio, statusi, nepoznati}
  let par = null, t = null, prva = false;
  for (const l of red) {
    if (zag.test(l)) { const [a, b] = l.replace(/\(.*$/, '').split(/\bvs\.\s/); par = [tim(a), tim(b)]; t = null; continue; }
    if (!par) continue;
    if (l.length < 28 && !/[.!]$/.test(l) && par.includes(tim(l))) { t = tim(l); timovi[t] = { potvrdio: false, pun: false, statusi: {} }; prva = true; continue; }
    if (!t) continue;
    const T = timovi[t], lista = [...(po[t] || new Map()).values()];
    if (prva) { prva = false; T.potvrdio = !/not yet sent/i.test(l); T.pun = /full roster|no (new )?injur|everyone (is )?available/i.test(l); }
    // "X je upitan, while Y is ruled out": svaki deo ima svoje igrače i svoje stanje
    for (const rec of l.split(/(?<=[a-z)\d]{2}\.)\s+(?=[A-Z])|\s+while\s+/)) {
      const o = oceniRecenicu(rec, T.potvrdio);
      if (o) for (const p of pomenuti(rec, lista)) if (!T.statusi[p.id]) T.statusi[p.id] = [o, rec.slice(0, 110)];
    }
  }
  return timovi;
}
// Izveštaj ima isti naslov svake sezone: tekuće kolo prepoznajemo po datumima utakmica, a stranica datum objave piše kao "About 3 hours ago"
function svezIzvestaj(t, kolo) {
  const K = citaj(path.join(SISTEM, 'kolo.json'), {});
  if (K.kolo !== kolo) return /\bago\b/.test(t) || t.includes(String(new Date().getFullYear()));
  const dan = new Intl.DateTimeFormat('en-US', { timeZone: 'Europe/Belgrade', month: 'long', day: 'numeric' });
  return K.games.some(g => t.includes(dan.format(new Date(g[3]))));
}
// Članci "A vs B injury report" sa Sportanda za utakmice tekućeg kola; neuspeh ne zaustavlja ostale izvore
// Ide preko curl-a jer Node ovde ne može da otvori HTTPS (NODE_USE_SYSTEM_CA)
const web = u => execFileSync('curl', ['-s', '-f', '-L', '--max-time', '20', u], { encoding: 'utf8', maxBuffer: 2e7 });
function clanciSportando(kolo) {
  const K = citaj(path.join(SISTEM, 'kolo.json'), {}), out = [];
  if (K.kolo !== kolo) return out;
  for (const [, it] of web('https://sportando.basketball/en/search/injury+report/feed/rss2/').matchAll(/<item>([\s\S]*?)<\/item>/g)) {
    const polje = n => (it.match(new RegExp(`<${n}>(?:<!\\[CDATA\\[)?([\\s\\S]*?)(?:\\]\\]>)?</${n}>`)) || [])[1] || '';
    const m = polje('title').match(/^(.+?)\s+vs\.?\s+(.+?)\s+injury report/i);
    if (!m || Date.now() - Date.parse(polje('pubDate')) > 4 * 864e5) continue;
    const a = tim(m[1]), b = tim(m[2]);
    if (!K.games.some(g => (g[0] === a && g[1] === b) || (g[0] === b && g[1] === a))) continue;
    try { out.push({ par: [a, b], html: web(polje('link').trim()) }); } catch {}
  }
  return out;
}
// Iz teksta članka uzima samo jasne izjave; "pridružio se listi povređenih" i slično se ne računa
function citajSportando(clanci, po, rw) {
  const out = {}, jacina = { Igra: 1, Upitan: 2, 'Ne igra': 3 };
  for (const { par, html } of clanci) {
    const lista = par.flatMap(t => [...(po[t] || new Map()).values()]);
    const od = Math.max(0, html.indexOf('<article')), do_ = html.indexOf('Leggi anche', od), telo = html.slice(od, do_ < 0 ? undefined : do_);
    for (const [, p] of telo.matchAll(/<p(?:\s[^>]*)?>([\s\S]*?)<\/p>/g)) {
      const tekst = p.replace(/<[^>]+>/g, '').replace(/&#8217;|&rsquo;/g, "'").replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&');
      for (const rec of tekst.split(/(?<=[A-Za-z)\d]\.)\s+(?=[A-Z])|\s+while\s+|;\s+/)) {
        const s = rec.toLowerCase();
        const o = /will be without|\b(is|are) out\b|ruled out|will miss|did not travel|sidelined/.test(s) ? 'Ne igra'
          : /doubtful|questionable|game[- ]time|uncertain/.test(s) ? 'Upitan'
          : /expected (to be available|back)|will play|\b(is|are) available\b|\bcleared\b/.test(s) ? 'Igra' : null;
        if (!o) continue;
        const nadjeni = pomenuti(rec, lista);
        if (o === 'Igra' && nadjeni.length !== 1) continue;   // "igra" važi samo ako je jasno na koga se odnosi
        for (const x of nadjeni) {
          const st = o === 'Igra' && rw[x.id]?.[0] === 'Ne igra' ? 'Upitan' : o;
          if (!out[x.id] || jacina[st] > jacina[out[x.id][0]]) out[x.id] = [st, rec.slice(0, 110)];
        }
      }
    }
  }
  return out;
}
async function preuzmi(kolo) {
  const b = await chromium.launch({ channel: 'chrome', headless: false, args: ['--headless=new'] });
  try {
    const c = await b.newContext(), p = await c.newPage(), out = { izvestaj: null, url: null, rotowire: null };
    for (const x of ['-fantasy', '-el2627', '']) {
      const u = `https://www.euroleaguebasketball.net/en/euroleague/news/injury-report-round-${kolo}${x}/`;
      const r = await p.goto(u, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => null);
      if (!r || !r.ok()) continue;
      await p.waitForTimeout(2500);
      const t = await p.evaluate(() => (document.querySelector('main') || document.body).innerText);
      if (new RegExp(`Injury report, Round ${kolo}\\b`, 'i').test(t) && svezIzvestaj(t, kolo)) { out.izvestaj = t; out.url = u; break; }
    }
    const r = await p.goto('https://www.rotowire.com/euro/injury-report.php', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => null);
    if (r && r.ok()) {
      await p.waitForSelector('.webix_column', { timeout: 15000 }).catch(() => {});
      // tabela je po kolonama: igrač, tim, pozicija, povreda, status
      const k = await p.evaluate(() => [...document.querySelectorAll('.webix_ss_left .webix_column, .webix_ss_center .webix_column')].map(c => [...c.querySelectorAll('.webix_cell')].map(x => x.innerText.trim())));
      if (k.length >= 5 && k[0].length) out.rotowire = k[0].map((n, i) => ({ ime: n, povreda: k[3][i], status: k[4][i] }));
    }
    return out;
  } finally { await b.close(); }
}
function saRotowirea(rw, po) {
  const svi = Object.values(po).flatMap(m => [...m.values()]), out = {};
  for (const x of rw) {
    const k = kljuc(x.ime), nadjen = svi.filter(p => p.puno === k);
    const p = nadjen.length === 1 ? nadjen[0] : null; if (!p) continue;
    out[p.id] = [/^out/i.test(x.status) ? 'Ne igra' : 'Upitan', `${x.povreda || 'povreda'}`];
  }
  return out;
}
const curl = u => JSON.parse(execFileSync('curl', ['-s', '-f', '--max-time', '20', API + u], { encoding: 'utf8', maxBuffer: 2e7 }));
function sudije(kolo) {
  const idx = citaj(path.join(SISTEM, 'sudije.json'), { sudije: {} }).sudije, out = {};
  for (const g of curl(`/v2/competitions/E/seasons/${SEZONA}/games?roundNumber=${kolo}`).data) {
    const s = [g.referee1, g.referee2, g.referee3].filter(Boolean).map(r => r.name); if (!s.length) continue;
    const v = s.map(n => idx[n] || [0, 1, 1]), pr = i => +(v.reduce((a, x) => a + x[i], 0) / v.length).toFixed(3);
    out[`${IME[g.local.club.code]} – ${IME[g.road.club.code]}`] = [s, pr(1), pr(2)];
  }
  return out;
}
const sada = () => new Intl.DateTimeFormat('sr-RS', { timeZone: 'Europe/Belgrade', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date());

async function main() {
  const a = process.argv.find(x => x.startsWith('--proba=')), proba = a ? +a.slice(8) : null;
  const kolo = proba || citaj(path.join(SISTEM, 'kolo.json'), {}).kolo;
  const po = igraci(), { izvestaj, url, rotowire } = await preuzmi(kolo);
  const timovi = izvestaj ? citajIzvestaj(izvestaj, po) : {};
  const rw = rotowire ? saRotowirea(rotowire, po) : {};
  let sportando = null; try { sportando = clanciSportando(kolo); } catch {}
  const sp = sportando ? citajSportando(sportando, po, rw) : {};
  if (!izvestaj && !rotowire) throw new Error('ni izveštaj ni Rotowire nisu dostupni');
  if (proba) {
    console.log('izveštaj', url, 'Rotowire', rotowire ? rotowire.length : null, 'povezano', Object.keys(rw).length, 'Sportando članaka', sportando ? sportando.length : null);
    for (const [k, v] of Object.entries(sp)) console.log('  Sportando', k, '=>', v[0], '|', v[1]);
    for (const [t, T] of Object.entries(timovi)) { console.log(`${t} potvrdio=${T.potvrdio} pun=${T.pun}`); for (const [k, v] of Object.entries(T.statusi)) console.log('   ', k.split('|')[0], '=>', v[0], '|', v[1]); }
    return;
  }
  const f = path.join(SISTEM, 'statusi.json'), stari = citaj(f, {}), vreme = sada();
  const auto = v => v && [IZVOR_IZV, IZVOR_RW, IZVOR_SP].some(i => (v[1] || '').startsWith(i));
  const ex = citaj(path.join(SISTEM, 'extras.json'), { status: {} }).status, novi = {};
  for (const [k, v] of Object.entries(stari)) if (!auto(v)) novi[k] = v;   // ručni unosi ostaju
  const stavi = (k, st, izv) => { if (!(k in novi) || auto(novi[k])) novi[k] = [st, izv]; };
  for (const [k, v] of Object.entries(rw)) stavi(k, v[0], `${IZVOR_RW} ${vreme}: ${v[1]}`);
  // stari statusi iz extras.json koje nijedan svež izvor više ne potvrđuje
  if (rotowire && rotowire.length >= 10) for (const k of Object.keys(ex)) if (!(k in rw) && !(k in novi)) stavi(k, 'Igra', `${IZVOR_RW} ${vreme}: nije na listi povreda`);
  // redosled je prednost: svaki sledeći izvor ide preko prethodnog
  const potvrdilo = Object.values(timovi).filter(T => T.potvrdio).length;
  const izIzvestaja = potvrdio => { for (const [t, T] of Object.entries(timovi)) {
    if (T.potvrdio !== potvrdio) continue;
    if (T.potvrdio) {
      for (const k of [...Object.keys(ex), ...Object.keys(rw)]) if (k.endsWith('|' + t) && !T.statusi[k]) stavi(k, 'Igra', `${IZVOR_IZV} ${vreme}: klub ga ne navodi`);
    }
    for (const [k, v] of Object.entries(T.statusi)) {
      if (!T.potvrdio && v[0] !== 'Ne igra' && rw[k]?.[0] === 'Ne igra') continue;   // nagađanje iz istorije ne obara potvrđenu povredu
      stavi(k, v[0], `${IZVOR_IZV} ${vreme}: ${v[1]}`);
    }
  } };
  izIzvestaja(false);
  for (const [k, v] of Object.entries(sp)) stavi(k, v[0], `${IZVOR_SP} ${vreme}: ${v[1]}`);
  izIzvestaja(true);
  fs.writeFileSync(f + '.tmp', JSON.stringify(novi, null, 0)); fs.renameSync(f + '.tmp', f);
  let sud = {}; try { sud = sudije(kolo); fs.writeFileSync(path.join(SISTEM, 'sudije_kolo.json'), JSON.stringify(sud)); } catch {}
  const br = s => Object.values(novi).filter(v => v[0] === s).length;
  console.log(`${izvestaj ? `Izveštaj ${kolo}. kola: potvrdilo ${potvrdilo} od ${Object.keys(timovi).length} klubova` : `Izveštaj ${kolo}. kola još nije objavljen`}; Sportando: ${sportando ? sportando.length + ' članaka' : 'nije dostupan'}; Rotowire: ${rotowire ? rotowire.length + ' igrača' : 'nije dostupan'}; Ne igra ${br('Ne igra')}, Upitan ${br('Upitan')}; sudije za ${Object.keys(sud).length} utakmica`);
}
if (require.main === module) main().catch(e => { console.error('GREŠKA ' + String(e.message).split('\n')[0]); process.exitCode = 1; });
