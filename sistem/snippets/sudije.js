// Sudije: koliko faulova i slobodnih bacanja svaki sudija "dosuđuje" u odnosu na prosek (sezone E2025 + E2026).
// Pokrenuti na api-live.euroleague.net. Indeks = prosek (faulovi utakmice / prosek lige) na utakmicama tog sudije,
// skupljeno ka 1 sa K utakmica. Za utakmice kola KOLO sa poznatim sudijama vraća indeks trojke (prosek tri sudije).
const KOLO = 10, K = 15, A = 'https://api-live.euroleague.net';
const J = u => fetch(A + u).then(r => r.json());
const rows = [];
for (const se of ['E2025', 'E2026']) {
  const g = (await J(`/v2/competitions/E/seasons/${se}/games`)).data.filter(x => x.played);
  for (let i = 0; i < g.length; i += 25) {
    await Promise.all(g.slice(i, i + 25).map(async x => {
      try {
        const s = await J(`/v3/competitions/E/seasons/${se}/games/${x.gameCode}/stats`);
        const tot = t => (s[t].total || {}), f = ['local', 'road'].reduce((a, t) => a + (tot(t).foulsCommited || 0), 0),
              fta = ['local', 'road'].reduce((a, t) => a + (tot(t).freeThrowsAttempted || 0), 0);
        const refs = [x.referee1, x.referee2, x.referee3].filter(Boolean).map(r => r.code + '|' + r.name);
        if (f > 0) rows.push([refs, f, fta]);
      } catch (e) {}
    }));
  }
}
const mf = rows.reduce((a, r) => a + r[1], 0) / rows.length, mt = rows.reduce((a, r) => a + r[2], 0) / rows.length;
const R = {};
for (const [refs, f, t] of rows) for (const r of refs) { const o = (R[r] = R[r] || [0, 0, 0]); o[0]++; o[1] += f / mf; o[2] += t / mt; }
const idx = {}; for (const [r, [n, sf, st]] of Object.entries(R)) idx[r] = [n, +((sf + K) / (n + K)).toFixed(3), +((st + K) / (n + K)).toFixed(3)];
const up = (await J(`/v2/competitions/E/seasons/E2026/games?roundNumber=${KOLO}`)).data.map(x => {
  const refs = [x.referee1, x.referee2, x.referee3].filter(Boolean).map(r => r.code + '|' + r.name);
  const v = refs.map(r => idx[r] || [0, 1, 1]);
  return [x.local.club.code, x.road.club.code, refs.map(r => r.split('|')[1]),
          refs.length ? +(v.reduce((a, z) => a + z[1], 0) / v.length).toFixed(3) : null,
          refs.length ? +(v.reduce((a, z) => a + z[2], 0) / v.length).toFixed(3) : null];
});
JSON.stringify({n: rows.length, prosek_faulova: +mf.toFixed(1), prosek_ft: +mt.toFixed(1), sudije: idx, kolo: up});
