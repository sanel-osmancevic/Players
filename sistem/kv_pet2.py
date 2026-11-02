import json,re,unicodedata
from pomocno import citaj, pisi
from kolo import KOLO,DAN,tim
raw=citaj('mb_pet_raw2.json'); rows=citaj('igraci2.json')
AL={'Both Tut Gach':'Both Gach','Santiago Yusta':'Santi Yusta','Aleksander Balcerowski':'Olek Balcerowski','AJ Lawson':'A.J. Lawson','T.J. Shorts':'TJ Shorts','Daniel Oturu':'Dan Oturu'}
def key(n):
    n=unicodedata.normalize('NFKD',n).encode('ascii','ignore').decode().lower().replace("'",'')
    n=re.sub(r'\b(iv|iii|jr)\b','',n); n=re.sub(r'\b[a-z]\b','',n); return re.sub(r'[^a-z]','',n)
idx={(key(r['igrac']),r['tim']):r for r in rows if r['termin'].startswith(DAN)}
K={'P':'Poeni','S':'Skokovi','A':'Asistencije'}
out=[];miss=[];seen=set()
for k,lines in raw.items():
    n,t=k.split('|'); n=AL.get(n,n)
    r=idx.get((key(n),tim(t)))
    if not r: miss.append(k); continue
    for l in lines:
        c,L,ov=l[0],l[1],l[2]; un=l[3] if len(l)>3 else None
        s=(r['igrac'],K[c],L,ov,un)
        if s in seen: continue
        seen.add(s); out.append(dict(igrac=r['igrac'],tim=r['tim'],utakmica=r['utakmica'],kategorija=K[c],linija=L,kvota_vise=ov,kvota_manje=un,kolo=KOLO))
print('nema u modelu:',miss)
# ostali dani istog kola ostaju u kvote.json
danas={r['utakmica'] for r in idx.values()}
cet=[x for x in citaj('kvote.json') if x.get('kolo')==KOLO and x['utakmica'] not in danas]
pisi(cet+out, 'kvote.json', ensure_ascii=False)
pisi(out, 'kvote_pet.json', ensure_ascii=False)
print(len(cet),len(out))
