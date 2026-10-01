#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《TTS 合成手册》的全部自绘图。配色沿用阵列手册：s1 蓝 / s2 橙 / s3 绿 / hot。
   红绿不同时作数据标记（CVD）。"""
import json, math
import numpy as np

G = json.load(open('demo_g2p.json'))
S = json.load(open('demo_smooth.json'))
ME = json.load(open('demo_mel.json'))
AL = json.load(open('demo_align.json'))
FL = json.load(open('demo_flow.json'))
RQ = json.load(open('demo_rvq.json'))
VO = json.load(open('demo_voc.json'))
EV = json.load(open('demo_eval.json'))

C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
T3, T2 = 'var(--text-3)', 'var(--text-2)'
OUT = {}


def defs(u):
    return (f'<defs><marker id="{u}a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" '
            f'fill="var(--text-2)"/></marker>'
            f'<marker id="{u}s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" '
            f'fill="var(--s1)"/></marker>'
            f'<marker id="{u}w" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" '
            f'fill="var(--s2)"/></marker></defs>')


def svg(w, h, body, label, cls='chart'):
    return (f'<svg viewBox="0 0 {w} {h}" class="{cls}" role="img" aria-label="{label}">'
            + ''.join(body) + '</svg>')


def axis(o, X, Y, W, H, ticks, fmt=lambda v: '%g' % v, minus=True):
    for v, y in ticks:
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+W}" y2="{y:.1f}" class="grid"/>')
        s = fmt(v)
        if minus and s.startswith('-'):
            s = '−' + s[1:]
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{s}</text>')


# ══════════════════════════════════════════════════════════════
def fig_chain():
    W, H = 700, 342
    o = [defs('ch'),
         '<text x="10" y="18" class="ct">TTS 的完整链路，'
         '<tspan font-weight="700">以及每一段各自会错成什么样</tspan>'
         '<tspan class="cu"> · 上排是模块，下排是它坏掉时你听到的声音</tspan></text>']
    boxes = [('文本归一化', 'TN：数字、符号、缩写', '“2025”读成“二零二五”还是“两千零二十五”'),
             ('字音转换', 'G2P + 多音字', '“行长”读成 xíng zhǎng'),
             ('韵律', '停顿、重音、语调', '该断的地方不断，一口气念完'),
             ('时长', '每个音素多少帧', '语速忽快忽慢，或者全句一个速度'),
             ('声学模型', '梅尔谱 / 隐表示', '发闷、糊、没有细节'),
             ('声码器', '波形', '电音、金属音、嘶嘶声')]
    x0, bw, gap = 14, 104, 9
    for i, (name, sub, err) in enumerate(boxes):
        x = x0 + i * (bw + gap)
        cls = 'bx-a' if i in (4, 5) else 'bx'
        o.append(f'<rect x="{x}" y="54" width="{bw}" height="46" rx="4" class="{cls}"/>')
        o.append(f'<text x="{x+bw/2}" y="74" class="blab" text-anchor="middle">{name}</text>')
        o.append(f'<text x="{x+bw/2}" y="89" class="bsub" text-anchor="middle">{sub}</text>')
        if i < len(boxes) - 1:
            o.append(f'<line x1="{x+bw}" y1="77" x2="{x+bw+gap-2}" y2="77" class="ar" '
                     f'marker-end="url(#cha)"/>')
        o.append(f'<circle cx="{x+bw/2}" cy="48" r="8" fill="none" stroke="{T3}" '
                 f'stroke-width="1"/>')
        o.append(f'<text x="{x+bw/2}" y="51.5" class="ctick" text-anchor="middle">{i+1}</text>')
    o.append('<text x="14" y="40" class="bsub">文本</text>')
    o.append(f'<text x="{x0+6*(bw+gap)-4}" y="77" class="bsub">波形</text>')
    o.append(f'<text x="14" y="128" class="blab">这一段坏掉时，你听到的是：</text>')
    for i, (_, _, err) in enumerate(boxes):
        y = 148 + i * 18
        o.append(f'<circle cx="21" cy="{y-4}" r="7.5" fill="none" stroke="{T3}" '
                 f'stroke-width="1"/>')
        o.append(f'<text x="21" y="{y-0.5}" class="ctick" text-anchor="middle">{i+1}</text>')
        o.append(f'<text x="36" y="{y}" class="bsub">{err}</text>')
    o.append('<line x1="14" y1="268" x2="686" y2="268" class="grid"/>')
    o.append('<text x="14" y="288" class="arlab">'
             '<tspan font-weight="600">前四段是"读成什么"，后两段是"听起来怎么样"</tspan>。'
             '前四段错了是内容错误，用户会当成产品 bug；</text>')
    o.append('<text x="14" y="306" class="arlab">'
             '后两段错了是音质问题，用户会说"机器味重"。'
             '两类问题的定位方法、评测指标、负责的团队通常都不一样。</text>')
    o.append('<text x="14" y="326" class="arlab" fill="var(--s2)">'
             '端到端模型把这六段合成一个黑盒——好处是联合优化，'
             '代价是<tspan font-weight="600">出错时你不知道该查哪一段</tspan>。</text>')
    return svg(W, H, o, 'TTS 完整链路的六个环节：文本归一化、字音转换、韵律、时长、'
                        '声学模型、声码器，以及每一段坏掉时听到的具体症状', 'chart diag')


# ══════════════════════════════════════════════════════════════
def fig_peel():
    W, H = 700, 400
    o = ['<text x="10" y="18" class="ct">同一句话读 %d 遍，'
         '<tspan font-weight="700">不确定性藏在哪儿</tspan>'
         '<tspan class="cu"> · 剥掉时长，再剥掉基频，看还剩多少</tspan></text>'
         % S['read']['n']]
    AX, AY, AW, AH = 52, 76, 300, 168
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 跨读法的方差，一层层剥</text>')
    o.append(f'<text x="{AX}" y="{AY-15}" class="bsub" fill="{T3}">'
             f'纵轴：同一个时频点在 {S["read"]["n"]} 种读法之间的方差（相对值）</text>')
    for v in (0, 25, 50, 75, 100):
        y = AY + (100 - v) / 100 * AH
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{AX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}%</text>')
    cols = [C2, C1, C3]
    n = len(S['peel'])
    bw = AW / n * 0.46
    for i, p in enumerate(S['peel']):
        x = AX + (i + 0.5) / n * AW - bw / 2
        h = p['var_pct'] / 100 * AH
        o.append(f'<rect x="{x:.1f}" y="{AY+AH-h:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                 f'rx="3" fill="{cols[i]}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+bw/2:.1f}" y="{AY+AH-h-8:.1f}" class="bsub" fill="{cols[i]}" '
                 f'text-anchor="middle" font-weight="600">{p["var_pct"]:.1f}%</text>')
        lab = p['tag'].replace(' + ', '<tspan dy="12" x="%.1f"> + </tspan>' % (x + bw / 2))
        o.append(f'<text x="{x+bw/2:.1f}" y="{AY+AH+16:.1f}" class="ctick" '
                 f'text-anchor="middle">{p["tag"]}</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+40}" class="bsub" fill="{C2}">'
             f'→ 时长一项就解释了 {S["explain"]["dur"]:.1f}%，基频再解释 {S["explain"]["f0"]:.1f}%</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+56}" class="bsub" fill="{T3}">'
             f'基频占比这么小，是因为 80 维梅尔谱本来就看不清谐波（见 16 节）</text>')

    BX, BY, BW, BH = 430, 76, 240, 168
    o.append(f'<text x="{BX}" y="{BY-30}" class="blab">② 用 L2 训出来的东西长什么样</text>')
    o.append(f'<text x="{BX}" y="{BY-15}" class="bsub" fill="{T3}">'
             f'纵轴：谱包络的峰谷对比度（越高细节越多）</text>')
    L = S['loss']
    items = [('真实读法', L['real_ct'], C3), ('L1', L['l1_ct'], C1),
             ('L2', L['l2_ct'], C2), ('L2+GV', S['gvc']['ct'], T3)]
    hi = max(v for _, v, _ in items) * 1.18
    for v in (0.0, 0.3, 0.6, 0.9):
        y = BY + (hi - v) / hi * BH
        o.append(f'<line x1="{BX}" y1="{y:.1f}" x2="{BX+BW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{BX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v:.1f}</text>')
    bw2 = BW / len(items) * 0.5
    for i, (nm, v, c) in enumerate(items):
        x = BX + (i + 0.5) / len(items) * BW - bw2 / 2
        h = v / hi * BH
        o.append(f'<rect x="{x:.1f}" y="{BY+BH-h:.1f}" width="{bw2:.1f}" height="{h:.1f}" '
                 f'rx="3" fill="{c}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+bw2/2:.1f}" y="{BY+BH-h-7:.1f}" class="bsub" fill="{c}" '
                 f'text-anchor="middle" font-weight="600">{v:.3f}</text>')
        o.append(f'<text x="{x+bw2/2:.1f}" y="{BY+BH+16:.1f}" class="ctick" '
                 f'text-anchor="middle">{nm}</text>')
    yr = BY + (hi - L['real_ct']) / hi * BH
    o.append(f'<line x1="{BX}" y1="{yr:.1f}" x2="{BX+BW}" y2="{yr:.1f}" stroke="{C3}" '
             f'stroke-width="1.1" stroke-dasharray="4 3" stroke-opacity="0.6"/>')
    o.append(f'<text x="{BX}" y="{BY+BH+40}" class="bsub" fill="{T3}">'
             f'GV 补偿把数字拉回去了，但放大的是被平均糊掉的形状</text>')

    o.append('<line x1="14" y1="300" x2="686" y2="300" class="grid"/>')
    o.append('<text x="14" y="320" class="arlab">'
             '左图是 <tspan font-weight="600">FastSpeech 那一系为什么成立</tspan>：'
             '把时长从"要靠 L2 猜"改成"先预测、再当条件"，九成的不确定性就没了。</text>')
    o.append('<text x="14" y="338" class="arlab">'
             '右图是 <tspan font-weight="600">为什么剩下那一成还得靠 GAN / 流 / 扩散</tspan>：'
             'L2 的最优解是条件均值，而条件均值不是任何一句真话。</text>')
    o.append(f'<text x="14" y="358" class="arlab" fill="{C2}">'
             f'L2 把对比度从 {L["real_ct"]:.3f} 压到 {L["l2_ct"]:.3f}（掉 '
             f'{(1-L["l2_ct"]/L["real_ct"])*100:.0f}%），L1 好一些但病根没动——'
             f'中位数同样是一个点。</text>')
    o.append(f'<text x="14" y="376" class="arlab" fill="{T3}">'
             f'全局方差：L2 {L["l2_gv"]:+.2f} dB，L1 {L["l1_gv"]:+.2f} dB，'
             f'真实读法为 0 dB 基准。</text>')
    return svg(W, H, o, '两张图：左边是把时长和基频从不确定性里剥出去之后方差只剩百分之八，'
                        '右边是 L2 损失让谱包络对比度下降三成八')


# ══════════════════════════════════════════════════════════════
def fig_poly():
    W, H = 700, 384
    o = ['<text x="10" y="18" class="ct">多音字：'
         '<tspan font-weight="700">字表里两成，真实文本里四成</tspan>'
         '<tspan class="cu"> · 语料 = pypinyin 的 %d 条人工标注词条</tspan></text>'
         % G['dict']['phrases']]
    AX, AY, AW, AH = 52, 74, 176, 160
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 谁更容易是多音字</text>')
    o.append(f'<text x="{AX}" y="{AY-15}" class="bsub" fill="{T3}">纵轴：多音字占比</text>')
    for v in (0, 10, 20, 30, 40):
        y = AY + (45 - v) / 45 * AH
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{AX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}%</text>')
    for i, (nm, v, c) in enumerate([('字表里的字', G['char_level']['poly_pct'], C1),
                                    ('文本里的字位', G['token_level']['poly_pct'], C2)]):
        x = AX + (i + 0.5) / 2 * AW - 26
        h = v / 45 * AH
        o.append(f'<rect x="{x:.1f}" y="{AY+AH-h:.1f}" width="52" height="{h:.1f}" rx="3" '
                 f'fill="{c}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+26:.1f}" y="{AY+AH-h-7:.1f}" class="bsub" fill="{c}" '
                 f'text-anchor="middle" font-weight="600">{v:.1f}%</text>')
        o.append(f'<text x="{x+26:.1f}" y="{AY+AH+16:.1f}" class="ctick" '
                 f'text-anchor="middle">{nm}</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+40}" class="bsub" fill="{T3}">'
             f'常用字更容易有多个读音，</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+55}" class="bsub" fill="{T3}">'
             f'所以它比"两成"难缠得多</text>')

    BX, BY, BW, BH = 288, 74, 180, 160
    o.append(f'<text x="{BX}" y="{BY-30}" class="blab">② 三种做法的准确率</text>')
    o.append(f'<text x="{BX}" y="{BY-15}" class="bsub" fill="{T3}">纵轴：字级正确率</text>')
    lo, hi = 92.0, 100.5
    for v in (92, 94, 96, 98, 100):
        y = BY + (hi - v) / (hi - lo) * BH
        o.append(f'<line x1="{BX}" y1="{y:.1f}" x2="{BX+BW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{BX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}%</text>')
    P = G['prior']
    items = [('单字表\n第一个音', G['naive']['char_acc'], C2),
             ('频率先验', P['char_acc'], C1),
             ('词典匹配', 100.0, C3)]
    for i, (nm, v, c) in enumerate(items):
        x = BX + (i + 0.5) / 3 * BW - 20
        h = (v - lo) / (hi - lo) * BH
        o.append(f'<rect x="{x:.1f}" y="{BY+BH-h:.1f}" width="40" height="{h:.1f}" rx="3" '
                 f'fill="{c}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+20:.1f}" y="{BY+BH-h-7:.1f}" class="bsub" fill="{c}" '
                 f'text-anchor="middle" font-weight="600">{v:.2f}</text>')
        for j, ln in enumerate(nm.split('\n')):
            o.append(f'<text x="{x+20:.1f}" y="{BY+BH+16+j*12:.1f}" class="ctick" '
                     f'text-anchor="middle">{ln}</text>')
    o.append(f'<text x="{BX}" y="{BY+AH+52}" class="bsub" fill="{C2}">'
             f'但整条词组全对只有 {P["phrase_acc"]:.1f}%——</text>')
    o.append(f'<text x="{BX}" y="{BY+AH+67}" class="bsub" fill="{C2}">'
             f'字级 95% 不等于句子对</text>')

    CX, CY, CW, CH = 528, 74, 144, 160
    o.append(f'<text x="{CX}" y="{CY-30}" class="blab">③ 错误集中在少数字上</text>')
    o.append(f'<text x="{CX}" y="{CY-15}" class="bsub" fill="{T3}">横轴：按错误数排序的字</text>')
    k50, k80, npoly = G['tail']['k50'], G['tail']['k80'], G['tail']['poly_chars']
    pts = [(0, 0), (k50, 50), (k80, 80), (npoly, 100)]
    fx = lambda v: CX + v / npoly * CW
    fy = lambda v: CY + (100 - v) / 100 * CH
    for v in (0, 50, 80, 100):
        o.append(f'<line x1="{CX}" y1="{fy(v):.1f}" x2="{CX+CW}" y2="{fy(v):.1f}" class="grid"/>')
        o.append(f'<text x="{CX-5}" y="{fy(v)+3.5:.1f}" class="ctick" text-anchor="end">{v}%</text>')
    o.append('<polyline points="' + ' '.join('%.1f,%.1f' % (fx(a), fy(b)) for a, b in pts)
             + f'" fill="none" stroke="{C1}" stroke-width="2.3"/>')
    for a, b, lab in ((k50, 50, '前 %d 个字' % k50), (k80, 80, '前 %d 个' % k80)):
        o.append(f'<circle cx="{fx(a):.1f}" cy="{fy(b):.1f}" r="3.4" fill="{C3}"/>')
        o.append(f'<text x="{fx(a)+6:.1f}" y="{fy(b)+4:.1f}" class="bsub" fill="{C3}">{lab}</text>')
    o.append(f'<text x="{CX+CW/2:.0f}" y="{CY+CH+18}" class="cax" text-anchor="middle">'
             f'{npoly} 个多音字</text>')
    o.append(f'<text x="{CX}" y="{CY+CH+40}" class="bsub" fill="{T3}">长尾没那么长——</text>')
    o.append(f'<text x="{CX}" y="{CY+CH+55}" class="bsub" fill="{T3}">值得逐字治</text>')

    o.append('<line x1="14" y1="296" x2="686" y2="296" class="grid"/>')
    o.append(f'<text x="14" y="316" class="arlab">'
             f'多音字字位的平均条件熵是 <tspan font-weight="600">{G["entropy_bits"]:.3f} bit</tspan>——'
             f'这就是上下文必须补上的信息量。词典能解决绝大部分，</text>')
    o.append('<text x="14" y="334" class="arlab">'
             '剩下的要靠句法和语义：“他<tspan font-weight="600">还</tspan>钱了”和'
             '“他<tspan font-weight="600">还</tspan>在”，光看词不够。</text>')
    o.append(f'<text x="14" y="354" class="arlab" fill="{T3}">'
             f'注意这份语料是词表加权，不是真实文本加权。真实文本里“的、了、着、地”'
             f'这类高频虚词占比更高，多音字位只会更多。</text>')
    o.append(f'<text x="14" y="372" class="arlab" fill="{C2}">'
             f'“一”有 {G["sandhi"]["yi_alt_pct"]:.1f}% 的出现不是本调，'
             f'相邻两字都是三声的情形占 {G["sandhi"]["t3t3_pct"]:.2f}%——变调是规则，不在拼音标注里。</text>')
    return svg(W, H, o, '三张图：字表里两成是多音字但文本里四成，三种基线的准确率，'
                        '以及错误高度集中在少数几十个字上')


OUT['chain'] = fig_chain()
OUT['peel'] = fig_peel()
OUT['poly'] = fig_poly()
json.dump(OUT, open('figs_a.json', 'w'), ensure_ascii=False)
print('figs_a.json:', {k: len(v) for k, v in OUT.items()})
