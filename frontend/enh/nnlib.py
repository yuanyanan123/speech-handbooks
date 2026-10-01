#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""demo_nn.py 里那套因果小网络的可复用部分。

   从 demo_nn.py 原样抽出来，供 demo_out.py / demo_gen.py / demo_tier.py 共用，
   保证三组实验用的是同一套特征、同一套初始化、同一套优化器。
"""
import numpy as np, time
import enhlib as E
NFFT, HOP = 512, 256
NBIN = NFFT // 2 + 1
NB = 32                      # 频带数
CTX = 6                      # 因果上下文帧数（含当前帧）
SNRS = (-5.0, 0.0, 5.0, 10.0, 15.0)
TRAIN_NOISE = ('white', 'pink', 'car')
UNSEEN_NOISE = 'babble'
def bands(nbin=NBIN, nb=NB, sr=E.SR):
    f = np.linspace(0, sr / 2, nbin)
    mel = lambda x: 2595 * np.log10(1 + x / 700)
    imel = lambda x: 700 * (10 ** (x / 2595) - 1)
    e = imel(np.linspace(mel(50), mel(sr / 2 - 100), nb + 2))
    W = np.zeros((nb, nbin))
    for b in range(nb):
        lo, c, hi = e[b], e[b + 1], e[b + 2]
        up = (f >= lo) & (f <= c)
        dn = (f > c) & (f <= hi)
        W[b, up] = (f[up] - lo) / max(c - lo, 1e-9)
        W[b, dn] = (hi - f[dn]) / max(hi - c, 1e-9)
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    Wt = W.T / np.maximum(W.sum(0)[:, None], 1e-9)      # 频带 → 频点（能量守恒的展开）
    return W, Wt

WB, WT = bands()
def make_pair(seed, kind, snr):
    x, segs = E.make_speech(dur=3.0, seed=seed)
    m = E.speech_mask(segs, len(x))
    v = E.make_noise(kind, len(x), seed=seed * 7 + 11)
    y, vv = E.mix_at_snr(x, v, snr, m)
    n = len(y)
    S = E.stft(x[:n], NFFT, HOP)
    V = E.stft(vv[:n], NFFT, HOP)
    Y = E.stft(y, NFFT, HOP)
    return x[:n], y, m[:n], S, V, Y
def featurize(Y):
    """因果特征：频带对数能量 + 其一阶差分，再做因果的均值方差归一化"""
    P = np.maximum((np.abs(Y) ** 2) @ WB.T, 1e-10)
    L = 10 * np.log10(P)
    mu = np.zeros_like(L); sd = np.zeros_like(L)
    a, m_, s_ = 0.98, L[0].copy(), np.ones(NB) * 10.0
    for l in range(len(L)):
        m_ = a * m_ + (1 - a) * L[l]
        s_ = a * s_ + (1 - a) * np.abs(L[l] - m_)
        mu[l], sd[l] = m_, np.maximum(s_, 1.0)
    Z = (L - mu) / sd
    D = np.vstack([np.zeros((1, NB)), np.diff(Z, axis=0)])
    F = np.concatenate([Z, D], 1)                                  # (帧, 2·NB)
    ctx = [np.vstack([np.repeat(F[:1], k, 0), F[:len(F) - k]]) for k in range(CTX)]
    return np.concatenate(ctx, 1).astype(np.float64)               # (帧, CTX·2·NB)
DIN = CTX * 2 * NB
def init(din, h1, h2, dout, seed=0):
    g = np.random.default_rng(seed)
    return {'W1': g.standard_normal((din, h1)) / np.sqrt(din), 'b1': np.zeros(h1),
            'W2': g.standard_normal((h1, h2)) / np.sqrt(h1), 'b2': np.zeros(h2),
            'W3': g.standard_normal((h2, dout)) / np.sqrt(h2), 'b3': np.zeros(dout)}


def fwd(P, X):
    a1 = X @ P['W1'] + P['b1']; h1 = np.maximum(a1, 0)
    a2 = h1 @ P['W2'] + P['b2']; h2 = np.maximum(a2, 0)
    o = h2 @ P['W3'] + P['b3']
    return a1, h1, a2, h2, o


def bwd(P, X, a1, h1, a2, h2, do):
    G = {}
    G['W3'] = h2.T @ do; G['b3'] = do.sum(0)
    d2 = (do @ P['W3'].T) * (a2 > 0)
    G['W2'] = h1.T @ d2; G['b2'] = d2.sum(0)
    d1 = (d2 @ P['W2'].T) * (a1 > 0)
    G['W1'] = X.T @ d1; G['b1'] = d1.sum(0)
    return G


def train(Xtr, dout, lossfn, steps=3000, bs=128, lr=2e-3, h=(128, 96), seed=0, tag='',
          out_zero=False):
    P = init(Xtr.shape[1], h[0], h[1], dout, seed)
    if out_zero:                 # 输出层零初始化：让各种输出参数化都从"全零输出"起步，
        P['W3'][:] = 0.0         # 否则 tanh 这类带尺度的参数化一开始就在饱和区，
        P['b3'][:] = 0.0         # 比的就成了初始化而不是参数化
    M = {k: np.zeros_like(v) for k, v in P.items()}
    Vv = {k: np.zeros_like(v) for k, v in P.items()}
    g = np.random.default_rng(seed + 5)
    hist = []
    for it in range(steps):
        i = g.integers(0, len(Xtr), bs)
        X = Xtr[i]
        a1, h1, a2, h2, o = fwd(P, X)
        L, do = lossfn(o, i)
        G = bwd(P, X, a1, h1, a2, h2, do / bs)
        for k in P:
            M[k] = 0.9 * M[k] + 0.1 * G[k]
            Vv[k] = 0.999 * Vv[k] + 0.001 * G[k] ** 2
            P[k] -= lr * (M[k] / (1 - 0.9 ** (it + 1))) / \
                (np.sqrt(Vv[k] / (1 - 0.999 ** (it + 1))) + 1e-8)
        if it % 500 == 0 or it == steps - 1:
            hist.append(round(float(L), 4))
    nparam = sum(v.size for v in P.values())
    print('    %-22s 参数 %6d  损失 %s' % (tag, nparam, ' → '.join(map(str, hist[:1] + hist[-1:]))))
    return P, nparam

sig = lambda z: 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
