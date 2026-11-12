// Maxbet: sve linije igrača i kvote utakmica Evrolige. Pokrenuti na www.maxbet.rs (isto što i fetch_direct u osvezi.py).
// Vraća {t, n, raw: {"Igrač|Tim": [[kat, linija, više, manje], [kat, linija, više]]}, games: [[domaćin, gost, početak_ms, hdp, ukupno, k1, k2]]}
const Q = '?annex=3&mobileVersion=1.21.18&locale=sr', BASE = '/restapi/offer/sr';
const get = async p => { const r = await fetch(BASE + p + Q); if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + p); return r.json(); };
const sve = async (ids, n = 4) => {   // najviše n istovremenih zahteva; svaka greška obara ceo snimak (nema delimičnih)
  const out = []; let i = 0;
  await Promise.all(Array.from({length: n}, async () => { while (i < ids.length) { const j = i++; out[j] = await get('/match/' + ids[j]); } }));
  return out;
};
const lst = (await get('/sport/SK/league/194042/mob')).esMatches || [];
const raw = {};
for (const d of await sve(lst.map(m => m.id))) {
  const o = d.odds || {}, p = d.params || {}, a = raw[d.home + '|' + d.away] = raw[d.home + '|' + d.away] || [];
  const add = (c, L, ov, un) => { if (L != null && (ov != null || un != null)) a.push([c, parseFloat(L), ov ?? null, un ?? null]); };
  add('P', p.ouPlPoints, o[51679], o[51681]);
  add('P', p.ouPlP2, o[55253], o[55255]);
  add('P', p.ouPlP3, o[55256], o[55258]);
  for (const [c, x] of [[54096, 5], [54101, 10], [54106, 15], [54111, 20], [54116, 25], [54121, 30], [54126, 35]])
    if (o[c]) a.push(['P', x - 0.5, o[c]]);
  add('S', p.ouPlRebounds, o[51685], o[51687]);
  add('A', p.ouPlAssists, o[51682], o[51684]);
}
const gl = (await get('/sport/B/league/131600/mob')).esMatches || [];
const games = (await sve(gl.map(m => m.id))).map(d => [d.home, d.away, d.kickOffTime, (d.params || {}).hdp, ((d.params || {}).overUnder ?? (d.params || {}).overUnderOvertime), (d.odds || {})[1], (d.odds || {})[3]]);   // od 6.11.2026. Maxbet šalje ukupno kao overUnderOvertime (sa produžecima)
JSON.stringify({t: new Date().toISOString(), n: lst.length, raw, games});
