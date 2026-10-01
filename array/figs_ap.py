#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§03：孔径下限与主瓣宽度的定量图。"""
import json, math, html
import numpy as np
from scipy.optimize import brentq
c = 343.0
OUT = {}
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
O = ['var(--o1)', 'var(--o2)', 'var(--o3)', 'var(--o4)']

def di_das(M, kL):
    kd = kL/M; m = np.arange(M); D = np.abs(m[:,None]-m[None,:])
    return M**2/np.real(np.sinc(kd*D/np.pi).sum())

def AF(M, kd, s):
    psi = kd*s
    return np.abs(np.where(np.abs(np.sin(psi/2)) < 1e-14, 1.0,
                           np.sin(M*psi/2)/(M*np.sin(psi/2))))

def fig_aperture():
    W, H = 700, 366
    ML, PW, TOP, PH = 46, 266, 56, 228
    ML2 = 414
    o = ['<text x="10" y="18" class="ct">'
         '"孔径至少半个波长"<tspan font-weight="700">是能算出来的</tspan>'
         '<tspan class="cu"> · 它等于"DAS 只拿到 1 dB 指向性"</tspan></text>']

    # ── 左：DI vs L/λ ───────────────────────────────────────
    lo, hi = 0.1, 4.0
    fx = lambda v: ML + (math.log10(v)-math.log10(lo))/(math.log10(hi)-math.log10(lo))*PW
    dlo, dhi = 0., 11.
    fy = lambda v: TOP + (dhi-v)/(dhi-dlo)*PH
    o.append(f'<text x="{ML}" y="{TOP-16}" class="blab">DAS 在扩散场里的 DI（dB）</text>')
    for v in range(0, 12, 2):
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    Ls = np.logspace(math.log10(lo), math.log10(hi), 160)
    for i, M in enumerate([4, 8, 16, 64]):
        pts = ' '.join(f'{fx(L):.1f},{fy(min(10*math.log10(di_das(M, 2*math.pi*L)), dhi)):.1f}'
                       for L in Ls)
        o.append(f'<polyline points="{pts}" fill="none" stroke="{O[i]}" stroke-width="2.2"/>')
    # 展开式
    pts = ' '.join(f'{fx(L):.1f},{fy(min(10*math.log10(1+(2*math.pi*L)**2/36), dhi)):.1f}'
                   for L in Ls)
    o.append(f'<polyline points="{pts}" fill="none" stroke="{S[2]}" stroke-width="1.6" '
             f'stroke-dasharray="5 3"/>')
    o.append(f'<text x="{fx(0.11):.1f}" y="{fy(9.4):.1f}" class="bsub" fill="var(--text-3)">'
             f'M = 4 / 8 / 16 / 64 四条线</text>')
    o.append(f'<text x="{fx(0.11):.1f}" y="{fy(8.4):.1f}" class="bsub" fill="var(--text-3)">'
             f'几乎<tspan font-weight="600">完全重合</tspan>——只看孔径，不看麦数</text>')
    o.append(f'<text x="{fx(0.11):.1f}" y="{fy(7.2):.1f}" class="bsub" fill="{S[2]}">'
             f'虚线：低频展开 1 + (kL)²/36</text>')
    for L, v, lab in [(0.486, 1.0, 'λ/2 → 1 dB'), (0.953, 3.0, 'λ → 3 dB'),
                      (1.649, 6.0, '1.65λ → 6 dB')]:
        o.append(f'<circle cx="{fx(L):.1f}" cy="{fy(v):.1f}" r="4.2" fill="var(--surface)" '
                 f'stroke="{S[1]}" stroke-width="2"/>')
        o.append(f'<text x="{fx(L)+9:.1f}" y="{fy(v)+13:.1f}" class="bsub" fill="{S[1]}">{lab}</text>')
    o.append(f'<text x="{fx(3.9):.1f}" y="{fy(1.7):.1f}" class="bsub" text-anchor="end" '
             f'fill="{O[0]}">M = 4 在这里 kd &gt; π</text>')
    o.append(f'<text x="{fx(3.9):.1f}" y="{fy(0.85):.1f}" class="bsub" text-anchor="end" '
             f'fill="{O[0]}">已经混叠，DI 掉头</text>')
    for v, lab in [(0.1,'0.1'),(0.25,'0.25'),(0.5,'0.5'),(1,'1'),(2,'2'),(4,'4')]:
        o.append(f'<line x1="{fx(v):.1f}" y1="{TOP+PH}" x2="{fx(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">'
             f'孔径 L / 波长 λ</text>')

    # ── 右：主瓣宽度 ────────────────────────────────────────
    glo, ghi = 0.25, 8.
    gx = lambda v: ML2 + (math.log10(v)-math.log10(glo))/(math.log10(ghi)-math.log10(glo))*PW
    blo, bhi = 3., 200.
    gy = lambda v: TOP + (math.log10(bhi)-math.log10(v))/(math.log10(bhi)-math.log10(blo))*PH
    o.append(f'<text x="{ML2}" y="{TOP-16}" class="blab">主瓣 −3 dB 全宽（度）· 边射</text>')
    for v in [5, 10, 30, 60, 120]:
        y = gy(v)
        o.append(f'<line x1="{ML2}" y1="{y:.1f}" x2="{ML2+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML2-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}°</text>')
    Ls2 = np.logspace(math.log10(glo), math.log10(ghi), 200)
    pts = []
    for L in Ls2:
        s = 0.886/2/L
        if s >= 1: continue
        pts.append(f'{gx(L):.1f},{gy(min(max(2*math.degrees(math.asin(s)), blo), bhi)):.1f}')
    o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{S[0]}" stroke-width="2.4"/>')
    pts = ' '.join(f'{gx(L):.1f},{gy(min(max(51.0/L, blo), bhi)):.1f}' for L in Ls2)
    o.append(f'<polyline points="{pts}" fill="none" stroke="var(--s2)" stroke-width="1.7" '
             f'stroke-dasharray="5 3"/>')
    o.append(f'<text x="{gx(7.8):.1f}" y="{gy(15):.1f}" class="bsub" text-anchor="end" '
             f'fill="{S[0]}">实线　2·arcsin(0.443 λ/L)</text>')
    o.append(f'<text x="{gx(7.8):.1f}" y="{gy(11):.1f}" class="bsub" text-anchor="end" '
             f'fill="var(--s2)">虚线　51° ÷ (L/λ)</text>')
    o.append(f'<rect x="{gx(glo):.1f}" y="{TOP:.1f}" width="{gx(0.75)-gx(glo):.1f}" '
             f'height="{PH:.1f}" fill="var(--s2)" fill-opacity="0.08"/>')
    o.append(f'<text x="{gx(0.42):.1f}" y="{gy(8.5):.1f}" class="bsub" text-anchor="middle" '
             f'fill="var(--text-3)">L &lt; 0.75λ：</text>')
    o.append(f'<text x="{gx(0.42):.1f}" y="{gy(6.4):.1f}" class="bsub" text-anchor="middle" '
             f'fill="var(--text-3)">小角近似失效</text>')
    o.append(f'<text x="{gx(0.42):.1f}" y="{gy(4.8):.1f}" class="bsub" text-anchor="middle" '
             f'fill="var(--text-3)">（差 20°以上）</text>')
    # 实例点
    for L, lab in [(0.408, '4 麦 35 mm @1 kHz'), (1.633, '同一阵列 @4 kHz')]:
        s = 0.886/2/L
        if s < 1:
            v = 2*math.degrees(math.asin(s))
            o.append(f'<circle cx="{gx(L):.1f}" cy="{gy(v):.1f}" r="4.2" fill="var(--surface)" '
                     f'stroke="{S[2]}" stroke-width="2"/>')
            o.append(f'<text x="{gx(L)-9:.1f}" y="{gy(v)+14:.1f}" class="bsub" fill="{S[2]}" '
                     f'text-anchor="end">@4 kHz　{v:.0f}°</text>')
        else:
            o.append(f'<text x="{gx(0.42):.1f}" y="{gy(20):.1f}" class="bsub" fill="{S[2]}" '
                     f'text-anchor="middle">{lab}</text>')
            o.append(f'<text x="{gx(0.42):.1f}" y="{gy(14.5):.1f}" class="bsub" fill="{S[2]}" '
                     f'text-anchor="middle">L = 0.41λ，根本没有主瓣</text>')
    for v, lab in [(0.25,'0.25'),(0.5,'0.5'),(1,'1'),(2,'2'),(4,'4'),(8,'8')]:
        o.append(f'<line x1="{gx(v):.1f}" y1="{TOP+PH}" x2="{gx(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{gx(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML2+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">'
             f'孔径 L = M·d / 波长 λ</text>')

    o.append(f'<text x="14" y="{H-10}" class="arlab">'
             f'两张图说的是同一件事：<tspan font-weight="600">决定低频性能的是孔径与波长之比，'
             f'不是阵元数</tspan>。加麦只能往上推混叠上限，推不动这条下限。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('左图：延迟求和阵在扩散场里的指向性指数随孔径与波长之比上升，'
                          '四麦到六十四麦的曲线几乎完全重合，说明只有孔径起作用；'
                          '孔径等于半波长时只有 1 分贝，等于一个波长时 3 分贝。'
                          '右图：主瓣负三分贝全宽等于 2 倍 arcsin(0.443 λ/L)，'
                          '常用的 51 度除以 L 比 λ 这条近似在孔径小于 0.75 个波长时失效')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['aperture'] = fig_aperture()
json.dump(OUT, open('figs10.json', 'w'))
for k, v in OUT.items(): print('figs10.json: %-10s %.1f KB' % (k, len(v)/1024))
