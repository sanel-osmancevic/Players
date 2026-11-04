import json,math
from pomocno import citaj, pisi
rows=citaj('igraci2.json')
G={'Real Madrid – Panathinaikos': (172.5, 2.3, 1.8), 'Anadolu Efes – Paris': (175.5, 1.43, 3.5), 'Fenerbahče – Baskonia': (168.5, 1.1, 9.75), 'Hapoel TA – Barcelona': (178.5, 1.54, 2.9), 'ASVEL – Bayern': (176.5, 1.84, 2.25), 'Olimpia Milano – Valencia': (178.5, 2.4, 1.77), 'Beşiktaş – Žalgiris': (174.5, 2.15, 1.94), 'Olympiacos – Crvena zvezda': (168.5, 1.46, 3.3), 'Virtus – Dubai': (173.5, 2.15, 1.87), 'Partizan – Maccabi TA': (170.5, 1.62, 2.7)}
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
