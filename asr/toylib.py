#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一个"玩具声学世界"：能真训、真测的帧级音素分类器，供 34–38 节的实验共用。

   · 语音：enhlib.make_speech 的源-滤波合成（5 个元音 + 3 个擦音 + 静音，真值边界已知；
     说话人 = 声道长度 × 基频区间，所以"换说话人"是真的共振峰整体缩放）
   · 特征：25 ms / 10 ms 的 40 维对数梅尔，前后各拼 2 帧
   · 模型：纯 numpy 的 MLP，手写反传，Adam
   · 标签：每帧一个类（sil / a i u e o / s sh f），共 9 类

   这不是语音识别——没有词、没有语言模型、没有解码。它量的是"声学模型这一层"
   在数据增强、说话人失配、校准、压缩这些问题上的行为。
   绝对数字别和真实系统比；可比的是形状、量级和趋势。
"""
import numpy as np
import enhlib as E
import aeclib as A

SR = E.SR
FR, HOP, NMEL = 400, 160, 40
PHN = ['sil', 'a', 'i', 'u', 'e', 'o', 's', 'sh', 'f']
PID = {p: i for i, p in enumerate(PHN)}
NCLS = len(PHN)
CTX = 2
EPS = 1e-8


# ══ 特征 ══════════════════════════════════════════════════════
def _mel_fb(nfft=512, nmel=NMEL, fmin=60.0, fmax=7600.0):
    mel = lambda f: 2595 * np.log10(1 + f / 700)
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    edges = imel(np.linspace(mel(fmin), mel(fmax), nmel + 2))
    f = np.linspace(0, SR / 2, nfft // 2 + 1)
    W = np.zeros((nmel, len(f)))
    for b in range(nmel):
        lo, c, hi = edges[b], edges[b + 1], edges[b + 2]
        up = (f >= lo) & (f <= c)
        dn = (f > c) & (f <= hi)
        W[b, up] = (f[up] - lo) / max(c - lo, 1e-9)
        W[b, dn] = (hi - f[dn]) / max(hi - c, 1e-9)
    return W


_FB = _mel_fb()
_WIN = np.hanning(FR)


def logmel(x):
    """(T, NMEL)，帧长 25 ms、帧移 10 ms"""
    n = 1 + (len(x) - FR) // HOP
    idx = np.arange(FR)[None, :] + HOP * np.arange(n)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * _WIN, 512, axis=1)) ** 2
    return np.log(S @ _FB.T + 1e-6)


def stack(F, ctx=CTX):
    T = len(F)
    P = np.pad(F, ((ctx, ctx), (0, 0)), mode='edge')
    return np.concatenate([P[k:k + T] for k in range(2 * ctx + 1)], axis=1)


def frame_labels(lab, nfr):
    c = FR // 2 + HOP * np.arange(nfr)
    return lab[np.minimum(c, len(lab) - 1)]


# ══ 语料 ══════════════════════════════════════════════════════
def utterance(seed, spk=None, dur=3.0):
    """返回 (波形, 样点级音素标签 int8)"""
    x, segs = E.make_speech(dur=dur, seed=seed, spk=spk)
    x = x + 10 ** (-55 / 20) * np.random.default_rng(seed + 31).standard_normal(len(x))   # 麦克风自噪声：静音不是数字零
    lab = np.zeros(len(x), np.int8)
    for s in segs:
        lab[s['i0']:s['i1']] = PID[s['ph']]
    return x, lab


def corpus(seeds, spks, dur=3.0):
    """seeds 与 spks 等长：每条一个 (种子, 说话人)"""
    return [utterance(sd, sp, dur) + (sp,) for sd, sp in zip(seeds, spks)]


# ══ 信道与增强 ═════════════════════════════════════════════════
def add_noise(x, kind, snr, seed):
    v = E.make_noise(kind, len(x), seed=seed)
    m = np.abs(x) > 1e-3                      # 按有语音的样点对齐信噪比
    return E.mix_at_snr(x, v, snr, mask=m if m.any() else None)[0]


def reverb(x, t60, seed):
    h = A.rir(t60, seed=seed, pre_ms=4.0)
    y = np.convolve(x, h)[:len(x)]
    return y / (np.std(y) + EPS) * (np.std(x) + EPS)


def band_limit(x, lo=300.0, hi=3400.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def speed(x, lab, factor):
    """变速（同时改音高和共振峰，和真实的 speed perturbation 一致）。factor>1 更快更短。"""
    n = int(len(x) / factor)
    t = np.arange(n) * factor
    i = np.minimum(t.astype(int), len(x) - 2)
    fr = t - i
    y = x[i] * (1 - fr) + x[i + 1] * fr
    return y, lab[np.minimum(np.round(t).astype(int), len(lab) - 1)]


def make_xy(utts, chan=None, norm='none'):
    """chan(x, lab, k) → (x', lab')；返回逐条的 (X, Y)"""
    out = []
    for k, (x, lab, sp) in enumerate(utts):
        if chan is not None:
            x, lab = chan(x, lab, k)
        F = logmel(x)
        Y = frame_labels(lab, len(F))
        out.append((F, Y, sp))
    return out


def cmvn(F):
    return (F - F.mean(0)) / (F.std(0) + 1e-3)


def assemble(xy, norm='none', mu=None, sd=None, specaug=None, rng=None):
    """把逐条的 (F, Y) 拼成 (X, Y)。norm: none / utt（逐条 CMVN）/ glob（用给定的全局 mu, sd）"""
    Xs, Ys = [], []
    for F, Y, _ in xy:
        if norm == 'utt':
            F = cmvn(F)
        elif norm == 'glob':
            F = (F - mu) / sd
        if specaug is not None:
            F = specaug(F.copy(), rng)
        Xs.append(stack(F))
        Ys.append(Y)
    return np.concatenate(Xs), np.concatenate(Ys)


def spec_augment(F, rng, nf=2, fw=6, nt=2, tw=10):
    """频率掩蔽 nf 条（最宽 fw 个频带）+ 时间掩蔽 nt 条（最宽 tw 帧），掩成该条的均值"""
    T, D = F.shape
    m = F.mean()
    for _ in range(nf):
        w = int(rng.integers(0, fw + 1))
        f0 = int(rng.integers(0, max(D - w, 1)))
        F[:, f0:f0 + w] = m
    for _ in range(nt):
        w = int(rng.integers(0, tw + 1))
        t0 = int(rng.integers(0, max(T - w, 1)))
        F[t0:t0 + w] = m
    return F


# ══ MLP ═══════════════════════════════════════════════════════
class MLP:
    def __init__(self, sizes, seed=0):
        g = np.random.default_rng(seed)
        self.W = [g.standard_normal((a, b)) * np.sqrt(2.0 / a) for a, b in zip(sizes[:-1], sizes[1:])]
        self.b = [np.zeros(b) for b in sizes[1:]]
        self.sizes = list(sizes)

    def copy(self):
        m = MLP(self.sizes)
        m.W = [w.copy() for w in self.W]
        m.b = [b.copy() for b in self.b]
        return m

    def nparams(self):
        return sum(w.size for w in self.W) + sum(b.size for b in self.b)

    def logits(self, X, keep=False):
        a = [X]
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            z = a[-1] @ W + b
            a.append(np.maximum(z, 0) if i < len(self.W) - 1 else z)
        return (a[-1], a) if keep else a[-1]

    def proba(self, X, T=1.0):
        z = self.logits(X) / T
        z = z - z.max(1, keepdims=True)
        p = np.exp(z)
        return p / p.sum(1, keepdims=True)

    def acc(self, X, Y):
        return float(np.mean(self.logits(X).argmax(1) == Y))

    def fit(self, X, Y, epochs=20, bs=256, lr=2e-3, seed=0, soft=None, T=1.0, alpha=1.0,
            freeze=(), weight_decay=0.0, Xval=None, Yval=None, verbose=False):
        """Adam。soft：教师的软标签（已按温度 T 给出的概率），损失 = α·KD·T² + (1−α)·CE。
           freeze：不更新的层下标（0 起）。"""
        g = np.random.default_rng(seed)
        n = len(X)
        mW = [np.zeros_like(w) for w in self.W]
        vW = [np.zeros_like(w) for w in self.W]
        mb = [np.zeros_like(b) for b in self.b]
        vb = [np.zeros_like(b) for b in self.b]
        t = 0
        L = len(self.W)
        for ep in range(epochs):
            perm = g.permutation(n)
            for s in range(0, n, bs):
                idx = perm[s:s + bs]
                xb, yb = X[idx], Y[idx]
                z, a = self.logits(xb, keep=True)
                zz = z - z.max(1, keepdims=True)
                p = np.exp(zz)
                p /= p.sum(1, keepdims=True)
                d = p.copy()
                d[np.arange(len(idx)), yb] -= 1.0
                d /= len(idx)
                if soft is not None:
                    zt = z / T
                    zt = zt - zt.max(1, keepdims=True)
                    pt = np.exp(zt)
                    pt /= pt.sum(1, keepdims=True)
                    dk = (pt - soft[idx]) / (T * len(idx)) * (T * T)
                    d = alpha * dk + (1 - alpha) * d
                t += 1
                for i in range(L - 1, -1, -1):
                    gW = a[i].T @ d + weight_decay * self.W[i]
                    gb = d.sum(0)
                    if i > 0:
                        d = (d @ self.W[i].T) * (a[i] > 0)
                    if i in freeze:
                        continue
                    for (m_, v_, w_, g_) in ((mW, vW, self.W, gW), (mb, vb, self.b, gb)):
                        m_[i] = 0.9 * m_[i] + 0.1 * g_
                        v_[i] = 0.999 * v_[i] + 0.001 * g_ * g_
                        w_[i] -= lr * (m_[i] / (1 - 0.9 ** t)) / (np.sqrt(v_[i] / (1 - 0.999 ** t)) + 1e-8)
            if verbose and Xval is not None:
                print('  ep %2d  val %.4f' % (ep, self.acc(Xval, Yval)))
        return self


def quantize(m, bits=8, per_channel=True):
    """对称均匀的权重量化（只量化权重，激活保持浮点）。返回一个新模型。"""
    q = m.copy()
    qmax = 2 ** (bits - 1) - 1
    for i, W in enumerate(q.W):
        if per_channel:
            s = np.abs(W).max(0, keepdims=True) / qmax
        else:
            s = np.full((1, W.shape[1]), np.abs(W).max() / qmax)
        s = np.maximum(s, 1e-12)
        q.W[i] = np.clip(np.round(W / s), -qmax, qmax) * s
    return q


def ece(p, y, nb=10):
    """期望校准误差：置信度分桶后，|桶内准确率 − 桶内平均置信度| 的加权平均"""
    conf = p.max(1)
    pred = p.argmax(1)
    ok = (pred == y).astype(float)
    e = 0.0
    for b in range(nb):
        lo, hi = b / nb, (b + 1) / nb
        m = (conf > lo) & (conf <= hi) if b > 0 else (conf >= lo) & (conf <= hi)
        if m.any():
            e += m.mean() * abs(ok[m].mean() - conf[m].mean())
    return float(e)
