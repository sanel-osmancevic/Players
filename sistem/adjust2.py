import json,math
from pomocno import citaj, pisi
rows=citaj('igraci2.json')
G={'Dubai – Hapoel TA':(174.5,1.75,2.4),'Anadolu Efes – Panathinaikos':(164.5,3.6,1.41),'Žalgiris – Partizan':(165.5,1.36,4.0),'ASVEL – Baskonia':(175.5,1.62,2.7),
   'Olympiacos – Olimpia Milano':(169.5,1.2,6.1),'Barcelona – Valencia':(182.5,1.77,2.4),'Virtus – Beşiktaş':(176.5,1.52,3.1)}
LG=173.8
for r in rows:
    g=G.get(r['utakmica'])
    if not g or r['status']=='Ne igra': continue
    tot,oh,oa=g; ph=(1/oh)/(1/oh+1/oa); fav= ph if r['teren']=='domaćin' else 1-ph
    pf=1+r['tempo']/100
    tf=math.sqrt((tot/LG)/pf)          # pola tezine na ukupnom broju poena iz kladionice
    mf=1.0
    r['total_kladionica']=tot; r['sansa_pobede']=round(fav,2); r['faktor_utakmica']=round(tf*mf,3)
    for k in ['pts','reb','ast']:
        f=(tf if k=='pts' else math.sqrt(tf))*mf
        r[k+'_proj']=round(r[k+'_proj']*f,1)
    r['minuti_proj']=round(r['minuti_proj']*mf,1)
pisi(rows, 'igraci2.json', ensure_ascii=False)
pisi(G, 'kvote_utakmica.json', ensure_ascii=False)
print([(r['igrac'],r['faktor_utakmica'],r['pts_proj']) for r in rows if r.get('faktor_utakmica') and abs(r['faktor_utakmica']-1)>0.04][:12])
