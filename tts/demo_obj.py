#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""33 节算例：客观指标——四个指标，几种排序；以及"合法的另一种读法"被打多少分。

   参考：一句话（ttssim 合成，音素与时长已知）。六种候选：
     ① 合法的另一种读法：同一串音素，语速 0.82–1.22 倍、各音素时长各自抖动 ±25%、基频中枢 98–148 Hz（12 种的均值）
     ② 声码器金属音：非线性失真 + 3 dB 的周期性调幅（转置卷积那种）
     ③ 过平滑：对数谱沿时间平滑 3 帧（L2 回归的典型症状），保留原相位
     ④ 加噪：白噪 20 dB
     ⑤ 变速变调：重采样 ×1.03（音高与共振峰上移 3%，时长缩短 3%）
     ⑥ 高频丢失：4 kHz 低通
   三个参考式指标：MCD（带 DTW 对齐 / 不对齐）、基频 RMSE（cents，DTW 路径上共同浊音帧；F0 取生成器真值，所以它<strong>只反映韵律、对波形质量完全不敏感</strong>）、LSD（STFT 对数谱距离，DTW 对齐）。
   这些都是"和一条参考比"的指标；没有听测，所以这一节只回答"几个指标是否同意排序"，不回答"哪个排序对"。
"""
import numpy as np, json, math, time
from ttssim import SR, HOP, NFFT, NMEL, melspec, utterance, stft, istft

t0 = time.time()
OUT = {}
BASE = [('sil', 'n', 180), ('sh', 'f', 130), ('a', 'v', 190), ('n', 'v', 90),
        ('t', 'p', 70), ('i', 'v', 210), ('sil', 'n', 90), ('h', 'f', 90),
        ('o', 'v', 230), ('u', 'v', 160), ('s', 'f', 140), ('e', 'v', 250), ('sil', 'n', 200)]


def plan(k):
    g = np.random.default_rng(100 + k)
    rate = g.uniform(0.82, 1.22)
    ph = [(p, t, max(30, int(d * rate * g.uniform(0.78, 1.28)))) for p, t, d in BASE]
    return ph, g.uniform(98.0, 148.0)


def f0_truth(u):
    """生成器给的真值 F0（Hz；清音 / 静音为 0）——取帧中心，浊音占一半以上才算浊音帧"""
    n = 1 + (len(u['x']) - NFFT) // HOP
    c = NFFT // 2 + HOP * np.arange(n)
    c = np.minimum(c, len(u['f0']) - 1)
    return np.where(u['voiced'][c] > 0.5, u['f0'][c], 0.0)


UREF = utterance(BASE, seed=7, f0_mean=120.0)
F0REF = f0_truth(UREF)
REF = UREF['x']
REF = REF + 1e-3 * np.random.default_rng(9).standard_normal(len(REF))     # 录音总有底噪：静音不是数字零

# ── 特征 ──
NC = 13
DCT = np.sqrt(2.0 / NMEL) * np.cos(np.pi / NMEL * (np.arange(NMEL)[None, :] + 0.5) * np.arange(NC + 1)[:, None])


def mcep(x):
    M = melspec(x, floor=1e-3)           # (80, T) 对数梅尔；底限 1e-3（1e-5 会让静音与高频丢失主导 MCD）
    return (DCT @ M)[1:].T                                           # (T, 13)，去掉 c0，正交 DCT


def dtw(A, B):
    """A、B：(T,d)；返回对齐路径上的下标对"""
    n, m = len(A), len(B)
    D = np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(2))
    C = np.full((n + 1, m + 1), np.inf)
    C[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            C[i, j] = D[i - 1, j - 1] + min(C[i - 1, j], C[i, j - 1], C[i - 1, j - 1])
    i, j = n, m
    path = []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = int(np.argmin([C[i - 1, j - 1], C[i - 1, j], C[i, j - 1]]))
        i, j = (i - 1, j - 1) if k == 0 else ((i - 1, j) if k == 1 else (i, j - 1))
    return path[::-1]


def logmag(x):
    return np.log(np.abs(stft(x, NFFT, HOP)) + 1e-3)


def metrics(ref, cand, fr, fc, align=True):
    Cr, Cc = mcep(ref), mcep(cand)
    Lr, Lc = logmag(ref).T, logmag(cand).T
    if align:
        p = dtw(Cr, Cc)
        ia = np.array([a for a, _ in p]); ib = np.array([b for _, b in p])
    else:
        n = min(len(Cr), len(Cc))
        ia = ib = np.arange(n)
    mcd = float(np.mean(np.sqrt(2 * ((Cr[ia] - Cc[ib]) ** 2).sum(1))) * 10 / math.log(10))
    nf = min(len(fr), len(fc))
    ja, jb = np.minimum(ia, len(fr) - 1), np.minimum(ib, len(fc) - 1)
    both = (fr[ja] > 0) & (fc[jb] > 0)
    f0 = float(np.sqrt(np.mean((1200 * np.log2(fc[jb][both] / fr[ja][both])) ** 2))) if both.any() else float('nan')
    lsd = float(np.mean(np.sqrt(np.mean((Lr[np.minimum(ia, len(Lr) - 1)] - Lc[np.minimum(ib, len(Lc) - 1)]) ** 2, 1))))
    # 浊音帧判定一致率（不对齐时无意义，仍记录）
    return {'mcd': mcd, 'f0': f0, 'lsd': lsd}


def smooth_time(x, w=3):
    S = stft(x, NFFT, HOP)
    lm = np.log(np.abs(S) + 1e-5)
    k = np.ones(2 * w + 1) / (2 * w + 1)
    lm = np.stack([np.convolve(np.pad(lm[i], w, mode='edge'), k, 'valid') for i in range(lm.shape[0])])
    return istft(np.exp(lm) * np.exp(1j * np.angle(S)), NFFT, HOP)[:len(x)]


def vocoder_metal(x):
    y = np.tanh(2.5 * x) / np.tanh(2.5)
    t = np.arange(len(x)) / SR
    y = y * (1 + 0.19 * np.sin(2 * np.pi * (SR / HOP) * t))      # ≈3 dB 峰峰的周期调幅
    return y / (np.max(np.abs(y)) + 1e-12)


def add_noise(x, snr=20.0, seed=3):
    g = np.random.default_rng(seed)
    v = g.standard_normal(len(x))
    return x + v * np.sqrt(np.mean(x ** 2) / 10 ** (snr / 10)) / (v.std() + 1e-12)


def resample(x, f):
    n = int(len(x) / f)
    t = np.arange(n) * f
    i = np.minimum(t.astype(int), len(x) - 2)
    fr = t - i
    return x[i] * (1 - fr) + x[i + 1] * fr


def lowpass(x, fc=4000.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[f > fc] = 0
    return np.fft.irfft(X, len(x))


CANDS = [('legal', '合法的另一种读法（12 种均值）'), ('metal', '声码器金属音'), ('smooth', '过平滑'),
         ('noise', '加噪 20 dB'), ('pitch', '变速变调 ×1.03'), ('lp', '4 kHz 低通')]
RES = {}
legal = []
for k in range(12):
    ph, f0m = plan(k)
    uc = utterance(ph, seed=200 + k, f0_mean=f0m)
    cand = uc['x'] + 1e-3 * np.random.default_rng(900 + k).standard_normal(len(uc['x']))
    fc = f0_truth(uc)
    legal.append((metrics(REF, cand, F0REF, fc, True), metrics(REF, cand, F0REF, fc, False)))
RES['legal'] = {'dtw': {m: float(np.nanmean([a[0][m] for a in legal])) for m in ('mcd', 'f0', 'lsd')},
                'raw': {m: float(np.nanmean([a[1][m] for a in legal])) for m in ('mcd', 'f0', 'lsd')},
                'sd_mcd': float(np.std([a[0]['mcd'] for a in legal]))}
for key, fn in (('metal', vocoder_metal), ('smooth', smooth_time), ('noise', add_noise),
                ('pitch', lambda x: resample(x, 1.03)), ('lp', lowpass)):
    cand = fn(REF)
    # F0 取真值：除变调 ×1.03（音高 +3%，时间轴 −3%）之外，其余退化不改变 F0 曲线本身
    if key == 'pitch':
        f = F0REF
        n = int(len(f) / 1.03)
        fc = np.where(f[np.minimum((np.arange(n) * 1.03).astype(int), len(f) - 1)] > 0,
                      f[np.minimum((np.arange(n) * 1.03).astype(int), len(f) - 1)] * 1.03, 0.0)
    else:
        fc = F0REF.copy()
    RES[key] = {'dtw': metrics(REF, cand, F0REF, fc, True), 'raw': metrics(REF, cand, F0REF, fc, False)}
OUT['rows'] = []
print('六种候选 × 指标（DTW 对齐 / 不对齐）')
for key, nm in CANDS:
    r = {'key': key, 'name': nm, 'mcd': round(RES[key]['dtw']['mcd'], 2), 'f0': round(RES[key]['dtw']['f0'], 1),
         'lsd': round(RES[key]['dtw']['lsd'], 3), 'mcd_raw': round(RES[key]['raw']['mcd'], 2),
         'f0_raw': round(RES[key]['raw']['f0'], 1), 'lsd_raw': round(RES[key]['raw']['lsd'], 3)}
    OUT['rows'].append(r)
    print('  %-22s MCD %5.2f dB  F0 %6.1f cents  LSD %.3f | 不对齐：MCD %5.2f F0 %6.1f LSD %.3f'
          % (nm, r['mcd'], r['f0'], r['lsd'], r['mcd_raw'], r['f0_raw'], r['lsd_raw']))
# 排名（1 = 最好 / 最像参考）
for m in ('mcd', 'f0', 'lsd', 'mcd_raw', 'f0_raw', 'lsd_raw'):
    dg = {'mcd': 1, 'f0': 0, 'lsd': 3, 'mcd_raw': 1, 'f0_raw': 0, 'lsd_raw': 3}[m]
    vals = np.round(np.array([r[m] for r in OUT['rows']]), dg)             # 按显示精度并列
    rk = np.array([1 + int((vals < v).sum()) for v in vals])
    for r, k in zip(OUT['rows'], rk):
        r['rank_' + m] = int(k)


def kendall(a, b):
    n = len(a)
    c = d = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = np.sign(a[i] - a[j]) * np.sign(b[i] - b[j])
            c += s > 0
            d += s < 0
    return float((c - d) / (n * (n - 1) / 2))


tau = {}
for a, b in (('mcd', 'f0'), ('mcd', 'lsd'), ('f0', 'lsd'), ('mcd', 'mcd_raw')):
    tau[a + '-' + b] = round(kendall([r['rank_' + a] for r in OUT['rows']], [r['rank_' + b] for r in OUT['rows']]), 2)
OUT['tau'] = tau
R = {r['key']: r for r in OUT['rows']}
OUT['note'] = {
    'legal_rank_mcd': R['legal']['rank_mcd'], 'legal_rank_f0': R['legal']['rank_f0'], 'legal_rank_lsd': R['legal']['rank_lsd'],
    'legal_mcd': R['legal']['mcd'], 'legal_f0': R['legal']['f0'], 'legal_mcd_raw': R['legal']['mcd_raw'],
    'metal_mcd': R['metal']['mcd'], 'metal_rank_mcd': R['metal']['rank_mcd'], 'metal_f0': R['metal']['f0'],
    'noise_mcd': R['noise']['mcd'], 'smooth_mcd': R['smooth']['mcd'], 'smooth_rank_mcd': R['smooth']['rank_mcd'],
    'lp_mcd': R['lp']['mcd'], 'lp_rank_mcd': R['lp']['rank_mcd'], 'lp_lsd': R['lp']['lsd'], 'lp_rank_lsd': R['lp']['rank_lsd'],
    'pitch_f0': R['pitch']['f0'], 'pitch_mcd': R['pitch']['mcd'], 'pitch_rank_f0': R['pitch']['rank_f0'],
    'legal_sd_mcd': round(RES['legal']['sd_mcd'], 2),
    'tau_mcd_f0': tau['mcd-f0'], 'tau_mcd_lsd': tau['mcd-lsd'], 'tau_f0_lsd': tau['f0-lsd'], 'tau_dtw_raw': tau['mcd-mcd_raw'],
}
OUT['const'] = {'ncand': 12, 'nc': NC, 'sr': SR, 'sec': round(len(REF) / SR, 2)}
OUT['runtime_s'] = round(time.time() - t0, 1)
print(json.dumps(OUT['tau']), json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_obj.json', 'w'), ensure_ascii=False)
print('写出 demo_obj.json %.1f s' % OUT['runtime_s'])
