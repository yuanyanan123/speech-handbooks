#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回声消除那一部分的"进阶件"：几种不靠能量比的双讲对策。

   · energy   能量比（Geigel 一族）：麦克风功率 / 滤波器预测的回声功率 > κ 就冻结
   · coh      相干性：滤波器输出 ŷ 与麦克风 y 逐频点的相干系数，低于 θ 就冻结
   · twopath  双路径：后台滤波器一直在学，只有它明显更好时才把权重拷给前台
   · fdkf     频域卡尔曼：每个频点、每个分区各有一个"自己的步长"，不需要 DTD
   · oracle   已知真值（上界）

   这些都装在同一个分区块频域框架里，块长 B、分区数 NP、其余常数与 demo_aec_dtd.py 一致。
"""
import numpy as np
import enhlib as E
import aeclib as A

SR = A.SR
B = 256
NP = 8                 # 8 × 16 ms = 128 ms
L = B * NP
N, K = 2 * B, B + 1
MU = 0.3
REG = 0.1
WARM = 2.0             # 前 2 s DTD 不参与（真实系统也这么做）
T_SCORE = 4.0          # 统计从 4 s 之后开始
BAND = (int(300 / (SR / 2) * (K - 1)), int(3400 / (SR / 2) * (K - 1)))


# ══ 场景：远端一直在说，近端每 2 s 插话 0.6 s ═══════════════════
_SC = {}


def scene(seed, ner_db=0.0, dur=24.0, t60=0.25, noise_snr=40.0, change_s=None):
    """change_s：第几秒把回声路径整个换成另一条（挡住喇叭那一类）。"""
    key = (seed, ner_db, dur, t60, noise_snr, change_s)
    if key in _SC:
        return _SC[key]
    x = A.farend('speech', dur, seed=seed + 1)
    h = A.rir(t60, seed=seed)
    d = np.convolve(x, h)[:len(x)]
    score_from = int(T_SCORE * SR)
    if change_s is not None:
        h = A.rir(t60, seed=seed + 1000)               # 换路径之后的那一条
        n1 = int(change_s * SR)
        d = np.concatenate([d[:n1], np.convolve(x, h)[:len(x)][n1:]])
        score_from = int((change_s + 4.0) * SR)        # 给 4 s 重新收敛
    g = np.random.default_rng(500 + seed)
    n = len(d)
    near = np.zeros(n)
    dt = np.zeros(n, bool)
    t = int(T_SCORE * SR)
    k = 0
    while t < n - int(0.8 * SR):
        seg, _ = E.make_speech(dur=0.6, seed=seed * 97 + k)
        ln = min(len(seg), n - t)
        near[t:t + ln] += seg[:ln]
        dt[t:t + ln] = True
        t += int(2.0 * SR)
        k += 1
    pe = np.mean(d[dt] ** 2)
    near *= np.sqrt(pe / (np.mean(near[dt] ** 2) + A.EPS)) * 10 ** (ner_db / 20)
    v = g.standard_normal(n)
    v *= np.sqrt(np.mean(d ** 2) / 10 ** (noise_snr / 10)) / (v.std() + A.EPS)
    y = d + near + v
    _SC[key] = dict(x=x, y=y, d=d, near=near, dt=dt, h=h, v=v, score_from=score_from)
    return _SC[key]


# ══ 评分 ══════════════════════════════════════════════════════
def far_erle(d, e, dt, frm=None):
    """只在单讲段上算 ERLE"""
    n = min(len(d), len(e))
    m = ~dt[:n]
    m[:int(T_SCORE * SR) if frm is None else frm] = False
    return float(10 * np.log10((np.mean(d[:n][m] ** 2) + A.EPS) /
                               (np.mean(e[:n][m] ** 2) + A.EPS)))


def near_snr(near, e, dt, frm=None):
    """双讲段里近端语音保住了多少：近端功率 / (输出 − 近端) 的功率，dB。
       这个量和 ERLE 是两回事——ERLE 好看并不说明近端没被伤。"""
    n = min(len(near), len(e))
    m = dt[:n].copy()
    m[:int(T_SCORE * SR) if frm is None else frm] = False
    return float(10 * np.log10((np.mean(near[:n][m] ** 2) + A.EPS) /
                               (np.mean((e[:n][m] - near[:n][m]) ** 2) + A.EPS)))


def rates(froz, dt, frm=None):
    nb = len(froz)
    dtb = np.array([dt[b * B:(b + 1) * B].any() for b in range(nb)])
    act = np.arange(nb) >= int((T_SCORE * SR if frm is None else frm) / B)
    d_, s_ = dtb & act, (~dtb) & act
    miss = float(np.mean(~froz[d_])) if d_.any() else 0.0
    fa = float(np.mean(froz[s_])) if s_.any() else 0.0
    return miss, fa


# ══ 分区块频域滤波器：能量比 / 相干性 / 全知 / 不冻结 ═══════════════
def run_pb(x, y, h, mode='none', kappa=2.0, theta=0.7, hang=0, oracle=None, mu=MU):
    nb = len(y) // B
    W = np.zeros((NP, K), complex)
    Xb = np.zeros((NP, K), complex)
    Pw = np.zeros(K)
    e = np.zeros(nb * B)
    froz = np.zeros(nb, bool)
    xprev = np.zeros(B)
    yprev = np.zeros(B)
    yhprev = np.zeros(B)
    pref = 1e-20
    xi_s = 1.0
    Syy = np.full(K, 1e-12)
    Shh = np.full(K, 1e-12)
    Syh = np.zeros(K, complex)
    rho_s = 1.0
    hcnt = 0
    for b in range(nb):
        xb = x[b * B:(b + 1) * B]
        X = np.fft.rfft(np.concatenate([xprev, xb]), N)
        xprev = xb
        Xb = np.roll(Xb, 1, axis=0)
        Xb[0] = X
        yh = np.fft.irfft((Xb * W).sum(0), N)[B:]
        yb = y[b * B:(b + 1) * B]
        eb = yb - yh
        e[b * B:(b + 1) * B] = eb
        Pw = 0.9 * Pw + 0.1 * (np.abs(Xb) ** 2).sum(0)
        pb = float(np.mean(np.abs(X) ** 2))
        pref = max(pref * 0.9995, pb)
        hold = False
        if mode == 'oracle':
            hold = bool(oracle[b * B:(b + 1) * B].any())
        elif mode == 'frozen':                 # 对照：收敛期一过就再也不学
            hold = b * B / SR > T_SCORE
        elif mode in ('energy', 'coh'):
            if mode == 'energy':
                xi = float((np.mean(yb ** 2) + A.EPS) / (np.mean(yh ** 2) + A.EPS))
                xi_s = 0.6 * xi_s + 0.4 * xi
                dtd = xi_s > kappa
            else:
                Yf = np.fft.rfft(np.concatenate([yprev, yb]), N)
                Hf = np.fft.rfft(np.concatenate([yhprev, yh]), N)
                Syy = 0.9 * Syy + 0.1 * np.abs(Yf) ** 2
                Shh = 0.9 * Shh + 0.1 * np.abs(Hf) ** 2
                Syh = 0.9 * Syh + 0.1 * Yf * np.conj(Hf)
                rho = np.abs(Syh) ** 2 / (Syy * Shh + 1e-20)
                rho_s = 0.6 * rho_s + 0.4 * float(rho[BAND[0]:BAND[1]].mean())
                dtd = rho_s < theta
            hold = (b * B / SR > WARM) and dtd
        yprev, yhprev = yb, yh
        if hold:
            hcnt = hang
        elif hcnt > 0:
            hcnt -= 1
            hold = True
        froz[b] = hold
        if hold or pb < pref * 1e-3:
            continue
        Eb = np.fft.rfft(np.concatenate([np.zeros(B), eb]), N)
        G = np.conj(Xb) * Eb[None, :] / ((Pw + REG * NP * pref)[None, :] + 1e-20)
        g = np.fft.irfft(G, N, axis=-1)
        g[:, B:] = 0.0
        W = W + 2.0 * mu * np.fft.rfft(g, N, axis=-1)
    w = np.fft.irfft(W, N, axis=-1)[:, :B].reshape(-1)
    return dict(e=e, w=w, froz=froz)


# ══ 双路径：后台一直学，前台只在后台明显更好时才换 ═══════════════
def run_twopath(x, y, h, mu_b=0.5, thr=0.5, lam=0.9):
    nb = len(y) // B
    Wf = np.zeros((NP, K), complex)
    Wb = np.zeros((NP, K), complex)
    Xb = np.zeros((NP, K), complex)
    Pw = np.zeros(K)
    e = np.zeros(nb * B)
    xprev = np.zeros(B)
    pref = 1e-20
    Pf = Pbk = 1e-12
    ncopy = 0
    for b in range(nb):
        xb = x[b * B:(b + 1) * B]
        X = np.fft.rfft(np.concatenate([xprev, xb]), N)
        xprev = xb
        Xb = np.roll(Xb, 1, axis=0)
        Xb[0] = X
        yb = y[b * B:(b + 1) * B]
        yf = np.fft.irfft((Xb * Wf).sum(0), N)[B:]
        yk = np.fft.irfft((Xb * Wb).sum(0), N)[B:]
        ef, ek = yb - yf, yb - yk
        e[b * B:(b + 1) * B] = ef
        Pf = lam * Pf + (1 - lam) * float(np.mean(ef ** 2))
        Pbk = lam * Pbk + (1 - lam) * float(np.mean(ek ** 2))
        Pw = 0.9 * Pw + 0.1 * (np.abs(Xb) ** 2).sum(0)
        pb = float(np.mean(np.abs(X) ** 2))
        pref = max(pref * 0.9995, pb)
        if pb >= pref * 1e-3:
            Eb = np.fft.rfft(np.concatenate([np.zeros(B), ek]), N)
            G = np.conj(Xb) * Eb[None, :] / ((Pw + REG * NP * pref)[None, :] + 1e-20)
            g = np.fft.irfft(G, N, axis=-1)
            g[:, B:] = 0.0
            Wb = Wb + 2.0 * mu_b * np.fft.rfft(g, N, axis=-1)
        if b * B / SR > 0.5 and Pbk < thr * Pf:        # 后台明显更好：拷过去
            Wf = Wb.copy()
            Pf = Pbk
            ncopy += 1
    w = np.fft.irfft(Wf, N, axis=-1)[:, :B].reshape(-1)
    return dict(e=e, w=w, ncopy=ncopy)


# ══ 频域卡尔曼（对角近似）：不需要 DTD ═══════════════════════════
def run_fdkf(x, y, h, a=0.9995, lam=0.97, q0=1e-2):
    """每个分区、每个频点一个状态 W[p,k]，协方差只保留对角 P[p,k]。
       观测噪声功率 Ψ[k] 用"后验误差的功率"递推——近端一开口，Ψ 就跟着变大，
       卡尔曼增益自己缩小，所以步长是自动变的，不需要一个外挂的双讲检测。"""
    nb = len(y) // B
    W = np.zeros((NP, K), complex)
    Xb = np.zeros((NP, K), complex)
    P = np.full((NP, K), q0)
    Psi = np.full(K, 1e-2)
    e = np.zeros(nb * B)
    xprev = np.zeros(B)
    pref = 1e-20
    a2 = a * a
    for b in range(nb):
        xb = x[b * B:(b + 1) * B]
        X = np.fft.rfft(np.concatenate([xprev, xb]), N)
        xprev = xb
        Xb = np.roll(Xb, 1, axis=0)
        Xb[0] = X
        yh = np.fft.irfft((Xb * W).sum(0), N)[B:]
        yb = y[b * B:(b + 1) * B]
        eb = yb - yh
        e[b * B:(b + 1) * B] = eb
        pb = float(np.mean(np.abs(X) ** 2))
        pref = max(pref * 0.9995, pb)
        if pb < pref * 1e-3:
            continue
        Ef = np.fft.rfft(np.concatenate([np.zeros(B), eb]), N)
        Xp = np.abs(Xb) ** 2
        # 先验协方差：路径做随机游走，W 越大，过程噪声越大
        Wp = np.abs(W) ** 2
        P = a2 * P + (1 - a2) * Wp + 1e-9
        den = (Xp * P).sum(0) + Psi + 1e-20
        Kg = P * np.conj(Xb) / den[None, :]
        Wn = W + Kg * Ef[None, :]
        # 约束：时域截成前 B 点
        wt = np.fft.irfft(Wn, N, axis=-1)
        wt[:, B:] = 0.0
        W = np.fft.rfft(wt, N, axis=-1)
        P = (1 - 0.5 * (Kg * Xb).real) * P
        # 后验误差 → 观测噪声功率
        yh2 = np.fft.irfft((Xb * W).sum(0), N)[B:]
        Ep = np.fft.rfft(np.concatenate([np.zeros(B), yb - yh2]), N)
        Psi = lam * Psi + (1 - lam) * np.abs(Ep) ** 2
    w = np.fft.irfft(W, N, axis=-1)[:, :B].reshape(-1)
    return dict(e=e, w=w)


# ══ 双参考通道（立体声）══════════════════════════════════════════
def run_pb2(xs, y, mu=0.15, reg=REG):
    """两路参考、一路麦克风。两路各有一组分区，归一化用的是两路所有分区的功率之和。
       返回回声估计后的误差 e，以及每个块之后的 [h1;h2] 估计（用来量失调）。"""
    nch = len(xs)
    nb = len(y) // B
    W = np.zeros((nch, NP, K), complex)
    Xb = np.zeros((nch, NP, K), complex)
    Pw = np.zeros(K)
    e = np.zeros(nb * B)
    xprev = [np.zeros(B) for _ in range(nch)]
    pref = 1e-20
    snaps = {}
    for b in range(nb):
        for c in range(nch):
            xb = xs[c][b * B:(b + 1) * B]
            X = np.fft.rfft(np.concatenate([xprev[c], xb]), N)
            xprev[c] = xb
            Xb[c] = np.roll(Xb[c], 1, axis=0)
            Xb[c][0] = X
        yh = np.fft.irfft((Xb * W).sum((0, 1)), N)[B:]
        yb = y[b * B:(b + 1) * B]
        eb = yb - yh
        e[b * B:(b + 1) * B] = eb
        Pw = 0.9 * Pw + 0.1 * (np.abs(Xb) ** 2).sum((0, 1))
        pb = float(np.mean(np.abs(Xb[:, 0]) ** 2))
        pref = max(pref * 0.9995, pb)
        if (b + 1) % 64 == 0:
            snaps[b] = np.fft.irfft(W, N, axis=-1)[:, :, :B].reshape(nch, -1).copy()
        if pb < pref * 1e-3:
            continue
        Eb = np.fft.rfft(np.concatenate([np.zeros(B), eb]), N)
        G = np.conj(Xb) * Eb[None, None, :] / ((Pw + reg * NP * nch * pref)[None, None, :] + 1e-20)
        g = np.fft.irfft(G, N, axis=-1)
        g[:, :, B:] = 0.0
        W = W + 2.0 * mu * np.fft.rfft(g, N, axis=-1)
    return e, snaps
