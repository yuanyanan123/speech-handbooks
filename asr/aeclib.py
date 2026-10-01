#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回声消除那几组实验的公共件：回声路径、NLMS、频域分块、ERLE 与失调。

   路径用指数衰减的随机冲激响应合成（给定 T60），不是真实房间，
   但"尾巴有多长、截断会丢多少"这两件事的形状是对的——
   而这一部分要讲的恰好是形状。
"""
import numpy as np
import enhlib as E

SR = E.SR
EPS = 1e-12


# ══ 回声路径 ══════════════════════════════════════════════════
def rir(t60=0.25, seed=0, sr=SR, direct=0.35, pre_ms=4.0):
    """指数衰减的随机冲激响应。direct 是直达声占总能量的比例，
       pre_ms 是扬声器到麦克风的纯时延（设备上通常只有几毫秒）。"""
    g = np.random.default_rng(seed)
    n = int(min(t60 * 1.6, 1.0) * sr)
    tau = t60 * sr / (3 * np.log(10))
    h = g.standard_normal(n) * np.exp(-np.arange(n) / tau)
    h /= np.linalg.norm(h) + EPS
    d = int(pre_ms * sr / 1000)
    out = np.zeros(d + n)
    out[d] = np.sqrt(direct)
    out[d:] += np.sqrt(1 - direct) * h
    return out / (np.linalg.norm(out) + EPS)


def tail_energy(h, l_ms, sr=SR):
    """截到 l_ms 之后，尾巴里还剩多少能量占比——它钉死了 ERLE 的上界"""
    n = int(l_ms * sr / 1000)
    if n >= len(h):
        return 0.0
    return float(np.sum(h[n:] ** 2) / (np.sum(h ** 2) + EPS))


# ══ 远端信号 ══════════════════════════════════════════════════
def farend(kind, dur=8.0, seed=1, sr=SR):
    """远端参考：白噪 / 粉噪 / 语音。谱越不平，NLMS 收敛越慢。"""
    n = int(dur * sr)
    if kind == 'white':
        x = np.random.default_rng(seed).standard_normal(n)
    elif kind == 'pink':
        x = E.make_noise('pink', n, seed=seed)
    elif kind == 'speech':
        xs = []
        k = 0
        while sum(len(s) for s in xs) < n:
            s, _ = E.make_speech(dur=3.0, seed=seed * 31 + k)
            xs.append(s)
            k += 1
        x = np.concatenate(xs)[:n]
    else:
        raise ValueError(kind)
    return x / (np.std(x) + EPS)


def eig_spread(x, p=32):
    """输入自相关阵的特征值扩散度——NLMS 收敛速度的真正决定因素"""
    r = np.correlate(x, x, 'full')[len(x) - 1:len(x) - 1 + p] / len(x)
    R = np.array([[r[abs(i - j)] for j in range(p)] for i in range(p)])
    ev = np.linalg.eigvalsh(R)
    return float(max(ev) / max(min(ev), 1e-9))


# ══ 指标 ══════════════════════════════════════════════════════
def erle_curve(d, e, blk_ms=64, sr=SR):
    """逐块的回声回损增强：10log10(E{d²}/E{e²})"""
    b = int(blk_ms * sr / 1000)
    nb = min(len(d), len(e)) // b
    out = []
    for i in range(nb):
        dd = d[i * b:(i + 1) * b]
        ee = e[i * b:(i + 1) * b]
        out.append(10 * np.log10((np.mean(dd ** 2) + EPS) / (np.mean(ee ** 2) + EPS)))
    return np.array(out)


def misalign(w, h):
    """失调：估出来的路径离真实路径有多远（dB，越低越好）"""
    n = min(len(w), len(h))
    hh = np.zeros(len(w)); hh[:n] = h[:n]
    return float(20 * np.log10((np.linalg.norm(w - hh) + EPS) /
                               (np.linalg.norm(hh) + EPS)))


def t_converge(curve, target, blk_ms=64):
    """头一次达到 target dB 的时刻（秒）；没达到返回 None"""
    idx = np.where(curve >= target)[0]
    return None if len(idx) == 0 else float(idx[0] * blk_ms / 1000)


# ══ 时域 NLMS ═════════════════════════════════════════════════
def nlms(x, y, L, mu=0.5, delta=1e-3, freeze=None, w0=None):
    """最朴素的那一版，一个抽头一个抽头地更新。
       freeze: 和 y 等长的布尔数组，True 的样本点上不更新（双讲冻结）。
       返回 (误差信号, 最终权, 每 1024 点记一次的失调轨迹用的权快照)"""
    n = len(y)
    w = np.zeros(L) if w0 is None else w0.copy()
    xb = np.zeros(L)
    e = np.zeros(n)
    pw = np.mean(x ** 2) * L + EPS
    snaps = []
    for i in range(n):
        xb[1:] = xb[:-1]
        xb[0] = x[i]
        yh = xb @ w
        e[i] = y[i] - yh
        if freeze is None or not freeze[i]:
            w += mu * e[i] * xb / (xb @ xb + delta * pw)
        if (i & 1023) == 0:
            snaps.append(w.copy())
    return e, w, snaps


# ══ 扬声器非线性 ══════════════════════════════════════════════
def loudspeaker(x, drive=0.0):
    """软限幅。drive 是过载倍数：0 完全线性，越大削得越狠。
       返回 (输出, 非线性占比%)——这里的"非线性"是<strong>减掉最佳线性拟合之后</strong>
       剩下的那部分，也就是线性滤波器结构上拿不到的那一截。"""
    if drive <= 0:
        return x.copy(), 0.0
    a = np.max(np.abs(x)) / drive
    y = a * np.tanh(x / (a + EPS))
    al = float(np.dot(y, x) / (np.dot(x, x) + EPS))     # 最佳线性拟合
    nl = y - al * x
    return y, float(100 * np.sqrt(np.mean(nl ** 2) /
                                  (np.mean((al * x) ** 2) + EPS)))


# ══ 采样率偏差 ════════════════════════════════════════════════
def drift(x, ppm):
    """把信号按 (1+ppm·1e-6) 重采样——播放端和采集端时钟不同步的后果"""
    if ppm == 0:
        return x.copy()
    n = len(x)
    t = np.arange(n) * (1 + ppm * 1e-6)
    t = np.clip(t, 0, n - 1.001)
    i = t.astype(int)
    f = t - i
    return x[i] * (1 - f) + x[i + 1] * f


# ══ 分区块频域（PBFDAF）═══════════════════════════════════════
def pbfdaf(x, y, B, np_, mu=0.5, lam=0.9, reg=1e-2, freeze=None, bins_norm=True):
    """把长滤波器切成 np_ 个 B 点的分区，各自在频域更新。
       这是实际系统用的那一版：块长 B 决定延迟，分区数 np_ 决定滤波器总长，
       两者解耦——单块 FDAF 里它们是绑死的。"""
    N, K = 2 * B, B + 1
    nb = len(y) // B
    W = np.zeros((np_, K), complex)
    Xb = np.zeros((np_, K), complex)
    Pw = np.zeros(K)
    e = np.zeros(nb * B)
    xprev = np.zeros(B)
    pref = 1e-20
    for b in range(nb):
        xb = x[b * B:(b + 1) * B]
        X = np.fft.rfft(np.concatenate([xprev, xb]), N)
        xprev = xb
        Xb = np.roll(Xb, 1, axis=0)
        Xb[0] = X
        yh = np.fft.irfft((Xb * W).sum(0), N)[B:]
        eb = y[b * B:(b + 1) * B] - yh
        e[b * B:(b + 1) * B] = eb
        # 分母必须是<strong>所有分区</strong>的功率之和：当前块安静、
        # 而几个块之前是元音时，只用当前块会把步长放大成发散。
        Pw = lam * Pw + (1 - lam) * (np.abs(Xb) ** 2).sum(0)
        pb = float(np.mean(np.abs(X) ** 2))
        pref = max(pref * 0.9995, pb)
        if pb < pref * 1e-3:                       # 远端静音，不更新
            continue
        if freeze is not None and freeze[b * B:(b + 1) * B].any():
            continue
        Eb = np.fft.rfft(np.concatenate([np.zeros(B), eb]), N)
        if bins_norm:
            den = Pw + reg * np_ * pref
        else:
            # 不做白化时，步长只能按<strong>最强的那个频点</strong>定，
            # 否则强频点先发散——弱频点于是慢了 λmax/λmin 倍。
            den = np.full(K, max(Pw.max(), reg * np_ * pref))
        G = np.conj(Xb) * Eb[None, :] / (den[None, :] + 1e-20)
        g = np.fft.irfft(G, N, axis=-1)
        g[:, B:] = 0.0
        W = W + 2.0 * mu * np.fft.rfft(g, N, axis=-1)
    w = np.fft.irfft(W, N, axis=-1)[:, :B].reshape(-1)
    return e, w
