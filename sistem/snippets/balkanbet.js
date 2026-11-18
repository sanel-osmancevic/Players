// pokrenuti na www.balkanbet.rs: glavne linije EuroLeague igrača (NSoft „Seven“ API, takmičenje „Igrači Evroliga“)
// Svaki igrač je poseban događaj „L.Walker IV (Besiktas)“; poeni imaju više linija, glavna je označena kao favorit (e=true),
// a bez oznake se uzima najuravnoteženija. Izlaz kao Merkur/Meridian: {t, out: {"Ime|Tim": {P|S|A: [linija, više, manje]}}}.
const API='https://sports-sm-distribution-api.de-2.nsoftcdn.com/api/v1/events', CO='4f54c6aa-82a9-475d-bf0e-dc02ded89225';
const TURNIR=29227, SPORT=273;   // Košarka Igrači / Igrači Evroliga
const MK={2402:'P',2403:'S',2406:'A'}, MANJE={8136:1,8142:1,8148:1}, VISE={8139:1,8145:1,8151:1};
const od=new Date(Date.now()-3*3600e3).toISOString().slice(0,19);
const jez=JSON.stringify({default:'sr-Latn',events:'sr-Latn',sport:'sr-Latn',category:'sr-Latn',tournament:'sr-Latn',team:'sr-Latn',market:'sr-Latn'});
const u=`${API}?deliveryPlatformId=3&dataFormat=${encodeURIComponent(JSON.stringify({default:'object',events:'array',outcomes:'array'}))}&language=${encodeURIComponent(jez)}`+
  `&timezone=Europe%2FBelgrade&company=%7B%7D&companyUuid=${CO}&filter[sportId]=${SPORT}&filter[tournamentId]=${TURNIR}&filter[from]=${od}&sort=startsAt&shortProps=1`;
const r=await fetch(u).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();});
const out={};
for(const e of (r.data&&r.data.events)||[]){
  const m=/^(.*?)\s*\(([^)]*)\)\s*$/.exec(e.j||''); if(!m)continue;
  const o={}, kand={};
  for(const mk of Object.values(e.o||{})){
    const c=MK[mk.b]; if(!c||!mk.d)continue;
    let ov=null,un=null; for(const h of mk.h||[]){ if(!h.c)continue; const n=String(h.e||''); if(/^Više/.test(n))ov=h.g; else if(/^Manje/.test(n))un=h.g; }
    if(!ov||!un)continue;
    const L=+(mk.g||[])[0]; if(!Number.isFinite(L))continue;
    (kand[c]=kand[c]||[]).push([L,ov,un,mk.e?-1:Math.abs(1/ov-1/un)]);
  }
  for(const [c,l] of Object.entries(kand)){l.sort((a,b)=>a[3]-b[3]);o[c]=l[0].slice(0,3);}
  if(Object.keys(o).length)out[m[1].trim()+'|'+m[2].trim()]=o;
}
JSON.stringify({t:new Date().toISOString(),out})
