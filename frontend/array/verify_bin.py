#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双耳：刚性球头模型（Rayleigh/Duda–Martens）→ ITD、ILD、双耳 MVDR 的线索畸变。

刚性球面上的总声压（平面波入射，e^{-iωt} 约定）：
   p(a,Θ) = Σ_n (2n+1) i^n [ j_n(ka) - j_n'(ka)/h_n'(ka)·h_n(ka) ] P_n(cosΘ)
用朗斯基行列式  j_n h_n' - j_n' h_n = i/x²  化简方括号为  i / (x² h_n'(x))，
数值上稳定得多（避免两个大数相减）。
"""
import numpy as np
from scipy.special import spherical_jn, spherical_yn
from numpy.polynomial import legendre as Lg
c, A = 343.0, 0.0875

def sphere_H(f, cosT, a=A):
    """返回球面上与入射方向夹角 Θ 处的传函；cosT 可以是数组。"""
    ka = 2 * np.pi * f * a / c
    N = int(np.ceil(ka)) + 30
    n = np.arange(N + 1)
    hp = spherical_jn(n, ka, derivative=True) + 1j * spherical_yn(n, ka, derivative=True)
    coef = (2 * n + 1) * (1j ** n) * 1j / (ka ** 2 * hp)      # 朗斯基化简
    cosT = np.atleast_1d(cosT)
    P = np.stack([Lg.legval(cosT, np.eye(N + 1)[k]) for k in n])   # (N+1, K)
    return coef @ P

def unit(az, el=0.):
    az, el = np.radians(az), np.radians(el)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])

EAR_L, EAR_R = unit(100), unit(-100)

# ── 0. 自检：ka→0 时球面各处传函应趋于同一常数（无 ILD、无 ITD）──
print('=' * 74)
h = sphere_H(20, np.array([1., 0., -1.]))
print('0. 自检 f=20 Hz（ka=0.032）：|H| 在 Θ=0/90/180° = %s  → 应几乎相等'
      % np.round(np.abs(h) / np.abs(h[0]), 4))
h = sphere_H(20, np.array([1., -1.]))
print('   低频极限下 p → 平面波值，相位差 ≈ 0：Δphase = %.3f°'
      % np.degrees(np.angle(h[0] / h[1])))

print('=' * 74)
print('1. ILD（左耳 / 右耳，dB）—— 声源在右侧时右耳更响，故取负号看同侧优势')
print('   %-8s' % 'f (Hz)', ''.join('%8s' % ('%d°' % t) for t in [15, 30, 45, 60, 90]))
for f in [250, 500, 1000, 2000, 4000, 8000]:
    row = []
    for az in [15, 30, 45, 60, 90]:
        s = unit(az)
        hl = sphere_H(f, np.array([s @ EAR_L]))[0]
        hr = sphere_H(f, np.array([s @ EAR_R]))[0]
        row.append(20 * np.log10(abs(hr / hl)))
    print('   %-8d' % f, ''.join('%8.1f' % v for v in row))
print('   （正值 = 同侧耳更响）')

print('=' * 74)
print('2. 由 IPD 反解 ITD，与 Woodworth (a/c)(θ+sinθ) 对照（低频，无相位卷绕）')
print('   %-7s %12s %12s %12s %12s' % ('f', 'θ=30° 模型', 'Woodworth', 'θ=90° 模型', 'Woodworth'))
for f in [100, 200, 300, 500, 700]:
    r = []
    for az in [30, 90]:
        s = unit(az)
        hl = sphere_H(f, np.array([s @ EAR_L]))[0]
        hr = sphere_H(f, np.array([s @ EAR_R]))[0]
        r.append(np.angle(hl / hr) / (2 * np.pi * f) * 1e6)
    w = [A / c * (np.radians(t) + np.sin(np.radians(t))) * 1e6 for t in (30, 90)]
    print('   %-7d %11.1fµ %11.1fµ %11.1fµ %11.1fµ' % (f, r[0], w[0], r[1], w[1]))
print('   注：耳位在 ±100°（略偏后），几何上比 ±90° 略长，模型值应略大于 Woodworth')

print('=' * 74)
print('3. 双耳 MVDR：目标在正前方 0°，干扰在右侧 60°，扩散噪声')
POS = [unit(100 - 4), unit(100 + 4), unit(-100 + 4), unit(-100 - 4)]   # 每侧前后两麦
iL, iR = 0, 2

def steer(f, s):
    return sphere_H(f, np.array([s @ p for p in POS]))

def fibo(Ng):
    i = np.arange(Ng) + .5
    ph = np.arccos(1 - 2 * i / Ng); th = np.pi * (1 + 5 ** .5) * i
    return np.stack([np.sin(ph) * np.cos(th), np.sin(ph) * np.sin(th), np.cos(ph)], 1)

U = fibo(900)
def diffuse_G(f):
    cosT = U @ np.array(POS).T                       # (Ng, 4)
    Aq = sphere_H(f, cosT.ravel()).reshape(cosT.shape)
    G = Aq.conj().T @ Aq / len(U)
    d = np.sqrt(np.real(np.diag(G)))
    return G / np.outer(d, d)

print('   %-7s %10s %10s %10s %10s %11s' %
      ('f', '目标ILD入', '目标ILD出', '干扰ILD入', '干扰ILD出', '阵列增益'))
for f in [500, 1000, 2000, 4000]:
    a = steer(f, unit(0)); ai = steer(f, unit(60))
    G = diffuse_G(f) + 1e-2 * np.eye(4)
    wm = np.linalg.solve(G, a); wm = wm / (a.conj() @ wm)
    wL, wR = np.conj(a[iL]) * wm, np.conj(a[iR]) * wm
    ild = lambda x, y: 20 * np.log10(abs(y / x))
    g = 10 * np.log10(abs(wm.conj() @ a) ** 2 / (wm.conj() @ G @ wm).real)
    print('   %-7d %9.2f %9.2f %9.2f %9.2f %10.2f dB' % (
        f, ild(a[iL], a[iR]), ild(wL.conj() @ a, wR.conj() @ a),
        ild(ai[iL], ai[iR]), ild(wL.conj() @ ai, wR.conj() @ ai), g))
print('   → 目标 ILD 入=出（保住）；干扰 ILD 出 → 塌到目标的值（被搬到正前方）')

print('=' * 74)
print('4. MWF-N：η 的真实取舍（f = 1 kHz，干扰在 60°）')
f = 1000
a = steer(f, unit(0)); ai = steer(f, unit(60))
G = diffuse_G(f) + 1e-2 * np.eye(4)
wm = np.linalg.solve(G, a); wm = wm / (a.conj() @ wm)
wL, wR = np.conj(a[iL]) * wm, np.conj(a[iR]) * wm
ILD0 = 20 * np.log10(abs(ai[iR] / ai[iL]))
IPD0 = np.degrees(np.angle(ai[iL] / ai[iR]))
print('   干扰真实线索：ILD %+.2f dB   IPD %+.1f°' % (ILD0, IPD0))
print('   %-6s %13s %13s %13s' % ('η', '干扰抑制', 'ILD 误差', 'IPD 误差'))
for e in [0, .1, .2, .3, .5, .7, 1.]:
    oL = (1 - e) * (wL.conj() @ ai) + e * ai[iL]
    oR = (1 - e) * (wR.conj() @ ai) + e * ai[iR]
    sup = 20 * np.log10(abs(oL) / abs(ai[iL]))
    dl = 20 * np.log10(abs(oR / oL)) - ILD0
    dp = (np.degrees(np.angle(oL / oR)) - IPD0 + 180) % 360 - 180
    print('   %-6.1f %+12.2f dB %+12.2f dB %+12.1f°' % (e, sup, dl, dp))
