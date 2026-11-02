// Meridian: igrači (poeni/skokovi/asistencije) za ligu LEAGUE (Evroliga = 208). Pokrenuti na meridianbet.rs.
// Vraća {t, out: {"Prezime, Ime|Domaćin – Gost": {P:[linija, više, manje], S:[...], A:[...]}}}
const LEAGUE = 208;
const ck = Object.fromEntries(document.cookie.split('; ').map(s => { const i = s.indexOf('='); return [s.slice(0, i), decodeURIComponent(s.slice(i + 1))]; }));
const H = {authorization: 'Bearer ' + ck.access_token, accept: 'application/json', 'accept-language': 'sr'};
const api = u => fetch('https://online.meridianbet.rs/betshop/api/' + u, {headers: H}).then(r => r.json());
const L = await api(`v1/offer/sport/55/league?page=0&time=ALL&leagues=${LEAGUE}`);
const ids = [...JSON.stringify(L).matchAll(/"eventId":(\d+)/g)].map(m => +m[1]);
const GR = {'Poeni Igrača': 'P', 'Skokovi Igrača': 'S', 'Asistencije Igrača': 'A'};
const out = {};
for (const id of [...new Set(ids)]) {
  const ev = (await api('v2/events/' + id)).payload; if (!ev) continue;
  const game = ev.header.rivals.join(' – ');
  for (const gg of ev.activeGameGroups || []) {
    const c = GR[gg.name]; if (!c) continue;
    const p = (await api(`v2/events/${id}?gameGroupId=${gg.id}`)).payload;
    for (const g of p.games || []) {
      if (!/^Ukupno (Poena|Skokova|Asistencija)/.test(g.marketName)) continue;
      for (const mk of g.markets) {
        if (mk.state !== 'ACTIVE' || mk.overUnder == null) continue;
        const ov = (mk.selections.find(s => s.name === 'Više' && s.state === 'ACTIVE') || {}).price;
        const un = (mk.selections.find(s => s.name === 'Manje' && s.state === 'ACTIVE') || {}).price;
        if (!ov || !un) continue;
        const k = mk.name + '|' + game; const cur = (out[k] = out[k] || {})[c];
        if (!cur || Math.abs(1 / ov - 1 / un) < Math.abs(1 / cur[1] - 1 / cur[2])) out[k][c] = [mk.overUnder, ov, un];
      }
    }
  }
}
JSON.stringify({t: new Date().toISOString(), n: ids.length, out});
