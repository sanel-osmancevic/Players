// pokrenuti na www.soccerbet.rs: glavne aktivne linije EuroLeague igrača
const q='?annex=0&mobileVersion=3.4.6&locale=sr';
const r=await fetch(`/restapi/offer/sr/ext/sport/B/PL/mob${q}`).then(r=>r.json());
const el=(r.esMatches||[]).filter(m=>/Evroliga/i.test(m.leagueName||''));
const C={P:[51679,51681],S:[51685,51687],A:[51682,51684]};const out={};
for(const m of el){const bm=m.betMap||{};const o={};
 for(const [c,[a,b]] of Object.entries(C)){const O=bm[a]||{},U=bm[b]||{};let best=null;
  for(const sv of Object.keys(O)){if(!U[sv]||O[sv].s!=='U'||U[sv].s!=='U')continue;const ov=O[sv].ov,un=U[sv].ov,L=+sv.split('=')[1];const bal=Math.abs(1/ov-1/un);if(!best||bal<best[3])best=[L,ov,un,bal];}
  if(best)o[c]=best.slice(0,3);}
 out[m.home+'|'+m.away]=o;}
JSON.stringify({t:new Date().toISOString(),out})
