#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《声纹与唤醒手册》图 1–4：共同骨架、DET 与工作点、校准、打分与 margin。"""
import json, math
import numpy as np

SC = json.load(open('demo_score.json'))
MT = json.load(open('demo_metric.json'))
CD = json.load(open('demo_cond.json'))
MG = json.load(open('demo_margin.json'))
KW = json.load(open('demo_kws.json'))

C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
T3, T2 = 'var(--text-3)', 'var(--text-2)'
OUT = {}


def defs(u):
    return (f'<defs><marker id="{u}a" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--text-2)"/></marker>'
            f'<marker id="{u}s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" '
            f'fill="var(--s1)"/></marker></defs>')


def svg(w, h, o, label, cls='chart'):
    return (f'<svg viewBox="0 0 {w} {h}" class="{cls}" role="img" aria-label="{label}">'
            + ''.join(o) + '</svg>')


def grid(o, X, Y, W, H, vals, f2y, fmt='%g'):
    for v in vals:
        y = f2y(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+W}" y2="{y:.1f}" class="grid"/>')
        s = fmt % v
        if s.startswith('-'):
            s = '−' + s[1:]
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{s}</text>')


def foot(o, H, lines, y0=None, dy=18):
    y0 = y0 or (H - 18 - (len(lines) - 1) * dy)
    o.append(f'<line x1="14" y1="{y0-20}" x2="686" y2="{y0-20}" class="grid"/>')
    for i, (t, c) in enumerate(lines):
        t = t.replace('<b>', '<tspan font-weight="600">').replace('</b>', '</tspan>')
        cc = f' fill="{c}"' if c else ''
        o.append(f'<text x="14" y="{y0+i*dy}" class="arlab"{cc}>{t}</text>')


# ══════════════════════════════════════════════════════════════
def fig_arch():
    W, H = 700, 368
    o = [defs('ar'),
         '<text x="10" y="18" class="ct">声纹与唤醒：'
         '<tspan font-weight="700">同一根骨架，两个极端的工作点</tspan>'
         '<tspan class="cu"> · 差别不在方法，在"一天要做多少次判决"</tspan></text>']
    rows = [('声纹确认', ['特征', '编码器', '一个向量', '打分', '阈值'], C1,
             '几次/天', '每次都有人在等结果'),
            ('唤醒', ['特征', '小模型', '一个分数', '平滑', '阈值'], C2,
             '288 万次/天', '绝大多数时候不该响')]
    for r, (name, boxes, col, rate, note) in enumerate(rows):
        y = 58 + r * 78
        o.append(f'<text x="14" y="{y+22}" class="blab">{name}</text>')
        o.append(f'<text x="14" y="{y+37}" class="bsub" fill="{col}">{rate}</text>')
        x0, bw, gap = 90, 96, 12
        for i, b in enumerate(boxes):
            x = x0 + i * (bw + gap)
            cls = 'bx-a' if i in (1, 4) else 'bx'
            o.append(f'<rect x="{x}" y="{y}" width="{bw}" height="38" rx="4" class="{cls}"/>')
            o.append(f'<text x="{x+bw/2}" y="{y+23}" class="blab" '
                     f'text-anchor="middle">{b}</text>')
            if i < len(boxes) - 1:
                o.append(f'<line x1="{x+bw}" y1="{y+19}" x2="{x+bw+gap-2}" y2="{y+19}" '
                         f'class="ar" marker-end="url(#ara)"/>')
        o.append(f'<text x="{x0+5*(bw+gap)-6}" y="{y+23}" class="bsub" fill="{col}">{note}</text>')
    o.append(f'<line x1="90" y1="216" x2="640" y2="216" class="grid"/>')
    o.append('<text x="90" y="236" class="blab">两个极端带来的三处不同</text>')
    items = [('判决次数', '几次 vs 288 万次/天', '→ 同样的"错误率"差六个数量级'),
             ('先验', 'P(是本人) 约 0.5', '→ 唤醒的先验是 10⁻⁶ 量级'),
             ('算力', '可以调用云端', '→ 必须常开、必须毫瓦级')]
    for i, (a, b, c) in enumerate(items):
        y = 252 + i * 18
        o.append(f'<text x="90" y="{y}" class="bsub" fill="{T2}">{a}</text>')
        o.append(f'<text x="168" y="{y}" class="bsub">{b}</text>')
        o.append(f'<text x="330" y="{y}" class="bsub" fill="{T3}">{c}</text>')
    foot(o, H, [('两件事的数学是同一个：<b>二元假设检验</b>，一个分数配一个阈值。', None),
                ('但工作点差了六个数量级，于是<b>所有的工程结论都不一样</b>——'
                 '从指标怎么报到模型能有多大。', None)], y0=330)
    return svg(W, H, o, '声纹确认和唤醒共享同一条流水线，但判决次数、先验和算力预算'
                        '差了几个数量级', 'chart diag')


# ══════════════════════════════════════════════════════════════
def fig_det():
    W, H = 700, 400
    o = ['<text x="10" y="18" class="ct">分数分布、DET 曲线，'
         '<tspan font-weight="700">以及 EER 那个点为什么没人用</tspan>'
         '<tspan class="cu"> · %d 个目标对 / %d 个冒充对，PLDA 对数似然比</tspan></text>'
         % (MT['base']['n_tar'], MT['base']['n_non'])]
    # ① 分数直方图
    AX, AY, AW, AH = 52, 78, 276, 156
    h = MT['hist']
    nb = len(h['tar'])
    lo, hi = h['lo'], h['hi']
    mx = max(max(h['tar']) / sum(h['tar']), max(h['non']) / sum(h['non']))
    fx = lambda v: AX + (v - lo) / (hi - lo) * AW
    fy = lambda p: AY + (1 - p / mx) * AH
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 两类分数长什么样</text>')
    o.append(f'<text x="{AX}" y="{AY-15}" class="bsub" fill="{T3}">'
             f'横轴：对数似然比；纵轴：占比</text>')
    for arr, col, nm in ((h['non'], C2, '冒充'), (h['tar'], C1, '目标')):
        s = sum(arr)
        pts = [(fx(lo + (i + .5) * (hi - lo) / nb), fy(v / s)) for i, v in enumerate(arr)]
        o.append('<polyline points="' + ' '.join('%.1f,%.1f' % p for p in pts)
                 + f'" fill="none" stroke="{col}" stroke-width="1.8"/>')
    o.append(f'<text x="{fx(-22):.1f}" y="{AY+14}" class="bsub" fill="{C2}">冒充</text>')
    o.append(f'<text x="{fx(26):.1f}" y="{AY+14}" class="bsub" fill="{C1}">目标</text>')
    ops = {r['p']: r for r in MT['ops']}
    for p, col, tag, side in ((0.5, T3, 'EER 阈值', 'end'),
                              (0.001, C3, 'P=0.001 的最优阈值', 'start')):
        t = ops[p]['thr']
        o.append(f'<line x1="{fx(t):.1f}" y1="{AY}" x2="{fx(t):.1f}" y2="{AY+AH}" '
                 f'stroke="{col}" stroke-width="1.4" stroke-dasharray="4 3"/>')
        dx = -5 if side == 'end' else 5
        dy = -22 if side == 'end' else -6
        o.append(f'<text x="{fx(t)+dx:.1f}" y="{AY+AH+dy:.1f}" class="bsub" fill="{col}" '
                 f'text-anchor="{side}">{tag}</text>')
    for v in (-40, -20, 0, 20, 40, 60):
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{"−" if v<0 else ""}{abs(v)}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'分数（对数似然比）</text>')

    # ② DET
    BX, BY, BW, BH = 400, 78, 270, 156
    from math import erf, sqrt

    def probit(p):
        p = min(max(p, 1e-6), 1 - 1e-6)
        # 反正态：用二分求 Φ(x)=p
        lo_, hi_ = -6.0, 6.0
        for _ in range(60):
            m = (lo_ + hi_) / 2
            if 0.5 * (1 + erf(m / sqrt(2))) < p:
                lo_ = m
            else:
                hi_ = m
        return (lo_ + hi_) / 2

    R = [-4.0, 1.5]
    gx = lambda p: BX + (probit(p) - R[0]) / (R[1] - R[0]) * BW
    gy = lambda p: BY + (R[1] - probit(p)) / (R[1] - R[0]) * BH
    o.append(f'<text x="{BX}" y="{BY-30}" class="blab">② DET 曲线（正态概率纸）</text>')
    o.append(f'<text x="{BX}" y="{BY-15}" class="bsub" fill="{T3}">'
             f'两轴都是概率刻度，好系统在左下角</text>')
    TK = [0.0001, 0.001, 0.01, 0.1, 0.5]
    LB = ['0.01%', '0.1%', '1%', '10%', '50%']
    for v, lab in zip(TK, LB):
        o.append(f'<line x1="{BX}" y1="{gy(v):.1f}" x2="{BX+BW}" y2="{gy(v):.1f}" class="grid"/>')
        o.append(f'<text x="{BX-5}" y="{gy(v)+3.5:.1f}" class="ctick" '
                 f'text-anchor="end">{lab}</text>')
        o.append(f'<line x1="{gx(v):.1f}" y1="{BY}" x2="{gx(v):.1f}" y2="{BY+BH}" class="grid"/>')
        o.append(f'<text x="{gx(v):.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{lab}</text>')
    pts = [(gx(f), gy(m)) for m, f in zip(MT['det']['miss'], MT['det']['fa'])
           if 1e-5 < m < .9 and 1e-5 < f < .9]
    o.append('<polyline points="' + ' '.join('%.1f,%.1f' % p for p in pts)
             + f'" fill="none" stroke="{C1}" stroke-width="2.2"/>')
    o.append(f'<line x1="{gx(0.0001):.1f}" y1="{gy(0.0001):.1f}" x2="{gx(0.5):.1f}" '
             f'y2="{gy(0.5):.1f}" stroke="{T3}" stroke-width="1" stroke-dasharray="3 3"/>')
    e = MT['base']['eer'] / 100
    o.append(f'<circle cx="{gx(e):.1f}" cy="{gy(e):.1f}" r="4" fill="{C3}"/>')
    o.append(f'<text x="{gx(e)+7:.1f}" y="{gy(e)+4:.1f}" class="bsub" fill="{C3}">'
             f'EER {MT["base"]["eer"]:.2f}%</text>')
    for p, col in ((0.01, C2), (0.001, C2)):
        r = ops[p]
        o.append(f'<circle cx="{gx(r["pfa"]/100):.1f}" cy="{gy(r["pmiss"]/100):.1f}" '
                 f'r="3.4" fill="{col}"/>')
        o.append(f'<text x="{gx(r["pfa"]/100)+6:.1f}" y="{gy(r["pmiss"]/100)+4:.1f}" '
                 f'class="bsub" fill="{col}">P={p}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'虚警率 Pfa</text>')
    foot(o, H, [
        ('<b>EER 是一个"两类代价相等、先验各半"的点</b>——现实中几乎没有应用长这样。',
         None),
        ('手机解锁的冒充试验远多于本人试验；门禁的漏检代价远小于误放。'
         '这两件事都会把最优阈值推离 EER。', None),
        ('实测：EER 的阈值是 %.2f，而 P_target=0.001 的最优阈值是 %.2f，'
         '<b>差 %.1f 个自然对数单位</b>。'
         % (ops[0.5]['thr'], ops[0.001]['thr'],
            abs(ops[0.001]['thr'] - ops[0.5]['thr'])), C2),
        ('报 EER 没错，但<b>只报 EER 等于报了一个没人用的工作点</b>。'
         '该报的是你那个应用的 P_target 下的 DCF。', T3),
    ], y0=300)
    return svg(W, H, o, '左边是目标与冒充的分数分布及两个不同工作点的阈值，'
                        '右边是 DET 曲线上 EER 点与实际工作点的距离')


# ══════════════════════════════════════════════════════════════
def fig_calib():
    W, H = 700, 356
    o = ['<text x="10" y="18" class="ct">'
         '<tspan font-weight="700">minDCF 好看，不代表上线能用</tspan>'
         '<tspan class="cu"> · 同一套分数只做单调变换，排序一点没变</tspan></text>']
    AX, AY, AW, AH = 190, 74, 344, 172
    rows = MT['calib']
    mx = 1.05
    fx = lambda v: AX + v / mx * AW
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">'
             f'左：minDCF（可以随便挑阈值）　右：actDCF（只能用一个固定阈值）</text>')
    o.append(f'<text x="{AX}" y="{AY-15}" class="bsub" fill="{T3}">'
             f'P_target = 0.01；1.0 表示"和什么都不做一样差"</text>')
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        o.append(f'<line x1="{fx(v):.1f}" y1="{AY}" x2="{fx(v):.1f}" y2="{AY+AH}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v:g}</text>')
    o.append(f'<line x1="{fx(1.0):.1f}" y1="{AY}" x2="{fx(1.0):.1f}" y2="{AY+AH}" '
             f'stroke="{C2}" stroke-width="1.2" stroke-dasharray="4 3"/>')
    for i, r in enumerate(rows):
        y = AY + 16 + i * 32
        o.append(f'<text x="{AX-8}" y="{y+4}" class="bsub" text-anchor="end">{r["tag"]}</text>')
        o.append(f'<rect x="{fx(0):.1f}" y="{y-8:.1f}" width="{fx(r["mindcf"])-fx(0):.1f}" '
                 f'height="7" rx="2" fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<rect x="{fx(0):.1f}" y="{y+1:.1f}" width="{fx(r["actdcf"])-fx(0):.1f}" '
                 f'height="7" rx="2" fill="{C2}" fill-opacity="0.9"/>')
        o.append(f'<text x="{AX+AW+14:.1f}" y="{y+4:.1f}" '
                 f'class="bsub" fill="{C2}" font-weight="600">{r["actdcf"]:.3f}</text>')
    o.append(f'<line x1="{AX+AW-116}" y1="{AY+6}" x2="{AX+AW-98}" y2="{AY+6}" '
             f'stroke="{C1}" stroke-width="3"/>')
    o.append(f'<text x="{AX+AW-94}" y="{AY+10}" class="bsub" fill="{C1}">minDCF</text>')
    o.append(f'<line x1="{AX+AW-116}" y1="{AY+22}" x2="{AX+AW-98}" y2="{AY+22}" '
             f'stroke="{C2}" stroke-width="3"/>')
    o.append(f'<text x="{AX+AW-94}" y="{AY+26}" class="bsub" fill="{C2}">actDCF</text>')
    r0, worst = rows[0], max(rows, key=lambda r: r['actdcf'])
    foot(o, H, [
        ('五行的 <b>EER 和 minDCF 完全相同</b>（%.2f%% / %.4f）——单调变换不改变排序。'
         % (r0['eer'], r0['mindcf']), None),
        ('而 actDCF 从 %.4f 一路涨到 %.4f，<b>差 %.1f 倍</b>；'
         '"%s"那一行已经和什么都不做一样差了。'
         % (r0['actdcf'], worst['actdcf'], worst['actdcf'] / r0['actdcf'],
            worst['tag']), C2),
        ('上线时你只能用一个固定阈值，所以真正决定体验的是 actDCF。'
         '<b>判别力和校准是两件事，论文常常只报前者。</b>', None),
        ('Cllr 这个指标把两者合在一起：%.3f → %.3f。'
         '它衡量的是"分数当成对数似然比用有多靠谱"。'
         % (r0['cllr'], worst['cllr']), T3),
    ], y0=282)
    return svg(W, H, o, '同一套分数经过五种单调变换，最小检测代价完全不变，'
                        '而按固定阈值算的实际代价最多差四倍多')


# ══════════════════════════════════════════════════════════════
def fig_score():
    W, H = 700, 434
    o = ['<text x="10" y="18" class="ct">打分：'
         '<tspan font-weight="700">白化买走大头，PLDA 再补一刀</tspan>'
         '<tspan class="cu"> · 32 维嵌入，测试说话人训练时没见过</tspan></text>']
    AX, AY, AW, AH = 214, 72, 300, 152
    ms = SC['methods']
    mx = max(m['eer'] for m in ms) * 1.12
    fx = lambda v: AX + v / mx * AW
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 五种打分的 EER</text>')
    for v in (0, 5, 10, 15):
        o.append(f'<line x1="{fx(v):.1f}" y1="{AY}" x2="{fx(v):.1f}" y2="{AY+AH}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v}%</text>')
    for i, m in enumerate(ms):
        y = AY + 14 + i * 24
        c = C3 if 'PLDA' in m['tag'] else (C2 if m['eer'] > 10 else C1)
        o.append(f'<text x="{AX-8}" y="{y+4}" class="bsub" text-anchor="end">{m["tag"]}</text>')
        o.append(f'<rect x="{fx(0):.1f}" y="{y-6:.1f}" width="{max(fx(m["eer"])-fx(0),2):.1f}" '
                 f'height="12" rx="2" fill="{c}" fill-opacity="0.88"/>')
        o.append(f'<text x="{fx(m["eer"])+6:.1f}" y="{y+4:.1f}" class="bsub" fill="{c}" '
                 f'font-weight="600">{m["eer"]:.2f}%</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'等错误率 EER</text>')

    # ② 各向异性扫描
    CX, CY, CW, CH = 62, 268, 250, 0
    an = SC['aniso']
    BX, BY, BW, BH = 400, 274, 270, 0
    o.append(f'<text x="52" y="292" class="blab">'
             f'② PLDA 比余弦好多少，取决于类内协方差有多各向异性</text>')
    yy = 312
    o.append(f'<text x="52" y="{yy}" class="bsub" fill="{T3}">类内特征值动态</text>')
    for i, r in enumerate(an):
        x = 186 + i * 82
        o.append(f'<text x="{x}" y="{yy}" class="bsub" text-anchor="middle">'
                 f'{r["aniso"]:g}:1</text>')
        o.append(f'<text x="{x}" y="{yy+17}" class="bsub" fill="{C1}" '
                 f'text-anchor="middle">{r["cos"]:.2f}%</text>')
        o.append(f'<text x="{x}" y="{yy+33}" class="bsub" fill="{C3}" '
                 f'text-anchor="middle">{r["plda"]:.2f}%</text>')
        o.append(f'<text x="{x}" y="{yy+50}" class="bsub" fill="{C2}" '
                 f'text-anchor="middle" font-weight="600">{r["ratio"]:.1f}×</text>')
    o.append(f'<text x="52" y="{yy+17}" class="bsub" fill="{C1}">余弦 EER</text>')
    o.append(f'<text x="52" y="{yy+33}" class="bsub" fill="{C3}">PLDA EER</text>')
    o.append(f'<text x="52" y="{yy+50}" class="bsub" fill="{C2}">倍数</text>')
    foot(o, H, [
        ('原始余弦 %.2f%% → 只做<b>类内白化</b> %.2f%% → PLDA %.2f%%：'
         '白化买走大头，PLDA 再补一刀。'
         % (ms[0]['eer'], ms[2]['eer'], ms[-1]['eer']), None),
        ('长度归一化对余弦<b>一点影响都没有</b>（前两行一模一样）——余弦本来就只看方向。'
         '它有用是因为它在 <b>PLDA/LDA 之前</b>做高斯化，不是因为它自己。', C2),
    ], y0=398, dy=18)
    return svg(W, H, o, '五种打分方式的等错误率对比，以及余弦与 PLDA 的差距'
                        '如何随类内协方差的各向异性变化')


# ══════════════════════════════════════════════════════════════
def fig_margin():
    W, H = 700, 400
    o = ['<text x="10" y="18" class="ct">margin 到底在干什么：'
         '<tspan font-weight="700">一个我猜错了归因的实验</tspan>'
         '<tspan class="cu"> · 真训一个小网络，在没见过的说话人上测</tspan></text>']
    AX, AY, AW, AH = 214, 74, 196, 132
    L = MG['losses']
    mx = max(r['eer'] for r in L) * 1.15
    fx = lambda v: AX + v / mx * AW
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 四种分类头</text>')
    for v in (0, 1, 2, 3, 4):
        o.append(f'<line x1="{fx(v):.1f}" y1="{AY}" x2="{fx(v):.1f}" y2="{AY+AH}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v}%</text>')
    for i, r in enumerate(L):
        y = AY + 16 + i * 30
        o.append(f'<text x="{AX-8}" y="{y+4}" class="bsub" text-anchor="end">{r["tag"]}</text>')
        o.append(f'<rect x="{fx(0):.1f}" y="{y-8:.1f}" width="{fx(r["eer"])-fx(0):.1f}" '
                 f'height="7" rx="2" fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<rect x="{fx(0):.1f}" y="{y+1:.1f}" width="{fx(r["plda"])-fx(0):.1f}" '
                 f'height="7" rx="2" fill="{C3}" fill-opacity="0.9"/>')
        o.append(f'<text x="{AX+AW+14:.1f}" y="{y+4:.1f}" '
                 f'class="bsub" fill="{C2}" font-weight="600">{r["gap"]:.2f}×</text>')
    LY = AY + AH + 34
    o.append(f'<line x1="{AX+2}" y1="{LY-4}" x2="{AX+20}" y2="{LY-4}" stroke="{C1}" '
             f'stroke-width="3"/><text x="{AX+24}" y="{LY}" class="bsub" fill="{C1}">'
             f'余弦打分</text>')
    o.append(f'<line x1="{AX+92}" y1="{LY-4}" x2="{AX+110}" y2="{LY-4}" stroke="{C3}" '
             f'stroke-width="3"/><text x="{AX+114}" y="{LY}" class="bsub" fill="{C3}">'
             f'PLDA 打分</text>')
    o.append(f'<text x="{AX+AW+14}" y="{AY+2}" class="bsub" fill="{C2}">余弦/PLDA</text>')

    # ② margin 扫描
    BX, BY, BW, BH = 520, 74, 150, 132
    sw = MG['msweep']
    lo, hi = 2.0, 2.95
    gy = lambda v: BY + (hi - v) / (hi - lo) * BH
    gx = lambda i: BX + i / (len(sw) - 1) * BW
    o.append(f'<text x="{BX}" y="{AY-30}" class="blab">② margin 取多大</text>')
    grid(o, BX, BY, BW, BH, [2.0, 2.4, 2.8], gy, '%.1f')
    pts = ' '.join('%.1f,%.1f' % (gx(i), gy(r['eer'])) for i, r in enumerate(sw))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{C1}" stroke-width="2.2"/>')
    bi = int(np.argmin([r['eer'] for r in sw]))
    for i, r in enumerate(sw):
        o.append(f'<circle cx="{gx(i):.1f}" cy="{gy(r["eer"]):.1f}" '
                 f'r="{4 if i==bi else 2.6}" fill="{C3 if i==bi else C1}"/>')
        if i % 2 == 0 or i == bi:
            o.append(f'<text x="{gx(i):.1f}" y="{BY+BH+16}" class="ctick" '
                     f'text-anchor="middle">{r["m"]:g}</text>')
    o.append(f'<text x="{gx(bi):.1f}" y="{gy(sw[bi]["eer"])-9:.1f}" class="bsub" '
             f'fill="{C3}" text-anchor="middle">{sw[bi]["eer"]:.2f}%</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'margin m</text>')
    lin, pl, aam = L[0], L[1], L[3]
    foot(o, H, [
        ('我原本的假说：<b>margin 让嵌入更各向同性，所以余弦追上了 PLDA</b>。'
         '实测把它否掉了——', None),
        ('加不加 margin，余弦/PLDA 都在 1.1 附近（%.2f → %.2f）。'
         % (pl['gap'], aam['gap']), C2),
        ('对照行给出了真答案：换成<b>普通线性分类头</b>，比值立刻涨到 %.2f，'
         '类内各向异性从 %.2f 涨到 %.2f。'
         % (lin['gap'], pl['aniso'], lin['aniso']), None),
        ('<b>是"余弦分类头"关上了这个差距，不是 margin</b>——'
         '训练目标本身就是余弦打分器，PLDA 没剩多少可补。', None),
        ('margin 的功劳是另一件：余弦 EER 从 %.2f%% 降到 %.2f%%，'
         '而且 m 有明显最优点（%.1f）。' % (pl['eer'], aam['eer'], sw[bi]['m']), T3),
    ], y0=280)
    return svg(W, H, o, '四种分类头的余弦与 PLDA 等错误率对比显示是余弦分类头而不是 margin '
                        '关上了两者的差距，以及 margin 取值的最优点')


OUT['arch'] = fig_arch()
OUT['det'] = fig_det()
OUT['calib'] = fig_calib()
OUT['score'] = fig_score()
OUT['margin'] = fig_margin()
json.dump(OUT, open('figs_a.json', 'w'), ensure_ascii=False)
print('figs_a.json:', {k: len(v) // 1024 for k, v in OUT.items()})
