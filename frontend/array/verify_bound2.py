#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证：kd→0 时超指向最优权的方向图 = Legendre 最优多项式 Σ(2n+1)P_n(u)/M²。"""
import numpy as np
from scipy.special import eval_legendre
c=343.0
def steer(M,d,f,th): 
    m=np.arange(M); return np.exp(1j*2*np.pi*f/c*d*m*np.cos(th))
def Gam(M,d,f):
    m=np.arange(M); D=np.abs(m[:,None]-m[None,:])*d; return np.sinc(2*f*D/c)

print('══ A. 最优权的方向图 vs Legendre 最优多项式 ══')
for M in [2,3,4]:
    kd=0.02; d=0.035; f=kd*c/(2*np.pi*d)
    G=Gam(M,d,f); a=steer(M,d,f,0.0)
    w=np.linalg.solve(G,a); w=w/(a.conj()@w)
    u=np.linspace(-1,1,9)
    B=np.array([w.conj()@steer(M,d,f,np.arccos(uu)) for uu in u])
    P=sum((2*n+1)*eval_legendre(n,u) for n in range(M))/M**2
    err=np.max(np.abs(np.abs(B)-np.abs(P)))
    print('  M=%d kd=%.3f  max|  |B(u)|-|P(u)|  | = %.3e' % (M,kd,err))
    print('       |B| =', np.array2string(np.abs(B),precision=5))
    print('       |P| =', np.array2string(np.abs(P),precision=5))

print('\n══ B. 端射 vs 边射（broadside）的上限对比 ══')
def Gam_(M,d,f): return Gam(M,d,f)
for M in [2,4,8]:
    kd=0.05; d=0.035; f=kd*c/(2*np.pi*d)
    G=Gam(M,d,f)
    for name,th in [('端射 0°',0.0),('边射 90°',np.pi/2)]:
        a=steer(M,d,f,th)
        di=np.real(a.conj()@np.linalg.solve(G,a))
        print('  M=%d %s  DI=%9.4f (%6.3f dB)   M²=%d  M=%d' % (M,name,di,10*np.log10(di),M*M,M))

print('\n══ C. 常用尺寸下，超指向离 M² 还差多少（35 mm、4 麦）══')
M=4; d=0.035
for f in [100,200,300,500,1000,2000,4000]:
    kd=2*np.pi*f/c*d
    G=Gam(M,d,f); a=steer(M,d,f,0.0)
    di=np.real(a.conj()@np.linalg.solve(G,a))
    w=np.linalg.solve(G,a); w=w/(a.conj()@w)
    wng=10*np.log10(abs(w.conj()@a)**2/np.real(w.conj()@w))
    print('  f=%5d Hz kd=%.4f  DI=%6.3f dB (上限 %.3f)  WNG=%9.2f dB'
          % (f,kd,10*np.log10(di),20*np.log10(M),wng))

print('\n══ D. WNG 的幂次：拟合 vs 20(M−1) ══')
for M in [2,3,4,5]:
    d=0.035; kds=np.array([0.05,0.02])
    ws=[]
    for kd in kds:
        f=kd*c/(2*np.pi*d); G=Gam(M,d,f); a=steer(M,d,f,0.0)
        w=np.linalg.solve(G,a); w=w/(a.conj()@w)
        ws.append(10*np.log10(abs(w.conj()@a)**2/np.real(w.conj()@w)))
    sl=(ws[1]-ws[0])/(np.log10(kds[1])-np.log10(kds[0]))
    print('  M=%d  拟合斜率 %.2f dB/dec   理论 20(M-1)=%d   = %d dB/oct  (=6×%d)'
          % (M,sl,20*(M-1),6*(M-1),M-1))
