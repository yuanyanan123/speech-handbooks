#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回声消除新增几节的图：不靠检测器的对策、延迟估计、多参考、全双工打断、联合链路。
   每张图的数都从对应的 demo_aec_*.json 里取。"""
import json, os
import numpy as np
from figlib import (svg, foot, ygrid, poly, neg, spread, C1, C2, C3, HOT, T3, T2)

HERE = os.path.dirname(os.path.abspath(__file__))
_j = lambda n: json.load(open(os.path.join(HERE, n)))
OUT = {}


# ══════════════════════════════════════════════════════════════
def fig_dtd2():
    D = _j('demo_aec_dtd2.json')
    W, H = 700, 540
    o = ['<text x="10" y="18" class="ct">不靠检测器：'
         '<tspan font-weight="700">能量比 DTD 其实不比"不再学"好</tspan>'
         '<tspan class="cu"> · 路径一变，被冻住的滤波器就回不来</tspan></text>']
    col = {'none': T3, 'frozen': T3, 'energy': C2, 'coh': C2, 'twopath': C3, 'fdkf': C3, 'oracle': C1}

    def bars(rows, X0, Y0, title, mx, label_x):
        o.append(f'<text x="{X0}" y="{Y0-16}" class="blab">{title}</text>')
        gx = lambda v: X0 + label_x + max(v, 0) / mx * 150
        for i, r_ in enumerate(rows):
            y = Y0 + i * 22
            o.append(f'<text x="{X0+label_x-8}" y="{y+4}" class="ctick" text-anchor="end" '
                     f'fill="{T2}">{r_["name"]}</text>')
            w = max(r_['erle'], 0) / mx * 150
            o.append(f'<rect x="{X0+label_x}" y="{y-7}" width="{w:.1f}" height="14" rx="2" '
                     f'fill="{col[r_["key"]]}" fill-opacity="0.88"/>')
            o.append(f'<text x="{gx(r_["erle"])+5:.1f}" y="{y+4}" class="ctick" '
                     f'fill="{col[r_["key"]]}">{neg("%.1f" % r_["erle"])} dB</text>')

    short = {'从不冻结': '不冻结', '收敛期之后不再学': '收敛后不再学', '能量比 DTD（κ=2）': '能量比 DTD',
             '相干性 DTD（θ=0.8）': '相干性 DTD', '双路径': '双路径', '频域卡尔曼': '频域卡尔曼',
             '全知 DTD（上界）': '全知（上界）'}
    st = [dict(r_, name=short[r_['name']]) for r_ in D['static']]
    ch = [dict(r_, name=short[r_['name']]) for r_ in D['change']]
    bars(st, 16, 74, '① 路径不变：单讲段 ERLE', 28, 100)
    bars(ch, 370, 74, '② 第 12 s 路径整条换掉', 28, 100)

    # ③ 近端电平扫描
    AX, AY, AW, AH = 58, 292, 250, 100
    o.append(f'<text x="16" y="{AY-24}" class="blab">③ 近端比回声响多少：单讲段 ERLE</text>')
    nn = D['ner']
    xs = [r_['ner'] for r_ in nn]
    fx = lambda v: AX + (v - xs[0]) / (xs[-1] - xs[0]) * AW
    ylo, yhi = -5.0, 30.0
    fy = lambda v: AY + (yhi - v) / (yhi - ylo) * AH
    ygrid(o, AX, AW, [0, 10, 20, 30], fy, '%g', ' dB')
    lab = {"none": "不冻结", "frozen": "不再学", "energy": "能量比", "twopath": "双路径",
           "fdkf": "卡尔曼", "oracle": "全知"}
    ends = []
    for k in ('none', 'frozen', 'energy', 'twopath', 'fdkf', 'oracle'):
        pts = []
        for r_ in nn:
            v = [q for q in r_['rows'] if q['key'] == k][0]['erle']
            pts.append((fx(r_['ner']), fy(v)))
        poly(o, pts, col[k], w=2.2, dash='4 3' if k in ('none', 'frozen', 'energy') else None)
        ends.append((k, pts[-1]))
    yy = spread([p[1] + 4 for _, p in ends], 12.0)
    for (k, p), y_ in zip(ends, yy):
        o.append(f'<text x="{p[0]+6:.1f}" y="{y_:.1f}" class="ctick" fill="{col[k]}">{lab[k]}</text>')
    for v in xs:
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{v:+.0f}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">近端相对回声的电平（dB）</text>')

    # ④ 一句话版：谁需要外挂检测器
    o.append(f'<text x="400" y="{AY-24}" class="blab">④ 三类做法</text>')
    notes = [(T3, '基线', '不冻结 / 收敛后不再学'),
             (C2, '要检测器', '能量比、相干性：检测器弱时\n最优点就是"几乎不学"'),
             (C3, '不要检测器', '双路径、卡尔曼：步长自己变'),
             (C1, '上界', '全知：知道哪几块是双讲')]
    y = AY
    for c_, t1, t2 in notes:
        o.append(f'<rect x="400" y="{y-8}" width="10" height="10" rx="2" fill="{c_}" fill-opacity="0.88"/>')
        o.append(f'<text x="418" y="{y+1}" class="bsub" fill="{c_}">{t1}</text>')
        for j, ln in enumerate(t2.split('\n')):
            o.append(f'<text x="418" y="{y+16+j*14}" class="ctick" fill="{T3}">{ln}</text>')
        y += 38 + 14 * (t2.count('\n'))

    n = D['note']
    foot(o, H, [
        ('我曾把"最优在线 DTD 误检 80%%"读成"宁可多冻"。加一条对照才看清：'
         '<b>收敛后干脆不再学，反而高 %.2f dB</b>（%.2f vs %.2f）。'
         % (n['frozen_vs_energy'], n['frozen_static'], n['energy_static']), HOT),
        ('代价在②：路径一换，不再学 %s dB、能量比 DTD %s dB——冻住的滤波器回不来；'
         '无检测器的卡尔曼仍有 %.1f dB。'
         % (neg('%.2f' % n['frozen_change']), neg('%.2f' % n['energy_change']), n['fdkf_change']), None),
        ('卡尔曼比不冻结高 %.1f dB、比能量比高 %.1f dB，但距全知仍差 %.1f dB，这一段还没解决。'
         % (n['fdkf_vs_none'], n['fdkf_vs_energy'], n['fdkf_gap_to_oracle']), C3),
    ], y0=474)
    return svg(W, H, o, '几种双讲对策在路径不变、路径突变与不同近端电平下的单讲段 ERLE')


# ══════════════════════════════════════════════════════════════
def fig_delay():
    D = _j('demo_aec_delay.json')
    W, H = 700, 470
    o = ['<text x="10" y="18" class="ct">延迟估计：'
         '<tspan font-weight="700">估高是悬崖，估低只是少了点尾巴</tspan>'
         '<tspan class="cu"> · 所以估计要故意往低的一侧偏</tspan></text>']
    # ① 窗长
    AX, AY, AW, AH = 58, 72, 250, 130
    wins = D['const']['wins']
    xs = [np.log10(w) for w in wins]
    fx = lambda w: AX + (np.log10(w) - xs[0]) / (xs[-1] - xs[0]) * AW
    fy = lambda v: AY + (100 - v) / 100 * AH
    o.append(f'<text x="16" y="{AY-28}" class="blab">① GCC-PHAT 估对（误差 ≤ 2 ms）的比例，随窗长</text>')
    ygrid(o, AX, AW, [0, 50, 100], fy, '%g', '%')
    hl = {'回声/底噪 −10 dB': HOT, '直达声很弱（反射更强）': C2, '干净（回声/底噪 40 dB）': C1}
    for r_ in D['acc']:
        pts = [(fx(c['win']), fy(c['ok'])) for c in r_['wins']]
        col = hl.get(r_['cond'], T3)
        poly(o, pts, col, w=2.4 if r_['cond'] in hl else 1.2, dash=None if r_['cond'] in hl else '3 3')
    for w in wins:
        o.append(f'<text x="{fx(w):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{w:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">窗长（s，对数轴）</text>')
    ly = AY + 6
    for nm, c_ in (('回声/底噪 −10 dB', HOT), ('直达声很弱（反射更强）', C2), ('干净', C1), ('其余四种（灰）', T3)):
        o.append(f'<text x="{AX+AW-4}" y="{ly+AH-50}" class="ctick" text-anchor="end" fill="{c_}">{nm}</text>')
        ly += 13
    # ② 估偏
    EX, EW = 420, 236
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">② 估偏之后的 ERLE（负 = 低估）</text>')
    ers = [c['err_ms'] for c in D['err'][0]['cells']]
    fex = lambda v: EX + (v - ers[0]) / (ers[-1] - ers[0]) * EW
    ylo, yhi = -15.0, 25.0
    fey = lambda v: AY + (yhi - max(v, ylo)) / (yhi - ylo) * AH
    ygrid(o, EX, EW, [-10, 0, 10, 20], fey, '%g', ' dB')
    for r_, col, dash in ((D['err'][0], C1, None), (D['err'][1], C3, '5 3')):
        poly(o, [(fex(c['err_ms']), fey(c['erle'])) for c in r_['cells']], col, w=2.4, dash=dash)
    o.append(f'<line x1="{fex(0):.1f}" y1="{AY}" x2="{fex(0):.1f}" y2="{AY+AH}" stroke="{T3}" stroke-dasharray="2 3"/>')
    for v in (-48, -32, -16, 0, 16, 32):
        o.append(f'<text x="{fex(v):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{neg("%+d" % v) if v else 0}</text>')
    o.append(f'<text x="{EX+EW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">估计 − 真值（ms）</text>')
    o.append(f'<text x="{EX+6}" y="{AY+AH-22}" class="ctick" fill="{C1}">实线：余量 0</text>')
    o.append(f'<text x="{EX+6}" y="{AY+AH-8}" class="ctick" fill="{C3}">虚线：余量 8 ms</text>')
    n = D['note']
    foot(o, H, [
        ('窗长 0.25 s 只有 %.0f%% 估对，1 s 以上才靠得住（干净时 %.0f%%）；最差的两种是回声比底噪还低 10 dB、和直达声很弱。'
         % (n['ok_short'], n['clean_ok_1s']), None),
        ('估高 8 ms 就从 %.1f dB 掉到 %s dB；估低 48 ms 也还有 %.1f dB——不对称，所以要故意往低的一侧偏。'
         % (n['erle_exact'], neg('%.1f' % n['over8']), n['under48']), HOT),
        ('留 8 ms 余量把悬崖往右推了 8 ms：估高 8 ms 仍有 %.1f dB，代价是估准时少 %.1f dB。'
         % (n['m8_over8'], n['erle_exact'] - n['m8_exact']), C3),
    ], y0=374)
    return svg(W, H, o, '延迟估计的窗长精度，以及估高与估低对回声消除的不对称影响')


# ══════════════════════════════════════════════════════════════
def fig_multi():
    D = _j('demo_aec_multi.json')
    W, H = 700, 420
    o = ['<text x="10" y="18" class="ct">立体声回声：'
         '<tspan font-weight="700">ERLE 好看，路径却没辨识对</tspan>'
         '<tspan class="cu"> · 去相关能买回一些，价钱是播放质量</tspan></text>']
    rows = D['rows']
    # ① 换人后掉多少
    BX, BW = 150, 170
    o.append(f'<text x="16" y="52" class="blab">① 远端说话人换人之后，ERLE 掉多少</text>')
    mx = max(r_['drop'] for r_ in rows) * 1.1
    for i, r_ in enumerate(rows):
        y = 78 + i * 24
        col = T3 if i == 0 else (C2 if '半波' in r_['name'] else C3)
        o.append(f'<text x="{BX-8}" y="{y+4}" class="ctick" text-anchor="end" fill="{T2}">{r_["name"]}</text>')
        w = r_['drop'] / mx * BW
        o.append(f'<rect x="{BX}" y="{y-7}" width="{w:.1f}" height="14" rx="2" fill="{col}" fill-opacity="0.88"/>')
        o.append(f'<text x="{BX+w+5:.1f}" y="{y+4}" class="ctick" fill="{col}">{r_["drop"]:.1f} dB</text>')
    # ② 失调 vs 播放信噪比
    AX, AY, AW, AH = 440, 78, 220, 130
    o.append(f'<text x="{AX-30}" y="52" class="blab">② 路径辨识 vs 播放被改了多少</text>')
    px = [r_['play_snr'] for r_ in rows[1:]]
    fx = lambda v: AX + (35 - v) / 30 * AW
    mlo, mhi = -16.0, 0.0
    fy = lambda v: AY + (mhi - v) / (mhi - mlo) * AH
    ygrid(o, AX, AW, [-15, -10, -5, 0], fy, '%g', ' dB')
    base = rows[0]
    o.append(f'<circle cx="{fx(36):.1f}" cy="{fy(base["mis"]):.1f}" r="5" fill="{T3}"/>')
    o.append(f'<text x="{fx(36)-8:.1f}" y="{fy(base["mis"])-8:.1f}" class="ctick" text-anchor="end" fill="{T3}">不去相关</text>')
    for r_ in rows[1:]:
        col = C2 if '半波' in r_['name'] else C3
        o.append(f'<circle cx="{fx(r_["play_snr"]):.1f}" cy="{fy(r_["mis"]):.1f}" r="5" fill="{col}"/>')
        dy = {'半波整流 α=0.3': 15, '半波整流 α=0.5': -9}.get(r_['name'], 4)
        dx = {'半波整流 α=0.3': -4, '半波整流 α=0.5': 4}.get(r_['name'], 7)
        o.append(f'<text x="{fx(r_["play_snr"])+dx:.1f}" y="{fy(r_["mis"])+dy:.1f}" class="ctick" fill="{col}">'
                 f'{r_["name"].replace("半波整流 ", "").replace("加噪 ", "")}</text>')
    for v in (10, 20, 30):
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{v}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">播放信噪比（dB，越右越保真）</text>')
    o.append(f'<text x="{AX-30}" y="{AY+AH+50}" class="ctick" fill="{T3}">纵轴：换人前的失调（越低越好）　橙 = 半波整流　绿 = 加噪</text>')
    n = D['note']
    foot(o, H, [
        ('同一说话人的两路只差时延与增益，两路相干性 %.3f：滤波器只能辨识出 h₁ + h₂∗c 这个组合，失调 %s dB，却有 %.1f dB 的 ERLE。'
         % (n['base_coh'], neg('%.1f' % n['base_mis']), n['base_before']), None),
        ('换人（c 变了）之后 ERLE 掉 %.1f dB。半波整流 α=0.5 只买回 %.1f dB，还让换人前的 ERLE 少 %.1f dB。'
         % (n['base_drop'], n['base_drop'] - n['hw05_drop'], n['base_before'] - n['hw05_before']), HOT),
        ('加噪 −10 dB 买回 %.1f dB、失调到 %s dB，但播放信噪比只剩 %.0f dB——能听见。−20 dB（%.0f dB 信噪比）几乎买不到。'
         % (n['base_drop'] - n['n10_drop'], neg('%.1f' % n['n10_mis']), n['n10_snr'], n['n20_snr']), C2),
    ], y0=336)
    return svg(W, H, o, '立体声参考的非唯一性，以及两种去相关各自的收益与代价')


# ══════════════════════════════════════════════════════════════
def fig_duplex():
    D = _j('demo_aec_duplex.json')
    W, H = 700, 480
    o = ['<text x="10" y="18" class="ct">全双工打断：'
         '<tspan font-weight="700">平均 ERLE 买到的灵敏度，被瞬态吃掉一大半</tspan>'
         '<tspan class="cu"> · 近端比回声轻 10 dB 仍可检，但要等 1 s</tspan></text>']
    ks = D['kinds']
    colr = {'raw': T3, 'energy': C2, 'fdkf': C3, 'oracle': C1, 'fdkf_mask': T2}
    AX, AY, AW, AH = 58, 72, 250, 130
    o.append(f'<text x="16" y="{AY-28}" class="blab">① 近端有多轻还能检出（6 次试验的检出率）</text>')
    ners = [c['ner'] for c in ks[0]['by_ner']]
    fx = lambda v: AX + (v - ners[0]) / (ners[-1] - ners[0]) * AW
    fy = lambda v: AY + (100 - v) / 100 * AH
    ygrid(o, AX, AW, [0, 50, 100], fy, '%g', '%')
    for r_ in ks:
        pts = [(fx(c['ner']), fy(c['det'])) for c in r_['by_ner']]
        poly(o, pts, colr[r_['kind']], w=2.4, dash='4 3' if r_['kind'] in ('raw', 'fdkf_mask') else None)
    for v in ners:
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{neg("%+d" % v) if v else 0}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">近端相对回声的电平（dB）</text>')
    # ② 回声底 vs 阈值
    EX, EW = 400, 270
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">② 稳态回声底 与 校准出的阈值</text>')
    lo, hi = -30.0, 35.0
    gx = lambda v: EX + 70 + (v - lo) / (hi - lo) * (EW - 70)
    for i, r_ in enumerate(ks):
        y = AY + i * 26
        nm = r_['name'].replace('AEC + ', '').replace('AEC（', '').replace('）', '')
        o.append(f'<text x="{EX+62}" y="{y+4}" class="ctick" text-anchor="end" fill="{T2}">{nm[:9]}</text>')
        o.append(f'<line x1="{gx(lo):.1f}" y1="{y}" x2="{gx(hi):.1f}" y2="{y}" class="grid"/>')
        o.append(f'<circle cx="{gx(r_["floor"]):.1f}" cy="{y}" r="4.5" fill="{colr[r_["kind"]]}"/>')
        o.append(f'<rect x="{gx(r_["theta"])-4:.1f}" y="{y-4.5}" width="9" height="9" fill="{HOT}"/>')
    o.append(f'<text x="{EX+70}" y="{AY+5*26+8}" class="ctick" fill="{T3}">● 回声底　■ 阈值（校准段最高 + 1 dB）</text>')
    o.append(f'<text x="{EX+70}" y="{AY+5*26+22}" class="ctick" fill="{T3}">统计量 = 10·log₁₀(残差功率 / 回声估计功率)</text>')
    n = D['note']
    K = {r_['kind']: r_ for r_ in ks}
    foot(o, H, [
        ('不做 AEC，近端比回声轻 5 dB 以下一个也检不出；有 AEC 之后，ERLE %.0f dB → 最轻可检 %s dB，ERLE %.0f dB → %s dB。'
         % (K['energy']['erle'], neg('%+.0f' % n['energy_min']), K['fdkf']['erle'], neg('%+.0f' % n['fdkf_min'])), None),
        ('但全知 DTD（ERLE %.0f dB）并不比卡尔曼更灵：阈值被回声里的瞬态尖峰定在回声底之上 %.0f–%.0f dB，'
         '平均 ERLE 的好处被抵掉一大半。' % (K['oracle']['erle'],
         K['energy']['theta'] - K['energy']['floor'], K['fdkf']['theta'] - K['fdkf']['floor']), HOT),
        ('我试了"远端起音后屏蔽 190 ms"，阈值没降（%.1f → %.1f dB），所以尖峰不在起音处。'
         % (K['fdkf']['theta'], K['fdkf_mask']['theta']), C2),
        ('延迟：近端 0 dB 时中位 %.0f ms 才触发，+10 dB 时 %.0f ms；半双工（播放时关麦）则一个也听不见。'
         % (n['fdkf_lat0'], n['fdkf_lat10']), C3),
    ], y0=374, dy=17)
    return svg(W, H, o, '全双工打断的可检测电平、回声底与阈值')


# ══════════════════════════════════════════════════════════════
def fig_chain():
    D = _j('demo_aec_chain.json')
    W, H = 700, 400
    o = ['<text x="10" y="18" class="ct">AEC 之后那一级：'
         '<tspan font-weight="700">RES 管回声，NS 管噪声，各管各的</tspan>'
         '<tspan class="cu"> · 先后顺序几乎无所谓</tspan></text>']
    rows = D['rows']
    base = D['base']
    panels = [('① 只有回声：再下降多少 dB', lambda r_: r_['echo'] - rows[0]['echo'], 0),
              ('② 只有近端 + 噪声：近端 segSNR 的收益', lambda r_: r_['noise_near'] - base['noise_near'], 0),
              ('③ 三样都有：近端 segSNR 的收益', lambda r_: r_['all_near'] - base['all_near'], 0)]
    col = {'aec': T3, 'ns': C1, 'res': C2, 'res_ns': C3, 'ns_res': C3}
    for pi, (title, fn, _) in enumerate(panels):
        X0 = 16 + pi * 230
        o.append(f'<text x="{X0}" y="52" class="blab">{title}</text>')
        vals = [fn(r_) for r_ in rows]
        mx = max(max(vals), 1.0) * 1.15
        for i, r_ in enumerate(rows):
            y = 84 + i * 40
            o.append(f'<text x="{X0}" y="{y-12}" class="ctick" fill="{T2}">{r_["name"]}</text>')
            v = vals[i]
            w = max(v, 0) / mx * 150
            o.append(f'<rect x="{X0}" y="{y-6}" width="{max(w,1):.1f}" height="14" rx="2" fill="{col[r_["key"]]}" fill-opacity="0.88"/>')
            o.append(f'<text x="{X0+w+5:.1f}" y="{y+5}" class="ctick" fill="{col[r_["key"]]}">{neg("%+.1f" % v)} dB</text>')
    n = D['note']
    foot(o, H, [
        ('NS 在只有回声时只多压 %.1f dB，RES 多压 %.1f dB；而只有噪声时 NS 给近端 +%.1f dB，RES 一点没有（它不看噪声）。'
         % (n['ns_echo'] - n['aec_echo'], n['res_echo'] - n['aec_echo'], n['ns_noise'] - n['base_noise']), None),
        ('三样都有时 RES→NS 比 NS→RES 好 %.2f dB——顺序几乎无所谓；真正有用的是两个都留。' % n['order_gap'], HOT),
    ], y0=332)
    return svg(W, H, o, 'AEC 之后残余回声抑制与单通道降噪的分工与先后顺序')


# ══════════════════════════════════════════════════════════════
def main():
    OUT['dtd2'] = fig_dtd2()
    for n, fn in (('delay', 'fig_delay'), ('multi', 'fig_multi'), ('duplex', 'fig_duplex'),
                  ('chain', 'fig_chain')):
        if fn in globals() and os.path.exists(os.path.join(HERE, 'demo_aec_%s.json' % n)):
            OUT[n] = globals()[fn]()
    json.dump(OUT, open(os.path.join(HERE, 'figs_fe2.json'), 'w'), ensure_ascii=False)
    print('figs_fe2.json:', {k: len(v) // 1024 for k, v in OUT.items()})


if __name__ == '__main__':
    main()
