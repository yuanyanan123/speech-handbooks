#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""10 / 09 节算例：时长、注册条数、分数归一化、信道失配，各值多少 EER。"""
import numpy as np, json, math
from svlib import (D, make_cov, gen, lnorm, lda_fit, plda_llr, eer, dcf,
                   dur_scale, as_norm)

OUT = {}
B = make_cov(seed=1, aniso=5.0)
W = make_cov(seed=2, aniso=8.0) * 1.6
Xtr, ltr, _ = gen(400, 8, B, W, seed=10)
V = lda_fit(Xtr, ltr, k=D)
NSPK, NUTT = 500, 4


def cos_v(a, b):
    return np.sum(lnorm(a @ V) * lnorm(b @ V), -1)


def make_trials(lab, seed=7, n_tar=20000, n_non=200000):
    g = np.random.default_rng(seed)
    idx = {s: np.where(lab == s)[0] for s in np.unique(lab)}
    spk = list(idx)
    ta = np.array([(lambda s: tuple(g.choice(idx[s], 2, replace=False)))(
        spk[g.integers(len(spk))]) for _ in range(n_tar)])
    no = []
    for _ in range(n_non):
        s1, s2 = g.choice(len(spk), 2, replace=False)
        no.append((idx[spk[s1]][g.integers(NUTT)], idx[spk[s2]][g.integers(NUTT)]))
    return ta, np.array(no)


# ══ ① 时长 ═══════════════════════════════════════════════════
print('① 测试语音时长（类内协方差按 %.2f + %.2f·(3/T) 放大）' % (0.35, 0.65))
print('  时长      类内放大   余弦 EER   PLDA EER')
OUT['dur'] = []
for T in (1.0, 2.0, 3.0, 5.0, 10.0, 30.0):
    sc = dur_scale(T)
    Wt = W * sc
    X, lab, _ = gen(NSPK, NUTT, B, Wt, seed=20)
    ta, no = make_trials(lab)
    ec, _ = eer(cos_v(X[ta[:, 0]], X[ta[:, 1]]), cos_v(X[no[:, 0]], X[no[:, 1]]))
    ep, _ = eer(plda_llr(X[ta[:, 0]], X[ta[:, 1]], B, Wt),
                plda_llr(X[no[:, 0]], X[no[:, 1]], B, Wt))
    OUT['dur'].append({'T': T, 'scale': round(sc, 3), 'cos': round(ec * 100, 2),
                       'plda': round(ep * 100, 2)})
    print('  %5.1f s    %5.2f×    %6.2f%%   %6.2f%%' % (T, sc, ec * 100, ep * 100))
d1 = next(r for r in OUT['dur'] if r['T'] == 1.0)
d10 = next(r for r in OUT['dur'] if r['T'] == 10.0)
OUT['dur_ratio'] = round(d1['plda'] / d10['plda'], 2)
print('  1 秒对 10 秒：EER 差 %.1f 倍。<strong>短时长是声纹落地的头号问题</strong>，'
      % OUT['dur_ratio'])
print('  而且它不是模型不行——是那几百帧统计量本身就不够。')

# ══ ② 注册条数 ═══════════════════════════════════════════════
print('\n② 注册用几条：多条取平均，把注册端的扰动除掉')
print('  注册条数   注册端等效放大   余弦 EER   PLDA EER')
OUT['enroll'] = []
X, lab, _ = gen(NSPK, 12, B, W, seed=30)
g = np.random.default_rng(3)
for N in (1, 2, 3, 5, 8):
    en, te_t, te_n = [], [], []
    idx = {s: np.where(lab == s)[0] for s in range(NSPK)}
    E = np.array([X[idx[s][:N]].mean(0) for s in range(NSPK)])
    Te = np.array([X[idx[s][8 + (s % 4)]] for s in range(NSPK)])
    t = cos_v(E, Te)
    pairs = [(i, (i + 1 + g.integers(NSPK - 1)) % NSPK) for i in range(NSPK)
             for _ in range(40)]
    pi = np.array([p[0] for p in pairs]); pj = np.array([p[1] for p in pairs])
    n = cos_v(E[pi], Te[pj])
    ec, _ = eer(t, n)
    Wn = W / N + W * 0            # 注册端方差降为 W/N
    pt = plda_llr(E, Te, B, W)    # 注意：模型里没告诉 PLDA 注册端方差变小了
    pn = plda_llr(E[pi], Te[pj], B, W)
    ep, _ = eer(pt, pn)
    OUT['enroll'].append({'n': N, 'scale': round(1.0 / N, 3),
                          'cos': round(ec * 100, 2), 'plda': round(ep * 100, 2)})
    print('  %6d     %8.2f×      %6.2f%%   %6.2f%%' % (N, 1.0 / N, ec * 100, ep * 100))
e1 = OUT['enroll'][0]['cos']; e5 = OUT['enroll'][3]['cos']
print('  1 → 5 条，EER 从 %.2f%% 降到 %.2f%%（降 %.0f%%）；再往上收益很小。'
      % (e1, e5, (1 - e5 / e1) * 100))
print('  <strong>注册端是免费的那一侧</strong>——用户只注册一次，'
      '而测试端每次都要面对短语音。')

# ══ ③ 分数归一化 ═════════════════════════════════════════════
print('\n③ AS-norm：为什么"有的人天生容易被冒充"')
X, lab, _ = gen(NSPK, NUTT, B, W, seed=20)
ta, no = make_trials(lab)
coh, clab, _ = gen(300, 2, B, W, seed=99)        # 冒充队列，与测试说话人无关
Ec = lnorm(coh @ V)


def cohort_scores(x):
    return lnorm(x @ V) @ Ec.T


t_raw = cos_v(X[ta[:, 0]], X[ta[:, 1]])
n_raw = cos_v(X[no[:, 0]], X[no[:, 1]])
e_raw, _ = eer(t_raw, n_raw)
t_as = as_norm(t_raw, cohort_scores(X[ta[:, 0]]), cohort_scores(X[ta[:, 1]]), k=200)
n_as = as_norm(n_raw, cohort_scores(X[no[:, 0]]), cohort_scores(X[no[:, 1]]), k=200)
e_as, _ = eer(t_as, n_as)
# 每个说话人自己的冒充分均值，看它散不散
spk_bias = np.array([n_raw[np.isin(no[:, 0], np.where(lab == s)[0])].mean()
                     for s in range(0, NSPK, 5)])
OUT['asnorm'] = {'eer_raw': round(e_raw * 100, 2), 'eer_as': round(e_as * 100, 2),
                 'gain_pct': round((1 - e_as / e_raw) * 100, 1),
                 'bias_sd': round(float(np.nanstd(spk_bias)), 4),
                 'bias_lo': round(float(np.nanmin(spk_bias)), 3),
                 'bias_hi': round(float(np.nanmax(spk_bias)), 3)}
print('  各说话人自己的冒充分均值，标准差 %.4f，范围 [%.3f, %.3f]'
      % (OUT['asnorm']['bias_sd'], OUT['asnorm']['bias_lo'], OUT['asnorm']['bias_hi']))
print('  同一个全局阈值对这些人是不公平的 —— 这就是 AS-norm 要修的东西')
print('  原始余弦 EER %.2f%%  →  AS-norm 后 %.2f%%（降 %.0f%%）'
      % (e_raw * 100, e_as * 100, OUT['asnorm']['gain_pct']))

# ══ ④ 信道 / 域失配 ══════════════════════════════════════════
print('\n④ 注册和测试来自不同信道')
OUT['domain'] = []
gg = np.random.default_rng(11)
for shift in (0.0, 0.3, 0.6, 1.0, 1.5):
    dvec = gg.standard_normal(D)
    dvec = dvec / np.linalg.norm(dvec) * shift * math.sqrt(np.trace(W))
    Xa = X.copy()
    Xb = X + dvec                                 # 测试侧整体挪一个信道向量
    t = cos_v(Xa[ta[:, 0]], Xb[ta[:, 1]])
    n = cos_v(Xa[no[:, 0]], Xb[no[:, 1]])
    e0, _ = eer(t, n)
    # 最简单的域适应：各域各自减去自己的均值
    Xa2 = Xa - Xa.mean(0); Xb2 = Xb - Xb.mean(0)
    t2 = cos_v(Xa2[ta[:, 0]], Xb2[ta[:, 1]])
    n2 = cos_v(Xa2[no[:, 0]], Xb2[no[:, 1]])
    e1_, _ = eer(t2, n2)
    OUT['domain'].append({'shift': shift, 'eer': round(e0 * 100, 2),
                          'eer_cmn': round(e1_ * 100, 2)})
    print('  信道偏移 %.1f·√tr(W)   EER %6.2f%%   各域去均值后 %6.2f%%'
          % (shift, e0 * 100, e1_ * 100))
print('  <strong>一个常数偏移就能把 EER 翻几倍，而减掉各域均值几乎全能救回来</strong>——')
print('  这就是"域适应"这件事最朴素、也最有效的那一版。')

json.dump(OUT, open('demo_cond.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_cond.json')
