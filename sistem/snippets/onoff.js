// On/off iz play-by-play za EuroLeague (pokrenuti u pregledaču na api-live.euroleague.net).
// Vraća kompaktno: po timu, za svakog igrača ukupno [min,pts,fga,fta,reb,ast] i kola u kojima je igrao,
// a za "promenljive" saigrače j (propustili bar jednu utakmicu ili navedeni u EXTRA) učinak svakog igrača i dok je j na terenu.
// Promenljive: MAXR (poslednje kolo), EXTRA (lista imena "PREZIME, IME" koja se uvek uključuju)
const MAXR = 9, EXTRA = [];
const T = {}; let nG = 0; const bad = [];
const ST = {'2FGM':[2,1,0,0,0],'3FGM':[3,1,0,0,0],'2FGA':[0,1,0,0,0],'3FGA':[0,1,0,0,0],'FTM':[1,0,1,0,0],'FTA':[0,0,1,0,0],'D':[0,0,0,1,0],'O':[0,0,0,1,0],'AS':[0,0,0,0,1]};
const mt = s => { const [m, x] = s.split(':').map(Number); return m + x / 60 };
for (let rd = 1; rd <= MAXR; rd++) {
  const g = await fetch(`https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games?roundNumber=${rd}`).then(r => r.json());
  await Promise.all(g.data.filter(x => x.played).map(async x => {
    try {
      const p = await fetch(`https://live.euroleague.net/api/PlayByPlay?gamecode=${x.gameCode}&seasoncode=E2026`).then(r => r.json());
      const ev = []; let start = 0;
      for (const q of ['FirstQuarter','SecondQuarter','ThirdQuarter','ForthQuarter','ExtraTime']) {
        const len = q == 'ExtraTime' ? 5 : 10; let ps = start;
        for (const e of (p[q] || [])) {
          const ty = (e.PLAYTYPE || '').trim();
          if (ty == 'BP') { if (q == 'ExtraTime' && ev.length && ev[ev.length-1].t > start) start += 5; ps = start; ev.push({t: ps, ty}); continue; }
          if (ty == 'EP') { ev.push({t: ps + len, ty}); continue; }
          if (!e.MARKERTIME) continue;
          ev.push({t: ps + len - mt(e.MARKERTIME), ty, tm: (e.CODETEAM || '').trim(), pl: e.PLAYER ? e.PLAYER.trim() : null});
        }
        start = q == 'ExtraTime' ? start + 5 : start + 10;
      }
      const first = {}, seen = {};
      for (const e of ev) { if (!e.pl) continue; const k = e.tm + '|' + e.pl; if (e.ty == 'IN' || e.ty == 'OUT') { if (!(k in first)) first[k] = e.ty; } else seen[k] = 1; }
      const all = new Set([...Object.keys(first), ...Object.keys(seen)]);
      const on = {};
      for (const k of all) { const [tm, pl] = k.split('|'); if (first[k] == 'OUT' || !(k in first)) (on[tm] = on[tm] || new Set()).add(pl); }
      for (const k of all) { const [tm, pl] = k.split('|'); const t = T[tm] = T[tm] || {tot: {}, on: {}, r: {}}; (t.r[pl] = t.r[pl] || []).push(rd); t.tot[pl] = t.tot[pl] || [0,0,0,0,0,0]; }
      let last = 0;
      const acc = dt => { if (dt <= 0) return; for (const tm in on) { const t = T[tm]; const L = [...on[tm]];
        for (const i of L) { t.tot[i][0] += dt; for (const j of L) { if (j == i) continue; const o = (t.on[j] = t.on[j] || {}); (o[i] = o[i] || [0,0,0,0,0,0])[0] += dt; } } } };
      for (const e of ev) {
        acc(e.t - last); last = Math.max(last, e.t);
        if (!e.pl) continue; const tm = e.tm;
        if (e.ty == 'IN') { (on[tm] = on[tm] || new Set()).add(e.pl); continue; }
        if (e.ty == 'OUT') { on[tm] && on[tm].delete(e.pl); continue; }
        const s = ST[e.ty]; if (!s) continue;
        const t = T[tm]; for (let k = 0; k < 5; k++) t.tot[e.pl][k+1] += s[k];
        for (const j of (on[tm] || [])) { if (j == e.pl) continue; const o = (t.on[j] = t.on[j] || {}); const a = (o[e.pl] = o[e.pl] || [0,0,0,0,0,0]); for (let k = 0; k < 5; k++) a[k+1] += s[k]; }
      }
      nG++;
    } catch (err) { bad.push([rd, x.gameCode, String(err)]); }
  }));
}
const R = v => v.map(x => Math.round(x * 10) / 10);
const OUT = {};
for (const tm in T) {
  const t = T[tm]; const games = new Set(Object.values(t.r).flat()).size;
  const prom = Object.keys(t.tot).filter(j => (t.r[j].length < games && t.tot[j][0] >= 40) || EXTRA.includes(j));
  OUT[tm] = {g: games, tot: Object.fromEntries(Object.entries(t.tot).map(([k, v]) => [k, R(v)])), r: Object.fromEntries(Object.entries(t.r).map(([k, v]) => [k, v.sort((a,b)=>a-b).join(',')])),
             on: Object.fromEntries(prom.map(j => [j, Object.fromEntries(Object.entries(t.on[j] || {}).map(([k, v]) => [k, R(v)]))]))};
}
window.ONOFF_C = OUT;
JSON.stringify({nG, bad, MAXR, d: OUT});
