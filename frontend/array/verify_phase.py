#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2° 相位预算的推导与蒙特卡洛验证。"""
import numpy as np
rng = np.random.default_rng(20260915)
c = 343.0

def setup(M, d, f, eps):
    kd = 2*np.pi*f/c*d
    G = np.array([[np.sinc(kd*abs(i-j)/np.pi) for j in range(M)] for i in range(M)])
    a = np.exp(1j*kd*np.arange(M))
    w = np.linalg.solve(G+eps*np.eye(M), a); w = w/(a.conj()@w)
    di = abs(w.conj()@a)**2/np.real(w.conj()@G@w)
    wng = abs(w.conj()@a)**2/np.real(w.conj()@w)
    return G, a, w, di, wng

print('══ 1. 误差矢量的协方差恰好是 σ²·I ══')
M = 8; sg, sp = 0.03, 0.03
N = 400000
g = 1+sg*rng.standard_normal((N, M)); ph = sp*rng.standard_normal((N, M))
a = np.exp(1j*2*np.pi*0.3*np.arange(M))
at = a*g*np.exp(1j*ph)
e = at-a
R = (e.conj().T@e)/N
print('  σ²理论 = %.6f   对角均值 = %.6f   非对角最大模 = %.2e'
      % (sg**2+sp**2, np.real(np.diag(R)).mean(), np.abs(R-np.diag(np.diag(R))).max()))

print('\n══ 2. 泄漏比 = σ²/WNG（理论 vs 蒙特卡洛）══')
for eps, tag in [(0.0,'无加载'), (1e-3,'ε=1e−3'), (1e-2,'ε=1e−2'), (1e-1,'ε=0.1')]:
    G, a, w, di, wng = setup(4, 0.035, 1000, eps)
    for s in [0.01, 0.03]:
        N = 200000
        gg = 1+ (s/np.sqrt(2))*rng.standard_normal((N,4))
        pp = (s/np.sqrt(2))*rng.standard_normal((N,4))
        at = a*gg*np.exp(1j*pp)
        leak = np.mean(np.abs((at-a)@w.conj())**2)
        print('  %-8s WNG=%7.2f dB  σ=%.3f  泄漏 理论 %.3e  实测 %.3e  比值 %.4f'
              % (tag, 10*np.log10(wng), s, s**2/wng, leak, leak/(s**2/wng)))

print('\n══ 3. 相位预算表：泄漏低 10 dB 时允许的 σ ══')
print('  WNG(dB)  σ_max(rad)  σ_max(度)  等效幅度(dB)')
for wdb in [6, 0, -10, -20, -30, -40]:
    wl = 10**(wdb/10); s = np.sqrt(0.1*wl)
    amp = 20*np.log10(1+s)
    print('  %+6.0f    %8.4f   %7.2f°   %6.2f dB' % (wdb, s, np.degrees(s), amp))
print('  经验式：σ_max(度) ≈ 18.1 × 10^(WNG_dB/20)')
for wdb in [0,-20,-40]:
    print('     WNG=%+d dB → %.2f°（精确 %.2f°）'
          % (wdb, 18.1*10**(wdb/20), np.degrees(np.sqrt(0.1*10**(wdb/10)))))

print('\n══ 4. 蒙特卡洛：实测 DI 随失配退化（4 麦 35mm 1 kHz）══')
for eps, tag in [(0.0,'无加载 WNG=−25.5dB'), (1e-2,'ε=0.01 WNG=−5.0dB'), (1e-1,'ε=0.1')]:
    G, a, w, di0, wng = setup(4, 0.035, 1000, eps)
    print('  %-22s 标称 DI=%.2f dB  WNG=%.1f dB' % (tag, 10*np.log10(di0), 10*np.log10(wng)))
    for sdeg in [0.2, 0.5, 1, 2, 5, 10]:
        s = np.radians(sdeg); N = 4000
        gg = 1+s*rng.standard_normal((N,4)); pp = s*rng.standard_normal((N,4))
        wt = w[None,:]*gg*np.exp(-1j*pp)
        num = np.abs(np.einsum('ij,j->i', wt.conj(), a))**2
        den = np.real(np.einsum('ij,jk,ik->i', wt.conj(), G, wt))
        d = 10*np.log10(num/den)
        print('     σ=%5.1f°（幅 %.2f dB）→ DI 中位 %6.2f dB  损失 %5.2f dB  最差5%% %6.2f dB'
              % (sdeg, 20*np.log10(1+s), np.median(d), 10*np.log10(di0)-np.median(d),
                 np.percentile(d,5)))
