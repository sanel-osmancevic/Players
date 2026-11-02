import json, math, itertools, statistics as S
exec(open('backtest.py').read().split('# 1) zaboravljanje')[0])
TIM={p[0]:p[2] for p in P}
res={}
for n,R in cilj():
    p=projekcija(n,R,0.9,0.9,30)
    if not p: continue
    a=G[n][R]
    res.setdefault((TIM[n],R),[]).append((n,{k:a[2+i]-p[k] for i,k in enumerate(K3)},{k:(a[2+i]>p[k]) for i,k in enumerate(K3)}))
def corr(x,y):
    mx,my=S.mean(x),S.mean(y); sx=math.sqrt(sum((a-mx)**2 for a in x)); sy=math.sqrt(sum((b-my)**2 for b in y)); return sum((a-mx)*(b-my) for a,b in zip(x,y))/(sx*sy)
for k1,k2 in [('pts','pts'),('reb','reb'),('ast','ast'),('pts','ast'),('pts','reb')]:
    X=[];Y=[];both=one=0;n=0
    for g,L in res.items():
        for (a,ra,oa),(b,rb,ob) in itertools.combinations(L,2):
            X.append(ra[k1]);Y.append(rb[k2])
    print(f"isti tim {k1}-{k2}: korelacija odstupanja {corr(X,Y):+.3f} (parova {len(X)})")
# isti smer "više" za dva saigrača: koliko često oba prođu u odnosu na nezavisno
for k in K3:
    pa=pb=pab=n=0
    for g,L in res.items():
        for (a,ra,oa),(b,rb,ob) in itertools.combinations(L,2):
            n+=1; pa+=oa[k]; pb+=ob[k]; pab+=oa[k] and ob[k]
    print(f"{k}: oba saigrača iznad projekcije {pab/n:.3f} vs nezavisno {pa/n*pb/n:.3f}")
OPP={}
for r,h,a in json.load(open('raspored.json')): OPP[(h,r)]=a; OPP[(a,r)]=h
print('--- protivnici u istoj utakmici ---')
for k in K3:
    X=[];Y=[]; pab=pa=pb=n=0
    for (t,R),L in res.items():
        o=OPP.get((t,R))
        if not o or (o,R) not in res or t>o: continue
        for (a,ra,oa) in L:
            for (b,rb,ob) in res[(o,R)]:
                X.append(ra[k]);Y.append(rb[k]); n+=1; pa+=oa[k]; pb+=ob[k]; pab+=oa[k] and ob[k]
    print(f"protivnici {k}: korelacija {corr(X,Y):+.3f}; oba iznad projekcije {pab/n:.3f} vs nezavisno {pa/n*pb/n:.3f} ({n} parova)")
# "manje": oba ispod
for k in K3:
    pab=pa=pb=n=0
    for g,L in res.items():
        for (a,ra,oa),(b,rb,ob) in itertools.combinations(L,2):
            n+=1; pa+=not oa[k]; pb+=not ob[k]; pab+=(not oa[k]) and (not ob[k])
    print(f"isti tim {k}: oba ispod projekcije {pab/n:.3f} vs nezavisno {pa/n*pb/n:.3f}")
