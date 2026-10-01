#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《TTS 合成手册》补图：温度、流式感受野、克隆的相似度协议。"""
import json, math
import numpy as np

TP = json.load(open('demo_temp.json'))
CK = json.load(open('demo_chunk.json'))
CL = json.load(open('demo_clone.json'))

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


def dots(o, pts, col, r=2.8):
    for x, y in pts:
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}"/>')


def legend(o, x, y, items, gap=96):
    for i, (col, nm) in enumerate(items):
        lx = x + i * gap
        o.append(f'<rect x="{lx}" y="{y-7}" width="12" height="3" rx="1.5" fill="{col}"/>')
        o.append(f'<text x="{lx+16}" y="{y}" class="ctick" fill="{col}">{nm}</text>')


# ══════════════════════════════════════════════════════════════
def fig_temp():
    """温度的两端各坏在哪，以及最优点在哪。"""
    W, H = 700, 392
    tm = TP['temp']
    o = ['<text x="10" y="18" class="ct">温度：'
         '<tspan font-weight="700">两端各有一种坏法，而且不是同一种</tspan>'
         '<tspan class="cu"> · 同一个模型，只改采样温度</tspan>']
    o.append('</text>')
    AX, AY, AW, AH = 62, 92, 262, 150
    xs = [r['temp'] for r in tm]
    fx = lambda v: AX + v / 1.5 * AW
    fy = lambda v: AY + (100 - v) / 100 * AH
    o.append(f'<text x="{AX-48}" y="{AY-42}" class="blab">① 两种失败模式</text>')
    legend(o, AX - 48, AY - 24, [(C2, '复读率'), (C1, '越界率（采到真实概率 &lt; 2% 的 token）')],
           gap=74)
    ygrid(o, AX, AW, [0, 25, 50, 75, 100], fy, '%g', '%')
    for key, col in (('rep', C2), ('off', C1)):
        pts = [(fx(r['temp']), fy(r[key])) for r in tm]
        poly(o, pts, col)
        dots(o, pts, col)
    for v in (0, 0.5, 1.0, 1.5):
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'采样温度</text>')
    o.append(f'<text x="{fx(0)+6:.1f}" y="{fy(100)+16:.1f}" class="ctick" fill="{C2}">'
             f'贪心：每一条都复读</text>')

    # ② 二元分布的对称 KL：真正的"像不像真的"
    BX, BY, BW, BH = 432, 92, 224, 150
    tb = TP['temp_best']
    tsb = TP['temp_small_best']
    o.append(f'<text x="{BX-16}" y="{AY-42}" class="blab">② 生成的分布像不像真的</text>')
    legend(o, BX - 16, AY - 24, [(C1, '数据充足'), (C3, '数据饥饿（过自信）')], gap=86)
    lo, hi = math.log10(0.1), math.log10(12.0)
    gy = lambda v: BY + (hi - math.log10(max(v, 0.1))) / (hi - lo) * BH
    gx = lambda v: BX + v / 1.5 * BW
    for v, s in ((10, '10'), (1, '1'), (0.1, '0.1')):
        y = gy(v)
        o.append(f'<line x1="{BX}" y1="{y:.1f}" x2="{BX+BW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{BX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{s}</text>')
    for key, col in (('temp', C1), ('temp_small', C3)):
        pts = [(gx(r['temp']), gy(r['skl'])) for r in TP[key]]
        poly(o, pts, col, 2.0)
        dots(o, pts, col, 2.4)
    for b, col in ((tb, C1), (tsb, C3)):
        o.append(f'<circle cx="{gx(b["temp"]):.1f}" cy="{gy(b["skl"]):.1f}" r="5.5" '
                 f'fill="none" stroke="{col}" stroke-width="1.8"/>')
    o.append(f'<text x="{gx(tb["temp"])-10:.1f}" y="{gy(tb["skl"])-14:.1f}" class="ctick" '
             f'fill="{C1}" text-anchor="end">充足：最优 {tb["temp"]:.1f}</text>')
    o.append(f'<text x="{gx(tsb["temp"])+8:.1f}" y="{gy(tsb["skl"])-12:.1f}" class="ctick" '
             f'fill="{C3}">饥饿：最优 {tsb["temp"]:.1f}</text>')
    for v in (0, 0.5, 1.0, 1.5):
        o.append(f'<text x="{gx(v):.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{v:g}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'采样温度（纵轴：二元分布的对称 KL，对数轴）</text>')
    cb = TP['calib']
    foot(o, H, [
        ('左图：<b>降温不是"更稳"</b>。贪心的复读率 100%%，每一条都撞到长度上限；'
         '温度 1.0 只有 %.1f%%。两端的坏法不是同一种——'
         '低温是复读，高温是读错。' % tm[5]['rep'], None),
        ('右图：<b>最优温度是校准问题</b>。数据充足的模型几乎完美校准'
         '（平均最高概率 %.3f，那个 token 的真实概率 %.3f），最优温度就是 %.1f。'
         % (cb['big']['conf'], cb['big']['true_p_of_argmax'], tb['temp']), C1),
        ('而<b>我原本以为过自信会把最优温度压到 1 以下——实测反而挪到了 %.1f</b>。'
         '数据饥饿的模型确实过自信（%.3f vs %.3f），'
         % (tsb['temp'], cb['small']['conf'], cb['small']['true_p_of_argmax']), C3),
        ('但它错的是<b>模态</b>，不是整体削尖了，所以一个全局温度压不回来。', T3),
    ], y0=300)
    return svg(W, H, o, '采样温度对复读率、越界率和生成分布保真度的影响')


# ══════════════════════════════════════════════════════════════
def fig_stream():
    """感受野、右上下文、块大小的三角关系。"""
    W, H = 700, 386
    o = ['<text x="10" y="18" class="ct">流式声码器：'
         '<tspan font-weight="700">要等的那一段是结构给的，不是实现不好</tspan>'
         '<tspan class="cu"> · 扰动一帧梅尔实测出来的</tspan></text>']
    AX, AY, AW, AH = 62, 88, 258, 150
    rt = CK['right']
    o.append(f'<text x="{AX-48}" y="{AY-38}" class="blab">① 右上下文给够了没有</text>')
    o.append(f'<text x="{AX-48}" y="{AY-22}" class="bsub" fill="{T3}">'
             f'纵轴：流式输出相对整句输出的误差</text>')
    lo, hi = -60.0, 0.0
    fy = lambda v: AY + (hi - max(v, lo)) / (hi - lo) * AH
    fx = lambda v: AX + v / 8.0 * AW
    ygrid(o, AX, AW, [0, -20, -40, -60], fy, '%g', ' dB')
    o.append(f'<line x1="{AX}" y1="{fy(-40):.1f}" x2="{AX+AW}" y2="{fy(-40):.1f}" '
             f'stroke="{T3}" stroke-width="1.2" stroke-dasharray="3 3"/>')
    o.append(f'<text x="{AX+AW-2}" y="{fy(-40)-6:.1f}" class="ctick" fill="{T3}" '
             f'text-anchor="end">−40 dB：听不出来了</text>')
    pts = [(fx(r['right']), fy(r['db'])) for r in rt]
    poly(o, pts, C2)
    dots(o, pts, C2)
    ok = CK['right_ok']
    o.append(f'<circle cx="{fx(ok["right"]):.1f}" cy="{fy(ok["db"]):.1f}" r="5.5" '
             f'fill="none" stroke="{C1}" stroke-width="2"/>')
    o.append(f'<text x="{fx(ok["right"]):.1f}" y="{fy(ok["db"])+20:.1f}" class="ctick" '
             f'fill="{C1}" text-anchor="middle">{ok["right"]} 帧 = {ok["lat_ms"]:.0f} ms</text>')
    rf = CK['rf']
    o.append(f'<line x1="{fx(rf["right_frames"]):.1f}" y1="{AY}" '
             f'x2="{fx(rf["right_frames"]):.1f}" y2="{AY+AH}" stroke="{C3}" '
             f'stroke-width="1.4" stroke-dasharray="4 3"/>')
    o.append(f'<text x="{fx(rf["right_frames"])+5:.1f}" y="{AY+14}" class="ctick" '
             f'fill="{C3}">实测右感受野 {rf["right_frames"]:.1f} 帧</text>')
    for v in (0, 2, 4, 6, 8):
        o.append(f'<text x="{fx(v):.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{v}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'给声码器的右上下文帧数</text>')

    # ② 块大小：首包 vs 摊销开销
    BX, BY, BW, BH = 430, 88, 226, 150
    ck = CK['chunk']
    o.append(f'<text x="{BX-16}" y="{AY-38}" class="blab">② 块大小：一个旋钮，两头拉扯</text>')
    legend(o, BX - 16, AY - 22, [(C1, '首包延迟'), (C2, '每块多算的比例')], gap=104)
    m1 = 820.0
    hy = lambda v: BY + (m1 - v) / m1 * BH
    m2 = 320.0
    hy2 = lambda v: BY + (m2 - v) / m2 * BH
    hx = lambda i: BX + i / (len(ck) - 1) * BW
    ygrid(o, BX, BW, [0, 200, 400, 600, 800], hy, '%g', '', C1)
    for v in (0, 100, 200, 300):
        o.append(f'<text x="{BX+BW+5}" y="{hy2(v)+3.5:.1f}" class="ctick" '
                 f'fill="{C2}">{v}%</text>')
    poly(o, [(hx(i), hy(r['lat_ms'])) for i, r in enumerate(ck)], C1, 2.0)
    dots(o, [(hx(i), hy(r['lat_ms'])) for i, r in enumerate(ck)], C1, 2.6)
    poly(o, [(hx(i), hy2(r['overhead'])) for i, r in enumerate(ck)], C2, 2.0)
    dots(o, [(hx(i), hy2(r['overhead'])) for i, r in enumerate(ck)], C2, 2.6)
    for i, r in enumerate(ck):
        o.append(f'<text x="{hx(i):.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{r["chunk"]}</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'块帧数（左轴 ms，右轴 %）</text>')
    x0 = CK['xfade'][0]
    xb = CK['xfade'][-1]
    foot(o, H, [
        ('右感受野实测 <b>%.1f 帧 = %.0f ms</b>：这一段流式时只能等。'
         '给到 %d 帧误差就掉到 %.0f dB，给到 6 帧输出和整句<b>逐比特相同</b>。'
         % (rf['right_frames'], rf['right_ms'], ok['right'], ok['db']), None),
        ('块从 16 帧切到 4 帧，首包 %.0f → %.0f ms，但每块多算的比例 %.0f%% → %.0f%%——'
         '<b>省下的延迟是拿算力买的</b>。'
         % (ck[2]['lat_ms'], ck[0]['lat_ms'], ck[2]['overhead'], ck[0]['overhead']), C2),
        ('右上下文给不起时，交叉淡入把边界的包络跳变从 %.2f× 压到 %.2f×'
         '（整句基准 %.2f×），而总误差只从 %.1f 变到 %.1f dB——'
         % (x0['seam'], xb['seam'], CK['seam_full'], x0['db'], xb['db']), T3),
        ('<b>淡入消的是"咔哒"，不是误差</b>。波形还是错的，只是不刺耳了。', None),
    ], y0=294)
    return svg(W, H, o, '声码器右感受野、右上下文与块大小对流式输出的影响')


# ══════════════════════════════════════════════════════════════
def fig_clone():
    """相似度协议与参考时长。"""
    W, H = 700, 380
    raw, cmn = CL['pairs']['raw'], CL['pairs']['cmn']
    o = ['<text x="10" y="18" class="ct">克隆的相似度：'
         '<tspan font-weight="700">换一个协议，EER 差 %.0f 倍</tspan>'
         '<tspan class="cu"> · 同一批嵌入，只改"拿什么去比"</tspan></text>'
         % (raw['eer_strict'] / max(raw['eer_naive'], 1e-9))]
    AX, AY, AW, AH = 76, 92, 248, 148
    keys = ['同人同室', '同人异室', '异人同室', '异人异室']
    cols = [C1, C1, C2, C2]
    ops = [0.95, 0.55, 0.95, 0.55]
    o.append(f'<text x="{AX-62}" y="{AY-38}" class="blab">① 四种配对的相似度</text>')
    o.append(f'<text x="{AX-62}" y="{AY-22}" class="bsub" fill="{T3}">'
             f'长时平均谱的余弦，误差棒是 ±1 个标准差</text>')
    lo, hi = 0.984, 1.0
    fy = lambda v: AY + (hi - v) / (hi - lo) * AH
    ygrid(o, AX, AW, [0.985, 0.99, 0.995, 1.0], fy, '%.3f')
    bw = AW / len(keys)
    for i, k in enumerate(keys):
        cx = AX + i * bw + bw / 2
        m, sd = raw[k]['mean'], raw[k]['sd']
        o.append(f'<rect x="{cx-16:.1f}" y="{fy(m):.1f}" width="32" '
                 f'height="{AY+AH-fy(m):.1f}" rx="2" fill="{cols[i]}" '
                 f'fill-opacity="{ops[i]}"/>')
        y_lo, y_hi = fy(max(m - sd, lo)), fy(min(m + sd, hi))
        o.append(f'<line x1="{cx:.1f}" y1="{y_lo:.1f}" x2="{cx:.1f}" '
                 f'y2="{y_hi:.1f}" stroke="{T2}" stroke-width="1.4"/>')
        for yy in (y_lo, y_hi):
            o.append(f'<line x1="{cx-5:.1f}" y1="{yy:.1f}" x2="{cx+5:.1f}" '
                     f'y2="{yy:.1f}" stroke="{T2}" stroke-width="1.2"/>')
        o.append(f'<text x="{cx:.1f}" y="{fy(min(m+sd, hi))-6:.1f}" class="ctick" '
                 f'text-anchor="middle" fill="{T2}">{m:.4f}</text>')
        o.append(f'<text x="{cx:.1f}" y="{AY+AH+16}" class="ctick" '
                 f'text-anchor="middle">{k}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+33}" class="cax" text-anchor="middle">'
             f'换房间掉 {raw["room_gap"]:.4f}，换人掉 {raw["spk_gap"]:.4f}</text>')

    # ② 参考时长
    BX, BY, BW, BH = 430, 92, 226, 148
    du = CL['dur']
    o.append(f'<text x="{BX-16}" y="{AY-38}" class="blab">② 参考音频要几秒</text>')
    o.append(f'<text x="{BX-16}" y="{AY-22}" class="bsub" fill="{T3}">'
             f'纵轴：严谨协议下的 EER</text>')
    m1 = 32.0
    hy = lambda v: BY + (m1 - v) / m1 * BH
    hx = lambda i: BX + i / (len(du) - 1) * BW
    ygrid(o, BX, BW, [0, 10, 20, 30], hy, '%g', '%')
    pts = [(hx(i), hy(r['eer'])) for i, r in enumerate(du)]
    poly(o, pts, C2)
    dots(o, pts, C2)
    for i, r in enumerate(du):
        o.append(f'<text x="{hx(i):.1f}" y="{BY+BH+16}" class="ctick" '
                 f'text-anchor="middle">{r["sec"]}</text>')
        if r['sec'] in (1, 5):
            dy2 = -10 if r['sec'] == 1 else -14
            o.append(f'<text x="{hx(i):.1f}" y="{hy(r["eer"])+dy2:.1f}" class="ctick" '
                     f'fill="{C2}" text-anchor="middle">{r["eer"]:.1f}%</text>')
    o.append(f'<text x="{BX+BW/2:.0f}" y="{BY+BH+33}" class="cax" text-anchor="middle">'
             f'参考音频时长（秒）</text>')
    foot(o, H, [
        ('<b>我原本以为房间会盖过说话人——实测没有</b>：换房间掉 %.4f，'
         '换人掉 %.4f，房间只有说话人的 %.2f 倍。'
         % (raw['room_gap'], raw['spk_gap'], raw['room_gap'] / raw['spk_gap']), None),
        ('但协议的乐观仍然是量级上的：拿那段参考本身比 EER %.2f%%，'
         '换一场录音再比 %.2f%%。EER 比的是<b>分布重叠</b>，不是绝对差距。'
         % (raw['eer_naive'], raw['eer_strict']), C2),
        ('倒谱均值归一化把 EER 从 %.2f%% 降到 %.2f%%，但机制不是消房间——'
         '<b>是把换人的差距放大了 %.1f 倍</b>（%.4f → %.4f）。'
         % (raw['eer_strict'], cmn['eer_strict'],
            cmn['spk_gap'] / raw['spk_gap'], raw['spk_gap'], cmn['spk_gap']), C1),
        ('参考时长是断崖不是斜坡：1 秒 %.1f%%，5 秒 %.1f%%，再长基本不涨。'
         % (du[0]['eer'], du[3]['eer']), T3),
    ], y0=288)
    return svg(W, H, o, '说话人相似度的四种配对、评测协议的差异与参考音频时长的影响')


OUT['temp'] = fig_temp()
OUT['stream'] = fig_stream()
OUT['clone2'] = fig_clone()
json.dump(OUT, open('figs_b.json', 'w'), ensure_ascii=False)
print('figs_b.json:', {k: len(v) // 1024 for k, v in OUT.items()})
