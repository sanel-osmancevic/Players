import json, math, re
from pomocno import citaj, pisi
from kolo import KOLO, GAMES as GAMES_KOLA
ex=citaj('extras.json'); d9=citaj('statistika.json'); d9b=dict(P=[],SP=[]); d9c=dict(P=[],SP=[])
# poslednja provera sastava: statusi.json {"PREZIME, IME|TIM": ["Igra"/"Upitan"/"Ne igra", "izvor"]} ima prednost
import os as _os
for _f in ('statusi_auto.json','statusi.json'):   # auto (nestanak iz ponude) pa ručni (zvaničan izveštaj, vesti) koji ima prednost
  if _os.path.exists(_f):
    for _k,_v in citaj(_f).items():
        if _v[0]=='Igra': ex['status'].pop(_k,None)
        else: ex['status'][_k]=_v
ex['posAllow']=d9['posAllow']; ex['pace']=d9['pace']
TEAM={'RED':'Crvena zvezda','MUN':'Bayern','TEL':'Maccabi TA','PRS':'Paris','MAD':'Real Madrid','ULK':'Fenerbahče','DUB':'Dubai','HTA':'Hapoel TA','IST':'Anadolu Efes','PAN':'Panathinaikos','ZAL':'Žalgiris','PAR':'Partizan','ASV':'ASVEL','BAS':'Baskonia','OLY':'Olympiacos','MIL':'Olimpia Milano','BAR':'Barcelona','PAM':'Valencia','VIR':'Virtus','BES':'Beşiktaş'}
GAMES=[tuple(g[:3]) for g in GAMES_KOLA]
opp={};home={};gname={};gtime={};gord={}
for i,(h,a,t) in enumerate(GAMES):
    g=f"{TEAM[h]} – {TEAM[a]}"
    for x,o,hh in ((h,a,1),(a,h,0)): opp[x]=o;home[x]=hh;gname[x]=g;gtime[x]=t;gord[x]=i
K=['pts','reb','ast']
# parametri modela podešeni proverom na celoj sezoni (backtest.py: kola 3–9, 1233 igrač-utakmice, provera i na kolima 8–9 posebno):
#   zaboravljanje starih utakmica 0.9 po kolu (bilo 0.85), težina proseka lige 30 min (bilo 15),
#   širina raspodele: više oslonca na opšti obrazac sqrt(proj)*c nego na rasipanje igrača iz malog uzorka (težina 16, bilo 4)
MP={'decay':0.9,'pw':30,'sd_c':{'pts':2.2,'reb':1.35,'ast':1.35},'sd_w':16}
LASTR=max(int(x) for p in d9['P']+d9b['P']+d9c['P'] for x in p[3].split(','))   # poslednje kolo u podacima
LS=citaj('prosla_sezona.json') if __import__('os').path.exists('prosla_sezona.json') else {}
# PRAVILO: kad protivniku fali ključni igrač koji je bio u uzorku, faktor odbrane protivnika vuče se ka proseku lige Upisuje se po kolu, npr. {('PAR','C'):0.5}.
KEYOUT={}
# position allowed per40, league means
pa={}; lgpos={}
for t,p,n,*v in ex['posAllow']:
    pa[(t,p)]=(n,dict(zip(K,v)))
    for k,x in zip(K,v): lgpos.setdefault((p,k),[]).append(x)
lgpos={k:sum(v)/len(v) for k,v in lgpos.items()}
pace=ex['pace']; lgpace=sum(pace.values())/len(pace)
sh={'P':d9['SP']+d9b['SP']+d9c['SP'],'D':d9['D']}
norm=lambda n:n.replace(' ,',',').replace('  ',' ')
SP={(norm(r[0]),r[1]):r for r in sh['P']}
DF={r[0]:r for r in sh['D']}
Z=['r','m','t']; VAL={'r':2,'m':2,'t':3}
lgA={};lgM={};lgP=sum(r[1] for r in sh['D'])
for i,z in enumerate(Z):
    lgA[z]=sum(r[2+2*i] for r in sh['D']); lgM[z]=sum(r[3+2*i] for r in sh['D'])
lgFTA=sum(r[9] for r in sh['D']); lgFTM=sum(r[8] for r in sh['D'])
def zone_factor(n,t,o):
    p=SP.get((norm(n),t)); d=DF[o]
    if not p: return 1.0,None
    mins=p[2]; base=adj=0; parts={}
    for i,z in enumerate(Z):
        a,m=p[3+2*i],p[4+2*i]; lp=lgM[z]/lgA[z]
        pct=(m+lp*15)/(a+15)
        fa=(d[2+2*i]/d[1])/(lgA[z]/lgP); fa=1+(fa-1)*8/14
        dp=(d[3+2*i]/d[2+2*i])/lp; dp=1+(dp-1)*0.5*8/14
        b=a/mins*pct*VAL[z]; base+=b; adj+=b*fa*dp; parts[z]=b
    fta,ftm=p[10],p[9]; ftp=(ftm+0.77*20)/(fta+20)
    ff=(d[9]/d[1])/(lgFTA/lgP); ff=1+(ff-1)*8/14
    b=fta/mins*ftp; base+=b; adj+=b*ff; parts['ft']=b
    tot=sum(parts.values()) or 1
    return adj/base if base else 1.0,{k:round(v/tot*100) for k,v in parts.items()}
Phi=lambda z:0.5*(1+math.erf(z/math.sqrt(2)))
def pr(mu,sd,th): return 1-Phi((th-0.5-mu)/sd)
fix={'Codi Miller-Mcintyre':'Codi Miller-McIntyre','A.j. Lawson':'A.J. Lawson','Dj Stewart':'DJ Stewart','Rj Cole':'RJ Cole','Tj Shorts':'TJ Shorts','Mckinley Wright IV':'McKinley Wright IV','Zach Leday':'Zach LeDay',"O'shae J Brissett":"O'Shae Brissett","O'Shae J Brissett":"O'Shae Brissett"}
def nm(s):
    l,f=s.split(', ',1); s=f+' '+l
    s=' '.join(w if w in('IV','III','JR.') else w.capitalize() for w in s.split()).replace('Jr.','Jr.').replace('JR.','Jr.')
    s=re.sub(r'-([a-z])',lambda m:'-'+m.group(1).upper(),s); s=re.sub(r"O'([a-z])",lambda m:"O'"+m.group(1).upper(),s)
    return fix.get(s,s)
P=[]
for n,pos,t,rr,mm,ss,vp,vr,va in d9['P']+d9b['P']+d9c['P']:
    rnds=[int(x) for x in rr.split(',')]; mins=[float(x) for x in mm.split(',')]; starts=[int(c) for c in ss]
    vals={'pts':[int(x) for x in vp.split(',')],'reb':[int(x) for x in vr.split(',')],'ast':[int(x) for x in va.split(',')]}
    assert len(vals['pts'])==len(mins), n
    w=[MP['decay']**(LASTR-x) for x in rnds]; W=sum(w)
    mproj=sum(m*x for m,x in zip(mins,w))/W; M=sum(m*x for m,x in zip(mins,w))
    stt=ex['status'].get(f'{n}|{t}',['Igra',''])
    P.append(dict(n=n,pos=pos,t=t,o=opp[t],mins=mins,starts=starts,rnds=rnds,vals=vals,w=w,M=M,mproj=mproj,status=stt[0],note=stt[1]))
# redistribute minutes of OUT players
grp=lambda p:'G' if p=='G' else 'FC'
for x in P:
    if x['status']=='Ne igra':
        mates=[y for y in P if y['t']==x['t'] and y['status']!='Ne igra' and grp(y['pos'])==grp(x['pos'])]
        tot=sum(y['mproj'] for y in mates)
        # bt_minuti.py, kola 3-9: stvarni višak posle prvog izostanka je oko 1 min, pa je 0.7 i najviše 4 min bilo previše
        for y in mates: y['bonus']=min(2.0,y.get('bonus',0)+x['mproj']*0.3*y['mproj']/tot) if tot else 0
MINFIX={}  # ručni dodatak minuta po kolu, npr. {'HAYES, KEVARRIUS|PAR':4.0}
for x in P:
    b=MINFIX.get(f"{x['n']}|{x['t']}")
    if b: x['bonus']=max(x.get('bonus',0),b)
rows=[];safe=[]
for x in P:
    t,o,pos=x['t'],x['o'],x['pos']
    mp=x['mproj']+x.get('bonus',0)
    hf=1.02 if home[t] else 0.98
    pf=((pace[t]+pace[o])/2)/lgpace
    n_o,al=pa[(o,pos)]
    on=ex['onoff'].get(f"{x['n']}|{t}",[None,None])
    name=nm(x['n'])
    zf,prof=zone_factor(x['n'],t,o)
    r=dict(api=x['n'],igrac=name,poz=pos,tim=TEAM[t],protiv=TEAM[o],teren='domaćin' if home[t] else 'gost',utakmica=gname[t],termin=gtime[t],red=gord[t],
           status=x['status'],napomena=x['note'],utakmice=len(x['mins']),
           minuti=round(sum(x['mins'])/len(x['mins']),1),minuti_proj=round(mp,1) if x['status']!='Ne igra' else 0,
           minuti_posl3=round(sum(x['mins'][-3:])/len(x['mins'][-3:]),1),
           starter=f"{sum(x['starts'])}/{len(x['starts'])}",
           on_net=on[0],off_net=on[1],onoff=None if on[0] is None or on[1] is None else round(on[0]-on[1],1),
           tempo=round(pf*100-100,1),zona_faktor=round((zf-1)*100,1),udeo_reket=prof and prof['r'],udeo_srednja=prof and prof['m'],udeo_trojka=prof and prof['t'],udeo_ft=prof and prof['ft'])
    r['minuti_trend']=round(r['minuti_posl3']-r['minuti'],1)
    mm=x['mins'][-6:]; mu_=sum(mm)/len(mm); r['minuti_sd']=round((sum((v-mu_)**2 for v in mm)/max(1,len(mm)-1))**0.5,1)
    for k in K:
        v=x['vals'][k]
        prior=lgpos[(pos,k)]/40; pw=MP['pw']
        ls=LS.get(x['n'])
        if ls and ls['min']>=150:   # prošla sezona: stopa igrača kao polazna tačka, težina do 20 min (oko jedne utakmice)
            prior=ls[k]/ls['min']; pw=min(20,0.02*ls['min'])
        rate=(sum(a*b for a,b in zip(v,x['w']))+prior*pw)/(x['M']+pw)
        of=1+(al[k]/lgpos[(pos,k)]-1)*n_o/(n_o+6)
        sh_=KEYOUT.get((o,pos),0); of=1+(of-1)*(1-sh_)
        if k=='pts': of=0.4*of+0.6*(1+(zf-1)*(1-sh_))
        mu=rate*mp*of*hf*pf
        av=sum(v)/len(v); sdE=math.sqrt(sum((a-av)**2 for a in v)/(len(v)-1))
        sdB=math.sqrt(max(mu,0.5))*MP['sd_c'][k]; sd=math.sqrt((sdE**2*len(v)+sdB**2*MP['sd_w'])/(len(v)+MP['sd_w']))
        if x['status']=='Ne igra': mu=0
        t80=0
        if mu>0:
            for th in range(1,60):
                if pr(mu,sd,th)>=0.8: t80=th
                else: break
        hit=sum(a>=t80 for a in v)
        r.update({f'{k}_proj':round(mu,1),f'{k}_prosek':round(av,1),f'{k}_sd':round(sd,1),f'{k}_80':t80,f'{k}_80_pogodak':f'{hit}/{len(v)}',
                  f'{k}_poslednje':' · '.join(map(str,v[-5:])),f'{k}_sve':','.join(map(str,v)),f'{k}_protivnik':round((of-1)*100,1)})
        if x['status']=='Igra' and t80>=(8 if k=='pts' else 3) and hit>=len(v)-1:
            safe.append(dict(kljuc=f'{name} {k}',igrac=name,tim=TEAM[t],utakmica=gname[t],termin=gtime[t],kategorija={'pts':'Poeni','reb':'Skokovi','ast':'Asistencije'}[k],
              granica=f'{t80}+',verovatnoca=round(pr(mu,sd,t80),3),pogodak=f'{hit}/{len(v)}',pogodak_udeo=round(hit/len(v),3),projekcija=round(mu,1),poslednje=' · '.join(map(str,v[-5:]))))
    rows.append(r)
safe.sort(key=lambda s:(-s['pogodak_udeo'],-s['verovatnoca']))
# matchup by position
mt=[]
for t in opp:
    o=opp[t]
    for p in 'GFC':
        n_o,al=pa[(o,p)]
        d=dict(kljuc=f'{t}-{p}',tim=TEAM[t],protiv=TEAM[o],utakmica=gname[t],red=gord[t],pozicija={'G':'Bekovi','F':'Krila','C':'Centri'}[p])
        for k in K: d[f'{k}_pct']=round((al[k]/lgpos[(p,k)]-1)*100,1)
        mt.append(d)
games=[dict(utakmica=gname[h],termin=t,red=gord[h],tempo=round((pace[h]+pace[a])/2,1),tempo_lig=round(lgpace,1),tempo_pct=round(((pace[h]+pace[a])/2/lgpace-1)*100,1)) for h,a,t in GAMES]
lus=[dict(kljuc=f'{TEAM[t]}: {l}',tim=TEAM[t],utakmica=gname[t],red=gord[t],petorka=l,minuti=m,net=nt) for t,l,m,nt in ex['lus'] if t in opp]
inj=[dict(kljuc=f'{t} {p}',tim=t,igrac=p,status=s,opis=d) for t,p,s,d in ex['injuries']]
team2game={TEAM[t]:gname[t] for t in opp}
for i in inj: i['utakmica']=team2game.get(i['tim'],'')
for d in (rows,safe,games,inj):
    for x in d: x['kolo']=KOLO
for fn,d in [('igraci2.json',rows),('najsigurnije2.json',safe),('matchup.json',mt),('utakmice.json',games),('petorke.json',lus),('povrede.json',inj)]:
    pisi(d, fn, ensure_ascii=False)
print(len(rows),len(safe),len(mt),len(lus),len(inj))

for s in safe[:12]: print(s['igrac'],s['kategorija'],s['granica'],s['verovatnoca'],s['pogodak'])
for r in rows:
    if r['status']!='Igra' or r.get('minuti_proj',0)-r['minuti']>2: print('*',r['igrac'],r['status'],r['minuti'],r['minuti_proj'],r['pts_proj'])
print(games)
