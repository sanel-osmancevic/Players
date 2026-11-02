import json, math
exec(open('backtest.py').read().split('# 1) zaboravljanje')[0])
from statistics import NormalDist
N=NormalDist()
def sd_f(mu, v, c, W):
    av=sum(v)/len(v); sdE=math.sqrt(sum((a-av)**2 for a in v)/max(1,len(v)-1)) if len(v)>1 else 0
    return math.sqrt((sdE**2*len(v)+(math.sqrt(max(mu,.5))*c)**2*W)/(len(v)+W))
def ll(p,y): p=min(max(p,.02),.98); return -math.log(p if y else 1-p)
OFF={'pts':(-3,-1,1,3),'reb':(-1,0,1),'ast':(-1,0,1)}
U=[(n,R,projekcija(n,R,0.9,0.9,30)) for n,R in cilj()]; U=[u for u in U if u[2]]
def oc(k,i,c,W,rs):
    s=m=0
    for n,R,p in U:
        if R not in rs: continue
        mu=p[k]; y=G[n][R][2+i]; sd=sd_f(mu,p[k+'_v'],c,W)
        for o in OFF[k]:
            L=math.floor(mu)+.5+o
            if L<.5: continue
            s+=ll(1-N.cdf((L-mu)/sd),y>L); m+=1
    return s/m
for i,k in enumerate(K3):
    cs=[1.4,1.7,2.0,2.3,2.6] if k=='pts' else [0.9,1.1,1.35,1.6,1.9]
    b=min((oc(k,i,c,W,range(3,8)),c,W) for c in cs for W in (2,4,8,16))
    old=(2.0 if k=='pts' else 1.35,4)
    print(k,'najbolje na 3-7:',b[1:],'| test 8-9: staro',round(oc(k,i,*old,(8,9)),4),'novo',round(oc(k,i,b[1],b[2],(8,9)),4))
