#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WPE 的加权到底在保护什么：语音式的强时变包络。"""
import numpy as np
rng = np.random.default_rng(7)
M, T = 4, 6000
D_EARLY = 3

def make_rir(M, Lt=40, T60=12.0):
    h = np.zeros((M, Lt), complex)
    dec = np.exp(-np.arange(Lt)*3*np.log(10)/T60)
    for m in range(M):
        h[m] = (rng.standard_normal(Lt)+1j*rng.standard_normal(Lt))/np.sqrt(2)*dec
        h[m,0] = np.exp(1j*rng.uniform(0,2*np.pi))
    return h

def speechlike(T):
    """语音式包络：随机的"音节"，高低差 40 dB"""
    lam = np.full(T, 1e-4)
    t = 0
    while t < T:
        L = rng.integers(20, 70)
        if rng.random() < 0.55:
            lam[t:t+L] = 10**rng.uniform(-0.3, 0.3)
        t += L
    return np.convolve(lam, np.hanning(9)/np.hanning(9).sum(), 'same')

def wpe(x, K, D, iters=6, weighted=True):
    M, T = x.shape
    d = x.copy()
    for _ in range(iters):
        lam = np.maximum(np.mean(np.abs(d)**2,0), 1e-10) if weighted else np.ones(T)
        X = np.zeros((M*K, T), complex)
        for k in range(K):
            t0 = D+k; X[k*M:(k+1)*M, t0:] = x[:, :T-t0]
        Wt = 1.0/lam
        R = (X*Wt)@X.conj().T; P = (X*Wt)@x.conj().T
        G = np.linalg.solve(R+1e-9*np.trace(R)/len(R)*np.eye(M*K), P)
        d = x - G.conj().T@X
    return d

def srr(y, ref):
    a = (ref.conj()@y)/(ref.conj()@ref)
    return 10*np.log10(np.sum(np.abs(a*ref)**2)/np.sum(np.abs(y-a*ref)**2))
def dyn(z):
    e = np.convolve(np.abs(z)**2, np.ones(9)/9, 'same')
    return 10*np.log10(np.percentile(e,95)/np.percentile(e,10))

lam = speechlike(T); h = make_rir(M)
s = (rng.standard_normal(T)+1j*rng.standard_normal(T))/np.sqrt(2)*np.sqrt(lam)
x = np.array([np.convolve(s, h[m])[:T] for m in range(M)])
early = np.array([np.convolve(s, np.r_[h[m,:D_EARLY], np.zeros(h.shape[1]-D_EARLY)])[:T]
                  for m in range(M)])

print('══ 目标：去掉晚期混响，同时保住语音的动态 ══')
print('  %-24s %10s %14s' % ('', '残余混响(dB)', '包络动态范围(dB)'))
print('  %-24s %10.2f %14.1f' % ('干净的"直达+早期"', float('inf') if False else 99.0, dyn(early[0])))
print('  %-24s %10.2f %14.1f' % ('输入（含混响）', srr(x[0], early[0]), dyn(x[0])))
yw = wpe(x,10,3,weighted=True); yu = wpe(x,10,3,weighted=False)
print('  %-24s %10.2f %14.1f' % ('WPE（加权）', srr(yw[0],early[0]), dyn(yw[0])))
print('  %-24s %10.2f %14.1f' % ('不加权线性预测', srr(yu[0],early[0]), dyn(yu[0])))

print('\n══ 加权在不同动态范围下的收益 ══')
print('   包络动态   WPE(dB)   不加权(dB)   差')
for hi in [0.0, 0.5, 1.0, 1.5, 2.0]:
    lam2 = np.full(T, 10**(-2*hi)); t=0
    while t<T:
        L=rng.integers(20,70)
        if rng.random()<0.55: lam2[t:t+L]=10**rng.uniform(-0.3,0.3)
        t+=L
    lam2=np.convolve(lam2,np.hanning(9)/np.hanning(9).sum(),'same')
    s2=(rng.standard_normal(T)+1j*rng.standard_normal(T))/np.sqrt(2)*np.sqrt(lam2)
    x2=np.array([np.convolve(s2,h[m])[:T] for m in range(M)])
    e2=np.array([np.convolve(s2,np.r_[h[m,:D_EARLY],np.zeros(h.shape[1]-D_EARLY)])[:T] for m in range(M)])
    a=srr(wpe(x2,10,3,True)[0],e2[0]); b=srr(wpe(x2,10,3,False)[0],e2[0])
    print('   %5.0f dB   %7.2f   %8.2f   %+5.2f' % (dyn(e2[0]), a, b, a-b))
