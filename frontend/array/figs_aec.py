#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§14 AEC 在阵列里放哪：把"波束一动 AEC 就废"量化出来。"""
import json, math
A = json.load(open('demo_aec.json'))
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
OUT = {}


def fig_aecq():
    W, H = 700, 392
    o = ['<text x="10" y="18" class="ct">波束权重一动，AEC 的 ERLE 上限'
         '<tspan font-weight="700">立刻塌下来</tspan>'
         '<tspan class="cu"> · 4 麦、d = 35 mm、扬声器在阵列旁 8 cm</tspan></text>']

    # ── A：ERLE 上限 vs 指向变化量 ───────────────────────────
    AX, AY, AW, AH = 46, 70, 262, 186
    ks = ['0.5', '1', '2', '5', '10', '20']
    xs = [math.log10(float(k)) for k in ks]
    xlo, xhi = math.log10(0.4), math.log10(26.)
    ylo, yhi = 0., 24.
    fx = lambda v: AX + (v - xlo) / (xhi - xlo) * AW
    fy = lambda v: AY + (yhi - v) / (yhi - ylo) * AH
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 指向只挪一点，上限就没了</text>')
    o.append(f'<text x="{AX}" y="{AY-15}" class="bsub" fill="var(--text-3)">'
             f'纵轴：换路径后滤波器还能消掉多少（dB）</text>')
    for v in range(0, 25, 6):
        y = fy(v)
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{AX-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    pts = ' '.join(f'{fx(x):.1f},{fy(A["dth"][k]):.1f}' for x, k in zip(xs, ks))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{S[1]}" stroke-width="2.4"/>')
    for x, k in zip(xs, ks):
        o.append(f'<circle cx="{fx(x):.1f}" cy="{fy(A["dth"][k]):.1f}" r="3" fill="{S[1]}"/>')
    # 25 dB 这条"能用"的线
    o.append(f'<line x1="{AX}" y1="{fy(20):.1f}" x2="{AX+AW}" y2="{fy(20):.1f}" '
             f'stroke="var(--s3)" stroke-width="1.2" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{AX+AW-2}" y="{fy(20)-6:.1f}" class="bsub" fill="var(--s3)" '
             f'text-anchor="end">20 dB：勉强可用的下限</text>')
    o.append(f'<text x="{fx(xs[0])+9:.1f}" y="{fy(A["dth"]["0.5"])+16:.1f}" class="bsub" '
             f'fill="{S[1]}">0.5° → {A["dth"]["0.5"]:.1f} dB</text>')
    o.append(f'<text x="{fx(xs[3]):.1f}" y="{fy(A["dth"]["5"])-9:.1f}" class="bsub" '
             f'fill="{S[1]}" text-anchor="middle">5° → {A["dth"]["5"]:.1f}</text>')
    for k in ks:
        x = fx(math.log10(float(k)))
        o.append(f'<line x1="{x:.1f}" y1="{AY+AH}" x2="{x:.1f}" y2="{AY+AH+4}" class="grid"/>')
        o.append(f'<text x="{x:.1f}" y="{AY+AH+17}" class="ctick" text-anchor="middle">{k}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+34}" class="cax" text-anchor="middle">'
             f'波束指向的变化量（度，对数轴）</text>')

    # ── B：时域 NLMS 的 ERLE 轨迹 ────────────────────────────
    BX, BY, BW, BH = 400, 70, 272, 186
    T = A['trace']
    nb = len(T['fix'])
    tmax = nb * T['blk_ms'] / 1000.
    blo, bhi = 0., 42.
    gx = lambda t: BX + t / tmax * BW
    gy = lambda v: BY + (bhi - min(max(v, blo), bhi)) / (bhi - blo) * BH
    o.append(f'<text x="{BX}" y="{BY-30}" class="blab">② 8 秒 NLMS：4 s 处指向挪 5°</text>')
    o.append(f'<text x="{BX}" y="{BY-15}" class="bsub" fill="var(--text-3)">'
             f'纵轴：分块实测 ERLE（100 ms 一块，dB）</text>')
    for v in range(0, 43, 10):
        y = gy(v)
        o.append(f'<line x1="{BX}" y1="{y:.1f}" x2="{BX+BW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{BX-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    tt = [(i + 0.5) * T['blk_ms'] / 1000. for i in range(nb)]
    for key, col, wd in [('fix', S[2], 3.4), ('var', S[1], 1.9)]:
        pts = ' '.join(f'{gx(t):.1f},{gy(v):.1f}' for t, v in zip(tt, T[key]))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wd}"/>')
    o.append(f'<line x1="{gx(4.0):.1f}" y1="{BY}" x2="{gx(4.0):.1f}" y2="{BY+BH}" '
             f'stroke="var(--text-3)" stroke-width="1.1" stroke-dasharray="3 3"/>')
    o.append(f'<text x="{gx(4.0)+5:.1f}" y="{BY+12}" class="bsub" fill="var(--text-3)">'
             f'波束 60°→65°</text>')
    o.append(f'<text x="{gx(1.1):.1f}" y="{gy(A["nlms"]["fix_tail"])-8:.1f}" class="bsub" '
             f'fill="{S[2]}">波束不动：收敛在 {A["nlms"]["fix_tail"]:.1f} dB</text>')
    o.append(f'<text x="{gx(4.3):.1f}" y="{gy(A["nlms"]["var_inst"])-7:.1f}" class="bsub" '
             f'fill="{S[1]}">塌到 {A["nlms"]["var_inst"]:.1f} dB</text>')
    o.append(f'<text x="{gx(4.35):.1f}" y="{gy(A["nlms"]["var_inst"])+11:.1f}" class="bsub" '
             f'fill="{S[1]}">（解析上限 {A["nlms"]["limit_5deg"]:.2f}）</text>')
    o.append(f'<text x="{gx(6.3):.1f}" y="{gy(A["nlms"]["var_late"])+15:.1f}" class="bsub" '
             f'fill="{S[1]}" text-anchor="middle">1 s 后才爬回来</text>')
    o.append(f'<text x="{gx(0.15):.1f}" y="{gy(1.5):.1f}" class="bsub" fill="var(--text-3)">'
             f'前 4 s 两条完全重合（绿线在下）</text>')
    for v in range(0, 9, 2):
        o.append(f'<line x1="{gx(v):.1f}" y1="{BY+BH}" x2="{gx(v):.1f}" y2="{BY+BH+4}" class="grid"/>')
        o.append(f'<text x="{gx(v):.1f}" y="{BY+BH+17}" class="ctick" text-anchor="middle">{v}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+34}" class="cax" text-anchor="middle">'
             f'时间（s）</text>')

    o.append(f'<line x1="14" y1="322" x2="686" y2="322" class="grid"/>')
    o.append('<text x="14" y="342" class="arlab">这两张图说的是同一件事：'
             '<tspan font-weight="600">AEC 的自适应速度追不上波束的自适应速度</tspan>。'
             f'指向只挪 1°，上限就掉到 {A["dth"]["1"]:.1f} dB；</text>')
    o.append('<text x="14" y="360" class="arlab">挪 5°，掉到 5 dB——'
             '等于回声原样透出来。而 MVDR 每帧都在重估 R，'
             '指向抖 1° 是<tspan font-weight="600">常态</tspan>，不是异常。</text>')
    o.append(f'<text x="14" y="378" class="arlab" fill="var(--s2)">'
             f'注意第二张图不是"AEC 坏了"——它一直在正常工作，'
             f'只是每次波束一动就要重新收敛 1 秒。会议里这 1 秒就是一声回声。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="'
            f'AEC 在阵列里的位置：波束指向变化 0.5 度 ERLE 上限就只剩 20 dB，变 5 度只剩 5 dB；'
            f'时域 NLMS 实测在波束跳变后塌到 5.7 dB 并需要 1 秒重新收敛">'
            + ''.join(o) + '</svg>')


OUT['aecq'] = fig_aecq()
json.dump(OUT, open('figs15.json', 'w'), ensure_ascii=False)
print('figs15.json:', {k: len(v) for k, v in OUT.items()})
