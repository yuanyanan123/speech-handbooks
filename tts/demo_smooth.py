#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""02 / 09 / 11 节算例：一对多映射 + L2 损失 = 过平滑，
   以及"把时长和基频拿出来单独建模"到底消掉了多少不确定性。

   同一串音素读 N 遍，每一遍的语速、各音素时长、基频中枢都不同（都合法）。
   分三步剥：绝对时间轴 → 对齐时长 → 再固定基频，看残差方差还剩多少。"""
import numpy as np, json, math
from ttssim import SR, HOP, NMEL, melspec, utterance

OUT = {}
N = 24
BASE = [('sil', 'n', 180), ('sh', 'f', 130), ('a', 'v', 190), ('n', 'v', 90),
        ('t', 'p', 70), ('i', 'v', 210), ('sil', 'n', 90), ('h', 'f', 90),
        ('o', 'v', 230), ('u', 'v', 160), ('s', 'f', 140), ('e', 'v', 250),
        ('sil', 'n', 200)]
MEAN_F0 = 120.0


def plan(k):
    g = np.random.default_rng(100 + k)
    rate = g.uniform(0.82, 1.22)
    ph = [(p, t, max(30, int(d * rate * g.uniform(0.78, 1.28)))) for p, t, d in BASE]
    return ph, g.uniform(98.0, 148.0)


PL = [plan(k) for k in range(N)]
durs = np.array([[p[2] for p in ph] for ph, _ in PL], float)
f0s = np.array([f for _, f in PL])
tot = durs.sum(1)
OUT['read'] = {'n': N, 'dur_mean': round(float(tot.mean())),
               'dur_lo': round(float(tot.min())), 'dur_hi': round(float(tot.max())),
               'dur_cv': round(float(tot.std() / tot.mean() * 100), 1),
               'f0_lo': round(float(f0s.min()), 1), 'f0_hi': round(float(f0s.max()), 1)}
print('%d 种合法读法：整句 %.0f ms（%.0f–%.0f，变异系数 %.1f%%），基频中枢 %.0f–%.0f Hz'
      % (N, tot.mean(), tot.min(), tot.max(), OUT['read']['dur_cv'], f0s.min(), f0s.max()))
cv = durs.std(0) / durs.mean(0) * 100
OUT['phone_cv'] = [[BASE[i][0], round(float(durs.mean(0)[i])), round(float(cv[i]), 1)]
                   for i in range(len(BASE))]
print('单个音素的时长变异系数：'
      + '  '.join('%s %.0f%%' % (p, c) for p, _, c in OUT['phone_cv']))
print('<- 时长不是文本的函数，是一个分布；这是 TTS 和 ASR 的根本差别\n')

MEANF = int(round(durs.mean(0).sum() / 1000 * SR / HOP))
TGT = np.round(np.cumsum(np.r_[0, durs.mean(0)]) / 1000 * SR / HOP).astype(int)


def mel_of(ph, f0m, seed):
    return melspec(utterance(ph, seed=seed, f0_mean=f0m)['x']), \
        np.round(np.cumsum(np.r_[0, [p[2] for p in ph]]) / 1000 * SR / HOP).astype(int)


def to_abs(M, L):
    """不做任何对齐，只按绝对时间轴截齐 / 补静音——朴素 seq2seq 面对的就是这个"""
    out = np.full((NMEL, L), M[:, :1].mean())
    n = min(L, M.shape[1])
    out[:, :n] = M[:, :n]
    return out


def to_warp(M, bnd):
    """按音素边界线性规整到平均时长——等于"时长已经被显式建模了" """
    out = np.zeros((NMEL, TGT[-1]))
    for i in range(len(BASE)):
        a, b = bnd[i], min(bnd[i + 1], M.shape[1])
        ta, tb = TGT[i], TGT[i + 1]
        if b <= a or tb <= ta:
            continue
        src = np.linspace(0, b - a - 1, tb - ta)
        for k in range(NMEL):
            out[k, ta:tb] = np.interp(src, np.arange(b - a), M[k, a:b])
    return out


A, B, C = [], [], []                      # 绝对轴 / 对齐时长 / 再固定基频
for k, (ph, f0m) in enumerate(PL):
    M, bnd = mel_of(ph, f0m, 200 + k)
    A.append(to_abs(M, MEANF))
    B.append(to_warp(M, bnd))
    M2, bnd2 = mel_of(ph, MEAN_F0, 200 + k)       # 同样的时长，基频固定
    C.append(to_warp(M2, bnd2))
A, B, C = np.stack(A), np.stack(B), np.stack(C)


def stats(X, tag):
    mu = X.mean(0)
    v = X.var(0).mean()                    # 逐时频点、跨读法的方差
    gv_r = X.var(2).mean()                 # 单次读法沿时间的全局方差
    gv_m = mu.var(1).mean()
    ct_r = float(np.mean([np.mean(np.array(
        [np.ptp(x[max(0, i - 3):i + 4], 0) for i in range(NMEL)])) for x in X]))
    ct_m = float(np.mean(np.array(
        [np.ptp(mu[max(0, i - 3):i + 4], 0) for i in range(NMEL)])))
    return {'tag': tag, 'var_across': float(v), 'gv_db': float(10 * math.log10(gv_m / gv_r)),
            'ct_real': ct_r, 'ct_mean': ct_m, 'ct_loss': (1 - ct_m / ct_r) * 100}


sA, sB, sC = stats(A, '绝对时间轴'), stats(B, '对齐时长'), stats(C, '对齐时长 + 固定基频')
tot_v = sA['var_across']
OUT['peel'] = []
prev = tot_v
for s in (sA, sB, sC):
    OUT['peel'].append({'tag': s['tag'],
                        'var': round(s['var_across'], 4),
                        'var_pct': round(s['var_across'] / tot_v * 100, 1),
                        'gv_db': round(s['gv_db'], 2),
                        'ct_loss': round(s['ct_loss'], 1)})
print('逐层剥掉不确定性（方差 = 同一时频点在 %d 种读法之间的方差）：' % N)
print('  %-22s 跨读法方差  占比    条件均值的全局方差  峰谷对比度损失' % '')
for r in OUT['peel']:
    print('  %-22s %8.4f  %5.1f%%   %8.2f dB        %5.1f%%'
          % (r['tag'], r['var'], r['var_pct'], r['gv_db'], r['ct_loss']))
OUT['explain'] = {
    'dur': round((sA['var_across'] - sB['var_across']) / tot_v * 100, 1),
    'f0': round((sB['var_across'] - sC['var_across']) / tot_v * 100, 1),
    'rest': round(sC['var_across'] / tot_v * 100, 1)}
print('\n  → 时长解释了 %.1f%% 的不确定性，基频再解释 %.1f%%，剩下 %.1f%% 是别的'
      % (OUT['explain']['dur'], OUT['explain']['f0'], OUT['explain']['rest']))
print('  <strong>这就是 FastSpeech2 那个 variance adaptor 的全部理由</strong>：')
print('  把时长和基频从"要靠 L2 猜的东西"变成"先预测、再当条件喂进去的东西"。')

# ══ L1 / 采样 / GV 补偿 ═══════════════════════════════════════
def ct(M):
    return float(np.mean(np.array([np.ptp(M[max(0, i - 3):i + 4], 0) for i in range(NMEL)])))


mu, med = A.mean(0), np.median(A, 0)
gv_r = A.var(2).mean()
OUT['loss'] = {
    'l2_gv': round(float(10 * math.log10(mu.var(1).mean() / gv_r)), 2),
    'l1_gv': round(float(10 * math.log10(med.var(1).mean() / gv_r)), 2),
    'l2_ct': round(ct(mu), 3), 'l1_ct': round(ct(med), 3),
    'real_ct': round(float(np.mean([ct(x) for x in A])), 3),
    'samp_ct': round(ct(A[5]), 3)}
print('\n在绝对时间轴上（= 不做时长建模）：')
print('  L2 最优解（条件均值）  全局方差 %+.2f dB  对比度 %.3f'
      % (OUT['loss']['l2_gv'], OUT['loss']['l2_ct']))
print('  L1 最优解（条件中位数）全局方差 %+.2f dB  对比度 %.3f'
      % (OUT['loss']['l1_gv'], OUT['loss']['l1_ct']))
print('  随便抽一遍真实读法                        对比度 %.3f  ← 真值'
      % OUT['loss']['real_ct'])
print('  L1 好一点，但病根没动：<strong>中位数同样是一个点，而答案是一个分布</strong>')

s = math.sqrt(gv_r / mu.var(1).mean())
gvc = (mu - mu.mean(1, keepdims=True)) * s + mu.mean(1, keepdims=True)
OUT['gvc'] = {'scale': round(float(s), 3), 'ct': round(ct(gvc), 3)}
print('\nHMM-TTS 时代的补丁（GV 补偿）：把均值的方差乘 %.3f 拉回去，对比度 %.3f → %.3f'
      % (s, OUT['loss']['l2_ct'], OUT['gvc']['ct']))
print('  数字回来了，放大的却是<strong>被平均糊掉的那个形状</strong>，不是真实细节')

np.save('smooth_A.npy', A[:6].astype(np.float32))
np.save('smooth_muA.npy', mu.astype(np.float32))
np.save('smooth_B.npy', B[:6].astype(np.float32))
np.save('smooth_muB.npy', B.mean(0).astype(np.float32))
json.dump(OUT, open('demo_smooth.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_smooth.json')
