import json, math
exec(open('backtest.py').read().split('# 1) zaboravljanje')[0])
from statistics import NormalDist
N=NormalDist(); M=json.load(open('model_param.json'))
def sd_f(mu, v, c, W):
    av=sum(v)/len(v); sdE=math.sqrt(sum((a-av)**2 for a in v)/max(1,len(v)-1)) if len(v)>1 else 0
    return math.sqrt((sdE**2*len(v)+(math.sqrt(max(mu,.5))*c)**2*W)/(len(v)+W))
def ll(p,y): p=min(max(p,.02),.98); return -math.log(p if y else 1-p)
OFF={'pts':(-3,-1,1,3),'reb':(-1,0,1),'ast':(-1,0,1)}
U=[(n,R,projekcija(n,R,M['dm'],M['dr'],M['pw'])) for n,R in cilj()]; U=[u for u in U if u[2]]
for KP in (3,6,10):
  tr=[u for u in U if u[1]<=7]; te=[u for u in U if u[1]>=8]
  mult={}
  for n in G:
    z=[((G[n][R][2+i]-p[k])/sd_f(p[k],p[k+'_v'],M['sd'][k]['c'],M['sd'][k]['W']))**2 for n2,R,p in tr if n2==n for i,k in enumerate(K3)]
    if z: mult[n]=min(1.3,max(.8,math.sqrt((sum(z)+KP*3)/(len(z)+KP*3))))
  for i,k in enumerate(K3):
    s0=s1=m=0
    for n,R,p in te:
      mu=p[k]; y=G[n][R][2+i]; sd0=sd_f(mu,p[k+'_v'],M['sd'][k]['c'],M['sd'][k]['W']); sd1=sd0*mult.get(n,1)
      for o in OFF[k]:
        L=math.floor(mu)+.5+o
        if L<.5: continue
        s0+=ll(1-N.cdf((L-mu)/sd0),y>L); s1+=ll(1-N.cdf((L-mu)/sd1),y>L); m+=1
    print('K',KP,k,'test kola 8-9: bez',round(s0/m,4),'sa širinom po igraču',round(s1/m,4),m)
