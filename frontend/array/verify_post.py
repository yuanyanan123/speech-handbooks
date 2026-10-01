#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§18 后置滤波：Zelinski / McCowan 的偏差，以及音乐噪声的方差来源。"""
import numpy as np
rng = np.random.default_rng(20260916)
c = 343.0; M = 4; d = 0.035

def Gam(f):
    m = np.arange(M); D = np.abs(m[:,None]-m[None,:])*d
    return np.sinc(2*f*D/c)

def gbar(f):
    G = Gam(f); iu = np.triu_indices(M,1); return G[iu].mean()

print('══ 1. 蒙特卡洛验证互谱模型 Φ_ij = φ_s + φ_n Γ_ij ══')
for f in [200, 1000, 4000]:
    G = Gam(f); L = np.linalg.cholesky(G+1e-12*np.eye(M))
    N = 200000; phis, phin = 1.0, 1.0
    s = (rng.standard_normal(N)+1j*rng.standard_normal(N))/np.sqrt(2)*np.sqrt(phis)
    z = (rng.standard_normal((N,M))+1j*rng.standard_normal((N,M)))/np.sqrt(2)*np.sqrt(phin)
    n = z@L.T
    x = s[:,None]+n                       # 已对齐（导向相位已补掉）
    P = (x.conj().T@x)/N
    iu = np.triu_indices(M,1)
    print('  f=%5d  Γ̄=%.4f | 实测 mean Re Φ_ij=%.4f 理论 %.4f | mean Φ_ii=%.4f 理论 %.4f'
          % (f, gbar(f), np.real(P[iu]).mean(), phis+phin*gbar(f),
             np.real(np.diag(P)).mean(), phis+phin))

print('\n══ 2. 两个估计器的增益与真值（输入 SNR = 0 dB）══')
print('   f(Hz)    Γ̄     G_true  G_Zelinski  G_McCowan   Zelinski 少压(dB)')
xi = 1.0
for f in [125,250,500,1000,2000,4000,8000]:
    gb = gbar(f)
    Gt = xi/(1+xi); Gz = (xi+gb)/(1+xi)
    # McCowan：逐对解 φ_s，再平均
    G = Gam(f); iu = np.triu_indices(M,1)
    Pij = xi + G[iu]; Pii = xi+1
    phis_hat = np.mean((Pij - G[iu]*Pii)/(1-G[iu]))
    Gm = phis_hat/Pii
    print('  %6d  %6.3f  %6.4f   %6.4f     %6.4f     %5.2f'
          % (f, gb, Gt, Gz, Gm, -20*np.log10(Gt)+20*np.log10(Gz)))

print('\n══ 3. Zelinski 完全失效的频率（少压超过 3 dB 处）══')
for xi_db in [-10, -5, 0, 5, 10]:
    xi = 10**(xi_db/10)
    fs = np.linspace(50, 8000, 4000); bad = None
    for f in fs:
        gb = gbar(f)
        loss = 20*np.log10((xi+gb)/xi)
        if loss < 3: bad = f; break
    print('  输入 SNR=%+3d dB → 低于 %.0f Hz 时 Zelinski 少压超过 3 dB' % (xi_db, bad))

print('\n══ 4. 音乐噪声：增益估计的方差 ══')
print('   用 K 帧平均估计功率谱时，增益的标准差（真值 G=0.5）')
for K in [1, 2, 4, 8, 16, 32]:
    N = 40000
    xi = 1.0
    # 每帧：|S|², |N|² 都是指数分布（瑞利幅度），K 帧平均 → Erlang/K
    ps = rng.gamma(K, xi/K, N); pn = rng.gamma(K, 1.0/K, N)
    Gh = np.clip(ps/(ps+pn), 0, 1)
    print('   K=%2d  均值 %.3f  标准差 %.3f  低于 0.1 的比例 %.1f%%  高于 0.9 的比例 %.1f%%'
          % (K, Gh.mean(), Gh.std(), 100*(Gh<0.1).mean(), 100*(Gh>0.9).mean()))

print('\n══ 5. 增益下限与平滑的效果（纯噪声输入，真值应为 0）══')
N = 60000; K = 4
pn1 = rng.gamma(K, 1.0/K, N); pn2 = rng.gamma(K, 1.0/K, N)
# 纯噪声时，"估计的目标功率"是两次独立估计之差的正部（典型做法）
raw = np.clip((pn1-pn2)/pn1, 0, 1)
def smooth(x, a):
    y = np.empty_like(x); acc = x[0]
    for i, v in enumerate(x):
        acc = a*acc+(1-a)*v; y[i] = acc
    return y
for name, g in [('无处理', raw), ('时间平滑 α=0.7', smooth(raw,0.7)),
                ('平滑 + 地板 −12 dB', np.maximum(smooth(raw,0.7), 10**(-12/20)))]:
    db = 20*np.log10(np.maximum(g,1e-6))
    print('   %-20s 增益 dB：中位 %6.2f  标准差 %5.2f  峰谷差 %5.1f dB'
          % (name, np.median(db), db.std(), np.percentile(db,99)-np.percentile(db,1)))
