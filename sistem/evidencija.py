# Usage: python3 evidencija.py <kvote.json> <dan_label> [results.json]  -> appends to evidencija.json
import json,sys,math,re,unicodedata,os
from pomocno import citaj, pisi
kv=citaj(sys.argv[1])
if not kv: sys.exit('nema kvota za evidenciju')
dan=sys.argv[2]; resf=sys.argv[3] if len(sys.argv)>3 else None
ig={(r['igrac'],r['kolo']):r for r in citaj('igraci2.json')}
def key(n):
    n=unicodedata.normalize('NFKD',n).encode('ascii','ignore').decode().lower().replace("'",'')
    n=re.sub(r'\b(iv|iii|jr)\b','',n); n=re.sub(r'\b[a-z]\b','',n); return re.sub(r'[^a-z]','',n)
R={}
if resf:
    for n,mn,p,r,a in citaj(resf):
        l,f=n.split(', ',1) if ', ' in n else (n,''); R[key(f+' '+l)]=dict(min=mn,Poeni=p,Skokovi=r,Asistencije=a)
Phi=lambda z:0.5*(1+math.erf(z/math.sqrt(2)))
K={'Poeni':'pts','Skokovi':'reb','Asistencije':'ast'}
ev=citaj('evidencija.json') if os.path.exists('evidencija.json') else []
ev=[e for e in ev if not (e['kolo']==kv[0]['kolo'] and e['dan']==dan)]
for o in kv:
    p=ig.get((o['igrac'],o['kolo']))
    if not p or not p['termin'].startswith(dan): continue
    k=K[o['kategorija']]; L=o['linija']; mu=p.get(k+'_proj_sirovo',p[k+'_proj']); sd=p.get(k+'_sd_sirovo',p[k+'_sd'])
    vals=[int(x) for x in str(p[k+'_sve']).split(',') if x!='']
    pv=1-Phi((math.floor(L)+0.5-mu)/sd)
    hv=sum(v>L for v in vals); hm=sum(v<L for v in vals); n=len(vals)
    row=dict(kolo=o['kolo'],dan=dan,utakmica=p['utakmica'],igrac=o['igrac'],tim=p['tim'],protiv=p['protiv'],teren=p['teren'],poz=p['poz'],status=p['status'],
      kategorija=o['kategorija'],linija=L,kvota_vise=o['kvota_vise'],kvota_manje=o['kvota_manje'],proj=mu,sd=sd,razmak=round((mu-(math.floor(L)+0.5))/sd,2),
      p_model_vise=round(pv,3),ist_vise=f'{hv}/{n}',ist_manje=f'{hm}/{n}',
      sansa_vise=round((pv+(hv+1)/(n+2))/2,3),sansa_manje=round((1-pv+(hm+1)/(n+2))/2,3),
      minuti_proj=p['minuti_proj'],minuti_sd=p.get('minuti_sd'),tempo=p['tempo'],zona=p['zona_faktor'],
      trz_vise=o.get('trz_vise'),ls_vise=o.get('ls_vise'),ls_n=o.get('ls_n'),trz_medijana=o.get('trz_medijana'),trz_raskorak=o.get('trz_raskorak'),
      rezultat=None,minuti_stvarno=None,proslo_vise=None)
    r=R.get(key(o['igrac']))
    if resf:
        if r is None or r['min']==0: row['proslo_vise']='nije igrao'
        else: row['rezultat']=r[o['kategorija']]; row['minuti_stvarno']=r['min']; row['proslo_vise']=r[o['kategorija']]>L
    ev.append(row)
pisi(ev, 'evidencija.json', ensure_ascii=False)
print(len(ev))

# puni zapisnik i u pozadinsku arhivu (arhiva/kolo{K}_rezultati.json)
if resf:
    import arhiva
    print('Arhiva rezultata:', arhiva.arhiva_rezultati(resf, kv[0]['kolo']))
