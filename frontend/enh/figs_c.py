#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《单通道增强手册》图 10–14：输出参数化、泛化消融、三档预算、保真与像真、翻车点代价。"""
import json
import numpy as np

OU = json.load(open('demo_out.json'))
GE = json.load(open('demo_gen.json'))
TI = json.load(open('demo_tier.json'))
PD = json.load(open('demo_pd.json'))
GA = json.load(open('demo_gain.json'))
DD = json.load(open('demo_dd.json'))
PH = json.load(open('demo_phase.json'))
NN = json.load(open('demo_nn.json'))
EV = json.load(open('demo_eval.json'))

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
def fig_out():
    W, H = 700, 486
    o = ['<text x="10" y="18" class="ct">输出参数化：'
         '<tspan font-weight="700">天花板最高的那个，兑现得最少</tspan>'
         '<tspan class="cu"> · 同一个网络容量，只换输出形式</tspan></text>']

    # ① 上界 vs 实得
    AX, AY, AW = 206, 74, 300
    ach = OU['achieved']
    mx = 16.0
    fx = lambda v: AX + min(v, mx) / mx * AW
    o.append(f'<text x="16" y="{AY-28}" class="blab">① 上界（知道干净语音）与实得（固定容量回归）</text>')
    o.append(f'<text x="{AX}" y="{AY-10}" class="ctick" fill="{T3}">'
             f'分段信噪比（dB）→</text>')
    for i, r in enumerate(ach):
        y = AY + 14 + i * 32
        o.append(f'<text x="{AX-10}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'{r["tag"]}</text>')
        cap = min(r['ceiling'], mx)
        o.append(f'<rect x="{AX}" y="{y-8:.1f}" width="{fx(cap)-AX:.1f}" height="16" '
                 f'rx="2" fill="{C2}" fill-opacity="0.26"/>')
        o.append(f'<rect x="{AX}" y="{y-8:.1f}" width="{fx(r["seen"]["segsnr"])-AX:.1f}" '
                 f'height="16" rx="2" fill="{C1}" fill-opacity="0.92"/>')

        if r['ceiling'] >= mx:
            o.append(f'<text x="{AX+AW-96}" y="{y+4:.1f}" class="ctick" fill="{C2}">'
                     f'上界＝完美重建</text>')
        else:
            o.append(f'<text x="{fx(cap)+6:.1f}" y="{y+4:.1f}" class="ctick" '
                     f'fill="{C2}">{r["ceiling"]:.2f}</text>')
        col = HOT if r['realized'] < 40 else T2
        o.append(f'<text x="{AX-10}" y="{y+16}" class="ctick" text-anchor="end" '
                 f'fill="{C1}">实得 {r["seen"]["segsnr"]:.2f}</text>')
        o.append(f'<text x="{AX+AW+76}" y="{y+4:.1f}" class="ctick" '
                 f'fill="{col}">兑现 {r["realized"]:.1f}%</text>')

    # ② 理想幅度掩码超出 [0,1] 的比例
    BY = 268
    o.append(f'<text x="16" y="{BY}" class="blab">'
             f'② 理想幅度掩码 |S|/|Y| 有多少落在 [0,1] 外（以及钳掉它的代价）</text>')
    BX, BW, BH = 60, 250, 80
    cl, cc = OU['clip'], OU['clip_cost']
    xs = [r['snr'] for r in cl]
    fx2 = lambda v: BX + (v - xs[0]) / (xs[-1] - xs[0]) * BW
    fy2 = lambda v: BY + 20 + (25.0 - v) / 25.0 * BH
    ygrid(o, BX, BW, [0, 10, 20], fy2, '%g', '%')
    poly(o, [(fx2(r['snr']), fy2(r['frac_gt1'])) for r in cl], C2)
    for r in cl:
        o.append(f'<circle cx="{fx2(r["snr"]):.1f}" cy="{fy2(r["frac_gt1"]):.1f}" r="3" '
                 f'fill="{C2}"/>')
    for v in xs:
        o.append(f'<text x="{fx2(v):.1f}" y="{BY+20+BH+14}" class="ctick" '
                 f'text-anchor="middle">{neg("%g" % v)}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+20+BH+30}" class="cax" '
             f'text-anchor="middle">输入信噪比（dB）</text>')
    o.append(f'<text x="{BX}" y="{BY+16}" class="ctick" fill="{C2}">超过 1 的格子占比</text>')
    DX, DW = 400, 180
    fy3 = lambda v: BY + 20 + (1.3 - v) / 1.3 * BH
    ygrid(o, DX, DW, [0, 0.5, 1.0], fy3, '%.1f', ' dB')
    fx3 = lambda v: DX + (v - xs[0]) / (xs[-1] - xs[0]) * DW
    poly(o, [(fx3(r['snr']), fy3(r['cost_db'])) for r in cc], HOT)
    for r in cc:
        o.append(f'<circle cx="{fx3(r["snr"]):.1f}" cy="{fy3(r["cost_db"]):.1f}" r="3" '
                 f'fill="{HOT}"/>')
    for v in xs:
        o.append(f'<text x="{fx3(v):.1f}" y="{BY+20+BH+14}" class="ctick" '
                 f'text-anchor="middle">{neg("%g" % v)}</text>')
    o.append(f'<text x="{DX}" y="{BY+16}" class="ctick" fill="{HOT}">钳到 1 的代价</text>')

    c0 = [r for r in OU['clip'] if r['snr'] == 0.0][0]
    c15 = [r for r in OU['clip_cost'] if r['snr'] == 15.0][0]
    cm5 = [r for r in OU['clip_cost'] if r['snr'] == -5.0][0]
    foot(o, H, [
        ('我原以为"有界掩码不会有损失，因为理想掩码本来就在 [0,1] 里"。错了：'
         '0 dB 时有 <b>%.1f%%</b> 的格子超过 1——噪声和语音反相叠加的那些。'
         % c0['frac_gt1'], None),
        ('但第二步也和我想的不一样：钳掉它几乎不花钱，而且<b>代价随信噪比上升</b>——'
         '−5 dB 只 %.2f dB，15 dB 才 %.2f dB。低信噪比时这个上界基本是免费的。'
         % (cm5['cost_db'], c15['cost_db']), C2),
        ('真正的落差在右边那一栏：复数掩码的上界是完美重建，'
         '兑现率只有 <b>%.1f%%</b>；有界的 IRM 上界最低，兑现 <b>%.1f%%</b>，实得最高。'
         % (ach[-1]['realized'], ach[0]['realized']), HOT),
    ], y0=432)
    return svg(W, H, o, '四种输出参数化的理论上界与固定容量网络的实得，'
                        '以及理想幅度掩码超出 [0,1] 的比例')


# ══════════════════════════════════════════════════════════════
def fig_gen():
    W, H = 700, 440
    o = ['<text x="10" y="18" class="ct">泛化：'
         '<tspan font-weight="700">"这个条件本身更难"比"训练没盖住"贵得多</tspan>'
         '<tspan class="cu"> · 一维一维地消融，其余维不动</tspan></text>']
    ab = GE['ablate']
    AX, AY, AW = 190, 70, 210
    mx = max(max(abs(r['drop']), abs(r['stress_cost'])) for r in ab) * 1.15
    o.append(f'<text x="16" y="{AY-28}" class="blab">'
             f'① 每一维：训练没盖住的代价 vs 这个条件本身的代价（dB）</text>')
    o.append(f'<text x="{AX}" y="{AY-10}" class="ctick" fill="{C1}">漏掉这一维</text>')
    o.append(f'<text x="{AX+230}" y="{AY-10}" class="ctick" fill="{HOT}">失配本身</text>')
    f1 = lambda v: AX + max(v, 0) / mx * (AW * 0.44)
    f2 = lambda v: AX + 236 + max(v, 0) / mx * (AW * 0.9)
    for i, r in enumerate(ab):
        y = AY + 16 + i * 26
        o.append(f'<text x="{AX-10}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'{r["axis"]}</text>')
        w1 = f1(r['drop']) - AX
        o.append(f'<rect x="{AX}" y="{y-6:.1f}" width="{max(w1,1.0):.1f}" height="12" '
                 f'rx="2" fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<text x="{AX+max(w1,1.0)+5:.1f}" y="{y+4:.1f}" class="ctick" '
                 f'fill="{C1}">{r["drop"]:+.2f}</text>')
        w2 = f2(r['stress_cost']) - (AX + 236)
        o.append(f'<rect x="{AX+236}" y="{y-6:.1f}" width="{max(w2,1.0):.1f}" height="12" '
                 f'rx="2" fill="{HOT}" fill-opacity="0.82"/>')
        o.append(f'<text x="{AX+236+max(w2,1.0)+5:.1f}" y="{y+4:.1f}" class="ctick" '
                 f'fill="{HOT}">{r["stress_cost"]:+.2f}</text>')

    BY = 254
    am = GE['amount']
    o.append(f'<text x="16" y="{BY}" class="blab">'
             f'② 同一个测试条件：加数据量 vs 加噪声种类</text>')
    CX, CW = 230, 190
    mx2 = max(max(r['one'], r['four']) for r in am) * 1.2
    gx = lambda v: CX + max(v, 0) / mx2 * CW
    for i, r in enumerate(am):
        y = BY + 22 + i * 32
        o.append(f'<text x="{CX-10}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'{r["nset"]} 段 × 3 s</text>')
        o.append(f'<rect x="{CX}" y="{y-9:.1f}" width="{gx(r["one"])-CX:.1f}" height="8" '
                 f'rx="2" fill="{C1}" fill-opacity="0.85"/>')
        o.append(f'<text x="{gx(r["one"])+5:.1f}" y="{y-2:.1f}" class="ctick" '
                 f'fill="{C1}">一种噪声 {r["one"]:+.2f}</text>')
        o.append(f'<rect x="{CX}" y="{y+2:.1f}" width="{gx(r["four"])-CX:.1f}" height="8" '
                 f'rx="2" fill="{C2}" fill-opacity="0.9"/>')
        o.append(f'<text x="{gx(r["four"])+5:.1f}" y="{y+9:.1f}" class="ctick" '
                 f'fill="{C2}">四种噪声 {r["four"]:+.2f}</text>')
    an = GE['amount_note']
    o.append(f'<text x="{CX}" y="{BY+22+2*32+8}" class="ctick" fill="{T3}">'
             f'数据量翻 {an["ratio"]} 倍 {an["one_gain_4x"]:+.2f} dB　·　'
             f'换成四种噪声 {an["div_gain"]:+.2f} dB</text>')

    top = ab[0]
    foot(o, H, [
        ('左边两栏是同一个测试条件上的两件事。漏掉"%s"这一维要 <b>%.2f dB</b>，'
         '而这个条件<b>本身</b>比基准档难 <b>%.2f dB</b>——后者是前者的 %.1f 倍。'
         % (top['axis'], top['drop'], top['stress_cost'],
            top['stress_cost'] / max(top['drop'], 1e-9)), None),
        ('也就是说：加数据能买回来的只有窄的那一条。'
         '<b>"把 babble 加进训练集"不会让 babble 变得和 pink 一样好处理。</b>', HOT),
        ('下半栏是老结论的定量版：同样的测试条件，'
         '把数据量翻 %d 倍值 %.2f dB，而把噪声从一种换成四种值 %.2f dB。'
         % (an['ratio'], an['one_gain_4x'], an['div_gain']), C2),
    ], y0=386)
    return svg(W, H, o, '六个数据维度各自的覆盖代价与失配代价，以及数据量与多样性的对比')


# ══════════════════════════════════════════════════════════════
def fig_tier():
    W, H = 700, 456
    t = TI['tiers']
    o = ['<text x="10" y="18" class="ct">三档预算：'
         '<tspan font-weight="700">延迟最紧的那一档，算力最贵、能拿到的最少</tspan>'
         '<tspan class="cu"> · 预算先定窗长，窗长再定一切</tspan></text>']
    AY = 62
    cols = [60, 250, 440]
    for i, r in enumerate(t):
        X = cols[i]
        o.append(f'<text x="{X}" y="{AY}" class="blab">{r["name"]}</text>')
        rows = [('延迟预算', '%.0f ms' % r['budget_ms']),
                ('窗 / 帧移', '%d / %d 点' % (r['nfft'], r['hop'])),
                ('窗长', '%.1f ms' % r['win_ms']),
                ('频率分辨率', '%.0f Hz' % r['df_hz']),
                ('前瞻', '%d 帧（%.0f ms）' % (r['look'], r['look_ms'])),
                ('实际延迟', '%.1f ms' % r['total_ms']),
                ('算力', '%.2f MMAC/s' % r['mmac_s']),
                ('功耗 @50 pJ', '%.2f mW' % r['mw50']),
                ('分得开谐波', '是' if r['resolves_f0'] else '否')]
        for j, (a, b) in enumerate(rows):
            y = AY + 20 + j * 17
            o.append(f'<text x="{X}" y="{y}" class="ctick" fill="{T3}">{a}</text>')
            col = HOT if (a == '分得开谐波' and not r['resolves_f0']) else T2
            o.append(f'<text x="{X+170}" y="{y}" class="ctick" text-anchor="end" '
                     f'fill="{col}">{b}</text>')

    BY = 250
    o.append(f'<text x="16" y="{BY}" class="blab">'
             f'拿到的增益（输入 5 dB，训练见过的噪声）</text>')
    BX, BW = 150, 300
    mx = max(r['gain_nn'] for r in t) * 1.25
    fx = lambda v: BX + v / mx * BW
    for i, r in enumerate(t):
        y = BY + 24 + i * 30
        o.append(f'<text x="{BX-10}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'{r["name"]}</text>')
        o.append(f'<rect x="{BX}" y="{y-9:.1f}" width="{fx(r["gain_classic"])-BX:.1f}" '
                 f'height="8" rx="2" fill="{C2}" fill-opacity="0.85"/>')
        o.append(f'<text x="{fx(r["gain_classic"])+5:.1f}" y="{y-2:.1f}" class="ctick" '
                 f'fill="{C2}">经典 {r["gain_classic"]:+.2f} dB</text>')
        o.append(f'<rect x="{BX}" y="{y+2:.1f}" width="{fx(r["gain_nn"])-BX:.1f}" '
                 f'height="8" rx="2" fill="{C1}" fill-opacity="0.92"/>')
        o.append(f'<text x="{fx(r["gain_nn"])+5:.1f}" y="{y+9:.1f}" class="ctick" '
                 f'fill="{C1}">网络 {r["gain_nn"]:+.2f} dB</text>')

    ear, call, meet = t
    foot(o, H, [
        ('耳机那一档的窗只有 %.1f ms，Δf %.0f Hz——分不开 %g Hz 的谐波'
         '（要 %.1f ms 以上）。经典法只拿到 %+.2f dB。'
         % (ear['win_ms'], ear['df_hz'], TI['summary']['f0_lo'],
            ear['need_win_ms'], ear['gain_classic']), None),
        ('<b>但网络在同一个窗下拿到 %+.2f dB</b>——短窗丢掉的那部分，'
         '它用时间上下文补回了一些。这是神经方法在低延迟档最硬的理由。'
         % ear['gain_nn'], C1),
        ('而算力是反的：帧移越短、帧率越高，%.2f MMAC/s vs %.2f MMAC/s，'
         '<b>差 %.1f 倍</b>。最省延迟的一档最耗电。'
         % (ear['mmac_s'], meet['mmac_s'], TI['summary']['mmac_spread']), HOT),
        ('到了会议那一档，两者的分段信噪比打平（%+.2f vs %+.2f），差别全在 LSD'
         '（%.2f vs %.2f）——这一档卡的不是延迟也不是算力，是你要哪个指标。'
         % (meet['gain_nn'], meet['gain_classic'], meet['nn']['lsd'],
            meet['classic']['lsd']), None),
    ], y0=368)
    return svg(W, H, o, '三档延迟预算下的窗长、频率分辨率、算力与实得增益')


# ══════════════════════════════════════════════════════════════
def fig_pd():
    W, H = 700, 456
    sw = PD['sweep']
    o = ['<text x="10" y="18" class="ct">保真与像真：'
         '<tspan font-weight="700">把被削掉的填回去，六个指标里五个变好</tspan>'
         '<tspan class="cu"> · 只有波形保真那一个变差</tspan></text>']
    AX, AY, AW, AH = 54, 64, 250, 130
    bs = [r['beta'] for r in sw]
    fx = lambda v: AX + v / 1.0 * AW
    lo, hi = 5.8, 8.0
    fy = lambda v: AY + (hi - v) / (hi - lo) * AH
    o.append(f'<text x="16" y="{AY-28}" class="blab">① 波形保真：分段信噪比（越高越好）</text>')
    ygrid(o, AX, AW, [6.0, 6.5, 7.0, 7.5, 8.0], fy, '%.1f')
    poly(o, [(fx(r['beta']), fy(r['segsnr'])) for r in sw], HOT)
    for r in sw:
        o.append(f'<circle cx="{fx(r["beta"]):.1f}" cy="{fy(r["segsnr"]):.1f}" r="3" '
                 f'fill="{HOT}"/>')
    # ② 长时谱距 + STOI*
    EX = 400
    o.append(f'<text x="{EX-18}" y="{AY-28}" class="blab">'
             f'② 像不像真的：长时谱距（越低越好）</text>')
    lo2, hi2 = 2.5, 6.0
    fy2 = lambda v: AY + (hi2 - v) / (hi2 - lo2) * AH
    fx2 = lambda v: EX + v / 1.0 * 240
    ygrid(o, EX, 240, [3, 4, 5, 6], fy2, '%g', ' dB')
    poly(o, [(fx2(r['beta']), fy2(r['ltas'])) for r in sw], C2)
    for r in sw:
        o.append(f'<circle cx="{fx2(r["beta"]):.1f}" cy="{fy2(r["ltas"]):.1f}" r="3" '
                 f'fill="{C2}"/>')
    for ax, w in ((AX, AW), (EX, 240)):
        for v in (0.0, 0.5, 1.0):
            x = ax + v * w
            o.append(f'<text x="{x:.1f}" y="{AY+AH+16}" class="ctick" '
                     f'text-anchor="middle">{v:.1f}</text>')
        o.append(f'<text x="{ax+w/2:.0f}" y="{AY+AH+32}" class="cax" '
                 f'text-anchor="middle">填充强度 β（0＝纯预测式，1＝填到底）</text>')

    # ③ 两种错误
    BY = 252
    o.append(f'<text x="16" y="{BY}" class="blab">'
             f'③ 两种错误：删掉了 vs 编出来了</text>')
    BX, BW, BH2 = 54, 250, 76
    o.append(f'<text x="{BX}" y="{BY+15}" class="ctick" fill="{T3}">'
             f'实线读左轴 0–35%，虚线读右轴 0–0.5%——两者差两个数量级</text>')
    fy3 = lambda v: BY + 30 + (35.0 - v) / 35.0 * BH2
    ygrid(o, BX, BW, [0, 10, 20, 30], fy3, '%g', '%')
    poly(o, [(fx(r['beta']) - AX + BX, fy3(r['miss'])) for r in sw], C1)
    o.append(f'<text x="{BX+BW+6}" y="{fy3(sw[-1]["miss"]):.1f}" class="ctick" '
             f'fill="{C1}">删掉了</text>')
    fy4 = lambda v: BY + 30 + (0.5 - v) / 0.5 * BH2
    poly(o, [(fx(r['beta']) - AX + BX, fy4(r['hall'])) for r in sw], HOT, dash='4 3')
    o.append(f'<text x="{BX+BW+6}" y="{fy4(sw[-1]["hall"]):.1f}" class="ctick" '
             f'fill="{HOT}">编出来了</text>')
    for v in (0.0, 0.5, 1.0):
        o.append(f'<text x="{BX+v*BW:.1f}" y="{BY+30+BH2+14}" class="ctick" '
                 f'text-anchor="middle">{v:.1f}</text>')

    # ④ 三种失效方式
    mo = PD['modes']
    o.append(f'<text x="430" y="{BY}" class="blab">④ 三种失效方式</text>')
    for i, r in enumerate(mo):
        y = BY + 20 + i * 24
        o.append(f'<text x="430" y="{y}" class="ctick" fill="{T3}">{r["tag"]}</text>')
        o.append(f'<text x="676" y="{y}" class="ctick" text-anchor="end" fill="{T2}">'
                 f'删 {r["miss"]:.1f}% · 编 {r["hall"]:.2f}%</text>')
        o.append(f'<text x="430" y="{y+11}" class="ctick" fill="{T2}">'
                 f'　SegSNR {r["segsnr"]:.2f} dB · STOI* {r["stoi"]:.3f}</text>')

    s = PD['summary']
    b0, b1 = sw[0], sw[-1]
    foot(o, H, [
        ('我原以为"填回去只是化妆，客观指标一定变差"。只对了一个指标：'
         'SegSNR 掉 %.2f dB，而 LSD %.2f→%.2f、STOI* %.3f→%.3f、'
         '长时谱距 %.2f→%.2f dB，全变好。'
         % (s['seg_cost'], b0['lsd'], b1['lsd'], b0['stoi'], b1['stoi'],
            b0['ltas'], b1['ltas']), None),
        ('代价在第三栏那条虚线上："编出来"从 %.2f%% 涨到 %.2f%%。绝对值很小，'
         '但<b>这类错误是预测式方法根本不会犯的</b>，而没有指标在看它。'
         % (s['hall_b0'], s['hall_b1']), HOT),
    ], y0=414)
    return svg(W, H, o, '填充强度从预测式到生成式的指标变化，以及删掉与编出来两类错误')


# ══════════════════════════════════════════════════════════════
def fig_traps():
    W, H = 700, 470
    o = ['<text x="10" y="18" class="ct">十个翻车点，分两栏排：'
         '<tspan font-weight="700">以"倍"计的全是流程与口径，以 dB 计的全是算法参数</tspan>'
         '<tspan class="cu"> · 同一栏内单位一致，可以互比</tspan></text>']
    ev = EV['asv']
    ab0 = GE['ablate'][0]
    ratio = sorted([
        ('拿感知指标去调给机器听的增强',
         max(r['eer_matched'] for r in ev) / max(EV['asv_clean'], 1e-9), '19'),
        ('把"这个条件更难"当成"数据没盖住"',
         ab0['stress_cost'] / max(ab0['drop'], 1e-9), '17'),
        ('把"兑现率"当成"上界"',
         OU['achieved'][0]['realized'] / max(OU['achieved'][-1]['realized'], 1e-9), '14'),
        ('注册 / 训练数据没过同一条前端',
         ev[0]['eer_mismatch'] / max(ev[0]['eer_matched'], 1e-9), '19'),
    ], key=lambda x: -x[1])
    dbs = sorted([
        ('低信噪比时忽略相位（上界）',
         max(r['phase_worth'] for r in PH['mask']), '11'),
        ('过减因子一刀切',
         max(r['segsnr'] for r in GA['oversub'])
         - min(r['segsnr'] for r in GA['oversub']), '04'),
        ('低延迟档沿用长窗的直觉', TI['summary']['ear_vs_meet'], '20'),
        ('噪声估计跟不上突变', DD['est_by_noise'][-1]['cost'], '09'),
        ('判决引导的 α 用默认值不看信噪比',
         abs(DD['capture']['0.98']['thr_db'] - DD['capture']['0.9']['thr_db']), '08'),
    ], key=lambda x: -x[1])

    def panel(title, items, y0, unit, col, mx):
        o.append(f'<text x="16" y="{y0}" class="blab">{title}</text>')
        AX, AW = 290, 230
        fx = lambda v: AX + abs(v) / mx * AW
        for i, (name, v, secn) in enumerate(items):
            y = y0 + 24 + i * 26
            o.append(f'<text x="{AX-72}" y="{y+4}" class="bsub" text-anchor="end">'
                     f'{name}</text>')
            o.append(f'<text x="{AX-10}" y="{y+4}" class="ctick" text-anchor="end" '
                     f'fill="{T3}">{secn} 节</text>')
            o.append(f'<rect x="{AX}" y="{y-7:.1f}" width="{max(fx(v)-AX,1.5):.1f}" '
                     f'height="14" rx="2" fill="{col}" fill-opacity="0.88"/>')
            o.append(f'<text x="{fx(v)+6:.1f}" y="{y+4:.1f}" class="ctick" fill="{col}">'
                     f'{abs(v):.1f} {unit}</text>')

    panel('① 以"倍"计：下游错误率或代价被放大多少倍', ratio, 48, '×', HOT,
          max(v for _, v, _ in ratio) * 1.18)
    panel('② 以 dB 计：算法参数选错或选保守，损失多少', dbs, 186, 'dB', C2,
          max(v for _, v, _ in dbs) * 1.18)
    o.append(f'<text x="16" y="346" class="ctick" fill="{T3}">'
             f'另外两条不在这两种单位里：</text>')
    o.append(f'<text x="30" y="362" class="ctick" fill="{T3}">'
             f'只看一个客观指标 → 同一系统名次能跨 {EV["max_spread"]["n"]} 位（18 节）</text>')
    o.append(f'<text x="30" y="378" class="ctick" fill="{T3}">'
             f'忘了编解码 → 覆盖代价 {GE["ablate"][1]["drop"]:.2f} dB '
             f'＋ 失配代价 {GE["ablate"][1]["stress_cost"]:.2f} dB（17 节）</text>')
    foot(o, H, [
        ('<b>第一栏没有一条是"算法选得不对"</b>：信号链不一致、指标选错、'
         '把失配当成覆盖不足、把上界当成实得。它们的量级是"倍"。', None),
        ('第二栏才是算法本身，量级是 dB，而且最大的那条（%.1f dB）是<b>理论上界</b>，'
         '真正能动的远小于它。' % dbs[0][1], C2),
        ('<b>调参的上限很低，流程的上限很高。</b>'
         '这是这本书十个坑排下来最该带走的一句。', HOT),
    ], y0=414)
    return svg(W, H, o, '十个常见翻车点，按倍数类与 dB 类分两栏排序，各自标注对应章节')


OUT['out'] = fig_out()
OUT['gen'] = fig_gen()
OUT['tier'] = fig_tier()
OUT['pd'] = fig_pd()
OUT['traps'] = fig_traps()
json.dump(OUT, open('figs_c.json', 'w'), ensure_ascii=False)
print('figs_c.json:', {k: len(v) // 1024 for k, v in OUT.items()})
