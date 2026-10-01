#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《单通道增强手册》图 6–9：相位、延迟预算、神经降噪、评测与下游。"""
import json, math
import numpy as np

GA = json.load(open('demo_gain.json'))
DD = json.load(open('demo_dd.json'))
PH = json.load(open('demo_phase.json'))
NN = json.load(open('demo_nn.json'))
EV = json.load(open('demo_eval.json'))

C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
T3, T2 = 'var(--text-3)', 'var(--text-2)'
OUT = {}


def svg(w, h, o, label, cls='chart'):
    return (f'<svg viewBox="0 0 {w} {h}" class="{cls}" role="img" aria-label="{label}">'
            + ''.join(o) + '</svg>')


def foot(o, H, lines, y0=None, dy=18):
    y0 = y0 or (H - 18 - (len(lines) - 1) * dy)
    o.append(f'<line x1="14" y1="{y0-20}" x2="686" y2="{y0-20}" class="grid"/>')
    for i, (t, c) in enumerate(lines):
        t = t.replace('<b>', '<tspan font-weight="600">').replace('</b>', '</tspan>')
        cc = f' fill="{c}"' if c else ''
        o.append(f'<text x="14" y="{y0+i*dy}" class="arlab"{cc}>{t}</text>')


def ygrid(o, X, W, vals, f2y, fmt='%g', suf=''):
    for v in vals:
        y = f2y(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+W}" y2="{y:.1f}" class="grid"/>')
        s = (fmt % v)
        if s.startswith('-'):
            s = '−' + s[1:]
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">'
                 f'{s}{suf}</text>')


def poly(o, pts, col, w=2.2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    o.append('<polyline points="' + ' '.join('%.1f,%.1f' % p for p in pts)
             + f'" fill="none" stroke="{col}" stroke-width="{w}"{d}/>')


# ══════════════════════════════════════════════════════════════
def fig_phase():
    W, H = 700, 402
    o = ['<text x="10" y="18" class="ct">被忽略的那一半：'
         '<tspan font-weight="700">相位在低信噪比时最值钱</tspan>'
         '<tspan class="cu"> · 而低信噪比正是你最需要降噪的时候</tspan></text>']
    AX, AY, AW, AH = 64, 80, 268, 150
    sw = PH['swap']
    xs = [r['snr'] for r in sw]
    lo, hi = -8.0, 22.0
    fx = lambda v: AX + (v - xs[0]) / (xs[-1] - xs[0]) * AW
    fy = lambda v: AY + (hi - v) / (hi - lo) * AH
    o.append(f'<text x="{AX-50}" y="{AY-30}" class="blab">① 幅度和相位，哪个更值钱</text>')
    o.append(f'<text x="{AX-50}" y="{AY-14}" class="bsub" fill="{T3}">'
             f'拿一个信号的幅度，配另一个信号的相位</text>')
    ygrid(o, AX, AW, [-5, 0, 5, 10, 15, 20], fy, '%g', ' dB')
    for key, col, nm in (('noisy', T3, '带噪（不处理）'),
                         ('cm_np', C1, '干净幅度 + 带噪相位'),
                         ('nm_cp', C2, '带噪幅度 + 干净相位')):
        poly(o, [(fx(r['snr']), fy(r[key])) for r in sw], col, 2.0)
    for i, (col, nm) in enumerate(((C1, '干净幅度 + 带噪相位'), (C2, '带噪幅度 + 干净相位'),
                                   (T3, '带噪（不处理）'))):
        o.append(f'<text x="{AX+8}" y="{AY+14+i*14}" class="ctick" fill="{col}">{nm}</text>')
    for r in sw:
        o.append(f'<text x="{fx(r["snr"]):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{("−" if r["snr"]<0 else "")}{abs(int(r["snr"]))}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'输入信噪比（dB）</text>')

    # ② 相位还值多少
    BX, BY, BW, BH = 440, 80, 226, 150
    mk = PH['mask']
    mx = max(max(r['irm_cp'], r['iam']) for r in mk) * 1.08
    hx = lambda v: BX + v / mx * BW
    o.append(f'<text x="{BX-16}" y="{AY-30}" class="blab">② 只改幅度的天花板</text>')
    o.append(f'<text x="{BX-16}" y="{AY-14}" class="bsub" fill="{T3}">'
             f'理想比值掩码 → 再把相位也换成干净的</text>')
    for i, r in enumerate(mk):
        y = BY + 40 + i * 42
        o.append(f'<text x="{BX-16}" y="{y-10}" class="ctick" fill="{T2}">'
                 f'输入 {r["snr"]:g} dB</text>')
        o.append(f'<rect x="{BX}" y="{y}" width="{hx(r["irm"])-BX:.1f}" height="9" rx="2" '
                 f'fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<rect x="{hx(r["irm"]):.1f}" y="{y}" '
                 f'width="{hx(r["irm_cp"])-hx(r["irm"]):.1f}" height="9" rx="2" '
                 f'fill="{C2}" fill-opacity="0.85"/>')
        o.append(f'<text x="{hx(r["irm_cp"])+6:.1f}" y="{y+8:.1f}" class="ctick" fill="{C2}">'
                 f'+{r["phase_worth"]:.2f} dB</text>')
        o.append(f'<text x="{BX+62}" y="{y-10}" class="ctick" fill="{C1}">'
                 f'{r["irm"]:.2f} dB</text>')
    o.append(f'<text x="{BX}" y="{BY+8}" class="ctick" fill="{C1}">理想比值掩码</text>')
    o.append(f'<text x="{BX+100}" y="{BY+8}" class="ctick" fill="{C2}">把相位也做对</text>')

    ov = PH['overlap']
    wn = PH['swap_win']
    foot(o, H, [
        ('左图：输入 −5 dB 时，"只把幅度修对"只拿到 %.2f dB；输入 15 dB 时拿到 %.2f dB。'
         '<b>相位的重要性随信噪比下降而上升。</b>'
         % (sw[0]['cm_np'], sw[-1]['cm_np']), None),
        ('右图：在理想幅度掩码之上，把相位也换成干净的，还能再拿 %.2f dB（0 dB 输入）。'
         '这是复数域方法的全部动机。' % mk[0]['phase_worth'], C2),
        ('我原以为"短窗系统可以不管相位"是因为重叠相加的冗余能纠错。实测<b>否掉了</b>：'
         '重叠 2×→16× 只多 %.2f dB，窗长跨 32 倍只差 %.2f dB。'
         % (PH['overlap_gain'], abs(wn[-1]['cm_np'] - wn[0]['cm_np'])), None),
        ('相位重不重要<b>几乎只由信噪比决定</b>，和变换参数关系很小。', T3),
    ], y0=348)
    return svg(W, H, o, '幅度与相位各自的贡献随信噪比变化，以及只改幅度的方法的上限')


# ══════════════════════════════════════════════════════════════
def fig_latency():
    W, H = 700, 412
    o = ['<text x="10" y="18" class="ct">延迟预算：'
         '<tspan font-weight="700">比任何算法选择都更硬的约束</tspan>'
         '<tspan class="cu"> · 重叠相加的算法延迟 = 一个窗长 + 一个帧移</tspan></text>']
    AX, AY, AW, AH = 64, 80, 280, 152
    real = {r['kind']: r['rows'] for r in PH['latency_real']}
    ideal = PH['latency']
    ws = [r['win_ms'] for r in ideal]
    fx = lambda v: AX + (math.log2(v) - math.log2(ws[0])) / \
        (math.log2(ws[-1]) - math.log2(ws[0])) * AW
    lo, hi = 2.0, 14.0
    fy = lambda v: AY + (hi - v) / (hi - lo) * AH
    o.append(f'<text x="{AX-50}" y="{AY-30}" class="blab">① 窗长买到了什么</text>')
    o.append(f'<text x="{AX-50}" y="{AY-14}" class="bsub" fill="{T3}">'
             f'输入 5 dB；实线是现实方法，虚线是理想掩码的上界</text>')
    ygrid(o, AX, AW, [4, 6, 8, 10, 12, 14], fy, '%g', ' dB')
    poly(o, [(fx(r['win_ms']), fy(r['irm_segsnr'])) for r in ideal], T3, 1.6, '4 3')
    poly(o, [(fx(r['win_ms']), fy(r['irm_segsnr'])) for r in PH['latency_babble']],
         T3, 1.6, '1 3')
    for kind, col, nm in (('pink', C1, '粉噪（平稳）'), ('babble', C2, 'babble（非平稳）')):
        rows = real[kind]
        poly(o, [(fx(r['win_ms']), fy(r['segsnr'])) for r in rows], col, 2.2)
        b = max(rows, key=lambda r: r['segsnr'])
        o.append(f'<circle cx="{fx(b["win_ms"]):.1f}" cy="{fy(b["segsnr"]):.1f}" r="4" '
                 f'fill="{col}"/>')
        o.append(f'<text x="{fx(b["win_ms"]):.1f}" y="{fy(b["segsnr"])-9:.1f}" '
                 f'class="ctick" fill="{col}" text-anchor="middle">{b["win_ms"]:g} ms</text>')
    for j, (col, nm, dash) in enumerate(((T3, '理想掩码（上界）', '4 3'),
                                         (C1, '现实方法 · 粉噪', None),
                                         (C2, '现实方法 · babble', None))):
        lx = AX + j * 100
        ly = AY + AH + 50
        d2 = f' stroke-dasharray="{dash}"' if dash else ''
        o.append(f'<line x1="{lx}" y1="{ly-4}" x2="{lx+16}" y2="{ly-4}" '
                 f'stroke="{col}" stroke-width="2.2"{d2}/>')
        o.append(f'<text x="{lx+20}" y="{ly}" class="ctick" fill="{col}">{nm}</text>')
    for r in ideal:
        o.append(f'<text x="{fx(r["win_ms"]):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["win_ms"]:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'窗长（ms，对数轴）</text>')

    # ② 三档预算
    BX, BY = 400, 80
    o.append(f'<text x="{BX-16}" y="{AY-30}" class="blab">② 三档场景各能用多长的窗</text>')
    tiers = PH['tiers']
    o.append(f'<text x="{BX-16}" y="{BY+4}" class="ctick" fill="{T2}">场景</text>')
    o.append(f'<text x="{BX+150}" y="{BY+4}" class="ctick" fill="{T2}" '
             f'text-anchor="end">延迟预算</text>')
    o.append(f'<text x="{BX+236}" y="{BY+4}" class="ctick" fill="{T2}" '
             f'text-anchor="end">可用窗长</text>')
    for i, t in enumerate(tiers):
        y = BY + 30 + i * 40
        o.append(f'<text x="{BX-16}" y="{y}" class="bsub">{t["tag"]}</text>')
        o.append(f'<text x="{BX+150}" y="{y}" class="bsub" text-anchor="end" fill="{T3}">'
                 f'{t["budget_ms"]:.0f} ms</text>')
        o.append(f'<text x="{BX+236}" y="{y}" class="bsub" text-anchor="end" '
                 f'font-weight="600">{t["best_win_ms"]:g} ms</text>')
        ok = t['resolves_f0']
        o.append(f'<text x="{BX-16}" y="{y+16}" class="ctick" '
                 f'fill="{C3 if ok else C2}">'
                 f'{"能" if ok else "不能"}分辨基频谐波（需要 ≥ %.0f ms）</text>'
                 % PH['resolve']['need_ms'])
    bp, bb = real['pink'], real['babble']
    foot(o, H, [
        ('理想掩码那两条虚线几乎是平的——<b>我原以为分辨率会很值钱，实测没有</b>。'
         '上界太宽松：它知道每个格子里的真实信噪比，格子粗一点也照样最优。', None),
        ('现实方法差别大得多。平稳噪声：窗越长越好，到 %g ms 饱和（跨度 %.2f dB）。'
         % (PH['best_win']['pink'], PH['best_win']['pink_span']), C1),
        ('非平稳噪声：<b>有最优点，在 %g ms</b>，再长反而变差——'
         '窗一长就把噪声自己的时间结构抹平了，估计器跟不上。'
         % PH['best_win']['babble'], C2),
        ('<b>所以窗长买的不是"分得开"，是"估得准"</b>；'
         '而对非平稳噪声，"估得准"和"跟得上"是矛盾的。', None),
    ], y0=358)
    return svg(W, H, o, '窗长对理想掩码上界与现实方法的不同影响，以及三档延迟预算下可用的窗长')


# ══════════════════════════════════════════════════════════════
def fig_nn():
    W, H = 700, 444
    d = NN['data']
    o = ['<text x="10" y="18" class="ct">神经降噪：'
         '<tspan font-weight="700">它买的是"见过"，不是"聪明"</tspan>'
         f'<tspan class="cu"> · 纯 numpy 手写反传，严格因果，{d["frames"]:,} 帧训练</tspan></text>']
    # ① 与经典同表
    AX, AY, AW = 250, 78, 180
    vs = NN['vs']
    mx = max(max(r['seen']['segsnr'], r['unseen']['segsnr']) for r in vs) * 1.12
    fx = lambda v: AX + v / mx * AW
    o.append(f'<text x="{AX-236}" y="{AY-30}" class="blab">'
             f'① 和 log-MMSE 放同一张表（输入 5 dB）</text>')
    o.append(f'<text x="{AX}" y="{AY-12}" class="ctick" fill="{C1}">训练见过的噪声</text>')
    o.append(f'<text x="{AX+AW+46}" y="{AY-12}" class="ctick" fill="{C2}">没见过的 babble</text>')
    for i, r in enumerate(vs):
        y = AY + 16 + i * 30
        tag = r['tag'].replace('（频点掩码（257 点））', '')
        o.append(f'<text x="{AX-10}" y="{y+4}" class="bsub" text-anchor="end">{tag}</text>')
        o.append(f'<rect x="{AX}" y="{y-7:.1f}" width="{fx(r["seen"]["segsnr"])-AX:.1f}" '
                 f'height="7" rx="2" fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<text x="{fx(r["seen"]["segsnr"])+5:.1f}" y="{y-1:.1f}" class="ctick" '
                 f'fill="{C1}">{r["seen"]["segsnr"]:.2f}</text>')
        o.append(f'<rect x="{AX}" y="{y+2:.1f}" width="{fx(r["unseen"]["segsnr"])-AX:.1f}" '
                 f'height="7" rx="2" fill="{C2}" fill-opacity="0.9"/>')
        o.append(f'<text x="{fx(r["unseen"]["segsnr"])+5:.1f}" y="{y+8:.1f}" class="ctick" '
                 f'fill="{C2}">{r["unseen"]["segsnr"]:.2f}</text>')
        o.append(f'<text x="{AX+AW+120}" y="{y-1:.1f}" class="ctick" fill="{T2}">'
                 f'LSD {r["seen"]["lsd"]:.2f}</text>')
        o.append(f'<text x="{AX+AW+120}" y="{y+9:.1f}" class="ctick" fill="{T2}">'
                 f'STOI* {r["seen"]["stoi"]:.3f}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+16+3*30+8:.0f}" class="cax" '
             f'text-anchor="middle">分段信噪比（dB）</text>')

    # ② 泛化 vs 训练噪声种类
    BY = 224
    dv = NN['diversity']
    o.append(f'<text x="16" y="{BY}" class="blab">② 训练噪声的多样性值多少</text>')
    CX, CW = 150, 200
    mx2 = max(r['unseen']['segsnr'] for r in dv) * 1.15
    gx = lambda v: CX + v / mx2 * CW
    for i, r in enumerate(dv):
        y = BY + 22 + i * 24
        o.append(f'<text x="{CX-8}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'{r["n"]} 种（{"/".join(r["kinds"])}）</text>')
        o.append(f'<rect x="{CX}" y="{y-5:.1f}" width="{gx(r["unseen"]["segsnr"])-CX:.1f}" '
                 f'height="10" rx="2" fill="{C2}" fill-opacity="0.9"/>')
        o.append(f'<text x="{gx(r["unseen"]["segsnr"])+6:.1f}" y="{y+4:.1f}" class="ctick" '
                 f'fill="{C2}">{r["unseen"]["segsnr"]:.2f} dB</text>')
    o.append(f'<text x="{CX}" y="{BY+22+3*24+6}" class="ctick" fill="{T3}">'
             f'在没见过的 babble 上的分段信噪比</text>')
    # ③ 算力
    c = NN['cost']
    o.append(f'<text x="420" y="{BY}" class="blab">③ 算力与延迟</text>')
    items = [('参数量', '%s' % f"{NN['form'][1]['params']:,}"),
             ('每帧乘加', '%s MAC' % f"{c['mac_per_frame']:,}"),
             ('算力', '%.2f MMAC/s' % c['mmac_s']),
             ('功耗 @50 pJ/MAC', '%.2f mW' % c['mw50']),
             ('一对 FFT 本身', '%.2f MMAC/s' % c['fft_mmac_s']),
             ('算法延迟', '%.0f ms' % c['lat_ms'])]
    for i, (a, b) in enumerate(items):
        y = BY + 22 + i * 17
        o.append(f'<text x="420" y="{y}" class="ctick" fill="{T3}">{a}</text>')
        o.append(f'<text x="672" y="{y}" class="ctick" text-anchor="end" fill="{T2}">{b}</text>')
    lm, nn_ = NN['vs'][1], NN['vs'][2]
    foot(o, H, [
        ('分段信噪比上神经网络只领先 %+.2f dB，看起来不值一提。'
         '但看右边两列：LSD %.2f → %.2f，STOI* %.3f → %.3f。'
         % (NN['gap_seen'], lm['seen']['lsd'], nn_['seen']['lsd'],
            lm['seen']['stoi'], nn_['seen']['stoi']), None),
        ('<b>信噪比类指标看不见这个差距</b>——而它恰好是听感和可懂度上最大的那部分。'
         '（08 节会看到，这种"指标看不见"的情况是常态。）', C2),
        ('没见过的噪声上领先 %+.2f dB，而训练噪声从 1 种加到 %d 种，'
         '在同一个没见过的噪声上从 %.2f 涨到 %.2f dB。'
         % (NN['gap_unseen'], dv[-1]['n'], dv[0]['unseen']['segsnr'],
            dv[-1]['unseen']['segsnr']), None),
        ('<b>这条决定了这类系统的工程重点全在数据上</b>：'
         '模型只有 %s 参数、%.2f mW，而它的好坏几乎全由训练噪声库决定。'
         % (f"{NN['form'][1]['params']:,}", c['mw50']), None),
    ], y0=390)
    return svg(W, H, o, '神经降噪与经典方法在见过和没见过的噪声上的对比，'
                        '训练噪声多样性的作用，以及模型的算力预算')


# ══════════════════════════════════════════════════════════════
def fig_eval():
    W, H = 700, 626
    o = ['<text x="10" y="18" class="ct">评测：'
         '<tspan font-weight="700">五个指标彼此大体一致，却都预测不了下游</tspan>'
         f'<tspan class="cu"> · {EV["n_systems"]} 个系统，输入 5 dB</tspan></text>']
    # ① 名次表
    AX, AY = 176, 78
    METR = ['SegSNR', 'SI-SDR', 'LSD', 'STOI*', '起伏dB']
    rows = EV['rank']
    colw = 62
    o.append(f'<text x="16" y="{AY-30}" class="blab">① 同一批系统，五个指标下的名次</text>')
    for j, mname in enumerate(METR):
        o.append(f'<text x="{AX+j*colw+20}" y="{AY}" class="ctick" fill="{T2}" '
                 f'text-anchor="middle">{mname}</text>')
    o.append(f'<text x="{AX+5*colw+56}" y="{AY}" class="ctick" fill="{C2}" '
             f'text-anchor="middle">名次跨度</text>')
    for i, r in enumerate(rows):
        y = AY + 22 + i * 19
        tag = r['tag'].replace('（谱减 α=0.5）', ' α=0.5').replace('（无判决引导）', '')
        tag = tag.replace('（谱减 α=6）', ' α=6').replace('谱减 α=2 + 谱底', '谱减 α=2+谱底')
        o.append(f'<text x="{AX-10}" y="{y}" class="bsub" text-anchor="end">{tag}</text>')
        rk = [EV['orders'][mn][i] for mn in METR]
        for j, v in enumerate(rk):
            c = C3 if v == 1 else (C2 if v >= len(rows) - 1 else T2)
            o.append(f'<text x="{AX+j*colw+20}" y="{y}" class="ctick" fill="{c}" '
                     f'text-anchor="middle">{v}</text>')
        sp = max(rk) - min(rk)
        cc = C2 if sp >= 6 else T3
        o.append(f'<text x="{AX+5*colw+56}" y="{y}" class="ctick" fill="{cc}" '
                 f'text-anchor="middle">{sp}</text>')
    # ② 下游
    BY = AY + 22 + len(rows) * 19 + 30
    asv = EV['asv']
    o.append(f'<text x="16" y="{BY}" class="blab">'
             f'② 把增强当成"信道"接到声纹上：处理之后的等错误率</text>')
    CX, CW = 176, 300
    mx = max(max(r['eer_matched'], r['eer_mismatch']) for r in asv) * 1.06
    gx = lambda v: CX + v / mx * CW
    o.append(f'<text x="{CX}" y="{BY+16}" class="ctick" fill="{C1}">'
             f'注册与测试用同一套前端</text>')
    o.append(f'<text x="{CX+186}" y="{BY+16}" class="ctick" fill="{C2}">'
             f'注册端是干净语音（失配）</text>')
    o.append(f'<line x1="{gx(EV["asv_clean"]):.1f}" y1="{BY+24}" '
             f'x2="{gx(EV["asv_clean"]):.1f}" y2="{BY+32+len(asv)*19}" '
             f'stroke="{C3}" stroke-width="1.3" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{gx(EV["asv_clean"])+5:.1f}" y="{BY+32+len(asv)*19+12}" '
             f'class="ctick" fill="{C3}">干净语音 {EV["asv_clean"]:.2f}%（下限）</text>')
    for i, r in enumerate(asv):
        y = BY + 36 + i * 19
        tag = r['tag'].replace('（谱减 α=0.5）', ' α=0.5').replace('（无判决引导）', '')
        tag = tag.replace('（谱减 α=6）', ' α=6').replace('谱减 α=2 + 谱底', '谱减 α=2+谱底')
        o.append(f'<text x="{CX-10}" y="{y}" class="bsub" text-anchor="end">{tag}</text>')
        o.append(f'<rect x="{CX}" y="{y-8:.1f}" '
                 f'width="{max(gx(r["eer_mismatch"])-CX,1):.1f}" height="6" rx="1.5" '
                 f'fill="{C2}" fill-opacity="0.85"/>')
        o.append(f'<rect x="{CX}" y="{y-1:.1f}" '
                 f'width="{max(gx(r["eer_matched"])-CX,1):.1f}" height="6" rx="1.5" '
                 f'fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<text x="{gx(max(r["eer_matched"],r["eer_mismatch"]))+6:.1f}" '
                 f'y="{y}" class="ctick" fill="{T2}">{r["eer_matched"]:.1f}% / '
                 f'{r["eer_mismatch"]:.1f}%</text>')
    corr = EV['corr']
    noi = asv[0]
    foot(o, H, [
        ('①：五个指标基本都说 log-MMSE（α=0.90）最好，'
         '但<b>同一个系统的名次能跨 %d 位</b>：「%s」残差起伏第一，STOI* 几乎垫底。'
         % (EV['max_spread']['n'], EV['max_spread']['tag'].replace('（谱减 α=6）', ' α=6')),
         None),
        ('②：<b>每一种增强都让声纹变差</b>。不处理 %.2f%%，最好的处理 %.2f%%，'
         '而注册端不做同样处理时全部崩到 40%% 以上。'
         % (noi['eer_matched'], min(r['eer_matched'] for r in asv[1:])), C2),
        ('五个指标与下游 EER 的相关系数：%s。'
         % '、'.join('%s %+.2f' % (k, v) for k, v in corr.items()), None),
        ('<b>波形保真类指标甚至是反相关的</b>：它们量"离干净波形有多远"，'
         '而下游要的是"谱的形状有没有被改坏"。给机器听的增强，必须直接用下游指标评。', None),
    ], y0=572)
    return svg(W, H, o, '五个客观指标给出的名次差异，以及各种增强处理对说话人确认等错误率的影响')


OUT['phase'] = fig_phase()
OUT['latency'] = fig_latency()
OUT['nn'] = fig_nn()
OUT['eval'] = fig_eval()
json.dump(OUT, open('figs_b.json', 'w'), ensure_ascii=False)
print('figs_b.json:', {k: len(v) // 1024 for k, v in OUT.items()})
