// Zvaničan izveštaj o povredama Evrolige za kolo KOLO (klubovi ga šalju i ažuriraju do dana utakmice).
// Pokrenuti na www.euroleaguebasketball.net. Vraća čist tekst članka (timovi, ko je van, upitan, vraća se).
const KOLO = 10;
// lista vesti se iscrtava u pregledaču, pa se probaju poznati oblici adrese (sajt ih menja), zatim linkovi sa stranice
const GOD = String(new Date().getFullYear());
const kand = ['-fantasy', '-el2627', ''].map(x => `/en/euroleague/news/injury-report-round-${KOLO}${x}/`)
  .concat([...document.querySelectorAll('a')].map(a => a.pathname).filter(p => new RegExp(`injury-report-round-${KOLO}\\b`).test(p)));
let url = null;
for (const u of kand) { const r = await fetch(u); if (r.ok && !r.url.includes('/404') && (await r.text()).includes(GOD)) { url = u; break; } }   // samo članak iz ove sezone
let tekst = null, naslov = null;
if (url) {
  const h = await (await fetch(url)).text();
  const d = new DOMParser().parseFromString(h, 'text/html');
  naslov = (d.querySelector('h1') || {}).textContent;
  tekst = (d.querySelector('main') || d.body).textContent.replace(/\s{2,}/g, ' ').slice(0, 20000);
}
JSON.stringify({url, naslov, tekst});
