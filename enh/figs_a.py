#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《单通道增强手册》图 1–5：骨架、增益族、音乐噪声、判决引导、噪声估计。"""
import json, math
import numpy as np

GA = json.load(open('demo_gain.json'))
DD = json.load(open('demo_dd.json'))
PH = json.load(open('demo_phase.json'))
NN = json.load(open('demo_nn.json'))
EV = json.load(open('demo_eval.json'))

C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
T3, T2 = 'var(--text-3)', 'var(--text-2)'
OUT = {}


def defs(u):
    return (f'<defs><marker id="{u}a" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--text-2)"/></marker></defs>')


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


# ══════════════════════════════════════════════════════════════
def fig_frame():
    W, H = 700, 388
    o = [defs('fr'),
         '<text x="10" y="18" class="ct">单通道的处境：'
         '<tspan font-weight="700">空间自由度为零，只剩下统计假设</tspan>'
         '<tspan class="cu"> · 每一代方法都是在换一个更好的假设</tspan></text>']
    # 两栏对比
    o.append(f'<text x="16" y="52" class="blab">多通道（姊妹篇《麦克风阵列手册》）</text>')
    o.append(f'<text x="360" y="52" class="blab">单通道（这一本）</text>')
    left = ['目标和干扰来自不同方向', '协方差矩阵给出空间结构',
            '可以<tspan font-weight="600">线性</tspan>地把它们分开', '失真小，代价是要多个麦克风']
    right = ['只有一路信号，方向信息全没了', '只能假设"噪声比语音平稳"',
             '只能<tspan font-weight="600">逐时频点</tspan>地压增益', '假设失效时，就有一种特定的失真']
    for i, (a, b) in enumerate(zip(left, right)):
        y = 74 + i * 19
        o.append(f'<text x="16" y="{y}" class="bsub" fill="{T2}">· {a}</text>')
        o.append(f'<text x="360" y="{y}" class="bsub" fill="{C2}">· {b}</text>')
    o.append(f'<line x1="348" y1="40" x2="348" y2="150" class="grid"/>')
    # 链路
    o.append(f'<line x1="14" y1="162" x2="686" y2="162" class="grid"/>')
    o.append('<text x="16" y="184" class="blab">这一族方法的完整链路，四个环节</text>')
    boxes = [('STFT', '窗长决定延迟\n和频率分辨率', '03'),
             ('噪声功率谱 λ', 'MS / MCRA / IMCRA', '04'),
             ('先验信噪比 ξ', '判决引导', '04'),
             ('增益 G', '谱减 / 维纳\n/ log-MMSE', '02')]
    x0, bw, gap = 20, 148, 22
    for i, (t, sub, sec) in enumerate(boxes):
        x = x0 + i * (bw + gap)
        o.append(f'<rect x="{x}" y="196" width="{bw}" height="56" rx="4" '
                 f'class="{"bx-a" if i in (1, 2) else "bx"}"/>')
        o.append(f'<text x="{x+bw/2}" y="{216}" class="blab" text-anchor="middle">{t}</text>')
        for k, ln in enumerate(sub.split('\n')):
            o.append(f'<text x="{x+bw/2}" y="{232+k*13}" class="ctick" '
                     f'text-anchor="middle" fill="{T3}">{ln}</text>')
        o.append(f'<text x="{x+bw-6}" y="{208}" class="ctick" fill="{C1}" '
                 f'text-anchor="end">{sec}</text>')
        if i < 3:
            o.append(f'<line x1="{x+bw}" y1="224" x2="{x+bw+gap-3}" y2="224" '
                     f'class="ar" marker-end="url(#fra)"/>')
    o.append(f'<text x="20" y="274" class="bsub" fill="{T3}">'
             f'重构时把<tspan font-weight="600">带噪相位</tspan>原样放回去——'
             f'这一步被忽略了几十年，05 节量一下它值多少。</text>')
    fl = GA['mus_floor']
    foot(o, H, [
        ('整条链路只有<b>一个输出</b>：每个时频点上的一个实数增益 G。'
         '所有的方法差别都在"G 怎么算"。', None),
        ('而 G 只能依赖<b>假设</b>——噪声平稳、语音稀疏、幅度服从某个分布。'
         '假设失效时的听感失真，各有各的样子。', C2),
        ('全书用一个共同的量来衡量"假设失效了多少"：残差的帧间起伏（dB）。'
         '它有理论零点 <b>%.2f dB</b>（χ²₂ 分布），实测平稳噪声 %.2f dB。'
         % (fl, GA['main']['5'][0]['mus']), None),
    ], y0=330)
    return svg(W, H, o, '单通道与多通道的处境对比，以及经典增强方法的四环节链路',
               'chart diag')


# ══════════════════════════════════════════════════════════════
def fig_gain():
    W, H = 700, 466
    o = ['<text x="10" y="18" class="ct">增益函数一族：'
         '<tspan font-weight="700">同一个 ξ，四条不同的曲线</tspan>'
         '<tspan class="cu"> · 其余条件全部固定，只有增益公式不同</tspan></text>']
    # ① 增益 vs 先验信噪比
    AX, AY, AW, AH = 66, 80, 268, 150
    cv = GA['curve_xi']
    xs = cv['xi_db']
    gx = lambda v: AX + (v - xs[0]) / (xs[-1] - xs[0]) * AW
    lo, hi = -32.0, 2.0
    gy = lambda v: AY + (hi - max(v, lo)) / (hi - lo) * AH
    o.append(f'<text x="{AX-52}" y="{AY-30}" class="blab">① 增益 vs 先验信噪比 ξ</text>')
    o.append(f'<text x="{AX-52}" y="{AY-14}" class="bsub" fill="{T3}">'
             f'取观测与假设一致的那条切面（γ = ξ + 1）</text>')
    ygrid(o, AX, AW, [0, -10, -20, -30], gy, '%g', ' dB')
    for key, col, nm, dash, ly in (('sub', C2, '谱减', None, 0),
                                   ('wiener', C1, '维纳', None, 1),
                                   ('stsa', C3, 'MMSE-STSA', '5 3', 2),
                                   ('logmmse', T2, 'log-MMSE', '2 3', 3)):
        poly(o, [(gx(g), gy(v)) for g, v in zip(xs, cv[key])], col, 2.0, dash)
        o.append(f'<text x="{AX+8}" y="{AY+16+ly*15}" class="ctick" fill="{col}">{nm}</text>')
    for v in (-20, -10, 0, 10, 20):
        o.append(f'<text x="{gx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{"−" if v<0 else ""}{abs(v)}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'先验信噪比 ξ（dB）</text>')
    i5 = xs.index(-5.0)
    o.append(f'<line x1="{gx(-5):.1f}" y1="{gy(cv["wiener"][i5]):.1f}" '
             f'x2="{gx(-5):.1f}" y2="{gy(cv["sub"][i5]):.1f}" stroke="{T2}" '
             f'stroke-width="1.2"/>')
    o.append(f'<text x="{gx(-5)+6:.1f}" y="{gy((cv["wiener"][i5]+cv["sub"][i5])/2)+4:.1f}" '
             f'class="ctick" fill="{T2}">差 {abs(cv["sub"][i5]-cv["wiener"][i5]):.1f} dB</text>')

    # ② 误差的正交分解
    BX, BY, BW, BH = 452, 80, 160, 150
    rows = [r for r in GA['main']['5'] if '理想' not in r['tag']]
    lo2 = -20.0
    hx = lambda v: BX + (max(v, lo2) - lo2) / (0 - lo2) * BW
    o.append(f'<text x="{BX-130}" y="{AY-30}" class="blab">② 输入 5 dB 的实测</text>')
    o.append(f'<text x="{BX-130}" y="{AY-14}" class="bsub" fill="{T3}">'
             f'误差按功率拆两块（正交，可直接相加）</text>')
    for v in (-20, -10, 0):
        o.append(f'<line x1="{hx(v):.1f}" y1="{BY}" x2="{hx(v):.1f}" y2="{BY+BH}" class="grid"/>')
        o.append(f'<text x="{hx(v):.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{"−" if v<0 else ""}{abs(v)}</text>')
    for i, r in enumerate(rows):
        y = BY + 14 + i * 24
        tag = (r['tag'].replace('（α=1，无谱底）', ' α=1')
               .replace('（过减 α=2，谱底 −20 dB）', ' α=2+谱底')
               .replace('带噪（不处理）', '不处理'))
        o.append(f'<text x="{BX-8}" y="{y+4}" class="bsub" text-anchor="end">{tag}</text>')
        for key, col, dy in (('sd_db', C2, -8), ('nr_db', C1, 1)):
            o.append(f'<rect x="{hx(lo2):.1f}" y="{y+dy:.1f}" '
                     f'width="{max(hx(r[key])-hx(lo2),1.5):.1f}" height="7" rx="1.5" '
                     f'fill="{col}" fill-opacity="0.9"/>')
        o.append(f'<text x="{BX+BW+8:.1f}" y="{y+4:.1f}" class="ctick" fill="{T2}">'
                 f'{r["segsnr"]:.2f}</text>')
    o.append(f'<text x="{BX}" y="{BY-2}" class="ctick" fill="{C2}">语音失真</text>')
    o.append(f'<text x="{BX+64}" y="{BY-2}" class="ctick" fill="{C1}">残留噪声</text>')
    o.append(f'<text x="{BX+BW+8}" y="{BY-2}" class="ctick" fill="{T2}">SegSNR</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'相对语音功率（dB）</text>')

    # ③ 过减扫描
    CY = 292
    ov = GA['oversub']
    o.append(f'<text x="16" y="{CY}" class="blab">'
             f'③ 过减因子 α：每多减一点噪声，就多一点语音失真</text>')
    DX = 150
    o.append(f'<text x="{DX-8}" y="{CY+22}" class="bsub" text-anchor="end" fill="{T3}">α</text>')
    for j, key, col, lab in ((0, 'sd_db', C2, '语音失真 dB'), (1, 'nr_db', C1, '残留噪声 dB'),
                             (2, 'tot_db', T2, '总误差 dB'), (3, 'mus', C3, '残差起伏 dB')):
        o.append(f'<text x="{DX-8}" y="{CY+40+j*17}" class="bsub" text-anchor="end" '
                 f'fill="{col}">{lab}</text>')
    for i, r in enumerate(ov):
        x = DX + 30 + i * 62
        o.append(f'<text x="{x}" y="{CY+22}" class="bsub" text-anchor="middle">'
                 f'{r["alpha"]:g}</text>')
        for j, key, col in ((0, 'sd_db', C2), (1, 'nr_db', C1), (2, 'tot_db', T2),
                            (3, 'mus', C3)):
            best = (key == 'tot_db' and r['alpha'] == GA['oversub_best'])
            fw = ' font-weight="600"' if best else ''
            s2 = ('%.1f' % r[key]).replace('-', '−')
            o.append(f'<text x="{x}" y="{CY+40+j*17}" class="bsub" text-anchor="middle" '
                     f'fill="{col}"{fw}>{s2}</text>')
    foot(o, H, [
        ('四条曲线在高 ξ 处都趋近 1（信号强就别动它），差别全在<b>低 ξ 那一段</b>——'
         '维纳压得最狠，谱减最轻。', None),
        ('这一段的陡峭程度，直接决定了残差抖得多厉害，也就决定了有没有音乐噪声。', C2),
        ('过减的总误差最小点在 α = %g，那时残差起伏还有 %.1f dB；'
         '要把起伏压到理论零点附近要 α = %g，而那时语音失真已经涨到 %.1f dB。'
         % (GA['oversub_best'],
            [r for r in ov if r['alpha'] == GA['oversub_best']][0]['mus'],
            ov[-1]['alpha'], ov[-1]['sd_db']), None),
        ('<b>这就是这一族方法的全部张力</b>：噪声抑制、语音失真、残差平稳性，三个只能要两个。',
         None),
    ], y0=412)
    return svg(W, H, o, '四种增益函数随先验信噪比的形状对比、五种方法的误差正交分解，'
                        '以及过减因子的取舍')


# ══════════════════════════════════════════════════════════════
def fig_music():
    W, H = 700, 400
    fl = GA['mus_floor']
    o = ['<text x="10" y="18" class="ct">音乐噪声：'
         '<tspan font-weight="700">它是一个可以量的东西，而且有理论零点</tspan>'
         f'<tspan class="cu"> · 平稳高斯噪声的起伏恰好是 {fl:.2f} dB</tspan></text>']
    AX, AY, AW, AH = 190, 80, 330, 170
    rows = [r for r in GA['main']['5']]
    mx = max(r['mus'] for r in rows) * 1.12
    fx = lambda v: AX + v / mx * AW
    o.append(f'<text x="{AX-170}" y="{AY-30}" class="blab">'
             f'① 残差的帧间起伏（只在无语音帧上量）</text>')
    for v in (0, 5, 10, 15, 20):
        o.append(f'<line x1="{fx(v):.1f}" y1="{AY}" x2="{fx(v):.1f}" y2="{AY+AH}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v}</text>')
    o.append(f'<line x1="{fx(fl):.1f}" y1="{AY-6}" x2="{fx(fl):.1f}" y2="{AY+AH}" '
             f'stroke="{C3}" stroke-width="1.4" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{fx(fl)+6:.1f}" y="{AY-12}" class="ctick" fill="{C3}">'
             f'理论零点 {fl:.2f} dB（平稳高斯噪声）</text>')
    for i, r in enumerate(rows):
        y = AY + 14 + i * 24
        tag = (r['tag'].replace('（α=1，无谱底）', ' α=1')
               .replace('（过减 α=2，谱底 −20 dB）', ' α=2+谱底')
               .replace('理想比值掩码 IRM（上界）', '理想比值掩码')
               .replace('理想二值掩码 IBM（0 dB）', '理想二值掩码'))
        c = C2 if r['mus'] > fl * 1.5 else (C3 if r['mus'] < fl * 0.9 else C1)
        o.append(f'<text x="{AX-8}" y="{y+4}" class="bsub" text-anchor="end">{tag}</text>')
        o.append(f'<rect x="{fx(0):.1f}" y="{y-5:.1f}" '
                 f'width="{max(fx(r["mus"])-fx(0),1.5):.1f}" height="10" rx="2" '
                 f'fill="{c}" fill-opacity="0.9"/>')
        o.append(f'<text x="{fx(r["mus"])+6:.1f}" y="{y+4:.1f}" class="ctick" fill="{c}">'
                 f'{r["mus"]:.2f}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'残差功率的帧间标准差（dB）</text>')
    sub = [r for r in rows if '谱减（α=1' in r['tag']][0]
    lm = [r for r in rows if r['tag'] == 'log-MMSE'][0]
    foot(o, H, [
        ('音乐噪声的物理定义很朴素：<b>同一个频点上，残差功率在帧与帧之间跳得太厉害</b>，'
         '大的那些被听成孤立的纯音。', None),
        ('平稳高斯噪声的周期图服从 χ²₂，取对数后标准差恒为 10/ln10·π/√6 = '
         '<b>%.2f dB</b>，实测 %.2f dB。它是"没有音乐噪声"的下限。'
         % (fl, rows[0]['mus']), C3),
        ('谱减（无谱底）把它推到 %.2f dB，log-MMSE 只有 %.2f dB——'
         '<b>比原始噪声还平稳</b>。这就是它听起来干净的确切原因。'
         % (sub['mus'], lm['mus']), C2),
        ('注意最后两行：理想掩码的起伏也很低，但它是"该压的压掉了"，'
         '而过减是"连该留的也压掉了"。起伏低不等于好——08 节会看到这个陷阱。', T3),
    ], y0=326)
    return svg(W, H, o, '各种增强方法残差的帧间起伏，与平稳高斯噪声的理论零点对比')


# ══════════════════════════════════════════════════════════════
def fig_dd():
    W, H = 700, 382
    o = ['<text x="10" y="18" class="ct">判决引导：'
         '<tspan font-weight="700">它不是一个平滑的估计器，是一个开关</tspan>'
         '<tspan class="cu"> · 这是我写这一节时最没料到的一件事</tspan></text>']
    # ① α 扫描
    AX, AY, AW, AH = 62, 78, 250, 150
    al = DD['alpha']
    lo, hi = -20.0, 0.0
    fy = lambda v: AY + (hi - v) / (hi - lo) * AH
    fx = lambda i: AX + i / (len(al) - 1) * AW
    o.append(f'<text x="{AX-48}" y="{AY-30}" class="blab">① α 在换什么</text>')
    ygrid(o, AX, AW, [0, -5, -10, -15, -20], fy, '%g', ' dB')
    for key, col, nm in (('sd_db', C2, '语音失真'), ('nr_db', C1, '残留噪声')):
        poly(o, [(fx(i), fy(max(r[key], lo))) for i, r in enumerate(al)], col)
        r = al[-1]
        o.append(f'<text x="{fx(len(al)-1)-4:.1f}" y="{fy(max(r[key],lo))+(14 if key=="nr_db" else -8):.1f}" '
                 f'class="ctick" fill="{col}" text-anchor="end">{nm}</text>')
    # 起伏画在右轴
    m2 = max(r['mus'] for r in al)
    fy2 = lambda v: AY + (1 - v / (m2 * 1.15)) * AH
    poly(o, [(fx(i), fy2(r['mus'])) for i, r in enumerate(al)], C3, 2.0, '4 3')
    o.append(f'<text x="{fx(0)+6:.1f}" y="{fy2(al[0]["mus"])-8:.1f}" class="ctick" '
             f'fill="{C3}">残差起伏（右轴）</text>')
    for i, r in enumerate(al):
        if i % 2 == 0 or i == len(al) - 1:
            o.append(f'<text x="{fx(i):.1f}" y="{AY+AH+16}" class="ctick" '
                     f'text-anchor="middle">{r["alpha"]:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'判决引导系数 α</text>')

    # ② 捕获阈值
    BX, BY, BW, BH = 410, 78, 260, 150
    cap = DD['capture']
    o.append(f'<text x="{BX-16}" y="{BY-30}" class="blab">② 固定 γ，ξ̂ 收敛到哪里</text>')
    o.append(f'<text x="{BX-16}" y="{BY-14}" class="bsub" fill="{T3}">'
             f'从静音状态启动；灰虚线是真值 γ−1</text>')
    glo, ghi = 1.0, 16.0
    xlo, xhi = -26.0, 14.0
    hx = lambda g: BX + (g - glo) / (ghi - glo) * BW
    hy = lambda v: BY + (xhi - max(min(v, xhi), xlo)) / (xhi - xlo) * BH
    ygrid(o, BX, BW, [10, 0, -10, -20], hy, '%g', ' dB')
    tru = cap['0.98']['curve']
    poly(o, [(hx(r['gam_db']), hy(r['true_db'])) for r in tru], T3, 1.4, '4 3')
    for a, col in (('0.9', C1), ('0.98', C2), ('0.99', C3)):
        poly(o, [(hx(r['gam_db']), hy(r['xi_db'])) for r in cap[a]['curve']], col, 2.0)
        t = cap[a]['thr_db']
        if t:
            o.append(f'<circle cx="{hx(t):.1f}" cy="{hy(0):.1f}" r="3" fill="{col}"/>')
    for i, (a, col) in enumerate((('0.9', C1), ('0.98', C2), ('0.99', C3))):
        o.append(f'<text x="{BX+4}" y="{BY+26+i*13}" class="ctick" fill="{col}">'
                 f'α={a} → {cap[a]["thr_db"]:.2f} dB</text>')
    o.append(f'<text x="{BX+4}" y="{BY+13}" class="ctick" fill="{T2}">捕获阈值</text>')
    for v in (2, 6, 10, 14):
        o.append(f'<text x="{hx(v):.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{v}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'后验信噪比 γ（dB）</text>')
    a0 = al[0]; a98 = [r for r in al if r['alpha'] == 0.98][0]
    foot(o, H, [
        ('α 的作用是让 ξ̂ 不再跟着<b>本帧</b>的噪声实现抖。'
         '残差起伏从 %.1f dB 降到 %.1f dB，音乐噪声基本就没了。'
         % (a0['mus'], a98['mus']), None),
        ('但右图显示它做的不是"平滑"：固定 γ 时递归有<b>两个稳定不动点</b>，'
         'ξ̂ 要么锁到真值附近，要么塌到下限。', C2),
        ('α=0.98 的捕获阈值是 γ ≈ <b>%.2f dB</b>。低于它的频点，增益直接是 −25 dB，'
         '语音成分被整个抹掉；高于它，几乎无损。中间没有过渡带。'
         % cap['0.98']['thr_db'], None),
        ('这一条解释了三件一直被当成调参玄学的事：为什么它听着特别干净、'
         '为什么它吃掉气声和辅音尾巴、为什么 ξ 下限这个参数影响那么大。', T3),
    ], y0=328)
    return svg(W, H, o, '判决引导系数的取舍曲线，以及它在固定后验信噪比下的双稳态与捕获阈值')


# ══════════════════════════════════════════════════════════════
def fig_noise():
    W, H = 700, 458
    o = ['<text x="10" y="18" class="ct">噪声功率谱怎么估：'
         '<tspan font-weight="700">要在有语音的时候估噪声</tspan>'
         '<tspan class="cu"> · 而且噪声变大的时候，它看起来很像语音</tspan></text>']
    AX, AY, AW, AH = 62, 80, 610, 150
    st = DD['step']
    tr = st['traj']
    n = len(st['true_traj'])
    fx = lambda i: AX + i / (n - 1) * AW
    allv = sum([tr[k] for k in tr], []) + st['true_traj']
    lo, hi = np.percentile(allv, 2) - 2, np.percentile(allv, 98) + 3
    fy = lambda v: AY + (hi - min(max(v, lo), hi)) / (hi - lo) * AH
    o.append(f'<text x="{AX-48}" y="{AY-30}" class="blab">'
             f'噪声在中途突然大 {st["jump_db"]:.0f} dB，各估计器多久跟上</text>')
    ygrid(o, AX, AW, [round(v) for v in np.linspace(lo + 2, hi - 2, 4)], fy, '%g', ' dB')
    sm = np.convolve(st['true_traj'], np.ones(8) / 8, 'same')
    poly(o, [(fx(i), fy(v)) for i, v in enumerate(sm)], T3, 1.4, '3 3')
    for k, col, nm in (('ms', C1, '最小统计量 MS'), ('mcra', C2, 'MCRA'),
                       ('imcra', C3, 'IMCRA')):
        poly(o, [(fx(i), fy(v)) for i, v in enumerate(tr[k])], col, 2.0)
    o.append(f'<line x1="{fx(st["step_fr"]):.1f}" y1="{AY}" x2="{fx(st["step_fr"]):.1f}" '
             f'y2="{AY+AH}" stroke="{T2}" stroke-width="1.2" stroke-dasharray="5 3"/>')
    o.append(f'<text x="{fx(st["step_fr"])+5:.1f}" y="{AY+14}" class="ctick" fill="{T2}">'
             f'噪声在这里变大</text>')
    for i, (k, col, nm) in enumerate((('ms', C1, '最小统计量 MS'), ('mcra', C2, 'MCRA'),
                                      ('imcra', C3, 'IMCRA'))):
        o.append(f'<text x="{AX+8}" y="{AY+16+i*15}" class="ctick" fill="{col}">'
                 f'{nm}　{st[k+"_delay_ms"]:.0f} ms</text>')
    o.append(f'<text x="{AX+8}" y="{AY+16+3*15}" class="ctick" fill="{T3}">真值（平滑后）</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+20}" class="cax" text-anchor="middle">'
             f'帧（每帧 {DD["fr_ms"]:.0f} ms）</text>')
    # 表：各噪声下的估计代价
    CY = 268
    o.append(f'<text x="16" y="{CY}" class="blab">估计不准要花掉多少 dB（输入 5 dB）</text>')
    eb = DD['est_by_noise']
    cols = [('噪声', 'kind'), ('非平稳度', 'nonstat'), ('用真值', 'oracle'),
            ('IMCRA', 'imcra'), ('MS', 'ms'), ('估计的代价', 'cost')]
    for j, (lab, key) in enumerate(cols):
        x = 30 + j * 112
        o.append(f'<text x="{x}" y="{CY+20}" class="ctick" fill="{T2}">{lab}</text>')
        for i, r in enumerate(eb):
            v = r[key]
            s = v if isinstance(v, str) else ('%.2f' % v)
            c = C2 if (key == 'cost' and v > 1.0) else (T3 if j < 2 else 'var(--text)')
            o.append(f'<text x="{x}" y="{CY+38+i*17}" class="ctick" fill="{c}">{s}</text>')
    foot(o, H, [
        ('噪声突然变大时，MS 要 %.0f ms、MCRA 要 %.0f ms 才跟上。'
         '这段时间里增益按<b>旧的、偏小的</b>噪声算，噪声整个漏出来。'
         % (st['ms_delay_ms'], st['mcra_delay_ms']), None),
        ('MCRA 系慢，是因为它靠"功率比局部最小值高多少"判语音——'
         '<b>而噪声变大看起来正是这个样子</b>。这是原理性的，不是实现问题。', C2),
        ('平稳噪声上估计几乎不花钱（%.2f dB），非平稳噪声上要花 %.2f dB。'
         '真实场景的噪声全在后一栏。'
         % (min(r['cost'] for r in eb), max(r['cost'] for r in eb)), None),
    ], y0=404)
    return svg(W, H, o, '三种噪声功率谱估计器在噪声阶跃上升时的追踪轨迹，'
                        '以及不同噪声类型下估计误差的代价')


OUT['frame'] = fig_frame()
OUT['gain'] = fig_gain()
OUT['music'] = fig_music()
OUT['dd'] = fig_dd()
OUT['noise'] = fig_noise()
json.dump(OUT, open('figs_a.json', 'w'), ensure_ascii=False)
print('figs_a.json:', {k: len(v) // 1024 for k, v in OUT.items()})
