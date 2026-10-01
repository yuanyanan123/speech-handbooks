#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三张数据图：扩散场相干曲线、球谐方向图、HOA 白噪声增益。"""
import json, math
import numpy as np
from scipy.special import spherical_jn, spherical_yn
from numpy.polynomial import legendre as Lg

c = 343.0
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
OUT = {}

# ════════════════════════════════════════════════════════════════
# G. 扩散场相干 Γ = sinc(kd) 随频率
# ════════════════════════════════════════════════════════════════
def fig_coh():
    W, ML, MR, PH, TOP = 700, 46, 118, 190, 34
    PW = W - ML - MR
    lo, hi = 100., 8000.
    fx = lambda f: ML + (math.log10(f) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * PW
    fy = lambda v: TOP + (1.05 - v) / (1.05 - (-0.3)) * PH
    o = [f'<text x="{ML}" y="{TOP-14}" class="ct">扩散场相干 Γ(f) = sinc(kd)'
         f'<tspan class="cu"> · 两个麦收到的环境噪声有多像</tspan></text>']
    for v in [1.0, 0.5, 0.0, -0.3]:
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-7}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v:g}</text>')
    o.append(f'<line x1="{ML}" y1="{fy(0):.1f}" x2="{ML+PW}" y2="{fy(0):.1f}" class="zero"/>')
    fs = np.logspace(math.log10(lo), math.log10(hi), 400)
    for i, d in enumerate([0.020, 0.035, 0.080]):
        kd = 2 * np.pi * fs / c * d
        g = np.sinc(kd / np.pi)                       # sin(kd)/(kd)
        pts = ' '.join(f'{fx(f):.1f},{fy(max(v,-0.3)):.1f}' for f, v in zip(fs, g))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{S[i]}" stroke-width="2" '
                 f'stroke-linejoin="round"/>')
        # 第一个零点 kd = π  →  f = c/(2d)
        f0 = c / (2 * d)
        if f0 < hi:
            o.append(f'<circle cx="{fx(f0):.1f}" cy="{fy(0):.1f}" r="3.2" fill="{S[i]}" '
                     f'stroke="var(--surface)" stroke-width="1.5"/>')
        o.append(f'<text x="{ML+PW+10}" y="{TOP+34+i*20}" class="clab" '
                 f'fill="{S[i]}">d = {int(d*1000)} mm</text>')
        o.append(f'<line x1="{ML+PW+2}" y1="{TOP+30+i*20}" x2="{ML+PW+7}" y2="{TOP+30+i*20}" '
                 f'stroke="{S[i]}" stroke-width="2.4"/>')
    # 说明带
    o.append(f'<rect x="{fx(lo):.1f}" y="{fy(1.05):.1f}" width="{fx(500)-fx(lo):.1f}" '
             f'height="{PH:.1f}" class="target"/>')
    o.append(f'<text x="{(fx(lo)+fx(500))/2:.1f}" y="{TOP+PH-10:.0f}" class="clab" '
             f'text-anchor="middle" fill="var(--text-3)">Γ → 1：噪声几乎一样，无差异可用</text>')
    for f in [100, 250, 500, 1000, 2000, 4000, 8000]:
        lab = f'{f//1000}k' if f >= 1000 else str(f)
        o.append(f'<line x1="{fx(f):.1f}" y1="{TOP+PH}" x2="{fx(f):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">频率 (Hz)</text>')
    return (f'<svg viewBox="0 0 {W} {TOP+PH+44}" class="chart" role="img" '
            f'aria-label="扩散场相干函数随频率下降，阵元间距越大下降越早，'
            f'第一个零点出现在 c 除以 2d 处">\n' + '\n'.join(o) + '\n</svg>')

OUT['coh'] = fig_coh()

# ════════════════════════════════════════════════════════════════
# H. 球谐波束方向图：N = 0,1,2,3 小倍数极坐标
# ════════════════════════════════════════════════════════════════
def fig_sh_polar():
    R, FLOOR = 62, -30.
    cells = [(78, 120), (248, 120), (418, 120), (588, 120)]
    o = []
    th = np.linspace(0, 2 * np.pi, 721)
    for idx, N in enumerate([0, 1, 2, 3]):
        cx, cy = cells[idx]
        B = np.zeros_like(th)
        for n in range(N + 1):
            cf = np.zeros(n + 1); cf[n] = 1
            B += (2 * n + 1) / (4 * np.pi) * Lg.legval(np.cos(th), cf)
        db = 20 * np.log10(np.abs(B) / np.abs(B).max() + 1e-12)
        for ring in [0, -10, -20]:
            rr = R * (ring - FLOOR) / (-FLOOR)
            o.append(f'<circle cx="{cx}" cy="{cy}" r="{rr:.1f}" class="grid" fill="none"/>')
        for ang in range(0, 360, 45):
            t = math.radians(ang)
            o.append(f'<line x1="{cx}" y1="{cy}" x2="{cx+R*math.sin(t):.1f}" '
                     f'y2="{cy-R*math.cos(t):.1f}" class="grid"/>')
        pts = []
        for a, v in zip(th, db):
            rr = R * (max(v, FLOOR) - FLOOR) / (-FLOOR)
            pts.append(f'{cx+rr*math.sin(a):.1f},{cy-rr*math.cos(a):.1f}')
        col = S[0] if N < 3 else S[1]
        o.append(f'<polygon points="{" ".join(pts)}" fill="{col}" fill-opacity="0.12" '
                 f'stroke="{col}" stroke-width="1.8" stroke-linejoin="round"/>')
        o.append(f'<text x="{cx}" y="{cy-R-16}" class="ct" text-anchor="middle">N = {N}</text>')
        di = 20 * math.log10(N + 1)
        o.append(f'<text x="{cx}" y="{cy+R+20}" class="clab" text-anchor="middle" '
                 f'fill="var(--text-2)">DI {di:.2f} dB</text>')
        o.append(f'<text x="{cx}" y="{cy+R+34}" class="clab" text-anchor="middle" '
                 f'fill="var(--text-3)">需 {(N+1)**2} 个麦</text>')
    o.append('<text x="14" y="18" class="ct">最大指向性球谐波束'
             '<tspan class="cu"> · 阶数每加一，主瓣收一点，所需阵元数按平方涨</tspan></text>')
    return ('<svg viewBox="0 0 700 236" class="chart" role="img" aria-label="零到三阶球谐波束的'
            '方向图，阶数越高主瓣越窄，指向性指数从 0 dB 增到 12 dB，所需阵元数从 1 增到 16">\n'
            + '\n'.join(o) + '\n</svg>')

OUT['shpolar'] = fig_sh_polar()

# ════════════════════════════════════════════════════════════════
# I. 球阵白噪声增益 vs 频率（闭式，刚性球 Q=64 r=42mm）
# ════════════════════════════════════════════════════════════════
def bn_rigid(n, kr):
    j = spherical_jn(n, kr); jp = spherical_jn(n, kr, derivative=True)
    h = j + 1j * spherical_yn(n, kr); hp = jp + 1j * spherical_yn(n, kr, derivative=True)
    return 4 * np.pi * (1j ** n) * (j - jp / hp * h)

def wng_db(Q, N, kr):
    s = sum((2 * n + 1) / abs(bn_rigid(n, kr)) ** 2 for n in range(N + 1))
    return 10 * np.log10(Q * (N + 1) ** 4 / ((4 * np.pi) ** 2 * s))

def fig_hoa_wng():
    W, ML, MR, PH, TOP = 700, 50, 26, 210, 36
    PW = W - ML - MR
    lo, hi = 100., 8000.
    vmin, vmax = -60., 25.
    fx = lambda f: ML + (math.log10(f) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * PW
    fy = lambda v: TOP + (vmax - v) / (vmax - vmin) * PH
    Q, r = 64, 0.042
    o = [f'<text x="{ML}" y="{TOP-14}" class="ct">球阵白噪声增益'
         f'<tspan class="cu"> · 刚性球 Q=64、半径 42 mm；低于 0 dB = 麦克风自噪声被放大</tspan></text>']
    for v in [20, 0, -20, -40, -60]:
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-7}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{ML}" y1="{fy(0):.1f}" x2="{ML+PW}" y2="{fy(0):.1f}" class="zero"/>')
    fs = np.logspace(math.log10(lo), math.log10(hi), 320)
    COL = ['var(--o1)', 'var(--o2)', 'var(--o3)', 'var(--o4)']  # 序数蓝阶：N 本来就是有序的
    ONSET = {}
    for i, N in enumerate([1, 2, 3, 4]):
        v = np.array([wng_db(Q, N, 2 * np.pi * f * r / c) for f in fs])
        pts = ' '.join(f'{fx(f):.1f},{fy(min(max(x,vmin),vmax)):.1f}' for f, x in zip(fs, v))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{COL[i]}" stroke-width="2" '
                 f'stroke-linejoin="round"/>')
        # 用二分把 WNG=0 dB 的交点定到 1 Hz 以内，图上标注与正文数字才一致
        if v[-1] >= 0 or v.max() >= 0:
            a_, b_ = lo, hi
            for _ in range(60):
                m_ = math.sqrt(a_ * b_)
                if wng_db(Q, N, 2 * math.pi * m_ * r / c) < 0: a_ = m_
                else: b_ = m_
            ONSET[N] = round(b_)
        ok = fs[v >= 0]
        if len(ok):
            o.append(f'<circle cx="{fx(ONSET[N]):.1f}" cy="{fy(0):.1f}" r="3.4" fill="{COL[i]}" '
                     f'stroke="var(--surface)" stroke-width="1.5"/>')

    for N, f0 in ONSET.items():
        o.append(f'<text x="{fx(f0):.1f}" y="{fy(0)-9:.1f}" class="clab halo" '
                 f'text-anchor="middle" fill="var(--text-2)">{f0:.0f}</text>')
    o.append(f'<text x="{fx(112):.1f}" y="{fy(-52):.1f}" class="clab" fill="var(--text-3)">'
             f'低频斜率 = 6N dB/oct</text>')
    o.append(f'<text x="{fx(2600):.1f}" y="{fy(-40):.1f}" class="clab" fill="var(--text-3)">'
             f'圆点 = WNG 回到 0 dB 的频率</text>')
    for f in [100, 250, 500, 1000, 2000, 4000, 8000]:
        lab = f'{f//1000}k' if f >= 1000 else str(f)
        o.append(f'<line x1="{fx(f):.1f}" y1="{TOP+PH}" x2="{fx(f):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">频率 (Hz)</text>')
    print('  WNG≥0dB 起点：', {k: round(float(v)) for k, v in ONSET.items()})
    return (f'<svg viewBox="0 0 {W} {TOP+PH+44}" class="chart" role="img" '
            f'aria-label="球阵白噪声增益随阶数升高而在低频急剧恶化，'
            f'一阶从 141 赫兹起可用，四阶要到 2256 赫兹才可用">\n' + '\n'.join(o) + '\n</svg>')

OUT['hoawng'] = fig_hoa_wng()

# ════════════════════════════════════════════════════════════════
# L. ITD / ILD 随频率（刚性球头模型实算）
# ════════════════════════════════════════════════════════════════
A_HEAD = 0.0875
def sphere_H(f, cosT, a=A_HEAD):
    ka = 2 * np.pi * f * a / c
    N = int(np.ceil(ka)) + 30
    n = np.arange(N + 1)
    hp = spherical_jn(n, ka, derivative=True) + 1j * spherical_yn(n, ka, derivative=True)
    coef = (2 * n + 1) * (1j ** n) * 1j / (ka ** 2 * hp)
    cosT = np.atleast_1d(cosT)
    P = np.stack([Lg.legval(cosT, np.eye(N + 1)[k]) for k in n])
    return coef @ P

def fig_cues():
    W, ML, MR, PH, TOP = 700, 52, 116, 150, 34
    PW = W - ML - MR
    lo, hi = 100., 8000.
    fx = lambda f: ML + (math.log10(f) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * PW
    fs = np.logspace(math.log10(lo), math.log10(hi), 150)
    uL = np.array([math.cos(math.radians(100)), math.sin(math.radians(100)), 0.])
    uR = np.array([math.cos(math.radians(-100)), math.sin(math.radians(-100)), 0.])
    o = [f'<text x="{ML}" y="{TOP-14}" class="ct">ILD 随频率'
         f'<tspan class="cu"> · 刚性球头模型，同侧耳比对侧耳响多少</tspan></text>']
    vmin, vmax = -2., 26.
    fy = lambda v: TOP + (vmax - v) / (vmax - vmin) * PH
    for v in [0, 10, 20]:
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-7}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{ML}" y1="{fy(0):.1f}" x2="{ML+PW}" y2="{fy(0):.1f}" class="zero"/>')
    for i, az in enumerate([30, 60, 90]):
        s = np.array([math.cos(math.radians(az)), math.sin(math.radians(az)), 0.])
        v = np.array([20 * math.log10(abs(sphere_H(f, np.array([s @ uR]))[0] /
                                          sphere_H(f, np.array([s @ uL]))[0])) for f in fs])
        pts = ' '.join(f'{fx(f):.1f},{fy(min(max(x,vmin),vmax)):.1f}' for f, x in zip(fs, v))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{S[i]}" stroke-width="2" '
                 f'stroke-linejoin="round"/>')
        o.append(f'<text x="{ML+PW+10}" y="{fy(min(max(v[-1],vmin),vmax))+3.5:.1f}" '
                 f'class="clab" fill="{S[i]}">声源 {az}°</text>')
    # 分界：头径 = λ
    fb = c / (2 * A_HEAD)
    o.append(f'<line x1="{fx(fb):.1f}" y1="{TOP}" x2="{fx(fb):.1f}" y2="{TOP+PH}" '
             f'class="cross" style="opacity:1"/>')
    o.append(f'<text x="{fx(fb)+6:.1f}" y="{TOP+13}" class="clab" fill="var(--text-3)">'
             f'头径 = λ　{fb:.0f} Hz</text>')
    for f in [100, 250, 500, 1000, 2000, 4000, 8000]:
        lab = f'{f//1000}k' if f >= 1000 else str(f)
        o.append(f'<line x1="{fx(f):.1f}" y1="{TOP+PH}" x2="{fx(f):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">频率 (Hz)</text>')
    return (f'<svg viewBox="0 0 {W} {TOP+PH+44}" class="chart" role="img" '
            f'aria-label="双耳声级差在低频几乎为零，越过头径等于波长的 1960 赫兹后迅速增大，'
            f'90 度方位在 8 千赫可达 20 dB 以上">\n' + '\n'.join(o) + '\n</svg>')

OUT['cues'] = fig_cues()

json.dump(OUT, open('figs2.json', 'w'))
print('figs2.json:', ', '.join('%s %.1fKB' % (k, len(v) / 1024) for k, v in OUT.items()))
