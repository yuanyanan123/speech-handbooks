#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《TTS 合成手册》图 4–9：梅尔、对齐、流匹配、tokenizer、混叠、听测功效。"""
import json, math
import numpy as np
from figs_tts import C1, C2, C3, T3, T2, defs, svg

ME = json.load(open('demo_mel.json'))
AL = json.load(open('demo_align.json'))
FL = json.load(open('demo_flow.json'))
RQ = json.load(open('demo_rvq.json'))
VO = json.load(open('demo_voc.json'))
EV = json.load(open('demo_eval.json'))
OUT = {}


def grid(o, X, Y, W, H, vals, f2y, fmt='%g'):
    for v in vals:
        y = f2y(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+W}" y2="{y:.1f}" class="grid"/>')
        s = fmt % v
        if s.startswith('-'):
            s = '−' + s[1:]
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{s}</text>')


# ══════════════════════════════════════════════════════════════
def fig_mel():
    W, H = 700, 400
    o = ['<text x="10" y="18" class="ct">梅尔谱'
         '<tspan font-weight="700">丢掉的三样东西</tspan>'
         '<tspan class="cu"> · 22.05 kHz，nfft %d，hop %d，%d 维梅尔</tspan></text>'
         % (ME['cfg']['nfft'], ME['cfg']['hop'], ME['cfg']['nmel'])]
    # ① 谐波什么时候看不见
    AX, AY, AW, AH = 52, 78, 206, 158
    f0s = [90, 120, 200, 300]
    vals = [ME['harm']['f0_%d' % f] for f in f0s]
    hi = 5000.
    fy = lambda v: AY + (hi - v) / hi * AH
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 谐波从哪个频率起看不见</text>')
    o.append(f'<text x="{AX}" y="{AY-15}" class="bsub" fill="{T3}">'
             f'纵轴：一个梅尔带开始装进 &gt;1 根谐波的频率</text>')
    grid(o, AX, AY, AW, AH, [0, 1000, 2000, 3000, 4000, 5000], fy, '%d')
    bw = AW / len(f0s) * 0.5
    for i, (f0, v) in enumerate(zip(f0s, vals)):
        x = AX + (i + 0.5) / len(f0s) * AW - bw / 2
        h = v / hi * AH
        c = C2 if f0 == 120 else C1
        o.append(f'<rect x="{x:.1f}" y="{AY+AH-h:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                 f'rx="3" fill="{c}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+bw/2:.1f}" y="{AY+AH-h-7:.1f}" class="bsub" fill="{c}" '
                 f'text-anchor="middle" font-weight="600">{v:.0f}</text>')
        o.append(f'<text x="{x+bw/2:.1f}" y="{AY+AH+16:.1f}" class="ctick" '
                 f'text-anchor="middle">{f0}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'基频 F0（Hz）</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+54}" class="bsub" fill="{C2}">'
             f'男声 120 Hz：{ME["harm"]["f0_120"]:.0f} Hz 以上就只剩包络</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+69}" class="bsub" fill="{T3}">'
             f'7 kHz 处一个带里塞了 {ME["harm"]["bins_at_7k"]:.1f} 根谐波</text>')

    # ② Griffin-Lim
    BX, BY, BW, BH = 318, 78, 168, 158
    its = [0, 1, 3, 10, 32, 100]
    gy = lambda v: BY + (18 - v) / 18 * BH
    gx = lambda i: BX + i / (len(its) - 1) * BW
    o.append(f'<text x="{BX}" y="{BY-30}" class="blab">② 相位补不回来</text>')
    o.append(f'<text x="{BX}" y="{BY-15}" class="bsub" fill="{T3}">'
             f'纵轴：重建谱的一致性（dB，越高越好）</text>')
    grid(o, BX, BY, BW, BH, [0, 6, 12, 18], gy, '%d')
    pts = ' '.join('%.1f,%.1f' % (gx(i), gy(ME['gl'][str(k)])) for i, k in enumerate(its))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{C1}" stroke-width="2.3"/>')
    for i, k in enumerate(its):
        o.append(f'<circle cx="{gx(i):.1f}" cy="{gy(ME["gl"][str(k)]):.1f}" r="2.8" fill="{C1}"/>')
        o.append(f'<text x="{gx(i):.1f}" y="{BY+BH+16}" class="ctick" text-anchor="middle">{k}</text>')
    mv = ME['melinv']
    for i, k in ((4, 32), (5, 100)):
        o.append(f'<circle cx="{gx(i):.1f}" cy="{gy(mv["gl_%d" % k]):.1f}" r="2.8" fill="{C2}"/>')
    o.append(f'<line x1="{gx(4):.1f}" y1="{gy(mv["gl_32"]):.1f}" x2="{gx(5):.1f}" '
             f'y2="{gy(mv["gl_100"]):.1f}" stroke="{C2}" stroke-width="2.3"/>')
    o.append(f'<text x="{gx(2.2):.1f}" y="{gy(ME["gl"]["100"])-8:.1f}" class="bsub" fill="{C1}">'
             f'从真实幅度谱出发</text>')
    o.append(f'<text x="{gx(1.6):.1f}" y="{gy(mv["gl_100"])+14:.1f}" class="bsub" fill="{C2}">'
             f'从 80 维梅尔伪逆出发</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'Griffin-Lim 迭代次数</text>')
    o.append(f'<text x="{BX}" y="{BY+BH+54}" class="bsub" fill="{T3}">'
             f'再多迭代也停在 {ME["gl"]["100"]:.1f} dB——</text>')
    o.append(f'<text x="{BX}" y="{BY+BH+69}" class="bsub" fill="{T3}">'
             f'两组约束本来就不相容</text>')

    # ③ 信息预算
    CX, CY, CW, CH = 548, 78, 124, 158
    B = ME['budget']
    items = [('PCM', B['pcm_kbps'], T3), ('f32', B['mel_f32_kbps'], C1),
             ('int8', B['mel_i8_kbps'], C3)]
    hi2 = 380.
    cy = lambda v: CY + (hi2 - v) / hi2 * CH
    o.append(f'<text x="{CX}" y="{CY-30}" class="blab">③ 它不是压缩</text>')
    o.append(f'<text x="{CX}" y="{CY-15}" class="bsub" fill="{T3}">纵轴：kbps</text>')
    grid(o, CX, CY, CW, CH, [0, 100, 200, 300], cy, '%d')
    bw3 = CW / 3 * 0.5
    for i, (nm, v, c) in enumerate(items):
        x = CX + (i + 0.5) / 3 * CW - bw3 / 2
        h = v / hi2 * CH
        o.append(f'<rect x="{x:.1f}" y="{cy(v):.1f}" width="{bw3:.1f}" height="{h:.1f}" '
                 f'rx="3" fill="{c}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+bw3/2:.1f}" y="{cy(v)-7:.1f}" class="bsub" fill="{c}" '
                 f'text-anchor="middle" font-weight="600">{v:.0f}</text>')
        o.append(f'<text x="{x+bw3/2:.1f}" y="{CY+CH+16:.1f}" class="ctick" '
                 f'text-anchor="middle" font-size="9">{nm}</text>')
    o.append(f'<text x="{CX}" y="{CY+CH+40}" class="bsub" fill="{T3}">'
             f'浮点梅尔只比 PCM 省 {B["ratio_bit"]:.1f} 倍。</text>')
    o.append(f'<text x="{CX}" y="{CY+CH+55}" class="bsub" fill="{T3}">'
             f'它的价值是"好回归"，</text>')
    o.append(f'<text x="{CX}" y="{CY+CH+70}" class="bsub" fill="{T3}">不是"小"。</text>')

    o.append('<line x1="14" y1="316" x2="686" y2="316" class="grid"/>')
    o.append(f'<text x="14" y="336" class="arlab">'
             f'梅尔滤波器组把 {ME["cfg"]["nbin"]} 维压到 {ME["cfg"]["nmel"]} 维，'
             f'满行秩、条件数只有 {ME["fb"]["cond"]:.1f}——'
             f'<tspan font-weight="600">丢信息不是因为病态，是因为 {ME["cfg"]["nbin"]}→'
             f'{ME["cfg"]["nmel"]} 本来就不可逆</tspan>。</text>')
    o.append(f'<text x="14" y="354" class="arlab">'
             f'从梅尔伪逆回线性谱，对数谱距离 {ME["melinv"]["lsd_db"]:.1f} dB；'
             f'再做 100 次 Griffin-Lim 也只有 {mv["gl_100"]:.1f} dB。'
             f'这就是"Griffin-Lim 有金属音"的全部来源。</text>')
    o.append(f'<text x="14" y="374" class="arlab" fill="{C2}">'
             f'神经声码器要干的活，一大半不是"还原"，是<tspan font-weight="600">编造</tspan>——'
             f'把梅尔谱里根本不存在的高频谐波和相位造出来，而且要造得像。</text>')
    return svg(W, H, o, '三张图：梅尔谱在一千二百赫兹以上看不清谐波、相位靠迭代补不回来、'
                        '它其实几乎没有压缩')


# ══════════════════════════════════════════════════════════════
def fig_align():
    W, H = 700, 402
    o = ['<text x="10" y="18" class="ct">时长从哪来：'
         '<tspan font-weight="700">单调对齐搜索</tspan>'
         '<tspan class="cu"> · %d 帧 × %d 个音素，边界真值已知</tspan></text>'
         % (AL['cfg']['T'], AL['cfg']['I'])]
    L = np.load('align_L.npy')
    path = np.load('align_path.npy')
    I, T = L.shape
    AX, AY, AW, AH = 52, 76, 400, 150
    # 每一帧做 softmax，得到"这一帧属于各音素"的后验，比 min-max 好看也更有意义
    E = np.exp((L - L.max(0, keepdims=True)) / 40.0)
    Ln = E / E.sum(0, keepdims=True)
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 似然矩阵与 DP 找出来的那条路</text>')
    o.append(f'<text x="{AX}" y="{AY-15}" class="bsub" fill="{T3}">'
             f'每一列是一帧，每一行是一个音素；颜色越深越像</text>')
    cw, chh = AW / T, AH / I
    for i in range(I):
        for t in range(0, T):
            v = float(Ln[i, t])
            if v < 0.06:
                continue
            o.append(f'<rect x="{AX+t*cw:.2f}" y="{AY+(I-1-i)*chh:.2f}" width="{cw+0.4:.2f}" '
                     f'height="{chh+0.4:.2f}" fill="{C1}" fill-opacity="{min(v,1)*0.85:.2f}"/>')
    # 真值边界
    bt = np.cumsum([0] + AL['cfg']['dur_true'])
    for i in range(I):
        a, b = bt[i], bt[i + 1]
        o.append(f'<rect x="{AX+a*cw:.2f}" y="{AY+(I-1-i)*chh:.2f}" width="{(b-a)*cw:.2f}" '
                 f'height="{chh:.2f}" fill="none" stroke="{C3}" stroke-width="1.3"/>')
    # MAS 路径
    pts = ' '.join('%.2f,%.2f' % (AX + (t + .5) * cw, AY + (I - 1 - path[t] + .5) * chh)
                   for t in range(T))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{C2}" stroke-width="2"/>')
    for i, p in enumerate(AL['cfg']['phones']):
        o.append(f'<text x="{AX-6}" y="{AY+(I-1-i)*chh+chh/2+3:.1f}" class="ctick" '
                 f'text-anchor="end">{p}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+18}" class="cax" text-anchor="middle">'
             f'帧（每帧 {AL["cfg"]["frame_ms"]:.1f} ms）</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+38}" class="bsub" fill="{C3}">'
             f'绿框 = 真实边界</text>')
    o.append(f'<text x="{AX+92}" y="{AY+AH+38}" class="bsub" fill="{C2}">'
             f'橙线 = MAS 找到的路径</text>')
    o.append(f'<text x="{AX+240}" y="{AY+AH+38}" class="bsub" fill="{T3}">'
             f'共 10^{AL["npaths_log10"]:.1f} 条合法路径</text>')

    # ② 按边界类型
    BX, BY, BW2, BH2 = 496, 76, 176, 150
    ks = list(AL['bykind'].items())
    hi = max(v[1] for _, v in ks) * 1.25
    by = lambda v: BY + (hi - v) / hi * BH2
    o.append(f'<text x="{BX}" y="{BY-30}" class="blab">② 误差集中在哪种边界</text>')
    o.append(f'<text x="{BX}" y="{BY-15}" class="bsub" fill="{T3}">纵轴：平均边界误差 ms</text>')
    grid(o, BX, BY, BW2, BH2, [0, 30, 60, 90], by, '%d')
    bw4 = BW2 / len(ks) * 0.46
    for i, (k, (n, m)) in enumerate(ks):
        x = BX + (i + 0.5) / len(ks) * BW2 - bw4 / 2
        h = m / hi * BH2
        c = C2 if m > 40 else C1
        o.append(f'<rect x="{x:.1f}" y="{by(m):.1f}" width="{bw4:.1f}" height="{h:.1f}" '
                 f'rx="3" fill="{c}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+bw4/2:.1f}" y="{by(m)-7:.1f}" class="bsub" fill="{c}" '
                 f'text-anchor="middle" font-weight="600">{m:.1f}</text>')
        short = {'静音 ↔ 有声': '静音边界', '有明显谱突变': '谱有突变',
                 '浊音 → 浊音': '浊音滑浊音'}.get(k, k)
        o.append(f'<text x="{x+bw4/2:.1f}" y="{BY+BH2+16:.1f}" class="ctick" '
                 f'text-anchor="middle" font-size="9.5">{short}</text>')
    o.append(f'<text x="{BX}" y="{BY+BH2+52}" class="bsub" fill="{C2}">'
             f'浊音→浊音那里本来就没有边界</text>')

    o.append('<line x1="14" y1="288" x2="686" y2="288" class="grid"/>')
    o.append(f'<text x="14" y="308" class="arlab">'
             f'MAS 的平均边界误差 {AL["mas"]["mae_ms"]:.1f} ms，均分基线是 '
             f'{AL["uniform"]["mae_ms"]:.1f} ms。但这个平均数会骗人：'
             f'<tspan font-weight="600">在有谱突变的地方它准到一帧以内</tspan>，</text>')
    o.append(f'<text x="14" y="326" class="arlab">'
             f'在浊音滑到浊音的地方差 {list(AL["bykind"].values())[-1][1]:.0f} ms——'
             f'那里物理上就没有一条线可标，人工标注同样标不准。</text>')
    o.append(f'<text x="14" y="346" class="arlab" fill="{C2}">'
             f'去掉单调约束、逐帧取最大：{AL["soft"]["nonmono_pct"]:.1f}% 的帧"时间倒流"，'
             f'{AL["soft"]["n_skipped"]} 个音素一帧没分到。'
             f'<tspan font-weight="600">漏词和重复读，结构上就是这两件事</tspan>。</text>')
    o.append(f'<text x="14" y="366" class="arlab" fill="{T3}">'
             f'Tacotron 的软注意力没有任何机制禁止它们；MAS / CTC / RNN-T 在结构上禁止——'
             f'代价是放弃了"让模型自己决定看哪儿"的自由度。</text>')
    o.append(f'<text x="14" y="386" class="arlab" fill="{T3}">'
             f'另一头：只知道音素身份时，时长预测的绝对误差仍有 '
             f'{AL["durpred"]["mae_ms"]:.1f} ms。韵律就住在这个残差里。</text>')
    return svg(W, H, o, '左边是似然矩阵上的单调对齐路径与真值边界的对比，'
                        '右边显示误差几乎全部来自浊音到浊音的边界')


OUT['mel'] = fig_mel()
OUT['align'] = fig_align()
json.dump(OUT, open('figs_b.json', 'w'), ensure_ascii=False)
print('figs_b.json:', {k: len(v) for k, v in OUT.items()})
