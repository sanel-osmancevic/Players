# Usage: python3 evidencija.py <kvote.json> <dan_label> [results.json] [kolo]  -> dopunjuje evidencija.json
# Menjaju se samo redovi utakmica koje su još u ponudi i nisu ocenjene; rezultati se upisuju na sve redove tog dana i kola,
# ali samo za utakmice koje se vide u rezultatima, pa fajl može da pokriva i jednu utakmicu.
import json,sys,math,re,unicodedata,os
from pomocno import citaj, pisi, MEDIJANA
from kolo import KOLO as KOLO_SADA
kv=citaj(sys.argv[1])
dan=sys.argv[2]; resf=sys.argv[3] if len(sys.argv)>3 else None
if not kv and not resf: sys.exit('nema kvota za evidenciju')
kolo=int(sys.argv[4]) if len(sys.argv)>4 else (kv[0]['kolo'] if kv else KOLO_SADA)
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
ocenjene={e['utakmica'] for e in ev if e['kolo']==kolo and e['dan']==dan and e.get('proslo_vise') is not None}
novi=[]
for o in kv:
    p=ig.get((o['igrac'],o['kolo']))
    if not p or not p['termin'].startswith(dan) or p['utakmica'] in ocenjene or o['kolo']!=kolo: continue
    k=K[o['kategorija']]; L=o['linija']; mu=p.get(k+'_proj_sirovo',p[k+'_proj']); sd=p.get(k+'_sd_sirovo',p[k+'_sd'])
    vals=[int(x) for x in str(p[k+'_sve']).split(',') if x!='']
    pv=1-Phi((math.floor(L)+0.5-(mu+MEDIJANA[k]))/sd)   # oko medijane (pomocno.MEDIJANA), od 6.11.2026.
    # šansa kao u preporukama (index32.html): konačna projekcija, istorija sa prošlom sezonom i tržište
    pf=1-Phi((math.floor(L)+0.5-p.get(k+'_med',p[k+'_proj']))/p[k+'_sd']); wl=o.get('tez_ls',0.2); lsn=o.get('ls_n') or 0; lsv=o.get('ls_vise') or 0
    hf=(sum(v>L for v in vals)+wl*lsv+1)/(len(vals)+wl*lsn+2); tv=o.get('trz_vise')
    prava=None if tv is None else round(o.get('tez_m',1/3)*pf+o.get('tez_h',1/3)*hf+o.get('tez_t',1/3)*tv,3)
    hv=sum(v>L for v in vals); hm=sum(v<L for v in vals); n=len(vals)
    row=dict(kolo=o['kolo'],dan=dan,utakmica=p['utakmica'],igrac=o['igrac'],tim=p['tim'],protiv=p['protiv'],teren=p['teren'],poz=p['poz'],status=p['status'],
      kategorija=o['kategorija'],linija=L,kvota_vise=o['kvota_vise'],kvota_manje=o['kvota_manje'],proj=mu,sd=sd,razmak=round((mu-(math.floor(L)+0.5))/sd,2),
      p_model_vise=round(pv,3),ist_vise=f'{hv}/{n}',ist_manje=f'{hm}/{n}',
      sansa_vise=round((pv+(hv+1)/(n+2))/2,3),sansa_prava_vise=prava,sansa_manje=round((1-pv+(hm+1)/(n+2))/2,3),
      minuti_proj=p['minuti_proj'],minuti_sd=p.get('minuti_sd'),tempo=p['tempo'],zona=p['zona_faktor'],
      trz_vise=o.get('trz_vise'),ls_vise=o.get('ls_vise'),ls_n=o.get('ls_n'),trz_medijana=o.get('trz_medijana'),trz_raskorak=o.get('trz_raskorak'),
      rezultat=None,minuti_stvarno=None,proslo_vise=None)
    novi.append(row)
igre={r['utakmica'] for r in novi}
ev=[e for e in ev if not (e['kolo']==kolo and e['dan']==dan and e['utakmica'] in igre)]+novi
if resf:
    pokrivene={e['utakmica'] for e in ev if e['kolo']==kolo and e['dan']==dan and key(e['igrac']) in R}
    for e in ev:
        if e['kolo']!=kolo or e['dan']!=dan or e['utakmica'] not in pokrivene: continue
        r=R.get(key(e['igrac']))
        if r is None or r['min']==0: e.update(rezultat=None,minuti_stvarno=None,proslo_vise='nije igrao')
        else: e.update(rezultat=r[e['kategorija']],minuti_stvarno=r['min'],proslo_vise=r[e['kategorija']]>e['linija'])
pisi(ev, 'evidencija.json', ensure_ascii=False)
print(len(ev))

# puni zapisnik i u pozadinsku arhivu (arhiva/kolo{K}_rezultati.json)
if resf:
    import arhiva
    print('Arhiva rezultata:', arhiva.arhiva_rezultati(resf, kolo))
