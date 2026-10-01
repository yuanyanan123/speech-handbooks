#!/usr/bin/env python3
import numpy as np, mpmath as mp
mp.mp.dps=60
c=343.0
def exact(M,d,f):
    kd=mp.mpf(2)*mp.pi*f/c*d
    G=mp.matrix(M,M)
    for i in range(M):
        for j in range(M):
            x=kd*abs(i-j); G[i,j]=mp.mpf(1) if x==0 else mp.sin(x)/x
    a=mp.matrix([mp.e**(1j*kd*k) for k in range(M)])
    return np.array([complex(v) for v in mp.lu_solve(G,a)])
def npG(M,d,f):
    m=np.arange(M); D=np.abs(m[:,None]-m[None,:])*d
    return np.sinc(2*f*D/c), np.exp(1j*2*np.pi*f/c*d*np.arange(M))

print('══ inv vs solve：按条件数分档，各档取多组 ══')
rows={}
for M in [3,4,5,6,8]:
    for d in [0.02,0.035,0.05]:
        for f in [80,150,300,600,1200,2500]:
            G,a=npG(M,d,f)
            k=np.linalg.cond(G)
            if k>1e15: continue
            ex=exact(M,d,f)
            ei=np.linalg.norm(np.linalg.inv(G)@a-ex)/np.linalg.norm(ex)
            es=np.linalg.norm(np.linalg.solve(G,a)-ex)/np.linalg.norm(ex)
            b=int(np.log10(max(k,1)))//3
            rows.setdefault(b,[]).append((ei,es))
for b in sorted(rows):
    v=np.array(rows[b])
    print('  cond ~1e%-2d–1e%-2d (%2d 组)  inv 中位 %.2e   solve 中位 %.2e   比值中位 %.2f'
          %(3*b,3*b+2,len(v),np.median(v[:,0]),np.median(v[:,1]),
            np.median(v[:,0]/np.maximum(v[:,1],1e-300))))

print('\n══ float32 协方差：直流偏置越大越致命 ══')
rng=np.random.default_rng(0); M,N=8,200000
for dc in [0., 10., 100., 1000.]:
    X=(rng.standard_normal((M,N))+1j*rng.standard_normal((M,N)))/np.sqrt(2)+dc
    R64=(X@X.conj().T)/N
    X32=X.astype(np.complex64)
    R32=(X32@X32.conj().T)/np.complex64(N)
    # 去掉直流之后的"真"协方差
    Xc=X-X.mean(1,keepdims=True); Rc=(Xc@Xc.conj().T)/N
    e64=np.linalg.norm((R64-np.outer(X.mean(1),X.mean(1).conj()))-Rc)/np.linalg.norm(Rc)
    e32=np.linalg.norm((R32-np.outer(X.mean(1),X.mean(1).conj()))-Rc)/np.linalg.norm(Rc)
    print('  直流 %6.0f  float64 去均值后误差 %.2e   float32 %.2e'%(dc,e64,e32))
print('  → 结论不是"别用 float32"，是"先去均值/去直流，再累积协方差"')
