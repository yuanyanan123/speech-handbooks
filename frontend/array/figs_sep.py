#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§19 两说话人分离：W-disjoint、空间可分度、各方法真 SIR。"""
import json, math
import numpy as np
D = json.load(open('demo_sep.json'))
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
OUT = {}


def fig_sepq():
    W, H = 700, 608
    o = ['<text x="10" y="18" class="ct">两个人同时说，'
         '<tspan font-weight="700">4 麦能分开多少</tspan>'
         '<tspan class="cu"> · 12 节那间会议室，60° 与 130°，'
         f'重叠占"有人说话"时间的 {D["overlap"]:.0f}%</tspan></text>']

    # ── ① W-disjoint 累积曲线 ────────────────────────────────
    AX, AY, AW, AH = 46, 68, 250, 150
    ks = [0, 3, 6, 10, 20]
    fx = lambda v: AX + v / 22. * AW
    fy = lambda v: AY + (100 - v) / 45. * AH
    o.append(f'<text x="{AX}" y="{AY-30}" class="blab">① 两人真的很少抢同一个格子</text>')
    o.append(f'<text x="{AX}" y="{AY-15}" class="bsub" fill="var(--text-3)">'
             f'纵轴：主导的那个人领先对方 &gt; X dB 的时频格占比</text>')
    for v in (60, 70, 80, 90, 100):
        y = fy(v)
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{AX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}%</text>')
    pts = ' '.join(f'{fx(k):.1f},{fy(D["wdo"][str(k)]):.1f}' for k in ks)
    o.append(f'<polyline points="{pts}" fill="none" stroke="{S[0]}" stroke-width="2.4"/>')
    for k in ks:
        v = D['wdo'][str(k)]
        o.append(f'<circle cx="{fx(k):.1f}" cy="{fy(v):.1f}" r="3" fill="{S[0]}"/>')
        o.append(f'<line x1="{fx(k):.1f}" y1="{AY+AH}" x2="{fx(k):.1f}" y2="{AY+AH+4}" class="grid"/>')
        o.append(f'<text x="{fx(k):.1f}" y="{AY+AH+17}" class="ctick" text-anchor="middle">{k}</text>')
    o.append(f'<circle cx="{fx(6):.1f}" cy="{fy(D["wdo"]["6"]):.1f}" r="4.6" fill="none" '
             f'stroke="{S[2]}" stroke-width="1.8"/>')
    o.append(f'<text x="{fx(6)+8:.1f}" y="{fy(D["wdo"]["6"])-8:.1f}" class="bsub" fill="{S[2]}">'
             f'6 dB 以上：{D["wdo"]["6"]:.1f}%</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+34}" class="cax" text-anchor="middle">'
             f'领先量 X（dB）</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+54}" class="bsub" fill="var(--text-3)">'
             f'这就是"掩码"这条路成立的全部依据——</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+70}" class="bsub" fill="var(--text-3)">'
             f'理想二值掩码能给 {D["ibm"]["sir"]:.1f} dB SIR，代价是 {D["ibm"]["sdr"]:.1f} dB 的失真</text>')

    # ── ② 空间可分度随频率 ──────────────────────────────────
    BX, BY, BW, BH = 380, 68, 292, 150
    lam = np.array(D['lam_f']); frq = np.array(D['freqs'])
    FHI = 5000.
    gx = lambda f: BX + (math.log10(max(f, 100)) - 2) / (math.log10(FHI) - 2) * BW
    lo, hi = -20., 45.
    gy = lambda v: BY + (hi - min(max(v, lo), hi)) / (hi - lo) * BH
    o.append(f'<text x="{BX}" y="{BY-30}" class="blab">② 但"空间上能分多开"随频率剧烈起伏</text>')
    o.append(f'<text x="{BX}" y="{BY-15}" class="bsub" fill="var(--text-3)">'
             f'纵轴：该频点上 SIR 的理论上限（广义特征值）</text>')
    for v in (-20, 0, 20, 40):
        y = gy(v)
        o.append(f'<line x1="{BX}" y1="{y:.1f}" x2="{BX+BW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{BX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">'
                 f'{"−" if v < 0 else ""}{abs(v)}</text>')
    sel = (frq >= 100) & (frq <= FHI)
    pts = ' '.join(f'{gx(f):.1f},{gy(v):.1f}' for f, v in zip(frq[sel], lam[sel]))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{S[0]}" stroke-width="0.9" '
             f'stroke-opacity="0.72"/>')
    med = float(np.median(lam[(frq >= 200) & (frq <= 4000)]))
    o.append(f'<line x1="{BX}" y1="{gy(med):.1f}" x2="{BX+BW}" y2="{gy(med):.1f}" '
             f'stroke="{S[1]}" stroke-width="1.6" stroke-dasharray="5 3"/>')
    o.append(f'<text x="{BX+BW-2}" y="{gy(38):.1f}" class="bsub" fill="{S[1]}" '
             f'text-anchor="end">200–4k 中位 {med:.1f} dB</text>')
    for f in (100, 300, 1000, 3000, 5000):
        o.append(f'<line x1="{gx(f):.1f}" y1="{BY+BH}" x2="{gx(f):.1f}" y2="{BY+BH+4}" class="grid"/>')
        o.append(f'<text x="{gx(f):.1f}" y="{BY+BH+17}" class="ctick" text-anchor="middle">'
                 f'{f if f < 1000 else str(f // 1000) + "k"}</text>')
    o.append(f'<text x="{BX}" y="{BY+BH+54}" class="bsub" fill="var(--text-3)">'
             f'3–4.5 kHz 那个坑是男声的谐波到头了，这一带只剩女声；</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+34}" class="cax" text-anchor="middle">'
             f'频率（Hz，对数轴）</text>')
    o.append(f'<text x="{BX}" y="{BY+BH+70}" class="bsub" fill="var(--text-3)">'
             f'低于 0 的频点空间滤波帮不上忙，只能靠掩码</text>')

    # ── ③ 各方法的真 SIR ─────────────────────────────────────
    CY = 344
    o.append(f'<text x="46" y="{CY-12}" class="blab">'
             f'③ 同一段录音，各条路线实测 SIR（把权重作用在纯 A / 纯 B 上算的）</text>')
    rows = [
        ('不处理', D['in_sir'], 'var(--text-3)', ''),
        ('盲空间聚类 → MVDR', D['blind']['sir'], S[1], '排列问题：只有 %.0f%% 的频点指对了人' % D['blind']['perm_ok']),
        ('只用 DOA（不聚类）→ MVDR', D['geo_mvdr'], S[1], '混响让导向向量对不上'),
        ('GSS（先验钉住）→ MVDR', D['gss']['0.0'], S[0], '先验把排列固定住，+%.1f dB' % (D['gss']['0.0'] - D['blind']['sir'])),
        ('神仙协方差 → rank-1 MVDR', D['oracle_r1'], S[0], '连掩码都不估了，还是只有这么多'),
        ('GSS → GEV+BAN', D['gss_gev']['0.0'], S[2], '放弃 rank-1 假设，一步跨过去'),
        ('理想二值掩码 → GEV+BAN', D['ibm_gev'], S[2], ''),
        ('神仙协方差 → GEV+BAN', D['oracle_gev'], S[2], '这间房子里 4 麦的物理上限'),
    ]
    LX, LW = 208, 300
    vlo, vhi = -4., 10.
    bx = lambda v: LX + (v - vlo) / (vhi - vlo) * LW
    for i, (lab, v, col, note) in enumerate(rows):
        y = CY + 10 + i * 25
        o.append(f'<text x="{LX-8}" y="{y+4}" class="bsub" text-anchor="end">{lab}</text>')
        x0, x1 = bx(min(v, 0.)), bx(max(v, 0.))
        o.append(f'<rect x="{x0:.1f}" y="{y-7:.1f}" width="{max(x1-x0,1.2):.1f}" height="14" '
                 f'rx="2" fill="{col}" fill-opacity="0.82"/>')
        o.append(f'<text x="{x1+6:.1f}" y="{y+4}" class="bsub" fill="{col}" '
                 f'font-weight="600">{v:+.2f}</text>')
        if note:
            o.append(f'<text x="{x1+52:.1f}" y="{y+4}" class="bsub" fill="var(--text-3)">{note}</text>')
    o.append(f'<line x1="{bx(0):.1f}" y1="{CY+2}" x2="{bx(0):.1f}" y2="{CY+10+len(rows)*25-14}" '
             f'stroke="var(--text-3)" stroke-width="1"/>')

    o.append(f'<line x1="14" y1="{H-76}" x2="686" y2="{H-76}" class="grid"/>')
    o.append(f'<text x="14" y="{H-54}" class="arlab">'
             f'最后三行是这一节的重点：<tspan font-weight="600">掩码估得准不准，几乎不是瓶颈</tspan>——'
             f'GSS 的掩码（{D["gss_gev"]["0.0"]:.2f}）离理想二值掩码（{D["ibm_gev"]:.2f}）'
             f'只差 {D["ibm_gev"]-D["gss_gev"]["0.0"]:.2f} dB，</text>')
    o.append(f'<text x="14" y="{H-34}" class="arlab">'
             f'而理想掩码离"连协方差都告诉你"的上限（{D["oracle_gev"]:.2f}）只差 '
             f'{D["oracle_gev"]-D["ibm_gev"]:.2f} dB。真正吃掉 '
             f'{D["oracle_gev"]-D["oracle_r1"]:.1f} dB 的是 rank-1 那个假设。</text>')
    o.append(f'<text x="14" y="{H-14}" class="arlab" fill="var(--s2)">'
             f'目标的空间协方差第一特征值只占 {D["rank1_frac"]:.0f}% 的能量——'
             f'混响房间里它离秩一差得远，而 MVDR 的导向向量只能表示秩一的那部分。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="'
            f'两说话人分离的三张图：一，九成时频格由单个说话人主导，掩码这条路成立；'
            f'二，每个频点的空间可分度上限起伏很大，语音带中位数只有几分贝；'
            f'三，八条路线的实测 SIR 阶梯，显示瓶颈在 rank-1 假设而不在掩码精度">'
            + ''.join(o) + '</svg>')


OUT['sepq'] = fig_sepq()
json.dump(OUT, open('figs17.json', 'w'), ensure_ascii=False)
print('figs17.json:', {k: len(v) for k, v in OUT.items()})
