#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§17：BAN 修好了什么，以及目标抵消的真正机理。"""
import json, math, html
import numpy as np, scipy.linalg as sla
rng = np.random.default_rng(31415)
c = 343.0
OUT = {}
S = ['var(--s1)', 'var(--s2)', 'var(--s3)']
O = ['var(--o1)', 'var(--o2)', 'var(--o3)', 'var(--o4)']

def steer(M, d, f, th): return np.exp(1j*2*np.pi*f/c*d*np.arange(M)*np.cos(th))

# ════════════════════════════════════════════════════════════════
# 图一：BAN 把逐频点的尺度钉回去
# ════════════════════════════════════════════════════════════════
def fig_ban():
    W, H = 700, 318
    ML, PW, TOP, PH = 52, 610, 60, 186
    lo, hi = 200., 6000.
    fx = lambda f: ML + (math.log10(f)-math.log10(lo))/(math.log10(hi)-math.log10(lo))*PW
    vlo, vhi = -22., 22.
    fy = lambda v: TOP + (vhi-v)/(vhi-vlo)*PH
    o = ['<text x="10" y="18" class="ct">GEV 的"失真"是什么：'
         '<tspan font-weight="700">每个频点的增益各随机一个数</tspan>'
         '<tspan class="cu"> · 6 麦、35 mm、目标 35°</tspan></text>',
         f'<text x="{ML}" y="{TOP-16}" class="blab">目标方向增益 20log₁₀|wᴴa|（dB）· 应当恒为 0</text>']
    for v in range(-20, 21, 10):
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v:+d}</text>')
    o.append(f'<line x1="{ML}" y1="{fy(0):.1f}" x2="{ML+PW}" y2="{fy(0):.1f}" class="zero"/>')
    M, d = 6, 0.035
    fbins = np.logspace(math.log10(lo), math.log10(hi), 46)
    raw, ban = [], []
    for f in fbins:
        A = rng.standard_normal((M,M))+1j*rng.standard_normal((M,M))
        Rn = A@A.conj().T + 2*np.eye(M); Rn = Rn/np.trace(Rn)*M
        a = steer(M, d, f, np.radians(35)); Rs = 2.7*np.outer(a, a.conj())
        ev, V = sla.eigh(Rs, Rn)
        wg = V[:, -1]*np.exp(1j*rng.uniform(0, 2*np.pi))*10**rng.uniform(-0.6, 0.6)
        raw.append(20*math.log10(abs(wg.conj()@a)))
        al = math.sqrt(np.real(wg.conj()@Rn@Rn@wg)/M)/np.real(wg.conj()@Rn@wg)
        ban.append(20*math.log10(abs(al*wg.conj()@a)))
    for f, v in zip(fbins, raw):
        o.append(f'<circle cx="{fx(f):.1f}" cy="{fy(min(max(v,vlo),vhi)):.1f}" r="3.2" '
                 f'fill="var(--s2)" fill-opacity="0.75"/>')
    pts = ' '.join(f'{fx(f):.1f},{fy(min(max(v,vlo),vhi)):.1f}' for f, v in zip(fbins, raw))
    o.append(f'<polyline points="{pts}" fill="none" stroke="var(--s2)" stroke-width="1" '
             f'stroke-opacity="0.45"/>')
    for f, v in zip(fbins, ban):
        o.append(f'<circle cx="{fx(f):.1f}" cy="{fy(v):.1f}" r="3.2" fill="var(--surface)" '
                 f'stroke="{S[2]}" stroke-width="1.7"/>')
    o.append(f'<text x="{fx(240):.1f}" y="{fy(-11):.1f}" class="bsub" fill="var(--s2)">'
             f'● 原始 GEV：尺度与相位都是任意的</text>')
    o.append(f'<text x="{fx(240):.1f}" y="{fy(-16.5):.1f}" class="bsub" fill="{S[2]}">'
             f'○ 做完 BAN：<tspan font-weight="600">每个频点精确回到 0 dB</tspan>'
             f'（与 MVDR 逐位相同）</text>')
    for f, lab in [(200,'200'),(500,'500'),(1000,'1k'),(2000,'2k'),(4000,'4k'),(6000,'6k')]:
        o.append(f'<line x1="{fx(f):.1f}" y1="{TOP+PH}" x2="{fx(f):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(f):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">频率 (Hz)</text>')
    o.append(f'<text x="14" y="{H-10}" class="arlab">'
             f'红点那条起伏，拼回时域就是<tspan font-weight="600">音色被随机重新加权</tspan>——'
             f'"GEV 有失真"指的就是它。BAN 只用 R_n 和 w 就把它钉死，全程不需要知道 a。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('原始 GEV 解在每个频点上的目标方向增益随机分布在正负十几分贝之间，'
                          '做完盲解析归一化 BAN 之后，所有频点精确回到 0 分贝')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['ban'] = fig_ban()

# ════════════════════════════════════════════════════════════════
# 图二：目标抵消的真正机理
# ════════════════════════════════════════════════════════════════
def fig_cancel():
    W, H = 700, 360
    ML, PW, TOP, PH = 46, 262, 56, 224
    ML2 = 414
    M, d, f = 6, 0.035, 1500
    a_true = steer(M, d, f, 0.0); ai = steer(M, d, f, np.radians(70))
    Rn_true = np.outer(ai, ai.conj()) + 0.01*np.eye(M)
    def sinr(a_asm, R, Rs):
        w = np.linalg.solve(R, a_asm); w = w/(a_asm.conj()@w)
        return 10*math.log10(np.real(w.conj()@Rs@w)/np.real(w.conj()@Rn_true@w))
    o = ['<text x="10" y="18" class="ct">目标抵消：'
         '<tspan font-weight="700">目标越响、越干净，反而掉得越狠</tspan>'
         '<tspan class="cu"> · 6 麦、35 mm、1.5 kHz，干扰在 70°</tspan></text>']

    # ── 左：损失 vs 输入 SNR ────────────────────────────────
    slo, shi = -15., 25.
    fx = lambda v: ML + (v-slo)/(shi-slo)*PW
    llo, lhi = -2., 46.
    fy = lambda v: TOP + (lhi-v)/(lhi-llo)*PH
    o.append(f'<text x="{ML}" y="{TOP-16}" class="blab">因"目标进了 R_n"损失的 SINR（dB）</text>')
    for v in range(0, 46, 10):
        y = fy(v)
        o.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    snrs = np.linspace(slo, shi, 60)
    for i, th in enumerate([0.0, 1.0, 3.0, 5.0]):
        a_asm = steer(M, d, f, np.radians(th))
        pts = []
        for sdb in snrs:
            phis = 10**(sdb/10); Rs = phis*np.outer(a_true, a_true.conj())
            loss = sinr(a_asm, Rn_true, Rs) - sinr(a_asm, Rn_true+Rs, Rs)
            pts.append(f'{fx(sdb):.1f},{fy(min(max(loss,llo),lhi)):.1f}')
        o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{O[i]}" stroke-width="2.3"/>')
        slab = [24., 21., 12., 5.][i]
        phis = 10**(slab/10); Rs = phis*np.outer(a_true, a_true.conj())
        lv = sinr(a_asm, Rn_true, Rs) - sinr(a_asm, Rn_true+Rs, Rs)
        o.append(f'<text x="{fx(slab)-6:.1f}" y="{fy(min(lv,lhi))-7:.1f}" class="bsub" '
                 f'text-anchor="end" fill="{O[i]}">导向偏 {th:.0f}°</text>')
    o.append(f'<text x="{fx(-11.5):.1f}" y="{fy(43):.1f}" class="bsub" fill="{O[0]}">'
             f'偏 0° 那条<tspan font-weight="600">恒等于零</tspan>：</text>')
    o.append(f'<text x="{fx(-11.5):.1f}" y="{fy(39):.1f}" class="bsub" fill="{O[0]}">'
             f'a 精确时目标进 R_n <tspan font-weight="600">完全无害</tspan></text>')
    for v in range(-15, 26, 10):
        o.append(f'<line x1="{fx(v):.1f}" y1="{TOP+PH}" x2="{fx(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{fx(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{v:+d}</text>')
    o.append(f'<text x="{ML+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">'
             f'输入信噪比（dB）</text>')

    # ── 右：对角加载救回多少 ────────────────────────────────
    elo, ehi = 1e-4, 1e2
    gx = lambda v: ML2 + (math.log10(v)-math.log10(elo))/(math.log10(ehi)-math.log10(elo))*PW
    ylo, yhi = 15., 40.
    gy = lambda v: TOP + (yhi-v)/(yhi-ylo)*PH
    o.append(f'<text x="{ML2}" y="{TOP-16}" class="blab">对角加载能救回来（导向偏 3°、SNR 10 dB）</text>')
    for v in range(15, 41, 5):
        y = gy(v)
        o.append(f'<line x1="{ML2}" y1="{y:.1f}" x2="{ML2+PW}" y2="{y:.1f}" class="grid"/>')
        o.append(f'<text x="{ML2-6}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">{v}</text>')
    a_asm = steer(M, d, f, np.radians(3.0)); Rs = 10*np.outer(a_true, a_true.conj())
    ref = sinr(a_asm, Rn_true, Rs)
    o.append(f'<line x1="{ML2}" y1="{gy(ref):.1f}" x2="{ML2+PW}" y2="{gy(ref):.1f}" '
             f'stroke="{S[2]}" stroke-width="1.7" stroke-dasharray="5 3"/>')
    o.append(f'<text x="{ML2+4}" y="{gy(ref)-6:.1f}" class="bsub" fill="{S[2]}">'
             f'理想上限：R_n 完全干净时 {ref:.1f} dB</text>')
    eps = np.logspace(math.log10(elo), math.log10(ehi), 90)
    pts, best, bx = [], -1e9, None
    for e in eps:
        v = sinr(a_asm, Rn_true+Rs+e*np.eye(M), Rs)
        if v > best: best, bx = v, e
        pts.append(f'{gx(e):.1f},{gy(min(max(v,ylo),yhi)):.1f}')
    o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{S[0]}" stroke-width="2.4"/>')
    o.append(f'<circle cx="{gx(bx):.1f}" cy="{gy(best):.1f}" r="4.5" fill="var(--surface)" '
             f'stroke="{S[1]}" stroke-width="2"/>')
    o.append(f'<text x="{gx(bx)+10:.1f}" y="{gy(best)+14:.1f}" class="bsub" fill="{S[1]}">'
             f'甜点 ε≈{bx:.2f} → {best:.1f} dB</text>')
    v0 = sinr(a_asm, Rn_true+Rs, Rs)
    o.append(f'<text x="{gx(1.3e-4):.1f}" y="{gy(v0)+15:.1f}" class="bsub" fill="{S[0]}">'
             f'不加载：{v0:.1f} dB</text>')
    for v, lab in [(1e-4,'10⁻⁴'),(1e-3,'10⁻³'),(1e-2,'10⁻²'),(1e-1,'10⁻¹'),(1,'1'),(10,'10'),(100,'100')]:
        o.append(f'<line x1="{gx(v):.1f}" y1="{TOP+PH}" x2="{gx(v):.1f}" y2="{TOP+PH+4}" class="grid"/>')
        o.append(f'<text x="{gx(v):.1f}" y="{TOP+PH+17}" class="ctick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ML2+PW/2:.0f}" y="{TOP+PH+34}" class="cax" text-anchor="middle">'
             f'对角加载 ε</text>')

    o.append(f'<text x="14" y="{H-10}" class="arlab">'
             f'所以"目标进了协方差就会被消掉"这句话<tspan font-weight="600">只说对了一半</tspan>：'
             f'真正的元凶是导向误差，目标功率只是放大器。而 3° 这个量级，正是 04 节那条相位预算。</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart diag" role="img" aria-label="'
            + html.escape('左图：导向矢量精确时，目标混进噪声协方差造成的信干噪比损失恒为零；'
                          '导向偏 1 度、3 度、5 度时，损失随输入信噪比迅速增大，'
                          '偏 5 度、输入 20 分贝时损失超过 40 分贝。'
                          '右图：加对角加载可以把偏 3 度、10 分贝这一档从 21 分贝救到 34 分贝，'
                          '但加载过重又会掉回去')
            + '">\n' + '\n'.join(o) + '\n</svg>')

OUT['cancel'] = fig_cancel()
json.dump(OUT, open('figs11.json', 'w'))
for k, v in OUT.items(): print('figs11.json: %-8s %.1f KB' % (k, len(v)/1024))
