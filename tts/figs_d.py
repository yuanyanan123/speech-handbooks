#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《TTS 合成手册》图 13–17：引导、跨语种、语音转换、长文本、客观指标。数都从 demo_*.json 取。
   配色遵守全书规矩：同一张图不同时用 --hot 与 --s3 作数据标记。"""
import json
import numpy as np
from figlib import svg, foot, ygrid, poly, neg, spread, C1, C2, C3, HOT, T3, T2

CFG = json.load(open('demo_cfg.json'))
LNG = json.load(open('demo_lang.json'))
VC = json.load(open('demo_vc.json'))
LNGT = json.load(open('demo_long.json'))
OBJ = json.load(open('demo_obj.json'))
OUT = {}


# ══════════════════════════════════════════════════════════════
def fig_cfg():
    W, H = 700, 490
    o = ['<text x="10" y="18" class="ct">引导：'
         '<tspan font-weight="700">补的是被学小的条件项，补过头先砍掉与对方重叠的那个峰</tspan>'
         '<tspan class="cu"> · 只看有效强度 λ(1+s)</tspan></text>']
    G = {r['lam']: r['cells'] for r in CFG['grid']}
    # ① 有效强度 → 遵循率 / 左峰占比 / W2（λ=1 一条线，λ=0.5、0.25 落在同一条线上）
    AX, AY, AW, AH = 58, 76, 250, 130
    o.append(f'<text x="16" y="{AY-28}" class="blab">① 有效强度 λ(1+s) ：遵循率（实）与较大子峰占比（虚）</text>')
    fx = lambda e: AX + (e - 0.25) / (6.0 - 0.25) * AW
    fy = lambda v: AY + (100 - v) / 100 * AH
    ygrid(o, AX, AW, [0, 50, 100], fy, '%g', '%')
    pts_adh, pts_lo = {}, {}
    for lam, col, mk in ((1.0, C1, 'o'), (0.5, C2, 's'), (0.25, T2, 'd')):
        for c in G[lam]:
            e = c['eff']
            pts_adh.setdefault(lam, []).append((fx(e), fy(c['adh'])))
            pts_lo.setdefault(lam, []).append((fx(e), fy(c['share_lo'])))
        for (x, y) in pts_adh[lam]:
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.3" fill="{col}" fill-opacity="0.9"/>')
        for (x, y) in pts_lo[lam]:
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.3" fill="none" stroke="{col}" stroke-width="1.5"/>')
    base = sorted(pts_adh[1.0])
    poly(o, base, C1, w=1.6)
    poly(o, sorted(pts_lo[1.0]), C1, w=1.4, dash='3 3')
    for e in (0.25, 1, 2, 4, 6):
        o.append(f'<text x="{fx(e):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{e:g}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">有效条件强度 λ(1+s)（1 = 恰好是真条件分布）</text>')
    o.append(f'<line x1="{fx(1):.1f}" y1="{AY}" x2="{fx(1):.1f}" y2="{AY+AH}" stroke="{T3}" stroke-dasharray="2 3"/>')
    o.append(f'<text x="{AX}" y="{AY+AH+48}" class="ctick" fill="{C1}">● λ=1（实心 = 遵循率，空心 = 较大子峰占比）　<tspan fill="{C2}">● λ=0.5　</tspan><tspan fill="{T2}">● λ=0.25</tspan></text>')
    # ② 概率密度（λ=1, s=0/1/2/5）
    EX, EW = 420, 236
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">② 生成的分布（λ=1）：随 s 变窄、被推离重叠区</text>')
    ed = CFG['hist']['edges']
    ctr = [(ed[i] + ed[i + 1]) / 2 for i in range(len(ed) - 1)]
    gx = lambda x: EX + (x + 3.2) / 6.8 * EW
    ymax = max(max(v) for v in CFG['hist']['dens'].values())
    gy = lambda v: AY + AH - v / ymax * AH
    for s_, col, dash in (('0.0', C1, None), ('1.0', C2, None), ('2.0', T2, None), ('5.0', T3, '4 3')):
        poly(o, [(gx(x), gy(v)) for x, v in zip(ctr, CFG['hist']['dens'][s_])], col, w=2.0, dash=dash)
    o.append(f'<line x1="{gx(0.2):.1f}" y1="{AY}" x2="{gx(0.2):.1f}" y2="{AY+AH}" stroke="{T3}" stroke-dasharray="2 3"/>')
    o.append(f'<text x="{gx(0.2)+4:.1f}" y="{AY+10}" class="ctick" fill="{T3}">与风格 B 重叠的峰</text>')
    for v in (-3, -1, 1, 3):
        o.append(f'<text x="{gx(v):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{neg("%d" % v)}</text>')
    o.append(f'<text x="{EX+EW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">声学量 x</text>')
    o.append(f'<text x="{EX}" y="{AY+AH+48}" class="ctick" fill="{C1}">s=0　<tspan fill="{C2}">s=1　</tspan><tspan fill="{T2}">s=2　</tspan><tspan fill="{T3}">s=5（虚）</tspan></text>')
    n = CFG['note']
    foot(o, H, [
        ('条件项完美（λ=1）：s=0 就是真条件分布（遵循 %.1f%%，较大子峰占比 %.1f%%，与真值差 W2 %.3f）。'
         % (n['perfect_adh'], n['perfect_lo'], n['perfect_w2']), None),
        ('s=2：遵循 <b>%.0f%%</b>，但标准差 %.2f → %.2f，较大子峰占比 %.1f%% → <b>%.1f%%</b>：与对方重叠的那个读法被删掉了。'
         % (n['s2_adh'], n['perfect_sd'], n['s2_sd'], n['perfect_lo'], n['s2_lo']), C2),
        ('条件项被学小了（λ=0.5）：遵循只有 %.1f%%，s=1 把它补回 %.1f%%；λ=0.25 要 s=3。三条线落在同一条曲线上。'
         % (n['weak_adh'], n['weak_fix_adh']), C1),
        ('补过头：s=5（有效强度 6）似然 %.2f（真分布内 %.2f），样本被推出两个峰之外。'
         % (n['s5_ll'], n['perfect_ll']), T2),
    ], y0=388, dy=17)
    return svg(W, H, o, '引导强度对遵循率、多样性与分布形状的影响，以及条件项被学小时引导补回了什么')


# ══════════════════════════════════════════════════════════════
def fig_lang():
    W, H = 700, 420
    o = ['<text x="10" y="18" class="ct">跨语种克隆：'
         '<tspan font-weight="700">嵌入里混着语言，完美的克隆会被评测判成"不像"</tspan>'
         '<tspan class="cu"> · 音素均衡后基本消除</tspan></text>']
    K = {r['key']: r for r in LNG['kinds']}
    # ① 余弦均值四类配对（raw vs balanced）
    BX, BW = 120, 170
    o.append(f'<text x="16" y="52" class="blab">① 四类配对的余弦均值（只保留 0.92–1.00）</text>')
    names = ['同人同语种', '同人跨语种', '异人同语种', '异人跨语种']
    for i, nm in enumerate(names):
        y = 78 + i * 38
        o.append(f'<text x="{BX-8}" y="{y+4}" class="ctick" text-anchor="end" fill="{T2}">{nm}</text>')
        for j, (kk, col) in enumerate((('raw', C1), ('balanced', C2))):
            v = K[kk]['mean'][nm]
            w = (v - 0.92) / 0.08 * BW
            yy = y - 8 + j * 12
            o.append(f'<rect x="{BX}" y="{yy}" width="{max(w,1):.1f}" height="9" rx="2" fill="{col}" fill-opacity="0.88"/>')
            o.append(f'<text x="{BX+w+5:.1f}" y="{yy+8}" class="ctick" fill="{col}">{v:.3f}</text>')
    o.append(f'<text x="{BX}" y="{78+4*38}" class="ctick" fill="{C1}">■ 原始（长时平均谱）　<tspan fill="{C2}">■ 音素均衡</tspan></text>')
    # ② EER
    EX, EW = 440, 200
    o.append(f'<text x="{EX-16}" y="52" class="blab">② 说话人确认 EER（%）</text>')
    cols = [('eer_same', '同语种'), ('eer_cross', '跨语种')]
    mx = max(K['raw']['eer_same'], K['raw']['eer_cross']) * 1.15
    for i, (kk, nm) in enumerate((('raw', '原始'), ('balanced', '音素均衡'))):
        y0 = 78 + i * 70
        o.append(f'<text x="{EX-8}" y="{y0+16}" class="ctick" text-anchor="end" fill="{T2}">{nm}</text>')
        for j, (ck, cn) in enumerate(cols):
            v = K[kk][ck]
            w = v / mx * EW
            yy = y0 + j * 22
            col = C1 if j == 0 else C2
            o.append(f'<rect x="{EX}" y="{yy}" width="{w:.1f}" height="14" rx="2" fill="{col}" fill-opacity="0.88"/>')
            o.append(f'<text x="{EX+w+5:.1f}" y="{yy+11}" class="ctick" fill="{col}">{cn} {v:.1f}</text>')
    n = LNG['note']
    foot(o, H, [
        ('同一个人换语言，余弦掉 %.3f，是"换人"所掉的 %.3f 的 <b>%.0f%%</b>；EER 同语种 %.1f%% → 跨语种 <b>%.1f%%</b>。'
         % (n['raw_lang_gap'], n['raw_spk_gap'], 100 * n['raw_ratio'], n['raw_eer_same'], n['raw_eer_cross']), None),
        ('一个完美的跨语种克隆（同一个人）得分 %.3f，比"说同一语言的另一个人"（%.3f）还低的说话人占 <b>%.0f%%</b>。'
         % (n['perfect_xl'], n['wrong_sl'], n['xl_below_wrong']), C2),
        ('按音素分别求均值再平均（需要音素对齐）：语言差距 %.4f，跨语种 EER %.1f%%，上面那个比例降到 %.0f%%。'
         % (n['bal_lang_gap'], n['bal_eer_cross'], n['bal_xl_below_wrong']), C1),
        ('"偷懒协议"（目标取同语种、冒充者取跨语种）的 EER 只有 %.1f%%——被语言差异白送的。' % n['raw_eer_lazy'], T2),
    ], y0=312, dy=17)
    return svg(W, H, o, '同语种与跨语种配对的余弦、说话人确认 EER，以及音素均衡的效果')


# ══════════════════════════════════════════════════════════════
def fig_vc():
    W, H = 700, 490
    o = ['<text x="10" y="18" class="ct">语音转换：'
         '<tspan font-weight="700">瓶颈只有一个旋钮，内容和说话人没有同时拆开的那一档</tspan>'
         '<tspan class="cu"> · 重建误差却一路变好</tspan></text>']
    rows = VC['rows']
    ks = [r['k'] for r in rows]
    AX, AY, AW, AH = 58, 76, 270, 130
    o.append(f'<text x="16" y="{AY-28}" class="blab">① 转换后：像目标（实）与内容保持（虚）</text>')
    fx = lambda k: AX + (np.log2(k) - np.log2(ks[0])) / (np.log2(ks[-1]) - np.log2(ks[0])) * AW
    fy = lambda v: AY + (100 - v) / 100 * AH
    ygrid(o, AX, AW, [0, 50, 100], fy, '%g', '%')
    poly(o, [(fx(r['k']), fy(100 * r['tgt_hit'])) for r in rows], C1)
    poly(o, [(fx(r['k']), fy(100 * r['ph_keep'])) for r in rows], C2)
    poly(o, [(fx(r['k']), fy(100 * r['src_keep'])) for r in rows], T3, dash='4 3')
    for r in rows:
        o.append(f'<circle cx="{fx(r["k"]):.1f}" cy="{fy(100*r["tgt_hit"]):.1f}" r="3" fill="{C1}"/>')
        o.append(f'<circle cx="{fx(r["k"]):.1f}" cy="{fy(100*r["ph_keep"]):.1f}" r="3" fill="{C2}"/>')
        o.append(f'<text x="{fx(r["k"]):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{r["k"]}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">瓶颈维数 k（对数轴）</text>')
    o.append(f'<text x="{AX}" y="{AY+AH+48}" class="ctick" fill="{C1}">蓝：输出被认作目标　<tspan fill="{C2}">橙：音素保持　</tspan><tspan fill="{T3}">灰虚：仍像源</tspan></text>')
    # ② 编码里的信息
    EX, EW = 420, 240
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">② 编码里剩下什么（探针，留出语音）</text>')
    gx = lambda k: EX + (np.log2(k) - np.log2(ks[0])) / (np.log2(ks[-1]) - np.log2(ks[0])) * EW
    ygrid(o, EX, EW, [0, 50, 100], fy, '%g', '%')
    poly(o, [(gx(r['k']), fy(100 * r['code_spk'])) for r in rows], T2)
    poly(o, [(gx(r['k']), fy(100 * r['code_ph'])) for r in rows], C2)
    for r in rows:
        o.append(f'<text x="{gx(r["k"]):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{r["k"]}</text>')
    o.append(f'<text x="{EX+EW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">瓶颈维数 k</text>')
    o.append(f'<text x="{EX}" y="{AY+AH+48}" class="ctick" fill="{T2}">深灰：说话人（随机 5%）　<tspan fill="{C2}">橙：音素</tspan></text>')
    n = VC['note']
    foot(o, H, [
        ('k=1–2：说话人几乎被抹掉（编码里 %.0f%%），输出 %.0f%% 被认作目标——但音素只剩 %.0f%%（探针上限 %.0f%%）。'
         % (n['k1_spk'], n['k2_hit'] if False else 100 * [r for r in rows if r['k'] == 2][0]['tgt_hit'], n['k2_ph'], n['probe_ph']), None),
        ('k≥6：内容保持 %.0f%%，但编码里说话人 %.0f%%，解码器不听嵌入——输出像目标只有 %.0f%%，k=32 时 %.0f%% 仍像源。'
         % (n['k8_ph'], n['k8_spk'], n['k8_hit'], n['k32_keep']), C2),
        ('折中点 k=%d：像目标 %.0f%%、内容 %.0f%%——两个都没到位。靠单纯收窄瓶颈，拆不开。' % (n['best_k'], n['best_hit'], n['best_ph']), C1),
        ('离标准答案的均方误差 k=1 最低（%.2f，低于直接拷贝源的 %.2f）——它靠把内容丢掉换来的，所以 MSE 不能当转换质量。'
         % (n['k1_mse'], n['copy_mse']), T2),
    ], y0=388, dy=17)
    return svg(W, H, o, '瓶颈维数对语音转换的目标说话人命中、内容保持和编码中说话人信息的影响')


# ══════════════════════════════════════════════════════════════
def fig_long():
    W, H = 700, 440
    o = ['<text x="10" y="18" class="ct">长文本：'
         '<tspan font-weight="700">注意力的平方项在 %d token 处追上线性层</tspan>' % LNGT['cross']['tokens'] +
         '<tspan class="cu"> · 分段：十分钟的算力降到 %.0f%%，KV %.0f GB → %.1f GB</tspan></text>' % (
             100 * LNGT['note']['c30p5_rel'], LNGT['note']['m10_kv'], LNGT['note']['c30p5_kv'])]
    S = [r for r in LNGT['single'] if r['nq'] == 4]
    AX, AY, AW, AH = 70, 76, 250, 130
    o.append(f'<text x="16" y="{AY-28}" class="blab">① 一次生成 D 秒（nq=4，%.0f token/s）：KV 显存</text>' % LNGT['const']['tok_s']['4'])
    secs = [r['sec'] for r in S]
    fx = lambda s: AX + (np.log10(s) - np.log10(secs[0])) / (np.log10(secs[-1]) - np.log10(secs[0])) * AW
    lo, hi = np.log10(0.3), np.log10(200)
    fy = lambda g: AY + (hi - np.log10(max(g, 0.3))) / (hi - lo) * AH
    for g in (1, 10, 100):
        y = fy(g)
        o.append(f'<line x1="{AX}" y1="{y:.1f}" x2="{AX+AW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{AX-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{g} GB</text>')
    poly(o, [(fx(r['sec']), fy(r['kv_gb'])) for r in S], C1)
    for r in S:
        o.append(f'<circle cx="{fx(r["sec"]):.1f}" cy="{fy(r["kv_gb"]):.1f}" r="3.5" fill="{C1}"/>')
        o.append(f'<text x="{fx(r["sec"]):.1f}" y="{AY+AH+16}" class="ctick" text-anchor="middle">{r["sec"] if r["sec"]<3600 else "1 h"}</text>')
    o.append(f'<text x="{AX+AW/2:.0f}" y="{AY+AH+32}" class="cax" text-anchor="middle">一次生成的音频时长（s，对数轴）</text>')
    # ② 注意力 / 线性
    EX, EW = 430, 230
    o.append(f'<text x="{EX-16}" y="{AY-28}" class="blab">② 注意力乘加 ÷ 线性层乘加</text>')
    ratios = [(sec, r['att_over_lin']) for sec in (10, 30, 120, 600) for r in LNGT['single'] if r['nq'] == 4 and r['sec'] == sec]
    mx = max(v for _, v in ratios) * 1.1
    for i, (sec, v) in enumerate(ratios):
        y = AY + 14 + i * 28
        o.append(f'<text x="{EX-8}" y="{y+4}" class="ctick" text-anchor="end" fill="{T2}">{sec} s</text>')
        w = v / mx * EW
        o.append(f'<rect x="{EX}" y="{y-8}" width="{w:.1f}" height="16" rx="2" fill="{C2 if v>1 else C1}" fill-opacity="0.88"/>')
        o.append(f'<text x="{EX+w+6:.1f}" y="{y+4}" class="ctick" fill="{C2 if v>1 else C1}">{v:.2f}×</text>')
    n = LNGT['note']
    foot(o, H, [
        ('每个 token：线性层 %.0f MMAC、KV %d KB（假设 24 层、d=1024、fp16）。' % (n['lin_mmac'], n['kv_per_tok_kb']), None),
        ('注意力追平线性层的位置是 n=12d=%d token，约 %.0f s（nq=4）/ %.0f s（nq=8）。' % (n['cross_tok'], n['cross_sec_nq4'], n['cross_sec_nq8']), T2),
        ('十分钟一次生成：%d token、KV %.1f GB、注意力是线性层的 <b>%.1f 倍</b>；一小时 %.0f GB。' % (n['m10_tok'], n['m10_kv'], n['m10_ratio'], n['h1_nq4_kv']), C2),
        ('分成 30 s 一段、各带前一段 5 s 做提示：每段上下文 %d token、KV %.2f GB，总乘加是一次生成的 <b>%.1f%%</b>（比不带提示多 %.0f%%）。'
         % (n['c30p5_ctx'], n['c30p5_kv'], 100 * n['c30p5_rel'], 100 * (n['c30p5_rel'] - n['c30p0_rel']) / n['c30p0_rel']), C1),
        ('代价没量：段边界的韵律是否连贯、停顿是否自然，本节不涉及。', T3),
    ], y0=326, dy=17)
    return svg(W, H, o, '长文本一次生成与分段生成的上下文长度、KV 显存与算力')


# ══════════════════════════════════════════════════════════════
def fig_obj():
    W, H = 700, 450
    o = ['<text x="10" y="18" class="ct">客观指标：'
         '<tspan font-weight="700">三个"和参考比"的指标，排序几乎互不相关</tspan>'
         '<tspan class="cu"> · 而且都在罚"合法的另一种读法"</tspan></text>']
    rows = OBJ['rows']
    cols = [('mcd', 'MCD（DTW）dB', 1), ('mcd_raw', 'MCD（不对齐）', 1), ('f0', 'F0 RMSE cents', 0), ('lsd', 'LSD（DTW）', 3)]
    X0, Y0, CW, RH = 190, 66, 118, 30
    for j, (k, nm, dg) in enumerate(cols):
        o.append(f'<text x="{X0+j*CW+CW/2}" y="{Y0-10}" class="ctick" text-anchor="middle" fill="{T2}">{nm}</text>')
    for i, r in enumerate(rows):
        y = Y0 + i * RH
        o.append(f'<text x="{X0-8}" y="{y+RH/2+4}" class="ctick" text-anchor="end" fill="{C2 if r["key"]=="legal" else T2}">{r["name"]}</text>')
        for j, (k, nm, dg) in enumerate(cols):
            rank = r['rank_' + k]
            a = 1 - (rank - 1) / 5
            col = C2 if r['key'] == 'legal' else C1
            o.append(f'<rect x="{X0+j*CW+2}" y="{y+2}" width="{CW-4}" height="{RH-4}" rx="3" fill="{col}" fill-opacity="{0.07+0.45*(1-a):.2f}"/>')
            o.append(f'<text x="{X0+j*CW+CW/2}" y="{y+RH/2+4}" class="ctick" text-anchor="middle" fill="var(--text)">{r[k]:.{dg}f}　#{rank}</text>')
    yb = Y0 + len(rows) * RH + 18
    o.append(f'<text x="{X0}" y="{yb}" class="ctick" fill="{T3}">格内：数值　#名次（1 = 最像参考）；橙色行是"合法的另一种读法"；颜色越深越差</text>')
    t = OBJ['tau']
    n = OBJ['note']
    foot(o, H, [
        ('Kendall τ：MCD 与 F0 %+.2f，MCD 与 LSD %+.2f，F0 与 LSD %+.2f——排序几乎互不相关；对齐前后的 MCD 也只有 %+.2f。'
         % (t['mcd-f0'], t['mcd-lsd'], t['f0-lsd'], t['mcd-mcd_raw']), None),
        ('合法的另一种读法：MCD（对齐）%.1f dB 排第 %d、不对齐 %.0f dB、F0 误差 %.0f cents 排第 %d——同一条合法输出，三个指标给出三种判决。'
         % (n['legal_mcd'], n['legal_rank_mcd'], n['legal_mcd_raw'], n['legal_f0'], n['legal_rank_f0']), C2),
        ('F0 对声码器金属音、加噪、低通都接近 0——它只看韵律；4 kHz 低通在 LSD 排最差、MCD 排第 %d。' % n['lp_rank_mcd'], C1),
        ('这里没有听测：只能说"指标之间不一致"，不能说谁对。', T3),
    ], y0=348, dy=17)
    return svg(W, H, o, '六种候选输出在三个参考式指标上的数值与名次')


OUT['cfg'] = fig_cfg()
OUT['lang'] = fig_lang()
OUT['vc'] = fig_vc()
OUT['long'] = fig_long()
OUT['obj'] = fig_obj()
json.dump(OUT, open('figs_d.json', 'w'), ensure_ascii=False)
print('figs_d.json:', {k: len(v) // 1024 for k, v in OUT.items()})
