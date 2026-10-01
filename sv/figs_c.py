#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《声纹与唤醒手册》补图：误唤醒的泊松统计、前端增强、自定义唤醒词。"""
import json, math
import numpy as np

FA = json.load(open('demo_fa.json'))
FE = json.load(open('demo_fe.json'))
OP = json.load(open('demo_open.json'))

C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
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


def ygrid(o, X, W, vals, f2y, fmt='%g', suf='', col=None):
    for v in vals:
        y = f2y(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+W}" y2="{y:.1f}" class="grid"/>')
        s = (fmt % v).replace('-', '−')
        cc = f' fill="{col}"' if col else ''
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end"{cc}>'
                 f'{s}{suf}</text>')


def poly(o, pts, col, w=2.2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    o.append('<polyline points="' + ' '.join('%.1f,%.1f' % p for p in pts)
             + f'" fill="none" stroke="{col}" stroke-width="{w}"{d}/>')


def dots(o, pts, col, r=2.8):
    for x, y in pts:
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}"/>')


def legend(o, x, y, items, gap=96):
    for i, (col, nm) in enumerate(items):
        lx = x + i * gap
        o.append(f'<rect x="{lx}" y="{y-7}" width="12" height="3" rx="1.5" fill="{col}"/>')
        o.append(f'<text x="{lx+16}" y="{y}" class="ctick" fill="{col}">{nm}</text>')


# ══════════════════════════════════════════════════════════════
def fig_fa():
    """零事件的上界，以及要测准得跑多久。"""
    W, H = 700, 392
    o = ['<text x="10" y="18" class="ct">误唤醒是个泊松率：'
         '<tspan font-weight="700">"跑了一天没问题"几乎什么都没证明</tspan>'
         '<tspan class="cu"> · 精确区间，蒙特卡洛核对过覆盖率</tspan></text>']
    AX, AY, AW, AH = 70, 92, 254, 148
    zr = FA['zero']
    xs = [math.log10(r['hours']) for r in zr]
    fx = lambda v: AX + (v - xs[0]) / (xs[-1] - xs[0]) * AW
    lo, hi = math.log10(0.02), math.log10(120)
    fy = lambda v: AY + (hi - math.log10(max(v, 0.02))) / (hi - lo) * AH
    o.append(f'<text x="{AX-56}" y="{AY-38}" class="blab">① 一次都没观测到时，能给的上界</text>')
    o.append(f'<text x="{AX-56}" y="{AY-22}" class="bsub" fill="{T3}">'
             f'纵轴：95% 上界（次/天，对数轴）</text>')
    for v, s in ((100, '100'), (10, '10'), (1, '1'), (0.1, '0.1')):
        y = fy(v)
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{AX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{s}</text>')
    pts = [(fx(x), fy(r['hi_day'])) for x, r in zip(xs, zr)]
    poly(o, pts, C2)
    dots(o, pts, C2)
    for tgt, nm, col in ((0.5, '0.5 次/天', T3), (0.1, '0.1 次/天', C1)):
        y = fy(tgt)
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" '
                 f'stroke="{col}" stroke-width="1.3" stroke-dasharray="4 3"/>')
        o.append(f'<text x="{AX+AW-2}" y="{y-6:.1f}" class="ctick" fill="{col}" '
                 f'text-anchor="end">常见指标 {nm}</text>')
    z24 = [r for r in zr if r['hours'] == 24][0]
    o.append(f'<circle cx="{fx(math.log10(24)):.1f}" cy="{fy(z24["hi_day"]):.1f}" r="5.5" '
             f'fill="none" stroke="{C2}" stroke-width="2"/>')
    o.append(f'<text x="{fx(math.log10(24))+8:.1f}" y="{fy(z24["hi_day"])-8:.1f}" '
             f'class="ctick" fill="{C2}">跑 24 h → 只能说 ≤ {z24["hi_day"]:.1f}</text>')
    for r in zr:
        o.append(f'<text x="{fx(math.log10(r["hours"])):.1f}" y="{AY+AH+16}" '
                 f'class="ctick" text-anchor="middle">{r["hours"]}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'负样本时长（小时，对数轴）</text>')

    # ② 要跑多久
    BX, BY, BW, BH = 432, 92, 224, 148
    sp = FA['spec']
    me = {r['spec']: r for r in FA['measure']}
    o.append(f'<text x="{BX-16}" y="{AY-38}" class="blab">② 要跑多久</text>')
    legend(o, BX - 16, AY - 22, [(C1, '零事件地"证明达标"'),
                                 (C2, '把它"测准"（±38%）')], gap=118)
    mx = math.log10(max(me[r['spec']]['days'] for r in sp) * 1.4)
    mn = math.log10(3)
    hy = lambda v: BY + BH - (math.log10(max(v, 3)) - mn) / (mx - mn) * BH
    gw = BW / len(sp)
    for i, r in enumerate(sp):
        cx = BX + i * gw + gw / 2
        for k, (v, col) in enumerate(((r['days'], C1), (me[r['spec']]['days'], C2))):
            x = cx - 15 + k * 15
            o.append(f'<rect x="{x:.1f}" y="{hy(v):.1f}" width="13" '
                     f'height="{BY+BH-hy(v):.1f}" rx="1.5" fill="{col}" '
                     f'fill-opacity="0.9"/>')
        o.append(f'<text x="{cx:.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["per_day"]:g}</text>')
    for v, s in ((10, '10 天'), (100, '100'), (1000, '1000')):
        y = hy(v)
        o.append(f'<line x1="{BX}" y1="{y:.1f}" x2="{BX+BW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{BX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{s}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'目标误唤醒率（次/天，纵轴对数）</text>')
    sp01 = [r for r in sp if r['per_day'] == 0.1][0]
    cmp2 = [r for r in FA['compare'] if r['ratio'] == 2.0][0]
    foot(o, H, [
        ('跑 24 小时、一次没误唤醒，95%% 上界是 <b>%.1f 次/天</b>——'
         '而常见的指标是 0.1 次/天，差着 %.0f 倍。'
         % (z24['hi_day'], z24['hi_day'] / 0.1), None),
        ('要"零事件地"证明 0.1 次/天，得跑 <b>%.0f 天</b>的负样本；'
         '要把它测准（相对区间 ±%.0f%%，也就是观测到 %d 次），得跑 <b>%.0f 天</b>。'
         % (sp01['days'], FA['k_ok']['rel'] * 50, FA['k_ok']['k'],
            me['0.1 次/天']['days']), C2),
        ('想说"新版把 0.5 降到了 0.25"，两套各要跑 <b>%.0f 天</b>——'
         '大多数"我们优化了误唤醒"的结论，样本量根本不够。' % cmp2['days'], C1),
        ('而这一切的前提是素材固定：换一套负样本素材，同一个模型差 <b>%.0f 倍</b>。'
         % FA['corpus_spread'], T3),
    ], y0=300)
    return svg(W, H, o, '误唤醒率作为泊松率的置信上界，以及测准它所需的负样本时长')


# ══════════════════════════════════════════════════════════════
def fig_fe():
    """前端增强：感知指标和下游的最优点不是同一个。"""
    W, H = 700, 386
    o = ['<text x="10" y="18" class="ct">前端降噪对唤醒：'
         '<tspan font-weight="700">有用，但最该做的不是调它</tspan>'
         '<tspan class="cu"> · 固定误唤醒次数下的漏唤醒率</tspan></text>']
    AX, AY, AW, AH = 66, 90, 256, 150
    g = {}
    for r in FE['grid']:
        g.setdefault(r['snr'], []).append(r)
    alphas = sorted({r['alpha'] for r in FE['grid']})
    fx = lambda a: AX + a / max(alphas) * AW
    fy = lambda v: AY + (80 - v) / 80 * AH
    o.append(f'<text x="{AX-52}" y="{AY-38}" class="blab">① 漏唤醒 vs 过减量（失配）</text>')
    legend(o, AX - 52, AY - 22, [(C1, '0 dB'), (C2, '5 dB'), (C3, '10 dB')], gap=62)
    ygrid(o, AX, AW, [0, 20, 40, 60, 80], fy, '%g', '%')
    for snr, col in ((0, C1), (5, C2), (10, C3)):
        rows = sorted(g[snr], key=lambda r: r['alpha'])
        pts = [(fx(r['alpha']), fy(r['frr_mismatch'])) for r in rows]
        poly(o, pts, col, 2.0)
        dots(o, pts, col, 2.4)
        b = min(rows, key=lambda r: r['frr_mismatch'])
        o.append(f'<circle cx="{fx(b["alpha"]):.1f}" cy="{fy(b["frr_mismatch"]):.1f}" '
                 f'r="5" fill="none" stroke="{col}" stroke-width="1.8"/>')
    for a in alphas:
        o.append(f'<text x="{fx(a):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{a:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'谱减的过减量 α（0 = 不处理）</text>')

    # ② 失配 vs 匹配
    BX, BY, BW, BH = 430, 90, 226, 150
    o.append(f'<text x="{BX-16}" y="{AY-38}" class="blab">② 调 α vs 换数据重估模板</text>')
    legend(o, BX - 16, AY - 22, [(C2, '模板没见过增强（失配）'),
                                 (C3, '模板重估过（匹配）')], gap=136)
    hy = lambda v: BY + (60 - v) / 60 * BH
    ygrid(o, BX, BW, [0, 20, 40, 60], hy, '%g', '%')
    rows5 = sorted(g[5], key=lambda r: r['alpha'])
    gx = lambda a: BX + a / max(alphas) * BW
    for key, col in (('frr_mismatch', C2), ('frr_matched', C3)):
        pts = [(gx(r['alpha']), hy(r[key])) for r in rows5]
        poly(o, pts, col, 2.0)
        dots(o, pts, col, 2.4)
    b2 = [r for r in rows5 if r['alpha'] == 2.0][0]
    o.append(f'<line x1="{gx(2.0):.1f}" y1="{hy(b2["frr_matched"]):.1f}" '
             f'x2="{gx(2.0):.1f}" y2="{hy(b2["frr_mismatch"]):.1f}" '
             f'stroke="{T2}" stroke-width="1.4" stroke-dasharray="3 2"/>')
    o.append(f'<text x="{gx(2.0)+7:.1f}" y="{(hy(b2["frr_matched"])+hy(b2["frr_mismatch"]))/2:.1f}" '
             f'class="ctick" fill="{T2}">差 {FE["summary"]["matched_gain_5db"]:.1f} 倍</text>')
    for a in alphas:
        o.append(f'<text x="{gx(a):.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{a:g}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'过减量 α（SNR 5 dB）</text>')
    ag = {r['snr']: r for r in FE['summary']['alpha_gap']}
    foot(o, H, [
        ('<b>增强对唤醒是有用的</b>——这和增强手册 19 节相反，'
         '那边每一档增强都让说话人确认变差。机制不同：'
         '身份藏在谱的精细结构里，唤醒只要粗轨迹。', None),
        ('但<b>感知指标和下游的最优过减量不是同一个</b>：'
         '分段信噪比一直停在 α=1，而漏唤醒最优的 α 随信噪比往上走'
         '（5 dB→%.0f，10 dB→%.0f）。'
         % (ag[5]['best_frr'], ag[10]['best_frr']), C2),
        ('<b>而这两件事加起来都不如"用增强后的数据重估模板"值钱</b>：'
         '5 dB、α=2 时失配与匹配差 %.1f 倍，调 α 只带来 %.1f 倍。'
         % (FE['summary']['matched_gain_5db'], FE['summary']['help_mismatch_5db']), C3),
        ('训练与推理的信号链必须一致——这一条和增强手册那边是同一个结论。', T3),
    ], y0=294)
    return svg(W, H, o, '谱减过减量对唤醒漏检率的影响，以及模板失配与匹配的差距')


# ══════════════════════════════════════════════════════════════
def fig_open():
    """自定义唤醒词：注册条数、覆盖面、注册环境。"""
    W, H = 700, 392
    o = ['<text x="10" y="18" class="ct">自定义唤醒词：'
         '<tspan font-weight="700">问题不在精度，在只认注册的那个人</tspan>'
         '<tspan class="cu"> · 固定误唤醒次数下的漏唤醒率</tspan></text>']
    AX, AY, AW, AH = 66, 92, 240, 148
    en = OP['enroll']
    fx = lambda i: AX + i / (len(en) - 1) * AW
    mx = 48.0
    fy = lambda v: AY + (mx - v) / mx * AH
    o.append(f'<text x="{AX-52}" y="{AY-38}" class="blab">① 注册几条够</text>')
    ygrid(o, AX, AW, [0, 12, 24, 36, 48], fy, '%g', '%')
    pts = [(fx(i), fy(r['frr'])) for i, r in enumerate(en)]
    poly(o, pts, C1)
    dots(o, pts, C1)
    e5 = [r for r in en if r['n'] == 5][0]
    i5 = [i for i, r in enumerate(en) if r['n'] == 5][0]
    o.append(f'<circle cx="{fx(i5):.1f}" cy="{fy(e5["frr"]):.1f}" r="5.5" '
             f'fill="none" stroke="{C1}" stroke-width="2"/>')
    o.append(f'<text x="{fx(i5):.1f}" y="{fy(e5["frr"])+20:.1f}" class="ctick" '
             f'fill="{C1}" text-anchor="middle">5 条之后不再降</text>')
    for i, r in enumerate(en):
        o.append(f'<text x="{fx(i):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["n"]}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'注册条数</text>')

    # ② 谁在说话
    BX, BY, BW, BH = 416, 92, 240, 148
    vt = OP['vs_trained']
    cr = OP['cross']
    bars = [('自定义\n本人喊', e5['frr'], C1),
            ('专训\n本人喊', vt['trained'], C3),
            ('自定义\n别人喊', cr['other'], C2),
            ('专训\n别人喊', cr.get('trained_other', vt['trained']), C3)]
    o.append(f'<text x="{BX-16}" y="{AY-38}" class="blab">② 换个人喊，两条路线就反过来了</text>')
    hy = lambda v: BY + (76 - v) / 76 * BH
    ygrid(o, BX, BW, [0, 20, 40, 60], hy, '%g', '%')
    bw = BW / len(bars)
    for i, (nm, v, col) in enumerate(bars):
        cx = BX + i * bw + bw / 2
        o.append(f'<rect x="{cx-19:.1f}" y="{hy(v):.1f}" width="38" '
                 f'height="{BY+BH-hy(v):.1f}" rx="2" fill="{col}" fill-opacity="0.9"/>')
        o.append(f'<text x="{cx:.1f}" y="{hy(v)-6:.1f}" class="ctick" '
                 f'text-anchor="middle" fill="{col}">{v:.1f}%</text>')
        for k, ln in enumerate(nm.split('\n')):
            o.append(f'<text x="{cx:.1f}" y="{BY+BH+15+k*12}" class="ctick" '
                     f'text-anchor="middle">{ln}</text>')
    env = OP['enroll_env']
    foot(o, H, [
        ('注册曲线是断崖不是斜坡：1 条 %.1f%%，5 条 %.1f%%，10 条 %.1f%%——'
         '<b>3–5 条就够，再多没用</b>。前几条补的是这个人自己的发音变异。'
         % (en[0]['frr'], e5['frr'], en[-1]['frr']), None),
('"自定义一定比专训差"要看谁在说话：<b>本人喊 %.1f%% vs %.1f%%</b>，'
         '换个人喊 %.1f%% vs %.1f%%——差距不在平均精度，在覆盖面。'
         % (e5['frr'], vt['trained'], cr['other'],
            cr.get('trained_other', vt['trained'])), C2),
        ('注册环境的规律不是"越干净越好"：<b>在绝对安静里注册是最差的一档</b>'
         '（%.1f%%），带一点真实环境声就降到 %.1f%%。'
         % (env[0]['frr'], min(r['frr'] for r in env[1:])), C3),
        ('这里的"专训"只是 %d 个说话人的最近邻，没有判别训练也没有加噪增广，'
         '所以它偏悲观——结论的方向不变。' % vt['nspk_train'], T3),
    ], y0=300)
    return svg(W, H, o, '自定义唤醒词的注册条数曲线、跨说话人代价与注册环境的影响')


OUT['fa'] = fig_fa()
OUT['fe'] = fig_fe()
OUT['open'] = fig_open()
json.dump(OUT, open('figs_c.json', 'w'), ensure_ascii=False)
print('figs_c.json:', {k: len(v) // 1024 for k, v in OUT.items()})
