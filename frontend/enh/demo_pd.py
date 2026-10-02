#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""当前的真正难点：把"保真"和"像真的"分开量，再看"编出来"从哪里开始。

   预测式增强只会削，所以它的失效方式是"削过头"；
   生成式增强会<strong>填</strong>，它的失效方式是"填错"。
   这一组实验用一个最小的生成式后处理（按估计出的谱包络填回成形噪声），
   扫一个填充强度 β，同时量三类东西：
     ① 保真类：SegSNR / LSD
     ② 像不像真的：残差起伏、长时谱距离
     ③ 填错了没有：帧级最近邻位移——这一帧现在更像哪一帧
   三类指标的最优 β 不在同一个地方，而第三类有一个明确的拐点。
"""
import numpy as np, json, time
import enhlib as E
from enhlib import g_logmmse, dd_xi, est_imcra

OUT = {}
t0 = time.time()
NFFT, HOP = 512, 256
NB = 24
NOISES = ('white', 'pink', 'babble')
SNR = 5.0
SEEDS = (900, 901, 902)
BETAS = (0.0, 0.1, 0.2, 0.35, 0.5, 0.7, 1.0)


def bands(nbin=NFFT // 2 + 1, nb=NB, sr=E.SR):
    f = np.linspace(0, sr / 2, nbin)
    mel = lambda x: 2595 * np.log10(1 + x / 700)
    imel = lambda x: 700 * (10 ** (x / 2595) - 1)
    e = imel(np.linspace(mel(50), mel(sr / 2 - 100), nb + 2))
    W = np.zeros((nb, nbin))
    for b in range(nb):
        lo, c, hi = e[b], e[b + 1], e[b + 2]
        up = (f >= lo) & (f <= c); dn = (f > c) & (f <= hi)
        W[b, up] = (f[up] - lo) / max(c - lo, 1e-9)
        W[b, dn] = (hi - f[dn]) / max(hi - c, 1e-9)
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    Wt = W.T / np.maximum(W.sum(0)[:, None], 1e-9)
    return W, Wt


WB, WT = bands()


def pair(seed, kind, snr=SNR):
    x, segs = E.make_speech(dur=3.0, seed=seed)
    m = E.speech_mask(segs, len(x))
    v = E.make_noise(kind, len(x), seed=seed * 7 + 11)
    y, vv = E.mix_at_snr(x, v, snr, m)
    n = len(y)
    return (x[:n], y, m[:n], E.stft(x[:n], NFFT, HOP),
            E.stft(vv[:n], NFFT, HOP), E.stft(y, NFFT, HOP))


def enhance(Y):
    """预测式的底子：IMCRA + 判决引导 + log-MMSE。β=0 时就是它本身。"""
    lam = est_imcra(np.abs(Y) ** 2)
    xi, gam = dd_xi(Y, lam, 0.98)
    return g_logmmse(xi, gam), lam


def generative(Y, G, lam, beta, seed=0):
    """把被削掉的那部分，按<strong>估计出来的语音谱包络</strong>填回成形噪声。
       它没有用到任何干净语音——只用了带噪谱和噪声估计，
       所以这是一个（极简的）生成式后处理，而不是作弊。"""
    g = np.random.default_rng(seed + 31)
    Ps = np.maximum(np.abs(G * Y) ** 2, 1e-12)
    Eb = Ps @ WB.T                               # 频带能量 → 平滑的谱包络
    for _ in range(2):                           # 频带方向平滑两遍
        Eb = np.concatenate([Eb[:, :1], Eb, Eb[:, -1:]], 1)
        Eb = (Eb[:, :-2] + 2 * Eb[:, 1:-1] + Eb[:, 2:]) / 4
    Env = np.maximum(Eb @ WT.T, 1e-12)
    cut = np.maximum(np.abs(Y) ** 2 - Ps, 0.0)   # 被削掉的能量
    amp = np.sqrt(beta * np.minimum(cut, Env))   # 填多少：不超过包络本身
    ph = np.exp(2j * np.pi * g.random(Y.shape))
    return G * Y + amp * ph


def ltas(X):
    p = np.mean(np.abs(X) ** 2, 0)
    return 10 * np.log10(p / (np.sum(p) + E.EPS) + 1e-12)


def err_kinds(Sc, Sz, fm, keep_db=15.0, quiet_db=25.0, tol_db=15.0):
    """把误差分成两种，分开数格子（只在有语音的帧上，按每帧峰值归一化）：
         删掉了：干净谱里显著的格子，输出里却掉了 15 dB 以上
         编出来了：干净谱里本来是"静"的格子，输出里却长到了峰值以下 15 dB 以内
       预测式只会犯第一种，生成式会开始犯第二种。"""
    sel = fm > 0.5
    if sel.sum() < 4:
        return 0.0, 0.0
    A = 20 * np.log10(np.abs(Sc[sel]) + 1e-12)
    B = 20 * np.log10(np.abs(Sz[sel]) + 1e-12)
    pk = A.max(1, keepdims=True)
    strong = A > pk - keep_db
    quiet = A < pk - quiet_db
    miss = strong & (B < A - 15.0)
    hall = quiet & (B > pk - tol_db)
    return (float(miss.sum() / max(strong.sum(), 1)),
            float(hall.sum() / max(quiet.sum(), 1)))


print('扫填充强度 β：预测式（β=0）→ 生成式（β=1）')
OUT['sweep'] = []
for b in BETAS:
    rs = []
    for k in NOISES:
        for sd in SEEDS:
            x, y, m, S, V, Y = pair(sd, k)
            G, lam = enhance(Y)
            Z = generative(Y, G, lam, b, seed=sd)
            z = E.istft(Z, NFFT, HOP, n=len(y))[:len(y)]
            fm = E.frame_mask(m, len(S), NFFT, HOP)
            res = Z - S                          # 残差（含削过头和填错两部分）
            rs.append((E.seg_snr(x, z, m), E.lsd(x, z, mask=m),
                       E.stoi_like(x, z, mask=m), E.musical(res, fm),
                       float(np.mean(np.abs(ltas(Z[fm > 0.5]) - ltas(S[fm > 0.5])))),
                       *err_kinds(S, Z, fm)))
    a = np.mean(rs, 0)
    r = {'beta': b, 'segsnr': round(float(a[0]), 2), 'lsd': round(float(a[1]), 2),
         'stoi': round(float(a[2]), 3), 'mus': round(float(a[3]), 2),
         'ltas': round(float(a[4]), 2), 'miss': round(float(a[5]) * 100, 1),
         'hall': round(float(a[6]) * 100, 2)}
    OUT['sweep'].append(r)
    print('  β=%.2f  SegSNR %5.2f  LSD %5.2f  STOI* %.3f  残差起伏 %5.2f  '
          '长时谱距 %4.2f dB  删掉 %4.1f%%  编出来 %4.2f%%'
          % (b, r['segsnr'], r['lsd'], r['stoi'], r['mus'], r['ltas'],
             r['miss'], r['hall']))

best = {}
for key, better in (('segsnr', max), ('lsd', min), ('stoi', max),
                    ('mus', lambda s, **k: min(s, key=lambda r: abs(r['mus'] - E.MUS_FLOOR_DB))),
                    ('ltas', min), ('miss', min), ('hall', min)):
    if key == 'mus':
        best[key] = min(OUT['sweep'], key=lambda r: abs(r['mus'] - E.MUS_FLOOR_DB))['beta']
    else:
        best[key] = better(OUT['sweep'], key=lambda r: r[key])['beta']
OUT['best_beta'] = best
print('\n各指标各自最优的 β：' +
      '  '.join('%s→%.2f' % (k, v) for k, v in best.items()))
OUT['n_distinct_beta'] = len(set(best.values()))

b0 = OUT['sweep'][0]
OUT['elbow'] = None
for r in OUT['sweep'][1:]:
    if r['hall'] > b0['hall'] * 2 and OUT['elbow'] is None:
        OUT['elbow'] = r['beta']
OUT['summary'] = {
    'seg_cost': round(b0['segsnr'] - OUT['sweep'][-1]['segsnr'], 2),
    'ltas_gain': round(b0['ltas'] - min(r['ltas'] for r in OUT['sweep']), 2),
    'ltas_best': best['ltas'],
    'mus_floor': round(float(E.MUS_FLOOR_DB), 2),
    'miss_b0': b0['miss'], 'miss_b1': OUT['sweep'][-1]['miss'],
    'hall_b0': b0['hall'], 'hall_b1': OUT['sweep'][-1]['hall'],
    'hall_ratio': round(OUT['sweep'][-1]['hall'] / max(b0['hall'], 1e-9), 1),
    'miss_gain': round(b0['miss'] - OUT['sweep'][-1]['miss'], 1),
    'n_distinct_beta': OUT['n_distinct_beta'],
    'elbow': OUT['elbow'],
}
print('从 β=0 到 β=1：SegSNR 掉 %.2f dB，长时谱距改善 %.2f dB，'
      '"删掉"从 %.1f%% 降到 %.1f%%，而"编出来"从 %.2f%% 涨到 %.2f%%（%.1f 倍）。'
      % (OUT['summary']['seg_cost'], OUT['summary']['ltas_gain'],
         OUT['summary']['miss_b0'], OUT['summary']['miss_b1'],
         OUT['summary']['hall_b0'], OUT['summary']['hall_b1'],
         OUT['summary']['hall_ratio']))

# ══ 同一组信号上，两种失效方式各自长什么样 ════════════════════
print('\n两种失效方式的对照：削过头 vs 填错')
OUT['modes'] = []
for tag, b, over in (('预测式·保守（α 小）', 0.0, 'under'),
                     ('预测式·削过头', 0.0, 'over'),
                     ('生成式·填到底', 1.0, 'none')):
    rs = []
    for k in NOISES:
        for sd in SEEDS:
            x, y, m, S, V, Y = pair(sd, k)
            lam = est_imcra(np.abs(Y) ** 2)
            sc = {'under': 0.4, 'over': 2.5, 'none': 1.0}[over]
            xi, gam = dd_xi(Y, lam * sc, 0.98)
            G = g_logmmse(xi, gam)
            Z = generative(Y, G, lam, b, seed=sd)
            z = E.istft(Z, NFFT, HOP, n=len(y))[:len(y)]
            fm = E.frame_mask(m, len(S), NFFT, HOP)
            rs.append((E.seg_snr(x, z, m), E.lsd(x, z, mask=m),
                       E.stoi_like(x, z, mask=m), E.musical(Z - S, fm),
                       *err_kinds(S, Z, fm)))
    a = np.mean(rs, 0)
    OUT['modes'].append({'tag': tag, 'segsnr': round(float(a[0]), 2),
                         'lsd': round(float(a[1]), 2), 'stoi': round(float(a[2]), 3),
                         'mus': round(float(a[3]), 2),
                         'miss': round(float(a[4]) * 100, 1),
                         'hall': round(float(a[5]) * 100, 2)})
    r = OUT['modes'][-1]
    print('  %-18s SegSNR %5.2f  LSD %5.2f  STOI* %.3f  起伏 %5.2f  '
          '删掉 %4.1f%%  编出来 %4.2f%%'
          % (tag, r['segsnr'], r['lsd'], r['stoi'], r['mus'], r['miss'], r['hall']))

OUT['const'] = {'snr': SNR, 'noises': list(NOISES), 'betas': list(BETAS),
                'nb': NB, 'nfft': NFFT, 'hop': HOP}
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_pd.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_pd.json（%.0f s）' % OUT['runtime_s'])
