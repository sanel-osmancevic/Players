import json,re,unicodedata
raw=json.load(open('mb_pet_raw2.json')); rows=json.load(open('igraci2.json'))
TM={'Hapoel T.A.':'Hapoel TA','Dubai':'Dubai','Panathinaikos':'Panathinaikos','Anadolu Efes':'Anadolu Efes','Partizan':'Partizan','Zalgiris':'Žalgiris','Baskonia':'Baskonia','Lyon-Villeurb.':'ASVEL','Olimpia Milano':'Olimpia Milano','Olympiacos':'Olympiacos','Barcelona':'Barcelona','Besiktas':'Beşiktaş','Valencia':'Valencia','Virtus Bologna':'Virtus'}
AL={'Both Tut Gach':'Both Gach','Santiago Yusta':'Santi Yusta','Aleksander Balcerowski':'Olek Balcerowski','AJ Lawson':'A.J. Lawson','T.J. Shorts':'TJ Shorts','Daniel Oturu':'Dan Oturu'}
def key(n):
    n=unicodedata.normalize('NFKD',n).encode('ascii','ignore').decode().lower().replace("'",'')
    n=re.sub(r'\b(iv|iii|jr)\b','',n); n=re.sub(r'\b[a-z]\b','',n); return re.sub(r'[^a-z]','',n)
idx={(key(r['igrac']),r['tim']):r for r in rows if r['termin'].startswith('pet')}
K={'P':'Poeni','S':'Skokovi','A':'Asistencije'}
out=[];miss=[];seen=set()
for k,lines in raw.items():
    n,t=k.split('|'); n=AL.get(n,n)
    r=idx.get((key(n),TM[t]))
    if not r: miss.append(k); continue
    for l in lines:
        c,L,ov=l[0],l[1],l[2]; un=l[3] if len(l)>3 else None
        s=(r['igrac'],K[c],L,ov,un)
        if s in seen: continue
        seen.add(s); out.append(dict(igrac=r['igrac'],tim=r['tim'],utakmica=r['utakmica'],kategorija=K[c],linija=L,kvota_vise=ov,kvota_manje=un,kolo=9))
print('nema u modelu:',miss)
old=[x for x in json.load(open('kvote.json')) if not any(x['utakmica']==o['utakmica'] for o in out[:1]) ]
cet=[x for x in json.load(open('kvote.json')) if x['utakmica'] in ('Crvena zvezda – Bayern','Maccabi TA – Paris','Real Madrid – Fenerbahče')]
json.dump(cet+out,open('kvote.json','w'),ensure_ascii=False)
json.dump(out,open('kvote_pet.json','w'),ensure_ascii=False)
print(len(cet),len(out))
