#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《声纹与唤醒手册》图 5–8：失配条件、统计功效、唤醒的工作点、级联与功耗。"""
import json, math
import numpy as np

MT = json.load(open('demo_metric.json'))
CD = json.load(open('demo_cond.json'))
KW = json.load(open('demo_kws.json'))

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


def ygrid(o, X, W, vals, f2y, fmt='%g', suf=''):
    for v in vals:
        y = f2y(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+W}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">'
                 f'{fmt % v}{suf}</text>')


def poly(o, pts, col, w=2.2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    o.append('<polyline points="' + ' '.join('%.1f,%.1f' % p for p in pts)
             + f'" fill="none" stroke="{col}" stroke-width="{w}"{d}/>')


# ══════════════════════════════════════════════════════════════
def fig_cond():
    W, H = 700, 506
    o = ['<text x="10" y="18" class="ct">'
         '<tspan font-weight="700">决定声纹能不能落地的，不是模型，是这四件事</tspan>'
         '<tspan class="cu"> · 同一套嵌入，只改条件</tspan></text>']
    # ① 时长
    AX, AY, AW, AH = 58, 72, 250, 130
    D = CD['dur']
    lo, hi = math.log10(0.05), math.log10(20)
    fy = lambda v: AY + (hi - math.log10(max(v, 0.05))) / (hi - lo) * AH
    fx = lambda T: AX + (math.log10(T) - math.log10(1.0)) / (math.log10(30) - 0) * AW
    o.append(f'<text x="{AX-42}" y="{AY-30}" class="blab">① 测试语音时长</text>')
    ygrid(o, AX, AW, [0.1, 1, 10], fy, '%g', '%')
    for key, col, nm in (('cos', C1, '余弦'), ('plda', C3, 'PLDA')):
        poly(o, [(fx(r['T']), fy(r[key])) for r in D], col)
        for r in D:
            o.append(f'<circle cx="{fx(r["T"]):.1f}" cy="{fy(r[key]):.1f}" r="2.6" fill="{col}"/>')
        r = D[-1]
        o.append(f'<text x="{fx(r["T"])+6:.1f}" y="{fy(r[key])+4:.1f}" class="bsub" '
                 f'fill="{col}">{nm}</text>')
    for r in D:
        o.append(f'<text x="{fx(r["T"]):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["T"]:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'测试语音时长（秒，对数轴）</text>')
    d1 = next(r for r in D if r['T'] == 1.0)
    d10 = next(r for r in D if r['T'] == 10.0)
    o.append(f'<text x="{AX+6}" y="{AY+14}" class="bsub" fill="{C2}" font-weight="600">'
             f'1 秒 : 10 秒 = {CD["dur_ratio"]:.0f}×</text>')

    # ② 注册条数
    BX, BY, BW, BH = 430, 72, 200, 130
    E = CD['enroll']
    mx = max(r['cos'] for r in E) * 1.15
    gy = lambda v: BY + (1 - v / mx) * BH
    o.append(f'<text x="{BX-36}" y="{BY-30}" class="blab">② 注册用几条</text>')
    ygrid(o, BX, BW, [0, 2, 4], gy, '%g', '%')
    bw = BW / len(E) - 10
    for i, r in enumerate(E):
        x = BX + i * (BW / len(E)) + 5
        o.append(f'<rect x="{x:.1f}" y="{gy(r["cos"]):.1f}" width="{bw:.1f}" '
                 f'height="{BY+BH-gy(r["cos"]):.1f}" rx="2" fill="{C1}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+bw/2:.1f}" y="{gy(r["cos"])-5:.1f}" class="ctick" '
                 f'text-anchor="middle" fill="{C1}">{r["cos"]:.2f}</text>')
        o.append(f'<text x="{x+bw/2:.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{r["n"]}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'注册条数（余弦 EER）</text>')

    # ③ 信道失配
    CY = 268
    o.append(f'<text x="16" y="{CY}" class="blab">'
             f'③ 注册和测试来自不同信道：一个常数偏移就能毁掉系统，而减掉各域均值几乎全救得回来</text>')
    DM = CD['domain']
    DX, DW = 150, 380
    mxd = max(r['eer'] for r in DM) * 1.08
    hx = lambda v: DX + v / mxd * DW
    for i, r in enumerate(DM):
        y = CY + 22 + i * 26
        o.append(f'<text x="{DX-8}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'偏移 {r["shift"]:.1f}·√tr(W)</text>')
        o.append(f'<rect x="{DX}" y="{y-7:.1f}" width="{max(hx(r["eer"])-DX,2):.1f}" '
                 f'height="7" rx="2" fill="{C2}" fill-opacity="0.9"/>')
        o.append(f'<rect x="{DX}" y="{y+2:.1f}" width="{max(hx(r["eer_cmn"])-DX,2):.1f}" '
                 f'height="7" rx="2" fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<text x="{hx(max(r["eer"],r["eer_cmn"]))+8:.1f}" y="{y+4:.1f}" '
                 f'class="bsub" fill="{C2}">{r["eer"]:.2f}% → '
                 f'<tspan fill="{C1}">{r["eer_cmn"]:.2f}%</tspan></text>')
    AS = CD['asnorm']
    foot(o, H, [
        ('时长是<b>头号问题</b>：1 秒的 EER 是 10 秒的 %.0f 倍。它不是模型不行——'
         '那几百帧统计量本身就不够。' % CD['dur_ratio'], None),
        ('注册端是<b>免费的那一侧</b>：1→5 条把余弦 EER 从 %.2f%% 降到 %.2f%%（降 %.0f%%），'
         '用户只注册一次。'
         % (E[0]['cos'], E[3]['cos'], (1 - E[3]['cos'] / E[0]['cos']) * 100), None),
        ('AS-norm 修的是"有的人天生容易被冒充"：各人的冒充分均值标准差 %.4f，'
         '范围 [%.3f, %.3f]，归一化后 %.2f%% → %.2f%%。'
         % (AS['bias_sd'], AS['bias_lo'], AS['bias_hi'], AS['eer_raw'], AS['eer_as']), None),
        ('<b>先把条件摆平，再谈换模型</b>——这四件事里随便一件的收益都大过换个骨干网络。', C2),
    ], y0=434)
    return svg(W, H, o, '时长、注册条数、分数归一化和信道失配四种条件各自对等错误率的影响')


# ══════════════════════════════════════════════════════════════
def fig_power():
    W, H = 700, 404
    o = ['<text x="10" y="18" class="ct">'
         '<tspan font-weight="700">榜单上相邻两名的差距，多半没有统计意义</tspan>'
         '<tspan class="cu"> · 自助法置信区间 + 功效分析</tspan></text>']
    AX, AY, AW, AH = 64, 76, 296, 140
    CI = MT['ci']
    lo, hi = math.log10(400), math.log10(20000)
    fx = lambda n: AX + (math.log10(n) - lo) / (hi - lo) * AW
    ymax = 2.2
    fy = lambda v: AY + (1 - v / ymax) * AH
    o.append(f'<text x="{AX-48}" y="{AY-30}" class="blab">① EER 的 95% 置信区间有多宽</text>')
    ygrid(o, AX, AW, [0, 0.5, 1.0, 1.5, 2.0], fy, '%.1f', '%')
    o.append(f'<line x1="{AX}" y1="{fy(MT["base"]["eer"]):.1f}" x2="{AX+AW}" '
             f'y2="{fy(MT["base"]["eer"]):.1f}" stroke="{T3}" stroke-width="1" '
             f'stroke-dasharray="3 3"/>')
    for r in CI:
        x = fx(r['n_tar'])
        o.append(f'<line x1="{x:.1f}" y1="{fy(r["lo"]):.1f}" x2="{x:.1f}" '
                 f'y2="{fy(r["hi"]):.1f}" stroke="{C1}" stroke-width="2.4"/>')
        for v in (r['lo'], r['hi']):
            o.append(f'<line x1="{x-5:.1f}" y1="{fy(v):.1f}" x2="{x+5:.1f}" '
                     f'y2="{fy(v):.1f}" stroke="{C1}" stroke-width="2"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{fy(r["eer"]):.1f}" r="3" fill="{C3}"/>')
        o.append(f'<text x="{x:.1f}" y="{fy(r["hi"])-8:.1f}" class="ctick" '
                 f'text-anchor="middle" fill="{C2}">±{r["width"]/2:.2f}</text>')
        o.append(f'<text x="{x:.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["n_tar"]:,}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'目标对数量（对数轴）</text>')

    # ② 功效
    BX, BY = 424, 76
    P = MT['power']
    o.append(f'<text x="{BX-20}" y="{BY-30}" class="blab">② 两套系统差多少才算真的不同</text>')
    o.append(f'<text x="{BX-20}" y="{BY-14}" class="bsub" fill="{T3}">'
             f'同一批试验，80% 功效，双侧 5%</text>')
    o.append(f'<text x="{BX-20}" y="{BY+14}" class="bsub" fill="{T2}">两套系统的 EER</text>')
    o.append(f'<text x="{BX+180}" y="{BY+14}" class="bsub" fill="{T2}" '
             f'text-anchor="end">需要多少目标对</text>')
    for i, r in enumerate(P):
        y = BY + 38 + i * 24
        o.append(f'<text x="{BX-20}" y="{y}" class="bsub">'
                 f'{r["e1"]*100:.1f}% vs {r["e2"]*100:.1f}%</text>')
        n = r['n_tar']
        c = C2 if n >= 20000 else T2
        o.append(f'<text x="{BX+180}" y="{y}" class="bsub" fill="{c}" '
                 f'text-anchor="end" font-weight="600">{n:,}</text>')
    o.append(f'<line x1="{BX-20}" y1="{BY+142}" x2="{BX+180}" y2="{BY+142}" class="grid"/>')
    o.append(f'<text x="{BX-20}" y="{BY+162}" class="bsub" fill="{T3}">'
             f'"三十法则"：要估 p 的错误率，至少要看到 ~30 个错误</text>')
    R = MT['rule30']
    for i, r in enumerate(R[:4]):
        x = BX - 20 + i * 52
        o.append(f'<text x="{x}" y="{BY+180}" class="ctick" fill="{T3}">'
                 f'{r["rate"]*100:g}%</text>')
        o.append(f'<text x="{x}" y="{BY+196}" class="ctick" fill="{C1}">{r["n"]:,}</text>')
    foot(o, H, [
        ('%d 个目标对时，EER 的 95%% 区间还有 ±%.2f 个百分点；缩到 %d 个，宽度变成 ±%.2f。'
         % (CI[0]['n_tar'], CI[0]['width'] / 2, CI[-1]['n_tar'], CI[-1]['width'] / 2), None),
        ('<b>2.0%% 和 2.2%% 的差别要 %s 个目标对才分得开</b>，而常见评测集只有几千对。'
         % f'{P[0]["n_tar"]:,}', C2),
        ('所以看到"我们把 EER 从 2.31% 降到 2.24%"，第一反应应该是问试验数，'
         '不是问用了什么结构。', T3),
    ], y0=352)
    return svg(W, H, o, '等错误率的置信区间随目标对数量收缩，以及分辨两套系统所需的试验规模')


# ══════════════════════════════════════════════════════════════
SUP = str.maketrans('0123456789-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻')


def sci(v):
    if v > 0.01:
        return '%.2f 次/天' % v
    e = int(math.floor(math.log10(v)))
    return '%.1f×10%s 次/天' % (v / 10 ** e, str(e).translate(SUP))


def fig_kws():
    W, H = 700, 392
    U = KW['unit']
    o = ['<text x="10" y="18" class="ct">唤醒：'
         '<tspan font-weight="700">误唤醒率的单位不是"%"，是"次/天"</tspan>'
         f'<tspan class="cu"> · 每 {U["hop_ms"]:.0f} ms 一次判决 = 每天 {U["dec_per_day"]/1e4:.0f} 万次</tspan></text>']
    AX, AY, AW, AH = 62, 76, 286, 150
    R = KW['roc']
    lo, hi = math.log10(0.02), math.log10(50)
    fx = lambda v: AX + (math.log10(min(max(v, 0.02), 50)) - lo) / (hi - lo) * AW
    mmax = 6.0
    fy = lambda m: AY + (1 - m / mmax) * AH
    o.append(f'<text x="{AX-46}" y="{AY-30}" class="blab">① 漏唤醒 vs 误唤醒</text>')
    o.append(f'<text x="{AX-46}" y="{AY-14}" class="bsub" fill="{T3}">'
             f'横轴是"次/天"，不是"%"</text>')
    ygrid(o, AX, AW, [0, 2, 4, 6], fy, '%g', '%')
    pts = [(fx(f), fy(m)) for f, m in zip(R['fa_day'], R['miss'])
           if 0.02 <= f <= 50 and m <= mmax]
    poly(o, pts, C1)
    for r in KW['op']:
        if not (0.02 <= r['fa_day'] <= 50 and r['miss'] <= mmax):
            continue
        o.append(f'<circle cx="{fx(r["fa_day"]):.1f}" cy="{fy(r["miss"]):.1f}" '
                 f'r="3" fill="{C3}"/>')
    hi_op = next(r for r in KW['op'] if r['fa_day'] == 5.0)
    lo_op = next(r for r in KW['op'] if r['fa_day'] == 0.5)
    for r, dx, dy, an in ((hi_op, 6, -8, 'start'), (lo_op, -10, 16, 'end')):
        o.append(f'<text x="{fx(r["fa_day"])+dx:.1f}" y="{fy(r["miss"])+dy:.1f}" '
                 f'class="bsub" fill="{C3}" text-anchor="{an}">'
                 f'{r["fa_day"]:g} 次/天，漏 {r["miss"]:.2f}%</text>')
    for v in (0.1, 1, 10):
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'误唤醒 次/天（对数轴）</text>')

    # ② 唤醒词选得好不好，差五个数量级
    BX, BY = 400, 76
    o.append(f'<text x="{BX-16}" y="{BY-30}" class="blab">② 唤醒词选得好不好，差五个数量级</text>')
    o.append(f'<text x="{BX-16}" y="{BY-14}" class="bsub" fill="{T3}">'
             f'"碰巧说出这串音节"的概率（按音节频率独立近似）</text>')
    Ws = KW['words']
    lg = lambda p: math.log10(max(p, 1e-13))
    lo2, hi2 = -12.5, -6.0
    bx0, bw0 = BX + 62, 190
    hx = lambda p: bx0 + (lg(p) - lo2) / (hi2 - lo2) * bw0
    for i, w in enumerate(Ws):
        y = BY + 20 + i * 24
        o.append(f'<text x="{bx0-8}" y="{y+4}" class="bsub" text-anchor="end">{w["w"]}</text>')
        c = C2 if w['n'] == 2 else C1
        o.append(f'<rect x="{bx0}" y="{y-5:.1f}" width="{max(hx(w["p"])-bx0,2):.1f}" '
                 f'height="9" rx="2" fill="{c}" fill-opacity="0.9"/>')
        v = w['per_day']
        o.append(f'<text x="{hx(w["p"])+8:.1f}" y="{y+4:.1f}" class="ctick" '
                 f'fill="{c}">{sci(v)}</text>')
    S = KW['syl']
    o.append(f'<text x="{BX-16}" y="{BY+178}" class="bsub" fill="{T3}">'
             f'{S["types"]} 个带调音节，熵 {S["entropy_bits"]:.2f} bit '
             f'→ 等效词表只有 {S["eff_types"]:.0f} 个</text>')
    HR = KW['hours'][0]
    foot(o, H, [
        ('同一条曲线，从 %g 次/天收到 %g 次/天，阈值只动了 %.2f，'
         '漏唤醒却从 %.2f%% 涨到 %.2f%%。'
         % (hi_op['fa_day'], lo_op['fa_day'], lo_op['thr'] - hi_op['thr'],
            hi_op['miss'], lo_op['miss']), None),
        ('两音节的"你好"比四音节的"小爱同学"碰巧被说出的概率高 %s 倍——'
         '<b>唤醒词的长度比模型更能决定误唤醒</b>。'
         % f'{KW["len_ratio"]:,.0f}', C2),
        ('而且这件事<b>测不出来</b>：要证明 %g 次/天真的降到了 %g 次/天，'
         '需要约 %s 小时的负样本音频。'
         % (HR['l1'], HR['l2'], f'{HR["hours"]:,}'), None),
        ('所以唤醒的指标永远是一对：<b>固定"次/天"，比漏唤醒</b>。'
         '只报其中一个没有意义。', T3),
    ], y0=320)
    return svg(W, H, o, '唤醒的漏检率与每天误唤醒次数的取舍曲线，以及六个候选唤醒词'
                        '被碰巧说出的概率差五个数量级')


# ══════════════════════════════════════════════════════════════
def fig_cascade():
    W, H = 700, 382
    o = ['<text x="10" y="18" class="ct">'
         '<tspan font-weight="700">常开这件事，是靠级联省出来的</tspan>'
         '<tspan class="cu"> · 一级小模型永远跑，二级大模型只在被叫醒时跑</tspan></text>']
    AX, AY, AW, AH = 70, 76, 280, 146
    CA = KW['cascade']
    xs = [r['t1'] for r in CA]
    lo, hi = math.log10(0.05), math.log10(400)
    fy = lambda v: AY + (math.log10(max(v, 0.05)) - lo) / (hi - lo) * AH
    fy = lambda v: AY + (hi - math.log10(max(v, 0.05))) / (hi - lo) * AH
    fx = lambda t: AX + (t - min(xs)) / (max(xs) - min(xs)) * AW
    o.append(f'<text x="{AX-54}" y="{AY-30}" class="blab">① 平均功耗 vs 一级阈值</text>')
    ygrid(o, AX, AW, [0.1, 1, 10, 100], fy, '%g', ' mW')
    nc = KW['nocascade_mw']
    o.append(f'<line x1="{AX}" y1="{fy(nc):.1f}" x2="{AX+AW}" y2="{fy(nc):.1f}" '
             f'stroke="{C2}" stroke-width="1.4" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{AX+AW-4}" y="{fy(nc)-6:.1f}" class="bsub" fill="{C2}" '
             f'text-anchor="end">不级联：大模型一直跑 {nc:g} mW</text>')
    poly(o, [(fx(r['t1']), fy(r['mw'])) for r in CA], C1)
    B = KW['cascade_best']
    CF = KW['casc_cfg']
    o.append(f'<circle cx="{fx(B["t1"]):.1f}" cy="{fy(B["mw"]):.1f}" r="4.5" fill="{C3}"/>')
    o.append(f'<text x="{fx(B["t1"])-8:.1f}" y="{fy(B["mw"])+4:.1f}" class="bsub" '
             f'fill="{C3}" text-anchor="end" font-weight="600">'
             f'拐点 {B["mw"]:.2f} mW</text>')
    for t in (0, 2, 4, 6, 8, 10):
        if min(xs) <= t <= max(xs):
            o.append(f'<text x="{fx(t):.1f}" y="{AY+AH+16}" class="ctick" '
                     f'text-anchor="middle">{t}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'一级阈值 t₁（越高越少叫醒二级）</text>')

    # ② 端侧模型阶梯 + VAD
    BX, BY = 400, 76
    o.append(f'<text x="{BX-14}" y="{BY-30}" class="blab">② 一级模型能有多大</text>')
    o.append(f'<text x="{BX-14}" y="{BY-14}" class="bsub" fill="{T3}">'
             f'按 50 pJ/MAC 的通用 DSP 估算；预算按 0.5 mW 算</text>')
    E = KW['edge']
    for i, r in enumerate(E):
        y = BY + 22 + i * 30
        ok = r['mw50'] <= 0.5
        c = C1 if ok else C2
        o.append(f'<text x="{BX-14}" y="{y}" class="bsub">{r["tag"]}</text>')
        o.append(f'<text x="{BX-14}" y="{y+14}" class="ctick" fill="{T3}">'
                 f'{r["mac"]:,} MAC / 次 = {r["mmac_s"]:.2f} MMAC/s</text>')
        o.append(f'<text x="686" y="{y+1:.1f}" class="ctick" fill="{c}" '
                 f'text-anchor="end" font-weight="600">'
                 f'{r["mw50"]:.3f} mW {"✓" if ok else "✗"}</text>')
    V = KW['vad']
    v15 = next(r for r in V if r['occ'] == 0.15)
    o.append(f'<line x1="{BX-14}" y1="{BY+118}" x2="{BX+180}" y2="{BY+118}" class="grid"/>')
    o.append(f'<text x="{BX-14}" y="{BY+138}" class="bsub" fill="{T3}">'
             f'再前面挂一级 VAD：只有 {v15["occ"]*100:.0f}% 的时间有人声</text>')
    o.append(f'<text x="{BX-14}" y="{BY+156}" class="bsub" fill="{C3}" font-weight="600">'
             f'{V[0]["mw"]:.2f} mW → {v15["mw"]:.3f} mW</text>')
    o.append(f'<text x="{BX-14}" y="{BY+174}" class="bsub" fill="{T3}">'
             f'（误唤醒也跟着按占空比打折）</text>')
    foot(o, H, [
        ('级联的收益来自一个不对称：<b>%.1f%% 的时间里，一级模型说"不是"就够了</b>。'
         '二级每小时只被叫醒 %.0f 次，占空比 %.2f%%。'
         % ((1 - CF['duty']) * 100, B['trig_h'], CF['duty'] * 100), None),
        ('拐点处平均 %.2f mW（一级 %.2f + 二级 %.2f），比不级联的 %g mW 省 %.0f 倍，'
         '代价是漏唤醒从 %.2f%% 到 %.2f%%（一级自己漏掉 %.3f%%）。'
         % (B['mw'], CF['p1'], CF['p2_share'], nc, nc / B['mw'],
            KW['op'][3]['miss'], B['miss'], B['m1']), C2),
        ('阈值再往上就不划算了：功耗已经被一级模型自己的固定开销占住，'
         '而漏唤醒开始线性变差。', None),
        ('<b>"常开"不是一个模型做到的，是一条从 VAD 到一级到二级的阶梯。</b>', None),
    ], y0=310)
    return svg(W, H, o, '级联唤醒的平均功耗随一级阈值变化的曲线与拐点，'
                        '以及三档端侧模型的算力与功耗预算')


OUT['cond'] = fig_cond()
OUT['power'] = fig_power()
OUT['kws'] = fig_kws()
OUT['cascade'] = fig_cascade()
json.dump(OUT, open('figs_b.json', 'w'), ensure_ascii=False)
print('figs_b.json:', {k: len(v) // 1024 for k, v in OUT.items()})
