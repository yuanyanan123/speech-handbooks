#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""13 节算例：扩散 vs 流匹配，为什么 TTS 转向了 ODE，以及步数值多少。

   关键设计：目标分布取一维高斯混合，于是<strong>两条路径的最优向量场都有闭式解</strong>。
   不训练任何网络——这样测出来的误差就<em>只</em>来自求解器和步数，
   和"模型学得好不好"彻底分开。"""
import numpy as np, json, math

rng = np.random.default_rng(0)
OUT = {}

# 目标：三峰混合（当成"某一维梅尔在所有合法读法上的分布"）
W = np.array([0.35, 0.40, 0.25])
Mu = np.array([-2.2, 0.4, 2.6])
Sd = np.array([0.45, 0.30, 0.55])
OUT['target'] = {'w': W.tolist(), 'mu': Mu.tolist(), 'sd': Sd.tolist()}


def sample_target(n, g):
    k = g.choice(3, size=n, p=W)
    return Mu[k] + Sd[k] * g.standard_normal(n)


def w2(a, b):
    """一维 Wasserstein-2：排序后逐分位相减，精确"""
    a = np.sort(a); b = np.sort(b)
    return float(np.sqrt(np.mean((a - b) ** 2)))


N = 200000
SEEDS = (10, 11, 12)
ref = sample_target(N, np.random.default_rng(1))
FLOOR = float(np.mean([w2(sample_target(N, np.random.default_rng(300 + i)), ref)
                       for i in range(8)]))
OUT['N'] = N
OUT['floor'] = round(FLOOR, 4)
print('目标分布：三峰高斯混合，每次 %d 个样本。' % N)
print('另取 8 组真样本与参考比，W2 平均 %.4f ← 这就是采样噪声地板，低于它没意义'
      % FLOOR)

# ══ VP 扩散（DDPM 那一支） ══════════════════════════════════
B0, B1 = 0.1, 20.0


def beta(t):
    return B0 + t * (B1 - B0)


def alpha(t):
    return np.exp(-0.5 * (B0 * t + 0.5 * t * t * (B1 - B0)))


def score_vp(x, t):
    """p_t = Σ w_k N(α m_k, α² s_k² + 1-α²)，score 有闭式解"""
    a = alpha(t)
    v = a * a * Sd ** 2 + (1 - a * a)
    m = a * Mu
    d = x[:, None] - m[None, :]
    lg = -0.5 * d ** 2 / v[None, :] - 0.5 * np.log(2 * np.pi * v)[None, :] + np.log(W)[None, :]
    lg -= lg.max(1, keepdims=True)
    g = np.exp(lg); g /= g.sum(1, keepdims=True)
    return (g * (-d / v[None, :])).sum(1)


def ddim(n_steps, g):
    """概率流 ODE，从 t=1 积回 t=0，Euler"""
    x = g.standard_normal(N)
    ts = np.linspace(1.0, 1e-3, n_steps + 1)
    for i in range(n_steps):
        t, dt = ts[i], ts[i + 1] - ts[i]
        x = x + (-0.5 * beta(t) * (x + score_vp(x, t))) * dt
    return x


def ddpm(n_steps, g):
    """反向 SDE，祖先采样"""
    x = g.standard_normal(N)
    ts = np.linspace(1.0, 1e-3, n_steps + 1)
    for i in range(n_steps):
        t, dt = ts[i], ts[i + 1] - ts[i]        # dt < 0
        b = beta(t)
        drift = -0.5 * b * x - b * score_vp(x, t)
        x = x + drift * dt + math.sqrt(b * abs(dt)) * g.standard_normal(N)
    return x


# ══ 流匹配（OT / rectified 路径） ═══════════════════════════
def vfield(x, t):
    """x_t=(1-t)x0+t x1，x0~N(0,1)，x1~混合。E[x1-x0 | x_t] 同样闭式。"""
    V = t * t * Sd ** 2 + (1 - t) ** 2
    m = t * Mu
    d = x[:, None] - m[None, :]
    lg = -0.5 * d ** 2 / V[None, :] - 0.5 * np.log(2 * np.pi * V)[None, :] + np.log(W)[None, :]
    lg -= lg.max(1, keepdims=True)
    g = np.exp(lg); g /= g.sum(1, keepdims=True)
    e1 = Mu[None, :] + (t * Sd ** 2 / V)[None, :] * d          # E[x1 | x_t, k]
    e0 = ((1 - t) / V)[None, :] * d                            # E[x0 | x_t, k]
    return (g * (e1 - e0)).sum(1)


def fm_euler(n_steps, g):
    x = g.standard_normal(N)
    ts = np.linspace(1e-3, 1.0, n_steps + 1)
    for i in range(n_steps):
        t, dt = ts[i], ts[i + 1] - ts[i]
        x = x + vfield(x, t) * dt
    return x


def fm_heun(n_steps, g):
    """二阶（Heun），一步两次函数调用，所以 NFE = 2×步数"""
    x = g.standard_normal(N)
    ts = np.linspace(1e-3, 1.0, n_steps + 1)
    for i in range(n_steps):
        t, dt = ts[i], ts[i + 1] - ts[i]
        k1 = vfield(x, t)
        k2 = vfield(x + dt * k1, ts[i + 1])
        x = x + dt * 0.5 * (k1 + k2)
    return x


NFE = [1, 2, 4, 8, 16, 32, 64, 128]
OUT['curves'] = {'nfe': NFE, 'ddpm': [], 'ddim': [], 'fm': [], 'fm_heun': []}
print('\nNFE = 网络前向次数（真实系统里它<strong>就是</strong>延迟）')
print(' NFE   DDPM(SDE)   DDIM(ODE)   流匹配-Euler   流匹配-Heun')
def avg(fn, n):
    return float(np.mean([w2(fn(n, np.random.default_rng(s)), ref) for s in SEEDS]))


for n in NFE:
    a = avg(ddpm, n)
    b = avg(ddim, n)
    c = avg(fm_euler, n)
    dh = avg(fm_heun, max(1, n // 2)) if n >= 2 else float('nan')
    for k, v in zip(('ddpm', 'ddim', 'fm', 'fm_heun'), (a, b, c, dh)):
        OUT['curves'][k].append(None if v != v else round(v, 4))
    print('%4d   %8.4f   %8.4f   %10.4f   %10s'
          % (n, a, b, c, '—' if dh != dh else '%.4f' % dh))
print('地板 %.4f（两组真样本之间的距离，低于它就没意义了）' % FLOOR)


def first_below(key, thr):
    for n, v in zip(NFE, OUT['curves'][key]):
        if v is not None and v <= thr:
            return n
    return None


THR = round(FLOOR * 1.5, 4)
OUT['thr'] = THR
OUT['nfe_at_thr'] = {k: first_below(k, THR) for k in ('ddpm', 'ddim', 'fm', 'fm_heun')}
print('\n达到 W2 ≤ %.4f（1.5 倍地板）所需的 NFE：' % THR)
for k, v in OUT['nfe_at_thr'].items():
    print('   %-10s %s' % (k, v if v else '>128'))

# ══ 为什么流匹配步数少：路径直不直 ═══════════════════════════
def straightness(vf, ts, n=4000, kind='fm'):
    """E|| (x1-x0) - v(x_t,t) ||²：越小说明这条路径越接近直线"""
    g = np.random.default_rng(5)
    x0 = g.standard_normal(n)
    x1 = sample_target(n, np.random.default_rng(6))
    out = []
    for t in ts:
        if kind == 'fm':
            xt = (1 - t) * x0 + t * x1
            v = vf(xt, t)
            ideal = x1 - x0
        else:
            a = alpha(t)
            xt = a * x1 + math.sqrt(max(1 - a * a, 1e-9)) * x0
            # 概率流 ODE 的瞬时速度，换成"从 t 到 0"的方向
            v = -(-0.5 * beta(t) * (xt + vf(xt, t)))
            ideal = (x1 - xt) / max(t, 1e-3)
        out.append(float(np.mean((ideal - v) ** 2)))
    return np.array(out)


ts = np.linspace(0.05, 0.95, 19)
s_fm = straightness(vfield, ts, kind='fm')
s_vp = straightness(score_vp, ts, kind='vp')
OUT['straight'] = {'t': [round(float(x), 3) for x in ts],
                   'fm': [round(float(x), 4) for x in s_fm],
                   'vp': [round(float(x), 4) for x in s_vp],
                   'fm_mean': round(float(s_fm.mean()), 4),
                   'vp_mean': round(float(s_vp.mean()), 4)}
print('\n路径弯曲度 E‖真实位移 − 当前速度‖²（越小越直，直线一步就能走完）：')
print('   流匹配 OT 路径  平均 %.4f' % s_fm.mean())
print('   VP 扩散路径     平均 %.4f' % s_vp.mean())
print('   <strong>差的就是这个</strong>：欧拉法的误差 ∝ 路径曲率 × 步长²。')

# ══ 把路径掰直：reflow ═══════════════════════════════════════
# 先用精确 ODE 把噪声 z 送到数据 T(z)，再<strong>只在这一对 (z, T(z)) 上</strong>
# 重新定义路径 x_t=(1-t)z+t·T(z)。一维里 T 单调，直线路径互不相交，
# 于是新的边缘速度场就是常数 T(z)-z —— 一步走完，且精确。
from scipy.stats import norm
xs = np.linspace(-8, 8, 400001)
cdf = np.zeros_like(xs)
for wk, mk, sk in zip(W, Mu, Sd):
    cdf += wk * norm.cdf(xs, mk, sk)


def reflow_1step(seed):
    z = np.sort(np.random.default_rng(seed).standard_normal(N))
    return np.interp(norm.cdf(z), cdf, xs)          # = 精确 ODE 的终点


OUT['reflow'] = {'w2_1step': round(float(np.mean(
    [w2(reflow_1step(s_), ref) for s_ in SEEDS])), 4)}
print('\n把路径掰直（reflow）之后，<strong>一步</strong>的 W2 = %.4f（地板 %.4f）'
      % (OUT['reflow']['w2_1step'], FLOOR))
print('   一维里这是精确的：单调映射的直线路径互不相交，速度场恒等于 T(z)−z。')
print('   高维里路径会相交，掰不直，所以真实系统仍要 4–32 步——')
print('   <strong>"一步生成"是蒸馏出来的，不是流匹配自带的</strong>。')

# ══ 换算成延迟 ═══════════════════════════════════════════════
OUT['latency'] = []
for step_ms in (3.0, 8.0):
    row = {'step_ms': step_ms}
    for k in ('ddpm', 'ddim', 'fm_heun'):
        n = OUT['nfe_at_thr'][k]
        row[k] = None if n is None else round(n * step_ms, 1)
    OUT['latency'].append(row)
print('\n换成延迟：单步 3 ms 的声学模型')
for row in OUT['latency']:
    print('   单步 %.0f ms → DDPM %s ms，DDIM %s ms，流匹配+Heun %s ms'
          % (row['step_ms'], row['ddpm'], row['ddim'], row['fm_heun']))

json.dump(OUT, open('demo_flow.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_flow.json')
