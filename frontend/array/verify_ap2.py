#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
c=343.0
def di_das(M,d,f):
    kd=2*np.pi*f/c*d; m=np.arange(M); D=np.abs(m[:,None]-m[None,:])
    return M**2/np.real(np.sinc(kd*D/np.pi).sum())

print('══ A. 低频展开 DI ≈ 1 + (kd)²(M²−1)/36 的精度 ══')
print('   M   d(mm)  f(Hz)   kd     精确(dB)   展开(dB)    差')
for M,d,f in [(2,.015,500),(4,.035,150),(4,.035,400),(8,.030,150),(8,.030,400),
              (16,.020,200),(4,.050,300),(8,.035,300)]:
    kd=2*np.pi*f/c*d
    ex=10*np.log10(di_das(M,d,f)); ap=10*np.log10(1+kd**2*(M*M-1)/36)
    print('  %3d  %5.1f  %5d  %6.3f  %8.4f  %8.4f  %+.4f'%(M,d*1000,f,kd,ex,ap,ex-ap))

print('\n══ B. 用"整孔径" L ≜ Md 时，DI 只由 kL 决定 ══')
print('   kL      各 M 的精确 DI(dB)                                   展开值')
for kL in [1.0,2.0,3.053,4.0,6.0]:
    row=[]
    for M in [4,8,16,32,64]:
        f=1000.; lam=c/f; L=kL*lam/(2*np.pi); d=L/M
        row.append(10*np.log10(di_das(M,d,f)))
    print('  %5.3f   '%kL + ' '.join('M=%-3d %5.3f'%(M,v) for M,v in zip([4,8,16,32,64],row))
          + '   %5.3f'%(10*np.log10(1+kL**2/36)))

print('\n══ C. 孔径判据（M ≫ 1 的极限，L = Md）══')
for tgt in [0.5,1.0,2.0,3.0,6.0]:
    kL=np.sqrt(36*(10**(tgt/10)-1)); print('   DI=%.1f dB → kL=%.3f → L=%.3fλ'%(tgt,kL,kL/(2*np.pi)))
print('\n══ D. 主瓣 −3 dB 全宽（sinθ 量度）= 0.886 λ/(Md) ══')
from scipy.optimize import brentq
def AF(M,kd,s):
    psi=kd*s
    return np.abs(np.where(np.abs(np.sin(psi/2))<1e-14,1.0,np.sin(M*psi/2)/(M*np.sin(psi/2))))
for M in [4,8,16,32,64,128]:
    d=.02; f=2000.; lam=c/f; kd=2*np.pi*d/lam
    s3=brentq(lambda s:AF(M,kd,s)-10**(-3/20),1e-12,2*np.pi/(M*kd))
    print('   M=%3d  2·sinθ₃·Md/λ = %.4f   （极限 0.8859）'%(M,2*s3*M*d/lam))
print('\n══ E. 换成角度（边射、小角近似 sinθ≈θ）══')
for LL in [0.5,1,2,4,8]:
    th=np.degrees(np.arcsin(min(0.886/2/LL,1)))*2
    print('   L = %4.1f λ → 主瓣 −3 dB 全宽 ≈ %5.1f°   （经验式 51°/(L/λ) = %5.1f°）'
          %(LL,th,51/LL))
