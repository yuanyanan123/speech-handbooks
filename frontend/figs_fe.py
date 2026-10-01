#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《前端信号处理手册》新增部分的图：三种信息源，以及回声那一部分的四组实测。"""
import json
import numpy as np

AD = json.load(open('demo_aec_adapt.json'))
DT = json.load(open('demo_aec_dtd.json'))
DR = json.load(open('demo_aec_drift.json'))
RS = json.load(open('demo_aec_res.json'))

C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
HOT = 'var(--hot)'
T3, T2 = 'var(--text-3)', 'var(--text-2)'
OUT = {}


def svg(w, h, o, label, cls='chart'):
    return (f'<svg viewBox="0 0 {w} {h}" class="{cls}" role="img" aria-label="{label}">'
            + ''.join(o) + '</svg>')


def foot(o, H, lines, y0=None, dy=18):
    y0 = y0 or (H - 18 - (len(lines) - 1) * dy)
    o.append(f'<line x1="14" y1="{y0-20}" x2="686" y2="{y0-20}" class="grid"/>')
    for i, (t, c) in enumerate(lines):
        t = t.replace('<b>', '<tspan font-weight="600">').replace('</b>', '</tspan>')
        cc = f' fill="{c}"' if c else ''
        o.append(f'<text x="14" y="{y0+i*dy}" class="arlab"{cc}>{t}</text>')


def ygrid(o, X, W, vals, f2y, fmt='%g', suf=''):
    for v in vals:
        y = f2y(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+W}" y2="{y:.1f}" class="grid"/>')
        s = (fmt % v)
        if s.startswith('-'):
            s = '−' + s[1:]
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">'
                 f'{s}{suf}</text>')


def poly(o, pts, col, w=2.2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    o.append('<polyline points="' + ' '.join('%.1f,%.1f' % p for p in pts)
             + f'" fill="none" stroke="{col}" stroke-width="{w}"{d}/>')


def neg(s):
    return ('−' + s[1:]) if s.startswith('-') else s


# ══════════════════════════════════════════════════════════════
def fig_three():
    """总纲：一个前端只有三种信息可用"""
    W, H = 700, 388
    o = ['<text x="10" y="18" class="ct">一个前端只有三种信息可用：'
         '<tspan font-weight="700">空间、统计、参考</tspan>'
         '<tspan class="cu"> · 这本书的三个部分，就是这三种信息各自能换来多少</tspan></text>']
    cols = [(30, '空间', C1, '多个麦克风',
             ['目标和干扰来自不同方向', '协方差矩阵给出空间结构',
              '可以<tspan font-weight="600">线性地</tspan>把它们分开',
              '上限：阵元数与孔径'],
             'DI ≤ 10·log₁₀M'),
            (255, '统计', C2, '只有一路',
             ['方向信息全没了', '只能假设"噪声比语音平稳"',
              '只能逐时频点地压增益',
              '上限：假设成立的程度'],
             '假设失效 → 一种特定的失真'),
            (480, '参考', C3, '知道自己播了什么',
             ['x(t) 完全已知', '这是<tspan font-weight="600">辨识</tspan>问题，不是估计问题',
              '理论上可以消干净',
              '上限：截断 / 非线性 / 底噪'],
             'ERLE ≤ −10·log₁₀(ε)')]
    for x0, name, col, sub, items, cap in cols:
        o.append(f'<rect x="{x0}" y="42" width="190" height="196" rx="6" '
                 f'fill="{col}" fill-opacity="0.07" stroke="{col}" '
                 f'stroke-opacity="0.35"/>')
        o.append(f'<text x="{x0+14}" y="68" class="blab" fill="{col}">{name}</text>')
        o.append(f'<text x="{x0+14}" y="86" class="ctick" fill="{T3}">{sub}</text>')
        for i, it in enumerate(items):
            o.append(f'<text x="{x0+14}" y="{110+i*22}" class="ctick" fill="{T2}">'
                     f'· {it}</text>')
        o.append(f'<text x="{x0+14}" y="{222}" class="ctick" fill="{col}">{cap}</text>')
    o.append('<text x="30" y="266" class="blab">三者不是替代关系，是<tspan '
             'font-weight="700">叠加</tspan>关系——缺一种，另外两种补不回来</text>')
    foot(o, H, [
        ('这也是这本书为什么把阵列、单通道、回声写在一起：'
         '它们在工程上是同一条链路的三段，在原理上是三种<b>互不替代</b>的信息。', None),
        ('一个常见的误判是拿其中一种去补另一种：'
         '麦克风不够就把单通道降噪调狠（换来失真）、'
         '回声没消干净就靠后面的抑制去压（换来近端被削）。', HOT),
        ('每一段的上限由不同的东西定，所以"提升前端效果"在三段里指的是三件不同的事。', C2),
    ], y0=306)
    return svg(W, H, o, '前端可用的三种信息：空间、统计、参考，及各自的上限')


# ══════════════════════════════════════════════════════════════
def fig_adapt():
    W, H = 700, 466
    o = ['<text x="10" y="18" class="ct">自适应滤波：'
         '<tspan font-weight="700">快和准的积是守恒的</tspan>'
         '<tspan class="cu"> · 而 ERLE 看不见"准"</tspan></text>']
    # ① μ 的三角
    AX, AY, AW, AH = 58, 72, 250, 128
    mu = AD['mu']
    xs = [np.log10(r['mu']) for r in mu]
    lo, hi = min(xs), max(xs)
    fx = lambda v: AX + (np.log10(v) - lo) / (hi - lo) * AW
    ylo, yhi = -50.0, -28.0
    fy = lambda v: AY + (yhi - v) / (yhi - ylo) * AH
    o.append(f'<text x="16" y="{AY-28}" class="blab">'
             f'① 步长 μ：收敛时间（柱）与稳态失调（线）</text>')
    ygrid(o, AX, AW, [-30, -35, -40, -45, -50], fy, '%g', ' dB')
    tmax = max(r['t20'] for r in mu) * 1.1
    for r_ in mu:
        x = fx(r_['mu'])
        hbar = r_['t20'] / tmax * AH
        o.append(f'<rect x="{x-11:.1f}" y="{AY+AH-hbar:.1f}" width="22" '
                 f'height="{hbar:.1f}" fill="{C3}" fill-opacity="0.28"/>')
        o.append(f'<text x="{x:.1f}" y="{AY+AH-hbar-5:.1f}" class="ctick" '
                 f'text-anchor="middle" fill="{C3}">{r_["t20"]:.2f}s</text>')
    poly(o, [(fx(r_['mu']), fy(r_['misalign'])) for r_ in mu], C1)
    for r_ in mu:
        o.append(f'<circle cx="{fx(r_["mu"]):.1f}" cy="{fy(r_["misalign"]):.1f}" '
                 f'r="3.4" fill="{C1}"/>')
        o.append(f'<text x="{fx(r_["mu"]):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r_["mu"]:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" '
             f'text-anchor="middle">步长 μ（对数轴）</text>')
    # ② ERLE 看不见失调
    EX, EW = 420, 230
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">'
             f'② 同一组里，ERLE 几乎没动</text>')
    elo, ehi = 26.0, 32.0
    fey = lambda v: AY + (ehi - v) / (ehi - elo) * AH
    fex = lambda v: EX + (np.log10(v) - lo) / (hi - lo) * EW
    ygrid(o, EX, EW, [27, 29, 31], fey, '%g', ' dB')
    poly(o, [(fex(r_['mu']), fey(r_['erle'])) for r_ in mu], C2)
    for r_ in mu:
        o.append(f'<circle cx="{fex(r_["mu"]):.1f}" cy="{fey(r_["erle"]):.1f}" '
                 f'r="3.4" fill="{C2}"/>')
        o.append(f'<text x="{fex(r_["mu"]):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r_["mu"]:g}</text>')
    o.append(f'<text x="{EX+EW/2:.0f}" y="{AY+AH+32}" class="cax" '
             f'text-anchor="middle">步长 μ</text>')

    # ③ 白化
    BY = 250
    o.append(f'<text x="16" y="{BY}" class="blab">'
             f'③ 逐频点归一化（输入白化）值多少——取决于远端的谱</text>')
    BX, BW = 150, 300
    wt = AD['white']
    mx = max(max(abs(r_['on']), abs(r_['off'])) for r_ in wt) * 1.12
    gx = lambda v: BX + abs(v) / mx * BW
    for i, r_ in enumerate(wt):
        y = BY + 24 + i * 28
        o.append(f'<text x="{BX-10}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'{r_["kind"]}（扩散 {AD["spec"][i]["spread"]:.0f}）</text>')
        o.append(f'<rect x="{BX}" y="{y-9:.1f}" width="{gx(r_["on"])-BX:.1f}" '
                 f'height="8" rx="2" fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<text x="{gx(r_["on"])+5:.1f}" y="{y-2:.1f}" class="ctick" '
                 f'fill="{C1}">开 {r_["on"]:.2f} dB</text>')
        o.append(f'<rect x="{BX}" y="{y+2:.1f}" width="{gx(r_["off"])-BX:.1f}" '
                 f'height="8" rx="2" fill="{C3}" fill-opacity="0.85"/>')
        col = HOT if r_['gain'] < 0 else T2
        o.append(f'<text x="{gx(r_["off"])+5:.1f}" y="{y+9:.1f}" class="ctick" '
                 f'fill="{C3}">关 {r_["off"]:.2f} dB</text>')
        o.append(f'<text x="{BX+BW+96}" y="{y+4:.1f}" class="ctick" fill="{col}">'
                 f'{"白化赚" if r_["gain"]>0 else "白化反而亏"} {abs(r_["gain"]):.2f} dB</text>')
    o.append(f'<text x="{BX}" y="{BY+24+3*28+6}" class="ctick" fill="{T3}">'
             f'横轴是失调（越长越好）</text>')

    tr = AD['mu_tradeoff']
    foot(o, H, [
        ('μ 从 %g 变到 %g（%.0f 倍）：收敛时间变 %.1f 倍、稳态失调变 %.2f dB，'
         '而<b>两者的积只在 %.1f 倍以内浮动</b>。'
         % (mu[0]['mu'], mu[-1]['mu'], mu[-1]['mu'] / mu[0]['mu'],
            mu[0]['t20'] / mu[-1]['t20'], mu[0]['misalign'] - mu[-1]['misalign'],
            tr['prod_spread']), None),
        ('想同时要快和准，只能换算法（变步长、双滤波器），<b>不能靠调 μ</b>。', C1),
        ('右上角那条线是这一节最该记住的：失调差了 %.2f dB，ERLE 只差 %.2f dB——'
         '<b>ERLE 看不见路径估得准不准</b>。'
         % (mu[0]['misalign'] - mu[-1]['misalign'],
            abs(mu[0]['erle'] - mu[-1]['erle'])), C2),
    ], y0=398)
    return svg(W, H, o, '步长与收敛速度、稳态失调的三角关系，以及输入白化在不同远端谱上的收益')


# ══════════════════════════════════════════════════════════════
def fig_dtd():
    W, H = 700, 470
    o = ['<text x="10" y="18" class="ct">双讲检测：'
         '<tspan font-weight="700">漏检是阈值型的，误检是渐进型的</tspan>'
         '<tspan class="cu"> · 所以最优工作点必然偏向多冻结</tspan></text>']
    # ① 阈值扫描
    AX, AY, AW, AH = 58, 72, 248, 126
    sw = DT['sweep']
    xs = [np.log10(r_['kappa']) for r_ in sw]
    lo, hi = min(xs), max(xs)
    fx = lambda v: AX + (np.log10(v) - lo) / (hi - lo) * AW
    o.append(f'<text x="16" y="{AY-28}" class="blab">'
             f'① 阈值 κ：两种错误率（左轴）与单讲段 ERLE（线）</text>')
    fy = lambda v: AY + (100 - v) / 100 * AH
    ygrid(o, AX, AW, [0, 50, 100], fy, '%g', '%')
    poly(o, [(fx(r_['kappa']), fy(r_['fa'])) for r_ in sw], C3, dash='4 3')
    poly(o, [(fx(r_['kappa']), fy(r_['miss'])) for r_ in sw], HOT)
    elo, ehi = 10.0, 17.0
    fey = lambda v: AY + (ehi - v) / (ehi - elo) * AH
    poly(o, [(fx(r_['kappa']), fey(r_['erle'])) for r_ in sw], C1, w=2.6)
    b = DT['best']
    o.append(f'<circle cx="{fx(b["kappa"]):.1f}" cy="{fey(b["erle"]):.1f}" r="5" '
             f'fill="none" stroke="{C1}" stroke-width="2"/>')
    o.append(f'<text x="{fx(b["kappa"])+8:.1f}" y="{fey(b["erle"])-6:.1f}" '
             f'class="ctick" fill="{C1}">最优 κ={b["kappa"]:g}</text>')
    o.append(f'<text x="{AX+6}" y="{AY+14}" class="ctick" fill="{C3}">误检</text>')
    o.append(f'<text x="{AX+6}" y="{AY+AH-6}" class="ctick" fill="{HOT}">漏检</text>')
    for r_ in sw:
        o.append(f'<text x="{fx(r_["kappa"]):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r_["kappa"]:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" '
             f'text-anchor="middle">判决阈值 κ（对数轴）</text>')

    # ② 两种错误的代价曲线
    EX, EW = 420, 236
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">② 两种错误的代价形状</text>')
    mi = DT['inject']['miss']
    mmax = max(r_['jump'] for r_ in mi) * 1.25
    fmx = lambda v: EX + v / 0.8 * EW
    fmy = lambda v: AY + (mmax - v) / mmax * AH
    ygrid(o, EX, EW, [0, 2, 4], fmy, '%g', ' dB')
    poly(o, [(fmx(r_['dur']), fmy(max(r_['jump'], 0))) for r_ in mi], HOT)
    for r_ in mi:
        o.append(f'<circle cx="{fmx(r_["dur"]):.1f}" '
                 f'cy="{fmy(max(r_["jump"],0)):.1f}" r="3" fill="{HOT}"/>')
    fa = DT['inject']['fa']
    base = DT['modes'][2]['erle']
    fay = lambda v: AY + (mmax - v) / mmax * AH
    poly(o, [(EX + r_['frac'] * EW, fay((base - r_['erle']) / 4.0)) for r_ in fa],
         C3, dash='4 3')
    for v in (0.0, 0.4, 0.8):
        o.append(f'<text x="{fmx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v:.1f}</text>')
    o.append(f'<text x="{EX+EW/2:.0f}" y="{AY+AH+32}" class="cax" '
             f'text-anchor="middle">漏检时长（s） / 误检占比（0–80%）</text>')
    o.append(f'<text x="{EX+6}" y="{AY+14}" class="ctick" fill="{HOT}">'
             f'漏检：失调恶化</text>')
    o.append(f'<text x="{EX+6}" y="{AY+28}" class="ctick" fill="{C3}">'
             f'误检：ERLE 损失 ÷4</text>')

    # ③ 三条线
    BY = 254
    md = DT['modes']
    o.append(f'<text x="16" y="{BY}" class="blab">③ 冻不冻结，差 %.2f dB</text>'
             % DT['no_dtd_cost'])
    BX, BW = 170, 300
    mx = max(r_['erle'] for r_ in md) * 1.18
    gx = lambda v: BX + v / mx * BW
    for i, r_ in enumerate(md):
        y = BY + 24 + i * 26
        o.append(f'<text x="{BX-10}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'{r_["mode"]}</text>')
        col = [HOT, C3, C1][i]
        o.append(f'<rect x="{BX}" y="{y-7:.1f}" width="{gx(r_["erle"])-BX:.1f}" '
                 f'height="14" rx="2" fill="{col}" fill-opacity="0.88"/>')
        o.append(f'<text x="{gx(r_["erle"])+6:.1f}" y="{y+4:.1f}" class="ctick" '
                 f'fill="{col}">{r_["erle"]:.2f} dB　漏 {r_["miss"]:.0f}% · '
                 f'误 {r_["fa"]:.0f}%</text>')

    kn = DT['miss_knee']
    foot(o, H, [
        ('最优工作点在 κ=%g：漏检 %.1f%%、误检 %.1f%%——<b>相差 %.0f 倍</b>。'
         '按"两种错误相等"去定（κ=%g），ERLE 要低 %.2f dB。'
         % (b['kappa'], b['miss'], b['fa'], b['fa'] / max(b['miss'], 1e-9),
            DT['eer_point']['kappa'], DT['eer_cost']), None),
        ('右上那两条线解释了为什么：漏检短于 %.1f s 几乎零代价（%.2f dB），'
         '%.1f s 就跳到 %.2f dB 并要 %.2f s 才还清；'
         % (kn['free_up_to'], kn['free_jump'], mi[3]['dur'], mi[3]['jump'],
            mi[4]['recover']), HOT),
        ('而误检只是少了更新机会：冻掉一半单讲时间，ERLE 才少 %.2f dB，而且是可以慢慢补回来的。'
         % (base - [r_ for r_ in fa if r_['frac'] == 0.5][0]['erle']), C3),
    ], y0=394)
    return svg(W, H, o, '双讲检测阈值扫描、两种错误的代价形状，以及冻结与否的差距')


# ══════════════════════════════════════════════════════════════
def fig_drift():
    W, H = 700, 462
    o = ['<text x="10" y="18" class="ct">追不上的那一部分：'
         '<tspan font-weight="700">滤波器越长，越扛不住时钟漂移</tspan>'
         '<tspan class="cu"> · 而延迟估偏是悬崖，不是斜坡</tspan></text>']
    # ① ppm
    AX, AY, AW, AH = 58, 72, 248, 128
    pp = DR['ppm'][1:]
    xs = [np.log10(r_['ppm']) for r_ in pp]
    lo, hi = min(xs), max(xs)
    fx = lambda v: AX + (np.log10(v) - lo) / (hi - lo) * AW
    ylo, yhi = 8.0, 32.0
    fy = lambda v: AY + (yhi - v) / (yhi - ylo) * AH
    o.append(f'<text x="16" y="{AY-28}" class="blab">① 时钟差几个 ppm</text>')
    ygrid(o, AX, AW, [10, 15, 20, 25, 30], fy, '%g', ' dB')
    o.append(f'<line x1="{AX}" y1="{fy(DR["ppm"][0]["erle"]):.1f}" x2="{AX+AW}" '
             f'y2="{fy(DR["ppm"][0]["erle"]):.1f}" stroke="{T3}" '
             f'stroke-dasharray="3 3" stroke-width="1"/>')
    o.append(f'<text x="{AX+AW-4}" y="{fy(DR["ppm"][0]["erle"])-5:.1f}" '
             f'class="ctick" text-anchor="end" fill="{T3}">时钟同步时 '
             f'{DR["ppm"][0]["erle"]:.1f} dB</text>')
    poly(o, [(fx(r_['ppm']), fy(r_['erle'])) for r_ in pp], HOT)
    for r_ in pp:
        o.append(f'<circle cx="{fx(r_["ppm"]):.1f}" cy="{fy(r_["erle"]):.1f}" '
                 f'r="3" fill="{HOT}"/>')
        o.append(f'<text x="{fx(r_["ppm"]):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r_["ppm"]:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" '
             f'text-anchor="middle">时钟偏差（ppm，对数轴）</text>')

    # ② 长度 × 漂移
    EX, EW = 420, 230
    ld = DR['len_drift']
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">'
             f'② 同样的漂移，滤波器越长越亏</text>')
    fy2 = lambda v: AY + (42.0 - v) / 42.0 * AH
    ygrid(o, EX, EW, [0, 10, 20, 30, 40], fy2, '%g', ' dB')
    fx2 = lambda i: EX + i / (len(ld) - 1) * EW
    for pi, (ppmv, col) in enumerate(((0, C1), (10, C3), (50, HOT))):
        pts = [(fx2(i), fy2(r_['cells'][pi]['erle'])) for i, r_ in enumerate(ld)]
        poly(o, pts, col, dash=None if pi == 0 else '4 3')
        o.append(f'<text x="{EX+EW+6}" y="{pts[-1][1]:.1f}" class="ctick" '
                 f'fill="{col}">{ppmv} ppm</text>')
    for i, r_ in enumerate(ld):
        o.append(f'<text x="{fx2(i):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r_["l_ms"]}</text>')
    o.append(f'<text x="{EX+EW/2:.0f}" y="{AY+AH+32}" class="cax" '
             f'text-anchor="middle">滤波器长度（ms）</text>')

    # ③ 延迟悬崖
    BY = 256
    dl = DR['delay']
    o.append(f'<text x="16" y="{BY}" class="blab">'
             f'③ 整块延迟吃掉滤波器的覆盖范围</text>')
    BX, BW, BH = 58, 248, 92
    fdx = lambda v: BX + v / dl[-1]['off_ms'] * BW
    fdy = lambda v: BY + 20 + (32.0 - v) / 36.0 * BH
    ygrid(o, BX, BW, [0, 10, 20, 30], fdy, '%g', ' dB')
    poly(o, [(fdx(r_['off_ms']), fdy(r_['erle'])) for r_ in dl], C2)
    for r_ in dl:
        o.append(f'<circle cx="{fdx(r_["off_ms"]):.1f}" cy="{fdy(r_["erle"]):.1f}" '
                 f'r="3" fill="{C2}"/>')
    o.append(f'<line x1="{fdx(DR["delay_note"]["l_ms"]):.1f}" y1="{BY+16}" '
             f'x2="{fdx(DR["delay_note"]["l_ms"]):.1f}" y2="{BY+20+BH}" '
             f'stroke="{HOT}" stroke-dasharray="3 3"/>')
    o.append(f'<text x="{fdx(DR["delay_note"]["l_ms"])-4:.1f}" y="{BY+30}" '
             f'class="ctick" text-anchor="end" fill="{HOT}">延迟＝滤波器长度</text>')
    for v in (0, 64, 128, 160):
        o.append(f'<text x="{fdx(v):.1f}" y="{BY+20+BH+14}" class="ctick" '
                 f'text-anchor="middle">{v}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+20+BH+30}" class="cax" '
             f'text-anchor="middle">参考与采集之间的整块延迟（ms）</text>')

    # ④ 路径突变
    ch = DR['change']
    o.append(f'<text x="400" y="{BY}" class="blab">④ 路径中途变了</text>')
    for i, r_ in enumerate(ch):
        y = BY + 24 + i * 26
        o.append(f'<text x="400" y="{y}" class="ctick" fill="{T3}">{r_["name"]}</text>')
        o.append(f'<text x="676" y="{y}" class="ctick" text-anchor="end" fill="{T2}">'
                 f'掉 {r_["dip"]:.1f} dB · {r_["recover"]:.2f} s 回来</text>')

    ln = DR['len_drift_note']
    foot(o, H, [
        ('我原以为"滤波器加长总能覆盖漂移"。正相反：50 ppm 下 %d ms 的滤波器'
         '几乎不受影响（%.2f dB），%d ms 的要赔 <b>%.2f dB</b>。'
         % (ln['short_ms'], ln['short'], ln['long_ms'], ln['long']), None),
        ('道理是尾部抽头的相关时间最短——漂移先把它们解相关，'
         '而长滤波器正好多的就是尾部。<b>有漂移时，长滤波器是净损失。</b>', HOT),
        ('%d ppm 就是掉 6 dB 的拐点，而消费级晶振是 ±20–50 ppm。'
         '延迟那一栏更干脆：延迟等于滤波器长度时 ERLE %.2f dB，比不处理还差。'
         % (DR['ppm_note']['ppm_6db'], dl[-2]['erle']), C2),
    ], y0=394)
    return svg(W, H, o, '时钟漂移、滤波器长度、整块延迟与路径突变对回声消除的影响')


# ══════════════════════════════════════════════════════════════
def fig_res():
    W, H = 700, 450
    o = ['<text x="10" y="18" class="ct">非线性与残余抑制：'
         '<tspan font-weight="700">把 ERLE 当目标优化，会把近端语音毁掉</tspan>'
         '<tspan class="cu"> · 两个指标的最优点不在一起</tspan></text>']
    # ① 非线性
    AX, AY, AW, AH = 58, 72, 248, 126
    nl = [r_ for r_ in RS['nl'] if r_['thd'] > 0]
    xs = [np.log10(r_['thd']) for r_ in nl]
    lo, hi = min(xs), max(xs)
    fx = lambda v: AX + (np.log10(v) - lo) / (hi - lo) * AW
    fy = lambda v: AY + (34.0 - v) / 26.0 * AH
    o.append(f'<text x="16" y="{AY-28}" class="blab">'
             f'① 喇叭的非线性占比 → 线性 AEC 的上界</text>')
    ygrid(o, AX, AW, [10, 15, 20, 25, 30], fy, '%g', ' dB')
    poly(o, [(fx(r_['thd']), fy(min(r_['theory'], 34))) for r_ in nl], T3, dash='4 3')
    poly(o, [(fx(r_['thd']), fy(r_['erle'])) for r_ in nl], HOT)
    for r_ in nl:
        o.append(f'<circle cx="{fx(r_["thd"]):.1f}" cy="{fy(r_["erle"]):.1f}" '
                 f'r="3" fill="{HOT}"/>')
        o.append(f'<text x="{fx(r_["thd"]):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r_["thd"]:.1f}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" '
             f'text-anchor="middle">非线性占比（%，对数轴）</text>')
    o.append(f'<text x="{AX+6}" y="{AY+14}" class="ctick" fill="{T3}">'
             f'−20log₁₀(非线性占比)</text>')
    o.append(f'<text x="{AX+6}" y="{AY+28}" class="ctick" fill="{HOT}">实测</text>')

    # ② RES 的两头
    EX, EW = 420, 230
    rs = RS['res']
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">'
             f'② RES 越激进：ERLE ↑，近端 ↓</text>')
    gs = [r_['gamma'] for r_ in rs]
    gx = lambda i: EX + i / (len(rs) - 1) * EW
    fy2 = lambda v: AY + (52.0 - v) / 46.0 * AH
    ygrid(o, EX, EW, [10, 20, 30, 40, 50], fy2, '%g', ' dB')
    poly(o, [(gx(i), fy2(r_['erle'])) for i, r_ in enumerate(rs)], C1)
    poly(o, [(gx(i), fy2(r_['near_segsnr'])) for i, r_ in enumerate(rs)], HOT)
    kg = RS['res_note']['knee_gamma']
    ki = gs.index(kg)
    o.append(f'<circle cx="{gx(ki):.1f}" cy="{fy2(rs[ki]["erle"]):.1f}" r="5" '
             f'fill="none" stroke="{C1}" stroke-width="2"/>')
    o.append(f'<text x="{gx(ki)+8:.1f}" y="{fy2(rs[ki]["erle"])-7:.1f}" '
             f'class="ctick" fill="{C1}">拐点 γ={kg:g}</text>')
    o.append(f'<text x="{EX+EW+6}" y="{fy2(rs[-1]["erle"]):.1f}" class="ctick" '
             f'fill="{C1}">ERLE</text>')
    o.append(f'<text x="{EX+EW+6}" y="{fy2(rs[-1]["near_segsnr"]):.1f}" '
             f'class="ctick" fill="{HOT}">近端</text>')
    for i in (0, 3, 6, len(rs) - 1):
        o.append(f'<text x="{gx(i):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{gs[i]:g}</text>')
    o.append(f'<text x="{EX+EW/2:.0f}" y="{AY+AH+32}" class="cax" '
             f'text-anchor="middle">RES 的泄漏系数 γ</text>')

    # ③ 同样的总 ERLE，钱花在哪
    BY = 252
    sp = RS['split']
    o.append(f'<text x="16" y="{BY}" class="blab">'
             f'③ 凑到同样的总 ERLE（约 {RS["const"]["target"]:.0f} dB），'
             f'近端还剩多少</text>')
    BX, BW = 214, 280
    mx = max(r_['near_segsnr'] for r_ in sp) * 1.2
    bx = lambda v: BX + max(v, 0) / mx * BW
    for i, r_ in enumerate(sp):
        y = BY + 24 + i * 28
        col = [HOT, C3, C1][i]
        o.append(f'<text x="{BX-10}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'{r_["name"]}</text>')
        o.append(f'<rect x="{BX}" y="{y-7:.1f}" width="{bx(r_["near_segsnr"])-BX:.1f}" '
                 f'height="14" rx="2" fill="{col}" fill-opacity="0.88"/>')
        o.append(f'<text x="{bx(r_["near_segsnr"])+6:.1f}" y="{y+4:.1f}" '
                 f'class="ctick" fill="{col}">近端 {r_["near_segsnr"]:.2f} dB　'
                 f'（总 ERLE {r_["erle"]:.1f}）</text>')

    nn = RS['nl_note']
    kn = RS['res_note']
    foot(o, H, [
        ('非线性 %.2f%% 还看不出来（只差 %.2f dB）；到 %.2f%% 就掉 %.2f dB，'
         '之后实测紧贴 −20log₁₀(非线性占比) 这条虚线。'
         % (nn['thd1'], nn['drop1'], nn['bind_thd'], nn['bind_drop']), None),
        ('RES 的拐点在 γ=%g：用 %.2f dB 的近端代价换了 %.2f dB 的 ERLE。'
         '再往后 ERLE 只多 %.2f dB，近端却要再掉 <b>%.2f dB</b>。'
         % (kn['knee_gamma'], rs[0]['near_segsnr'] - kn['knee_q'],
            kn['knee_erle_gain'], kn['tail_erle_gain'], kn['tail_q_loss']), HOT),
        ('所以第三栏才是结论：同样的总 ERLE，<b>钱花在线性那一级，近端能多留 %.2f dB</b>。'
         % RS['split_note']['gap'], C1),
    ], y0=382)
    return svg(W, H, o, '扬声器非线性对线性回声消除上界的限制，以及残余抑制的激进程度与近端质量的取舍')


OUT['three'] = fig_three()
OUT['adapt'] = fig_adapt()
OUT['dtd'] = fig_dtd()
OUT['drift'] = fig_drift()
OUT['res'] = fig_res()
json.dump(OUT, open('figs_fe.json', 'w'), ensure_ascii=False)
print('figs_fe.json:', {k: len(v) // 1024 for k, v in OUT.items()})
