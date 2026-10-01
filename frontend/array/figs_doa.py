#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§16 算例：同一段录音，三种做法三个结果 + SRP 曲面有多平。"""
import json, math, html
import numpy as np
D = json.load(open('demo_doa.json'))
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
OUT = {}

def fig():
    W, H = 700, 348
    ML, PW, TOP, PH = 48, 380, 62, 196
    fx = lambda t: ML + t/180*PW
    fy = lambda v: TOP + (1.06-v)/(1.06-(-0.04))*PH
    o = ['<text x="10" y="18" class="ct">同一段录音，三种做法，'
         '<tspan font-weight="700">三个不同的答案</tspan>'
         '<tspan class="cu"> · 标准算例：目标 60°、干扰 130°、RT₆₀ 0.6 s</tspan></text>',
         f'<text x="{ML}" y="{TOP-16}" class="blab">SRP-PHAT 曲面（全阵列、4 帧、300–4900 Hz）</text>']
    for v in (0, .5, 1):
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v:g}</text>')
    th, Pn = D['srp_curve']['th'], D['srp_curve']['P']
    pts = ' '.join(f'{fx(t):.1f},{fy(v):.1f}' for t, v in zip(th, Pn))
    o.append(f'<polygon points="{fx(th[0]):.1f},{fy(0):.1f} {pts} {fx(th[-1]):.1f},{fy(0):.1f}" '
             f'fill="{S[0]}" fill-opacity="0.12"/>')
    o.append(f'<polyline points="{pts}" fill="none" stroke="{S[0]}" stroke-width="2.4"/>')
    # 真值与估计
    o.append(f'<line x1="{fx(60):.1f}" y1="{fy(-0.04):.1f}" x2="{fx(60):.1f}" y2="{fy(1.06):.1f}" '
             f'stroke="{S[2]}" stroke-width="1.6" stroke-dasharray="5 3"/>')
    o.append(f'<text x="{fx(60)-6:.1f}" y="{fy(1.02):.1f}" class="bsub" fill="{S[2]}" '
             f'text-anchor="end">真值 60°</text>')
    pk = D['srp_4']['peak']
    o.append(f'<circle cx="{fx(pk):.1f}" cy="{fy(1.0):.1f}" r="4.5" fill="var(--surface)" '
             f'stroke="{S[1]}" stroke-width="2"/>')
    o.append(f'<text x="{fx(pk)+8:.1f}" y="{fy(1.0)+4:.1f}" class="bsub" fill="{S[1]}">'
             f'峰 {pk:.1f}°</text>')
    # −3 dB 宽度
    w3 = D['srp_4']['w3db']
    o.append(f'<line x1="{fx(max(1,pk-w3/2)):.1f}" y1="{fy(0.5):.1f}" '
             f'x2="{fx(min(179,pk+w3/2)):.1f}" y2="{fy(0.5):.1f}" stroke="{S[1]}" '
             f'stroke-width="2" stroke-dasharray="2 2"/>')
    o.append(f'<text x="{fx(pk):.1f}" y="{fy(0.44):.1f}" class="bsub" fill="{S[1]}" '
             f'text-anchor="middle">半高宽 {w3:.0f}°——几乎是平的</text>')
    for t in (0, 45, 90, 135, 180):
        o.append(f'<line x1="{fx(t):.1f}" y1="{TOP+PH}" x2="{fx(t):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(t):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{t}°</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">'
             f'扫描角度（从阵轴量起）</text>')

    # ── 右：三种做法的结果 ──────────────────────────────────
    RX = 452
    o.append(f'<text x="{RX}" y="{TOP-16}" class="blab">三种做法的结果</text>')
    rows = [('两麦 GCC-PHAT　不限带', D['pair_full'][1], '锁到了干扰（130°）', 'var(--s2)'),
            ('两麦 GCC-PHAT　限 300–3k', D['pair_band'][1], '锁到了混响（0 时延）', 'var(--s2)'),
            ('全阵列 SRP　4 帧', D['srp_4']['peak'], '可用，但只有 ±4°', 'var(--s3)'),
            ('全阵列 SRP　16 帧', D['srp_16']['peak'], '越平均越糟', 'var(--s2)'),
            ('全阵列 SRP　64 帧', D['srp_64']['peak'], '混响把峰拉向 90°', 'var(--s2)')]
    for i, (nm, val, note, col) in enumerate(rows):
        y = TOP + 6 + i*42
        o.append(f'<text x="{RX}" y="{y}" class="bsub">{nm}</text>')
        o.append(f'<text x="{RX}" y="{y+16}" class="blab" fill="{col}">{val:.1f}°</text>')
        o.append(f'<text x="{RX+52}" y="{y+16}" class="bsub" fill="{col}">{note}</text>')
        o.append(f'<line x1="{RX}" y1="{y+25}" x2="{RX+232}" y2="{y+25}" class="grid"/>')
    o.append(f'<text x="14" y="{H-26}" class="arlab">'
             f'真值 60°。<tspan font-weight="600">失败不是算法差，'
             f'是这个尺寸的阵列在这种混响下本来就没有角度分辨率</tspan>——'
             f'SRP 曲面的半高宽有 {w3:.0f}°。</text>')
    o.append(f'<text x="14" y="{H-10}" class="arlab">'
             f'想要真的定位，只有两条路：加大孔径，或者接受"宽波束 + 不精确指向"。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('左边是 SRP-PHAT 的角度功率曲面，峰在 63.5 度而真值是 60 度，'
                          '但半高宽达到 112 度，曲面几乎是平的。'
                          '右边列出三种做法的结果：两麦 GCC-PHAT 不限带时锁到干扰方向，'
                          '限带后锁到混响造成的零时延，全阵列 SRP 用四帧才给出可用的估计，'
                          '平均帧数越多反而越偏向 90 度')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['doaex'] = fig()
json.dump(OUT, open('figs14.json', 'w'))
print('figs14.json: doaex %.1f KB' % (len(OUT['doaex'])/1024))
