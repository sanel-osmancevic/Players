import statistics as S
src=open('bt_prilike.py').read()
exec(src.split('# B) širina')[0].replace("print(","(lambda *a,**k:None)("))
exec('#'+src.split('# B) širina')[1].split('def start_udeo')[0])
def st5(n,R):
    rr=sorted(r for r in G[n] if r<R)[-5:]; s=[G[n][r][1] for r in rr]; return sum(s)/len(s), G[n][rr[-1]][1]
rows=[]
for u in U:
    n,R=u['n'],u['R']; nm=NEM.get((TIM[n],R)); 
    if nm is None: continue
    a,last=st5(n,R); err=abs(G[n][R][0]-u['p']['min'])/max(u['p']['min'],1)
    rows.append((nm/LGN[R], a, last, err, u['p']['min']))
rows.sort(key=lambda x:x[0]); t=len(rows)//3
for nm_,L in (('mirni timovi',rows[:t]),('srednji',rows[t:2*t]),('nemirni timovi',rows[2*t:])):
    print(nm_, 'rel. greška minuta', round(S.mean(r[3] for r in L),3), len(L))
for lab,f in (('sigurni starteri (5/5 i startovao poslednju)',lambda r:r[1]>=0.99 and r[2]==1),('pretežno starteri (3-4/5)',lambda r:0.59<r[1]<0.99),('klupa (0-2/5)',lambda r:r[1]<=0.41)):
    L=[r for r in rows if f(r)]; print(lab,'rel. greška minuta',round(S.mean(r[3] for r in L),3),'| apsolutna',round(S.mean(r[3]*max(r[4],1) for r in L),2),len(L))
# u minutima 20+: nemirni vs mirni
L=[r for r in rows if r[4]>=20]; L.sort(key=lambda x:x[0]); t=len(L)//3
print('20+ min: mirni',round(S.mean(r[3] for r in L[:t]),3),'nemirni',round(S.mean(r[3] for r in L[2*t:]),3))
