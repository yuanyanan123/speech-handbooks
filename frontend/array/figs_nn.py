#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§20 掩码估错了会怎样：直接乘 vs 只拿去估协方差。"""
import json
N = json.load(open('demo_nn.json'))
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
OUT = {}
BET = [str(b) for b in N['beta']]


def panel(o, X, Y, PW, PH, kind, idx, lab, sub, ylo, yhi, ticks, legend=False):
    xs = [N[kind]['macc'][b] for b in BET]
    xlo, xhi = 0., 0.50
    fx = lambda v: X + (v - xlo) / (xhi - xlo) * PW
    fy = lambda v: Y + (yhi - min(max(v, ylo), yhi)) / (yhi - ylo) * PH
    o.append(f'<text x="{X}" y="{Y-28}" class="blab">{lab}</text>')
    o.append(f'<text x="{X}" y="{Y-13}" class="bsub" fill="var(--text-3)">{sub}</text>')
    for v in ticks:
        y = fy(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">'
                 f'{"−" if v < 0 else ""}{abs(v)}</text>')
    series = [('mask', S[1], '直接乘掩码'), ('gev', S[0], 'GEV+BAN'), ('mvdr', S[2], 'MVDR')]
    for key, col, nm in series:
        ys = [N[kind][key][b][idx] for b in BET]
        pts = ' '.join(f'{fx(a):.1f},{fy(b):.1f}' for a, b in zip(xs, ys))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.3"/>')
        for a, b in zip(xs, ys):
            o.append(f'<circle cx="{fx(a):.1f}" cy="{fy(b):.1f}" r="2.7" fill="{col}"/>')
    for v in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5):
        o.append(f'<line x1="{fx(v):.1f}" y1="{Y+PH}" x2="{fx(v):.1f}" y2="{Y+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{Y+PH+17}" class="ctick" text-anchor="middle">{v:.1f}</text>')
    o.append(f'<text x="{X+PW/2:.0f}" y="{Y+PH+34}" class="cax" text-anchor="middle">'
             f'掩码误差 平均|m̂−m|</text>')
    if legend:
        for i, (key, col, nm) in enumerate(series):
            yy = Y + 14 + i * 16
            o.append(f'<line x1="{X+PW-116}" y1="{yy-4}" x2="{X+PW-96}" y2="{yy-4}" '
                     f'stroke="{col}" stroke-width="2.6"/>')
            o.append(f'<text x="{X+PW-90}" y="{yy}" class="bsub" fill="{col}">{nm}</text>')


def fig_maskerr():
    W, H = 700, 470
    Y, PH = 84, 168
    o = ['<text x="10" y="18" class="ct">掩码估错了，'
         '<tspan font-weight="700">两条路的下场完全不同</tspan>'
         '<tspan class="cu"> · 12 节那个场景，输入 SNR '
         f'{N["in_snr"]:.2f} dB，理想比值掩码逐步掺进随机掩码</tspan></text>']
    o.append('<text x="10" y="38" class="bsub" fill="var(--text-3)">'
             '同一份掩码：一条路直接乘到频谱上（纯神经增强的等价物），'
             '一条路只拿去估两个协方差、再解出一个每频点固定的 w。</text>')

    panel(o, 46, Y, 250, PH, 'iid', 0, '① 输出 SNR', '越高越好（dB）',
          -2., 14., [0, 4, 8, 12], legend=True)
    panel(o, 392, Y, 250, PH, 'iid', 1, '② 目标被改成了什么样',
          '越高失真越小（dB）', -12., 18., [-12, -6, 0, 6, 12, 18])

    o.append(f'<text x="46" y="{Y+PH+56}" class="bsub" fill="var(--s2)">'
             f'直接乘：掩码一烂，SNR 从 {N["iid"]["mask"]["0.0"][0]:.1f} 一路掉到 '
             f'{N["iid"]["mask"]["1.0"][0]:.1f} dB</text>')
    o.append(f'<text x="392" y="{Y+PH+56}" class="bsub" fill="var(--s3)">'
             f'MVDR 那条几乎是平的：{N["iid"]["mvdr"]["0.0"][1]:.1f} → '
             f'{N["iid"]["mvdr"]["1.0"][1]:.1f} dB，掩码全随机也不动</text>')
    o.append(f'<text x="392" y="{Y+PH+72}" class="bsub" fill="var(--s1)">'
             f'GEV 没有无失真约束，掩码一坏就崩：'
             f'{N["iid"]["gev"]["0.0"][1]:.1f} → −{abs(N["iid"]["gev"]["1.0"][1]):.1f} dB</text>')

    FT = [
        ('MVDR 那条平，<b>不是因为协方差估得准</b>——协方差本身错得很厉害。', None),
        ('掩码只通过两条路影响它：导向向量 a，和噪声协方差 R_n。', None),
        ('a 是 R_s 的主特征向量，由能量最强的方向定，掩码只是重新加权——'
         '全随机掩码下 cos 仍有 %.4f。' % N['steer']['cos']['1.0'], None),
        ('而 w^H a = 1 这条约束跟掩码无关，目标被钉死了。R_n 错了只是零点放歪，'
         '扩散噪声本来也没多少可放。', None),
        ('代价是波束的 SNR 起点就低（%.1f vs %.1f dB）——它本来就不该单独用，'
         '18 节的后置滤波补的正是这一段。' % (N['iid']['mvdr']['0.0'][0],
                                       N['iid']['mask']['0.0'][0]), 'var(--s2)'),
        ('它真正的边界是<b>对抗性</b>的错法：掩码整个反过来，R_n 变成目标的协方差，'
         'SNR 掉到 −%.2f dB。' % abs(N['adv_mvdr'][0]), 'var(--s2)'),
        ('GEV 没有无失真约束，掩码一坏方向就没人钉着——失真最低到 −%.0f dB，'
         '这是它比 MVDR 脆的全部原因。' % abs(N['blk']['gev']['1.0'][1]), 'var(--text-3)'),
    ]
    y0 = H - 18 - (len(FT) - 1) * 17
    o.append(f'<line x1="14" y1="{y0-20}" x2="686" y2="{y0-20}" class="grid"/>')
    for i2, (t, col) in enumerate(FT):
        t = t.replace('<b>', '<tspan font-weight="600">').replace('</b>', '</tspan>')
        t = t.replace('w^H a', 'w<tspan baseline-shift="super" font-size="9">H</tspan>a')
        c = f' fill="{col}"' if col else ''
        o.append(f'<text x="14" y="{y0 + i2 * 17}" class="arlab"{c}>{t}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="'
            f'掩码误差对两条路线的影响：直接乘掩码时输出信噪比随掩码变差而大幅下降，'
            f'而把掩码只用于估协方差的 MVDR 几乎完全不受影响，'
            f'GEV 因为没有无失真约束在掩码变差时失真崩溃">'
            + ''.join(o) + '</svg>')


OUT['maskerr'] = fig_maskerr()
json.dump(OUT, open('figs18.json', 'w'), ensure_ascii=False)
print('figs18.json:', {k: len(v) for k, v in OUT.items()})
