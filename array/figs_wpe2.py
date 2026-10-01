#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§15 WPE 跑在 12 节那间真实仿真房间里：Δ、K、M 各值多少 dB。"""
import json
W = json.load(open('demo_wpe.json'))
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
OUT = {}


def panel(o, X, Y, PW, PH, keys, lab, xlab, ylo, yhi, ticks, best=None,
          col=None, extra=None, exlab=None):
    col = col or S[0]
    n = len(keys)
    fx = lambda i: X + (i + 0.5) / n * PW
    fy = lambda v: Y + (yhi - min(max(v, ylo), yhi)) / (yhi - ylo) * PH
    o.append(f'<text x="{X}" y="{Y-14}" class="blab">{lab}</text>')
    for v in ticks:
        y = fy(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">'
                 f'{"−" if v < 0 else ""}{abs(v)}</text>')
    if ylo <= W['in'] <= yhi:
        o.append(f'<line x1="{X}" y1="{fy(W["in"]):.1f}" x2="{X+PW}" y2="{fy(W["in"]):.1f}" '
                 f'stroke="var(--text-3)" stroke-width="1.1" stroke-dasharray="4 3"/>')
    if extra:
        pos = {k: i for i, (k, v) in enumerate(keys)}
        pe = [(pos[k], v) for k, v in extra if k in pos]
        pts = ' '.join(f'{fx(i):.1f},{fy(v):.1f}' for i, v in pe)
        o.append(f'<polyline points="{pts}" fill="none" stroke="{S[0]}" stroke-width="1.9" '
                 f'stroke-dasharray="5 3"/>')
        for i, v in pe:
            o.append(f'<circle cx="{fx(i):.1f}" cy="{fy(v):.1f}" r="2.4" fill="{S[0]}"/>')
        if exlab:
            i, v = pe[exlab[0]]
            o.append(f'<text x="{fx(i)+exlab[1]:.1f}" y="{fy(v)+exlab[2]:.1f}" class="bsub" '
                     f'fill="{S[0]}">{exlab[3]}</text>')
    pts = ' '.join(f'{fx(i):.1f},{fy(v):.1f}' for i, (k, v) in enumerate(keys))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.3"/>')
    for i, (k, v) in enumerate(keys):
        hit = (best is not None and k == best)
        o.append(f'<circle cx="{fx(i):.1f}" cy="{fy(v):.1f}" r="{4.2 if hit else 2.9}" '
                 f'fill="{S[2] if hit else col}"/>')
        if hit:
            o.append(f'<text x="{fx(i):.1f}" y="{fy(v)-10:.1f}" class="bsub" fill="{S[2]}" '
                     f'text-anchor="middle">{v:.2f}</text>')
        o.append(f'<text x="{fx(i):.1f}" y="{Y+PH+15}" class="ctick" '
                 f'text-anchor="middle">{k}</text>')
    o.append(f'<text x="{X+PW/2:.0f}" y="{Y+PH+32}" class="cax" text-anchor="middle">{xlab}</text>')


def fig_wpereal():
    WD, H = 700, 408
    Y, PH = 90, 164
    g = W['best'] - W['in']
    o = ['<text x="10" y="18" class="ct">同一个 WPE，'
         '<tspan font-weight="700">放进真实房间只剩几分之一的收益</tspan>'
         '<tspan class="cu"> · 12 节那间会议室，RT₆₀ = 0.6 s，4 麦，目标 = 直达 + 前 50 ms</tspan></text>']
    o.append(f'<text x="10" y="38" class="bsub" fill="var(--text-3)">'
             f'纵轴都是"早期成分 / 晚期混响"之比（dB，越高越好）；'
             f'灰虚线 = 完全不处理的 {W["in"]:.2f} dB。三张图都停在同一个工作点 '
             f'Δ={W["best_delay"]}、K={W["best_taps"]}、M=4。</text>')

    dl = [(str(k), W['delay'][str(k)]) for k in (0, 1, 2, 3, 4, 6)]
    un = [(str(k), W['unw_delay'][str(k)]) for k in (1, 2, 3, 4)]
    panel(o, 46, Y, 186, PH, dl, '① 预测延迟 Δ（帧）', 'Δ（一帧 16 ms）',
          -6., 9., [-6, -3, 0, 3, 6, 9], best='3', col=S[1],
          extra=un, exlab=(0, -4, -8, '不加权'))
    o.append(f'<text x="46" y="{Y+PH+50}" class="bsub" fill="var(--s2)">'
             f'Δ=0 时 −{abs(W["delay"]["0"]):.1f} dB——把直达声也一起预测掉了</text>')
    o.append(f'<text x="{46+186*0.5:.0f}" y="{Y+PH+66}" class="bsub" fill="var(--text-3)" '
             f'text-anchor="middle">最优 Δ=3 → 48 ms，正好是 50 ms 早期窗</text>')

    tp = [(k, W['taps'][k]) for k in ['2', '5', '10', '20', '30']]
    panel(o, 292, Y, 150, PH, tp, '② 预测阶数 K（帧）', 'K',
          5.5, 8., [6, 7, 8], best=str(W['best_taps']), col=S[0])
    o.append(f'<text x="{292+150*0.5:.0f}" y="{Y+PH+50}" class="bsub" fill="var(--text-3)" '
             f'text-anchor="middle">K·16 ms ≈ 160 ms</text>')
    o.append(f'<text x="{292+150*0.5:.0f}" y="{Y+PH+66}" class="bsub" fill="var(--text-3)" '
             f'text-anchor="middle">再长反而变差（估计方差）</text>')

    mm = [(k, W['M'][k]) for k in ['1', '2', '3', '4']]
    panel(o, 500, Y, 136, PH, mm, '③ 通道数 M', 'M',
          3.5, 8., [4, 5, 6, 7, 8], best='4', col=S[0])
    o.append(f'<text x="{500+136*0.5:.0f}" y="{Y+PH+50}" class="bsub" fill="var(--text-3)" '
             f'text-anchor="middle">1→2 就拿走 {W["M"]["2"]-W["M"]["1"]:+.2f} dB</text>')
    o.append(f'<text x="{500+136*0.5:.0f}" y="{Y+PH+66}" class="bsub" fill="var(--text-3)" '
             f'text-anchor="middle">单通道几乎等于不处理</text>')

    o.append('<line x1="14" y1="344" x2="686" y2="344" class="grid"/>')
    o.append(f'<text x="14" y="364" class="arlab">'
             f'最优工作点把早期/晚期比从 {W["in"]:.2f} dB 抬到 '
             f'<tspan font-weight="600">{W["best"]:.2f} dB</tspan>，净赚 {g:.2f} dB。'
             f'合成房间里同一份代码能做到 20 dB 以上——差的不是算法，</text>')
    o.append('<text x="14" y="382" class="arlab">'
             '是真实 RIR 的晚期部分并不服从那个低阶线性预测模型。</text>')
    o.append(f'<text x="14" y="400" class="arlab" fill="var(--s1)">'
             f'虚线那条说明 1/λ 加权买的是什么：不是无条件加分，而是'
             f'<tspan font-weight="600">敢用短延迟</tspan>。'
             f'Δ=1 时它值 {W["delay"]["1"]-W["unw_delay"]["1"]:+.2f} dB，'
             f'Δ=3 时 {W["delay"]["3"]-W["unw_delay"]["3"]:+.2f} dB，'
             f'Δ=4 时只剩 {W["delay"]["4"]-W["unw_delay"]["4"]:+.2f} dB。</text>')
    return (f'<svg viewBox="0 0 {WD} {H}" class="chart" role="img" aria-label="'
            f'WPE 在真实仿真会议室里的实测：预测延迟 3 帧即 48 毫秒最优，阶数 10、'
            f'通道数 4，总收益只有 3.5 dB；不加权的普通线性预测在短延迟处会把目标也削掉">'
            + ''.join(o) + '</svg>')


OUT['wpereal'] = fig_wpereal()
json.dump(OUT, open('figs16.json', 'w'), ensure_ascii=False)
print('figs16.json:', {k: len(v) for k, v in OUT.items()})
