#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高精度验证端射/边射的 kd→0 极限。"""
import mpmath as mp
import numpy as np
from scipy.special import eval_legendre
mp.mp.dps = 80

def limit_DI(M, th_deg, kd):
    th = mp.mpf(th_deg)*mp.pi/180
    a = mp.matrix([mp.e**(1j*kd*m*mp.cos(th)) for m in range(M)])
    G = mp.matrix(M, M)
    for i in range(M):
        for j in range(M):
            x = kd*abs(i-j)
            G[i,j] = mp.mpf(1) if x==0 else mp.sin(x)/x
    x = mp.lu_solve(G, a)
    return mp.re(sum(mp.conj(a[i])*x[i] for i in range(M)))

print('══ 端射极限 → M²（80 位精度）══')
for M in [2,3,4,6,8,10]:
    v = [limit_DI(M,0,mp.mpf(10)**(-k)) for k in (2,3,4)]
    print('  M=%2d  kd=1e-2 %.10f  1e-3 %.10f  1e-4 %.10f   M²=%d'
          % (M, float(v[0]), float(v[1]), float(v[2]), M*M))

print('\n══ 边射极限 → Σ_{n 偶, n≤M−1}(2n+1)P_n(0)²（不是 M²！）══')
for M in [2,3,4,5,6,8]:
    s = sum((2*n+1)*eval_legendre(n,0.0)**2 for n in range(M) if n%2==0)
    v = float(limit_DI(M,90,mp.mpf('1e-4')))
    print('  M=%2d  数值 %.8f   解析 Σ(2n+1)P_n(0)² = %.8f   M=%d  M²=%d  %s'
          % (M, v, s, M, M*M, '✓' if abs(v-s)<1e-5 else '✗'))
