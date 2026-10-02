#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""球谐波束成形：把手册里要写的每个数字算一遍。"""
import numpy as np
from scipy.special import spherical_jn, spherical_yn, sph_harm_y

c = 343.0

# ── 1. 连续球面孔径：最大指向性 DI = (N+1)² ────────────────────
print('=' * 62)
print('1. 连续球面、c_n = 1（最大指向性）的 DI')
th = np.linspace(0, np.pi, 200001)
for N in range(0, 7):
    n = np.arange(N + 1)
    # B(Θ) = Σ (2n+1)/(4π) P_n(cosΘ)
    from numpy.polynomial import legendre as Lg
    B = np.zeros_like(th)
    for nn in n:
        cf = np.zeros(nn + 1); cf[nn] = 1
        B += (2 * nn + 1) / (4 * np.pi) * Lg.legval(np.cos(th), cf)
    num = B[0] ** 2
    den = 0.5 * np.trapezoid(B ** 2 * np.sin(th), th)     # (1/4π)∫|B|²dΩ
    DI = num / den
    print('   N=%d  DI=%8.4f  → %6.2f dB   理论 (N+1)²=%3d = %6.2f dB'
          % (N, DI, 10 * np.log10(DI), (N + 1) ** 2, 20 * np.log10(N + 1)))

# ── 2. 模态强度 b_n(kr) 的低频斜率 ────────────────────────────
print('=' * 62)
print('2. 开球 b_n = 4π i^n j_n(kr) 的低频斜率（每倍频程 dB）')
for n in range(0, 5):
    kr = np.array([0.02, 0.04])
    v = np.abs(spherical_jn(n, kr))
    slope = 20 * np.log10(v[1] / v[0])          # 一个倍频程
    print('   n=%d  |j_n| 斜率 = %+6.2f dB/oct   → 1/b_n 放大 %+6.2f dB/oct   理论 6n=%d'
          % (n, slope, -slope, 6 * n))
print('   小 kr 展开 j_n(x) ≈ x^n/(2n+1)!! 校验：')
for n in range(0, 5):
    x = 1e-3
    dbl = np.prod(np.arange(2 * n + 1, 0, -2)) if n > 0 else 1.0
    print('      n=%d  j_n=%.6e   x^n/(2n+1)!!=%.6e   比值 %.6f'
          % (n, spherical_jn(n, x), x ** n / dbl, spherical_jn(n, x) / (x ** n / dbl)))

# ── 3. 刚性球 vs 开球：b_n 在零点处的表现 ─────────────────────
print('=' * 62)
print('3. 开球的 j_n 零点 = 模态强度陷零（刚性球没有）')
kr = np.linspace(0.05, 12, 40000)
for n in range(0, 3):
    j = spherical_jn(n, kr)
    z = kr[np.where(np.diff(np.sign(j)))[0]]
    print('   n=%d  j_n 零点 kr ≈ %s' % (n, np.round(z[:3], 3)))
def b_rigid(n, kr):
    jn = spherical_jn(n, kr); jnp = spherical_jn(n, kr, derivative=True)
    hn = jn - 1j * spherical_yn(n, kr)                       # h_n^(2)
    hnp = jnp - 1j * spherical_yn(n, kr, derivative=True)
    return 4 * np.pi * (1j ** n) * (jn - jnp / hnp * hn)
kk = np.array([np.pi, 4.493, 5.763])
for n in range(0, 3):
    print('   n=%d  开球 |b_n| 在 kr=%s → %s ；刚性球 → %s'
          % (n, np.round(kk, 2),
             np.round(np.abs(4 * np.pi * spherical_jn(n, kk)), 4),
             np.round(np.abs(b_rigid(n, kk)), 4)))

# ── 4. 离散球阵：模态波束的 DI 与 WNG（直接按 04 节定义算）────
print('=' * 62)
print('4. 离散开球阵 Q 个阵元、N 阶模态波束：DI / WNG')

def fib_sphere(Q):
    i = np.arange(Q) + 0.5
    phi = np.arccos(1 - 2 * i / Q)
    tht = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.sin(phi) * np.cos(tht),
                     np.sin(phi) * np.sin(tht), np.cos(phi)], 1)

def sh(n, m, u):                       # u: (...,3) 单位矢量 → Y_n^m
    theta = np.arccos(np.clip(u[..., 2], -1, 1))
    phi = np.arctan2(u[..., 1], u[..., 0])
    return sph_harm_y(n, m, theta, phi)

def modal_w(Q, N, kr, pos_u, look):
    """开球模态波束权重（plane-wave decomposition, c_n=1）。"""
    w = np.zeros(Q, complex)
    for n in range(N + 1):
        bn = 4 * np.pi * (1j ** n) * spherical_jn(n, kr)
        for m in range(-n, n + 1):
            w += (4 * np.pi / Q) * np.conj(sh(n, m, pos_u)) * sh(n, m, look) / bn
    return np.conj(w)                  # 上面算的是 w^H 的元素，取共轭得 w

def steer(pos_u, kr, u):               # 开球远场导向矢量
    return np.exp(1j * kr * (pos_u @ u))

Q, r = 64, 0.042
look = np.array([0., 0., 1.])
pu = fib_sphere(Q)
print('   Q=%d  r=%.3f m（≈ Eigenmike 尺寸）' % (Q, r))
print('   %-6s %-8s %10s %10s %10s' % ('N', 'f (Hz)', 'kr', 'DI dB', 'WNG dB'))
for N in [1, 2, 3, 4]:
    for f in [250, 500, 1000, 2000, 4000, 6000]:
        kr = 2 * np.pi * f * r / c
        w = modal_w(Q, N, kr, pu, look)
        a = steer(pu, kr, look)
        # DI：扩散场 = 全方向均匀积分
        gx = fib_sphere(2000)
        B = np.array([np.vdot(w, steer(pu, kr, g)) for g in gx])
        DI = abs(np.vdot(w, a)) ** 2 / np.mean(np.abs(B) ** 2)
        WNG = abs(np.vdot(w, a)) ** 2 / (np.vdot(w, w).real)
        print('   %-6d %-8d %10.3f %10.2f %10.2f'
              % (N, f, kr, 10 * np.log10(DI), 10 * np.log10(WNG)))
    print('        ↑ 理论上限 DI = 20log10(N+1) = %.2f dB' % (20 * np.log10(N + 1)))

# ── 5. 阵元数下限与混叠上限 ───────────────────────────────────
print('=' * 62)
print('5. 阶数 ↔ 阵元数 ↔ 可用上限频率（r = 4.2 cm）')
print('   %-4s %-10s %-10s %-12s %-10s' % ('N', '(N+1)²', 'DI 上限', 'kr≤N 上限 f', 'em32 够吗'))
for N in range(1, 7):
    fmax = N * c / (2 * np.pi * r)
    print('   %-4d %-10d %-10.2f %-12.0f %-10s'
          % (N, (N + 1) ** 2, 20 * np.log10(N + 1), fmax, '是' if (N + 1) ** 2 <= 32 else '否'))
