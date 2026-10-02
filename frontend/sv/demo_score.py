#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""08 节算例：四种打分各值多少；以及 LDA / 长度归一化各自买到了什么。"""
import numpy as np, json, math
from svlib import (D, make_cov, gen, lnorm, cosine, lda_fit, plda_llr,
                   eer, dcf, bayes_thr, cllr, det_curve)

OUT = {}
B = make_cov(seed=1, aniso=5.0)                 # 类间
W = make_cov(seed=2, aniso=8.0)                 # 类内，更各向异性
W *= 1.6                                        # 让任务有点难度
OUT['model'] = {'d': D,
                'tr_B': round(float(np.trace(B)), 3),
                'tr_W': round(float(np.trace(W)), 3),
                'cond_B': round(float(np.linalg.cond(B)), 1),
                'cond_W': round(float(np.linalg.cond(W)), 1)}
print('嵌入维数 %d；类间协方差 tr=%.2f cond=%.1f，类内 tr=%.2f cond=%.1f'
      % (D, np.trace(B), np.linalg.cond(B), np.trace(W), np.linalg.cond(W)))
print('（类内比类间还大一点，而且更各向异性——真实声纹就是这个样子）')

# ══ 训练集（估 LDA / PLDA 用）与测试集（另一批说话人） ══════════
Xtr, ltr, _ = gen(400, 8, B, W, seed=10)
Xte, lte, _ = gen(500, 4, B, W, seed=20)
OUT['data'] = {'tr_spk': 400, 'tr_utt': 8, 'te_spk': 500, 'te_utt': 4}


def trials(X, lab, seed=0, n_tar=20000, n_non=200000):
    """造试验对：同人 = 目标，不同人 = 冒充。测试集的说话人训练时没见过。"""
    g = np.random.default_rng(seed)
    idx = {s: np.where(lab == s)[0] for s in np.unique(lab)}
    spk = list(idx)
    ta = []
    while len(ta) < n_tar:
        s = spk[g.integers(len(spk))]
        i, j = g.choice(idx[s], 2, replace=False)
        ta.append((i, j))
    no = []
    while len(no) < n_non:
        s1, s2 = g.choice(len(spk), 2, replace=False)
        no.append((idx[spk[s1]][g.integers(len(idx[spk[s1]]))],
                   idx[spk[s2]][g.integers(len(idx[spk[s2]]))]))
    return np.array(ta), np.array(no)


ta, no = trials(Xte, lte, seed=7)
OUT['trials'] = {'tar': len(ta), 'non': len(no)}
print('\n试验：%d 个目标对，%d 个冒充对（测试说话人训练时没见过）' % (len(ta), len(no)))

V = lda_fit(Xtr, ltr, k=D)                       # 类内白化 + 类间排序


def run(tag, f):
    t = f(Xte[ta[:, 0]], Xte[ta[:, 1]])
    n = f(Xte[no[:, 0]], Xte[no[:, 1]])
    e, th = eer(t, n)
    m1, _ = dcf(t, n, p_tar=0.01)
    m2, _ = dcf(t, n, p_tar=0.001)
    return {'tag': tag, 'eer': round(e * 100, 2), 'mindcf01': round(m1, 4),
            'mindcf001': round(m2, 4), 'thr': round(th, 4)}, t, n


METH = [
    ('原始余弦', lambda a, b: cosine(a, b)),
    ('长度归一化后余弦', lambda a, b: np.sum(lnorm(a) * lnorm(b), -1)),
    ('LDA → 余弦', lambda a, b: cosine(a @ V, b @ V)),
    ('LDA → 长度归一化 → 余弦', lambda a, b: np.sum(lnorm(a @ V) * lnorm(b @ V), -1)),
    ('PLDA 对数似然比', lambda a, b: plda_llr(a, b, B, W)),
]
OUT['methods'] = []
SC = {}
print('\n  打分方式                      EER      minDCF(0.01)  minDCF(0.001)')
for tag, f in METH:
    r, t, n = run(tag, f)
    OUT['methods'].append(r)
    SC[tag] = (t, n)
    print('  %-26s %6.2f%%   %8.4f      %8.4f' % (tag, r['eer'], r['mindcf01'], r['mindcf001']))
print('  <- 前两行几乎一样：原始余弦本来就只看方向，长度归一化没改变夹角')
print('     LDA 那一步才是真正有用的：它把类内协方差白化掉了')

# ══ 白化到底贡献了多少：拆成两步 ═══════════════════════════════
Wi = np.linalg.inv(np.linalg.cholesky(W))        # 类内白化
r_w, _, _ = run('仅类内白化 → 余弦', lambda a, b: cosine(a @ Wi.T, b @ Wi.T))
OUT['methods'].insert(2, r_w)
print('\n  拆开看：仅做类内白化（不做 LDA 降维排序）EER %.2f%%' % r_w['eer'])
print('  说明 LDA 的好处几乎全来自<strong>白化</strong>，不是降维')

# ══ PLDA 什么时候才明显赢过余弦 ═══════════════════════════════
# 关键在"类内协方差白化之后，类间还剩多少各向异性"。
print('\n余弦和 PLDA 的差距，取决于类内协方差有多各向异性：')
OUT['aniso'] = []
for an in (1.0, 1.5, 2.5, 4.0, 8.0):
    W2 = make_cov(seed=2, aniso=an) * 1.6
    Xtr2, ltr2, _ = gen(400, 8, B, W2, seed=10)
    Xte2, lte2, _ = gen(500, 4, B, W2, seed=20)
    V2 = lda_fit(Xtr2, ltr2, k=D)
    c = np.sum(lnorm(Xte2[ta[:, 0]] @ V2) * lnorm(Xte2[ta[:, 1]] @ V2), -1)
    cn = np.sum(lnorm(Xte2[no[:, 0]] @ V2) * lnorm(Xte2[no[:, 1]] @ V2), -1)
    pt = plda_llr(Xte2[ta[:, 0]], Xte2[ta[:, 1]], B, W2)
    pn = plda_llr(Xte2[no[:, 0]], Xte2[no[:, 1]], B, W2)
    ec, _ = eer(c, cn); ep, _ = eer(pt, pn)
    OUT['aniso'].append({'aniso': an, 'cos': round(ec * 100, 2), 'plda': round(ep * 100, 2),
                         'ratio': round(ec / max(ep, 1e-9), 2)})
    print('  类内特征值动态 %4.1f:1   余弦 %5.2f%%   PLDA %5.2f%%   差 %.1f 倍'
          % (an, ec * 100, ep * 100, ec / max(ep, 1e-9)))
print('  <strong>类内越接近各向同性，两者越接近</strong>——')
print('  而 AAM-softmax 训出来的嵌入恰好就是近各向同性的（07 节），')
print('  这才是工业界从 PLDA 退回余弦的真正原因。')

json.dump(OUT, open('demo_score.json', 'w'), ensure_ascii=False, indent=1)
np.save('sc_tar.npy', SC['PLDA 对数似然比'][0])
np.save('sc_non.npy', SC['PLDA 对数似然比'][1])
np.save('sc_cos_tar.npy', SC['LDA → 长度归一化 → 余弦'][0])
np.save('sc_cos_non.npy', SC['LDA → 长度归一化 → 余弦'][1])
print('\n→ demo_score.json')
