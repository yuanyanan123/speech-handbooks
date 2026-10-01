#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《ASR 链路手册》图 1–5：链路总览、对齐格、格的稀疏性、HCLG 构图、规模扫描。"""
import json, math
import numpy as np

WF = json.load(open('demo_wfst.json'))
AL = json.load(open('demo_align.json'))
DE = json.load(open('demo_decode.json'))
ST = json.load(open('demo_stream.json'))

C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
T3, T2 = 'var(--text-3)', 'var(--text-2)'
OUT = {}


def defs(u):
    return (f'<defs><marker id="{u}a" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--text-2)"/></marker></defs>')


def svg(w, h, o, label, cls='chart'):
    return (f'<svg viewBox="0 0 {w} {h}" class="{cls}" role="img" aria-label="{label}">'
            + ''.join(o) + '</svg>')


def foot(o, H, lines, y0=None, dy=18):
    y0 = y0 or (H - 18 - (len(lines) - 1) * dy)
    o.append(f'<line x1="14" y1="{y0-20}" x2="686" y2="{y0-20}" class="grid"/>')
    for i, (t, c) in enumerate(lines):
        t = t.replace('<b>', '<tspan font-weight="600">').replace('</b>', '</tspan>')
        t = t.replace(' -0.', ' −0.').replace('率 -', '率 −')
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
def fig_chain():
    W, H = 700, 356
    o = [defs('ch'),
         '<text x="10" y="18" class="ct">一句话从波形到文字：'
         '<tspan font-weight="700">六段路，六种错法</tspan>'
         '<tspan class="cu"> · 每一段的错，在最终指标上长得不一样</tspan></text>']
    boxes = [('前端', '加窗、滤波\n回声消除', '前 19'),
             ('特征', '梅尔谱 / 自监督\n下采样 4×', '12'),
             ('编码器', 'Conformer\n看多少未来帧', '15 · 30'),
             ('对齐与损失', 'CTC / RNN-T\n对齐格', '17'),
             ('解码', 'beam + 语言模型\nHCLG 或前缀', '19–22'),
             ('后处理', '标点、数字\n热词、顺滑', '26–27')]
    x0, bw, gap = 16, 100, 12
    for i, (t, sub, sec) in enumerate(boxes):
        x = x0 + i * (bw + gap)
        o.append(f'<rect x="{x}" y="52" width="{bw}" height="60" rx="4" '
                 f'class="{"bx-a" if i in (2, 3, 4) else "bx"}"/>')
        o.append(f'<text x="{x+bw/2}" y="{72}" class="blab" text-anchor="middle">{t}</text>')
        for k, ln in enumerate(sub.split('\n')):
            o.append(f'<text x="{x+bw/2}" y="{88+k*13}" class="ctick" '
                     f'text-anchor="middle" fill="{T3}">{ln}</text>')
        o.append(f'<text x="{x+bw-2}" y="{46}" class="ctick" fill="{C1}" '
                 f'text-anchor="end">§{sec}</text>')
        if i < len(boxes) - 1:
            o.append(f'<line x1="{x+bw}" y1="82" x2="{x+bw+gap-3}" y2="82" '
                     f'class="ar" marker-end="url(#cha)"/>')
    rows = [('前端 / 特征', '整段都差，而且看不出是哪里差', '对所有句子一致地变坏'),
            ('编码器', '难词、口音、噪声段错得多', '错误集中在少数句子'),
            ('对齐与损失', '时间戳不准；训练不稳', 'WER 看不出来，做字幕才发现'),
            ('解码', '同音词选错、专名丢失', '错的词读音都对'),
            ('后处理', '断句、数字格式、热词误触', 'WER 可能反而变差')]
    o.append(f'<line x1="14" y1="130" x2="686" y2="130" class="grid"/>')
    o.append('<text x="16" y="150" class="blab">错在哪一段，症状不一样</text>')
    for j, (a, b, c) in enumerate(rows):
        y = 172 + j * 20
        o.append(f'<text x="16" y="{y}" class="bsub" fill="{T2}">{a}</text>')
        o.append(f'<text x="118" y="{y}" class="bsub">{b}</text>')
        em = ' font-weight="600"' if j == 3 else ''
        cc = C1 if j == 3 else T3
        o.append(f'<text x="380" y="{y}" class="bsub" fill="{cc}"{em}>{c}</text>')
    foot(o, H, [
        ('定位错误的第一步，不是看 WER 有多高，是看<b>错的词长什么样</b>。', None),
        ('读音都对、字选错 → 语言模型或解码；读音就不对 → 声学或前端；'
         '时间戳飘 → 对齐。', C2),
        ('这本书的顺序就是这条链路：Ⅱ 讲每一段的模型怎么来的，'
         'Ⅲ–Ⅳ 拆开最难的三段，Ⅴ 讲工程。', T3),
    ], y0=290)
    return svg(W, H, o, '语音识别从前端到后处理的六段链路，以及每一段出错时的不同症状',
               'chart diag')


# ══════════════════════════════════════════════════════════════
def fig_lattice():
    W, H = 700, 348
    o = ['<text x="10" y="18" class="ct">对齐格：'
         '<tspan font-weight="700">路径多不等于内存大</tspan>'
         '<tspan class="cu"> · 这两件事经常被混在一起</tspan></text>']
    # ① 路径数
    AX, AY, AW, AH = 64, 78, 262, 150
    cn = AL['count']
    xs = [math.log10(r['T']) for r in cn]
    lo, hi = 0.0, 240.0
    fx = lambda v: AX + (v - xs[0]) / (xs[-1] - xs[0]) * AW
    fy = lambda v: AY + (hi - v) / (hi - lo) * AH
    o.append(f'<text x="{AX-50}" y="{AY-30}" class="blab">① 对齐路径有多少条</text>')
    o.append(f'<text x="{AX-50}" y="{AY-14}" class="bsub" fill="{T3}">'
             f'纵轴是 10 的多少次方</text>')
    ygrid(o, AX, AW, [0, 60, 120, 180, 240], fy, '%g')
    for key, col, nm in (('ctc_log10', C1, 'CTC'), ('rnnt_log10', C2, 'RNN-T')):
        poly(o, [(fx(x), fy(r[key])) for x, r in zip(xs, cn)], col)
        r = cn[-1]
        o.append(f'<text x="{fx(xs[-1])-4:.1f}" y="{fy(r[key])-8:.1f}" class="ctick" '
                 f'fill="{col}" text-anchor="end">{nm}</text>')
    for x, r in zip(xs, cn):
        o.append(f'<text x="{fx(x):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["T"]}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'帧数 T（标签数 U = T/10，对数轴）</text>')
    g = AL['count_gap']
    o.append(f'<text x="{AX+8}" y="{AY+16}" class="ctick" fill="{C1}">'
             f'CTC 反而多 {g:.0f} 个数量级</text>')

    # ② 内存
    BX, BY, BW = 430, 78, 226
    mem = AL['mem']
    mx = max(r['rnnt_mb'] for r in mem)
    hx = lambda v: BX + (math.log10(max(v, 0.5)) - math.log10(0.5)) / \
        (math.log10(mx) - math.log10(0.5)) * BW
    o.append(f'<text x="{BX-16}" y="{AY-30}" class="blab">② 联合网络的张量有多大</text>')
    o.append(f'<text x="{BX-16}" y="{AY-14}" class="bsub" fill="{T3}">'
             f'前向一份，float32（对数轴）</text>')
    for i, r in enumerate(mem):
        y = BY + 26 + i * 30
        o.append(f'<text x="{BX-16}" y="{y-5}" class="ctick" fill="{T2}">'
                 f'{r["sec"]} s · V={r["V"]:,}</text>')
        o.append(f'<rect x="{BX}" y="{y}" width="{max(hx(r["ctc_mb"])-BX,1):.1f}" '
                 f'height="7" rx="1.5" fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<rect x="{BX}" y="{y+9}" width="{max(hx(r["rnnt_mb"])-BX,1):.1f}" '
                 f'height="7" rx="1.5" fill="{C2}" fill-opacity="0.9"/>')
        o.append(f'<text x="{hx(r["ctc_mb"])+6:.1f}" y="{y+6.5:.1f}" class="ctick" '
                 f'fill="{C1}">{r["ctc_mb"]:.0f}</text>')
        o.append(f'<text x="{hx(r["rnnt_mb"])+6:.1f}" y="{y+15.5:.1f}" class="ctick" '
                 f'fill="{C2}">{r["rnnt_mb"]:,.0f} MB</text>')
    for k, (col, nm) in enumerate(((C1, 'CTC'), (C2, 'RNN-T'))):
        lx = BX + 118 + k * 62
        o.append(f'<rect x="{lx}" y="{AY-22}" width="12" height="7" rx="1.5" '
                 f'fill="{col}" fill-opacity="0.9"/>')
        o.append(f'<text x="{lx+16}" y="{AY-15}" class="ctick" fill="{col}">{nm}</text>')
    b = mem[-1]
    foot(o, H, [
        ('左图：<b>CTC 的对齐路径反而比 RNN-T 多 %.0f 个数量级</b>——'
         'CTC 的扩展序列有 2U+1 个槽，T 帧往里分；RNN-T 只有 C(T+U, U) 条单调路径。'
         % g, None),
        ('右图：内存反过来。RNN-T 要在 <b>T×(U+1) 个格子</b>上各算一次 V 维分布，'
         'CTC 只在 T 个格子上算。', C2),
        ('%d 秒、词表 %s：一条就 <b>%.1f GB</b>，而且这只是前向的一份。'
         'batch=16 时 %.0f GB——这是 RNN-T 全部工程麻烦的来源。'
         % (b['sec'], '{:,}'.format(b['V']), b['rnnt_mb'] / 1000,
            AL['mem_note']['batch16_gb']), None),
        ('<b>路径数决定算法怎么写，格子数决定显存够不够</b>。两件事。', T3),
    ], y0=294)
    return svg(W, H, o, 'CTC 与 RNN-T 的对齐路径数量和联合网络张量大小的对比')


# ══════════════════════════════════════════════════════════════
def fig_occ():
    W, H = 700, 386
    oc = AL['occupancy']
    o = ['<text x="10" y="18" class="ct">对齐格是极度稀疏的：'
         f'<tspan font-weight="700">99% 的占据度挤在 {oc["q0.99"]*100:.0f}% 的格子里</tspan>'
         '<tspan class="cu"> · 这是 pruned RNN-T 的全部原理</tspan></text>']
    AX, AY, AW, AH = 64, 84, 250, 150
    qs = [(0.5, 'q0.5'), (0.9, 'q0.9'), (0.99, 'q0.99'), (0.999, 'q0.999')]
    mx = 0.10
    fy = lambda v: AY + (mx - v) / mx * AH
    o.append(f'<text x="{AX-50}" y="{AY-34}" class="blab">'
             f'① 按后验从大到小，占到 x% 要几个格子</text>')
    ygrid(o, AX, AW, [0, 2.5, 5, 7.5, 10], lambda p: fy(p / 100), '%g', '%')
    bw = AW / len(qs) - 22
    for i, (q, k) in enumerate(qs):
        x = AX + i * (AW / len(qs)) + 11
        v = oc[k]
        o.append(f'<rect x="{x:.1f}" y="{fy(v):.1f}" width="{bw:.1f}" '
                 f'height="{AY+AH-fy(v):.1f}" rx="2" fill="{C1}" fill-opacity="0.9"/>')
        o.append(f'<text x="{x+bw/2:.1f}" y="{fy(v)-6:.1f}" class="ctick" '
                 f'text-anchor="middle" fill="{C1}">{v*100:.1f}%</text>')
        o.append(f'<text x="{x+bw/2:.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{q*100:g}%</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'要覆盖的后验占据度</text>')
    # ② 固定带宽 vs 按后验
    BX, BY, BW, BH = 420, 84, 240, 150
    pr = [r for r in AL['prune'] if r['frac'] <= 0.62]
    FLOOR = 1e-4
    gx = lambda f: BX + f / 0.62 * BW
    gy = lambda e: BY + (2.0 - math.log10(max(e, FLOOR))) / 6.0 * BH
    o.append(f'<text x="{BX-16}" y="{AY-34}" class="blab">② 固定带宽剪枝的代价</text>')
    o.append(f'<text x="{BX-16}" y="{AY-18}" class="bsub" fill="{T3}">'
             f'纵轴 = log P 的绝对误差（对数轴）</text>')
    for v, s in ((100, '100 nat'), (1, '1'), (0.01, '0.01'), (1e-4, '&lt;10⁻⁴')):
        y = gy(v)
        o.append(f'<line x1="{BX}" y1="{y:.1f}" x2="{BX+BW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{BX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">'
                 f'{s}</text>')
    o.append(f'<line x1="{BX}" y1="{gy(0.05):.1f}" x2="{BX+BW}" y2="{gy(0.05):.1f}" '
             f'stroke="{T3}" stroke-width="1.2" stroke-dasharray="3 3"/>')
    o.append(f'<text x="{BX+BW-2}" y="{gy(0.05)-5:.1f}" class="ctick" fill="{T3}" '
             f'text-anchor="end">可接受线 0.05 nat</text>')
    poly(o, [(gx(r['frac']), gy(r['err'])) for r in pr], C2)
    for r in pr:
        o.append(f'<circle cx="{gx(r["frac"]):.1f}" cy="{gy(r["err"]):.1f}" r="2.6" '
                 f'fill="{C2}"/>')
        if r['band'] in (2, 3):
            o.append(f'<text x="{gx(r["frac"]):.1f}" y="{gy(r["err"])-8:.1f}" '
                     f'class="ctick" fill="{C2}" text-anchor="middle">'
                     f'带宽 {r["band"]}</text>')
    ok = AL['prune_ok']
    o.append(f'<line x1="{gx(oc["q0.99"]):.1f}" y1="{BY}" '
             f'x2="{gx(oc["q0.99"]):.1f}" y2="{BY+BH}" stroke="{C1}" '
             f'stroke-width="1.4" stroke-dasharray="4 3"/>')
    o.append(f'<line x1="{gx(ok["frac"]):.1f}" y1="{BY}" '
             f'x2="{gx(ok["frac"]):.1f}" y2="{BY+BH}" stroke="{C2}" '
             f'stroke-width="1.4" stroke-dasharray="4 3"/>')
    for f, col in ((oc['q0.99'], C1), (ok['frac'], C2)):
        o.append(f'<path d="M{gx(f)-4:.1f},{BY+BH+5} L{gx(f)+4:.1f},{BY+BH+5} '
                 f'L{gx(f):.1f},{BY+BH-1} z" fill="{col}"/>')
    for v in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
        o.append(f'<text x="{gx(v):.1f}" y="{BY+BH+20}" class="ctick" '
                 f'text-anchor="middle">{v*100:.0f}%</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+37}" class="cax" text-anchor="middle">'
             f'保留的格子比例：'
             f'<tspan fill="{C1}">按后验剪 {oc["q0.99"]*100:.0f}%</tspan>'
             f'<tspan fill="{T3}"> ┆ </tspan>'
             f'<tspan fill="{C2}">固定带宽 {ok["frac"]*100:.0f}%</tspan></text>')
    foot(o, H, [
        ('T=%d、U=%d 的格子共 %s 个。按后验从大到小排，'
         '<b>一半的占据度只要 %.1f%% 的格子</b>。'
         % (oc['T'], oc['U'], '{:,}'.format(oc['cells']), oc['q0.5'] * 100), None),
        ('右图：达到同样的精度（误差 &lt; 0.05 nat），按后验剪只要 %.0f%% 的格子，'
         '固定带宽要 %.0f%%。而且它是<b>悬崖</b>：带宽 3 还差 0.07 nat，带宽 2 就差 5.2 nat。'
         % (oc['q0.99'] * 100, ok['frac'] * 100), C2),
        ('固定带宽会把"先憋着不输、后面连输几个"这类合法路径整段切掉，'
         '而那些路径在训练早期份额并不小。<b>按后验剪才安全。</b>', None),
    ], y0=330)
    return svg(W, H, o, 'RNN-T 对齐格的后验占据度分布，以及按后验剪枝与固定带宽剪枝的对比')


# ══════════════════════════════════════════════════════════════
def fig_hclg():
    W, H = 700, 448
    o = ['<text x="10" y="18" class="ct">HCLG 构图：'
         '<tspan font-weight="700">爆炸在哪一级，又被哪一步收回来</tspan>'
         '<tspan class="cu"> · 真造了四级 FST 并真做了合成，数是数出来的</tspan></text>']
    AX, AY, AW, AH = 150, 80, 420, 172
    st = WF['stages']
    keep = ['G 二元文法', 'L 发音词典', 'L∘G', 'det(L∘G)', 'min·det(L∘G)',
            'C∘L∘G', 'det(C∘L∘G)', 'min·det(C∘L∘G)',
            'H∘C∘L∘G', 'det(HCLG)', 'min·det(HCLG)']
    rows = [r for r in st if r['tag'] in keep]
    mx = math.log10(max(r['arcs'] for r in rows) * 1.5)
    mn = math.log10(50)
    fx = lambda v: AX + (math.log10(max(v, 50)) - mn) / (mx - mn) * AW
    o.append(f'<text x="{AX-134}" y="{AY-30}" class="blab">① 每一级的边数（对数轴）</text>')
    for v in (100, 1000, 10000):
        o.append(f'<line x1="{fx(v):.1f}" y1="{AY}" x2="{fx(v):.1f}" y2="{AY+AH}" '
                 f'class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v:,}</text>')
    for i, r in enumerate(rows):
        y = AY + 12 + i * 15
        c = C3 if r['tag'].startswith('min') else (C2 if r['tag'].startswith('det') else C1)
        o.append(f'<text x="{AX-8}" y="{y+4}" class="bsub" text-anchor="end">'
                 f'{r["tag"]}</text>')
        o.append(f'<rect x="{AX}" y="{y-3:.1f}" width="{max(fx(r["arcs"])-AX,1.5):.1f}" '
                 f'height="8" rx="1.5" fill="{c}" fill-opacity="0.9"/>')
        o.append(f'<text x="{fx(r["arcs"])+6:.1f}" y="{y+4:.1f}" class="ctick" fill="{c}">'
                 f'{r["arcs"]:,}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'边数</text>')
    # ② 消歧符
    CY = 292
    nd, dd = WF['nodisambig'], WF['disambig']
    o.append(f'<text x="16" y="{CY}" class="blab">'
             f'② 不加消歧符，确定化根本不收敛</text>')
    items = [('带消歧符', '%d 态 / %d 边' % (dd['states'], dd['arcs']), C3),
             ('不加消歧符', '在 %s 态上被迫中止' % '{:,}'.format(nd.get('cap', 60000)), C2)]
    for i, (a, b, c) in enumerate(items):
        y = CY + 24 + i * 20
        o.append(f'<text x="30" y="{y}" class="bsub" fill="{T2}">{a}</text>')
        o.append(f'<text x="150" y="{y}" class="bsub" fill="{c}" font-weight="600">{b}</text>')
    o.append(f'<text x="360" y="{CY+24}" class="bsub" fill="{T3}">'
             f'词表 {WF["setup"]["nword"]} 个词，其中同音词 {WF["setup"]["nhomo"]} 个</text>')
    o.append(f'<text x="360" y="{CY+44}" class="bsub" fill="{T3}">'
             f'实际用到的三音子 {WF["ntri_used"]:,} 个 / 全集 {WF["ntri_all"]:,}</text>')
    opt = {r['tag']: r for r in WF['opt']}
    foot(o, H, [
        ('<b>确定化不一定让图变小</b>：L∘G 那一级从 %d 边变成 %d 边（%.0f%%），'
         '因为输入侧确定化要把输出串背在状态里。'
         % (opt['L∘G']['raw']['arcs'], opt['L∘G']['det']['arcs'],
            opt['L∘G']['det_pct']), None),
        ('真正收得回来的是最小化：C∘L∘G 收到 %.0f%%，HCLG 的确定化收到 %.0f%%。'
         % (opt['C∘L∘G']['min_pct'], opt['H∘C∘L∘G']['det_pct']), C3),
        ('而消歧符不是工程细节，是<b>可确定化的前提</b>——'
         '两个同音词让子集构造永远分不出该输出哪个词，残留串随词数指数增长。', C2),
    ], y0=394)
    return svg(W, H, o, 'HCLG 各级合成的边数、确定化与最小化的收缩效果，以及消歧符的作用')


# ══════════════════════════════════════════════════════════════
def fig_scale():
    W, H = 700, 392
    o = ['<text x="10" y="18" class="ct">词表变大时：'
         '<tspan font-weight="700">展开倍数不涨，不是数量级</tspan>'
         '<tspan class="cu"> · 又一个我按斜率外推、结果推错了的地方</tspan></text>']
    AX, AY, AW, AH = 64, 80, 268, 152
    sc = WF['scale']
    xs = [math.log2(r['nword']) for r in sc]
    lo, hi = math.log10(80), math.log10(12000)
    fx = lambda v: AX + (v - xs[0]) / (xs[-1] - xs[0]) * AW
    fy = lambda v: AY + (hi - math.log10(max(v, 80))) / (hi - lo) * AH
    o.append(f'<text x="{AX-50}" y="{AY-30}" class="blab">① 各级的边数</text>')
    ygrid(o, AX, AW, [100, 1000, 10000], fy, '%g')
    for key, col, nm, dy in (('g_arcs', T3, 'G', -4), ('lg_arcs', C1, 'min(L∘G)', 12),
                             ('clg_arcs', C2, 'min(C∘L∘G)', 4),
                             ('hclg_arcs', C3, 'min(HCLG)', 4)):
        poly(o, [(fx(x), fy(r[key])) for x, r in zip(xs, sc)], col, 2.0)
        o.append(f'<text x="{fx(xs[-1])+5:.1f}" y="{fy(sc[-1][key])+dy:.1f}" '
                 f'class="ctick" fill="{col}">{nm}</text>')
    for x, r in zip(xs, sc):
        o.append(f'<text x="{fx(x):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["nword"]}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'词表大小（对数轴）</text>')
    # ② 展开倍数
    BX, BY, BW, BH = 440, 80, 216, 152
    ex = WF['expand']
    eslope = float(np.polyfit([math.log10(r['nword']) for r in sc],
                              [math.log10(v) for v in ex], 1)[0])
    mxe = max(ex) * 1.2
    hy = lambda v: BY + (mxe - v) / mxe * BH
    hx = lambda i: BX + i / (len(ex) - 1) * BW
    o.append(f'<text x="{BX-16}" y="{AY-30}" class="blab">② H∘C 的展开倍数</text>')
    o.append(f'<text x="{BX-16}" y="{AY-14}" class="bsub" fill="{T3}">'
             f'min(HCLG) 边数 ÷ min(L∘G) 边数</text>')
    ygrid(o, BX, BW, [0, 3, 6, 9], hy, '%g', '×')
    poly(o, [(hx(i), hy(v)) for i, v in enumerate(ex)], C2)
    for i, v in enumerate(ex):
        o.append(f'<circle cx="{hx(i):.1f}" cy="{hy(v):.1f}" r="3" fill="{C2}"/>')
    m = WF['expand_mean']
    o.append(f'<line x1="{BX}" y1="{hy(m):.1f}" x2="{BX+BW}" y2="{hy(m):.1f}" '
             f'stroke="{C3}" stroke-width="1.4" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{BX+BW-4}" y="{hy(m)-6:.1f}" class="ctick" fill="{C3}" '
             f'text-anchor="end">均值 {m:.1f}×</text>')
    for i, r in enumerate(sc):
        o.append(f'<text x="{hx(i):.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{r["nword"]}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'词表大小</text>')
    pk = WF['peak']
    foot(o, H, [
        ('HCLG 的对数斜率是 %.2f，而 min(L∘G) 也差不多——'
         '<b>两者都被 |G| 支配</b>，所以比值不随词表变大。' % WF['scale_slope'], None),
        ('我原本按斜率外推，以为词表上到十万时"按需合成"能省几十倍。<b>那个外推是错的</b>：'
         '词表涨 6 倍，倍数在 %.1f–%.1f× 之间摆动，斜率 %.2f。'
         % (min(ex), max(ex), eslope), C2),
        ('按需合成真正值钱的是另外两件：<b>换 G 不用重建</b>，'
         '以及离线构图时的峰值内存（中间结果比最终的 HCLG 大 %.1f 倍）。'
         % pk['ratio'], None),
    ], y0=338)
    return svg(W, H, o, '词表规模对各级 FST 边数的影响，以及 H∘C 展开倍数不随词表变化')


OUT['chain'] = fig_chain()
OUT['lattice'] = fig_lattice()
OUT['occ'] = fig_occ()
OUT['hclg'] = fig_hclg()
OUT['scale'] = fig_scale()
json.dump(OUT, open('figs_a.json', 'w'), ensure_ascii=False)
print('figs_a.json:', {k: len(v) // 1024 for k, v in OUT.items()})
