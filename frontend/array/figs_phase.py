#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2° 相位预算：实测退化曲线 + 预算图。"""
import json, math, html
import numpy as np
rng = np.random.default_rng(20260916)
c = 343.0
OUT = {}
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
O = ['var(--o1)', 'var(--o2)', 'var(--o3)', 'var(--o4)']

def setup(M, d, f, eps):
    kd = 2*np.pi*f/c*d
    G = np.array([[np.sinc(kd*abs(i-j)/np.pi) for j in range(M)] for i in range(M)])
    a = np.exp(1j*kd*np.arange(M))
    w = np.linalg.solve(G+eps*np.eye(M), a); w = w/(a.conj()@w)
    return G, a, w, abs(w.conj()@a)**2/np.real(w.conj()@G@w), abs(w.conj()@a)**2/np.real(w.conj()@w)

def mc(G, a, w, s, N=6000):
    M = len(w)
    wt = w[None,:]*(1+s*rng.standard_normal((N,M)))*np.exp(-1j*s*rng.standard_normal((N,M)))
    num = np.abs(np.einsum('ij,j->i', wt.conj(), a))**2
    den = np.real(np.einsum('ij,jk,ik->i', wt.conj(), G, wt))
    return 10*np.log10(np.mean(num)/np.mean(den))

def fig_phase():
    W, H = 700, 372
    ML, PW, TOP, PH = 46, 264, 54, 236
    ML2 = 414
    o = ['<text x="10" y="18" class="ct">"相位预算 2°"是<tspan font-weight="700">从 WNG 算出来的</tspan>'
         '<tspan class="cu"> · 不是行业口口相传的经验值</tspan></text>']

    # ── 左：实测 DI 随失配退化 ──────────────────────────────
    lo, hi = 0.1, 20.
    fx = lambda v: ML + (math.log10(v)-math.log10(lo))/(math.log10(hi)-math.log10(lo))*PW
    dlo, dhi = 0., 13.
    fy = lambda v: TOP + (dhi-v)/(dhi-dlo)*PH
    o.append(f'<text x="{ML}" y="{TOP-16}" class="blab">实测 DI（dB）· 4 麦 35 mm 端射 1 kHz</text>')
    for v in range(0, 13, 3):
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    sig = np.logspace(math.log10(lo), math.log10(hi), 70)
    cases = [(0.0, '无加载', 'WNG −25.5'), (1e-2, 'ε = 0.01', 'WNG −5.0'), (1e-1, 'ε = 0.1', 'WNG +1.5')]
    for i, (eps, tag, wt) in enumerate(cases):
        G, a, w, di, wng = setup(4, 0.035, 1000, eps)
        pts = []
        for sd in sig:
            s = math.radians(sd); x = 2*s*s/wng
            pts.append(f'{fx(sd):.1f},{fy(max(min(10*math.log10((1+x)/(1/di+x)), dhi), dlo)):.1f}')
        o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{S[i]}" stroke-width="2.2"/>')
        # 蒙特卡洛点
        for sd in [0.2, 0.5, 1., 2., 5., 10.]:
            v = mc(G, a, w, math.radians(sd))
            o.append(f'<circle cx="{fx(sd):.1f}" cy="{fy(max(min(v,dhi),dlo)):.1f}" r="2.8" '
                     f'fill="var(--surface)" stroke="{S[i]}" stroke-width="1.6"/>')
        # 1 dB 损失点
        r = 10**0.1; xx = (r-1)/(di-r); s1 = math.degrees(math.sqrt(xx*wng/2))
        d1 = 10*math.log10(di)-1
        if lo < s1 < hi:
            o.append(f'<line x1="{fx(s1):.1f}" y1="{fy(d1):.1f}" x2="{fx(s1):.1f}" '
                     f'y2="{TOP+PH}" stroke="{S[i]}" stroke-width="1.1" stroke-dasharray="3 2.5"/>')
            o.append(f'<text x="{fx(s1):.1f}" y="{TOP+PH-6:.1f}" class="bsub" fill="{S[i]}" '
                     f'text-anchor="middle">{s1:.1f}°</text>')
        o.append(f'<text x="{ML+4}" y="{fy(10*math.log10(di))-7:.1f}" class="bsub" fill="{S[i]}">'
                 f'{tag}（{wt} dB）</text>')
    for v, lab in [(0.1,'0.1'), (0.5,'0.5'), (1,'1'), (2,'2'), (5,'5'), (20,'20')]:
        o.append(f'<line x1="{fx(v):.1f}" y1="{TOP+PH}" x2="{fx(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">'
             f'每通道幅相失配 σ（度）</text>')
    o.append(f'<text x="{ML+PW}" y="{fy(11.2):.1f}" class="bsub" text-anchor="end" fill="var(--text-3)">'
             f'线 = 闭式　○ = 蒙特卡洛</text>')
    o.append(f'<text x="{ML+PW}" y="{fy(10.3):.1f}" class="bsub" text-anchor="end" fill="var(--text-3)">'
             f'竖虚线 = 掉 1 dB 的失配量</text>')

    # ── 右：预算图 ──────────────────────────────────────────
    wl, wh = -30., 10.
    gx = lambda v: ML2 + (v-wl)/(wh-wl)*PW
    slo, shi = 0.1, 40.
    gy = lambda v: TOP + (math.log10(shi)-math.log10(v))/(math.log10(shi)-math.log10(slo))*PH
    o.append(f'<text x="{ML2}" y="{TOP-16}" class="blab">允许的失配 σ（度）· 掉 1 dB 为限</text>')
    for v in [0.1, 0.3, 1, 3, 10, 30]:
        y = gy(v)
        o.append(f'<line x1="{ML2}" y1="{y:.1f}" x2="{ML2+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML2-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v:g}°</text>')
    for i, didb in enumerate([6, 9, 12, 15]):
        di = 10**(didb/10); r = 10**0.1; xx = (r-1)/(di-r)
        pts = []
        for wdb in np.linspace(wl, wh, 60):
            s = math.degrees(math.sqrt(xx*10**(wdb/10)/2))
            pts.append(f'{gx(wdb):.1f},{gy(min(max(s,slo),shi)):.1f}')
        o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{O[i]}" stroke-width="2.2"/>')
        wlab = [8., 4., 0., -4.][i]
        s_l = math.degrees(math.sqrt(xx*10**(wlab/10)/2))
        o.append(f'<text x="{gx(wlab)+4:.1f}" y="{gy(s_l)-7:.1f}" class="bsub" '
                 f'fill="{O[i]}">DI = {didb} dB</text>')
    # 2° 参考线与工作点
    o.append(f'<line x1="{ML2}" y1="{gy(2):.1f}" x2="{ML2+PW}" y2="{gy(2):.1f}" '
             f'stroke="var(--s2)" stroke-width="1.4" stroke-dasharray="5 3"/>')
    o.append(f'<text x="{ML2+PW-2}" y="{gy(2)-6:.1f}" class="bsub" fill="var(--s2)" '
             f'text-anchor="end">常说的 2°</text>')
    di = 10**1.2; r = 10**0.1; xx = (r-1)/(di-r)
    s0 = math.degrees(math.sqrt(xx*10**(-1.0)/2))
    o.append(f'<circle cx="{gx(-10):.1f}" cy="{gy(s0):.1f}" r="5.5" fill="none" '
             f'stroke="var(--s2)" stroke-width="2"/>')
    o.append(f'<text x="{gx(-10)+11:.1f}" y="{gy(s0)+15:.1f}" class="bsub" fill="var(--s2)">'
             f'典型超指向工作点</text>')
    o.append(f'<text x="{gx(-10)+11:.1f}" y="{gy(s0)+28:.1f}" class="bsub" fill="var(--s2)">'
             f'DI 12 dB、WNG −10 dB → {s0:.2f}°</text>')
    for v in range(-30, 11, 10):
        o.append(f'<line x1="{gx(v):.1f}" y1="{TOP+PH}" x2="{gx(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{gx(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{v:+d}</text>')
    o.append(f'<text x="{ML2+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">'
             f'设计的 WNG（dB）</text>')

    o.append(f'<text x="14" y="{H-10}" class="arlab">'
             f'一条可以背的式子：<tspan font-weight="600">σ(度) ≈ 22 × 10^((WNG−DI)/20)</tspan>'
             f'——WNG 每降 6 dB，允许的失配就减半。2° 相位 ≙ 0.3 dB 幅度，两者同等贡献。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('左图：同一个四麦阵列的三种设计，实测指向性指数随每通道幅相失配增大而下降，'
                          '无加载超指向在 0.29 度就掉了 1 dB，而重加载的设计到十几度才掉 1 dB；'
                          '闭式曲线与蒙特卡洛点完全重合。'
                          '右图：允许的失配随设计 WNG 变化，四条线对应不同的标称 DI；'
                          '常说的 2 度对应 DI 12 dB、WNG 负 10 dB 这个典型工作点')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['phase'] = fig_phase()
json.dump(OUT, open('figs8.json', 'w'))
for k, v in OUT.items(): print('figs8.json: %-8s %.1f KB' % (k, len(v)/1024))
