#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增益函数一族：谱减 → 维纳 → MMSE-STSA → log-MMSE。

   这一节只让<增益规则>变，其余全部固定：
   同一段语音、同一批噪声、同一个噪声功率谱（<用真值>，不估）、
   同一个先验信噪比估计（判决引导，α=0.98）。
   这样表里的差别就只能归因于增益公式本身。
"""
import numpy as np, json, math
from scipy.special import i0e, i1e, exp1
import enhlib as E

OUT = {}
NFFT, HOP = 512, 256
rng = np.random.default_rng(0)

x, segs = E.make_speech(dur=6.0, seed=1)
m = E.speech_mask(segs, len(x))
OUT['mus_floor'] = round(float(E.MUS_FLOOR_DB), 3)
OUT['sig'] = {'dur': round(len(x) / E.SR, 2), 'speech_pct': round(m.mean() * 100, 1),
              'nfft': NFFT, 'hop': HOP, 'hop_ms': round(HOP / E.SR * 1000, 1),
              'pr_db': round(E.check_pr(NFFT, HOP), 1)}
print('干净语音 %.1f s，语音段 %.1f%%；STFT %d/%d（%.1f ms），完美重构误差 %.0f dB'
      % (OUT['sig']['dur'], OUT['sig']['speech_pct'], NFFT, HOP,
         OUT['sig']['hop_ms'], OUT['sig']['pr_db']))


# ══ 增益函数 ══════════════════════════════════════════════════
def g_subtract(xi, gam, alpha=1.0, floor=0.0):
    """功率谱减：|Ŝ|² = |Y|² − α·λ_v，再压一个谱底。
       用 γ 写出来就是 G = sqrt(max(1 − α/γ, floor²))"""
    return np.sqrt(np.maximum(1.0 - alpha / np.maximum(gam, E.EPS), floor ** 2))


def g_wiener(xi, gam):
    return xi / (1.0 + xi)


def g_stsa(xi, gam):
    """Ephraim-Malah 1984：幅度的 MMSE 估计"""
    nu = np.clip(xi / (1.0 + xi) * gam, 1e-8, 500.0)
    h = nu / 2.0
    # exp(−ν/2)·I_k(ν/2) = i_ke(ν/2)，直接用指数缩放版避免溢出
    g = (np.sqrt(np.pi) / 2.0) * (np.sqrt(nu) / np.maximum(gam, E.EPS)) \
        * ((1.0 + nu) * i0e(h) + nu * i1e(h))
    return np.minimum(g, 1.0)


def g_logmmse(xi, gam):
    """Ephraim-Malah 1985：对数幅度的 MMSE 估计"""
    nu = np.clip(xi / (1.0 + xi) * gam, 1e-8, 500.0)
    return xi / (1.0 + xi) * np.exp(0.5 * exp1(nu))


def g_ibm(xi, gam, thr=1.0):
    """理想二值掩码：信噪比大于阈值就留，否则删"""
    return (xi > thr).astype(float)


def g_irm(xi, gam):
    """理想比值掩码（= 用真值算的维纳）"""
    return np.sqrt(xi / (1.0 + xi))


# ══ 先验信噪比：判决引导 ═══════════════════════════════════════
def dd_xi(Y, lam, alpha=0.98, xi_min_db=-25.0):
    """decision-directed：ξ̂(k,l) = α·|Ŝ(k,l−1)|²/λ_v + (1−α)·max(γ−1, 0)"""
    gam = np.abs(Y) ** 2 / np.maximum(lam, E.EPS)
    xi = np.zeros_like(gam)
    xi_min = 10 ** (xi_min_db / 10)
    prev = np.maximum(gam[0] - 1.0, 0.0)
    for l in range(len(gam)):
        ml = np.maximum(gam[l] - 1.0, 0.0)
        xi[l] = np.maximum(alpha * prev + (1 - alpha) * ml, xi_min)
        prev = g_wiener(xi[l], gam[l]) ** 2 * gam[l]      # |Ŝ|²/λ_v
    return xi, gam


def enhance(y, lam, gfun, alpha_dd=0.98, **kw):
    Y = E.stft(y, NFFT, HOP)
    xi, gam = dd_xi(Y, lam, alpha_dd)
    G = gfun(xi, gam, **kw)
    return E.istft(G * Y, NFFT, HOP, n=len(y)), G, Y


def oracle_lam(v):
    """噪声功率谱的<真值>：直接从纯噪声信号算，并在时间上平滑
       （平稳噪声的真值就是它的长时功率谱）"""
    V = E.stft(v, NFFT, HOP)
    return np.mean(np.abs(V) ** 2, axis=0)[None, :] * np.ones((1, 1))


# ══ ① 主表：同一条件下五种增益 ═════════════════════════════════
METHODS = [
    ('谱减（α=1，无谱底）', lambda: (g_subtract, dict(alpha=1.0, floor=0.0))),
    ('谱减（过减 α=2，谱底 −20 dB）', lambda: (g_subtract, dict(alpha=2.0, floor=0.1))),
    ('维纳', lambda: (g_wiener, {})),
    ('MMSE-STSA', lambda: (g_stsa, {})),
    ('log-MMSE', lambda: (g_logmmse, {})),
]
ORACLE = [('理想比值掩码 IRM（上界）', g_irm, {}),
          ('理想二值掩码 IBM（0 dB）', g_ibm, dict(thr=1.0))]

SNRS = (0.0, 5.0, 10.0)
NOISE = 'pink'
v_full = E.make_noise(NOISE, len(x), seed=3)

print('\n① 同一段语音、同一噪声（%s）、同一个噪声功率谱真值、同一个判决引导 α=0.98' % NOISE)
print('   只有增益公式不同。指标：分段信噪比 / 对数谱距离 / 可懂度代理 / 音乐噪声')
OUT['main'] = {}
for snr in SNRS:
    y, vv = E.mix_at_snr(x, v_full, snr, m)
    lam = np.mean(np.abs(E.stft(vv, NFFT, HOP)) ** 2, axis=0)[None, :]
    S = E.stft(x[:len(y)], NFFT, HOP)
    V = E.stft(vv[:len(y)], NFFT, HOP)
    fm = E.frame_mask(m, len(S), NFFT, HOP)
    rows = []
    base = {'tag': '带噪（不处理）', 'segsnr': E.seg_snr(x, y, m), 'lsd': E.lsd(x, y, mask=m),
            'stoi': E.stoi_like(x, y, mask=m), 'sisdr': E.si_sdr(x, y),
            'mus': E.musical(V, fm), 'kurt': E.kurt_ratio(V, V, fm),
            'sd_db': -99.0, 'nr_db': 10 * np.log10(np.sum(np.abs(V) ** 2)
                                                   / np.sum(np.abs(S) ** 2))}
    rows.append(base)
    for tag, mk in METHODS:
        gf, kw = mk()
        z, G, Y = enhance(y, lam, gf, **kw)
        d = E.decompose(S, V, G)
        rows.append({'tag': tag, 'segsnr': E.seg_snr(x, z, m), 'lsd': E.lsd(x, z, mask=m),
                     'stoi': E.stoi_like(x, z, mask=m), 'sisdr': E.si_sdr(x, z),
                     'mus': E.musical(G * V, fm), 'kurt': E.kurt_ratio(G * V, V, fm),
                     'sd_db': d['sd_db'], 'nr_db': d['nr_db']})
    for tag, gf, kw in ORACLE:
        Y = E.stft(y, NFFT, HOP)
        gam = np.abs(Y) ** 2 / np.maximum(lam, E.EPS)
        xi_true = np.abs(S) ** 2 / np.maximum(lam, E.EPS)
        G = gf(xi_true, gam, **kw)
        z = E.istft(G * Y, NFFT, HOP, n=len(y))
        d = E.decompose(S, V, G)
        rows.append({'tag': tag, 'segsnr': E.seg_snr(x, z, m), 'lsd': E.lsd(x, z, mask=m),
                     'stoi': E.stoi_like(x, z, mask=m), 'sisdr': E.si_sdr(x, z),
                     'mus': E.musical(G * V, fm), 'kurt': E.kurt_ratio(G * V, V, fm),
                     'sd_db': d['sd_db'], 'nr_db': d['nr_db']})
    for r in rows:
        for k in r:
            if k != 'tag':
                r[k] = round(float(r[k]), 3)
    OUT['main'][str(int(snr))] = rows
    print('\n  输入 %g dB' % snr)
    print('  %-28s %8s %7s %7s %9s %9s %9s %7s'
          % ('方法', 'SegSNR', 'LSD', 'STOI*', '语音失真', '残留噪声', '起伏dB', '峰度比'))
    for r in rows:
        print('  %-28s %7.2f %7.2f %7.3f %8.1f %8.1f %8.2f %7.2f'
              % (r['tag'], r['segsnr'], r['lsd'], r['stoi'],
                 r['sd_db'], r['nr_db'], r['mus'], r['kurt']))

# ══ ② 过减因子扫描：失真与残留的取舍 ═══════════════════════════
print('\n② 过减因子 α 在换什么：每多减一点噪声，就多一点语音失真')
y, vv = E.mix_at_snr(x, v_full, 5.0, m)
lam = np.mean(np.abs(E.stft(vv, NFFT, HOP)) ** 2, axis=0)[None, :]
S = E.stft(x[:len(y)], NFFT, HOP); V = E.stft(vv[:len(y)], NFFT, HOP)
fm = E.frame_mask(m, len(S), NFFT, HOP)
OUT['oversub'] = []
print('  %5s %9s %9s %9s %8s %7s %7s %6s' % ('α', '语音失真', '残留噪声', '总误差',
                                             'SegSNR', 'LSD', '起伏dB', '峰度比'))
for a in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0):
    z, G, Y = enhance(y, lam, g_subtract, alpha=a, floor=0.0)
    d = E.decompose(S, V, G)
    r = {'alpha': a, 'sd_db': round(d['sd_db'], 2), 'nr_db': round(d['nr_db'], 2),
         'tot_db': round(d['tot_db'], 2), 'segsnr': round(E.seg_snr(x, z, m), 2),
         'lsd': round(E.lsd(x, z, mask=m), 2), 'mus': round(E.musical(G * V, fm), 2),
         'kurt': round(E.kurt_ratio(G * V, V, fm), 2)}
    OUT['oversub'].append(r)
    print('  %5.1f %8.1f %8.1f %8.1f %8.2f %7.2f %7.2f %6.2f'
          % (a, r['sd_db'], r['nr_db'], r['tot_db'], r['segsnr'], r['lsd'],
             r['mus'], r['kurt']))
best = min(OUT['oversub'], key=lambda r: r['tot_db'])
OUT['oversub_best'] = best['alpha']
print('  总误差最小在 α = %.1f。<strong>再往上就是拿语音失真换噪声抑制</strong>，'
      '而听感上失真比残留噪声更伤。' % best['alpha'])

# ══ ③ 谱底：音乐噪声的第一道补丁 ═══════════════════════════════
print('\n③ 谱底（spectral floor）：不让增益降到零')
OUT['floor'] = []
print('  %8s %8s %7s %7s %9s' % ('谱底 dB', 'SegSNR', 'LSD', 'STOI*', '音乐噪声'))
for fdb in (-60.0, -30.0, -20.0, -15.0, -10.0, -6.0):
    z, G, Y = enhance(y, lam, g_subtract, alpha=2.0, floor=10 ** (fdb / 20))
    r = {'floor_db': fdb, 'segsnr': round(E.seg_snr(x, z, m), 2),
         'lsd': round(E.lsd(x, z, mask=m), 2), 'stoi': round(E.stoi_like(x, z, mask=m), 3),
         'mus': round(E.musical(G * V, fm), 2),
         'kurt': round(E.kurt_ratio(G * V, V, fm), 2)}
    OUT['floor'].append(r)
    print('  %8.0f %8.2f %7.2f %7.3f %8.2f'
          % (fdb, r['segsnr'], r['lsd'], r['stoi'], r['mus']))
print('  谱底每抬高 10 dB，音乐噪声降一截，代价是残留噪声的绝对量上升。')
print('  它是一个<strong>纯粹的听感补丁</strong>：任何客观信噪比指标都不喜欢它。')

# ══ ④ 增益曲线本身 ════════════════════════════════════════════
gam_fix = 10 ** (np.linspace(-15, 25, 161) / 10)
OUT['curve'] = {'gamma_db': [round(10 * np.log10(g), 2) for g in gam_fix]}
for tag, gf, kw in (('sub', g_subtract, dict(alpha=1.0, floor=0.0)),
                    ('wiener', g_wiener, {}),
                    ('stsa', g_stsa, {}),
                    ('logmmse', g_logmmse, {})):
    # 画增益曲线时取 ξ = γ − 1（瞬时最大似然），这是"没有平滑"的极限情形
    xi = np.maximum(gam_fix - 1.0, 1e-3)
    g = gf(xi, gam_fix, **kw)
    OUT['curve'][tag] = [round(float(20 * np.log10(max(v, 1e-6))), 2) for v in g]
# 固定 ξ 的一族曲线：显示 log-MMSE 在低 γ 时的额外抑制
OUT['curve_fixed_xi'] = {}
for xdb in (-10.0, 0.0, 10.0):
    xi = np.full_like(gam_fix, 10 ** (xdb / 10))
    OUT['curve_fixed_xi'][str(int(xdb))] = {
        'stsa': [round(float(20 * np.log10(max(v, 1e-6))), 2)
                 for v in g_stsa(xi, gam_fix)],
        'logmmse': [round(float(20 * np.log10(max(v, 1e-6))), 2)
                    for v in g_logmmse(xi, gam_fix)],
        'wiener': [round(float(20 * np.log10(max(v, 1e-6))), 2)
                   for v in g_wiener(xi, gam_fix)]}

# 增益 vs 先验信噪比（取 γ = ξ+1，即"观测与假设一致"的那条切面）
xi_ax = 10 ** (np.linspace(-25, 20, 181) / 10)
gam_ax = 1.0 + xi_ax
OUT['curve_xi'] = {'xi_db': [round(10 * math.log10(v), 2) for v in xi_ax]}
for tag, gf, kw in (('sub', g_subtract, dict(alpha=1.0, floor=0.0)),
                    ('wiener', g_wiener, {}),
                    ('stsa', g_stsa, {}),
                    ('logmmse', g_logmmse, {})):
    g = gf(xi_ax, gam_ax, **kw)
    OUT['curve_xi'][tag] = [round(float(20 * math.log10(max(v, 1e-6))), 2) for v in g]

# ══ ⑤ 四种噪声下的 log-MMSE ═══════════════════════════════════
print('\n⑤ 换噪声类型：平稳性决定了这一整套方法还灵不灵')
OUT['noises'] = []
for kind in ('white', 'pink', 'car', 'babble'):
    vk = E.make_noise(kind, len(x), seed=3)
    yk, vk2 = E.mix_at_snr(x, vk, 5.0, m)
    lamk = np.mean(np.abs(E.stft(vk2, NFFT, HOP)) ** 2, axis=0)[None, :]
    z, G, Y = enhance(yk, lamk, g_logmmse)
    Sk = E.stft(x[:len(yk)], NFFT, HOP); Vk = E.stft(vk2[:len(yk)], NFFT, HOP)
    fmk = E.frame_mask(m, len(Sk), NFFT, HOP)
    d = E.decompose(Sk, Vk, G)
    # 噪声本身有多不平稳：各频点功率的帧间起伏
    nonstat = E.nonstat(Vk)
    r = {'kind': kind, 'nonstat': round(nonstat, 2),
         'in_segsnr': round(E.seg_snr(x, yk, m), 2),
         'out_segsnr': round(E.seg_snr(x, z, m), 2),
         'gain': round(E.seg_snr(x, z, m) - E.seg_snr(x, yk, m), 2),
         'lsd': round(E.lsd(x, z, mask=m), 2),
         'stoi_in': round(E.stoi_like(x, yk, mask=m), 3),
         'stoi_out': round(E.stoi_like(x, z, mask=m), 3),
         'sd_db': round(d['sd_db'], 1), 'nr_db': round(d['nr_db'], 1)}
    OUT['noises'].append(r)
    print('  %-7s 非平稳度 %5.2f dB   SegSNR %5.2f → %5.2f（+%.2f）  STOI* %.3f → %.3f'
          % (kind, r['nonstat'], r['in_segsnr'], r['out_segsnr'], r['gain'],
             r['stoi_in'], r['stoi_out']))
print('  <strong>噪声越不平稳，这一族方法的收益越小</strong>——'
      '它们全都建立在"噪声功率谱在几百毫秒里不变"这个假设上。')

json.dump(OUT, open('demo_gain.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_gain.json')
