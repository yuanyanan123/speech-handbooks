#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§15 WPE：加权、延迟、通道数各自值多少。"""
import json, math, html
D = json.load(open('wpe_data.json'))
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
OUT = {}

def fig_wpe():
    W, H = 700, 374
    TOP, PH = 66, 200
    o = ['<text x="10" y="18" class="ct">WPE 的三个设计量，'
         '<tspan font-weight="700">各自值多少 dB</tspan>'
         '<tspan class="cu"> · 4 麦、<tspan font-weight="600">合成房间</tspan>'
         '（STFT 域指数衰减随机 RIR）——模型与数据完全一致的理想情形</tspan></text>']

    # ── A：加权 vs 包络动态 ────────────────────────────────
    AX, AW = 44, 232
    xlo, xhi = 0., 56.
    ylo, yhi = 12., 50.
    fx = lambda v: AX + (v-xlo)/(xhi-xlo)*AW
    fy = lambda v: TOP + (yhi-v)/(yhi-ylo)*PH
    o.append(f'<text x="{AX}" y="{TOP-16}" class="blab">① 为什么要"加权"</text>')
    o.append(f'<text x="{AX}" y="{TOP-3}" class="bsub" fill="var(--text-3)">'
             f'纵轴：残余混响比（越高越好）</text>')
    for v in range(20, 51, 10):
        y = fy(v)
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{AX-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{AX}" y1="{fy(D["inp"]):.1f}" x2="{AX+AW}" y2="{fy(D["inp"]):.1f}" '
             f'stroke="var(--text-3)" stroke-width="1.2" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{AX+4}" y="{fy(D["inp"])-6:.1f}" class="bsub" fill="var(--text-3)">'
             f'不处理：{D["inp"]:.1f} dB</text>')
    for key, col, lab in [('w', S[2], 'WPE（按 1/λ 加权）'), ('u', 'var(--s2)', '普通线性预测')]:
        pts = ' '.join(f'{fx(a):.1f},{fy(min(max(b,ylo),yhi)):.1f}' for a, b in zip(D['dyn'], D[key]))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.4"/>')
        for a, b in zip(D['dyn'], D[key]):
            o.append(f'<circle cx="{fx(a):.1f}" cy="{fy(b):.1f}" r="2.8" fill="{col}"/>')
    o.append(f'<text x="{fx(2):.1f}" y="{fy(47):.1f}" class="bsub" fill="{S[2]}">'
             f'WPE（按 1/λ 加权）</text>')
    o.append(f'<text x="{fx(2):.1f}" y="{fy(43.3):.1f}" class="bsub" fill="var(--s2)">'
             f'普通线性预测（不加权）</text>')
    # 差值标注
    i = len(D['dyn'])-2
    o.append(f'<line x1="{fx(D["dyn"][i]):.1f}" y1="{fy(D["w"][i]):.1f}" '
             f'x2="{fx(D["dyn"][i]):.1f}" y2="{fy(D["u"][i]):.1f}" stroke="{S[1]}" '
             f'stroke-width="1.6"/>')
    o.append(f'<text x="{fx(D["dyn"][i])-6:.1f}" y="{(fy(D["w"][i])+fy(D["u"][i]))/2+4:.1f}" '
             f'class="bsub" fill="{S[1]}" text-anchor="end">+{D["w"][i]-D["u"][i]:.1f} dB</text>')
    for v in [0, 20, 40]:
        o.append(f'<line x1="{fx(v):.1f}" y1="{TOP+PH}" x2="{fx(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{v}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">'
             f'语音包络的动态范围（dB）</text>')
    o.append(f'<text x="{AX}" y="{TOP+PH+52}" class="bsub" fill="var(--text-3)">'
             f'真实语音在 35–45 dB 这一段</text>')

    # ── B：预测延迟 D ──────────────────────────────────────
    BX, BW = 328, 160
    blo, bhi = 0., 11.
    gx = lambda v: BX + (v-blo)/(bhi-blo)*BW
    gy = lambda v: TOP + (yhi-v)/(yhi-ylo)*PH
    o.append(f'<text x="{BX}" y="{TOP-16}" class="blab">② 预测延迟 D</text>')
    o.append(f'<text x="{BX}" y="{TOP-3}" class="bsub" fill="var(--text-3)">'
             f'本例的早期窗是 3 帧</text>')
    for v in range(20, 51, 10):
        o.append(f'<line x1="{BX}" y1="{gy(v):.1f}" x2="{BX+BW}" y2="{gy(v):.1f}" class="grid"/>')
    pts = ' '.join(f'{gx(a):.1f},{gy(min(max(b,ylo),yhi)):.1f}'
                   for a, b in zip(D['D'][1:], D['Dv'][1:]))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{S[0]}" stroke-width="2.4"/>')
    for a, b in zip(D['D'][1:], D['Dv'][1:]):
        o.append(f'<circle cx="{gx(a):.1f}" cy="{gy(min(max(b,ylo),yhi)):.1f}" r="2.8" fill="{S[0]}"/>')
    o.append(f'<circle cx="{gx(3):.1f}" cy="{gy(D["Dv"][3]):.1f}" r="5" fill="none" '
             f'stroke="{S[2]}" stroke-width="2"/>')
    o.append(f'<text x="{gx(3)+9:.1f}" y="{gy(D["Dv"][3])+14:.1f}" class="bsub" fill="{S[2]}">'
             f'D = 早期窗</text>')
    o.append(f'<line x1="{gx(0):.1f}" y1="{gy(ylo):.1f}" x2="{gx(0):.1f}" y2="{gy(yhi):.1f}" '
             f'stroke="var(--s2)" stroke-width="1.6" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{gx(0.3):.1f}" y="{gy(47):.1f}" class="bsub" fill="var(--s2)">'
             f'D = 0：直达也被预测掉了</text>')
    o.append(f'<text x="{gx(0.3):.1f}" y="{gy(43.3):.1f}" class="bsub" fill="var(--s2)">'
             f'（输出已经不是目标了）</text>')
    o.append(f'<text x="{gx(5.5):.1f}" y="{gy(14):.1f}" class="bsub" fill="var(--text-3)" '
             f'text-anchor="middle">D 太大 → 尾巴留在里面</text>')
    for v in [0, 3, 6, 10]:
        o.append(f'<line x1="{gx(v):.1f}" y1="{TOP+PH}" x2="{gx(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{gx(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{v}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">D（帧）</text>')

    # ── C：通道数 M ────────────────────────────────────────
    CX, CW = 530, 150
    o.append(f'<text x="{CX}" y="{TOP-16}" class="blab">③ 通道数 M</text>')
    o.append(f'<text x="{CX}" y="{TOP-3}" class="bsub" fill="var(--text-3)">'
             f'1 → 2 那一跳是关键</text>')
    for v in range(20, 51, 10):
        o.append(f'<line x1="{CX}" y1="{gy(v):.1f}" x2="{CX+CW}" y2="{gy(v):.1f}" class="grid"/>')
    bw = CW/len(D['M'])
    for i, (m, v) in enumerate(zip(D['M'], D['Mv'])):
        x = CX + i*bw + 4
        hh = gy(ylo)-gy(v)
        col = 'var(--s2)' if m == 1 else S[0]
        o.append(f'<rect x="{x:.1f}" y="{gy(v):.1f}" width="{bw-8:.1f}" height="{hh:.1f}" rx="2.5" '
                 f'fill="{col}" fill-opacity="0.85"/>')
        o.append(f'<text x="{x+(bw-8)/2:.1f}" y="{gy(v)-5:.1f}" class="bsub" text-anchor="middle" '
                 f'fill="{col}">{v:.0f}</text>')
        o.append(f'<text x="{x+(bw-8)/2:.1f}" y="{TOP+PH+17:.1f}" class="ctick" '
                 f'text-anchor="middle">{m}</text>')
    o.append(f'<line x1="{CX}" y1="{gy(ylo):.1f}" x2="{CX+CW}" y2="{gy(ylo):.1f}" class="grid"/>')
    o.append(f'<text x="{CX+CW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">M</text>')
    o.append(f'<text x="{CX}" y="{TOP+PH+52}" class="bsub" fill="var(--text-3)">'
             f'单通道逆滤波做不到的事，</text>')
    o.append(f'<text x="{CX}" y="{TOP+PH+66}" class="bsub" fill="var(--text-3)">'
             f'两通道就能做到（+{D["Mv"][1]-D["Mv"][0]:.0f} dB）</text>')

    o.append(f'<text x="14" y="{H-10}" class="arlab">'
             f'三个量里，<tspan font-weight="600">D 定成败、M 定上限、加权定实际拿到多少</tspan>。'
             f'K（预测阶）反而不敏感——因为房间尾巴在模型里是"极点"，短滤波器就能翻掉。'
             f'<tspan fill="var(--s2)">同样三个量在真实房间里差很多，见本节末的算例。</tspan></text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('三张小图：一，按 1 除以瞬时功率加权的 WPE 随语音包络动态范围增大而越来越好，'
                          '不加权的普通线性预测则停在二十一分贝不动，语音式动态下相差十七分贝。'
                          '二，预测延迟等于早期窗时最好，等于零时连直达声一起被预测掉，太大则尾巴留在里面。'
                          '三，通道数从一增到二带来十六分贝的跳变，再往上收益很小')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['wpe'] = fig_wpe()
json.dump(OUT, open('figs12.json', 'w'))
for k, v in OUT.items(): print('figs12.json: %-6s %.1f KB' % (k, len(v)/1024))
