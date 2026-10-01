#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""声纹侧的共用件：双协方差嵌入模型、四种打分、以及 EER / DCF / 校准的算法。

   为什么不用真语料：这本手册里每个数都要能复算。真的说话人嵌入既不能随书分发，
   也没有"真实的类内/类间协方差"这种真值。这里直接<strong>规定</strong>一个
   双协方差模型——类间 B、类内 W 都是已知的——于是"PLDA 比余弦好多少"、
   "时长缩一半 EER 涨多少"才有客观答案，而且能和闭式推导对照。
"""
import numpy as np

D = 32                      # 嵌入维数（真实系统 192–512，这里取 32 好算也好画）


# ══════════════════════════════════════════════════════════════
# 一、嵌入的生成模型：x = y + ε，y~N(0,B) 说话人因子，ε~N(0,W) 会话内扰动
# ══════════════════════════════════════════════════════════════
def make_cov(d=D, seed=0, aniso=6.0, rank=None):
    """造一个各向异性的协方差：特征值按几何级数铺开，特征向量随机正交。"""
    g = np.random.default_rng(seed)
    Q, _ = np.linalg.qr(g.standard_normal((d, d)))
    k = rank or d
    lam = np.r_[np.geomspace(aniso, 1.0 / aniso, k), np.full(d - k, 1e-3)]
    lam = lam / lam.mean()
    return Q @ np.diag(lam) @ Q.T


def gen(nspk, nutt, B, W, seed=0, dur=None, mu=None):
    """返回 (X, lab)。dur 给定时，类内协方差按 W0 + Wn/T 变大（时长越短越抖）。"""
    g = np.random.default_rng(seed)
    d = B.shape[0]
    Ly = np.linalg.cholesky(B + 1e-9 * np.eye(d))
    y = g.standard_normal((nspk, d)) @ Ly.T
    if mu is not None:
        y = y + mu
    Wt = W if dur is None else W * dur_scale(dur)
    Lw = np.linalg.cholesky(Wt + 1e-9 * np.eye(d))
    e = g.standard_normal((nspk, nutt, d)) @ Lw.T
    X = y[:, None, :] + e
    lab = np.repeat(np.arange(nspk), nutt)
    return X.reshape(-1, d), lab, y


def dur_scale(T, T0=3.0, floor=0.35):
    """时长 T 秒时类内协方差的放大倍数。
       会话内扰动分两部分：和时长无关的（信道、状态）+ 统计估计噪声 ∝ 1/T。"""
    return floor + (1.0 - floor) * (T0 / T)


# ══════════════════════════════════════════════════════════════
# 二、四种打分
# ══════════════════════════════════════════════════════════════
def lnorm(X):
    return X / (np.linalg.norm(X, axis=-1, keepdims=True) + 1e-12)


def cosine(a, b):
    return np.sum(lnorm(a) * lnorm(b), -1)


def lda_fit(X, lab, k=None):
    """类内白化 + 类间主方向。返回投影矩阵 (d,k)。"""
    d = X.shape[1]
    k = k or d
    mus = np.array([X[lab == s].mean(0) for s in np.unique(lab)])
    Sw = np.zeros((d, d))
    for i, s in enumerate(np.unique(lab)):
        Z = X[lab == s] - mus[i]
        Sw += Z.T @ Z
    Sw /= len(X)
    Sb = np.cov(mus.T, bias=True)
    from scipy.linalg import eigh as geigh          # 广义对称特征问题 Sb v = λ Sw v
    ev, V = geigh(Sb, Sw + 1e-6 * np.eye(d))
    return V[:, np.argsort(-ev)[:k]]                # 列向量对 Sw 正交 = 顺带白化


def plda_llr(a, b, B, W):
    """双协方差 PLDA 的对数似然比，直接用分块高斯算，无近似。"""
    d = B.shape[0]
    T = B + W
    S_same = np.block([[T, B], [B, T]])
    S_diff = np.block([[T, np.zeros((d, d))], [np.zeros((d, d)), T]])
    Ps, Pd = np.linalg.inv(S_same), np.linalg.inv(S_diff)
    _, lds = np.linalg.slogdet(S_same)
    _, ldd = np.linalg.slogdet(S_diff)
    z = np.concatenate([a, b], -1)
    q = lambda P: np.einsum('...i,ij,...j->...', z, P, z)
    return -0.5 * (q(Ps) - q(Pd)) - 0.5 * (lds - ldd)


# ══════════════════════════════════════════════════════════════
# 三、指标：EER、DCF、校准
# ══════════════════════════════════════════════════════════════
def det_curve(tar, non):
    """返回 (阈值, 漏检率 Pmiss, 虚警率 Pfa)，按阈值升序。"""
    s = np.r_[tar, non]
    y = np.r_[np.ones(len(tar)), np.zeros(len(non))]
    o = np.argsort(s)
    s, y = s[o], y[o]
    miss = np.cumsum(y) / len(tar)                 # 阈值取到 s[i] 时被判负的目标数
    fa = 1.0 - np.cumsum(1 - y) / len(non)
    return s, miss, fa


def eer(tar, non):
    s, miss, fa = det_curve(tar, non)
    i = np.argmin(np.abs(miss - fa))
    return float((miss[i] + fa[i]) / 2), float(s[i])


def dcf(tar, non, p_tar=0.01, c_miss=1.0, c_fa=1.0, thr=None):
    """归一化检测代价。thr=None 时返回 minDCF 与对应阈值；给了 thr 则返回 actDCF。"""
    s, miss, fa = det_curve(tar, non)
    norm = min(c_miss * p_tar, c_fa * (1 - p_tar))
    c = (c_miss * p_tar * miss + c_fa * (1 - p_tar) * fa) / norm
    if thr is None:
        i = int(np.argmin(c))
        return float(c[i]), float(s[i])
    m = float(np.mean(np.asarray(tar) < thr))
    f = float(np.mean(np.asarray(non) >= thr))
    return (c_miss * p_tar * m + c_fa * (1 - p_tar) * f) / norm, thr


def bayes_thr(p_tar=0.01, c_miss=1.0, c_fa=1.0):
    """对数似然比域上的贝叶斯最优阈值。"""
    return float(np.log(c_fa * (1 - p_tar) / (c_miss * p_tar)))


def cllr(tar, non):
    """代价对数似然比：衡量分数作为 LLR 的校准好坏。1.0 = 和瞎猜一样。"""
    t = np.logaddexp(0.0, -np.asarray(tar)).mean()
    n = np.logaddexp(0.0, np.asarray(non)).mean()
    return float((t + n) / (2 * np.log(2)))


def as_norm(score, coh_a, coh_b, k=200):
    """自适应分数归一化：用队列里最像的 k 个冒充分做均值方差归一。"""
    def z(sc, coh):
        top = np.sort(coh, -1)[..., -k:]
        return (sc - top.mean(-1)) / (top.std(-1) + 1e-9)
    return 0.5 * (z(score, coh_a) + z(score, coh_b))
