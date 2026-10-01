#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《ASR 链路手册》图 6–9：beam 的悖论、语言模型融合、流式前瞻与状态、说话人日志。"""
import json, math

DE = json.load(open('demo_decode.json'))
ST = json.load(open('demo_stream.json'))

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


def ygrid(o, X, W, vals, f2y, fmt='%g', suf='', col=None):
    for v in vals:
        y = f2y(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+W}" y2="{y:.1f}" class="grid"/>')
        s = (fmt % v).replace('-', '−')
        cc = f' fill="{col}"' if col else ''
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end"{cc}>'
                 f'{s}{suf}</text>')


def poly(o, pts, col, w=2.2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    o.append('<polyline points="' + ' '.join('%.1f,%.1f' % p for p in pts)
             + f'" fill="none" stroke="{col}" stroke-width="{w}"{d}/>')


def dots(o, pts, col, r=3.0):
    for x, y in pts:
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}"/>')


def legend(o, x, y, items, gap=88):
    for i, (col, nm) in enumerate(items):
        lx = x + i * gap
        o.append(f'<rect x="{lx}" y="{y-7}" width="12" height="3" rx="1.5" fill="{col}"/>')
        o.append(f'<text x="{lx+16}" y="{y}" class="ctick" fill="{col}">{nm}</text>')


# ══════════════════════════════════════════════════════════════
def fig_beam():
    """beam 开大，模型分更高、错得更多。"""
    W, H = 700, 372
    bm = DE['beam']
    o = ['<text x="10" y="18" class="ct">beam 的悖论：'
         '<tspan font-weight="700">搜得越准，错得越多</tspan>'
         '<tspan class="cu"> · 同一个模型、同一批句子，只改 beam</tspan></text>']
    AX, AY, AW, AH = 66, 84, 254, 148
    xs = [math.log2(r['beam']) for r in bm]
    fx = lambda v: AX + (v - xs[0]) / (xs[-1] - xs[0]) * AW
    t0, t1 = 17.4, 19.6
    fy = lambda v: AY + (t1 - v) / (t1 - t0) * AH
    s0, s1 = -1.235, -1.080
    gy = lambda v: AY + (s1 - v) / (s1 - s0) * AH
    o.append(f'<text x="{AX-52}" y="{AY-34}" class="blab">① 搜索质量 vs 识别质量</text>')
    legend(o, AX - 52, AY - 16, [(C2, '错误率 TER（左轴）'),
                                 (C1, '每步模型得分（右轴）')], gap=140)
    ygrid(o, AX, AW, [17.5, 18.0, 18.5, 19.0, 19.5], fy, '%.1f', '%', C2)
    for v in (-1.22, -1.16, -1.10):
        y = gy(v)
        o.append(f'<text x="{AX+AW+5}" y="{y+3.5:.1f}" class="ctick" fill="{C1}">'
                 f'{("%.2f" % v).replace("-", "−")}</text>')
    poly(o, [(fx(x), fy(r['ter'])) for x, r in zip(xs, bm)], C2)
    dots(o, [(fx(x), fy(r['ter'])) for x, r in zip(xs, bm)], C2, 2.8)
    poly(o, [(fx(x), gy(r['score'])) for x, r in zip(xs, bm)], C1)
    dots(o, [(fx(x), gy(r['score'])) for x, r in zip(xs, bm)], C1, 2.8)
    rs = DE['ref_score']
    o.append(f'<line x1="{AX}" y1="{gy(rs):.1f}" x2="{AX+AW}" y2="{gy(rs):.1f}" '
             f'stroke="{C1}" stroke-width="1.3" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{AX+4}" y="{gy(rs)-6:.1f}" class="ctick" fill="{C1}">'
             f'参考答案本身的得分 {("%.3f" % rs).replace("-", "−")}</text>')
    for x, r in zip(xs, bm):
        o.append(f'<text x="{fx(x):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["beam"]}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'beam 宽度（每步展开 {bm[0]["expand"]:.0f} → {bm[-1]["expand"]:.0f} 次）</text>')

    # ② oracle
    BX, BY, BW, BH = 432, 84, 224, 148
    orc = DE['oracle']
    o.append(f'<text x="{BX-16}" y="{AY-34}" class="blab">② 答案在不在 n-best 里</text>')
    legend(o, BX - 16, AY - 16, [(C2, 'top-1'), (C3, 'oracle')], gap=72)
    m0, m1 = 0.0, 21.0
    hy = lambda v: BY + (m1 - v) / (m1 - m0) * BH
    ygrid(o, BX, BW, [0, 5, 10, 15, 20], hy, '%g', '%')
    gw = BW / len(orc)
    for i, r in enumerate(orc):
        cx = BX + i * gw + gw / 2
        for k, (key, col) in enumerate((('top1', C2), ('oracle', C3))):
            x = cx - 20 + k * 21
            o.append(f'<rect x="{x:.1f}" y="{hy(r[key]):.1f}" width="19" '
                     f'height="{BY+BH-hy(r[key]):.1f}" rx="2" fill="{col}" '
                     f'fill-opacity="0.9"/>')
            o.append(f'<text x="{x+9.5:.1f}" y="{hy(r[key])-5:.1f}" class="ctick" '
                     f'fill="{col}" text-anchor="middle">{r[key]:.1f}</text>')
        o.append(f'<text x="{cx:.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{r["beam"]}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'beam 宽度</text>')
    foot(o, H, [
        ('beam 从 1 开到 32，<b>模型得分一路变高（−1.107 → −1.088），'
         'TER 却从 17.8% 涨到 19.3%</b>。搜索没坏，是模型的排序坏了。', None),
        ('证据在虚线上：<b>参考答案自己的得分只有 −1.223</b>，'
         '比 beam=32 找到的错句子还低——模型本来就认为错的那句更像话。', C1),
        ('但 oracle 一直在往下走：beam=32 时答案有 %.1f%% 的概率落在 n-best 里，'
         'top-1 却是 %.1f%%，<b>中间差 %.1f 个点</b>。'
         % (orc[-1]['oracle'], orc[-1]['top1'], DE['oracle_gap']), C3),
        ('所以开大 beam 的正确用法不是直接取 top-1，而是<b>留着这 %.1f 个点给重打分</b>。'
         % DE['oracle_gap'], T3),
    ], y0=294)
    return svg(W, H, o, 'beam 宽度增大时模型得分升高但错误率上升，以及 oracle 与 top-1 的差距')


# ══════════════════════════════════════════════════════════════
def fig_fusion():
    """三种融合方式的扫描，以及域漂移时最优权重的移动。"""
    W, H = 700, 366
    o = ['<text x="10" y="18" class="ct">语言模型融合：'
         '<tspan font-weight="700">减掉内部语言模型，比加外部的更值钱</tspan>'
         '<tspan class="cu"> · 内部 LM 的强度 τ 是我自己设的，所以是已知量</tspan></text>']
    AX, AY, AW, AH = 66, 88, 252, 150
    e0, e1 = 6.0, 22.5
    fy = lambda v: AY + (e1 - v) / (e1 - e0) * AH
    fx = lambda v: AX + v / 1.25 * AW
    o.append(f'<text x="{AX-52}" y="{AY-38}" class="blab">① 三种做法的权重扫描</text>')
    legend(o, AX - 52, AY - 20, [(C1, '浅融合 λ'), (C2, '密度比 γ'), (C3, 'ILME γ')],
           gap=88)
    ygrid(o, AX, AW, [6, 10, 14, 18, 22], fy, '%g', '%')
    for key, col, nm in (('shallow', C1, 'lam'), ('dr', C2, 'gam'), ('ilme', C3, 'gam')):
        pts = [(fx(r[nm]), fy(min(r['ter'], e1))) for r in DE[key]]
        poly(o, pts, col, 2.0)
        dots(o, pts, col, 2.4)
        b = DE[key + '_best']
        bx, by = fx(b[nm]), fy(b['ter'])
        o.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="5" fill="none" '
                 f'stroke="{col}" stroke-width="1.8"/>')
        o.append(f'<text x="{bx:.1f}" y="{by+16:.1f}" class="ctick" fill="{col}" '
                 f'text-anchor="middle">{b["ter"]:.2f}%</text>')
    for v in (0, 0.25, 0.5, 0.75, 1.0, 1.25):
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'权重（λ 加外部 / γ 减内部）</text>')
    n = DE['fusion']['none']
    o.append(f'<line x1="{AX}" y1="{fy(n):.1f}" x2="{AX+AW}" y2="{fy(n):.1f}" '
             f'stroke="{T3}" stroke-width="1.2" stroke-dasharray="3 3"/>')
    o.append(f'<text x="{AX+AW-2}" y="{fy(n)-6:.1f}" class="ctick" fill="{T3}" '
             f'text-anchor="end">不融合 {n:.2f}%</text>')

    # ② 域漂移
    BX, BY, BW, BH = 434, 88, 180, 150
    dr = DE['drift']
    o.append(f'<text x="{BX-16}" y="{AY-38}" class="blab">② 外部 LM 越贴合，最优 λ 越大</text>')
    o.append(f'<text x="{BX-16}" y="{AY-22}" class="bsub" fill="{T3}">'
             f'横轴 λ，每条线是一个"LM 有多贴合目标域"</text>')
    d0, d1 = 12.0, 48.0
    gy = lambda v: BY + (d1 - min(v, d1)) / (d1 - d0) * BH
    gx = lambda v: BX + v / 0.7 * BW
    ygrid(o, BX, BW, [12, 24, 36, 48], gy, '%g', '%')
    cols = [T3, T3, C1, C2, C3]
    ops = [0.35, 0.55, 1, 1, 1]
    for j, r in enumerate(dr):
        pts = [(gx(c['lam']), gy(c['ter'])) for c in r['curve'] if c['ter'] <= d1 + 6]
        o.append('<polyline points="' + ' '.join('%.1f,%.1f' % p for p in pts)
                 + f'" fill="none" stroke="{cols[j]}" stroke-width="2" '
                 f'stroke-opacity="{ops[j]}"/>')
        b = gx(r['best_lam']), gy(r['ter'])
        o.append(f'<circle cx="{b[0]:.1f}" cy="{b[1]:.1f}" r="3.4" fill="{cols[j]}" '
                 f'fill-opacity="{ops[j]}"/>')
        if j in (0, 3, 4):
            lx, ly = pts[-1]
            end = lx > BX + BW - 40
            o.append(f'<text x="{lx + (-5 if end else 5):.1f}" y="{ly+4:.1f}" '
                     f'class="ctick" fill="{cols[j]}" fill-opacity="{ops[j]}"'
                     + (' text-anchor="end"' if end else '') +
                     f'>贴合 {r["mix"]*100:.0f}%</text>')
    for v in (0, 0.2, 0.4, 0.6):
        o.append(f'<text x="{gx(v):.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{v:g}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'浅融合权重 λ</text>')
    f = DE['fusion']
    foot(o, H, [
        ('同一个 beam=%d：不融合 %.2f%%，浅融合最好 %.2f%%，'
         '密度比 %.2f%%，ILME %.2f%%。<b>后两者比浅融合又少了近一半的错</b>。'
         % (f['beam'], f['none'], f['shallow'], f['dr'], f['ilme']), None),
        ('道理是：声学模型自己已经背下了训练文本的语言模型（这里 τ=%.2f）。'
         '直接加外部 LM，等于把语言先验<b>算了两遍</b>。'
         % f['tau'], C2),
        ('右图是同一件事的另一面：外部 LM 跟目标域完全不沾边时，最优 λ 是 <b>0</b>——'
         '融合不是默认该开的开关。LM 越贴合，最优 λ 才从 0 抬到 %.1f。'
         % dr[-1]['best_lam'], C1),
    ], y0=300)
    return svg(W, H, o, '浅融合、密度比与 ILME 的权重扫描，以及域漂移下最优融合权重的变化')


# ══════════════════════════════════════════════════════════════
def fig_stream():
    """前瞻帧数的非单调曲线，和状态缓存的线性代价。"""
    W, H = 700, 376
    lk = ST['look']
    o = ['<text x="10" y="18" class="ct">流式：'
         '<tspan font-weight="700">前瞻不是越多越好，有一个和音素时长挂钩的最优点</tspan>'
         '<tspan class="cu"> · 帧移 40 ms</tspan></text>']
    AX, AY, AW, AH = 66, 88, 256, 150
    xs = [math.log2(r['look']) for r in lk]
    fx = lambda v: AX + (v - xs[0]) / (xs[-1] - xs[0]) * AW
    fy = lambda v: AY + (60 - v) / 60 * AH
    o.append(f'<text x="{AX-52}" y="{AY-38}" class="blab">① 前瞻帧数 vs 错误率</text>')
    o.append(f'<text x="{AX-52}" y="{AY-22}" class="bsub" fill="{T3}">'
             f'两头都差，中间有个坑</text>')
    ygrid(o, AX, AW, [0, 20, 40, 60], fy, '%g', '%')
    pts = [(fx(x), fy(r['ter'])) for x, r in zip(xs, lk)]
    poly(o, pts, C2)
    dots(o, pts, C2, 2.8)
    fl = ST['look_full']
    o.append(f'<line x1="{AX}" y1="{fy(fl):.1f}" x2="{AX+AW}" y2="{fy(fl):.1f}" '
             f'stroke="{T3}" stroke-width="1.2" stroke-dasharray="3 3"/>')
    o.append(f'<text x="{AX+AW-2}" y="{fy(fl)-6:.1f}" class="ctick" fill="{T3}" '
             f'text-anchor="end">整句解码 {fl:.2f}%</text>')
    b = ST['look_best']
    bx, by = fx(math.log2(b['look'])), fy(b['ter'])
    o.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="5.5" fill="none" stroke="{C1}" '
             f'stroke-width="2"/>')
    o.append(f'<line x1="{bx:.1f}" y1="{AY+30}" x2="{bx:.1f}" y2="{by-8:.1f}" '
             f'stroke="{C1}" stroke-width="1" stroke-dasharray="2 3"/>')
    o.append(f'<text x="{bx:.1f}" y="{AY+22:.1f}" class="ctick" fill="{C1}" '
             f'text-anchor="middle">最优 {b["look"]} 帧 = {b["lat_ms"]:.0f} ms</text>')
    o.append(f'<text x="{bx:.1f}" y="{AY+9:.1f}" class="ctick" fill="{C1}" '
             f'text-anchor="middle">{b["ter"]:.2f}%</text>')
    for x, r in zip(xs, lk):
        o.append(f'<text x="{fx(x):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["look"]}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'前瞻帧数（对数轴）</text>')

    # ② 状态缓存
    BX, BY, BW, BH = 438, 88, 218, 150
    ca = ST['cache']
    o.append(f'<text x="{BX-16}" y="{AY-38}" class="blab">② chunk 变大，延迟和显存一起涨</text>')
    o.append(f'<text x="{BX-16}" y="{AY-22}" class="bsub" fill="{T3}">'
             f'单路编码器状态缓存，float32</text>')
    m1 = 10.0
    hy = lambda v: BY + (m1 - v) / m1 * BH
    ygrid(o, BX, BW, [0, 2.5, 5, 7.5, 10], hy, '%g', ' MB')
    gw = BW / len(ca)
    for i, r in enumerate(ca):
        x = BX + i * gw + gw / 2 - 13
        o.append(f'<rect x="{x:.1f}" y="{hy(r["total_mb"]):.1f}" width="26" '
                 f'height="{BY+BH-hy(r["total_mb"]):.1f}" rx="2" fill="{C1}" '
                 f'fill-opacity="0.9"/>')
        o.append(f'<text x="{x+13:.1f}" y="{hy(r["total_mb"])-5:.1f}" class="ctick" '
                 f'fill="{C1}" text-anchor="middle">{r["total_mb"]:.2f}</text>')
        o.append(f'<text x="{x+13:.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{r["chunk"]}</text>')
        o.append(f'<text x="{x+13:.1f}" y="{BY+BH+29}" class="ctick" fill="{T3}" '
                 f'text-anchor="middle">{r["lat_ms"]/1000:g}s</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+45}" class="cax" text-anchor="middle">'
             f'chunk 帧数 / 对应的分块延迟</text>')
    foot(o, H, [
        ('前瞻 1 帧 %.1f%%，6 帧 %.2f%%，20 帧又回到 %.1f%%。'
         '<b>最优 %d 帧 = %.0f ms，正好是一个音素的长度</b>。'
         % (lk[0]['ter'], b['ter'], lk[-1]['ter'], b['look'], b['lat_ms']), None),
        ('前瞻太短，证据还没攒够就得定；前瞻太长，<b>解码点一直往后拖，'
         '已经定下的假设被后面的观测推翻的机会反而变多</b>。两端各有一个失效机制。', C2),
        ('chunk=16 时单路缓存 %.2f MB，<b>100 路并发就是 %.0f MB</b>，'
         '而且是常驻的。延迟和显存在这里是同一个旋钮的两端。'
         % (ca[2]['total_mb'], ST['cache_100']), C1),
    ], y0=310)
    return svg(W, H, o, '流式解码的前瞻帧数与错误率的非单调关系，以及分块大小对状态缓存的影响')


# ══════════════════════════════════════════════════════════════
def fig_dia():
    """DER 的三项分解、聚类下限，以及多标签拿回多少。"""
    W, H = 700, 362
    dia, d2 = ST['dia'], ST['dia2']
    o = ['<text x="10" y="18" class="ct">说话人日志：'
         '<tspan font-weight="700">漏检那一项，一分错都不是模型犯的</tspan>'
         '<tspan class="cu"> · 是"一帧一个人"这个假设本身的下限</tspan></text>']
    AX, AY, AW, AH = 66, 92, 268, 148
    o.append(f'<text x="{AX-52}" y="{AY-42}" class="blab">① DER 拆成三项</text>')
    legend(o, AX - 52, AY - 24, [(C2, '混淆'), (C1, '漏检'),
                                 (T3, '重叠造成的漏检下限')], gap=68)
    m1 = 40.0
    fy = lambda v: AY + (m1 - v) / m1 * AH
    ygrid(o, AX, AW, [0, 10, 20, 30, 40], fy, '%g', '%')
    gw = AW / len(dia)
    for i, r in enumerate(dia):
        cx = AX + i * gw + gw / 2
        x = cx - 17
        y_m = fy(r['miss'])
        o.append(f'<rect x="{x:.1f}" y="{y_m:.1f}" width="34" '
                 f'height="{AY+AH-y_m:.1f}" rx="2" fill="{C1}" fill-opacity="0.9"/>')
        y_c = fy(r['miss'] + r['conf'])
        o.append(f'<rect x="{x:.1f}" y="{y_c:.1f}" width="34" '
                 f'height="{y_m-y_c:.1f}" rx="2" fill="{C2}" fill-opacity="0.9"/>')
        o.append(f'<text x="{cx:.1f}" y="{y_c-6:.1f}" class="ctick" '
                 f'text-anchor="middle" fill="{T2}">{r["der"]:.1f}</text>')
        if r['floor'] > 0:
            o.append(f'<line x1="{x-3:.1f}" y1="{fy(r["floor"]):.1f}" '
                     f'x2="{x+37:.1f}" y2="{fy(r["floor"]):.1f}" stroke="{T3}" '
                     f'stroke-width="1.6" stroke-dasharray="3 2"/>')
        o.append(f'<text x="{cx:.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{r["overlap"]*100:.0f}%</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'重叠说话的比例</text>')

    # ② 多标签
    BX, BY, BW, BH = 446, 92, 210, 148
    o.append(f'<text x="{BX-16}" y="{AY-42}" class="blab">② 换成多标签能拿回多少</text>')
    legend(o, BX - 16, AY - 24, [(C2, '聚类式'), (C3, '多标签')], gap=72)
    hy = lambda v: BY + (m1 - v) / m1 * BH
    ygrid(o, BX, BW, [0, 10, 20, 30, 40], hy, '%g', '%')
    gw2 = BW / len(d2)
    for i, r in enumerate(d2):
        cx = BX + i * gw2 + gw2 / 2
        for k, (key, col) in enumerate((('clu', C2), ('multi', C3))):
            x = cx - 20 + k * 21
            o.append(f'<rect x="{x:.1f}" y="{hy(r[key]):.1f}" width="19" '
                     f'height="{BY+BH-hy(r[key]):.1f}" rx="2" fill="{col}" '
                     f'fill-opacity="0.9"/>')
        o.append(f'<text x="{cx:.1f}" y="{hy(r["clu"])-6:.1f}" class="ctick" '
                 f'text-anchor="middle" fill="{C3}">−{r["gain"]:.1f}</text>')
        o.append(f'<text x="{cx:.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{r["overlap"]*100:.0f}%</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'重叠说话的比例</text>')
    r3 = [r for r in dia if r['overlap'] == 0.3][0]
    foot(o, H, [
        ('重叠 0%% 时 DER %.2f%%，全是混淆——谁是谁认错了。重叠到 30%%，DER 变成 %.2f%%，'
         '其中 <b>漏检 %.2f%%</b>。' % (dia[0]['der'], r3['der'], r3['miss']), None),
        ('虚线是<b>下限</b>：一帧只输出一个人，重叠段的第二人必然记成漏检。'
         '每一档的实测漏检都<b>正好等于这个下限</b>（30%% 时都是 %.2f%%）——'
         '漏检这一项里，模型一分错都没多犯。' % r3['floor'], T3),
        ('所以调聚类阈值收不回来。换成每帧多标签，30%% 重叠时 DER 从 %.2f%% 降到 %.2f%%，'
         '<b>一次拿回 %.1f 个点</b>——调聚类阈值一个点也收不回来，改输出形式就全回来了。'
         % (d2[-1]['clu'], d2[-1]['multi'], d2[-1]['gain']), C3),
    ], y0=296)
    return svg(W, H, o, 'DER 的漏检与混淆分解、重叠造成的理论下限，以及多标签输出的收益')


OUT['beam'] = fig_beam()
OUT['fusion'] = fig_fusion()
OUT['stream'] = fig_stream()
OUT['dia'] = fig_dia()
json.dump(OUT, open('figs_b.json', 'w'), ensure_ascii=False)
print('figs_b.json:', {k: len(v) // 1024 for k, v in OUT.items()})
