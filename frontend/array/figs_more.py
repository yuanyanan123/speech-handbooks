#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补齐 9 张缺的图：§02 §06 §07 §08 §14 §15 §16 §19 §23。"""
import json, math, html
import numpy as np

OUT = {}
c = 343.0

def defs(u):
    return (f'<defs>'
            f'<marker id="{u}a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--text-2)"/></marker>'
            f'<marker id="{u}h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--hot)"/></marker>'
            f'<marker id="{u}s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--s1)"/></marker>'
            f'<marker id="{u}w" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--s2)"/></marker></defs>')

def box(x, y, w, h, t, s=None, cls='bx', rx=4):
    o = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>'
    if s:
        o += (f'<text x="{x+w/2}" y="{y+h/2-3}" class="blab" text-anchor="middle">{t}</text>'
              f'<text x="{x+w/2}" y="{y+h/2+11}" class="bsub" text-anchor="middle">{s}</text>')
    else:
        o += f'<text x="{x+w/2}" y="{y+h/2+4}" class="blab" text-anchor="middle">{t}</text>'
    return o

def ar(x1, y1, x2, y2, u, cls='ar', mk='a'):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}" marker-end="url(#{u}{mk})"/>'

def pa(d, u, cls='ar', mk='a'):
    return f'<path d="{d}" class="{cls}" marker-end="url(#{u}{mk})"/>'

def svg(w, h, body, lab, u, diag=True):
    cl = 'chart diag' if diag else 'chart'
    return (f'<svg viewBox="0 0 {w} {h}" class="{cl}" role="img" '
            f'aria-label="{html.escape(lab)}">\n{defs(u)}\n{body}\n</svg>')

# ═══════════════════════════════════════════════════════════════
# M1 §02  近场 / 远场  +  临界距离
# ═══════════════════════════════════════════════════════════════
def f_nearfar():
    u = 'nf'; o = []
    o.append('<text x="10" y="18" class="ct">两个都会推翻工程预期的距离'
             '<tspan class="cu"> · 左：波前还弯不弯　右：房间给的天花板</tspan></text>')
    # ── 左：波前曲率（弧 vs 弦）──
    import math as _m
    ax, ay, HA, R = 158, 150, 60, 120     # 阵列 x、中心 y、半孔径、波前半径
    dx = R - _m.sqrt(R * R - HA * HA)     # 边缘程差（像素）
    o.append('<text x="18" y="46" class="blab">① 近场：波前是弯的</text>')
    o.append(f'<line x1="{ax}" y1="{ay-HA-16}" x2="{ax}" y2="{ay+HA+16}" class="ar-d" '
             f'marker-end="none"/>')
    for i in range(4):
        yy = ay - HA + i * (2 * HA / 3)
        o.append(f'<circle cx="{ax}" cy="{yy:.0f}" r="6.5" class="bx-a"/>')
    o.append(f'<text x="{ax-14}" y="{ay+4}" class="bsub" text-anchor="end">孔径 L</text>')
    # 声源
    o.append(f'<circle cx="{ax+R}" cy="{ay}" r="6" fill="var(--s1)"/>')
    o.append(f'<text x="{ax+R}" y="{ay+24}" class="bsub" text-anchor="middle" '
             f'fill="var(--s1)">声源</text>')
    o.append(f'<line x1="{ax}" y1="{ay}" x2="{ax+R-8}" y2="{ay}" class="ar-d" marker-end="none"/>')
    o.append(f'<text x="{ax+R/2}" y="{ay-8}" class="bsub" text-anchor="middle">距离 r</text>')
    # 真实球面波前：过中心阵元，边缘外凸 dx
    o.append(f'<path d="M{ax+dx:.1f},{ay-HA-14} Q {ax-dx:.1f},{ay} {ax+dx:.1f},{ay+HA+14}" '
             f'fill="none" stroke="var(--s1)" stroke-width="2.4"/>')
    o.append(f'<text x="18" y="{ay-HA-18}" class="bsub" fill="var(--s1)">真实波前（球面）</text>')
    o.append(f'<line x1="96" y1="{ay-HA-23}" x2="{ax-dx-4:.0f}" y2="{ay-HA-23}" '
             f'stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"/>')
    # 平面波近似
    o.append(f'<line x1="{ax+dx:.1f}" y1="{ay-HA-14}" x2="{ax+dx:.1f}" y2="{ay+HA+14}" '
             f'stroke="var(--text-3)" stroke-width="1.6" stroke-dasharray="4 3"/>')
    o.append(f'<text x="18" y="{ay+HA+30}" class="bsub">平面波近似（直线）</text>')
    o.append(f'<line x1="120" y1="{ay+HA+26}" x2="{ax+dx-4:.0f}" y2="{ay+HA+26}" '
             f'stroke="var(--text-3)" stroke-width="1" stroke-dasharray="2 2"/>')
    # 边缘程差
    for sg in (-1, 1):
        yy = ay + sg * HA
        o.append(f'<line x1="{ax}" y1="{yy}" x2="{ax+dx:.1f}" y2="{yy}" stroke="var(--hot)" '
                 f'stroke-width="3.5"/>')
    o.append(f'<text x="{ax+dx+10:.0f}" y="{ay-HA+4}" class="blab" fill="var(--hot)">'
             f'Δ ≈ L²/8r</text>')
    o.append(f'<text x="{ax+dx+10:.0f}" y="{ay-HA+20}" class="bsub" fill="var(--hot)">'
             f'边缘阵元晚到这么多</text>')
    o.append('<text x="18" y="256" class="blab">平面波近似成立的条件：'
             '<tspan fill="var(--s1)">r &gt; 2L²/λ</tspan></text>')
    o.append('<text x="18" y="276" class="bsub">200 mm 孔径、8 kHz → 远场边界 1.87 m</text>')
    o.append('<text x="18" y="292" class="bsub" fill="var(--hot)">'
             '坐在桌边 1 m 的人，整段高频都还在近场</text>')
    # ── 右：直达 vs 混响 ──
    ML, W2, PH, TOP = 372, 300, 132, 66
    rc = 0.73
    fx = lambda r: ML + (math.log10(r) - math.log10(0.2)) / (math.log10(8) - math.log10(0.2)) * W2
    fy = lambda v: TOP + (16 - v) / (16 - (-26)) * PH
    o.append(f'<text x="{ML}" y="44" class="blab">② 超过临界距离，走近也没用</text>')
    for v in (10, 0, -10, -20):
        o.append(f'<line x1="{ML}" y1="{fy(v):.1f}" x2="{ML+W2}" y2="{fy(v):.1f}" class="grid"/>')
        o.append(f'<text x="{ML-7}" y="{fy(v)+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    rr = np.logspace(math.log10(0.2), math.log10(8), 260)
    direct = -20 * np.log10(rr)
    rev = np.full_like(rr, -20 * math.log10(rc))
    tot = 10 * np.log10(10 ** (direct / 10) + 10 ** (rev / 10))
    for arr, col, nm, dash in [(direct, 'var(--s1)', '直达声 −20log r', ''),
                               (rev, 'var(--s2)', '混响声　恒定', ''),
                               (tot, 'var(--text-2)', '实际收到', ' stroke-dasharray="4 3"')]:
        pts = ' '.join(f'{fx(r):.1f},{fy(max(min(v,16),-26)):.1f}' for r, v in zip(rr, arr))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"{dash}/>')
    o.append(f'<line x1="{fx(rc):.1f}" y1="{TOP}" x2="{fx(rc):.1f}" y2="{TOP+PH}" '
             f'stroke="var(--hot)" stroke-width="1.4" stroke-dasharray="3 3"/>')
    o.append(f'<text x="{fx(rc)+6:.1f}" y="{TOP+14}" class="bsub" fill="var(--hot)">'
             f'r_c = 0.73 m</text>')
    o.append(f'<rect x="{fx(rc):.1f}" y="{TOP}" width="{ML+W2-fx(rc):.1f}" height="{PH}" '
             f'class="target"/>')
    o.append(f'<text x="{(fx(rc)+ML+W2)/2:.1f}" y="{TOP+PH-10}" class="bsub" '
             f'text-anchor="middle" fill="var(--text-3)">混响主导区</text>')
    for r, lab in [(0.2, '0.2'), (0.5, '0.5'), (1, '1'), (2, '2'), (4, '4'), (8, '8 m')]:
        o.append(f'<line x1="{fx(r):.1f}" y1="{TOP+PH}" x2="{fx(r):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(r):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+W2/2:.0f}" y="{TOP+PH+33}" class="cax" text-anchor="middle">说话人距离</text>')
    for i, (col, nm) in enumerate([('var(--s1)', '直达声 ∝ 1/r'),
                                   ('var(--s2)', '混响声　与距离无关'),
                                   ('var(--text-2)', '实际收到（两者之和）')]):
        y = TOP + PH + 52 + i * 17
        o.append(f'<line x1="{ML}" y1="{y-4}" x2="{ML+16}" y2="{y-4}" stroke="{col}" stroke-width="2.4"/>')
        o.append(f'<text x="{ML+22}" y="{y}" class="bsub">{nm}</text>')
    o.append(f'<text x="{ML}" y="{TOP+PH+122}" class="bsub" fill="var(--hot)">'
             f'过了 r_c，实际收到的几乎不再随距离变——</text>')
    o.append(f'<text x="{ML}" y="{TOP+PH+138}" class="bsub" fill="var(--hot)">'
             f'掉的只有信混比。走近一点点没用。</text>')
    return svg(700, 330, '\n'.join(o),
               '左图：近场声源的球面波在阵列边缘产生 L 平方除以 8r 的程差，'
               '平面波近似只在距离大于 2L 平方除以波长时成立；'
               '右图：直达声按距离衰减而混响声恒定，两者在临界距离相交，'
               '之后接收总能量几乎不随距离变化', u)

OUT['nearfar'] = f_nearfar()

# ═══════════════════════════════════════════════════════════════
# M2 §06  前后模糊：线阵 vs 圆阵
# ═══════════════════════════════════════════════════════════════
def f_cone():
    u = 'cn'; o = []
    o.append('<text x="10" y="18" class="ct">选拓扑的第一个问题：前后要不要分'
             '<tspan class="cu"> · 这不是精度问题，是拓扑固有的</tspan></text>')
    # 左：线阵
    cx, cy = 178, 158
    o.append(f'<text x="{cx}" y="46" class="blab" text-anchor="middle">均匀线阵 ULA</text>')
    for i in range(4):
        o.append(f'<circle cx="{cx-54+i*36}" cy="{cy}" r="6" class="bx-a"/>')
    o.append(f'<line x1="{cx-84}" y1="{cy}" x2="{cx+84}" y2="{cy}" class="ar-d" marker-end="none"/>')
    o.append(f'<text x="{cx+92}" y="{cy+4}" class="bsub">阵轴</text>')
    # 模糊锥：同一夹角的一圈方向
    for sgn in (-1, 1):
        for dy in (-1, 1):
            a = math.radians(40)
            x2 = cx + sgn * 96 * math.cos(a)
            y2 = cy + dy * 96 * math.sin(a)
            o.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="var(--s2)" stroke-width="1.8" opacity="0.85"/>')
            o.append(f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="5" fill="var(--s2)"/>')
            o.append(f'<text x="{x2+sgn*12:.1f}" y="{y2+(dy*12 if dy<0 else dy*16):.1f}" '
                     f'class="bsub" fill="var(--s2)" '
                     f'text-anchor="{"end" if sgn<0 else "start"}">都报 40°</text>')
    o.append(f'<ellipse cx="{cx+73}" cy="{cy}" rx="10" ry="62" fill="none" '
             f'stroke="var(--s2)" stroke-width="1.2" stroke-dasharray="3 3"/>')
    o.append(f'<ellipse cx="{cx-73}" cy="{cy}" rx="10" ry="62" fill="none" '
             f'stroke="var(--s2)" stroke-width="1.2" stroke-dasharray="3 3"/>')
    o.append(f'<text x="{cx}" y="{cy+92}" class="bsub" text-anchor="middle" fill="var(--s2)">'
             f'这四个方向，阵列<tspan font-weight="600">完全无法区分</tspan></text>')
    o.append(f'<text x="{cx}" y="{cy+110}" class="bsub" text-anchor="middle">'
             f'因为它们与阵轴的夹角相同</text>')
    o.append(f'<text x="{cx}" y="{cy+134}" class="bsub" text-anchor="middle" fill="var(--text-3)">'
             f'cone of confusion　加多少麦都补不回来</text>')
    # 右：圆阵
    cx2 = 520
    o.append(f'<text x="{cx2}" y="46" class="blab" text-anchor="middle">均匀圆阵 UCA</text>')
    R = 46
    for k in range(6):
        t = math.radians(k * 60 - 90)
        o.append(f'<circle cx="{cx2+R*math.cos(t):.1f}" cy="{cy+R*math.sin(t):.1f}" r="6" class="bx-a"/>')
    o.append(f'<circle cx="{cx2}" cy="{cy}" r="{R}" class="grid" fill="none"/>')
    for k, lab in [(40, '40°'), (140, '140°'), (220, '220°'), (320, '320°')]:
        t = math.radians(k)
        o.append(f'<line x1="{cx2}" y1="{cy}" x2="{cx2+96*math.cos(t):.1f}" '
                 f'y2="{cy+96*math.sin(t):.1f}" stroke="var(--s3)" stroke-width="1.8"/>')
        o.append(f'<circle cx="{cx2+96*math.cos(t):.1f}" cy="{cy+96*math.sin(t):.1f}" r="5" '
                 f'fill="var(--s3)"/>')
        o.append(f'<text x="{cx2+114*math.cos(t):.1f}" y="{cy+114*math.sin(t)+4:.1f}" '
                 f'class="bsub" fill="var(--s3)" '
                 f'text-anchor="{"end" if math.cos(t)<0 else "start"}">{lab}</text>')
    o.append(f'<text x="{cx2}" y="{cy+92}" class="bsub" text-anchor="middle" fill="var(--s3)">'
             f'水平面 360° <tspan font-weight="600">全部可分</tspan></text>')
    o.append(f'<text x="{cx2}" y="{cy+110}" class="bsub" text-anchor="middle">'
             f'代价：同样麦数，单方向 DI 更低</text>')
    o.append(f'<text x="{cx2}" y="{cy+134}" class="bsub" text-anchor="middle" fill="var(--text-3)">'
             f'仰角仍不可分，要分得上平面/立体阵</text>')
    o.append('<text x="14" y="322" class="arlab">'
             '所以选型的第一问不是"几个麦"，是<tspan font-weight="600">"要不要分前后、要不要分仰角"</tspan>。'
             '贴墙放的条形音箱用线阵正好——墙已经帮它把后半边挡掉了；</text>')
    o.append('<text x="14" y="338" class="arlab">'
             '放桌子中间的设备用线阵就是错的拓扑，这一条在画板之前就得定死。</text>')
    return svg(700, 350, '\n'.join(o),
               '线阵只能分辨与阵轴的夹角，绕阵轴一圈的所有方向不可区分，形成混淆锥；'
               '圆阵在水平面内 360 度都可分辨，代价是同样麦克风数下单方向指向性更低', u)

OUT['cone'] = f_cone()

# ═══════════════════════════════════════════════════════════════
# M3 §07  差分阵结构：为什么均衡把自噪声一起放大
# ═══════════════════════════════════════════════════════════════
def f_dma():
    u = 'dm'; o = []
    o.append('<text x="10" y="18" class="ct">差分阵：指向性来自相减，代价来自把它补回来'
             '<tspan class="cu"> · 两条路径，同一个增益</tspan></text>')
    Y = 96
    o.append(box(18, Y - 30, 64, 30, 'mic 1', None))
    o.append(box(18, Y + 34, 64, 30, 'mic 2', None))
    o.append(f'<text x="50" y="{Y+82}" class="bsub" text-anchor="middle">间距 d &lt; 20 mm</text>')
    o.append(pa(f'M82,{Y-15} L128,{Y-15} L128,{Y-7} L155,{Y-7}', u))
    o.append(box(90, Y + 34, 62, 30, '延迟 τ', None))
    o.append(pa(f'M152,{Y+49} L172,{Y+49} L172,{Y+8}', u))
    o.append(f'<circle cx="172" cy="{Y-7}" r="15" class="bx-a"/>')
    o.append(f'<text x="172" y="{Y-2}" class="blab" text-anchor="middle">Σ</text>')
    o.append(f'<text x="156" y="{Y-24}" class="bsub">+</text>')
    o.append(f'<text x="186" y="{Y+16}" class="bsub">−</text>')
    o.append(ar(187, Y - 7, 226, Y - 7, u))
    o.append(box(230, Y - 27, 96, 40, '差分输出', '|H| = 2sin(kd/2)', 'bx-a'))
    o.append(ar(326, Y - 7, 366, Y - 7, u))
    o.append(box(370, Y - 27, 96, 40, '低频均衡', '×1/|H|', 'bx-h'))
    o.append(ar(466, Y - 7, 506, Y - 7, u))
    o.append(box(510, Y - 27, 80, 40, '输出', 'DI 恒 6 dB', 'bx-a'))
    # 两条路径
    o.append(f'<text x="230" y="{Y-42}" class="bsub" fill="var(--s1)">'
             f'目标信号：被压低 kd 倍</text>')
    o.append(f'<text x="370" y="{Y-42}" class="bsub" fill="var(--s1)">→ 拉回原样 ✓</text>')
    o.append(f'<path d="M50,{Y+92} L50,{Y+118} L404,{Y+118} L404,{Y+20}" class="ar-h" '
             f'marker-end="url(#{u}h)" stroke-dasharray="4 3"/>')
    o.append(f'<text x="58" y="{Y+112}" class="bsub" fill="var(--hot)">'
             f'麦克风自噪声：各通道独立，相减不减小</text>')
    o.append(f'<text x="414" y="{Y+112}" class="bsub" fill="var(--hot)">'
             f'→ 被同一个 1/|H| 放大 ✗</text>')
    o.append('<text x="14" y="252" class="arlab">'
             '两条路径穿过<tspan font-weight="600">同一个均衡器</tspan>，'
             '所以"均衡增益"和"WNG 的负值"必然是同一个数——07 节那张表最后两列相等，不是巧合。</text>')
    o.append('<text x="14" y="270" class="arlab">'
             'd = 15 mm、200 Hz 时 kd = 0.055：目标被压 25 dB，均衡补 25 dB，自噪声也就被抬了 25 dB。</text>')
    return svg(700, 284, '\n'.join(o),
               '差分阵把两路麦克风相减得到与频率无关的指向性，低频输出被压低 kd 倍，'
               '均衡器把它拉回来的同时，把各通道独立的自噪声按完全相同的倍数放大', u)

OUT['dma'] = f_dma()

# ═══════════════════════════════════════════════════════════════
# M4 §08  对数嵌套子阵
# ═══════════════════════════════════════════════════════════════
def f_nest():
    u = 'ns'; o = []
    o.append('<text x="10" y="18" class="ct">嵌套子阵：一套阵元，三个频段'
             '<tspan class="cu"> · 阵元被复用，不是各造一套</tspan></text>')
    POS = [0, 20, 40, 80, 160]
    X0, SC, Y = 52, 2.2, 78
    fx = lambda mm: X0 + mm * SC
    o.append(f'<line x1="{X0-16}" y1="{Y}" x2="{fx(160)+20}" y2="{Y}" class="ar-d" marker-end="none"/>')
    for mm in POS:
        o.append(f'<circle cx="{fx(mm):.0f}" cy="{Y}" r="6.5" class="bx-a"/>')
        o.append(f'<text x="{fx(mm):.0f}" y="{Y-16}" class="bsub" text-anchor="middle">{mm}</text>')
    o.append(f'<text x="{X0-30}" y="{Y-16}" class="bsub">mm</text>')
    SUB = [([0, 20, 40], 20, '2.9 – 8.6 kHz', 'var(--o2)', 34),
           ([0, 40, 80], 40, '1.4 – 4.3 kHz', 'var(--o3)', 66),
           ([0, 80, 160], 80, '715 Hz – 2.1 kHz', 'var(--o4)', 98)]
    for els, d, band, col, dy in SUB:
        yy = Y + dy
        o.append(f'<line x1="{fx(els[0]):.0f}" y1="{yy}" x2="{fx(els[-1]):.0f}" y2="{yy}" '
                 f'stroke="{col}" stroke-width="2.4"/>')
        for e in els:
            o.append(f'<circle cx="{fx(e):.0f}" cy="{yy}" r="4" fill="{col}"/>')
            o.append(f'<line x1="{fx(e):.0f}" y1="{Y+7}" x2="{fx(e):.0f}" y2="{yy-5}" '
                     f'stroke="{col}" stroke-width="0.9" stroke-dasharray="2 3" opacity="0.6"/>')
        o.append(f'<text x="{fx(160)+30}" y="{yy+4}" class="bsub" fill="{col}">'
                 f'间距 {d} mm　→　{band}</text>')
    o.append(f'<text x="14" y="{Y+140}" class="arlab">'
             f'5 个阵元撑起三个子阵。'
             f'<tspan font-weight="600">阵元 0 被三个子阵共用，阵元 40 和 80 各被两个共用</tspan>——'
             f'"每个频段独立造一套"要 9 个，这里只要 5 个。</text>')
    o.append(f'<text x="14" y="{Y+158}" class="arlab">'
             f'代价：各子阵的输出要做频带合成，交叠区的相位必须对齐，否则合成处出现凹陷。</text>')
    return svg(700, 252, '\n'.join(o),
               '对数嵌套阵列用五个阵元组成三个不同间距的子阵，'
               '分别覆盖高中低三个频段，阵元在子阵之间复用', u)

OUT['nest'] = f_nest()

# ═══════════════════════════════════════════════════════════════
# M5 §14  AEC 的三种位置
# ═══════════════════════════════════════════════════════════════
def f_aec():
    u = 'ae'; o = []
    o.append('<text x="10" y="18" class="ct">AEC 放哪：三种方案，代价完全不同'
             '<tspan class="cu"> · 差别就在那几个方块的先后</tspan></text>')
    ROWS = [
        ('A　AEC 在前', [('AEC ×M', 'bx-w'), ('去混响', 'bx'), ('自适应波束', 'bx-a')],
         '× M 算力', '唯一严格正确', 'var(--s3)', 52),
        ('B　波束在前', [('自适应波束', 'bx-a'), ('AEC ×1', 'bx-w'), ('后处理', 'bx')],
         '× 1 算力', '权重时变 → AEC 永不收敛', 'var(--s2)', 128),
        ('C　折中', [('固定波束', 'bx-a'), ('AEC ×2~4', 'bx-w'), ('自适应', 'bx')],
         '× 1~2 算力', '牺牲自适应能力，换可收敛', 'var(--s1)', 204),
    ]
    for name, blocks, cost, note, col, y in ROWS:
        o.append(f'<text x="14" y="{y+22}" class="blab">{name}</text>')
        o.append(f'<text x="14" y="{y+40}" class="bsub">{cost}</text>')
        x = 116
        o.append(f'<text x="{x}" y="{y-6}" class="bsub">M 路输入</text>')
        for k, (t, cls) in enumerate(blocks):
            o.append(box(x, y, 92, 36, t, None, cls))
            if k < 2:
                o.append(ar(x + 92, y + 18, x + 108, y + 18, u))
            x += 108
        o.append(ar(x, y + 18, x + 16, y + 18, u))
        o.append(f'<text x="{x+22}" y="{y+22}" class="bsub">1 路</text>')
        o.append(f'<text x="470" y="{y+52}" class="bsub" fill="{col}">{note}</text>')
    o.append(f'<line x1="14" y1="270" x2="686" y2="270" class="grid"/>')
    o.append('<text x="14" y="290" class="arlab">'
             '<tspan font-weight="600">智能音箱选 A</tspan>——扬声器就在麦旁边，回声强到不消干净后面全废，算力硬吃。　'
             '<tspan font-weight="600">会议设备选 C</tspan>——8~16 路先用固定波束降到 2~4 路再 AEC。</text>')
    o.append('<text x="14" y="308" class="arlab" fill="var(--s2)">'
             'B 只在波束完全固定时才成立。一旦上自适应就会翻车，'
             '而症状（回声偶尔冒一下）极难定位——这是这一节最值钱的一句话。</text>')
    return svg(700, 320, '\n'.join(o),
               'AEC 的三种放置方案：每通道各一个 AEC 放在最前算力翻 M 倍但严格正确；'
               '波束在前只需一个 AEC 但时变权重让它无法收敛；'
               '折中方案用固定波束降维后再做 AEC', u)

OUT['aecpos'] = f_aec()

# ═══════════════════════════════════════════════════════════════
# M6 §15  WPE：预测延迟 Δ 在时间轴上切在哪
# ═══════════════════════════════════════════════════════════════
def f_wpe():
    u = 'wp'; o = []
    o.append('<text x="10" y="18" class="ct">WPE 的全部关键，是那个预测延迟 Δ 切在哪'
             '<tspan class="cu"> · 早期反射要留，晚期混响才减</tspan></text>')
    X0, Y, W = 56, 146, 560
    o.append(f'<line x1="{X0}" y1="{Y}" x2="{X0+W}" y2="{Y}" class="ar" '
             f'marker-end="url(#{u}a)"/>')
    o.append(f'<text x="{X0+W+6}" y="{Y+4}" class="bsub">时间</text>')
    # 冲激响应示意
    import random
    random.seed(5)
    o.append(f'<line x1="{X0+12}" y1="{Y}" x2="{X0+12}" y2="{Y-62}" stroke="var(--s1)" '
             f'stroke-width="3"/>')
    o.append(f'<text x="{X0+12}" y="{Y-70}" class="bsub" text-anchor="middle" '
             f'fill="var(--s1)">直达声</text>')
    xs = [X0 + 34 + i * 13 for i in range(7)]
    for i, x in enumerate(xs):
        hgt = 46 * math.exp(-i * 0.22) * (0.55 + 0.45 * random.random())
        o.append(f'<line x1="{x}" y1="{Y}" x2="{x}" y2="{Y-hgt:.0f}" stroke="var(--s3)" '
                 f'stroke-width="2.4"/>')
    xs2 = [X0 + 146 + i * 9 for i in range(44)]
    for i, x in enumerate(xs2):
        hgt = 34 * math.exp(-i * 0.055) * (0.25 + 0.75 * random.random())
        o.append(f'<line x1="{x}" y1="{Y}" x2="{x}" y2="{Y-hgt:.0f}" stroke="var(--s2)" '
                 f'stroke-width="1.6" opacity="0.8"/>')
    # 三段标注
    o.append(f'<line x1="{X0+30}" y1="{Y+12}" x2="{X0+130}" y2="{Y+12}" stroke="var(--s3)" '
             f'stroke-width="2"/>')
    o.append(f'<text x="{X0+80}" y="{Y+28}" class="bsub" text-anchor="middle" fill="var(--s3)">'
             f'早期反射</text>')
    o.append(f'<text x="{X0+80}" y="{Y+43}" class="bsub" text-anchor="middle">提升可懂度，<tspan '
             f'font-weight="600">要留</tspan></text>')
    o.append(f'<line x1="{X0+144}" y1="{Y+12}" x2="{X0+W-20}" y2="{Y+12}" stroke="var(--s2)" '
             f'stroke-width="2"/>')
    o.append(f'<text x="{X0+340}" y="{Y+28}" class="bsub" text-anchor="middle" fill="var(--s2)">'
             f'晚期混响</text>')
    o.append(f'<text x="{X0+340}" y="{Y+43}" class="bsub" text-anchor="middle">'
             f'和目标完全相关，降噪压不掉，<tspan font-weight="600">要减</tspan></text>')
    # Δ 标注
    o.append(f'<line x1="{X0+12}" y1="{Y-86}" x2="{X0+144}" y2="{Y-86}" class="ar-d" '
             f'marker-end="none"/>')
    o.append(f'<line x1="{X0+12}" y1="{Y-90}" x2="{X0+12}" y2="{Y-82}" class="ar-d" marker-end="none"/>')
    o.append(f'<line x1="{X0+144}" y1="{Y-90}" x2="{X0+144}" y2="{Y-82}" class="ar-d" marker-end="none"/>')
    o.append(f'<text x="{X0+78}" y="{Y-94}" class="blab" text-anchor="middle" fill="var(--s2)">'
             f'预测延迟 Δ　2–3 帧（32–48 ms）</text>')
    o.append(f'<line x1="{X0+144}" y1="{Y-76}" x2="{X0+144}" y2="{Y+18}" stroke="var(--s2)" '
             f'stroke-width="1.6" stroke-dasharray="4 3"/>')
    # ── 下半：预测 → 相减 ──
    y0 = Y + 92
    o.append(pa(f'M{X0+206},{Y+22} L{X0+206},{y0-6}', u, cls='ar-w', mk='w'))
    o.append(f'<text x="{X0+214}" y="{Y+62}" class="bsub" fill="var(--s2)">'
             f'只拿 Δ 之后的帧去预测</text>')
    o.append(box(X0 + 150, y0, 160, 38, '多通道线性预测', 'L = 10–30 帧', 'bx-a'))
    o.append(pa(f'M{X0+310},{y0+19} L{X0+384},{y0+19}', u))
    o.append(f'<circle cx="{X0+400}" cy="{y0+19}" r="15" class="bx-a"/>')
    o.append(f'<text x="{X0+400}" y="{y0+24}" class="blab" text-anchor="middle">Σ</text>')
    o.append(f'<text x="{X0+382}" y="{y0+8}" class="bsub">−</text>')
    o.append(f'<text x="{X0+414}" y="{y0+46}" class="bsub">+</text>')
    o.append(f'<path d="M{X0+12},{Y+22} L{X0+12},{y0+62} L{X0+400},{y0+62} L{X0+400},{y0+38}" '
             f'class="ar" marker-end="url(#{u}a)"/>')
    o.append(f'<text x="{X0+20}" y="{y0+56}" class="bsub">当前帧 x_t 原样送来</text>')
    o.append(pa(f'M{X0+416},{y0+19} L{X0+466},{y0+19}', u))
    o.append(f'<text x="{X0+472}" y="{y0+23}" class="bsub">去混响输出</text>')

    o.append('<text x="14" y="324" class="arlab">'
             'Δ 太小 → 把直达声也预测掉了，语音发干、失真。Δ 太大 → 晚期混响漏过去，白做。'
             '<tspan font-weight="600">这一个参数决定 WPE 是有用还是有害。</tspan></text>')
    return svg(700, 338, '\n'.join(o),
               'WPE 在房间冲激响应的时间轴上，用预测延迟把早期反射排除在预测之外，'
               '只用多通道线性预测估计晚期混响并从当前帧减掉', u)

OUT['wpe'] = f_wpe()

# ═══════════════════════════════════════════════════════════════
# M7 §16  GCC-PHAT 与那条最常见的实现错误
# ═══════════════════════════════════════════════════════════════
def f_gcc():
    u = 'gc'; o = []
    o.append('<text x="10" y="18" class="ct">GCC-PHAT：扔掉幅度，只留相位'
             '<tspan class="cu"> · 以及那条改一行代码的修复</tspan></text>')
    Y = 58
    o.append(f'<text x="14" y="{Y+22}" class="bsub">x₁, x₂</text>')
    o.append(ar(56, Y + 18, 84, Y + 18, u))
    o.append(box(88, Y, 66, 36, 'FFT', None))
    o.append(ar(154, Y + 18, 182, Y + 18, u))
    o.append(box(186, Y, 92, 36, '互谱 X₁X₂*', None))
    o.append(ar(278, Y + 18, 306, Y + 18, u))
    o.append(box(310, Y, 96, 36, '除以 |·|', 'PHAT 白化', 'bx-w'))
    o.append(ar(406, Y + 18, 434, Y + 18, u))
    o.append(box(438, Y, 66, 36, 'IFFT', None))
    o.append(ar(504, Y + 18, 532, Y + 18, u))
    o.append(box(536, Y, 92, 36, 'argmax τ̂', 'θ̂ = arccos(cτ̂/d)', 'bx-a'))
    o.append(f'<text x="310" y="{Y+52}" class="bsub" fill="var(--s2)">'
             f'这一步是全部：幅度带着混响和噪声，相位带着时延</text>')
    # 频带条
    ML, W2, BY = 56, 560, 190
    fx = lambda f: ML + (math.log10(f) - math.log10(50)) / (math.log10(16000) - math.log10(50)) * W2
    o.append(f'<text x="14" y="{BY-26}" class="blab">积分要限频带，否则两端都在帮倒忙</text>')
    o.append(f'<rect x="{ML}" y="{BY}" width="{W2}" height="26" rx="3" '
             f'fill="var(--surface-2)" stroke="var(--border-2)"/>')
    o.append(f'<rect x="{fx(300):.1f}" y="{BY}" width="{fx(4900)-fx(300):.1f}" height="26" rx="3" '
             f'fill="var(--s3)" fill-opacity="0.25" stroke="var(--s3)" stroke-width="1.4"/>')
    o.append(f'<text x="{(fx(300)+fx(4900))/2:.1f}" y="{BY+17}" class="bsub" '
             f'text-anchor="middle" fill="var(--s3)">只在这一段积分</text>')
    for f, lab in [(50, '50'), (300, '300'), (1000, '1k'), (4900, 'f_alias'), (16000, '16k')]:
        o.append(f'<line x1="{fx(f):.1f}" y1="{BY+26}" x2="{fx(f):.1f}" y2="{BY+32}" class="grid"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{BY+44}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{(ML+fx(300))/2:.1f}" y="{BY-8}" class="bsub" text-anchor="middle" '
             f'fill="var(--s2)">波长太长</text>')
    o.append(f'<text x="{(ML+fx(300))/2:.1f}" y="{BY+60}" class="bsub" text-anchor="middle">'
             f'几乎不带方向信息，</text>')
    o.append(f'<text x="{(ML+fx(300))/2:.1f}" y="{BY+74}" class="bsub" text-anchor="middle">'
             f'噪声却被等权放大</text>')
    o.append(f'<text x="{(fx(4900)+ML+W2)/2:.1f}" y="{BY-8}" class="bsub" text-anchor="middle" '
             f'fill="var(--s2)">相位缠绕</text>')
    o.append(f'<text x="{(fx(4900)+ML+W2)/2:.1f}" y="{BY+60}" class="bsub" text-anchor="middle">'
             f'出现多个等高峰，</text>')
    o.append(f'<text x="{(fx(4900)+ML+W2)/2:.1f}" y="{BY+74}" class="bsub" text-anchor="middle">'
             f'即 03 节的空间混叠</text>')
    o.append('<text x="14" y="300" class="arlab">'
             '症状是"混响房间里方向乱跳、有时锁到墙上"。'
             '多数人会去换算法、加滤波——<tspan font-weight="600">其实只是积分限没设。</tspan></text>')
    return svg(700, 312, '\n'.join(o),
               'GCC-PHAT 的流程：互谱除以自身模值做相位白化后逆变换取峰；'
               '积分必须限制在 300 赫兹到空间混叠频率之间，'
               '低频不带方向信息、高频相位缠绕，两端都会引入伪峰', u)

OUT['gcc'] = f_gcc()

# ═══════════════════════════════════════════════════════════════
# M8 §19  GSS 流程
# ═══════════════════════════════════════════════════════════════
def f_gss():
    u = 'gs2'; o = []
    o.append('<text x="10" y="18" class="ct">GSS：不做盲分离，用外部先验把聚类"钉住"'
             '<tspan class="cu"> · CHiME 至今的主力前端</tspan></text>')
    o.append(box(16, 52, 128, 44, '说话人分离', '谁在什么时候说', 'bx-a'))
    o.append(f'<text x="80" y="{112}" class="bsub" text-anchor="middle">diarization 或 DOA</text>')
    o.append(f'<text x="80" y="{128}" class="bsub" text-anchor="middle" fill="var(--hot)">'
             f'质量决定上限</text>')
    o.append(pa('M144,74 L186,74', u))
    o.append(f'<text x="150" y="66" class="arlab">先验</text>')
    o.append(box(190, 52, 132, 44, 'CACGMM 空间聚类', '每个时频点属于谁', 'bx-a'))
    o.append(f'<text x="256" y="112" class="bsub" text-anchor="middle">'
             f'在先验约束下细化，不从零开始</text>')
    o.append(pa('M322,74 L364,74', u))
    o.append(f'<text x="326" y="66" class="arlab">后验</text>')
    o.append(box(368, 52, 122, 44, '加权估协方差', 'R_s / R_n 每人一套', 'bx'))
    o.append(pa('M490,74 L532,74', u))
    o.append(box(536, 52, 118, 44, 'MVDR / GEV', '每人一路干净输出', 'bx-a'))
    # 多通道输入
    o.append(f'<path d="M80,160 L80,196 L250,196" class="ar-d" marker-end="none"/>')
    o.append(f'<text x="16" y="200" class="bsub">M 路原始信号</text>')
    o.append(pa('M256,196 L256,100', u))
    o.append(pa('M430,196 L430,100', u))
    o.append(f'<path d="M256,196 L430,196 L595,196 L595,100" class="ar-d" marker-end="none"/>')
    o.append(pa('M595,196 L595,100', u))
    o.append(f'<text x="300" y="214" class="bsub">原始多通道谱贯穿始终——聚类只产生权重，不改信号</text>')
    o.append('<text x="14" y="248" class="arlab">'
             '对比纯盲分离（IVA / 神经分离）：GSS 不需要解排列问题，也不需要匹配的训练数据，'
             '因为"哪一段是谁"由外部给定。</text>')
    o.append('<text x="14" y="266" class="arlab" fill="var(--hot)">'
             '代价同样明确：整条链的上限被第一个方块锁死。'
             'diarization 错了，后面全错，而且错得很自信。</text>')
    return svg(700, 278, '\n'.join(o),
               'GSS 流程：用说话人分离或 DOA 的结果作为先验约束空间聚类，'
               '再用聚类后验加权估计每个说话人的协方差，最后解 MVDR 或 GEV 得到每人一路输出', u)

OUT['gss'] = f_gss()

# ═══════════════════════════════════════════════════════════════
# M9 §23  降维再自适应：算力花在哪
# ═══════════════════════════════════════════════════════════════
def f_cost():
    u = 'cs'; o = []
    o.append('<text x="10" y="18" class="ct">省算力最有效的一招：先降维，再自适应'
             '<tspan class="cu"> · 贵的模块都随通道数增长</tspan></text>')
    def chain(y, title, blocks, tail):
        s = [f'<text x="14" y="{y+22}" class="blab">{title}</text>']
        x = 108
        for t, sub, cls, ch in blocks:
            s.append(box(x, y, 92, 38, t, sub, cls))
            if ch: s.append(f'<text x="{x+46}" y="{y+52}" class="bsub" text-anchor="middle">{ch}</text>')
            x += 106
            if x < 108 + 106 * len(blocks):
                s.append(ar(x - 14, y + 19, x - 4, y + 19, u))
        s.append(f'<text x="{x+4}" y="{y+23}" class="bsub">{tail}</text>')
        return s
    o += chain(54, '直接做', [
        ('AEC', '×16 路', 'bx-w', ''),
        ('WPE', '×16 路', 'bx-w', ''),
        ('自适应波束', '16×16 求逆', 'bx-w', '')], '算力爆掉')
    o.append(f'<text x="520" y="90" class="bsub" fill="var(--s2)">三个最贵的模块全在 16 路上跑</text>')
    o += chain(152, '降维再做', [
        ('固定波束', '只是加权和', 'bx-a', '16 → 4 路'),
        ('AEC', '×4 路', 'bx', ''),
        ('自适应波束', '4×4 求逆', 'bx', '')], '可落地')
    o.append(f'<text x="520" y="188" class="bsub" fill="var(--s3)">AEC 省 4 倍，求逆省 ~64 倍</text>')
    o.append(f'<line x1="14" y1="230" x2="686" y2="230" class="grid"/>')
    o.append('<text x="14" y="250" class="arlab">'
             '<tspan font-weight="600">为什么可行：</tspan>固定波束几乎不花算力（一次加权求和），'
             '却把后面每个模块的通道数按比例砍掉；</text>')
    o.append('<text x="14" y="266" class="arlab">'
             '而 MVDR 的矩阵求逆是 O(M³)，砍通道数的收益是<tspan font-weight="600">立方级</tspan>的。</text>')
    o.append('<text x="14" y="288" class="arlab" fill="var(--s2)">'
             '<tspan font-weight="600">代价：</tspan>降维丢掉的空间自由度再也找不回来。'
             '固定波束指错方向，后面全部白做——所以它必须足够宽。</text>')
    return svg(700, 302, '\n'.join(o),
               '把十六路直接送进 AEC、去混响和自适应波束会让算力爆掉；'
               '先用几乎不花算力的固定波束降到四路，再做后面的模块，'
               '矩阵求逆的开销按通道数的立方下降', u)

OUT['cost'] = f_cost()

json.dump(OUT, open('figs4.json', 'w'))
print('figs4.json:', ', '.join('%s %.1fKB' % (k, len(v) / 1024) for k, v in OUT.items()))
