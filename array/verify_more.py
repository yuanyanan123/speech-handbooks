#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 §10 / §11 / §13 的新图把数字算死。"""
import numpy as np
c = 343.0

print('=' * 68)
print('§10  时钟偏差 → 相位误差：360·f·(ppm·1e-6·t)')
for ppm in (1, 20, 100):
    for f in (1000, 4000):
        t2 = 2.0 / (360 * f * ppm * 1e-6)          # 触及 2° 预算的时刻
        print('   %4d ppm @ %4d Hz：每秒漂 %6.1f°，触及 2° 预算需 %8.3f s'
              % (ppm, f, 360 * f * ppm * 1e-6, t2))
print('   手册原文说"1 ppm，十秒就把 4 kHz 的预算吃光"——')
print('   严格算是 %.2f 秒；十秒时已到 %.1f°。原文偏保守，图里按精确值标。'
      % (2 / (360 * 4000 * 1e-6), 360 * 4000 * 1e-6 * 10))

print('=' * 68)
print('§11  d = 15 mm 一阶差分阵的均衡增益（应与 07 节表逐位吻合）')
d = 0.015
for f in (100, 200, 500, 1000, 2000):
    kd = 2 * np.pi * f / c * d
    H = 2 * np.sin(kd / 2)
    print('   %5d Hz  kd=%.4f  |H|=%7.2f dB  需均衡 %+6.2f dB  扩散场相干 %.4f'
          % (f, kd, 20 * np.log10(H), -20 * np.log10(H), np.sinc(kd / np.pi)))

print('=' * 68)
print('§13  两种 STFT 相位写法的真实后果')
M, dd, fs, N = 4, 0.035, 16000, 512
th0 = np.deg2rad(60)
tau = dd * np.cos(th0) / c
print('   目标 60°，d=35 mm → 相邻阵元时延 τ = %.2f µs' % (tau * 1e6))

def peak_angle(phase_of, f):
    """给定每个阵元的权重相位函数，扫角找主瓣峰。"""
    k = 2 * np.pi * f / c
    m = np.arange(M)
    w = np.exp(1j * phase_of(f) * m)               # 权重
    th = np.linspace(0, np.pi, 4001)
    a = np.exp(1j * k * dd * np.outer(np.cos(th), m))
    B = np.abs(a @ np.conj(w))
    return np.rad2deg(th[np.argmax(B)])

correct = lambda f: 2 * np.pi * f * tau            # 正确：相位随频率线性
missfs = lambda f: 2 * np.pi * (f / fs) * tau      # bug1：漏掉 fs
constph = lambda f: 2 * np.pi * 1000 * tau         # bug2：只在 1 kHz 算一次

print('   %8s %10s %14s %14s' % ('f', '正确', 'bug1 漏 fs', 'bug2 定相位'))
for f in (250, 500, 1000, 2000, 4000, 6000):
    print('   %8d %9.1f° %13.1f° %13.1f°'
          % (f, peak_angle(correct, f), peak_angle(missfs, f), peak_angle(constph, f)))
print()
print('   bug1 的等效延迟 = τ/fs = %.3e s（≈0）→ 全频段都指向 90°，根本不转向' % (tau / fs))
print('   bug2 的等效延迟 = τ·(1000/f) → cosθ ∝ 1/f：')
for f in (400, 500, 1000, 2000, 4000):
    ct = np.cos(th0) * 1000 / f
    s = '无解（指向丢失）' if abs(ct) > 1 else '%.1f°' % np.rad2deg(np.arccos(ct))
    print('       %5d Hz  cosθ_app = %.3f → %s' % (f, ct, s))
print('   → 手册原文把 bug1 的症状写成了"随频率漂移"，其实那是 bug2 的症状。要改。')
