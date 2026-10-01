#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全书统一算例：场景俯视图 + 各方案在 1 kHz 的三项指标。"""
import json, math, html
E = json.load(open('demo_ex.json'))
P, S17 = E['par'], E['s17']
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
O = ['var(--o1)', 'var(--o2)', 'var(--o3)', 'var(--o4)']
OUT = {}

def fig_scene():
    W, H = 700, 386
    o = ['<text x="10" y="18" class="ct">全书的标准算例：'
         '<tspan font-weight="700">一间会议室、一个阵列、一个目标、一个干扰</tspan>'
         '<tspan class="cu"> · 后面每节的数字都从这里来</tspan></text>']

    # ── 左：俯视几何 ────────────────────────────────────────
    CX, CY, SC = 196, 210, 62           # SC: 每米多少像素
    o.append(f'<text x="44" y="50" class="blab">俯视图（阵列在原点，阵轴 = 横向）</text>')
    # 房间示意（只画一角）
    o.append(f'<rect x="40" y="62" width="312" height="232" rx="4" '
             f'fill="var(--surface-2)" stroke="var(--border-2)" stroke-width="1"/>')
    o.append(f'<text x="48" y="78" class="bsub" fill="var(--text-3)">'
             f'6.0 × 5.0 × 3.3 m　V = {P["V"]:.0f} m³　RT₆₀ = {P["RT60"]} s</text>')
    # 临界距离圆
    rc = P['rc']
    o.append(f'<circle cx="{CX}" cy="{CY}" r="{rc*SC:.1f}" fill="var(--s3)" '
             f'fill-opacity="0.10" stroke="var(--s3)" stroke-width="1.3" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{CX+rc*SC+8:.1f}" y="{CY+rc*SC-2:.1f}" class="bsub" fill="{S[2]}">'
             f'r_c = {rc:.2f} m</text>')
    # 阵轴与四个阵元
    o.append(f'<line x1="{CX-84}" y1="{CY}" x2="{CX+84}" y2="{CY}" class="ar-d" marker-end="none"/>')
    for m in range(4):
        x = CX + (m-1.5)*14
        o.append(f'<circle cx="{x:.1f}" cy="{CY}" r="4.6" class="bx-a"/>')
    o.append(f'<text x="{CX}" y="{CY+rc*SC+16:.1f}" class="bsub" text-anchor="middle">'
             f'4 麦　d = 35 mm</text>')
    o.append(f'<text x="{CX+90}" y="{CY+4}" class="bsub" fill="var(--text-3)">0°</text>')
    o.append(f'<text x="{CX-90}" y="{CY+4}" class="bsub" fill="var(--text-3)" '
             f'text-anchor="end">180°</text>')
    # 目标与干扰
    for th, r, col, lab, sub in [
            (P['th_s'], P['r_s'], S[0], '目标说话人', f'{P["th_s"]:.0f}°　{P["r_s"]} m'),
            (P['th_i'], P['r_i'], S[1], '干扰（风扇）', f'{P["th_i"]:.0f}°　{P["r_i"]} m')]:
        t = math.radians(th)
        x, y = CX + r*SC*math.cos(t), CY - r*SC*math.sin(t)
        x = max(50, min(342, x)); y = max(72, min(286, y))
        o.append(f'<line x1="{CX}" y1="{CY}" x2="{x:.1f}" y2="{y:.1f}" stroke="{col}" '
                 f'stroke-width="1.5" stroke-dasharray="3 2.5"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{col}"/>')
        anc = 'start' if x < CX else 'end'
        dx = 11 if x < CX else -11
        o.append(f'<text x="{x+dx:.1f}" y="{y-4:.1f}" class="bsub" fill="{col}" '
                 f'text-anchor="{anc}">{lab}</text>')
        o.append(f'<text x="{x+dx:.1f}" y="{y+9:.1f}" class="bsub" fill="{col}" '
                 f'text-anchor="{anc}">{sub}</text>')
    o.append(f'<text x="44" y="314" class="bsub" fill="{S[1]}">'
             f'说话人在 {P["r_over_rc"]:.2f} 倍临界距离外 → 直达/混响 {P["DR_dB"]:.1f} dB</text>')
    o.append(f'<text x="44" y="330" class="bsub" fill="var(--text-3)">'
             f'要把他"拉回"r_c 以内，需要 DI ≥ {E["s02"]["need_DI"]:.1f} dB——下面看谁做得到</text>')

    # ── 右：1 kHz 处三项指标 ────────────────────────────────
    RX, RW, RT, RH = 386, 292, 74, 186
    tags = [('DAS', 'DAS 延迟求和'), ('SD0', '超指向 无加载'),
            ('SD0.01', '超指向 ε=0.01'), ('MVDR', 'MVDR 已知干扰')]
    o.append(f'<text x="{RX}" y="50" class="blab">同一组参数下，四种权在 1 kHz 的表现</text>')
    lo, hi = -46., 14.
    fy = lambda v: RT + (hi-v)/(hi-lo)*RH
    for v in range(-40, 11, 10):
        y = fy(v)
        o.append(f'<line x1="{RX}" y1="{y:.1f}" x2="{RX+RW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{RX-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{RX}" y1="{fy(0):.1f}" x2="{RX+RW}" y2="{fy(0):.1f}" class="zero"/>')
    gw = RW/len(tags); bw = (gw-16)/3
    METS = [('di', S[0], 'DI'), ('wng', S[2], 'WNG'), ('att_i', S[1], '干扰衰减')]
    for i, (tag, lab) in enumerate(tags):
        gx0 = RX + i*gw + 8
        for j, (mk, col, _) in enumerate(METS):
            v = S17[tag][mk]
            x = gx0 + j*bw
            y0, y1 = fy(max(v, 0)), fy(min(v, 0))
            o.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bw-2.5:.1f}" '
                     f'height="{max(y1-y0,1):.1f}" rx="2" fill="{col}" fill-opacity="0.9"/>')
            vy = y0-4 if v >= 0 else y1+11
            o.append(f'<text x="{x+(bw-2.5)/2:.1f}" y="{vy:.1f}" class="bsub" '
                     f'text-anchor="middle" fill="{col}">{v:.0f}</text>')
        o.append(f'<text x="{gx0+(gw-16)/2:.1f}" y="{RT+RH+16:.1f}" class="ctick" '
                 f'text-anchor="middle">{lab.split()[0]}</text>')
        o.append(f'<text x="{gx0+(gw-16)/2:.1f}" y="{RT+RH+29:.1f}" class="bsub" '
                 f'text-anchor="middle" fill="var(--text-3)">'
                 f'{lab.split()[1] if len(lab.split())>1 else ""}</text>')
    for j, (mk, col, nm) in enumerate(METS):
        x = RX + j*92
        o.append(f'<rect x="{x}" y="{RT+RH+42}" width="11" height="11" rx="2" fill="{col}"/>')
        o.append(f'<text x="{x+15}" y="{RT+RH+51}" class="bsub">{nm}</text>')
    o.append(f'<text x="{RX}" y="{RT+RH+72}" class="bsub" fill="var(--text-3)">'
             f'没有一种能同时把三项做好——</text>')
    o.append(f'<text x="{RX}" y="{RT+RH+87}" class="bsub" fill="{S[1]}" font-weight="600">'
             f'04 节那条边界在一个具体场景里的样子</text>')

    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('左边是算例场景的俯视图：四麦三十五毫米阵列在原点，'
                          '目标说话人在 60 度、1.5 米，干扰在 130 度、2.2 米，'
                          '临界距离只有 0.727 米，说话人在两倍临界距离之外。'
                          '右边是同一组参数下四种波束权在 1 千赫的指向性指数、白噪声增益与干扰衰减')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['scene'] = fig_scene()
json.dump(OUT, open('figs13.json', 'w'))
for k, v in OUT.items(): print('figs13.json: %-8s %.1f KB' % (k, len(v)/1024))
