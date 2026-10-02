#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WPE：多次实现取中位数，稳定地量出加权/延迟/阶数的贡献。"""
import numpy as np
D_EARLY = 3

def make_rir(rng, M, Lt=40, T60=12.0):
    dec = np.exp(-np.arange(Lt)*3*np.log(10)/T60)
    h = (rng.standard_normal((M,Lt))+1j*rng.standard_normal((M,Lt)))/np.sqrt(2)*dec
    h[:,0] = np.exp(1j*rng.uniform(0,2*np.pi,M))
    return h

def envelope(rng, T, floor_db):
    lam = np.full(T, 10**(floor_db/10)); t=0
    while t<T:
        L=rng.integers(20,70)
        if rng.random()<0.55: lam[t:t+L]=10**rng.uniform(-0.3,0.3)
        t+=L
    return np.convolve(lam, np.hanning(9)/np.hanning(9).sum(), 'same')

def wpe(x, K, D, iters=6, weighted=True):
    M,T = x.shape; d = x.copy()
    for _ in range(iters):
        lam = np.maximum(np.mean(np.abs(d)**2,0),1e-10) if weighted else np.ones(T)
        X = np.zeros((M*K,T),complex)
        for k in range(K):
            t0=D+k; X[k*M:(k+1)*M, t0:] = x[:, :T-t0]
        Wt=1.0/lam
        R=(X*Wt)@X.conj().T; P=(X*Wt)@x.conj().T
        G=np.linalg.solve(R+1e-9*np.trace(R)/len(R)*np.eye(M*K),P)
        d = x - G.conj().T@X
    return d

def srr(y, ref):
    a=(ref.conj()@y)/(ref.conj()@ref)
    return 10*np.log10(np.sum(np.abs(a*ref)**2)/np.sum(np.abs(y-a*ref)**2))

def trial(seed, floor_db=-40, M=4, T=6000, K=10, D=3, weighted=True):
    rng=np.random.default_rng(seed)
    lam=envelope(rng,T,floor_db); h=make_rir(rng,M)
    s=(rng.standard_normal(T)+1j*rng.standard_normal(T))/np.sqrt(2)*np.sqrt(lam)
    x=np.array([np.convolve(s,h[m])[:T] for m in range(M)])
    e=np.array([np.convolve(s,np.r_[h[m,:D_EARLY],np.zeros(h.shape[1]-D_EARLY)])[:T] for m in range(M)])
    y=wpe(x,K,D,weighted=weighted)
    return srr(x[0],e[0]), srr(y[0],e[0])

N=25
print('══ 1. 加权 vs 不加权（%d 次实现的中位数）══' % N)
for fl,lab in [(-5,'弱动态'),(-20,'中'),(-40,'语音式强动态')]:
    ins=[];w=[];u=[]
    for k in range(N):
        i1,o1=trial(100+k,fl,weighted=True); i2,o2=trial(100+k,fl,weighted=False)
        ins.append(i1); w.append(o1); u.append(o2)
    print('  %-14s 输入 %5.1f dB → WPE 加权 %5.1f dB，不加权 %5.1f dB（差 %+4.1f）'
          % (lab,np.median(ins),np.median(w),np.median(u),np.median(w)-np.median(u)))

print('\n══ 2. 预测延迟 D（加权，语音式动态）══')
for D in [0,1,2,3,4,6,8]:
    v=[trial(200+k,-40,D=D)[1] for k in range(N)]
    print('   D=%d  %6.2f dB' % (D,np.median(v)))
print('   （D=0 时把直达也预测掉了，"残余"极小但目标已不在）')

print('\n══ 3. 预测阶 K 与通道数 M（加权，D=3）══')
for K in [2,5,10,20,40]:
    v=[trial(300+k,-40,K=K)[1] for k in range(N)]
    print('   K=%2d  %6.2f dB' % (K,np.median(v)))
print()
for M in [1,2,4,8]:
    v=[trial(400+k,-40,M=M)[1] for k in range(N)]
    print('   M=%d   %6.2f dB' % (M,np.median(v)))
