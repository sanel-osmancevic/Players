// Preraspodela šuteva, poena, skokova i asistencija prema sastavu (posle snippets/onoff.js).
// D = on/off podaci, LAST = poslednje kolo u podacima, PI = verovatnoća da igrač igra danas (samo oni < 1),
// igrač koji je propustio poslednje kolo, a danas igra, računa se kao povratak (PPOV).
// Za igrača i i saigrača j: učinak po minuti dok je j na terenu (on) i van terena (off), skupljeno ka proseku.
// Model (ponderisani prosek kola 0.85^) vidi mešavinu kola sa i bez j; cilj je mešavina prema današnjem stanju j.
// faktor = cilj / model, množi se preko svih promenljivih saigrača, ograničeno na ±CAP.
const fakt = (D, LAST, PI, PPOV = 0.65, K = 60, KE = 10, CAP = 0.18) => {
  const res = {};
  const use = v => v[2] + 0.44 * v[3];
  const G = {pts: use, fga: v => v[2], reb: v => v[4], ast: v => v[5]};
  for (const tm in D) {
    const d = D[tm]; res[tm] = {};
    const Rj = j => new Set((d.r[j] || '').split(',').filter(Boolean).map(Number));
    const stanje = j => { if (j in PI) return PI[j]; const r = Rj(j); return r.size && !r.has(LAST) && [...Object.values(d.r)].some(s => s.split(',').map(Number).includes(LAST)) ? PPOV : 1; };
    for (const i in d.tot) {
      const tot = d.tot[i]; if (tot[0] < 40 || PI[i] === 0) continue;
      const Ri = [...Rj(i)]; const wsum = Ri.reduce((a, r) => a + 0.85 ** (LAST - r), 0);
      const f = {pts: 1, fga: 1, reb: 1, ast: 1}; const zbog = [];
      for (const j in d.on) {
        if (j == i) continue;
        const rj = Rj(j); const both = Ri.filter(r => rj.has(r));
        const sw = both.reduce((a, r) => a + 0.85 ** (LAST - r), 0) / wsum;
        const p = stanje(j);
        if (Math.abs(p - sw) < 0.05) continue;
        const on = d.on[j][i] || [0, 0, 0, 0, 0, 0];
        const minWith = tot[0] * both.length / Ri.length;
        const c = minWith > 0 ? Math.min(1, on[0] / minWith) : 0;
        const off = tot.map((v, k) => v - on[k]);
        const parts = {};
        for (const k in G) {
          const rt = G[k](tot) / tot[0]; if (rt <= 0) continue;
          const kk = Math.max(K, KE / rt);
          const onr = (G[k](on) + rt * kk) / (on[0] + kk), offr = (G[k](off) + rt * kk) / (Math.max(0, off[0]) + kk);
          const sa = c * onr + (1 - c) * offr;
          const model = sw * sa + (1 - sw) * offr, cilj = p * sa + (1 - p) * offr;
          const r = cilj / model; f[k] *= r; parts[k] = r;
        }
        const big = Object.entries(parts).filter(([k, v]) => Math.abs(v - 1) >= 0.05);
        if (big.length) zbog.push(`${j.split(',')[0]} (${p == 0 ? 'van' : p < 1 ? (p == PPOV ? 'povratak' : 'upitan') : 'igra'}): ` + big.map(([k, v]) => `${k} ${v > 1 ? '+' : ''}${Math.round(100 * (v - 1))}%`).join(', '));
      }
      for (const k in f) f[k] = Math.max(1 - CAP, Math.min(1 + CAP, f[k]));
      if (Object.values(f).some(v => Math.abs(v - 1) >= 0.01)) res[tm][i] = [+f.pts.toFixed(3), +f.reb.toFixed(3), +f.ast.toFixed(3), +f.fga.toFixed(3), zbog.join('; ')];
    }
  }
  return res;
};
