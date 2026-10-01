#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""07 节算例：AAM-softmax 的 margin 到底在干什么。

   真训一个小网络（纯 numpy，手写反传）：
   输入 40 维"特征"，编码成 16 维嵌入，用余弦分类头 + 三种损失训练，
   然后在<strong>训练时没见过的说话人</strong>上测 EER。
   同时量两件事：类内角度散布、以及类内协方差的各向异性——
   后者正好解释了 08 节那个"余弦什么时候能追上 PLDA"。
"""
import numpy as np, json, math

rng = np.random.default_rng(0)
OUT = {}
DIN, H, E = 40, 64, 16
NSPK_TR, NSPK_TE, NUTT = 300, 200, 40
LAT = 10                                   # 真实说话人因子的维数
S, MARGIN = 30.0, 0.20


def make_world(seed=1):
    g = np.random.default_rng(seed)
    A = g.standard_normal((LAT, DIN)) / math.sqrt(LAT)      # 因子 → 特征
    Cn = g.standard_normal((DIN, DIN)) / math.sqrt(DIN)     # 会话内扰动的形状
    Cn = Cn @ Cn.T + 0.15 * np.eye(DIN)
    Ln = np.linalg.cholesky(Cn)
    return A, Ln


A, Ln = make_world()


def sample(nspk, nutt, seed):
    g = np.random.default_rng(seed)
    y = g.standard_normal((nspk, LAT))
    x = y @ A
    x = x[:, None, :] + (g.standard_normal((nspk, nutt, DIN)) @ Ln.T) * 0.85
    lab = np.repeat(np.arange(nspk), nutt)
    return x.reshape(-1, DIN), lab


Xtr, ytr = sample(NSPK_TR, NUTT, 11)
Xte, yte = sample(NSPK_TE, 8, 22)
mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-8
Xtr = (Xtr - mu) / sd
Xte = (Xte - mu) / sd
OUT['setup'] = {'din': DIN, 'hid': H, 'emb': E, 'latent': LAT,
                'spk_tr': NSPK_TR, 'spk_te': NSPK_TE, 'utt_tr': NUTT,
                's': S, 'm': MARGIN}
print('输入 %d 维 → 隐层 %d → 嵌入 %d；训练 %d 人 × %d 条，测试 %d 人（没见过）'
      % (DIN, H, E, NSPK_TR, NUTT, NSPK_TE))


def lnorm(v, eps=1e-9):
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + eps)


def train(kind, steps=4000, bs=256, lr=3e-3, seed=7):
    g = np.random.default_rng(seed)
    P = {'W1': g.standard_normal((DIN, H)) / math.sqrt(DIN), 'b1': np.zeros(H),
         'W2': g.standard_normal((H, E)) / math.sqrt(H), 'b2': np.zeros(E),
         'Wc': g.standard_normal((NSPK_TR, E)) / math.sqrt(E)}
    M = {k: np.zeros_like(v) for k, v in P.items()}
    Vv = {k: np.zeros_like(v) for k, v in P.items()}
    for it in range(steps):
        i = g.integers(0, len(Xtr), bs)
        x, t = Xtr[i], ytr[i]
        # ── 前向 ──
        a = x @ P['W1'] + P['b1']
        h = np.maximum(a, 0)
        z = h @ P['W2'] + P['b2']
        if kind == 'linear':                      # 对照：普通线性分类头，不归一化
            nz = np.ones((bs, 1)); e = z
            nc = np.ones((NSPK_TR, 1)); c = P['Wc']
            cos = e @ c.T
            logit = cos
        else:
            nz = np.linalg.norm(z, axis=1, keepdims=True) + 1e-9
            e = z / nz
            nc = np.linalg.norm(P['Wc'], axis=1, keepdims=True) + 1e-9
            c = P['Wc'] / nc
            cos = np.clip(e @ c.T, -1 + 1e-7, 1 - 1e-7)
            logit = S * cos
        oh = np.zeros_like(cos); oh[np.arange(bs), t] = 1.0
        ct = cos[np.arange(bs), t]
        if kind == 'am':
            logit[np.arange(bs), t] = S * (ct - MARGIN)
        elif kind == 'aam':
            th = np.arccos(ct)
            logit[np.arange(bs), t] = S * np.cos(th + MARGIN)
        # ── 反传 ──
        p = np.exp(logit - logit.max(1, keepdims=True))
        p /= p.sum(1, keepdims=True)
        dlogit = (p - oh) / bs
        dcos = (np.ones_like(cos) if kind == 'linear' else S * np.ones_like(cos))
        if kind == 'aam':
            th = np.arccos(ct)
            dcos[np.arange(bs), t] = S * np.sin(th + MARGIN) / np.maximum(np.sin(th), 1e-6)
        dcos = dlogit * dcos
        de = dcos @ c
        dc = dcos.T @ e
        if kind == 'linear':
            dWc = dc
            dz = de
        else:
            dWc = (dc - (np.sum(dc * c, 1, keepdims=True)) * c) / nc
            dz = (de - np.sum(de * e, 1, keepdims=True) * e) / nz
        dW2 = h.T @ dz; db2 = dz.sum(0)
        dh = dz @ P['W2'].T
        da = dh * (a > 0)
        dW1 = x.T @ da; db1 = da.sum(0)
        G = {'W1': dW1, 'b1': db1, 'W2': dW2, 'b2': db2, 'Wc': dWc}
        for k in P:                                    # Adam
            M[k] = 0.9 * M[k] + 0.1 * G[k]
            Vv[k] = 0.999 * Vv[k] + 0.001 * G[k] ** 2
            mh = M[k] / (1 - 0.9 ** (it + 1))
            vh = Vv[k] / (1 - 0.999 ** (it + 1))
            P[k] -= lr * mh / (np.sqrt(vh) + 1e-8)
    return P


def embed(P, X):
    h = np.maximum(X @ P['W1'] + P['b1'], 0)
    return lnorm(h @ P['W2'] + P['b2'])


def eer_of(t, n):
    s = np.r_[t, n]
    y = np.r_[np.ones(len(t)), np.zeros(len(n))]
    o = np.argsort(s); s, y = s[o], y[o]
    miss = np.cumsum(y) / len(t)
    fa = 1 - np.cumsum(1 - y) / len(n)
    i = np.argmin(np.abs(miss - fa))
    return float((miss[i] + fa[i]) / 2)


g = np.random.default_rng(5)
idx = {s_: np.where(yte == s_)[0] for s_ in range(NSPK_TE)}
TA = np.array([tuple(g.choice(idx[s_], 2, replace=False))
               for s_ in range(NSPK_TE) for _ in range(60)])
NO = []
for _ in range(60000):
    a_, b_ = g.choice(NSPK_TE, 2, replace=False)
    NO.append((idx[a_][g.integers(8)], idx[b_][g.integers(8)]))
NO = np.array(NO)

print('\n  损失                        余弦 EER  PLDA EER  余弦/PLDA  类内角σ  类内各向异性')
OUT['losses'] = []
for kind, tag in (('linear', '普通线性 softmax（对照）'),
                  ('plain', '余弦 softmax（无 margin）'),
                  ('am', 'AM-softmax（m=%.2f）' % MARGIN),
                  ('aam', 'AAM-softmax（m=%.2f）' % MARGIN)):
    P = train(kind)
    Ete = embed(P, Xte)
    e_ = eer_of(np.sum(Ete[TA[:, 0]] * Ete[TA[:, 1]], 1),
                np.sum(Ete[NO[:, 0]] * Ete[NO[:, 1]], 1))
    # 类内角度散布（对测试说话人）
    ang, Wcov = [], np.zeros((E, E))
    for s_ in range(NSPK_TE):
        Z = Ete[idx[s_]]
        m_ = lnorm(Z.mean(0))
        ang.append(np.degrees(np.arccos(np.clip(Z @ m_, -1, 1))))
        Zc = Z - Z.mean(0)
        Wcov += Zc.T @ Zc
    ang = np.concatenate(ang)
    Wcov /= len(Ete)
    ev = np.linalg.eigvalsh(Wcov)[::-1]
    aniso = float(ev[0] / max(ev[LAT - 1], 1e-12))
    cen = np.array([lnorm(Ete[idx[s_]].mean(0)) for s_ in range(NSPK_TE)])
    cc = cen @ cen.T
    np.fill_diagonal(cc, -1)
    inter = float(np.degrees(np.arccos(np.clip(cc.max(1), -1, 1))).mean())
    # 在这套<strong>学出来的</strong>嵌入上，PLDA 还能比余弦多拿多少？
    Etr = embed(P, Xtr)
    mus = np.array([Etr[ytr == s2].mean(0) for s2 in range(NSPK_TR)])
    Bm = np.cov(mus.T, bias=True)
    Zc = np.concatenate([Etr[ytr == s2] - mus[s2] for s2 in range(NSPK_TR)])
    Wm = Zc.T @ Zc / len(Zc) + 1e-6 * np.eye(E)
    from svlib import plda_llr as _pl
    ep_ = eer_of(_pl(Ete[TA[:, 0]], Ete[TA[:, 1]], Bm, Wm),
                 _pl(Ete[NO[:, 0]], Ete[NO[:, 1]], Bm, Wm))
    r = {'tag': tag, 'eer': round(e_ * 100, 2), 'intra_sd': round(float(ang.std()), 2),
         'inter_deg': round(inter, 1), 'aniso': round(aniso, 2),
         'plda': round(ep_ * 100, 2), 'gap': round(e_ / max(ep_, 1e-9), 2)}
    OUT['losses'].append(r)
    print('  %-26s %6.2f%%  %6.2f%%   %5.2f×   %5.2f°   %5.2f:1'
          % (tag, r['eer'], r['plda'], r['gap'], r['intra_sd'], r['aniso']))
print('  （各向异性 = 类内协方差前 %d 个特征值里最大与最小之比）' % LAT)
best = min(OUT['losses'], key=lambda r: r['eer'])
base = OUT['losses'][1]
OUT['gain'] = round((1 - best['eer'] / base['eer']) * 100, 1)
print('\n  margin 把余弦 EER 从 %.2f%% 降到 %.2f%%（降 %.0f%%）。'
      % (base['eer'], best['eer'], OUT['gain']))
print('  而"余弦/PLDA"那一列是我原本想验证的假说：'
      'margin 是不是让嵌入变得更各向同性、从而让余弦追上 PLDA。')
print('  实测：')
for r in OUT['losses']:
    print('    %-26s 余弦/PLDA = %.2f×' % (r['tag'], r['gap']))
print('  假说<strong>没被支持</strong>：加不加 margin，这个比值都在 1.1 附近。')
print('  但对照行给出了更好的解释——见正文。')

# ══ margin 取多大 ════════════════════════════════════════════
print('\n  margin 取多大：太小没用，太大训不动')
OUT['msweep'] = []
for m in (0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5):
    MARGIN = m
    P = train('aam', steps=3000)
    Ete = embed(P, Xte)
    e_ = eer_of(np.sum(Ete[TA[:, 0]] * Ete[TA[:, 1]], 1),
                np.sum(Ete[NO[:, 0]] * Ete[NO[:, 1]], 1))
    OUT['msweep'].append({'m': m, 'eer': round(e_ * 100, 2)})
    print('    m = %.2f   EER %6.2f%%' % (m, e_ * 100))

json.dump(OUT, open('demo_margin.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_margin.json')
