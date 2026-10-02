#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""球阵 WNG 闭式 vs 数值；以及双耳部分的全部数字。"""
import numpy as np
from scipy.special import spherical_jn, spherical_yn, sph_harm_y
c = 343.0

def fib(Q):
    i = np.arange(Q) + .5
    ph = np.arccos(1 - 2 * i / Q); th = np.pi * (1 + 5 ** .5) * i
    return np.stack([np.sin(ph) * np.cos(th), np.sin(ph) * np.sin(th), np.cos(ph)], 1)
def sh(n, m, u):
    t = np.arccos(np.clip(u[..., 2], -1, 1)); p = np.arctan2(u[..., 1], u[..., 0])
    return sph_harm_y(n, m, t, p)
def bn_open(n, kr):  return 4 * np.pi * (1j ** n) * spherical_jn(n, kr)
def bn_rigid(n, kr):
    j = spherical_jn(n, kr); jp = spherical_jn(n, kr, derivative=True)
    h = j - 1j * spherical_yn(n, kr); hp = jp - 1j * spherical_yn(n, kr, derivative=True)
    return 4 * np.pi * (1j ** n) * (j - jp / hp * h)

def wng_closed(Q, N, kr, bfun):
    s = sum((2 * n + 1) / abs(bfun(n, kr)) ** 2 for n in range(N + 1))
    return Q * (N + 1) ** 4 / ((4 * np.pi) ** 2 * s)

def modal_w(Q, N, kr, pu, look, bfun):
    wH = np.zeros(Q, complex)
    for n in range(N + 1):
        b = bfun(n, kr)
        for m in range(-n, n + 1):
            wH += (4 * np.pi / Q) * np.conj(sh(n, m, pu)) * sh(n, m, look) / b
    return np.conj(wH)

print('=' * 70)
print('A. WNG 闭式  Q(N+1)^4 / [(4π)² Σ(2n+1)/|b_n|²]   与数值对照（开球, Q=64, r=42mm）')
Q, r = 64, .042; pu = fib(Q); look = np.array([0., 0., 1.])
print('   %-3s %-7s %8s %12s %12s' % ('N', 'f', 'kr', '闭式 WNG dB', '数值 WNG dB'))
for N in [1, 2, 3, 4]:
    for f in [250, 500, 1000, 2000, 4000]:
        kr = 2 * np.pi * f * r / c
        w = modal_w(Q, N, kr, pu, look, bn_open)
        a = np.exp(1j * kr * (pu @ look))
        num = abs(np.vdot(w, a)) ** 2 / np.vdot(w, w).real
        print('   %-3d %-7d %8.3f %12.2f %12.2f'
              % (N, f, kr, 10 * np.log10(wng_closed(Q, N, kr, bn_open)), 10 * np.log10(num)))

print('=' * 70)
print('B. 刚性球 vs 开球：同阶同频的 WNG（Q=64, r=42mm）')
print('   %-3s %-7s %12s %12s' % ('N', 'f', '开球 dB', '刚性球 dB'))
for N in [2, 4]:
    for f in [250, 500, 1000, 2000, 4000, 6000]:
        kr = 2 * np.pi * f * r / c
        print('   %-3d %-7d %12.2f %12.2f' % (N, f,
              10 * np.log10(wng_closed(Q, N, kr, bn_open)),
              10 * np.log10(wng_closed(Q, N, kr, bn_rigid))))

print('=' * 70)
print('C. 「WNG ≥ 0 dB」所需的最低频率（Q=64, r=42mm, 刚性球）')
ff = np.arange(80, 8000, 5.)
for N in range(1, 6):
    w = np.array([10 * np.log10(wng_closed(Q, N, 2 * np.pi * f * r / c, bn_rigid)) for f in ff])
    ok = ff[w >= 0]
    print('   N=%d  DI 上限 %5.2f dB   WNG≥0dB 起始于 %s Hz'
          % (N, 20 * np.log10(N + 1), ('%.0f' % ok[0]) if len(ok) else '全频段不达标'))

print('=' * 70)
print('D. 双耳：ITD')
a_head = 0.0875
for th in [15, 30, 45, 60, 90]:
    t = np.radians(th)
    wood = a_head / c * (t + np.sin(t))
    kuhn_lo = 3 * a_head / c * np.sin(t)
    kuhn_hi = 2 * a_head / c * np.sin(t)
    print('   θ=%2d°  Woodworth %6.1f µs   低频(3a/c·sinθ) %6.1f µs   高频(2a/c·sinθ) %6.1f µs'
          % (th, wood * 1e6, kuhn_lo * 1e6, kuhn_hi * 1e6))
itd_max = a_head / c * (np.pi / 2 + 1)
print('   最大 ITD (θ=90°, Woodworth) = %.1f µs' % (itd_max * 1e6))
print('   相位 ITD 开始有歧义: f = 1/(2·ITD) = %.0f Hz' % (1 / (2 * itd_max)))
print('   头径 2a = %.1f cm 等于一个波长的频率 f = c/2a = %.0f Hz' % (2 * a_head * 100, c / (2 * a_head)))

print('=' * 70)
print('E. 双耳 MVDR：目标线索保住了，残余噪声被搬到目标方向')
rng = np.random.default_rng(3)
M = 6                                  # 每侧 3 麦，合成 6 通道
B = (rng.normal(size=(M, M)) + 1j * rng.normal(size=(M, M))) / np.sqrt(2)
Rn = B @ B.conj().T
a = (rng.normal(size=M) + 1j * rng.normal(size=M)) / np.sqrt(2)   # 目标的声学传函（含头影）
iL, iR = 0, 3                                                      # 左右参考麦
aL, aR = a[iL], a[iR]
wm = np.linalg.solve(Rn, a); wm = wm / (a.conj() @ wm)             # 单通道 MVDR
wL = np.conj(aL) * wm; wR = np.conj(aR) * wm                       # 双耳 MVDR
print('   目标 ITF（输入）      = %.4f %+.4fj' % ((aL / aR).real, (aL / aR).imag))
tL = wL.conj() @ a; tR = wR.conj() @ a
print('   目标 ITF（输出）      = %.4f %+.4fj   ← 完全保住' % ((tL / tR).real, (tL / tR).imag))
# 干扰：取一个与目标无关的方向
ai = (rng.normal(size=M) + 1j * rng.normal(size=M)) / np.sqrt(2)
print('   干扰 ITF（输入）      = %.4f %+.4fj' % ((ai[iL] / ai[iR]).real, (ai[iL] / ai[iR]).imag))
nL = wL.conj() @ ai; nR = wR.conj() @ ai
print('   干扰 ITF（输出）      = %.4f %+.4fj   ← 变成了目标的 ITF' % ((nL / nR).real, (nL / nR).imag))
print('   两者之差 |Δ| = %.2e  （0 表示干扰被搬到了目标方向）'
      % abs(nL / nR - aL / aR))

print('=' * 70)
print('F. MWF-N：用 η 把噪声线索换回来（噪声 ITF 从目标方向滑回原方向）')
for eta in [0, .1, .2, .35, .5, .7, 1.]:
    oL = (1 - eta) * (wL.conj() @ ai) + eta * ai[iL]
    oR = (1 - eta) * (wR.conj() @ ai) + eta * ai[iR]
    # 噪声抑制量（相对不处理）
    nr = 20 * np.log10(abs(oL) / abs(ai[iL]))
    err = abs(oL / oR - ai[iL] / ai[iR]) / abs(ai[iL] / ai[iR])
    print('   η=%.2f  左耳噪声 %+6.2f dB   噪声 ITF 相对误差 %6.1f%%' % (eta, nr, err * 100))
