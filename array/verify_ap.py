#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§03：主瓣宽度 ≈ λ/L 与孔径下限的定量推导。"""
import numpy as np
from scipy.optimize import brentq
c = 343.0

def AF(M, kd, s):                     # s = sin(θ)，边射
    psi = kd*s
    with np.errstate(invalid='ignore', divide='ignore'):
        v = np.where(np.abs(np.sin(psi/2)) < 1e-12, 1.0,
                     np.sin(M*psi/2)/(M*np.sin(psi/2)))
    return np.abs(v)

print('══ 1. 主瓣 −3 dB 半宽：数值 vs 0.443 λ/L ══')
print('   M    d(mm)  f(Hz)   L(m)   数值 sinθ₃  0.443λ/L   比值   零点 sinθ  λ/(Md)')
for M, d, f in [(4,0.035,4000),(8,0.030,3000),(16,0.020,4000),(8,0.050,1500),(32,0.015,6000)]:
    lam = c/f; kd = 2*np.pi*d/lam; L = (M-1)*d; Ld = M*d
    g = lambda s: AF(M, kd, s) - 10**(-3/20)
    s3 = brentq(g, 1e-9, min(1.0, np.pi/kd*0.9)) if g(1e-9)*g(min(0.99, 2*np.pi/(M*kd)))<0 else np.nan
    # 第一零点
    s0 = 2*np.pi/(M*kd)
    print('  %3d  %5.1f  %5d  %.3f     %.4f     %.4f   %.3f    %.4f   %.4f'
          % (M, d*1000, f, L, s3, 0.443*lam/L, s3/(0.443*lam/L), s0, lam/(M*d)))

print('\n══ 2. 用 Md（不是 (M−1)d）做孔径时的常数 ══')
for M, d, f in [(4,0.035,4000),(8,0.030,3000),(16,0.020,4000),(32,0.015,6000),(64,0.010,6000)]:
    lam = c/f; kd = 2*np.pi*d/lam
    g = lambda s: AF(M, kd, s) - 10**(-3/20)
    s3 = brentq(g, 1e-9, 2*np.pi/(M*kd))
    print('   M=%3d  sinθ₃·(Md)/λ = %.4f   （大 M 极限 0.4429）' % (M, s3*M*d/lam))

print('\n══ 3. DAS 在低频的 DI：精确 vs 1 + (kL)²/36 ══')
def di_das(M, d, f):
    kd = 2*np.pi*f/c*d
    m = np.arange(M); D = np.abs(m[:,None]-m[None,:])
    G = np.sinc(kd*D/np.pi)
    return M**2/np.real(G.sum())
print('   M    d(mm)   f(Hz)    kL     精确 DI(dB)  近似 1+(kL)²/36 (dB)  差')
for M, d, f in [(4,0.035,150),(4,0.035,400),(8,0.030,150),(8,0.030,400),
                (16,0.020,200),(2,0.015,500),(4,0.050,300)]:
    L = (M-1)*d; k = 2*np.pi*f/c; kL = k*L
    ex = 10*np.log10(di_das(M,d,f))
    ap = 10*np.log10(1+kL**2/36)
    print('  %3d  %5.1f   %5d   %6.3f   %8.4f     %8.4f          %+.4f'
          % (M, d*1000, f, kL, ex, ap, ex-ap))

print('\n══ 4. 孔径要多大才有 N dB 的 DI（DAS，扩散场）══')
print('   目标 DI     kL       L/λ      判据说法')
for tgt in [0.5, 1.0, 2.0, 3.0, 6.0]:
    kL = np.sqrt(36*(10**(tgt/10)-1))
    print('    %.1f dB    %.3f    %.3f λ    L = λ/%.2f' % (tgt, kL, kL/(2*np.pi), 1/(kL/(2*np.pi))))
print('   → "孔径至少半波长"这条经验，正好对应 DAS 拿到 1 dB 的 DI')

print('\n══ 5. 精确解：L = λ/2 时各 M 的真实 DI ══')
for M in [2,4,8,16,32]:
    for lo in [0.5, 0.8, 1.0]:
        f = 1000.; lam = c/f; L = lo*lam; d = L/(M-1)
        print('   M=%2d L=%.1fλ  DI=%.3f dB' % (M, lo, 10*np.log10(di_das(M,d,f))), end='')
    print()
