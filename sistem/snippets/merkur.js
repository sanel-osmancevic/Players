// pokrenuti na www.merkurxtip.rs: glavne linije EuroLeague igrača
const q='?annex=0&mobileVersion=1.27.12&locale=sr';
const r=await fetch('/restapi/offer/sr/sport/SK/league/2314247/mob'+q).then(r=>r.json());
const det=await Promise.all((r.esMatches||[]).map(m=>fetch(`/restapi/offer/sr/match/${m.id}`+q).then(r=>r.json())));
const out={};for(const d of det){const o=d.odds||{},p=d.params||{},x={};
 if(p.ouPlPoints&&o[51679]&&o[51681])x.P=[+p.ouPlPoints,o[51679],o[51681]];
 if(p.ouPlRebounds&&o[51685]&&o[51687])x.S=[+p.ouPlRebounds,o[51685],o[51687]];
 if(p.ouPlAssists&&o[51682]&&o[51684])x.A=[+p.ouPlAssists,o[51682],o[51684]];
 out[d.home+'|'+d.away]=x;}
JSON.stringify({t:new Date().toISOString(),out})
