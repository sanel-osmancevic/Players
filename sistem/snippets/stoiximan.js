// Stoiximan (Grčka): igrači za Evroligu (liga 10666). Pokrenuti na www.stoiximan.gr.
// Stoiximan nudi "lestvice" (N+ poena / skokova / asistencija) umesto više/manje. Za svakog igrača uzima se stepenik
// sa kvotom najbližom 1.87 i pretvara u liniju N-0.5 (više = ta kvota); kvota za manje se izvodi uz pretpostavljenu
// maržu jednostrane lestvice MARZA (polazno 7.5%), tako da je verovatnoća bez marže = (1/kvota)/MARZA.
// Vraća {t, out: {"Ime Prezime|slug-utakmice": {P:[linija, više, manje], S:[...], A:[...]}}}
const LIGA = '/sport/basket/diorganoseis/euroleague/10666/', MARZA = 1.075;
const html = await (await fetch(LIGA)).text();
const evs = [...new Set([...html.matchAll(/\/apodoseis\/([a-z0-9-]+)\/(\d{8,})\//g)].map(m => m[0]))];
const TIP = {PLNP: 'P', PLTR: 'S', PALA: 'A'};
const out = {};
for (const e of evs) {
  const slug = e.split('/')[2];
  const h = await (await fetch(e + '?bt=1')).text();
  const m = h.match(/window\["initial_state"\]\s*=\s*(\{[\s\S]*?\})\s*;?\s*<\/script>/); if (!m) continue;
  const ms = (JSON.parse(m[1]).data.event || {}).markets || [];
  for (const mk of ms) {
    const c = TIP[mk.type]; if (!c || !mk.tableLayout) continue;
    for (const row of mk.tableLayout.rows || []) {
      const sel = (row.groupSelections || []).flatMap(g => g.selections || []).filter(s => /^\d+\+$/.test(s.name) && s.price > 1);
      if (!sel.length) continue;
      const b = sel.reduce((a, s) => Math.abs(s.price - 1.87) < Math.abs(a.price - 1.87) ? s : a);
      const N = parseInt(b.name), ov = b.price, un = 1 / Math.max(0.05, MARZA - 1 / ov);
      (out[row.title + '|' + slug] = out[row.title + '|' + slug] || {})[c] = [N - 0.5, ov, Math.round(un * 100) / 100];
    }
  }
}
JSON.stringify({t: new Date().toISOString(), n: evs.length, out});
