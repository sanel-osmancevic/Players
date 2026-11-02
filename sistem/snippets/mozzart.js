// Mozzart: igrači (poeni/skokovi/asistencije) za takmičenje COMP. Pokrenuti na www.mozzartbet.com.
// Vraća {t, out: {"Inicijal.Prezime|Domaćin – Gost": {P:[linija, više, manje], S:[...], A:[...]}}}
// Za svakog igrača i kategoriju uzima se najuravnoteženija linija (kvote najbliže 50:50).
const COMP = 'Evroliga';
const H = {'content-type': 'application/json', 'medium': 'PREMATCH_WEB'};
const f = {sportIds: [2], pageSize: 50, currentPage: 0, includeDuplicate: true, matchTypeId: 2, orderType: 'BY_COMPETITION',
  loadPriorityTemplateGamesOnly: true, loadAllTemplateGames: false, packGamesGroupBySport: false, medium: 'PREMATCH_WEB',
  loadExtendedOffer: false, packGroupsInMatch: true, packAllGroups: false, sportsLoad: true, uberOffer: true};
const lst = await fetch('/betting/matches', {method: 'POST', headers: H, body: JSON.stringify(f)}).then(r => r.json());
const ms = (lst.items || []).filter(m => m.competition && m.competition.name === COMP);
const CAT = {'Broj poena': 'P', 'Broj skokova': 'S', 'Broj asistencija': 'A'};
const out = {};
for (const m of ms) {
  const d = await fetch('/betting/match/' + m.id, {method: 'POST', headers: H,
    body: JSON.stringify({subgameIds: [], subgames: [], participantId: '', matchTypeId: 2, onlyBindableGames: false})}).then(r => r.json());
  const game = m.home.name + ' – ' + m.visitor.name;
  for (const g of (d.match.oddsGroup || [])) {
    const mm = /^(Broj poena|Broj skokova|Broj asistencija) (.+)$/.exec(g.groupName || ''); if (!mm) continue;
    const c = CAT[mm[1]], pl = mm[2], L = parseFloat(g.specialOddValue);
    const ov = (g.odds.find(o => o.subgame.name === 'više' && o.oddStatus === 'ACTIVE') || {}).value;
    const un = (g.odds.find(o => o.subgame.name === 'manje' && o.oddStatus === 'ACTIVE') || {}).value;
    if (!ov || !un || isNaN(L)) continue;
    const k = pl + '|' + game; const cur = (out[k] = out[k] || {})[c];
    if (!cur || Math.abs(1 / ov - 1 / un) < Math.abs(1 / cur[1] - 1 / cur[2])) out[k][c] = [L, ov, un];
  }
}
JSON.stringify({t: new Date().toISOString(), n: ms.length, out});
