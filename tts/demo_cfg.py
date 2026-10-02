#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""29 节算例：引导（classifier-free guidance）——它到底在补什么，补过头又是什么。

   一维"声学量"（比如某一维归一化的基频或谱倾斜），两种说话风格 A / B，每种风格自己是双峰，彼此有重叠：
       p(x|A) = 0.6 N(−1.6, 0.5²) + 0.4 N(0.2, 0.35²)
       p(x|B) = 0.5 N( 0.9, 0.4²) + 0.5 N(2.4, 0.5²)
   和 14 节一样，流匹配路径下的<strong>最优向量场有闭式解</strong>，不训练任何网络。
   条件模型的"条件项"被学小了的情形：v̂_c = v_u + λ (v_c − v_u)，λ=1 是完美，λ<1 是条件项学得偏弱。
   引导：v_g = v̂_c + s (v̂_c − v_u)。

   ① λ=1 时引导有什么用：准确（风格遵循）、真实（落在真分布里的似然）、多样（两个子峰的占比）
   ② λ<1 时引导补回了什么：s = 1/λ − 1 正好把条件项补回
   ③ 补过头：s 继续加，样本被推到哪里
"""
import numpy as np, json, math

OUT = {}
N = 100000
STEPS = 100
SEED = 5

CLS = {
    'A': dict(w=np.array([0.6, 0.4]), mu=np.array([-1.6, 0.2]), sd=np.array([0.5, 0.35])),
    'B': dict(w=np.array([0.5, 0.5]), mu=np.array([0.9, 2.4]), sd=np.array([0.4, 0.5])),
}
UNC = dict(w=np.concatenate([0.5 * CLS['A']['w'], 0.5 * CLS['B']['w']]),
           mu=np.concatenate([CLS['A']['mu'], CLS['B']['mu']]),
           sd=np.concatenate([CLS['A']['sd'], CLS['B']['sd']]))


def vfield(x, t, P):
    """x_t=(1-t)x0+t x1，x0~N(0,1)，x1~混合 P；返回 E[x1-x0 | x_t=x]"""
    w, mu, sd = P['w'], P['mu'], P['sd']
    v = (1 - t) ** 2 + t * t * sd ** 2
    d = x[:, None] - t * mu[None, :]
    lg = -0.5 * d ** 2 / v[None, :] - 0.5 * np.log(2 * np.pi * v)[None, :] + np.log(w)[None, :]
    lg -= lg.max(1, keepdims=True)
    g = np.exp(lg)
    g /= g.sum(1, keepdims=True)
    vel = mu[None, :] + (t * sd ** 2 - (1 - t))[None, :] / v[None, :] * d
    return (g * vel).sum(1)


def sample(cls, lam, s, n=N, seed=SEED):
    g = np.random.default_rng(seed)
    x = g.standard_normal(n)
    dt = 1.0 / STEPS
    for i in range(STEPS):
        t = i * dt
        vu = vfield(x, t, UNC)
        vc = vfield(x, t, CLS[cls])
        vh = vu + lam * (vc - vu)
        x = x + (vh + s * (vh - vu)) * dt
    return x


def pdf(x, P):
    w, mu, sd = P['w'], P['mu'], P['sd']
    return (w[None, :] / (sd[None, :] * math.sqrt(2 * math.pi)) *
            np.exp(-0.5 * ((x[:, None] - mu[None, :]) / sd[None, :]) ** 2)).sum(1)


def w2(a, b):
    a, b = np.sort(a), np.sort(b)
    return float(np.sqrt(np.mean((a - b) ** 2)))


def truth(cls, n=N, seed=99):
    g = np.random.default_rng(seed)
    P = CLS[cls]
    k = g.choice(len(P['w']), size=n, p=P['w'])
    return P['mu'][k] + P['sd'][k] * g.standard_normal(n)


REF = {c: truth(c) for c in CLS}
# 采样噪声地板：真样本对真样本
FLOOR = float(np.mean([w2(truth('A', seed=200 + i), REF['A']) for i in range(4)]))


def metrics(x, cls):
    other = 'B' if cls == 'A' else 'A'
    pc, po = pdf(x, CLS[cls]), pdf(x, CLS[other])
    adh = float(np.mean(pc > po))                     # 贝叶斯判决（两风格先验相等）认为它属于目标风格的比例
    ll = float(np.mean(np.log(np.maximum(pc, 1e-300))))      # 目标风格真分布下的平均对数似然（越高越"像"）
    # 两个子峰的占比：以两峰中点划分
    P = CLS[cls]
    cut = float(P['mu'].mean())
    share_lo = float(np.mean(x < cut))
    return {'adh': round(100 * adh, 1), 'll': round(ll, 3), 'sd': round(float(np.std(x)), 3),
            'share_lo': round(100 * share_lo, 1), 'w2': round(w2(x, REF[cls]), 3),
            'mean': round(float(np.mean(x)), 3)}


TRUE = {c: metrics(REF[c], c) for c in CLS}
OUT['true'] = TRUE
OUT['floor'] = round(FLOOR, 4)
print('真分布自己：', TRUE, '采样地板 W2 %.4f' % FLOOR)

# ══ ① ② λ 与 s ══════════════════════════════════════════════
LAMS = (1.0, 0.5, 0.25)
SS = (0.0, 0.5, 1.0, 2.0, 3.0, 5.0)
OUT['grid'] = []
print('\n风格 A 的生成：')
for lam in LAMS:
    row = {'lam': lam, 'cells': []}
    for s in SS:
        x = sample('A', lam, s)
        m = metrics(x, 'A')
        m.update({'s': s, 'eff': round(lam * (1 + s), 2)})
        row['cells'].append(m)
        print('  λ=%.2f s=%.1f (有效条件强度 λ(1+s)=%.2f)  遵循 %5.1f%%  均值似然 %7.3f  标准差 %.3f  左峰占比 %5.1f%%  W2 %.3f'
              % (lam, s, m['eff'], m['adh'], m['ll'], m['sd'], m['share_lo'], m['w2']))
    OUT['grid'].append(row)

# ══ 直方图：λ=1 时不同 s 的样本分布（画图用）══════════════════
OUT['hist'] = {'edges': [round(float(v), 3) for v in np.linspace(-3.2, 3.6, 41)], 'dens': {}}
for s in (0.0, 1.0, 2.0, 5.0):
    h, _ = np.histogram(sample('A', 1.0, s), bins=np.linspace(-3.2, 3.6, 41), density=True)
    OUT['hist']['dens'][str(s)] = [round(float(v), 4) for v in h]

# ══ 补过头：更细的 s 扫描（λ=0.5）══════════════════════════
OUT['fine'] = []
for s in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0):
    x = sample('A', 0.5, s)
    m = metrics(x, 'A')
    m['s'] = s
    m['frac_out'] = round(100 * float(np.mean((x < CLS['A']['mu'][0] - 3 * CLS['A']['sd'][0]) |
                                              (x > CLS['A']['mu'][1] + 3 * CLS['A']['sd'][1]))), 2)
    OUT['fine'].append(m)

G = {r['lam']: {c['s']: c for c in r['cells']} for r in OUT['grid']}
F = {m['s']: m for m in OUT['fine']}
bestw2 = min(OUT['grid'][1]['cells'], key=lambda c: c['w2'])
OUT['note'] = {
    'perfect_adh': G[1.0][0.0]['adh'], 'perfect_w2': G[1.0][0.0]['w2'], 'perfect_sd': G[1.0][0.0]['sd'],
    'perfect_lo': G[1.0][0.0]['share_lo'], 'true_lo': TRUE['A']['share_lo'],
    's2_adh': G[1.0][2.0]['adh'], 's2_w2': G[1.0][2.0]['w2'], 's2_sd': G[1.0][2.0]['sd'], 's2_lo': G[1.0][2.0]['share_lo'],
    's2_ll': G[1.0][2.0]['ll'], 'perfect_ll': G[1.0][0.0]['ll'],
    's5_adh': G[1.0][5.0]['adh'], 's5_w2': G[1.0][5.0]['w2'], 's5_sd': G[1.0][5.0]['sd'], 's5_ll': G[1.0][5.0]['ll'],
    's5_lo': G[1.0][5.0]['share_lo'],
    'weak_adh': G[0.5][0.0]['adh'], 'weak_w2': G[0.5][0.0]['w2'],
    'weak_fix_s': 1.0, 'weak_fix_adh': G[0.5][1.0]['adh'], 'weak_fix_w2': G[0.5][1.0]['w2'], 'weak_fix_sd': G[0.5][1.0]['sd'],
    'weak2_adh': G[0.25][0.0]['adh'], 'weak2_w2': G[0.25][0.0]['w2'],
    'weak2_fix_adh': G[0.25][3.0]['adh'], 'weak2_fix_w2': G[0.25][3.0]['w2'],
    'weak_best_s': bestw2['s'], 'weak_best_w2': bestw2['w2'],
    'true_adh': TRUE['A']['adh'], 'true_sd': TRUE['A']['sd'], 'true_ll': TRUE['A']['ll'],
    'floor': OUT['floor'],
    'fine8_adh': F[8.0]['adh'], 'fine8_ll': F[8.0]['ll'], 'fine8_out': F[8.0]['frac_out'], 'fine8_sd': F[8.0]['sd'],
    'fine8_mean': F[8.0]['mean'],
}
OUT['const'] = {'n': N, 'steps': STEPS, 'lams': list(LAMS), 'ss': list(SS)}
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_cfg.json', 'w'), ensure_ascii=False)
print('写出 demo_cfg.json')
