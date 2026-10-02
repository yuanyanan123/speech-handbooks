#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最后 4 张：§09 声学结构、§10 STO/SRO、§11 风噪双重打击、§13 相位写错的两种后果。"""
import json, math, html
import numpy as np
c = 343.0
OUT = {}

def defs(u):
    return (f'<defs>'
            f'<marker id="{u}a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--text-2)"/></marker>'
            f'<marker id="{u}h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--hot)"/></marker></defs>')

def ar(x1, y1, x2, y2, u, cls='ar', mk='a'):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}" marker-end="url(#{u}{mk})"/>'

def svg(w, h, body, lab, u, diag=True):
    return (f'<svg viewBox="0 0 {w} {h}" class="chart{" diag" if diag else ""}" role="img" '
            f'aria-label="{html.escape(lab)}">\n{defs(u)}\n{body}\n</svg>')

# ═══════════════════════════════════════════════════════════════
# §09  声学结构剖面：五件事都在这张图里
# ═══════════════════════════════════════════════════════════════
def f_acoustic():
    u = 'ac'; o = []
    o.append('<text x="10" y="18" class="ct">声学结构：在画板阶段就把上限锁死了'
             '<tspan class="cu"> · 定型后无解，所以必须先测</tspan></text>')

    def channel(x0, y0, ok=True, tag='通道 A'):
        s = []
        W, PCB = 150, 14
        # 外壳
        s.append(f'<rect x="{x0}" y="{y0}" width="{W}" height="26" '
                 f'fill="var(--surface-2)" stroke="var(--border-2)" stroke-width="1.2"/>')
        s.append(f'<text x="{x0+W+8}" y="{y0+17}" class="bsub">外壳</text>')
        # 拾音孔
        px = x0 + 52
        s.append(f'<rect x="{px}" y="{y0}" width="14" height="26" fill="var(--bg)" '
                 f'stroke="var(--s1)" stroke-width="1.6"/>')
        # 前腔
        s.append(f'<rect x="{x0+26}" y="{y0+26}" width="{W-52}" height="30" '
                 f'fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.3"/>')
        # 防尘网
        s.append(f'<line x1="{px-3}" y1="{y0+26}" x2="{px+17}" y2="{y0+26}" '
                 f'stroke="var(--s3)" stroke-width="3"/>')
        # MEMS + PCB
        s.append(f'<rect x="{x0+50}" y="{y0+56}" width="50" height="18" rx="2" '
                 f'fill="var(--surface)" stroke="var(--accent)" stroke-width="1.4"/>')
        s.append(f'<text x="{x0+75}" y="{y0+69}" class="bsub" text-anchor="middle">MEMS</text>')
        s.append(f'<rect x="{x0+10}" y="{y0+74}" width="{W-20}" height="{PCB}" '
                 f'fill="var(--surface-2)" stroke="var(--border-2)"/>')
        s.append(f'<text x="{x0+W/2}" y="{y0+85}" class="bsub" text-anchor="middle">PCB</text>')
        # 密封圈
        for sx in (x0 + 26, x0 + W - 28):
            s.append(f'<rect x="{sx-3}" y="{y0+26}" width="6" height="30" fill="var(--s2)" '
                     f'fill-opacity="0.55" stroke="var(--s2)" stroke-width="1"/>')
        # 声波
        s.append(ar(px + 7, y0 - 20, px + 7, y0 - 3, u))
        s.append(f'<text x="{px+14}" y="{y0-9}" class="bsub">声波</text>')
        if not ok:
            s.append(f'<rect x="{px-2}" y="{y0-4}" width="8" height="8" fill="var(--s2)"/>')
            s.append(f'<text x="{px+20}" y="{y0-24}" class="bsub" fill="var(--s2)">'
                     f'结构件挡住一点</text>')
        s.append(f'<text x="{x0}" y="{y0-32}" class="blab">{tag}</text>')
        return '\n'.join(s)

    o.append(channel(40, 84, True, '通道 A'))
    o.append(channel(250, 84, False, '通道 B'))
    # 图例
    LX = 452
    for i, (col, t, d) in enumerate([
            ('var(--s1)', '拾音孔', '孔径 + 深度'),
            ('var(--accent)', '前腔', '容积决定谐振'),
            ('var(--s3)', '防尘 / 防风网', '插入损耗与相位'),
            ('var(--s2)', '密封圈', '漏气 → 低频跑偏'),
            ('var(--text-2)', 'PCB / 隔振', '结构传声进 MEMS')]):
        y = 92 + i * 22
        o.append(f'<rect x="{LX}" y="{y-9}" width="11" height="11" rx="2" fill="{col}" '
                 f'fill-opacity="0.75"/>')
        o.append(f'<text x="{LX+18}" y="{y}" class="blab">{t}</text>')
        o.append(f'<text x="{LX+92}" y="{y}" class="bsub">{d}</text>')
    o.append(f'<text x="{LX}" y="216" class="bsub" fill="var(--s2)">'
             f'这五件事全部要求各通道<tspan font-weight="600">完全相同</tspan></text>')
    o.append('<text x="40" y="216" class="bsub" fill="var(--s2)">'
             'B 通道只是被挡了一点，幅相就跑了——</text>')
    o.append('<text x="40" y="232" class="bsub" fill="var(--s2)">'
             '而 04 节的预算是幅度 &lt;0.3 dB、相位 &lt;2°</text>')
    # 亥姆霍兹算例
    BY = 262
    o.append(f'<line x1="14" y1="{BY-16}" x2="686" y2="{BY-16}" class="grid"/>')
    o.append(f'<text x="14" y="{BY}" class="blab">前腔容积直接决定谐振落在哪：'
             f'<tspan class="bsub">f_H = (c/2π)·√(A / V·L_eff)，孔 Ø1 mm、深 1 mm</tspan></text>')
    W2, X0 = 470, 120
    fx = lambda V: X0 + (math.log10(V) - math.log10(2)) / (math.log10(100) - math.log10(2)) * W2
    yy = BY + 34
    o.append(f'<rect x="{fx(2):.0f}" y="{yy-11}" width="{fx(100)-fx(2):.0f}" height="22" rx="3" '
             f'fill="var(--surface-2)" stroke="var(--border-2)"/>')
    for V in (2, 5, 10, 20, 50, 100):
        a_ = 0.5e-3; A = math.pi * a_ * a_; Le = 1e-3 + 1.7 * a_
        fH = c / (2 * math.pi) * math.sqrt(A / (V * 1e-9 * Le))
        bad = fH < 8500
        col = 'var(--s2)' if bad else 'var(--s3)'
        o.append(f'<line x1="{fx(V):.1f}" y1="{yy-11}" x2="{fx(V):.1f}" y2="{yy+11}" '
                 f'stroke="{col}" stroke-width="2.4"/>')
        o.append(f'<text x="{fx(V):.1f}" y="{yy-17}" class="bsub" text-anchor="middle" '
                 f'fill="{col}">{fH/1000:.1f}k</text>')
        o.append(f'<text x="{fx(V):.1f}" y="{yy+26}" class="ctick" text-anchor="middle">{V}</text>')
    o.append(f'<text x="{X0-8}" y="{yy+4}" class="bsub" text-anchor="end">前腔 mm³</text>')
    o.append(f'<text x="14" y="{yy+50}" class="arlab">'
             f'<tspan fill="var(--s2)" font-weight="600">前腔从 2 mm³ 涨到 20 mm³，'
             f'谐振就从 25 kHz 掉到 8 kHz</tspan>——直接落进语音频段。</text>')
    o.append(f'<text x="14" y="{yy+68}" class="arlab">'
             f'谐振点附近相位剧烈变化，那个频段的 DOA 和超指向会整段失效。'
             f'<tspan font-weight="600">必须在结构定型前测，定型后无解。</tspan></text>')
    return svg(700, 390, '\n'.join(o),
               '麦克风声学结构剖面：拾音孔、前腔、防尘网、密封圈和隔振五件事都要求各通道完全一致；'
               '前腔容积从 2 立方毫米增到 20 立方毫米会把亥姆霍兹谐振从 25 千赫降到 8 千赫，'
               '落进语音频段', u)

OUT['acoustic'] = f_acoustic()

# ═══════════════════════════════════════════════════════════════
# §10  STO 是台阶，SRO 是斜坡
# ═══════════════════════════════════════════════════════════════
def f_clock():
    u = 'ck'; o = []
    o.append('<text x="10" y="18" class="ct">STO 是台阶，SRO 是斜坡'
             '<tspan class="cu"> · 一个测一次就补掉，一个必须一直补</tspan></text>')
    ML, W2, PH, TOP = 56, 400, 190, 52
    fy = lambda v: TOP + (40 - v) / 40 * PH
    T0, T1 = 0.006, 30.
    fx = lambda t: ML + (math.log10(max(t,T0)) - math.log10(T0)) / (math.log10(T1) - math.log10(T0)) * W2
    for v in (0, 10, 20, 30, 40):
        o.append(f'<line x1="{ML}" y1="{fy(v):.1f}" x2="{ML+W2}" y2="{fy(v):.1f}" class="grid"/>')
        o.append(f'<text x="{ML-7}" y="{fy(v)+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    o.append(f'<text x="{ML-40}" y="{TOP-14}" class="cax">4 kHz 处的相位误差（°）</text>')
    # 2° 预算线
    o.append(f'<line x1="{ML}" y1="{fy(2):.1f}" x2="{ML+W2}" y2="{fy(2):.1f}" '
             f'stroke="var(--text-3)" stroke-width="1.4" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{ML+W2-4}" y="{fy(2)+15:.1f}" class="bsub" text-anchor="end" '
             f'fill="var(--text-3)">超指向的 2° 预算</text>')
    tt = np.logspace(math.log10(T0), math.log10(T1), 400)
    # STO：固定台阶（这里取 8°），补一次就没了
    o.append(f'<polyline points="{" ".join(f"{fx(t):.1f},{fy(14):.1f}" for t in tt)}" '
             f'fill="none" stroke="var(--s3)" stroke-width="2.4"/>')
    o.append(f'<text x="{fx(3.2):.0f}" y="{fy(14)-8:.1f}" class="clab halo" fill="var(--s3)">'
             f'STO：固定值，不随时间变</text>')
    # SRO：三条斜坡
    for ppm, col in [(1, 'var(--o1)'), (20, 'var(--o3)'), (100, 'var(--o4)')]:
        v = 360 * 4000 * ppm * 1e-6 * tt
        pts = ' '.join(f'{fx(t):.1f},{fy(min(x,40)):.1f}' for t, x in zip(tt, v))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.4"/>')
        t2 = 2.0 / (360 * 4000 * ppm * 1e-6)
        o.append(f'<circle cx="{fx(t2):.1f}" cy="{fy(2):.1f}" r="3.6" fill="{col}" '
                 f'stroke="var(--surface)" stroke-width="1.4"/>')
        lab = '%.0f ms' % (t2 * 1000) if t2 < 1 else '%.1f s' % t2
        yl = {100: fy(2) - 10, 20: fy(2) - 26, 1: fy(2) - 10}[ppm]
        o.append(f'<line x1="{fx(t2):.1f}" y1="{fy(2):.1f}" x2="{fx(t2):.1f}" '
                 f'y2="{yl+4:.1f}" stroke="{col}" stroke-width="1" stroke-dasharray="2 2"/>')
        o.append(f'<text x="{fx(t2)+5:.1f}" y="{yl:.1f}" class="clab halo" fill="{col}">'
                 f'{ppm} ppm · {lab}</text>')
    o.append(f'<text x="{fx(0.12):.0f}" y="{fy(37):.0f}" class="clab" fill="var(--text-3)">'
             f'SRO：随时间线性增长（对数横轴上看是曲线）</text>')
    for t, lab in [(0.01, '10 ms'), (0.1, '100 ms'), (1, '1 s'), (10, '10 s'), (30, '30 s')]:
        o.append(f'<line x1="{fx(t):.1f}" y1="{TOP+PH}" x2="{fx(t):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(t):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+W2/2:.0f}" y="{TOP+PH+33}" class="cax" text-anchor="middle">时间（秒）</text>')
    # 右侧对照
    RX = 496
    o.append(f'<line x1="{RX-16}" y1="{TOP-24}" x2="{RX-16}" y2="{TOP+PH+30}" class="ar-d" '
             f'marker-end="none"/>')
    rows = [('STO', 'var(--s3)', '起始时刻不同', '互相关测一次，补一个固定延迟就完事'),
            ('SRO', 'var(--o3)', '时钟频率不同', '必须持续估计 + 重采样，停一会儿就废')]
    for i, (n, col, what, fix) in enumerate(rows):
        y = TOP + i * 96
        o.append(f'<text x="{RX}" y="{y}" class="blab" fill="{col}">{n}</text>')
        o.append(f'<text x="{RX}" y="{y+18}" class="bsub">{what}</text>')
        o.append(f'<text x="{RX}" y="{y+36}" class="bsub">{fix}</text>')
    o.append(f'<text x="{RX}" y="{TOP+196}" class="bsub" fill="var(--text-3)">'
             f'诊断：分段做通道间互相关，</text>')
    o.append(f'<text x="{RX}" y="{TOP+212}" class="bsub" fill="var(--text-3)">'
             f'峰位置随时间移动 = SRO</text>')
    o.append('<text x="14" y="296" class="arlab">'
             '消费级晶振 ±20–50 ppm，两台独立设备最坏差 100 ppm——'
             '<tspan font-weight="600">4 kHz 处 14 毫秒就吃光 2° 预算</tspan>。'
             '即使是 1 ppm，也只撑得住 1.4 秒。</text>')
    o.append('<text x="14" y="314" class="arlab">'
             '所以同一块板上必须共享 MCLK/BCLK/WS；跨设备组阵则必须显式估计并补偿 SRO，没有第三条路。</text>')
    return svg(700, 326, '\n'.join(o),
               '采样时刻偏移是一条水平线，测一次补掉即可；'
               '采样率偏移是随时间线性增长的斜坡，1 ppm 在 4 千赫处 1.4 秒就用光 2 度的相位预算，'
               '100 ppm 只要 14 毫秒', u, diag=False)

OUT['clock'] = f_clock()

# ═══════════════════════════════════════════════════════════════
# §11  风噪的双重打击，以及同一条相干函数就是检测器
# ═══════════════════════════════════════════════════════════════
def f_wind():
    u = 'wd'; o = []
    o.append('<text x="10" y="18" class="ct">风噪为什么专挑差分阵下手'
             '<tspan class="cu"> · 两件事叠在同一个频段上</tspan></text>')
    ML, W2, PH, TOP = 54, 456, 168, 54
    lo, hi = 80., 8000.
    fx = lambda f: ML + (math.log10(f) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * W2
    fy = lambda v: TOP + (36 - v) / 40 * PH
    o.append(f'<text x="{ML-42}" y="{TOP-14}" class="cax">差分阵所需均衡增益（dB）</text>')
    for v in (0, 10, 20, 30):
        o.append(f'<line x1="{ML}" y1="{fy(v):.1f}" x2="{ML+W2}" y2="{fy(v):.1f}" class="grid"/>')
        o.append(f'<text x="{ML-7}" y="{fy(v)+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    # 风噪能量集中带（定性）
    o.append(f'<rect x="{fx(lo):.1f}" y="{TOP}" width="{fx(500)-fx(lo):.1f}" height="{PH}" '
             f'fill="var(--hot)" opacity="0.10"/>')
    o.append(f'<text x="{(fx(lo)+fx(500))/2:.1f}" y="{TOP+PH-24}" class="clab" '
             f'text-anchor="middle" fill="var(--hot)">风噪能量集中区</text>')
    o.append(f'<text x="{(fx(lo)+fx(500))/2:.1f}" y="{TOP+PH-9}" class="ctick" '
             f'text-anchor="middle" fill="var(--text-3)">&lt; 500 Hz（定性）</text>')
    ff = np.logspace(math.log10(lo), math.log10(hi), 300)
    d = 0.015
    eq = -20 * np.log10(2 * np.sin(2 * np.pi * ff / c * d / 2))
    pts = ' '.join(f'{fx(f):.1f},{fy(min(v,36)):.1f}' for f, v in zip(ff, eq))
    o.append(f'<polyline points="{pts}" fill="none" stroke="var(--s2)" stroke-width="2.4"/>')
    for f in (100, 200, 500):
        v = -20 * math.log10(2 * math.sin(2 * math.pi * f / c * d / 2))
        o.append(f'<circle cx="{fx(f):.1f}" cy="{fy(v):.1f}" r="3.4" fill="var(--s2)" '
                 f'stroke="var(--surface)" stroke-width="1.4"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{fy(v)-9:.1f}" class="clab halo" '
                 f'text-anchor="middle" fill="var(--s2)">+{v:.0f}</text>')
    o.append(f'<text x="{fx(1400):.0f}" y="{fy(14):.0f}" class="clab" fill="var(--s2)">'
             f'd = 15 mm 一阶差分的均衡增益</text>')
    for f in (100, 250, 500, 1000, 2000, 4000, 8000):
        lab = f'{f//1000}k' if f >= 1000 else str(f)
        o.append(f'<line x1="{fx(f):.1f}" y1="{TOP+PH}" x2="{fx(f):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+W2/2:.0f}" y="{TOP+PH+33}" class="cax" text-anchor="middle">频率 (Hz)</text>')
    # 右侧：相干判据
    RX = 534
    o.append(f'<text x="{RX}" y="{TOP+6}" class="blab">同一条相干函数</text>')
    o.append(f'<text x="{RX}" y="{TOP+24}" class="blab">就是现成的检测器</text>')
    o.append(f'<line x1="{RX}" y1="{TOP+40}" x2="{RX+130}" y2="{TOP+40}" class="grid"/>')
    for i, (col, t, v) in enumerate([
            ('var(--s1)', '语音 / 环境声', 'γ → 1'),
            ('var(--hot)', '风噪（湍流）', 'γ → 0'),
            ('var(--hot)', '手持摩擦声', 'γ → 0')]):
        y = TOP + 64 + i * 30
        o.append(f'<rect x="{RX}" y="{y-10}" width="10" height="10" rx="2" fill="{col}"/>')
        o.append(f'<text x="{RX+16}" y="{y}" class="bsub">{t}</text>')
        o.append(f'<text x="{RX+16}" y="{y+14}" class="blab" fill="{col}">{v}</text>')
    o.append(f'<text x="{RX}" y="{TOP+PH+2}" class="bsub">低频段算 γ，设个阈值</text>')
    o.append(f'<text x="{RX}" y="{TOP+PH+18}" class="bsub">就能切模式，几乎不花算力</text>')
    o.append(f'<text x="{RX}" y="{TOP+PH+34}" class="bsub">（互谱本来就在算）</text>')
    o.append('<text x="14" y="276" class="arlab">'
             '<tspan font-weight="600">风噪不是声音，是膜片上的局部湍流压力</tspan>——各阵元间不相关，'
             '所以按白噪声处理，被 1/WNG 全额放大；</text>')
    o.append('<text x="14" y="294" class="arlab">'
             '而它的能量恰好堆在差分阵均衡增益最大的那一段。'
             '<tspan fill="var(--hot)" font-weight="600">100 Hz 处要补 +31 dB，风噪就跟着涨 31 dB。</tspan>'
             '两者相乘，</text>')
    o.append('<text x="14" y="312" class="arlab">'
             '户外的一阶差分阵可能比单个全向麦还难听——这不是算法问题，是选型阶段就要认的账。</text>')
    return svg(700, 324, '\n'.join(o),
               '差分阵所需的低频均衡增益在 100 赫兹处高达 31 dB，'
               '而风噪能量恰好集中在 500 赫兹以下的同一段，两者相乘造成双重放大；'
               '通道间相干函数可以直接把风噪与真实声场区分开', u, diag=False)

OUT['wind'] = f_wind()

# ═══════════════════════════════════════════════════════════════
# §13  STFT 里相位写错的两种后果
# ═══════════════════════════════════════════════════════════════
def f_phasebug():
    u = 'pb'; o = []
    o.append('<text x="10" y="18" class="ct">相位写错的两种后果，症状完全不同'
             '<tspan class="cu"> · 目标 60°，4 麦、d = 35 mm</tspan></text>')
    ML, W2, PH, TOP = 56, 440, 190, 54
    lo, hi = 200., 8000.
    fx = lambda f: ML + (math.log10(f) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * W2
    fy = lambda a: TOP + a / 95 * PH
    for a in (0, 30, 60, 90):
        o.append(f'<line x1="{ML}" y1="{fy(a):.1f}" x2="{ML+W2}" y2="{fy(a):.1f}" class="grid"/>')
        o.append(f'<text x="{ML-7}" y="{fy(a)+3.5:.1f}" class="ctick" text-anchor="end">{a}°</text>')
    o.append(f'<text x="{ML-40}" y="{TOP-14}" class="cax">主瓣实际指向</text>')
    ff = np.logspace(math.log10(lo), math.log10(hi), 300)
    tau = 0.035 * math.cos(math.radians(60)) / c
    # 正确：恒 60°
    o.append(f'<polyline points="{" ".join(f"{fx(f):.1f},{fy(60):.1f}" for f in ff)}" '
             f'fill="none" stroke="var(--s3)" stroke-width="2.6"/>')
    o.append(f'<text x="{fx(1500):.0f}" y="{fy(60)-9:.0f}" class="clab" fill="var(--s3)">'
             f'正确：φ = 2πfτ，恒 60°</text>')
    # bug1：漏掉 fs → 等效延迟≈0 → 恒 90°
    o.append(f'<polyline points="{" ".join(f"{fx(f):.1f},{fy(90):.1f}" for f in ff)}" '
             f'fill="none" stroke="var(--s1)" stroke-width="2.6" stroke-dasharray="6 4"/>')
    o.append(f'<text x="{fx(460):.0f}" y="{fy(90)-9:.0f}" class="clab" fill="var(--s1)">'
             f'bug ①　漏掉 f_s：等效延迟 ≈ 0，<tspan font-weight="600">根本不转向</tspan></text>')
    # bug2：只在 1 kHz 算一次相位 → cosθ ∝ 1/f
    seg, pts = [], []
    for f in ff:
        ct = math.cos(math.radians(60)) * 1000 / f
        if abs(ct) <= 1:
            pts.append(f'{fx(f):.1f},{fy(math.degrees(math.acos(ct))):.1f}')
        else:
            if pts: seg.append(pts); pts = []
    if pts: seg.append(pts)
    for pg in seg:
        o.append(f'<polyline points="{" ".join(pg)}" fill="none" stroke="var(--s2)" '
                 f'stroke-width="2.6"/>')
    o.append(f'<circle cx="{fx(1000):.1f}" cy="{fy(60):.1f}" r="4" fill="var(--s2)" '
             f'stroke="var(--surface)" stroke-width="1.5"/>')
    o.append(f'<text x="{fx(1000):.0f}" y="{fy(60)+22:.0f}" class="clab halo" '
             f'text-anchor="middle" fill="var(--s2)">只有这一点是对的</text>')
    o.append(f'<rect x="{fx(lo):.1f}" y="{TOP}" width="{fx(500)-fx(lo):.1f}" height="{PH}" '
             f'fill="var(--s1)" opacity="0.09"/>')
    o.append(f'<text x="{(fx(lo)+fx(500))/2:.1f}" y="{fy(22):.0f}" class="clab" '
             f'text-anchor="middle" fill="var(--s1)">解不存在</text>')
    o.append(f'<text x="{(fx(lo)+fx(500))/2:.1f}" y="{fy(30):.0f}" class="ctick" '
             f'text-anchor="middle" fill="var(--text-3)">cosθ &gt; 1</text>')
    o.append(f'<text x="{fx(1400):.0f}" y="{fy(80):.0f}" class="clab" fill="var(--s2)">'
             f'bug ②　只算一次相位：cosθ ∝ 1/f</text>')
    for f in (200, 500, 1000, 2000, 4000, 8000):
        lab = f'{f//1000}k' if f >= 1000 else str(f)
        o.append(f'<line x1="{fx(f):.1f}" y1="{TOP+PH}" x2="{fx(f):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+W2/2:.0f}" y="{TOP+PH+33}" class="cax" text-anchor="middle">频率 (Hz)</text>')
    RX = 518
    o.append(f'<text x="{RX}" y="{TOP+10}" class="blab" fill="var(--s1)">① 症状</text>')
    o.append(f'<text x="{RX}" y="{TOP+28}" class="bsub">转向旋钮完全没反应，</text>')
    o.append(f'<text x="{RX}" y="{TOP+44}" class="bsub">波束死死指着正侧方</text>')
    o.append(f'<text x="{RX}" y="{TOP+82}" class="blab" fill="var(--s2)">② 症状</text>')
    o.append(f'<text x="{RX}" y="{TOP+100}" class="bsub">低频直接没指向，</text>')
    o.append(f'<text x="{RX}" y="{TOP+116}" class="bsub">高频一路塌向 90°</text>')
    o.append(f'<text x="{RX}" y="{TOP+134}" class="bsub" fill="var(--s1)">很像"高频声学结构</text>')
    o.append(f'<text x="{RX}" y="{TOP+150}" class="bsub" fill="var(--s1)">有问题"，极易误判</text>')
    o.append('<text x="14" y="296" class="arlab">'
             '两个 bug 都出在同一行代码上，但<tspan font-weight="600">症状完全不同，误判的方向也完全不同</tspan>。'
             '①  查一下转向是否有效即可排除；</text>')
    o.append('<text x="14" y="314" class="arlab">'
             '②  必须扫频看指向才发现——只测 1 kHz 的话，它看起来完全正常。</text>')
    return svg(700, 326, '\n'.join(o),
               '在 STFT 域实现延迟时，漏掉采样率因子会让等效延迟趋近于零、波束根本不转向；'
               '而只在一个频率上算一次相位再全频段复用，会让指向随频率按 1 除以 f 漂移，'
               '低频无解、高频塌向正侧方', u, diag=False)

OUT['phasebug'] = f_phasebug()

json.dump(OUT, open('figs5.json', 'w'))
print('figs5.json:', ', '.join('%s %.1fKB' % (k, len(v) / 1024) for k, v in OUT.items()))
