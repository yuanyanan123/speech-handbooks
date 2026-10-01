#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""18 节算例：音频 tokenizer。
   残差矢量量化（RVQ）跑在一批合成语音的隐表示上，
   量码率、重建误差、码本利用率，以及 LLM-TTS 最关心的那个数：每秒几个 token。"""
import numpy as np, json, math
from ttssim import SR, HOP, NMEL, melspec, utterance, VOWELS

rng = np.random.default_rng(0)
OUT = {}

# ══ 造一批"语料"：不同音素串、不同语速、不同基频 ═══════════════
PH = list(VOWELS) + ['n', 'm', 'l']
FR = ['s', 'sh', 'f', 'h', 'x']
PL = ['t', 'p', 'k']


def rand_utt(k):
    g = np.random.default_rng(1000 + k)
    seq = [('sil', 'n', int(g.uniform(80, 200)))]
    for _ in range(g.integers(6, 11)):
        r = g.random()
        if r < .55:
            seq.append((g.choice(PH), 'v', int(g.uniform(90, 260))))
        elif r < .8:
            seq.append((g.choice(FR), 'f', int(g.uniform(70, 160))))
        else:
            seq.append((g.choice(PL), 'p', int(g.uniform(50, 100))))
    seq.append(('sil', 'n', int(g.uniform(80, 200))))
    return utterance(seq, seed=2000 + k, f0_mean=float(g.uniform(95, 210)))


NU = 150
MELS = [melspec(rand_utt(k)['x']) for k in range(NU)]
X = np.concatenate(MELS, 1).T.astype(np.float64)          # (T, 80)
T = X.shape[0]
fps = SR / HOP
OUT['data'] = {'utts': NU, 'frames': int(T), 'dim': NMEL,
               'secs': round(T / fps, 1), 'fps': round(fps, 2)}
print('语料：%d 句，共 %d 帧（%.1f 秒），每帧 %d 维，帧率 %.2f Hz'
      % (NU, T, T / fps, NMEL, fps))

mu, sd = X.mean(0), X.std(0) + 1e-6
Z = (X - mu) / sd                                         # 归一化，当作编码器输出


# ══ k-means ═════════════════════════════════════════════════
def assign(Y, C):
    d = (Y ** 2).sum(1)[:, None] - 2 * Y @ C.T + (C ** 2).sum(1)[None, :]
    return d.argmin(1), d


def kmeans(Y, K, iters=25, seed=0):
    g = np.random.default_rng(seed)
    C = Y[g.choice(len(Y), K, replace=False)].copy()
    D = Y.shape[1]
    for _ in range(iters):
        a, d = assign(Y, C)
        cnt = np.bincount(a, minlength=K)
        S = np.zeros((K, D)); np.add.at(S, a, Y)
        live = cnt > 0
        C[live] = S[live] / cnt[live, None]
        if (~live).any():                                  # 死码：搬到误差最大的点
            worst = np.argsort(-d.min(1))[:int((~live).sum())]
            C[~live] = Y[worst] + 1e-3 * g.standard_normal(((~live).sum(), D))
    a, _ = assign(Y, C)
    return C, a


def rvq(Y, nq, K, seed=0):
    R = Y.copy()
    books, idxs = [], []
    for q in range(nq):
        C, a = kmeans(R, K, seed=seed + q)
        books.append(C); idxs.append(a)
        R = R - C[a]
    return books, np.stack(idxs), R


def snr(Y, R):
    return 10 * math.log10(np.sum(Y ** 2) / np.sum(R ** 2))


K = 1024
NQ = 8
sub = Z[rng.choice(T, min(T, 40000), replace=False)]
books, idxs, _ = rvq(sub, NQ, K, seed=7)

# 用全部数据评估
R = Z.copy()
OUT['ladder'] = []
bits = math.log2(K)
print('\n码本大小 %d（每级 %.0f bit），残差逐级量化：' % (K, bits))
print('  级数  码率(kbps)  token/秒  重建 SNR  梅尔谱误差  码本利用率  困惑度')
for q in range(NQ):
    C = books[q]
    a, _ = assign(R, C)
    R = R - C[a]
    used = len(np.unique(a))
    p = np.bincount(a, minlength=K) / len(a)
    perp = float(np.exp(-(p[p > 0] * np.log(p[p > 0])).sum()))
    rec = (Z - R) * sd + mu
    lsd = float(np.sqrt(np.mean((rec - X) ** 2)))          # 对数梅尔域的 RMSE
    row = {'nq': q + 1, 'kbps': round((q + 1) * bits * fps / 1000, 2),
           'tok_s': round((q + 1) * fps, 1), 'snr': round(snr(Z, R), 2),
           'lsd': round(lsd, 4), 'used': used,
           'used_pct': round(used / K * 100, 1), 'perp': round(perp, 1)}
    OUT['ladder'].append(row)
    print('  %3d   %8.2f   %7.1f   %6.2f dB   %8.4f   %4d (%4.1f%%)  %7.1f'
          % (row['nq'], row['kbps'], row['tok_s'], row['snr'], row['lsd'],
             row['used'], row['used_pct'], row['perp']))
print('  （"梅尔谱误差"是对数梅尔域的 RMSE，1.0 大约相当于 8.7 dB）')

# ══ 为什么不用一个大码本 ═════════════════════════════════════
OUT['why_rvq'] = {'equiv_bits': int(NQ * bits),
                  'equiv_size': '2^%d' % int(NQ * bits),
                  'kmeans_cost': '%.1e' % (2.0 ** (NQ * bits))}
print('\n%d 级 × %.0f bit = %d bit，等价于一个 2^%d ≈ 10^%.0f 条目的单码本——'
      % (NQ, bits, NQ * bits, NQ * bits, NQ * bits * math.log10(2)))
print('  存不下，更别说训。<strong>RVQ 把指数变成了线性</strong>：'
      '%d 个 %d×%d 的表，总参数 %.2f M。'
      % (NQ, K, NMEL, NQ * K * NMEL / 1e6))

# ══ 码本坍塌：初始化差一点会怎样 ═════════════════════════════
def rvq_collapse(seed, kill_dead=True):
    R = sub.copy(); us = []
    g = np.random.default_rng(seed)
    for q in range(4):
        C = g.standard_normal((K, sub.shape[1])) * 0.05      # 随机小初始化，不用数据点
        D = sub.shape[1]
        for _ in range(25):
            a, d = assign(R, C)
            cnt = np.bincount(a, minlength=K)
            S = np.zeros((K, D)); np.add.at(S, a, R)
            live = cnt > 0
            C[live] = S[live] / cnt[live, None]
            if kill_dead and (~live).any():
                worst = np.argsort(-d.min(1))[:int((~live).sum())]
                C[~live] = R[worst] + 1e-3 * g.standard_normal(((~live).sum(), D))
        a, _ = assign(R, C)
        us.append(len(np.unique(a)))
        R = R - C[a]
    return us, snr(sub, R)


u_no, s_no = rvq_collapse(5, kill_dead=False)
u_yes, s_yes = rvq_collapse(5, kill_dead=True)
OUT['collapse'] = {'no_revive': {'used': u_no, 'snr': round(s_no, 2)},
                   'revive': {'used': u_yes, 'snr': round(s_yes, 2)}}
print('\n码本坍塌（随机小初始化，不用数据点）：')
print('  不救死码：前四级各用了 %s 个码，4 级后 SNR %.2f dB' % (u_no, s_no))
print('  救死码：  前四级各用了 %s 个码，4 级后 SNR %.2f dB' % (u_yes, s_yes))
print('  <strong>差的不是算法，是那几行"把没人用的码搬到误差最大处"</strong>')

# ══ LLM-TTS 的上下文预算 ═════════════════════════════════════
OUT['ctx'] = []
print('\n给 LLM-TTS 算上下文：')
for rate, name in ((fps, '梅尔帧率 86 Hz'), (75.0, '常见 75 Hz'), (50.0, '常见 50 Hz'),
                   (25.0, '低帧率 25 Hz')):
    for nq in (1, 4, 8):
        row = {'rate': round(rate, 1), 'nq': nq, 'tok_s': round(rate * nq, 1),
               'tok_10s': int(round(rate * nq * 10)),
               'kbps': round(rate * nq * bits / 1000, 2)}
        OUT['ctx'].append(row)
    print('  %-14s  1 级 %5.0f tok/s   4 级 %5.0f   8 级 %5.0f   '
          '→ 10 秒话 8 级 = %d 个 token'
          % (name, rate, rate * 4, rate * 8, round(rate * 8 * 10)))
print('  <strong>这就是 LLM-TTS 为什么拼命压帧率</strong>：'
      'token 数直接变成上下文长度和首包延迟。')

json.dump(OUT, open('demo_rvq.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_rvq.json')
