#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《ASR 链路手册》图 11–15：数据增强、说话人自适应、置信度与校准、蒸馏与量化、长音频切分。
   每张图的数都从对应的 demo_*.json 里取。"""
import json
import numpy as np
from figlib import svg, foot, ygrid, poly, neg, spread, C1, C2, C3, HOT, T3, T2

AUG = json.load(open('demo_aug.json'))
ADP = json.load(open('demo_adapt.json'))
CNF = json.load(open('demo_conf.json'))
KD = json.load(open('demo_kd.json'))
VAD = json.load(open('demo_vad.json'))
OUT = {}


# ══════════════════════════════════════════════════════════════
def fig_aug():
    W, H = 700, 440
    o = ['<text x="10" y="18" class="ct">数据增强：'
         '<tspan font-weight="700">每种做法只覆盖它见过的那一块</tspan>'
         '<tspan class="cu"> · 零成本的逐条 CMVN 比单一增强更能抗没见过的条件</tspan></text>']
    conds = AUG['conds']
    short = {'clean': '干净', 'white10': '白噪10', 'white0': '白噪0', 'babble10': 'babble10',
             'babble0': 'babble0', 'rev05': '混响.5', 'rev12': '混响1.2', 'spd09': '×0.9',
             'spd125': '×1.25', 'tel': '电话'}
    seen = set(AUG['const']['seen'])
    X0, Y0, CW, RH = 150, 66, 52, 26
    for j, c in enumerate(conds):
        col = C1 if c['key'] in seen else (C2 if c['key'] in AUG['const']['unseen'] else T3)
        o.append(f'<text x="{X0+j*CW+CW/2}" y="{Y0-8}" class="ctick" text-anchor="middle" fill="{col}">{short[c["key"]]}</text>')
    for i, r_ in enumerate(AUG['rows']):
        y = Y0 + i * RH
        o.append(f'<text x="{X0-8}" y="{y+RH/2+4}" class="ctick" text-anchor="end" fill="{T2}">{r_["name"]}</text>')
        for j, c in enumerate(conds):
            v = r_['acc'][c['key']]
            a = max(0.0, (v - 10) / 90)
            o.append(f'<rect x="{X0+j*CW+1}" y="{y+1}" width="{CW-2}" height="{RH-2}" rx="2" fill="{C1}" '
                     f'fill-opacity="{0.06 + 0.52*a:.2f}"/>')
            o.append(f'<text x="{X0+j*CW+CW/2}" y="{y+RH/2+4}" class="ctick" text-anchor="middle" '
                     f'fill="var(--text)">{v:.0f}</text>')
    yb = Y0 + len(AUG['rows']) * RH + 18
    o.append(f'<text x="{X0}" y="{yb}" class="ctick" fill="{C1}">■ 训练里出现过的类型</text>')
    o.append(f'<text x="{X0+170}" y="{yb}" class="ctick" fill="{C2}">■ 没见过 / 超出范围</text>')
    o.append(f'<text x="{X0+340}" y="{yb}" class="ctick" fill="{T3}">格内为帧准确率 %</text>')
    n = AUG['note']
    foot(o, H, [
        ('只用干净数据：白噪 10 dB 掉到 <b>%.0f%%</b>；加噪之后 <b>%.0f%%</b>，但没见过的 babble 只有 %.0f%%（干净时 %.0f%%）。'
         % (n['clean_white10'], n['noise_white10'], n['noise_babble10'], n['clean_babble10']), None),
        ('混响增强把混响 0.5 s 拉到 %.0f%%，对白噪毫无帮助；加噪增强对混响也没用（%.0f%%）。各管各的。'
         % (n['rev_rev05'], n['noise_rev05']), C2),
        ('逐条 CMVN 不用任何增强：电话带宽 %.0f%%（加噪 %.0f%%、全部叠加 %.0f%%）；与增强叠加后没见过的平均 %.1f%%。'
         % (n['cmvn_tel'], n['noise_tel'], n['all_tel'], n['allcmvn_unseen']), C1),
        ('SpecAugment 在这里几乎没有效果（babble %.0f%%，干净 %.0f%%）：它是正则，不是鲁棒性手段。'
         % (n['specaug_babble10'], n['specaug_clean']), T2),
    ], y0=332, dy=17)
    return svg(W, H, o, '各种数据增强做法在十种测试条件下的帧准确率')


# ══════════════════════════════════════════════════════════════
def fig_adapt():
    W, H = 700, 490
    o = ['<text x="10" y="18" class="ct">说话人自适应：'
         '<tspan font-weight="700">3 秒标注就能补回大部分，代价是忘掉原来的</tspan>'
         '<tspan class="cu"> · 无标注的伪标签自训练几乎没用</tspan></text>']
    # ① 失配曲线
    AX, AY, AW, AH = 58, 72, 220, 120
    o.append(f'<text x="16" y="{AY-28}" class="blab">① 源模型 vs 说话人声道因子 v</text>')
    cv = ADP['curve']
    vs = [c['v'] for c in cv]
    fx = lambda v: AX + (v - min(vs)) / (max(vs) - min(vs)) * AW
    fy = lambda a: AY + (100 - a) / 50 * AH
    ygrid(o, AX, AW, [50, 70, 90, 100], fy, '%g', '%')
    poly(o, [(fx(c['v']), fy(c['acc'])) for c in cv], C1)
    for c in cv:
        o.append(f'<circle cx="{fx(c["v"]):.1f}" cy="{fy(c["acc"]):.1f}" r="3.5" fill="{C1}"/>')
    for v in (-0.3, -0.1, 0.1, 0.3):
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{neg("%+.1f" % v)}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">声道长度因子 v（源模型只见过 |v|&lt;0.1）</text>')
    # ② 自适应曲线
    EX, EW = 372, 230
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">② 目标说话人：标注秒数 vs 准确率</text>')
    secs = [3, 9, 18, 45, 90]
    gx = lambda s: EX + (np.log10(s) - np.log10(3)) / (np.log10(90) - np.log10(3)) * EW
    gy = lambda a: AY + (100 - a) / 40 * AH
    ygrid(o, EX, EW, [60, 80, 100], gy, '%g', '%')
    colr = {'all': C1, 'mix': C3, 'first': C2, 'last': T2, 'pseudo': T3, 'none': T3}
    lab = {'all': '全部', 'mix': '混源', 'first': '首层', 'last': '末层',
           'pseudo': '伪标签', 'none': '不适应'}
    ends = []
    for r_ in ADP['rows']:
        if r_['key'] == 'cmvn':
            continue
        pts = [(gx(s), gy(r_['acc'][str(s)])) for s in secs]
        poly(o, pts, colr[r_['key']], w=2.2, dash='4 3' if r_['key'] in ('pseudo', 'none') else None)
        ends.append((r_['key'], pts[-1]))
    yy = spread([p[1] + 4 for _, p in ends], 12.0)
    for (k, p), y_ in zip(ends, yy):
        o.append(f'<text x="{p[0]+6:.1f}" y="{y_:.1f}" class="ctick" fill="{colr[k]}">{lab[k]}</text>')
    for s in secs:
        o.append(f'<text x="{gx(s):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{s}</text>')
    o.append(f'<text x="{EX+EW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">有标注的目标说话人语音（秒）</text>')
    # ③ 遗忘
    BY = 266
    o.append(f'<text x="16" y="{BY}" class="blab">③ 调完之后，原说话人（源域）的准确率（目标侧 3 s / 90 s）</text>')
    BX, BW = 150, 300
    names = [('none', '不自适应'), ('all', '全部微调'), ('mix', '微调+混源数据'), ('first', '只调第一层'), ('last', '只调最后一层')]
    gb = lambda a: BX + (a - 60) / 40 * BW
    for i, (k, nm) in enumerate(names):
        y = BY + 26 + i * 22
        a3 = ADP['forget'][k]['3']
        a90 = ADP['forget'][k]['90']
        o.append(f'<text x="{BX-8}" y="{y+4}" class="ctick" text-anchor="end" fill="{T2}">{nm}</text>')
        o.append(f'<rect x="{BX}" y="{y-7}" width="{gb(a90)-BX:.1f}" height="14" rx="2" fill="{colr[k]}" fill-opacity="0.88"/>')
        o.append(f'<text x="{gb(a90)+6:.1f}" y="{y+4}" class="ctick" fill="{colr[k]}">3 s: {a3:.0f}%　90 s: {a90:.0f}%</text>')
    n = ADP['note']
    foot(o, H, [
        ('只给 3 秒标注，全部微调 %.0f%%（原 %.0f%%）、只调第一层 %.0f%%；只调最后一层要 90 秒才到 %.0f%%——失配在输入端，改输出端补不上。'
         % (n['all_3'], n['none_tgt'], n['first_3'], n['last_90']), None),
        ('代价：全部微调后原说话人从 %.0f%% 掉到 %.0f%%；混入等量源数据能压到 %.0f%%，目标侧只少 %.1f 个点。'
         % (n['forget_none'], n['forget_all_3'], n['forget_mix_3'], n['all_3'] - n['mix_3']), C2),
        ('无标注：高置信伪标签自训练 3 秒 %.0f%%、90 秒 %.0f%%，几乎不动——错的帧被当成对的再学一遍。'
         % (R_get(ADP, 'pseudo', '3'), n['pseudo_90']), T2),
    ], y0=424, dy=17)
    return svg(W, H, o, '说话人声道失配曲线、不同自适应方式的数据量曲线与遗忘代价')


def R_get(D, key, sec):
    return [r for r in D['rows'] if r['key'] == key][0]['acc'][sec]


SHORT2 = {'clean': '干净', 'white10': '白噪', 'babble10': 'bab', 'tel': '电话', 'shift': '陌生'}


# ══════════════════════════════════════════════════════════════
def fig_conf():
    W, H = 700, 470
    o = ['<text x="10" y="18" class="ct">置信度与校准：'
         '<tspan font-weight="700">失配时置信度几乎不降，准确率却掉了一大截</tspan>'
         '<tspan class="cu"> · 干净数据上拟合的温度救不了它</tspan></text>']
    P = CNF['models']['plain']['conds']
    Rb = CNF['models']['robust']['conds']
    names = {c['key']: c['name'] for c in CNF['conds']}
    short = {'clean': '干净', 'white10': '白噪 10 dB', 'babble10': 'babble 10 dB', 'tel': '电话带宽',
             'shift': '陌生说话人'}
    # ① 准确率 vs 置信度（只见过干净的模型）
    BX, BW = 100, 150
    o.append(f'<text x="16" y="52" class="blab">① 只见过干净语音的模型：准确率（实）vs 平均置信度（空）</text>')
    for i, k in enumerate(short):
        y = 78 + i * 28
        a, c = P[k]['acc'], P[k]['conf']
        o.append(f'<text x="{BX-8}" y="{y+4}" class="ctick" text-anchor="end" fill="{T2}">{short[k]}</text>')
        o.append(f'<rect x="{BX}" y="{y-8}" width="{a/100*BW:.1f}" height="9" rx="2" fill="{C1}" fill-opacity="0.88"/>')
        o.append(f'<rect x="{BX}" y="{y+2}" width="{c/100*BW:.1f}" height="9" rx="2" fill="none" stroke="{C2}" stroke-width="1.6"/>')
        o.append(f'<text x="{BX+BW+8}" y="{y+4}" class="ctick" fill="{T2}">{a:.0f}/{c:.0f}　ECE {P[k]["ece"]:.0f}</text>')
    # ② 拒识：覆盖 vs 准确率
    AX, AY, AW, AH = 480, 76, 190, 124
    o.append(f'<text x="{AX-40}" y="52" class="blab">② 只收置信度最高的一半，准确率</text>')
    ks = list(short)
    gx = lambda i: AX + (i + 0.5) / len(ks) * AW
    gy = lambda a: AY + (100 - a) / 100 * AH
    ygrid(o, AX, AW, [0, 50, 100], gy, '%g', '%')
    for i, k in enumerate(ks):
        o.append(f'<rect x="{gx(i)-17:.1f}" y="{gy(P[k]["acc"]):.1f}" width="14" height="{AH-(gy(P[k]["acc"])-AY):.1f}" fill="{T3}" fill-opacity="0.55"/>')
        o.append(f'<rect x="{gx(i)+3:.1f}" y="{gy(P[k]["at50"]):.1f}" width="14" height="{AH-(gy(P[k]["at50"])-AY):.1f}" fill="{C3}" fill-opacity="0.9"/>')
        o.append(f'<text x="{gx(i):.1f}" y="{AY+AH+14}" class="ctick" text-anchor="middle">{SHORT2[k]}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+30}" class="ctick" text-anchor="middle" fill="{T3}">灰：全收　绿：收最高 50%</text>')
    # ③ AUROC：置信度能不能判断对错
    CY = 268
    o.append(f'<text x="16" y="{CY}" class="blab">③ 置信度能区分对错吗（AUROC，0.5 = 瞎猜）；两个模型</text>')
    CX, CW = 100, 300
    for i, k in enumerate(ks):
        y = CY + 24 + i * 22
        o.append(f'<text x="{CX-8}" y="{y+4}" class="ctick" text-anchor="end" fill="{T2}">{short[k]}</text>')
        gx3 = lambda a: CX + (a - 0.5) / 0.5 * CW
        o.append(f'<line x1="{gx3(0.5):.1f}" y1="{y-9}" x2="{gx3(0.5):.1f}" y2="{y+9}" stroke="{T3}" stroke-dasharray="2 2"/>')
        o.append(f'<rect x="{gx3(0.5):.1f}" y="{y-8}" width="{gx3(P[k]["auc_maxp"])-gx3(0.5):.1f}" height="7" rx="2" fill="{C1}" fill-opacity="0.88"/>')
        o.append(f'<rect x="{gx3(0.5):.1f}" y="{y+1}" width="{gx3(Rb[k]["auc_maxp"])-gx3(0.5):.1f}" height="7" rx="2" fill="{C2}" fill-opacity="0.88"/>')
        o.append(f'<text x="{gx3(max(P[k]["auc_maxp"], Rb[k]["auc_maxp"]))+6:.1f}" y="{y+4}" class="ctick" fill="{T2}">'
                 f'{P[k]["auc_maxp"]:.2f} / {Rb[k]["auc_maxp"]:.2f}</text>')
    o.append(f'<text x="{CX+CW+90}" y="{CY+34}" class="ctick" fill="{C1}">蓝：只见过干净的</text>')
    o.append(f'<text x="{CX+CW+90}" y="{CY+50}" class="ctick" fill="{C2}">橙：增强过的</text>')
    n = CNF['note']
    foot(o, H, [
        ('白噪 10 dB：准确率 <b>%.0f%%</b>，置信度仍有 <b>%.0f%%</b>；用干净验证集拟合的温度（T=%.1f）把 ECE 从 %.0f 只降到 %.0f，在该条件自己拟合才到 %.0f。'
         % (n['w10_acc'], n['w10_conf'], n['T_clean'], n['w10_ece'], n['w10_eceT'], n['w10_eceTm']), None),
        ('此时置信度几乎没有区分能力（AUROC %.2f），"只收最高的一半"准确率 %.0f%%——拒识救不了一个全错的模型。'
         % (n['w10_auc'], n['w10_at50']), C2),
        ('增强过的模型电话带宽 %.0f%% 对、置信度 %.0f%%，ECE %.0f——增强提高了准确率，没有让它知道自己不知道。'
         % (n['rob_tel_acc'], n['rob_tel_conf'], n['rob_tel_ece']), T2),
    ], y0=424, dy=17)
    return svg(W, H, o, '失配条件下的准确率、置信度、拒识收益与置信度的判别力')


# ══════════════════════════════════════════════════════════════
def fig_kd():
    W, H = 700, 470
    o = ['<text x="10" y="18" class="ct">蒸馏与压缩：'
         '<tspan font-weight="700">值钱的是教师打标的无标注数据，不是软标签本身</tspan>'
         '<tspan class="cu"> · 权重量化到 4 位几乎免费</tspan></text>']
    # ① 学生三种做法（H=32）在 babble10 / white10 / 干净
    S = {(r['H'], r['key']): r for r in KD['students']}
    BX, BW = 170, 150
    o.append(f'<text x="16" y="52" class="blab">① 学生（2×32，参数 %d）的三种训练做法</text>' % S[(32, 'hard')]['params'])
    conds = [('clean', '干净'), ('white10', '白噪 10 dB'), ('babble10', 'babble 10 dB')]
    colr = {'hard': T3, 'kd': C2, 'kd_u': C1}
    y = 80
    for ck, nm in conds:
        o.append(f'<text x="16" y="{y}" class="ctick" fill="{T2}">{nm}</text>')
        for j, key in enumerate(('hard', 'kd', 'kd_u')):
            v = S[(32, key)]['acc'][ck]
            yy = y + 6 + j * 14
            w = (v - 80) / 20 * BW
            o.append(f'<rect x="{BX}" y="{yy}" width="{max(w,1):.1f}" height="10" rx="2" fill="{colr[key]}" fill-opacity="0.9"/>')
            o.append(f'<text x="{BX+w+6:.1f}" y="{yy+9}" class="ctick" fill="{colr[key]}">{v:.1f}</text>')
        y += 66
    ly = 300
    for key, nm in (('hard', '只用硬标签（12 条）'), ('kd', '+ 教师软标签（同样 12 条）'), ('kd_u', '+ 教师给无标注增强数据打标')):
        o.append(f'<rect x="16" y="{ly-8}" width="10" height="10" rx="2" fill="{colr[key]}"/>')
        o.append(f'<text x="32" y="{ly+1}" class="ctick" fill="{colr[key]}">{nm}</text>')
        ly += 14
    # ② 量化
    AX, AY, AW, AH = 440, 76, 220, 130
    o.append(f'<text x="{AX-30}" y="52" class="blab">② 权重量化（干净准确率）</text>')
    Q = KD['quant']
    bits = [8, 6, 4, 3]
    fx = lambda b: AX + (8 - b) / 5 * AW
    fy = lambda a: AY + (100 - a) / 8 * AH
    ygrid(o, AX, AW, [92, 94, 96, 98, 100], fy, '%g', '%')
    for mdl, ls in (('教师 2×512', None), ('学生 2×64', '4 3')):
        for pc, col in ((False, C2), (True, C1)):
            pts = [(fx(q['bits']), fy(q['acc']['clean'])) for q in Q if q['model'] == mdl and q['bits'] in bits
                   and q['per_channel'] == pc]
            poly(o, sorted(pts), col, w=2.2, dash=ls)
    for b in bits:
        o.append(f'<text x="{fx(b):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">int{b}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="ctick" text-anchor="middle" fill="{T3}">橙：按张量　蓝：按通道　实线：教师　虚线：学生</text>')
    n = KD['note']
    foot(o, H, [
        ('教师 %d 参数、学生 %d 参数（%.0f 倍）。同样 12 条标注加教师软标签，babble 从 %.1f 到 %.1f，几乎没动；'
         % (n['teacher_params'], n['student32_params'], n['ratio_params'], n['hard32_babble'], n['kd32_babble']), None),
        ('加教师打标的无标注增强数据，babble 到 <b>%.1f</b>，白噪 10 dB 从 %.1f 到 %.1f。'
         % (n['kdu32_babble'], n['hard32_white'], n['kdu32_white']), C1),
        ('温度 T 与 α 在 T=1–8、α=0–1 的整个扫描里干净与带噪的差别都在 ±1 个点以内——这两个旋钮没有那么重要。', C2),
        ('教师 int8 按张量 %.1f%%；int4 %.1f%%（按通道同）；int3 按张量掉到 %.1f%%、按通道 %.1f%%。学生更小，int3 按张量掉到 %.1f%%。'
         % (n['q8_pt'], n['q4_pt'], n['q3_pt'], n['q3_pc'], n['sq3_pt']), C1),
    ], y0=392, dy=17)
    return svg(W, H, o, '学生模型三种训练做法的准确率，以及权重量化位数与准确率的关系')


# ══════════════════════════════════════════════════════════════
def fig_vad():
    W, H = 700, 470
    o = ['<text x="10" y="18" class="ct">长音频切分：'
         '<tspan font-weight="700">固定切块切到的是少数，VAD 的参数却随噪声而变</tspan>'
         '<tspan class="cu"> · 补偿 100 ms 是便宜的保险</tspan></text>']
    # ① 固定切块
    BX, BW = 120, 160
    o.append(f'<text x="16" y="52" class="blab">① 固定切块：被切断的语音岛（%）</text>')
    for i, r_ in enumerate(VAD['fixed']):
        y = 78 + i * 24
        nm = '%d s %s' % (r_['L'], '无重叠' if r_['overlap'] == 0 else '重叠 1 s')
        o.append(f'<text x="{BX-8}" y="{y+4}" class="ctick" text-anchor="end" fill="{T2}">{nm}</text>')
        w = r_['pct'] / 6.0 * BW
        col = C2 if r_['overlap'] == 0 else C1
        o.append(f'<rect x="{BX}" y="{y-7}" width="{max(w,1):.1f}" height="14" rx="2" fill="{col}" fill-opacity="0.88"/>')
        o.append(f'<text x="{BX+w+6:.1f}" y="{y+4}" class="ctick" fill="{col}">{r_["pct"]:.1f}%{"" if r_["overlap"]==0 else "　算力 ×%.2f" % r_["cost"]}</text>')
    # ② 余量扫描
    AX, AY, AW, AH = 430, 76, 190, 130
    o.append(f'<text x="{AX-30}" y="52" class="blab">② 能量 VAD：余量 vs 召回（实）/ 误报（虚）</text>')
    margs = VAD['const']['margins_db']
    fx = lambda m: AX + (m - margs[0]) / (margs[-1] - margs[0]) * AW
    fy = lambda a: AY + (100 - a) / 100 * AH
    ygrid(o, AX, AW, [0, 50, 100], fy, '%g', '%')
    colr = {'clean': T3, 'w10': C1, 'w0': T2, 'b10': C2}
    lab = {'clean': '干净', 'w10': '白噪10', 'w0': '白噪0', 'b10': 'babble10'}
    ends = []
    for r_ in VAD['vad']:
        if r_['key'] not in colr:
            continue
        c0 = {c['margin']: c for c in r_['cells'] if c['pad_ms'] == 0}
        poly(o, [(fx(m), fy(c0[m]['recall'])) for m in margs], colr[r_['key']], w=2.2)
        poly(o, [(fx(m), fy(c0[m]['fa'])) for m in margs], colr[r_['key']], w=1.4, dash='3 3')
        ends.append((r_['key'], (fx(margs[-1]), fy(c0[margs[-1]]['recall']))))
    yy = spread([p[1] + 4 for _, p in ends], 12.0)
    for (k, p), y_ in zip(ends, yy):
        o.append(f'<text x="{p[0]+6:.1f}" y="{y_:.1f}" class="ctick" fill="{colr[k]}">{lab[k]}</text>')
    for m in margs:
        o.append(f'<text x="{fx(m):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{m:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">高出噪声底的余量（dB）</text>')
    # ③ 补偿：被削头尾的语音岛
    CY = 262
    o.append(f'<text x="16" y="{CY}" class="blab">③ 首尾补偿：头或尾被削掉的语音岛（%，余量 9 dB）</text>')
    pads = [0, 50, 100, 200, 300]
    CX, CW = 120, 300
    for i, (ck, nm) in enumerate((('w10', '白噪 10 dB'), ('b10', 'babble 10 dB'))):
        r_ = [r for r in VAD['vad'] if r['key'] == ck][0]
        for j, p in enumerate(pads):
            c = [c for c in r_['cells'] if c['margin'] == 9.0 and c['pad_ms'] == p][0]
            x = CX + j * 60
            if i == 0:
                o.append(f'<text x="{x+22}" y="{CY+22}" class="ctick" text-anchor="middle" fill="{T3}">补 {p} ms</text>')
            y = CY + 44 + i * 24
            o.append(f'<rect x="{x}" y="{y-9}" width="44" height="18" rx="2" fill="{C1}" fill-opacity="{0.08+min(c["clip_pct"],10)/10*0.8:.2f}"/>')
            o.append(f'<text x="{x+22}" y="{y+4}" class="ctick" text-anchor="middle" fill="{T2}">{c["clip_pct"]:.1f}</text>')
        o.append(f'<text x="{CX-8}" y="{CY+48+i*24}" class="ctick" text-anchor="end" fill="{T2}">{nm}</text>')
    n = VAD['note']
    foot(o, H, [
        ('10 s 切块无重叠会切断 <b>%.1f%%</b> 的语音岛（%.0f 个里的 %.0f 个）；重叠 1 s 降到 %.1f%%，算力 ×%.2f。'
         % (n['fix10_pct'], n['islands'], n['fix10_cut'], n['fix10ov_pct'], n['fix10ov_cost']), None),
        ('同一个 9 dB 余量：白噪 10 dB 召回 %.0f%%、白噪 0 dB 召回 <b>%.0f%%</b>；降到 3 dB 才有 %.0f%%，代价是误报 %.0f%%。'
         'babble 10 dB 余量 3 dB 时误报 %.0f%%。'
         % (n['w10_recall'], n['w0_recall9'], n['w0_recall3'], n['w0_fa3'], n['b10_fa3']), C2),
        ('补 100 ms：白噪 10 dB 被削头尾的语音岛从 %.1f%% 到 %.1f%%，送进模型的时长从 %.0f%% 到 %.0f%%（干净 %.0f%% → %.0f%%）。'
         % (n['w10_clip0'], n['w10_clip100'], n['w10_keep0'], n['w10_keep300'] if False else
            [c for c in [r for r in VAD['vad'] if r['key'] == 'w10'][0]['cells'] if c['margin'] == 9.0 and c['pad_ms'] == 100][0]['keep'],
            n['clean_keep0'], n['clean_keep100']), C3),
    ], y0=392, dy=17)
    return svg(W, H, o, '固定切块的切断率、能量 VAD 的余量扫描与首尾补偿的收益')


OUT['aug'] = fig_aug()
OUT['adapt'] = fig_adapt()
OUT['conf'] = fig_conf()
OUT['kd'] = fig_kd()
OUT['vad'] = fig_vad()
json.dump(OUT, open('figs_c.json', 'w'), ensure_ascii=False)
print('figs_c.json:', {k: len(v) // 1024 for k, v in OUT.items()})
