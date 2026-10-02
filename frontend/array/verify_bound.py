#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§04 两条边界：DAS WNG = M，端射超指向 DI -> M²（Uzkov）。全部数值核对。"""
import numpy as np
from numpy.polynomial import legendre as L
from scipy.special import eval_legendre
np.set_printoptions(precision=6, suppress=False)
c = 343.0

def steer(M, d, f, th):      # 端射 th=0 沿轴
    m = np.arange(M)
    return np.exp(1j * 2*np.pi*f/c * d * m * np.cos(th))

def Gam(M, d, f):
    m = np.arange(M)
    D = np.abs(m[:,None]-m[None,:]) * d
    return np.sinc(2*f*D/c)   # np.sinc(x)=sin(pi x)/(pi x); sinc(kd)=sin(kd)/kd, kd=2pi f D/c -> x=2fD/c

print('══ 1. DAS 的 WNG 精确等于 M ══')
for M in [2,4,8,16]:
    for f in [300, 2000, 6000]:
        d = 0.035
        a = steer(M, d, f, 0.0)
        w = a/M
        wng = abs(w.conj()@a)**2 / np.real(w.conj()@w)
        print('  M=%2d f=%5d  WNG=%.12f  10log=%.4f dB  (M=%d, 10logM=%.4f)'
              % (M,f,wng,10*np.log10(wng),M,10*np.log10(M)))

print('\n══ 2. 端射超指向 DI = aᴴΓ⁻¹a → M² ══')
for M in [2,3,4,6,8]:
    print('  M=%d  (M²=%d, 20log₁₀M=%.3f dB)' % (M, M*M, 20*np.log10(M)))
    for kd in [1.0, 0.3, 0.1, 0.03, 0.01, 0.003, 0.001]:
        d = 0.035; f = kd*c/(2*np.pi*d)
        G = Gam(M,d,f); a = steer(M,d,f,0.0)
        try:
            Gi = np.linalg.solve(G, a)
        except Exception as e:
            print('    kd=%.4f  奇异' % kd); continue
        di = np.real(a.conj()@Gi)
        cond = np.linalg.cond(G)
        print('    kd=%6.3f f=%8.1f Hz  DI=%12.6f (%7.3f dB)  DI/M²=%.6f  cond(Γ)=%.2e'
              % (kd, f, di, 10*np.log10(abs(di)), di/M**2, cond))

print('\n══ 3. Uzkov 的 Cauchy–Schwarz 界：Σ_{n=0}^{M-1}(2n+1) = M² ══')
for M in range(1,9):
    s = sum(2*n+1 for n in range(M))
    print('  M=%d  Σ(2n+1)=%d  M²=%d  %s' % (M, s, M*M, '✓' if s==M*M else '✗'))

print('\n══ 4. 用 Legendre 系数 c_n ∝ (2n+1) 直接构造，验证 Q=M² ══')
for M in [2,3,4,5,6]:
    cn = np.array([2*n+1 for n in range(M)], float)
    num = cn.sum()**2                      # |P(1)|², P_n(1)=1
    den = sum(cn[n]**2/(2*n+1) for n in range(M))   # (1/2)∫|P|²du
    print('  M=%d  Q=|ΣC|²/Σ(c²/(2n+1))=%.10f   M²=%d' % (M, num/den, M*M))
    # 顺便验证 (1/2)∫P²du 的 Legendre 正交性
    u = np.linspace(-1,1,200001)
    P = sum(cn[n]*eval_legendre(n,u) for n in range(M))
    quad = 0.5*np.trapezoid(P**2,u)
    print('        数值积分 (1/2)∫P²du=%.8f  解析 Σc²/(2n+1)=%.8f  P(1)=%.6f'
          % (quad, den, sum(cn)))

print('\n══ 5. 超指向的代价：WNG 随 kd 的幂次 ══')
for M in [2,3,4]:
    print('  M=%d  理论斜率 20(M-1) dB/十倍频 = %d' % (M, 20*(M-1)))
    prev=None
    for kd in [0.3,0.1,0.03,0.01]:
        d=0.035; f=kd*c/(2*np.pi*d)
        G=Gam(M,d,f); a=steer(M,d,f,0.0)
        w=np.linalg.solve(G,a); w=w/ (a.conj()@w)
        wng=abs(w.conj()@a)**2/np.real(w.conj()@w)
        db=10*np.log10(wng)
        s='' if prev is None else '  斜率 %.1f dB/dec' % ((db-prev)/np.log10(0.3/1.0) if False else (db-prev)/(np.log10(kd)-np.log10(prevkd)))
        print('    kd=%.3f  WNG=%8.3f dB%s' % (kd, db, s))
        prev=db; prevkd=kd
