#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""16 节算例：时长从哪来。
   单调对齐搜索（MAS）跑在一段边界已知的合成语音上，
   和"均分"、"不带单调约束的软注意力"对比，误差直接用毫秒报；
   再按边界类型拆开，看误差到底集中在哪儿。"""
import numpy as np, json, math
from ttssim import SR, HOP, NMEL, melspec, utterance

OUT = {}
u = utterance()
M = melspec(u['x'])
T = M.shape[1]
ph = u['phones']
I = len(ph)
bnd_true = np.round(np.array(u['bnd']) / HOP).astype(int)
bnd_true[-1] = T
dur_true = np.diff(bnd_true)
ms = HOP / SR * 1000
OUT['cfg'] = {'T': int(T), 'I': int(I), 'frame_ms': round(ms, 3),
              'dur_true': [int(d) for d in dur_true],
              'phones': [p[0] for p in ph]}
print('%d 帧（每帧 %.2f ms），%d 个音素。真实时长（帧）：%s'
      % (T, ms, I, [int(d) for d in dur_true]))

npaths = math.comb(T - 1, I - 1)
OUT['npaths_log10'] = round(math.log10(npaths), 1)
print('单调对齐的总数 C(%d,%d) ≈ 10^%.1f —— 必须用动态规划，和 CTC 是同一件事'
      % (T - 1, I - 1, math.log10(npaths)))

# 每个音素一个对角高斯（Glow-TTS / VITS 的先验形态）。
# 这里直接用真实切分的统计量，相当于"文本编码器已经训好"，
# 把"对齐"这一步单独拿出来看它自己能做到多准。
mu = np.zeros((I, NMEL)); sg = np.zeros((I, NMEL))
for i, (a, b) in enumerate(zip(bnd_true[:-1], bnd_true[1:])):
    seg = M[:, a:b]
    mu[i] = seg.mean(1)
    sg[i] = seg.std(1) + 0.35
d = (M.T[None] - mu[:, None]) / sg[:, None]
maha = -0.5 * (d ** 2).sum(-1)
logdet = -np.log(sg).sum(-1)[:, None]
sg_sh = np.tile(M.std(1) + 0.35, (I, 1))
dsh = (M.T[None] - mu[:, None]) / sg_sh[:, None]
SCORES = {
    '标准高斯（每音素 σ）': maha + logdet,
    '共享 σ': -0.5 * (dsh ** 2).sum(-1) - np.log(sg_sh).sum(-1)[:, None],
    '每音素 σ，去掉 logdet 项': maha,
}


def mas(L):
    """单调对齐搜索：每帧归且仅归一个音素，音素顺序固定，每个至少一帧。"""
    I, T = L.shape
    Q = np.full((I, T), -1e30)
    bt = np.zeros((I, T), np.int8)
    Q[0, 0] = L[0, 0]
    for t in range(1, T):
        Q[0, t] = Q[0, t - 1] + L[0, t]
        for i in range(1, min(t + 1, I)):
            if Q[i - 1, t - 1] > Q[i, t - 1]:
                Q[i, t] = Q[i - 1, t - 1] + L[i, t]; bt[i, t] = 1
            else:
                Q[i, t] = Q[i, t - 1] + L[i, t]
    path = np.zeros(T, int); i = I - 1
    for t in range(T - 1, -1, -1):
        path[t] = i
        if bt[i, t] == 1:
            i -= 1
    return path


def evaluate(L):
    p = mas(L)
    dur = np.bincount(p, minlength=I)
    b = np.r_[0, np.cumsum(dur)]
    e = np.abs(b[1:-1] - bnd_true[1:-1]) * ms
    return p, dur, b, e


OUT['variants'] = []
print('\n三种打分写法，同一个 DP：')
print('  %-24s MAE      最大    ±20ms   最短音素' % '')
for tag, L in SCORES.items():
    p, dur, b, e = evaluate(L)
    r = {'tag': tag, 'mae': round(float(e.mean()), 2), 'max': round(float(e.max()), 1),
         'within20': round(float((e <= 20).mean() * 100)), 'minlen': int(dur.min())}
    OUT['variants'].append(r)
    print('  %-24s %5.2f ms %6.1f ms %4.0f%%    %d 帧'
          % (tag, r['mae'], r['max'], r['within20'], r['minlen']))
print('  <- logdet 那一项给"方差小的音素"额外加分，会让它多吃帧；'
      '去掉它反而更准，但那就不是最大似然了')

L = SCORES['标准高斯（每音素 σ）']
path, dur_mas, bnd_mas, err_mas = evaluate(L)
OUT['mas'] = {'dur': [int(x) for x in dur_mas], 'mae_ms': round(float(err_mas.mean()), 2),
              'max_ms': round(float(err_mas.max()), 1),
              'within20': round(float((err_mas <= 20).mean() * 100))}

# ══ 误差集中在哪种边界上 ═════════════════════════════════════
grp = {}
OUT['bnd'] = []
for i in range(1, I):
    e = abs(bnd_mas[i] - bnd_true[i]) * ms
    a_, b_ = ph[i - 1][1], ph[i][1]
    kind = ('静音 ↔ 有声' if 'n' in (a_, b_) else
            '浊音 → 浊音' if a_ == 'v' and b_ == 'v' else '有明显谱突变')
    grp.setdefault(kind, []).append(e)
    OUT['bnd'].append([ph[i - 1][0], ph[i][0], kind, round(float(e), 1)])
OUT['bykind'] = {k: [len(v), round(float(np.mean(v)), 1)] for k, v in grp.items()}
print('\n按边界类型拆开（标准写法）：')
for k, (n, m) in OUT['bykind'].items():
    print('  %-12s n=%d   平均误差 %5.1f ms' % (k, n, m))
print('  <strong>误差几乎全在"浊音→浊音"上</strong>——那里本来就没有边界，')
print('  共振峰是连续滑过去的，人工标注同样标不准。')

# ══ 基线① 均分 ═══════════════════════════════════════════════
bnd_u = np.round(np.linspace(0, T, I + 1)).astype(int)
err_u = np.abs(bnd_u[1:-1] - bnd_true[1:-1]) * ms
OUT['uniform'] = {'mae_ms': round(float(err_u.mean()), 1), 'max_ms': round(float(err_u.max()), 1)}
print('\n基线① 均分：平均 %.1f ms，最大 %.1f ms（GMM-HMM 的冷启动就从这里迭代）'
      % (OUT['uniform']['mae_ms'], OUT['uniform']['max_ms']))

# ══ 基线② 去掉单调约束 ═══════════════════════════════════════
hard = L.argmax(0)
nonmono = int(np.sum(np.diff(hard) < 0))
skipped = [ph[i][0] for i in range(I) if i not in set(hard.tolist())]
OUT['soft'] = {'nonmono': nonmono, 'nonmono_pct': round(nonmono / (T - 1) * 100, 1),
               'skipped': skipped, 'n_skipped': len(skipped)}
print('\n基线② 逐帧取似然最大、不加单调约束：')
print('  %d / %d 处（%.1f%%）"时间倒流"；%d 个音素一帧没分到：%s'
      % (nonmono, T - 1, OUT['soft']['nonmono_pct'], len(skipped), '、'.join(skipped) or '无'))
print('  <strong>漏词和重复读，结构上就是这两件事</strong>。'
      'Tacotron 的软注意力没有任何机制禁止它们；MAS / CTC / RNN-T 在结构上禁止。')

# ══ 时长本身能预测到什么程度 ═════════════════════════════════
BASE = [('sil', 'n', 180), ('sh', 'f', 130), ('a', 'v', 190), ('n', 'v', 90),
        ('t', 'p', 70), ('i', 'v', 210), ('sil', 'n', 90), ('h', 'f', 90),
        ('o', 'v', 230), ('u', 'v', 160), ('s', 'f', 140), ('e', 'v', 250),
        ('sil', 'n', 200)]
DUR = []
for k in range(64):
    g = np.random.default_rng(500 + k)
    rate = g.uniform(0.82, 1.22)
    DUR.append([max(30, int(d * rate * g.uniform(0.78, 1.28))) for _, _, d in BASE])
DUR = np.array(DUR, float)
res = DUR - DUR.mean(0)
OUT['durpred'] = {'sd_ms': round(float(DUR.std(0).mean()), 1),
                  'mae_ms': round(float(np.abs(res).mean()), 1),
                  'r2': round(float(1 - res.var() / DUR.var()), 3)}
print('\n时长预测的上限：只知道"是哪个音素"时，R² = %.3f，但绝对误差仍有 %.1f ms'
      % (OUT['durpred']['r2'], OUT['durpred']['mae_ms']))
print('  R² 高是因为音素之间差别大，不是因为同一个音素好预测。')
print('  <strong>韵律就住在那 ±%.0f ms 的残差里</strong>，它要靠上下文和风格解释。'
      % OUT['durpred']['mae_ms'])

np.save('align_L.npy', L.astype(np.float32))
np.save('align_path.npy', path)
np.save('align_mel.npy', M.astype(np.float32))
json.dump(OUT, open('demo_align.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_align.json')
