#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《TTS 合成手册》图 6–9：流匹配步数、tokenizer 码率、声码器混叠、听测功效。"""
import json, math
import numpy as np
from figs_tts import C1, C2, C3, T3, T2, svg
from figs_tts2 import grid

FL = json.load(open('demo_flow.json'))
RQ = json.load(open('demo_rvq.json'))
VO = json.load(open('demo_voc.json'))
EV = json.load(open('demo_eval.json'))
OUT = {}


# ══════════════════════════════════════════════════════════════
def fig_flow():
    W, H = 700, 404
    o = ['<text x="10" y="18" class="ct">几步能生成完：'
         '<tspan font-weight="700">扩散 vs 流匹配</tspan>'
         '<tspan class="cu"> · 目标是三峰高斯混合，两条路径的最优向量场都有闭式解，'
         '不训练任何网络</tspan></text>']
    AX, AY, AW, AH = 54, 84, 330, 176
    nfe = FL['curves']['nfe']
    fx = lambda n: AX + (math.log2(n) / math.log2(128)) * AW
    lo, hi = -2.2, 1.0                                     # log10 W2
    fy = lambda v: AY + (hi - max(min(math.log10(max(v, 1e-3)), hi), lo)) / (hi - lo) * AH
    o.append(f'<text x="{AX}" y="{AY-32}" class="blab">① 误差 vs 前向次数（都是对数轴）</text>')
    o.append(f'<text x="{AX}" y="{AY-17}" class="bsub" fill="{T3}">'
             f'纵轴：和真实分布的 Wasserstein-2 距离，越低越好</text>')
    for v in (-2, -1, 0, 1):
        y = AY + (hi - v) / (hi - lo) * AH
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{AX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">'
                 f'10{"⁻" if v < 0 else ""}{"¹²"[abs(v)-1] if v else "⁰"}</text>')
    fl = AY + (hi - math.log10(FL['floor'])) / (hi - lo) * AH
    o.append(f'<rect x="{AX}" y="{fl:.1f}" width="{AW}" height="{AY+AH-fl:.1f}" '
             f'fill="{T3}" fill-opacity="0.09"/>')
    o.append(f'<text x="{AX+AW-3}" y="{fl-5:.1f}" class="bsub" fill="{T3}" text-anchor="end">'
             f'采样噪声地板 {FL["floor"]:.4f}——低于这条线没意义</text>')
    series = [('ddpm', C1, 'DDPM（随机）', '4 2'), ('ddim', T2, 'DDIM（ODE）', ''),
              ('fm', C2, '流匹配 + Euler', ''), ('fm_heun', C3, '流匹配 + Heun（二阶）', '')]
    for key, c, nm, dash in series:
        vs = FL['curves'][key]
        pts = ' '.join('%.1f,%.1f' % (fx(n), fy(v)) for n, v in zip(nfe, vs) if v is not None)
        da = f' stroke-dasharray="{dash}"' if dash else ''
        o.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.2"{da}/>')
        for n, v in zip(nfe, vs):
            if v is not None:
                o.append(f'<circle cx="{fx(n):.1f}" cy="{fy(v):.1f}" r="2.5" fill="{c}"/>')
    for i, (key, c, nm, _) in enumerate(series):
        y = AY + 12 + i * 15
        o.append(f'<line x1="{AX+AW-146}" y1="{y-4}" x2="{AX+AW-126}" y2="{y-4}" '
                 f'stroke="{c}" stroke-width="2.6"/>')
        o.append(f'<text x="{AX+AW-120}" y="{y}" class="bsub" fill="{c}">{nm}</text>')
    for n in nfe:
        o.append(f'<line x1="{fx(n):.1f}" y1="{AY+AH}" x2="{fx(n):.1f}" y2="{AY+AH+4}" class="grid"/>')
        o.append(f'<text x="{fx(n):.1f}" y="{AY+AH+17}" class="ctick" text-anchor="middle">{n}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+34}" class="cax" text-anchor="middle">'
             f'NFE（网络前向次数 = 延迟）</text>')

    BX, BY, BW, BH = 452, 84, 218, 176
    o.append(f'<text x="{BX}" y="{BY-32}" class="blab">② 达到同样质量要几步</text>')
    o.append(f'<text x="{BX}" y="{BY-17}" class="bsub" fill="{T3}">'
             f'横轴：NFE（W2 ≤ {FL["thr"]:.4f}，即 1.5 倍地板）</text>')
    rows = [('DDPM（随机）', FL['nfe_at_thr']['ddpm'], C1),
            ('DDIM（ODE）', FL['nfe_at_thr']['ddim'], T2),
            ('流匹配 + Euler', FL['nfe_at_thr']['fm'], C2),
            ('流匹配 + Heun', FL['nfe_at_thr']['fm_heun'], C3),
            ('掰直之后（reflow）', 1, C3)]
    mx = 160.
    for i, (nm, v, c) in enumerate(rows):
        y = BY + 16 + i * 30
        vv = v if v else 160
        w = vv / mx * (BW - 60)
        o.append(f'<text x="{BX}" y="{y-6}" class="bsub">{nm}</text>')
        o.append(f'<rect x="{BX}" y="{y}" width="{max(w,2):.1f}" height="11" rx="2" '
                 f'fill="{c}" fill-opacity="0.85"/>')
        o.append(f'<text x="{BX+max(w,2)+6:.1f}" y="{y+9}" class="bsub" fill="{c}" '
                 f'font-weight="600">{v if v else ">128"}</text>')
    o.append(f'<text x="{BX}" y="{BY+BH+8}" class="bsub" fill="{T3}">'
             f'路径弯曲度：OT {FL["straight"]["fm_mean"]:.2f}，'
             f'扩散 {FL["straight"]["vp_mean"]:.2f}</text>')

    o.append('<line x1="14" y1="292" x2="686" y2="292" class="grid"/>')
    o.append('<text x="14" y="312" class="arlab">'
             '<tspan font-weight="600">一个和流行说法不一样的结论</tspan>：'
             '流匹配配一阶欧拉法并<tspan font-weight="600">没有</tspan>比 DDIM 省步数'
             '（图里橙线和灰线几乎重合）。</text>')
    o.append(f'<text x="14" y="330" class="arlab">'
             f'它省在<tspan font-weight="600">路径够直，所以高阶求解器好用</tspan>：'
             f'换成二阶 Heun，{FL["nfe_at_thr"]["fm_heun"]} 次前向就到了，'
             f'而 DDIM 要 {FL["nfe_at_thr"]["ddim"]}。</text>')
    o.append(f'<text x="14" y="350" class="arlab" fill="{C2}">'
             f'"够直"不等于"直"：OT 路径的弯曲度是 {FL["straight"]["fm_mean"]:.2f}，不是 0。'
             f'真正一步生成要靠 reflow 或蒸馏，不是流匹配自带的。</text>')
    lat = EV_lat = FL['latency'][0]
    o.append(f'<text x="14" y="370" class="arlab" fill="{T3}">'
             f'换成延迟（单步 3 ms）：DDPM {lat["ddpm"]:.0f} ms，DDIM {lat["ddim"]:.0f} ms，'
             f'流匹配 + Heun {lat["fm_heun"]:.0f} ms——首包预算就是这么花掉的。</text>')
    o.append(f'<text x="14" y="390" class="arlab" fill="{T3}">'
             f'注意这是一维闭式场的理想实验：真实高维里模型本身的误差通常比求解器误差大，'
             f'所以实际步数还要更多。</text>')
    return svg(W, H, o, '两张图：误差随前向次数下降的四条曲线，以及达到同等质量所需的步数对比，'
                        '结论是流匹配的优势来自高阶求解器而不是一阶')


# ══════════════════════════════════════════════════════════════
def fig_rvq():
    W, H = 700, 432
    o = ['<text x="10" y="18" class="ct">音频 token：'
         '<tspan font-weight="700">码率、质量、上下文长度</tspan>'
         '<tspan class="cu"> · 残差矢量量化，码本 1024，语料 %.0f 秒合成语音</tspan></text>'
         % RQ['data']['secs']]
    lad = RQ['ladder']
    AX, AY, AW, AH = 54, 80, 250, 160
    fx = lambda v: AX + v / 7.4 * AW
    lo, hi = 18., 36.
    fy = lambda v: AY + (hi - v) / (hi - lo) * AH
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 每加一级换多少质量</text>')
    o.append(f'<text x="{AX}" y="{AY-15}" class="bsub" fill="{T3}">纵轴：重建 SNR（dB）</text>')
    grid(o, AX, AY, AW, AH, [20, 25, 30, 35], fy, '%d')
    pts = ' '.join('%.1f,%.1f' % (fx(r['kbps']), fy(r['snr'])) for r in lad)
    o.append(f'<polyline points="{pts}" fill="none" stroke="{C1}" stroke-width="2.3"/>')
    for r in lad:
        o.append(f'<circle cx="{fx(r["kbps"]):.1f}" cy="{fy(r["snr"]):.1f}" r="3" fill="{C1}"/>')
    for r in (lad[0], lad[3], lad[7]):
        o.append(f'<text x="{fx(r["kbps"]):.1f}" y="{fy(r["snr"])-9:.1f}" class="bsub" '
                 f'fill="{C1}" text-anchor="middle">{r["nq"]} 级 {r["snr"]:.1f}</text>')
    for v in (0, 2, 4, 6):
        o.append(f'<line x1="{fx(v):.1f}" y1="{AY+AH}" x2="{fx(v):.1f}" y2="{AY+AH+4}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+17}" class="ctick" text-anchor="middle">{v}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+34}" class="cax" text-anchor="middle">'
             f'码率（kbps）</text>')
    cl = RQ['collapse']
    o.append(f'<text x="{AX}" y="{AY+AH+54}" class="bsub" fill="{T3}">'
             f'每级大约 +1.5 dB，而困惑度从 {lad[0]["perp"]:.0f} 掉到 {lad[7]["perp"]:.0f}——</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+69}" class="bsub" fill="{T3}">'
             f'越靠后的码本，信息越少、越难学</text>')

    BX, BY, BW, BH = 374, 80, 296, 160
    o.append(f'<text x="{BX}" y="{BY-30}" class="blab">② 10 秒话要占多少个 token</text>')
    o.append(f'<text x="{BX}" y="{BY-15}" class="bsub" fill="{T3}">'
             f'对 LLM-TTS 来说，这就是上下文长度和首包延迟</text>')
    rates = [(86.1, '86 Hz（梅尔帧率）'), (75.0, '75 Hz'), (50.0, '50 Hz'), (25.0, '25 Hz')]
    mx = 7200.
    for i, (rt, nm) in enumerate(rates):
        y = BY + 16 + i * 36
        o.append(f'<text x="{BX}" y="{y-5}" class="bsub">{nm}</text>')
        for j, (nq, c) in enumerate(((1, C3), (4, C1), (8, C2))):
            v = rt * nq * 10
            w = v / mx * (BW - 76)
            yy = y + j * 7
            o.append(f'<rect x="{BX+70}" y="{yy}" width="{max(w,1.5):.1f}" height="5.4" '
                     f'rx="1.5" fill="{c}" fill-opacity="0.9"/>')
        o.append(f'<text x="{BX+70+rt*8*10/mx*(BW-76)+6:.1f}" y="{y+18}" class="bsub" '
                 f'fill="{C2}">{int(rt*8*10)}</text>')
    for j, (nq, c, nm) in enumerate(((1, C3, '1 级'), (4, C1, '4 级'), (8, C2, '8 级'))):
        o.append(f'<line x1="{BX+70+j*54}" y1="{BY+BH-4}" x2="{BX+86+j*54}" y2="{BY+BH-4}" '
                 f'stroke="{c}" stroke-width="3"/>')
        o.append(f'<text x="{BX+90+j*54}" y="{BY+BH}" class="bsub" fill="{c}">{nm}</text>')

    o.append('<line x1="14" y1="308" x2="686" y2="308" class="grid"/>')
    FT = [
        ('%d bit 等价于一个 2^%d 条目的单码本，存不下也训不了。'
         '<b>RVQ 把指数变成了线性</b>：8 个 1024×80 的表。'
         % (RQ['why_rvq']['equiv_bits'], RQ['why_rvq']['equiv_bits']), None),
        ('码本坍塌不是玄学：随机小初始化、不救死码，第一级只有 %d 个码被用上（共 1024）。'
         % cl['no_revive']['used'][0], C2),
        ('加上"把没人用的码搬到误差最大处"这几行，就变成 1024 个全用、'
         'SNR %.1f → %.1f dB。' % (cl['no_revive']['snr'], cl['revive']['snr']), C2),
        ('右图是 <b>LLM-TTS 为什么拼命压帧率</b>：86 Hz × 8 级的 10 秒话是 %d 个 token，'
         '25 Hz × 8 级只要 %d 个。' % (int(86.1 * 8 * 10), int(25 * 8 * 10)), None),
        ('但帧率压下去，时长分辨率也跟着掉：25 Hz 一帧 40 ms，'
         '而 17 节说过音素边界的精度要求是 10–20 ms。', T3),
        ('（SNR 是在合成语料的梅尔域上测的，绝对值和真实编解码器不可比；'
         '可比的是形状：每级约 +1.5 dB，很快饱和。）', T3),
    ]
    for i2, (t, c) in enumerate(FT):
        t = t.replace('<b>', '<tspan font-weight="600">').replace('</b>', '</tspan>')
        cc = f' fill="{c}"' if c else ''
        o.append(f'<text x="14" y="{328 + i2 * 17}" class="arlab"{cc}>{t}</text>')
    return svg(W, H, o, '左边是残差量化每加一级换到的信噪比，右边是不同帧率和级数下'
                        '十秒语音占用的 token 数')


# ══════════════════════════════════════════════════════════════
def fig_alias():
    W, H = 700, 420
    o = ['<text x="10" y="18" class="ct">声码器的两个"电音"来源：'
         '<tspan font-weight="700">非线性混叠</tspan> 与 '
         '<tspan font-weight="700">棋盘伪影</tspan>'
         '<tspan class="cu"> · 3 kHz 纯音，22.05 kHz 采样</tspan></text>']
    AX, AY, AW, AH = 54, 84, 300, 150
    o.append(f'<text x="{AX}" y="{AY-32}" class="blab">① 谐波折回来落在哪儿</text>')
    o.append(f'<text x="{AX}" y="{AY-17}" class="bsub" fill="{T3}">'
             f'横轴：频率（kHz），竖线 = 一个非线性造出来的谐波</text>')
    fmax = 22.05
    fx = lambda f: AX + f / fmax * AW
    o.append(f'<line x1="{AX}" y1="{AY+AH}" x2="{AX+AW}" y2="{AY+AH}" class="grid"/>')
    nyq = 11.025
    o.append(f'<rect x="{fx(nyq):.1f}" y="{AY}" width="{AW-fx(nyq)+AX:.1f}" height="{AH}" '
             f'fill="{T3}" fill-opacity="0.08"/>')
    o.append(f'<line x1="{fx(nyq):.1f}" y1="{AY-4}" x2="{fx(nyq):.1f}" y2="{AY+AH}" '
             f'stroke="{T3}" stroke-width="1.2" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{fx(nyq)+4:.1f}" y="{AY+9}" class="bsub" fill="{T3}">'
             f'奈奎斯特 11.025 kHz——右边这一半采样率表示不了</text>')
    for k in range(1, 8):
        f = 3.0 * k
        fold = f
        while fold > nyq:
            fold = 2 * nyq - fold if fold < 2 * nyq else fold - 2 * nyq
            if fold < 0:
                fold = -fold
        inb = f <= nyq
        c = C1 if inb else C2
        MID = AY + AH * 0.52                              # 上半层画"理论谐波"
        h = (AH * 0.40) * (1.0 if k == 1 else 0.62 / math.sqrt(k))
        o.append(f'<line x1="{fx(f):.1f}" y1="{MID:.1f}" x2="{fx(f):.1f}" y2="{MID-h:.1f}" '
                 f'stroke="{c}" stroke-width="2" stroke-opacity="{1 if inb else .5}"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{MID-h-4:.1f}" class="bsub" fill="{c}" '
                 f'text-anchor="middle">{k}f</text>')
        if not inb:                                       # 下半层画"实际听到的位置"
            yy = MID + 10 + (k - 4) * 5
            o.append(f'<path d="M{fx(f):.1f},{MID+3:.1f} L{fx(f):.1f},{yy:.1f} '
                     f'L{fx(fold):.1f},{yy:.1f} L{fx(fold):.1f},{MID+34:.1f}" fill="none" '
                     f'stroke="{C2}" stroke-width="1" stroke-dasharray="3 2" '
                     f'stroke-opacity=".6"/>')
            o.append(f'<line x1="{fx(fold):.1f}" y1="{AY+AH}" x2="{fx(fold):.1f}" '
                     f'y2="{MID+34:.1f}" stroke="{C2}" stroke-width="2"/>')
            o.append(f'<text x="{fx(fold):.1f}" y="{AY+AH+13:.1f}" class="bsub" fill="{C2}" '
                     f'text-anchor="middle">{fold:.1f}k</text>')
    for f in (0, 5, 10, 15, 20):
        o.append(f'<text x="{fx(f):.1f}" y="{AY+AH+30}" class="ctick" '
                 f'text-anchor="middle">{f}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+46}" class="cax" text-anchor="middle">kHz</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+66}" class="bsub" fill="{C2}">'
             f'上半层是非线性造出的谐波，下半层是它实际出现的位置</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+81}" class="bsub" fill="{C2}">'
             f'7 次谐波落回 1.05 kHz——语音最要命的频段</text>')

    BX, BY, BW, BH = 412, 84, 258, 150
    o.append(f'<text x="{BX}" y="{BY-32}" class="blab">② 反混叠值多少</text>')
    o.append(f'<text x="{BX}" y="{BY-17}" class="bsub" fill="{T3}">'
             f'纵轴：混叠能量 / 谐波能量（dB，越低越好）</text>')
    lo, hi = -115., 0.
    by = lambda v: BY + (hi - v) / (hi - lo) * BH
    grid(o, BX, BY, BW, BH, [0, -30, -60, -90], by, '%d')
    cases = VO['alias']['cases']
    xs = ['直接做', '上采 2×', '上采 4×']
    for ci, case in enumerate(cases):
        c = C2 if ci == 0 else C1
        vs = [case['naive'], case['up2'], case['up4']]
        pts = ' '.join('%.1f,%.1f' % (BX + (i + .5) / 3 * BW, by(v)) for i, v in enumerate(vs))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.3"/>')
        for i, v in enumerate(vs):
            x = BX + (i + .5) / 3 * BW
            o.append(f'<circle cx="{x:.1f}" cy="{by(v):.1f}" r="3" fill="{c}"/>')
            o.append(f'<text x="{x:.1f}" y="{by(v)-8:.1f}" class="bsub" fill="{c}" '
                     f'text-anchor="middle">{v:.0f}</text>')
        o.append(f'<text x="{BX+(2.5)/3*BW+8:.1f}" y="{by(vs[2])+(16 if ci else -12):.1f}" '
                 f'class="bsub" fill="{c}">{case["act"]}</text>')
    for i, nm in enumerate(xs):
        o.append(f'<text x="{BX+(i+.5)/3*BW:.1f}" y="{BY+BH+17}" class="ctick" '
                 f'text-anchor="middle">{nm}</text>')
    o.append(f'<text x="{BX}" y="{BY+BH+40}" class="bsub" fill="{T3}">'
             f'snake 是光滑函数，谐波指数衰减；</text>')
    o.append(f'<text x="{BX}" y="{BY+BH+55}" class="bsub" fill="{T3}">'
             f'leaky ReLU 有折点，谐波只按 1/k² 衰减</text>')

    o.append('<line x1="14" y1="326" x2="686" y2="326" class="grid"/>')
    FT = [
        ('<b>激活函数光滑不光滑，差了七十个 dB</b>：同样上采 2× 再做，'
         'snake 降到 −108.8 dB，leaky ReLU 只到 −42.7 dB。', None),
        ('棋盘伪影是另一件事，而且可以纸上算死：步长 s 的转置卷积，'
         '第 p 个相位上叠加 ⌈(k−p)/s⌉ 个权重。', None),
        ('k 不能被 s 整除时各相位不等，输出就带上周期为 s 的功率调制——'
         '<b>3.01 dB</b>（推导）对 <b>3.19 dB</b>（实测）。', None),
        ('还有一条决定了损失函数怎么写：把一个正弦相位挪 90°，波形 L2 是 +3.01 dB'
         '（误差比信号还大），幅度谱距离是 0——而人耳听不出区别。', C2),
        ('所以 HiFi-GAN 一类的损失里没有波形 L2，只有多尺度谱损失加判别器。', T3),
    ]
    for i2, (t, c) in enumerate(FT):
        t = t.replace('<b>', '<tspan font-weight="600">').replace('</b>', '</tspan>')
        cc = f' fill="{c}"' if c else ''
        o.append(f'<text x="14" y="{346 + i2 * 17}" class="arlab"{cc}>{t}</text>')
    return svg(W, H, o, '左边显示三千赫兹纯音经非线性产生的高次谐波如何折回语音频段，'
                        '右边显示上采样反混叠能把混叠压低多少')


# ══════════════════════════════════════════════════════════════
def fig_mos():
    W, H = 700, 372
    o = ['<text x="10" y="18" class="ct">听测要多少人：'
         '<tspan font-weight="700">同一个 ΔMOS，三种设计差一个量级</tspan>'
         '<tspan class="cu"> · 20 句，80% 功效，α = 0.05；方差参数见正文</tspan></text>']
    AX, AY, AW, AH = 54, 84, 330, 168
    deltas = [0.05, 0.10, 0.20, 0.30]
    fy = lambda v: AY + (math.log10(520) - math.log10(max(v, 4))) / (math.log10(520) - math.log10(4)) * AH
    fx = lambda i: AX + (i + .5) / len(deltas) * AW
    o.append(f'<text x="{AX}" y="{AY-32}" class="blab">① 要多少位评分人</text>')
    o.append(f'<text x="{AX}" y="{AY-17}" class="bsub" fill="{T3}">'
             f'纵轴：达到 80% 检出率所需人数（对数轴），20 句</text>')
    for v in (5, 10, 20, 40, 80, 160, 320):
        y = fy(v)
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{AX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    series = []
    pa = [next((r['paired'].get('20句') for r in EV['mos'] if r['delta'] == d), None) for d in deltas]
    ia = [next((r['indep'].get('20句') for r in EV['mos'] if r['delta'] == d), None) for d in deltas]
    ca = [next((r['raters_20sent'] for r in EV['cmos'] if r['delta'] == d), None) for d in deltas]
    for vals, c, nm in ((ia, C2, '绝对 MOS · 两批人分别听'),
                        (pa, C1, '绝对 MOS · 同一批人都听'),
                        (ca, C3, 'CMOS · 直接比 A/B')):
        pts = ' '.join('%.1f,%.1f' % (fx(i), fy(v if v else 400))
                       for i, v in enumerate(vals) if v)
        o.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.3"/>')
        for i, v in enumerate(vals):
            if v:
                o.append(f'<circle cx="{fx(i):.1f}" cy="{fy(v):.1f}" r="3" fill="{c}"/>')
                o.append(f'<text x="{fx(i):.1f}" y="{fy(v)-8:.1f}" class="bsub" fill="{c}" '
                         f'text-anchor="middle">{v}</text>')
            else:
                o.append(f'<text x="{fx(i):.1f}" y="{fy(420):.1f}" class="bsub" fill="{c}" '
                         f'text-anchor="middle">测不出</text>')
    for i, d in enumerate(deltas):
        o.append(f'<text x="{fx(i):.1f}" y="{AY+AH+17}" class="ctick" '
                 f'text-anchor="middle">{d:.2f}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+34}" class="cax" text-anchor="middle">'
             f'要检出的差距 ΔMOS</text>')
    for i, (c, nm) in enumerate(((C2, '绝对 MOS · 两批人分别听'), (C1, '绝对 MOS · 同一批人都听'),
                                 (C3, 'CMOS · 直接比 A/B'))):
        y = AY + AH - 46 + i * 15
        o.append(f'<line x1="{AX+8}" y1="{y-4}" x2="{AX+28}" y2="{y-4}" '
                 f'stroke="{c}" stroke-width="2.6"/>')
        o.append(f'<text x="{AX+34}" y="{y}" class="bsub" fill="{c}">{nm}</text>')

    BX, BY, BW, BH = 452, 84, 218, 168
    o.append(f'<text x="{BX}" y="{BY-32}" class="blab">② 客观指标便宜得多</text>')
    o.append(f'<text x="{BX}" y="{BY-17}" class="bsub" fill="{T3}">'
             f'用 ASR 回环测可懂度，需要多少句</text>')
    ws = EV['wer']
    mx = 2000.
    for i, r in enumerate(ws):
        y = BY + 20 + i * 34
        v = r['sents'] or 5000
        w = min(v / mx, 1.0) * (BW - 84)
        o.append(f'<text x="{BX}" y="{y-6}" class="bsub">CER {r["w1"]*100:.1f}% vs '
                 f'{r["w2"]*100:.1f}%</text>')
        o.append(f'<rect x="{BX}" y="{y}" width="{max(w,2):.1f}" height="11" rx="2" '
                 f'fill="{C1}" fill-opacity="0.85"/>')
        o.append(f'<text x="{BX+max(w,2)+6:.1f}" y="{y+9}" class="bsub" fill="{C1}" '
                 f'font-weight="600">{v} 句</text>')
    o.append(f'<text x="{BX}" y="{BY+BH+2}" class="bsub" fill="{T3}">'
             f'几百句能测出 1 个百分点，</text>')
    o.append(f'<text x="{BX}" y="{BY+BH+17}" class="bsub" fill="{T3}">'
             f'而且不用请人</text>')

    o.append('<line x1="14" y1="286" x2="686" y2="286" class="grid"/>')
    FT = [
        ('<b>听测设计比听测人数值钱</b>：同一批人同时听两套系统，'
         '评分人的松紧偏置被差分掉，ΔMOS = 0.2 的人数需求从 320 降到 20。', None),
        ('ΔMOS = 0.1 在"两批人分别听"的设计下，<b>320 人也测不出来</b>——'
         '论文里那些"MOS 提升 0.08"的结论，多数经不起这个检验。', C2),
        ('所以：客观指标（ASR 回环、说话人相似度、基频 RMSE）守底线，'
         'CMOS 定成败，绝对 MOS 只用来对外报数。', T3),
    ]
    for i2, (t, c) in enumerate(FT):
        t = t.replace('<b>', '<tspan font-weight="600">').replace('</b>', '</tspan>')
        cc = f' fill="{c}"' if c else ''
        o.append(f'<text x="14" y="{306 + i2 * 19}" class="arlab"{cc}>{t}</text>')
    return svg(W, H, o, '左边是三种听测设计达到八成检出率所需的评分人数，'
                        '右边是 ASR 回环测可懂度所需的句数')


OUT['flow'] = fig_flow()
OUT['rvq'] = fig_rvq()
OUT['alias'] = fig_alias()
OUT['mos'] = fig_mos()
json.dump(OUT, open('figs_c.json', 'w'), ensure_ascii=False)
print('figs_c.json:', {k: len(v) for k, v in OUT.items()})
