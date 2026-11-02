import json, math, statistics as S
exec(open('backtest.py').read().split('# 1) zaboravljanje')[0])
def err(par, rounds):
    dm,dr,pw=par; e={k:[] for k in ('min',)+K3}
    for n,R in cilj():
        if R not in rounds: continue
        p=projekcija(n,R,dm,dr,pw)
        if not p: continue
        a=G[n][R]; e['min'].append(abs(a[0]-p['min']))
        for i,k in enumerate(K3): e[k].append(abs(a[2+i]-p[k]))
    return {k:round(S.mean(v),3) for k,v in e.items()}
for par in [(0.85,0.85,15),(1.0,0.9,60),(0.9,0.9,30),(1.0,0.9,30),(0.9,0.85,60)]:
    print(par,'trening 3-7',err(par,range(3,8)),'| test 8-9',err(par,(8,9)))
