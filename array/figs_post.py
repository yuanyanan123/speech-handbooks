#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§18：Zelinski/McCowan 的偏差，以及音乐噪声的机理。"""
import json, math, html
import numpy as np
rng = np.random.default_rng(20260916)
c = 343.0; M = 4; d = 0.035
OUT = {}
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']

def gbar(f):
    m = np.arange(M); D = np.abs(m[:,None]-m[None,:])*d
    G = np.sinc(2*f*D/c); iu = np.triu_indices(M,1); return G[iu].mean()

# ════════════════════════════════════════════════════════════════
# 图一：两个估计器的偏差
# ════════════════════════════════════════════════════════════════
def fig_postfilt():
    W, H = 700, 360
    ML, PW, TOP, PH = 46, 262, 54, 224
    ML2 = 412
    lo, hi = 100., 8000.
    fx  = lambda f: ML  + (math.log10(f)-math.log10(lo))/(math.log10(hi)-math.log10(lo))*PW
    fx2 = lambda f: ML2 + (math.log10(f)-math.log10(lo))/(math.log10(hi)-math.log10(lo))*PW
    o = ['<text x="10" y="18" class="ct">Zelinski 的那条假设，'
         '<tspan font-weight="700">正好在最需要降噪的频段失效</tspan>'
         '<tspan class="cu"> · 4 麦、35 mm</tspan></text>']

    # ── 左：Γ̄(f) ────────────────────────────────────────────
    fy = lambda v: TOP + (1.05-v)/(1.05-(-0.25))*PH
    o.append(f'<text x="{ML}" y="{TOP-16}" class="blab">通道间噪声相干 Γ̄(f)</text>')
    for v in [1.0, 0.5, 0.0]:
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v:g}</text>')
    fs_ = np.logspace(math.log10(lo), math.log10(hi), 300)
    gb = np.array([gbar(f) for f in fs_])
    pts = ' '.join(f'{fx(f):.1f},{fy(max(v,-0.25)):.1f}' for f, v in zip(fs_, gb))
    # 误差区域填充
    poly = pts + f' {fx(hi):.1f},{fy(0):.1f} {fx(lo):.1f},{fy(0):.1f}'
    o.append(f'<polygon points="{poly}" fill="var(--s2)" fill-opacity="0.13"/>')
    o.append(f'<polyline points="{pts}" fill="none" stroke="{S[0]}" stroke-width="2.4"/>')
    o.append(f'<line x1="{ML}" y1="{fy(0):.1f}" x2="{ML+PW}" y2="{fy(0):.1f}" '
             f'stroke="var(--s2)" stroke-width="2" stroke-dasharray="5 3"/>')
    o.append(f'<text x="{ML+PW-2}" y="{fy(0)-7:.1f}" class="bsub" text-anchor="end" '
             f'fill="var(--s2)">Zelinski 假设 Γ = 0</text>')
    o.append(f'<text x="{fx(150):.1f}" y="{fy(0.88):.1f}" class="bsub" fill="{S[0]}">真实的 Γ̄</text>')
    o.append(f'<text x="{fx(330):.1f}" y="{fy(0.36):.1f}" class="bsub" fill="var(--s2)">'
             f'这块面积就是偏差</text>')
    for f, lab in [(100,'100'),(250,'250'),(1000,'1k'),(2000,'2k'),(4000,'4k'),(8000,'8k')]:
        o.append(f'<line x1="{fx(f):.1f}" y1="{TOP+PH}" x2="{fx(f):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">频率 (Hz)</text>')

    # ── 右：实际压制量 ──────────────────────────────────────
    slo, shi = -1., 7.
    gy = lambda v: TOP + (shi-v)/(shi-slo)*PH
    o.append(f'<text x="{ML2}" y="{TOP-16}" class="blab">实际压制量（dB）· 输入 SNR = 0 dB</text>')
    for v in range(0, 8, 2):
        y = gy(v)
        o.append(f'<line x1="{ML2}" y1="{y:.1f}" x2="{ML2+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML2-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    xi = 1.0
    Gt = xi/(1+xi)
    o.append(f'<line x1="{ML2}" y1="{gy(-20*math.log10(Gt)):.1f}" x2="{ML2+PW}" '
             f'y2="{gy(-20*math.log10(Gt)):.1f}" stroke="{S[2]}" stroke-width="2.4"/>')
    o.append(f'<text x="{ML2+6}" y="{gy(-20*math.log10(Gt))-7:.1f}" class="bsub" fill="{S[2]}">'
             f'真值 = McCowan：6.02 dB，全频段正确</text>')
    pz = []
    for f in fs_:
        g = (xi+gbar(f))/(1+xi)
        pz.append(f'{fx2(f):.1f},{gy(min(max(-20*math.log10(max(g,1e-6)),slo),shi)):.1f}')
    o.append(f'<polyline points="{" ".join(pz)}" fill="none" stroke="var(--s2)" stroke-width="2.4"/>')
    o.append(f'<text x="{fx2(220):.1f}" y="{gy(0.85):.1f}" class="bsub" fill="var(--s2)">Zelinski</text>')
    # 3 dB 失效点
    f3 = None
    for f in np.linspace(100, 8000, 4000):
        if 20*math.log10((xi+gbar(f))/xi) < 3: f3 = f; break
    o.append(f'<line x1="{fx2(f3):.1f}" y1="{gy(slo):.1f}" x2="{fx2(f3):.1f}" y2="{gy(shi):.1f}" '
             f'stroke="var(--text-3)" stroke-width="1.1" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{fx2(f3)-7:.1f}" y="{gy(5.2):.1f}" class="bsub" text-anchor="end" '
             f'fill="var(--text-3)">{f3:.0f} Hz 以下</text>')
    o.append(f'<text x="{fx2(f3)-7:.1f}" y="{gy(4.5):.1f}" class="bsub" text-anchor="end" '
             f'fill="var(--text-3)">Zelinski 少压 &gt; 3 dB</text>')
    o.append(f'<line x1="{ML2}" y1="{gy(0):.1f}" x2="{ML2+PW}" y2="{gy(0):.1f}" class="zero"/>')
    o.append(f'<text x="{fx2(7000):.1f}" y="{gy(-0.55):.1f}" class="bsub" text-anchor="end" '
             f'fill="var(--text-3)">高频 Γ̄ 转负 → 反而多压</text>')
    for f, lab in [(100,'100'),(250,'250'),(1000,'1k'),(2000,'2k'),(4000,'4k'),(8000,'8k')]:
        o.append(f'<line x1="{fx2(f):.1f}" y1="{TOP+PH}" x2="{fx2(f):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx2(f):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML2+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">频率 (Hz)</text>')

    o.append(f'<text x="14" y="{H-10}" class="arlab">'
             f'McCowan 只是把 Γ 从 0 换成真实值，<tspan font-weight="600">'
             f'一行代码的差别，低频换回 5–6 dB</tspan>。'
             f'代价是要知道阵列几何——而那在 01 节就已经有了。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('左图：四麦三十五毫米阵列通道间的噪声相干在 2 千赫以下都接近 1，'
                          '而 Zelinski 假设它是 0，两者之间的面积就是估计偏差。'
                          '右图：输入信噪比 0 分贝时真正该有的压制量是 6.02 分贝，'
                          'McCowan 全频段正确，Zelinski 在 2 千赫以下少压超过 3 分贝，'
                          '在 125 赫兹几乎一点都不压')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['postfilt'] = fig_postfilt()

# ════════════════════════════════════════════════════════════════
# 图二：音乐噪声
# ════════════════════════════════════════════════════════════════
def fig_music():
    W, H = 700, 372
    o = ['<text x="10" y="18" class="ct">音乐噪声不是玄学，'
         '<tspan font-weight="700">是功率估计的方差</tspan>'
         '<tspan class="cu"> · 纯噪声输入，增益本该恒为地板值</tspan></text>']

    # ── 左：两张时频热力图 ──────────────────────────────────
    NT, NF = 46, 16
    CW, CH = 5.6, 5.6
    BX = 44
    K = 4
    pn1 = rng.gamma(K, 1.0/K, (NF, NT)); pn2 = rng.gamma(K, 1.0/K, (NF, NT))
    raw = np.clip((pn1-pn2)/pn1, 0, 1)
    sm = np.zeros_like(raw); acc = raw[:, 0].copy()
    for t in range(NT):
        acc = 0.7*acc + 0.3*raw[:, t]; sm[:, t] = acc
    fixed = np.maximum(sm, 10**(-12/20))

    for idx, (mat, title, sub) in enumerate([
            (raw, '① 直接用估计值', '每格独立跳动 → 叮叮咚咚'),
            (fixed, '② 时间平滑 α=0.7 + 地板 −12 dB', '底噪回到平的，代价是少压一点')]):
        TY = 58 + idx*138
        o.append(f'<text x="{BX}" y="{TY-14}" class="blab">{title}'
                 f'<tspan class="bsub" fill="var(--text-3)">　{sub}</tspan></text>')
        LV = 12
        buckets = {}
        for i in range(NF):
            for t in range(NT):
                lv = int(round(float(mat[i, t])*(LV-1)))
                if lv == 0: continue
                buckets.setdefault(lv, []).append(
                    'M%.1f %.1fh%.1fv%.1fh-%.1fz' % (BX+t*CW, TY+i*CH, CW-0.5, CH-0.5, CW-0.5))
        for lv in sorted(buckets):
            o.append('<path d="%s" fill="var(--s1)" fill-opacity="%.3f"/>'
                     % (''.join(buckets[lv]), lv/(LV-1)))
        o.append(f'<rect x="{BX-1}" y="{TY-1}" width="{NT*CW+1:.1f}" height="{NF*CH+1:.1f}" '
                 f'fill="none" stroke="var(--border-2)" stroke-width="1"/>')
        o.append(f'<text x="{BX-6}" y="{TY+NF*CH/2:.0f}" class="bsub" text-anchor="end" '
                 f'transform="rotate(-90 {BX-6} {TY+NF*CH/2:.0f})">频率</text>')
        o.append(f'<text x="{BX+NT*CW/2:.0f}" y="{TY+NF*CH+15:.0f}" class="bsub" '
                 f'text-anchor="middle">时间 →</text>')
    # 色标
    LX = BX + NT*CW + 16
    o.append(f'<text x="{LX}" y="{54}" class="bsub">增益</text>')
    for i in range(6):
        g = i/5
        o.append(f'<rect x="{LX}" y="{62+i*13}" width="13" height="12" fill="var(--s1)" '
                 f'fill-opacity="{g:.2f}" stroke="var(--border-2)" stroke-width="0.6"/>')
    o.append(f'<text x="{LX+17}" y="{71}" class="bsub" fill="var(--text-3)">0 压死</text>')
    o.append(f'<text x="{LX+17}" y="{136}" class="bsub" fill="var(--text-3)">1 放行</text>')

    # ── 右：K → 方差 ────────────────────────────────────────
    RX, RW, RT, RH = 400, 250, 74, 168
    klist = [1, 2, 4, 8, 16, 32]
    sig = []
    frac = []
    for K_ in klist:
        Nn = 40000
        ps = rng.gamma(K_, 1.0/K_, Nn); pn = rng.gamma(K_, 1.0/K_, Nn)
        Gh = np.clip(ps/(ps+pn), 0, 1)
        sig.append(Gh.std()); frac.append(100*((Gh < 0.1) | (Gh > 0.9)).mean())
    o.append(f'<text x="{RX}" y="{RT-16}" class="blab">平均的帧数 K 决定抖动</text>')
    o.append(f'<text x="{RX}" y="{RT-2}" class="bsub" fill="var(--text-3)">'
             f'真值 G = 0.5，柱高是增益的标准差</text>')
    bw = RW/len(klist)
    for i, K_ in enumerate(klist):
        hgt = sig[i]/0.32*RH
        x = RX + i*bw + 6
        o.append(f'<rect x="{x:.1f}" y="{RT+14+RH-hgt:.1f}" width="{bw-14:.1f}" height="{hgt:.1f}" '
                 f'rx="2.5" fill="{S[0] if K_>1 else "var(--s2)"}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+(bw-14)/2:.1f}" y="{RT+14+RH-hgt-14:.1f}" class="bsub" '
                 f'text-anchor="middle" fill="{S[0] if K_>1 else "var(--s2)"}">{sig[i]:.2f}</text>')
        o.append(f'<text x="{x+(bw-14)/2:.1f}" y="{RT+14+RH-hgt-4:.1f}" class="bsub" '
                 f'text-anchor="middle" fill="var(--text-3)">{frac[i]:.0f}%</text>')
        o.append(f'<text x="{x+(bw-14)/2:.1f}" y="{RT+14+RH+15:.1f}" class="ctick" '
                 f'text-anchor="middle">{K_}</text>')
    o.append(f'<line x1="{RX}" y1="{RT+14+RH:.1f}" x2="{RX+RW}" y2="{RT+14+RH:.1f}" class="grid"/>')
    o.append(f'<text x="{RX+RW/2:.0f}" y="{RT+14+RH+32:.0f}" class="cax" text-anchor="middle">'
             f'用多少帧平均 K</text>')
    o.append(f'<text x="{RX}" y="{RT+14+RH+50:.0f}" class="bsub">'
             f'柱顶第二行是<tspan fill="var(--s2)">"被压死或被放行"的格子占比</tspan></text>')
    o.append(f'<text x="{RX}" y="{RT+14+RH+66:.0f}" class="bsub" fill="var(--text-3)">'
             f'K = 1 时五分之一的格子走极端</text>')
    o.append(f'<text x="{RX}" y="{RT+14+RH+82:.0f}" class="bsub" fill="var(--text-3)">'
             f'——那就是听到的那个声音</text>')

    o.append(f'<text x="14" y="{H-10}" class="arlab">'
             f'一帧的功率估计服从 χ²₂：<tspan font-weight="600">标准差等于均值本身</tspan>。'
             f'所以问题不在维纳公式，在喂给它的 ξ 太抖——'
             f'治法是平滑和设地板，不是换更聪明的增益函数。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('左边两张时频图：纯噪声输入下，直接使用逐帧估计的维纳增益使各个时频格子随机忽明忽暗，'
                          '这就是音乐噪声；经时间平滑并设 −12 分贝地板后整片变得均匀。'
                          '右边柱状图：平均帧数 K 从 1 增到 32 时，增益的标准差从 0.29 降到 0.06，'
                          '走极端的格子占比从两成降到几乎为零')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['music'] = fig_music()
json.dump(OUT, open('figs9.json', 'w'))
for k, v in OUT.items(): print('figs9.json: %-10s %.1f KB' % (k, len(v)/1024))
