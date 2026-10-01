#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§04 两条边界的两张仿真图：(1) DI/WNG 随 kd 逼近 M² 与代价；(2) Uzkov 的 Σ(2n+1) 拼图。"""
import json, math, html
import numpy as np
import mpmath as mp
from scipy.special import eval_legendre
mp.mp.dps = 60
c = 343.0
OUT = {}
O = ['var(--o1)', 'var(--o2)', 'var(--o3)', 'var(--o4)']   # 序数蓝阶（M 是有序的）

def di_wng(M, kd):
    """高精度算端射超指向的 DI 与 WNG，避免双精度崩掉。"""
    a = mp.matrix([mp.mpf(1)*mp.e**(1j*kd*m) for m in range(M)])
    G = mp.matrix(M, M)
    for i in range(M):
        for j in range(M):
            x = mp.mpf(kd)*abs(i-j)
            G[i, j] = mp.mpf(1) if x == 0 else mp.sin(x)/x
    x = mp.lu_solve(G, a)
    di = mp.re(sum(mp.conj(a[i])*x[i] for i in range(M)))
    w = [x[i]/di for i in range(M)]                 # w = Γ⁻¹a/(aᴴΓ⁻¹a)
    num = abs(sum(mp.conj(w[i])*a[i] for i in range(M)))**2
    den = sum(abs(w[i])**2 for i in range(M))
    return float(di), float(num/den)

# ════════════════════════════════════════════════════════════════
# 图一：DI → M²，以及 WNG 付出的代价
# ════════════════════════════════════════════════════════════════
def fig_bound():
    W, H = 700, 366
    ML, PW, TOP, PH = 44, 268, 52, 232
    ML2 = 412
    lo, hi = 1e-2, 6.0
    fx  = lambda v: ML  + (math.log10(v)-math.log10(lo))/(math.log10(hi)-math.log10(lo))*PW
    fx2 = lambda v: ML2 + (math.log10(v)-math.log10(lo))/(math.log10(hi)-math.log10(lo))*PW
    o = ['<text x="10" y="18" class="ct">两条边界都是<tspan font-weight="700">算出来的</tspan>，'
         '不是记住的<tspan class="cu"> · 端射均匀线阵，Γ 取扩散场</tspan></text>']

    kds = np.logspace(math.log10(lo), math.log10(hi), 90)
    Ms = [2, 3, 4, 6]

    # ── 左：DI ───────────────────────────────────────────────
    dlo, dhi = 0., 18.
    fy = lambda v: TOP + (dhi-v)/(dhi-dlo)*PH
    o.append(f'<text x="{ML}" y="{TOP-16}" class="blab">DI（dB）→ 上界 20log₁₀M</text>')
    for v in range(0, 19, 3):
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    for i, M in enumerate(Ms):
        lim = 20*math.log10(M)
        o.append(f'<line x1="{ML}" y1="{fy(lim):.1f}" x2="{ML+PW}" y2="{fy(lim):.1f}" '
                 f'stroke="{O[i]}" stroke-width="1.1" stroke-dasharray="5 3" opacity="0.85"/>')

        pts = []
        for kd in kds:
            d, _ = di_wng(M, kd)
            pts.append(f'{fx(kd):.1f},{fy(min(max(10*math.log10(max(d,1e-9)),dlo),dhi)):.1f}')
        o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{O[i]}" '
                 f'stroke-width="2.2" stroke-linejoin="round"/>')
        o.append(f'<text x="{fx(0.0105):.1f}" y="{fy(lim)-5:.1f}" class="bsub" fill="{O[i]}">'
                 f'M={M}　上界 20log₁₀M = {lim:.2f} dB</text>')
    # DAS 的 DI 做对照（M=4）
    pts = []
    for kd in kds:
        M = 4
        a = np.exp(1j*kd*np.arange(M)); w = a/M
        Gm = np.array([[np.sinc(kd*abs(i-j)/np.pi) for j in range(M)] for i in range(M)])
        di = abs(w.conj()@a)**2/np.real(w.conj()@Gm@w)
        pts.append(f'{fx(kd):.1f},{fy(min(max(10*math.log10(di),dlo),dhi)):.1f}')
    o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="var(--s2)" '
             f'stroke-width="1.8" stroke-dasharray="3 2.5"/>')
    o.append(f'<text x="{fx(0.9):.1f}" y="{fy(1.5):.1f}" class="bsub" fill="var(--s2)">'
             f'DAS（M=4）：靠不上上界</text>')
    for v, lab in [(0.01,'0.01'), (0.1,'0.1'), (1.0,'1'), (math.pi,'π')]:
        o.append(f'<line x1="{fx(v):.1f}" y1="{TOP+PH}" x2="{fx(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">kd（间距／波长）</text>')
    o.append(f'<text x="{ML+6}" y="{TOP+PH-10:.0f}" class="bsub" fill="var(--text-3)">'
             f'← 阵元越挤，越贴上界</text>')

    # ── 右：WNG ──────────────────────────────────────────────
    wlo, whi = -100., 20.
    gy = lambda v: TOP + (whi-v)/(whi-wlo)*PH
    o.append(f'<text x="{ML2}" y="{TOP-16}" class="blab">同一组权的 WNG（dB）→ 代价</text>')
    for v in range(-100, 21, 20):
        y = gy(v)
        o.append(f'<line x1="{ML2}" y1="{y:.1f}" x2="{ML2+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML2-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{ML2}" y1="{gy(0):.1f}" x2="{ML2+PW}" y2="{gy(0):.1f}" class="zero"/>')
    for i, M in enumerate(Ms):
        pts = []
        for kd in kds:
            _, g = di_wng(M, kd)
            v = 10*math.log10(max(g, 1e-30))
            if v < wlo:                       # 掉出画面就断开，不压成平线
                if pts: break
                continue
            pts.append(f'{fx2(kd):.1f},{gy(min(v, whi)):.1f}')
        o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{O[i]}" '
                 f'stroke-width="2.2" stroke-linejoin="round"/>')
        if pts:
            px, py = pts[max(0, len(pts)//7)].split(',')
            o.append(f'<text x="{float(px)+6:.1f}" y="{float(py)+13:.1f}" class="bsub" '
                     f'fill="{O[i]}">M={M}</text>')
    # DAS 的 WNG 是常数 10log M
    for i, M in enumerate([4]):
        o.append(f'<line x1="{ML2}" y1="{gy(10*math.log10(M)):.1f}" x2="{ML2+PW}" '
                 f'y2="{gy(10*math.log10(M)):.1f}" stroke="var(--s2)" stroke-width="1.8" '
                 f'stroke-dasharray="3 2.5"/>')
        o.append(f'<text x="{ML2+PW-2}" y="{gy(10*math.log10(M))-6:.1f}" class="bsub" '
                 f'text-anchor="end" fill="var(--s2)">DAS：10log₁₀M，与 kd 无关</text>')
    # 斜率标注
    o.append(f'<text x="{fx2(0.0105):.1f}" y="{gy(-7):.1f}" class="bsub" fill="{O[1]}">'
             f'每条的斜率都是 20(M−1) dB/十倍频</text>')
    o.append(f'<text x="{fx2(0.0105):.1f}" y="{gy(-16):.1f}" class="bsub" fill="var(--text-3)">'
             f'＝ 6(M−1) dB/倍频程，和 07 节是同一条曲线</text>')
    for v, lab in [(0.01,'0.01'), (0.1,'0.1'), (1.0,'1'), (math.pi,'π')]:
        o.append(f'<line x1="{fx2(v):.1f}" y1="{TOP+PH}" x2="{fx2(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx2(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML2+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">kd（间距／波长）</text>')

    # 图例
    for i, M in enumerate(Ms):
        x = ML + 4 + i*66
        o.append(f'<line x1="{x}" y1="{H-10}" x2="{x+16}" y2="{H-10}" stroke="{O[i]}" stroke-width="2.6"/>')
        o.append(f'<text x="{x+21}" y="{H-6}" class="bsub">M = {M}</text>')
    o.append(f'<text x="{ML2}" y="{H-6}" class="bsub" fill="var(--text-3)">'
             f'（60 位精度计算，双精度在 kd &lt; 0.1 会先崩掉）</text>')

    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('左图：端射超指向阵的 DI 随 kd 减小单调逼近虚线标出的 20log10M 上限，'
                          'M 越大上限越高；作为对照，DAS 的 DI 远低于该上限。'
                          '右图：同一组权的白噪声增益随 kd 以每十倍频 20(M-1) dB 的斜率坠落，'
                          '而 DAS 的 WNG 恒为 10log10M，与 kd 无关')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['bound'] = fig_bound()

# ════════════════════════════════════════════════════════════════
# 图二：Uzkov 的 Σ(2n+1) —— 04 与 27 节是同一个和式
# ════════════════════════════════════════════════════════════════
def fig_uzkov():
    W, H = 700, 318
    o = ['<text x="10" y="18" class="ct">'
         '上界 M² 的来历：<tspan font-weight="700">1 + 3 + 5 + ⋯ = M²</tspan>'
         '<tspan class="cu"> · 每一阶方向图各自能贡献多少</tspan></text>']

    # ── 左：阶梯拼图 ──────────────────────────────────────────
    BX, BY, UW, UH = 34, 70, 30, 30
    M = 4
    o.append(f'<text x="{BX}" y="{BY-16}" class="blab">第 n 阶贡献 2n+1 块，拼成完全平方</text>')
    for n in range(M):
        col = O[n]
        cells = [(n, j) for j in range(n+1)] + [(i, n) for i in range(n)]
        for (r, cc) in cells:
            x = BX + cc*UW; y = BY + r*UH
            o.append(f'<rect x="{x}" y="{y}" width="{UW-3}" height="{UH-3}" rx="3" '
                     f'fill="{col}" fill-opacity="0.9" stroke="var(--surface)" stroke-width="1.2"/>')
        o.append(f'<text x="{BX+M*UW+14}" y="{BY+n*UH+19}" class="bsub" fill="{col}">'
                 f'n = {n}　贡献 {2*n+1} 块</text>')
    o.append(f'<line x1="{BX}" y1="{BY+M*UH+7}" x2="{BX+M*UW-3}" y2="{BY+M*UH+7}" class="ar-d"/>')
    o.append(f'<text x="{BX+(M*UW-3)/2:.0f}" y="{BY+M*UH+23}" class="bsub" '
             f'text-anchor="middle">M = 4 个阵元</text>')
    o.append(f'<text x="{BX}" y="{BY+M*UH+56}" class="blab">'
             f'1 + 3 + 5 + 7 = <tspan fill="var(--s2)">16</tspan> = M²　'
             f'→　DI ≤ <tspan fill="var(--s2)">12.04 dB</tspan></text>')
    o.append(f'<text x="{BX}" y="{BY+M*UH+74}" class="bsub" fill="var(--text-3)">'
             f'等号成立当 c_n ∝ 2n+1——每一阶都恰好"按份额"用满</text>')

    # ── 右：两节的同一个和式 ──────────────────────────────────
    RX, RW = 366, 300
    o.append(f'<text x="{RX}" y="{BY-16}" class="blab">04 节和 27 节，是同一个和式</text>')
    rows = [('04 节　端射线阵', 'M 个阵元 → 合成 M−1 次多项式',
             'n 从 0 加到 M−1：　Σ(2n+1) = M²', 'var(--s1)'),
            ('27 节　球阵球谐', 'N 阶球谐 → (N+1)² 个模态',
             'n 从 0 加到 N：　　Σ(2n+1) = (N+1)²', 'var(--s3)')]
    for i, (who, how, eq, col) in enumerate(rows):
        y = BY - 4 + i*84
        o.append(f'<rect x="{RX}" y="{y}" width="{RW}" height="62" rx="5" '
                 f'fill="var(--surface-2)" stroke="{col}" stroke-width="1.3"/>')
        o.append(f'<text x="{RX+12}" y="{y+20}" class="blab" fill="{col}">{who}</text>')
        o.append(f'<text x="{RX+12}" y="{y+37}" class="bsub">{how}</text>')
        o.append(f'<text x="{RX+12}" y="{y+54}" class="bsub" fill="var(--text)">{eq}</text>')
    ym = BY - 4 + 62 + 11
    o.append(f'<text x="{RX+RW/2:.0f}" y="{ym}" class="bsub" text-anchor="middle" '
             f'fill="var(--text-3)">同一个 Cauchy–Schwarz　·　N = M − 1</text>')
    o.append(f'<rect x="{RX}" y="{BY+164}" width="{RW}" height="48" rx="5" '
             f'fill="var(--hot-soft)" stroke="var(--s2)" stroke-width="1.3"/>')
    o.append(f'<text x="{RX+12}" y="{BY+184}" class="blab" fill="var(--s2)">'
             f'所以 6.02 / 9.54 / 12.04 dB 到处出现</text>')
    o.append(f'<text x="{RX+12}" y="{BY+201}" class="bsub">'
             f'M=2 与 N=1 是同一个 4；M=4 与 N=3 是同一个 16。</text>')

    o.append(f'<text x="14" y="{H-12}" class="arlab">'
             f'两条路都终结在 Σ(2n+1)：<tspan font-weight="600">能用的方向图基函数只有那么多阶，'
             f'每阶能贡献的份额是 2n+1</tspan>——这就是指向性的天花板。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('左边用 4×4 的方块阵列把 1+3+5+7=16 拼成完全平方，每个 L 形对应一阶方向图，'
                          '第 n 阶贡献 2n+1 块；右边指出 04 节端射线阵的 M 平方与 27 节球谐的 '
                          '(N+1) 平方是同一个求和，对应关系是 N = M 减 1')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['uzkov'] = fig_uzkov()

json.dump(OUT, open('figs7.json', 'w'))
for k, v in OUT.items():
    print('figs7.json: %-8s %.1f KB' % (k, len(v)/1024))
