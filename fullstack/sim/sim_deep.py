# -*- coding: utf-8 -*-
"""深化篇的检验（D 系列）：每项的预测来自本节推导出的闭式，仿真来自独立的蒙特卡洛 / 暴力枚举 / 直接模拟。"""
import numpy as np
from itertools import product
from math import comb
from scipy import linalg, signal
from common import check, rng, cn


# ── D1 阵列：对角加载、WNG 与导向失配 ──
def d1():
    M, d, c, f = 6, 0.04, 343.0, 1500.0
    pos = d * np.arange(M)
    a = np.exp(-2j * np.pi * f * pos * np.cos(np.deg2rad(60)) / c)            # 目标 60°
    dist = np.abs(pos[:, None] - pos[None])
    G = np.sinc(2 * f * dist / c)                                             # 扩散场相干
    P = G + 1e-3 * np.eye(M)

    def w_of(delta):
        Q = linalg.inv(P + delta * np.eye(M)); v = Q @ a
        return v / (a.conj() @ v)
    wng = lambda w: abs(w.conj() @ a) ** 2 / np.real(w.conj() @ w)
    ds = [0, 1e-3, 1e-2, 1e-1, 1, 10, 1e3, 1e6]
    ws = [wng(w_of(x)) for x in ds]
    check('D1a', '2', 'dl_wng', '加载量增大时 WNG 单调不降（最小增量，dB）', 0.0, min(10 * np.log10(ws[i + 1] / ws[i]) for i in range(len(ws) - 1)), 1e-9, 'ge')
    check('D1b', '2', 'dl_wng', 'δ→∞ 时 MVDR→DAS，WNG→M（dB）', 10 * np.log10(M), 10 * np.log10(ws[-1]), 0.01)
    # 蒙特卡洛：白噪声通过 w，输出功率 = wᴴw·σ²
    g = rng(51); n = 400000
    w = w_of(0.1); z = cn(g, M, n)
    pw = np.mean(np.abs(w.conj() @ z) ** 2)
    check('D1c', '2', 'dl_wng', '白噪声输出功率 = ‖w‖²（蒙特卡洛）', np.real(w.conj() @ w), pw, 0.01, 'rel')
    # 导向失配：真实源与假设方向偏 8°，加载使信号增益 |wᴴa_true|² 更接近 1（抗自消除）
    a_t = np.exp(-2j * np.pi * f * pos * np.cos(np.deg2rad(68)) / c)
    gains = [abs(w_of(x).conj() @ a_t) ** 2 for x in (0, 1e-2, 1e-1, 1, 1e3)]
    check('D1d', '2', 'dl_wng', '导向失配下信号增益：重加载（δ=10³）比不加载至少高 0.1（注：并非严格单调）', gains[0] + 0.1, gains[-1], 0.0, 'ge')


# ── D2 AEC：跟踪与噪声的折中，最优步长 ──
def d2():
    L, sx, sv, q = 16, 1.0, 0.1, 2e-7
    N = 120000
    g = rng(52)
    mus = [0.05, 0.1, 0.2, 0.4, 0.8]
    sim_msd = []
    pred_msd = []
    for mu in mus:
        h = g.standard_normal(L) / np.sqrt(L)
        w = np.zeros(L); x = g.standard_normal(N + L) * sx; v = g.standard_normal(N) * sv
        rw = g.standard_normal((N, L)) * np.sqrt(q)
        acc = []
        for n in range(N):
            xv = x[n:n + L][::-1]
            h = h + rw[n]
            e = xv @ h + v[n] - xv @ w
            w = w + mu * e * xv / (xv @ xv + 1e-9)
            if n > N // 2:
                acc.append(np.sum((h - w) ** 2))
        sim_msd.append(np.mean(acc))
        pred_msd.append(mu * sv ** 2 / ((2 - mu) * sx ** 2) + L ** 2 * q / (mu * (2 - mu)))
    for mu, p, s in zip(mus, pred_msd, sim_msd):
        check('D2a', '3,19', 'nlms_track', 'NLMS 跟踪稳态 MSD（μ=%g）' % mu, p, s, 0.25, 'rel')
    check('D2b', '3,19', 'nlms_track', '最优步长落在同一格（μ 网格 argmin）', float(np.argmin(pred_msd)), float(np.argmin(sim_msd)), 1.0)


# ── D3 单通道：噪声抑制与语音失真的约束形式，参数维纳 ──
def d3():
    g = rng(53); n = 2_000_000
    ss, sn = 1.0, 0.5
    s = g.standard_normal(n) * np.sqrt(ss); v = g.standard_normal(n) * np.sqrt(sn)
    xi = ss / sn
    for mu in (0.5, 1.0, 3.0):
        Gm = xi / (xi + mu)
        dist = np.mean((s - Gm * s) ** 2); res = np.mean((Gm * v) ** 2)
        check('D3a', '4', 'pwf', '参数维纳 μ=%g：语音失真 (1−G)²σs²' % mu, (1 - Gm) ** 2 * ss, dist, 0.01, 'rel')
        check('D3b', '4', 'pwf', '参数维纳 μ=%g：残余噪声 G²σn²' % mu, Gm ** 2 * sn, res, 0.01, 'rel')
    # 约束形式：给定残余噪声上限 R，最小失真的 G 就是 √(R/σn²)；与 μ 的关系 G=ξ/(ξ+μ)
    R = 0.1
    Gc = np.sqrt(R / sn); mu_star = xi * (1 / Gc - 1)
    check('D3c', '4', 'pwf', '约束形式的拉格朗日乘子 μ* = ξ(1/G−1) 回代满足约束', R, (xi / (xi + mu_star)) ** 2 * sn, 1e-9)
    grid = np.linspace(0.01, 1, 2000)
    feas = grid[grid ** 2 * sn <= R + 1e-12]
    best = feas[np.argmin((1 - feas) ** 2 * ss)]
    check('D3d', '4', 'pwf', '约束下最小失真的 G 在可行域边界上', Gc, best, 1e-3)


# ── D4 混响：Schroeder 反向积分与晚期能量 ──
def d4():
    g = rng(54); fs = 16000
    T60 = 0.5
    rho = 6.9078 / T60 / fs                                                   # 振幅衰减率 per sample，使能量 −60 dB 在 T60
    n = np.arange(int(1.2 * fs))
    est = []
    for k in range(20):
        h = g.standard_normal(len(n)) * np.exp(-rho * n)
        edc = np.cumsum((h ** 2)[::-1])[::-1]; edc_db = 10 * np.log10(edc / edc[0])
        i1 = np.argmax(edc_db <= -5); i2 = np.argmax(edc_db <= -35)
        slope = (edc_db[i2] - edc_db[i1]) / ((i2 - i1) / fs)                  # dB/s
        est.append(-60 / slope)
    check('D4a', '5', 'rt60', 'Schroeder 反向积分估得的 RT60（s）', T60, np.mean(est), 0.03, 'rel')
    # 晚期混响能量与直达能量之比：直达幅度 1，扩散尾 σ²exp(−2ρn)，n ≥ N0
    sig2 = 0.01; N0 = int(0.05 * fs)
    late = np.mean([np.sum((g.standard_normal(len(n) - N0) * np.sqrt(sig2) * np.exp(-rho * n[N0:])) ** 2) for _ in range(200)])
    pred = sig2 * np.exp(-2 * rho * N0) / (1 - np.exp(-2 * rho))
    check('D4b', '5', 'rt60', '晚期混响总能量闭式（几何级数）', pred, late, 0.03, 'rel')


# ── D5 特征：DCT 近似 KLT；窗的主瓣宽度 ──
def d5():
    from scipy.fft import dct
    N, rho = 16, 0.9
    C = rho ** np.abs(np.arange(N)[:, None] - np.arange(N)[None])             # AR(1) 协方差
    ev = np.linalg.eigvalsh(C)
    D = dct(np.eye(N), type=2, norm='ortho', axis=0)                           # 行是 DCT 基
    vd = np.diag(D @ C @ D.T)
    gm = lambda v: 10 * np.log10(np.mean(v) / np.exp(np.mean(np.log(v))))     # 编码增益：算术均值/几何均值
    gk, gd = gm(ev), gm(vd)
    check('D5a', '6', 'dct_klt', 'KLT 的编码增益不低于 DCT（dB）', 0.0, gk - gd, 1e-9, 'ge')
    check('D5b', '6', 'dct_klt', 'AR(1) ρ=0.9 下 DCT 与 KLT 编码增益之差 ≤ 0.15 dB', 0.0, gk - gd, 0.15)
    # 窗：Hann 主瓣半宽 = 2 bin，矩形窗 = 1 bin
    Nw, Z = 256, 16
    for name, w, pred in (('Hann', np.hanning(Nw + 1)[:-1], 2.0), ('矩形', np.ones(Nw), 1.0)):
        S = np.abs(np.fft.rfft(w, Nw * Z))
        first_null = np.argmax(np.diff(S) > 1e-9 * S.max()) / Z                 # 第一个零点（单调下降结束处）
        check('D5c', '6', 'win_lobe', '%s 窗主瓣半宽（bin）' % name, pred, first_null, 0.1)


# ── D6 解码：对数线性组合中，声学标度与 LM 权重的比值为 1 时最优 ──
def d6():
    g = rng(56); K, n = 6, 400000
    kappa = 2.5                                                                # 声学分数被放大 κ 倍（过自信）
    prior = np.array([0.4, 0.25, 0.15, 0.1, 0.06, 0.04])
    w_true = g.choice(K, size=n, p=prior)
    mu = np.arange(K) * 0.7
    x = mu[w_true] + g.standard_normal(n)                                       # 标量观测，高斯似然
    ll = -0.5 * (x[:, None] - mu[None]) ** 2                                    # log p(x|w) 去掉常数
    accs = []
    lams = [0.5, 1, 1.5, 2, 2.5, 3, 4, 6]
    for lam in lams:
        sc = kappa * ll + lam * np.log(prior)[None]
        accs.append(np.mean(np.argmax(sc, 1) == w_true))
    best = max(accs)
    check('D6a', '8', 'logLin', 'λ=κ（贝叶斯比例）时的准确率不低于网格上的最优', best, accs[lams.index(2.5)], 0.003, 'ge')
    check('D6b', '8', 'logLin', '最优网格点就是 λ/κ = 1', 2.5, lams[int(np.argmax(accs))], 0.01)


# ── D7 理解：误认的代价与拒识阈值 ──
def d7():
    g = rng(57); n = 600000
    conf = g.beta(3, 1.2, n)                                                   # 置信度
    correct = g.random(n) < conf                                               # 校准：P(正确|conf)=conf
    c_err, c_rej = 5.0, 1.0                                                    # 误执行代价、拒识（追问）代价
    t_star = 1 - c_rej / c_err                                                 # 接受当且仅当 (1−p)·c_err ≤ c_rej
    def cost(t):
        acc = conf >= t
        return np.mean(np.where(acc, (~correct) * c_err, c_rej))
    ts = np.linspace(0.05, 0.99, 95)
    cs = np.array([cost(t) for t in ts])
    check('D7a', '9', 'rej_thr', '拒识阈值 t* = 1 − c_拒/c_误（网格最优位置）', t_star, ts[np.argmin(cs)], 0.03)
    check('D7b', '9', 'rej_thr', 't* 处的平均代价不高于网格最优 + 噪声', cs.min(), cost(t_star), 0.003, 'le')


# ── D8 文本前端：线性链 CRF 的配分函数与梯度 ──
def d8():
    g = rng(58); T, K = 5, 3
    E = g.standard_normal((T, K)); A = g.standard_normal((K, K))                 # 发射分数与转移分数
    def score(y):
        return sum(E[t, y[t]] for t in range(T)) + sum(A[y[t - 1], y[t]] for t in range(1, T))
    allp = list(product(range(K), repeat=T))
    sc = np.array([score(y) for y in allp])
    logZ_b = np.log(np.sum(np.exp(sc)))
    al = E[0].copy()
    for t in range(1, T):
        al = np.logaddexp.reduce(al[:, None] + A, axis=0) + E[t]
    logZ_f = np.logaddexp.reduce(al)
    check('D8a', '10', 'crf', '前向算法的 log Z = 暴力枚举', logZ_b, logZ_f, 1e-9)
    ybest = allp[int(np.argmax(sc))]
    dp = E[0].copy(); bp = []
    for t in range(1, T):
        m = dp[:, None] + A; bp.append(np.argmax(m, 0)); dp = m.max(0) + E[t]
    y = [int(np.argmax(dp))]
    for b in reversed(bp):
        y.append(int(b[y[-1]]))
    y = tuple(reversed(y))
    check('D8b', '10', 'crf', 'Viterbi 路径 = 暴力枚举最优路径', 1.0, float(y == ybest), 0.0)
    # 梯度：∂ log p(y*)/∂E[t,k] = 1[y*_t=k] − p(y_t=k)
    ystar = allp[7]
    p = np.exp(sc - logZ_b)
    marg = np.zeros((T, K))
    for pi, yy in zip(p, allp):
        for t in range(T):
            marg[t, yy[t]] += pi
    gr = -marg
    for t in range(T):
        gr[t, ystar[t]] += 1
    def ll(Ep):
        s0 = sum(Ep[t, ystar[t]] for t in range(T)) + sum(A[ystar[t - 1], ystar[t]] for t in range(1, T))
        s_all = [sum(Ep[t, yy[t]] for t in range(T)) + sum(A[yy[t - 1], yy[t]] for t in range(1, T)) for yy in allp]
        return s0 - np.log(np.sum(np.exp(s_all)))
    fd = np.zeros((T, K)); h = 1e-6
    for t in range(T):
        for k in range(K):
            Ep = E.copy(); Ep[t, k] += h; Em = E.copy(); Em[t, k] -= h
            fd[t, k] = (ll(Ep) - ll(Em)) / (2 * h)
    check('D8c', '10', 'crf', 'CRF 梯度 = 经验计数 − 期望计数（对有限差分的最大偏差）', 0.0, np.max(np.abs(gr - fd)), 1e-6)


# ── D9 编解码：RVQ 的率失真下界 ──
def d9():
    from scipy.cluster.vq import kmeans2
    g = rng(59); d, K, n = 4, 16, 60000
    X = g.standard_normal((n, d)); R = X.copy()
    mse = []
    for q in range(4):
        cb, lab = kmeans2(R, K, minit='++', seed=q + 1, iter=25)
        R = R - cb[lab]
        mse.append(np.mean(R ** 2))
    bits = [(q + 1) * np.log2(K) / d for q in range(4)]
    for q in range(4):
        bound = 2 ** (-2 * bits[q])
        check('D9a', '12', 'rd_bound', 'RVQ 第 %d 级的 MSE 不低于率失真下界 σ²·2^(−2R)' % (q + 1), bound, mse[q], 1e-9, 'ge')
    ratios = [mse[i + 1] / mse[i] for i in range(3)]
    check('D9b', '12', 'rd_bound', '每级把残差能量压到上一级的 0~1 倍（最大比值）', 1.0, max(ratios), 0.0, 'le')


# ── D10 传输：Gilbert–Elliott 丢包与 FEC 残余丢包 ──
def d10():
    g = rng(60); n = 3_000_000
    p, r = 0.02, 0.25                                                          # 好→坏、坏→好
    pi_b = p / (p + r)
    state = np.zeros(n, dtype=bool); u = g.random(n); s = False
    for i in range(n):
        s = (u[i] < p) if not s else (u[i] >= r)
        state[i] = s
    check('D10a', '18', 'ge', 'GE 模型的平稳丢包率 π_B = p/(p+r)', pi_b, state.mean(), 0.03, 'rel')
    d = np.diff(np.concatenate(([0], state.astype(int), [0])))
    runs = np.where(d == -1)[0] - np.where(d == 1)[0]
    check('D10b', '18', 'ge', '平均突发长度 1/r', 1 / r, runs.mean(), 0.03, 'rel')
    # FEC (n,k)：独立丢包 p0 时，一组中丢包数 > n−k 则失败
    nn, kk, p0 = 10, 8, 0.05
    pred = sum(comb(nn, i) * p0 ** i * (1 - p0) ** (nn - i) for i in range(nn - kk + 1, nn + 1))
    losses = (g.random((400000, nn)) < p0).sum(1)
    check('D10c', '18', 'fec', '(n,k) 擦除码的失败概率', pred, np.mean(losses > nn - kk), 0.03, 'rel')


# ── D11 评测：WER 的方差（delta 方法）与 bootstrap ──
def d11():
    g = rng(61); n = 400
    Nn = g.integers(5, 25, n).astype(float)
    err = np.array([g.binomial(int(k), 0.1) for k in Nn], dtype=float)
    R = err.sum() / Nn.sum()
    z = err - R * Nn
    se_delta = np.sqrt(np.sum(z ** 2)) / Nn.sum()
    bs = []
    for _ in range(3000):
        i = g.integers(0, n, n)
        bs.append(err[i].sum() / Nn[i].sum())
    check('D11a', '15', 'wer_var', 'WER 标准误：delta 方法 vs bootstrap', np.std(bs), se_delta, 0.05, 'rel')
    # 对独立重复抽样的总体：真实标准误
    emp = []
    for _ in range(3000):
        N2 = g.integers(5, 25, n).astype(float); e2 = g.binomial(N2.astype(int), 0.1).astype(float)
        emp.append(e2.sum() / N2.sum())
    check('D11b', '15', 'wer_var', 'WER 标准误：delta 方法 vs 重复抽样', np.std(emp), se_delta, 0.08, 'rel')


# ── D12 闭环：回声路径的稳定性与 ERLE 换算的增益裕量 ──
def d12():
    g = rng(62)
    h = np.zeros(40); h[[8, 15, 23, 31]] = [0.6, -0.4, 0.3, 0.2]; h[3] = 0.0
    def radius(G, hh):
        # y[n] = G Σ hh[k] y[n−k]：特征方程 z^L = G Σ hh[k] z^{L−k}
        L = len(hh) - 1 + 1
        co = np.zeros(L + 1); co[0] = 1.0
        for k in range(1, len(hh)):
            co[k] = -G * hh[k]
        return np.max(np.abs(np.roots(co)))
    lo, hi = 0.01, 50.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if radius(mid, h) < 1 else (lo, mid)
    Gc = lo
    def diverges(G, hh, n=6000):
        y = np.zeros(n); y[0] = 1.0
        for i in range(1, n):
            kmax = min(i, len(hh) - 1)
            y[i] = G * np.dot(hh[1:kmax + 1], y[i - 1::-1][:kmax]) if kmax > 0 else 0
        return abs(y[-1]) > abs(y[0]) * 10 or not np.isfinite(y[-1])
    check('D12a', '14', 'loop_gain', '增益 0.95·G_crit 时时域仿真不发散', 0.0, float(diverges(0.95 * Gc, h)), 0.0)
    check('D12b', '14', 'loop_gain', '增益 1.05·G_crit 时时域仿真发散', 1.0, float(diverges(1.05 * Gc, h)), 0.0)
    check('D12c', '14', 'loop_gain', '充分条件 G < 1/Σ|h| 保守地低于临界增益', 1 / np.sum(np.abs(h)), Gc, 0.0, 'ge')
    # ERLE E dB：残余路径 = h·10^(−E/20) → 临界增益抬高 E dB
    for E in (6, 20):
        Gc2 = Gc * 10 ** (E / 20)
        check('D12d', '14', 'loop_gain', 'ERLE=%d dB 使临界增益提高同样的 dB（根轨迹验证）' % E, 20 * np.log10(Gc2 / Gc),
              20 * np.log10(Gc2 / Gc) if abs(radius(Gc2, h * 10 ** (-E / 20)) - 1) < 1e-3 else -999, 0.01)


def run():
    for f in (d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11, d12):
        f()


# ════════ 第二批（D13–D20）：评价、评测、硬件、时钟 ════════
from scipy.stats import norm


def d13():
    """MOS 的方差分解：条目 × 评分员交叉设计"""
    g = rng(63); I, J = 20, 15
    si, sr, se = 0.5, 0.35, 0.8
    reps = 20000
    a = g.standard_normal((reps, I, 1)) * si
    b = g.standard_normal((reps, 1, J)) * sr
    e = g.standard_normal((reps, I, J)) * se
    m = (3.8 + a + b + e).mean((1, 2))
    pred = si ** 2 / I + sr ** 2 / J + se ** 2 / (I * J)
    check('D13a', '13', 'mos_var', 'MOS 均值的方差：σᵢ²/I + σᵣ²/J + σₑ²/(IJ)', pred, m.var(), 0.03, 'rel')
    # 评分员很多时，方差趋于下限 σᵢ²/I（条目效应不会被评分员平均掉）
    J2 = 600
    a2 = g.standard_normal((reps, I, 1)) * si
    b2 = g.standard_normal((reps, 1, J2)) * sr
    e2 = g.standard_normal((reps, I, J2)) * se
    m2 = (3.8 + a2 + b2 + e2).mean((1, 2))
    check('D13b', '13', 'mos_var', '评分员增至 600 人：方差 → σᵢ²/I + 小项，下限不被评分员数消掉', si ** 2 / I + sr ** 2 / J2 + se ** 2 / (I * J2), m2.var(), 0.04, 'rel')
    check('D13c', '13', 'mos_var', '600 人时的方差仍不低于 σᵢ²/I（条目数决定下限）', si ** 2 / I, m2.var(), 0.0, 'ge')


def d14():
    """流式合成：不欠载所需的最小预缓冲"""
    g = rng(64)
    c = 0.20                                                                    # 每块音频时长（s）
    worst = 0
    ok_at = ok_below = True
    for trial in range(200):
        n = 60
        p = g.lognormal(np.log(0.14), 0.45, n)                                  # 每块的生成耗时
        A = np.cumsum(p)
        T0 = max(A[k] - k * c for k in range(n))                                # 闭式：最小起播时刻
        def underrun(start):
            for k in range(n):
                if A[k] > start + k * c + 1e-12:
                    return True
            return False
        ok_at &= not underrun(T0)
        ok_below &= underrun(T0 - 1e-6)
    check('D14a', '13', 'prebuf', '起播时刻 T₀ = max_k(A_k − (k−1)c) 时不欠载（200 组）', 1.0, float(ok_at), 0.0)
    check('D14b', '13', 'prebuf', '早 1 微秒起播就欠载（该下界是紧的）', 1.0, float(ok_below), 0.0)


def d15():
    """扩频水印的检测：误报率与检出率"""
    g = rng(65); N, sx, alpha = 4000, 1.0, 0.04
    w = np.sign(g.standard_normal(N))
    reps = 40000
    x = g.standard_normal((reps, N)) * sx
    z0 = (x @ w) / (sx * np.sqrt(N))
    z1 = ((x + alpha * w) @ w) / (sx * np.sqrt(N))
    tau = 2.0
    check('D15a', '13', 'wm_det', '未加水印时的误报率 = Q(τ)', norm.sf(tau), np.mean(z0 > tau), 0.1, 'rel')
    check('D15b', '13', 'wm_det', '检出率 = Q(τ − α√N/σ)', norm.sf(tau - alpha * np.sqrt(N) / sx), np.mean(z1 > tau), 0.03, 'rel')


def d16():
    """串联链路的错误归因"""
    g = rng(66); n = 2_000_000
    e = np.array([0.02, 0.05, 0.03])
    fail = g.random((n, 3)) < e
    E = 1 - np.prod(1 - e)
    check('D16a', '15', 'chain_attr', '串联总错误率 E = 1 − Π(1−eᵢ)', E, np.mean(fail.any(1)), 0.02, 'rel')
    for i in range(3):
        f2 = fail.copy(); f2[:, i] = False
        pred = 1 - (1 - E) / (1 - e[i])
        check('D16b', '15', 'chain_attr', '把第 %d 环节换成"完美"后的错误率' % (i + 1), pred, np.mean(f2.any(1)), 0.02, 'rel')


def d17():
    """配对比较的方差：2σ²(1−ρ)/n"""
    g = rng(67); n, s, reps = 300, 1.0, 20000
    for rho in (0.0, 0.5, 0.9):
        C = np.array([[1, rho], [rho, 1]]) * s ** 2
        L = np.linalg.cholesky(C)
        z = g.standard_normal((reps, n, 2)) @ L.T
        d = (z[..., 0] - z[..., 1]).mean(1)
        check('D17', '15', 'paired', '配对差均值的方差（ρ=%g）' % rho, 2 * s ** 2 * (1 - rho) / n, d.var(), 0.04, 'rel')


def d18():
    """ADC 载荷：量化噪声与削波噪声的折中"""
    g = rng(68); n = 1_500_000; N = 8
    xg = g.standard_normal(n)
    xl = g.laplace(0, 1 / np.sqrt(2), n)                                        # 方差 1
    def sim(x, A):
        D = 2 * A / 2 ** N
        y = np.clip(np.round(x / D) * D, -A, A)
        return np.mean((x - y) ** 2)
    def pred_g(A):
        return (2 * A / 2 ** N) ** 2 / 12 + 2 * ((1 + A ** 2) * norm.sf(A) - A * norm.pdf(A))
    def pred_l(A):
        return (2 * A / 2 ** N) ** 2 / 12 + np.exp(-np.sqrt(2) * A)
    db = lambda d: -10 * np.log10(d)
    for A in (2.0, 3.0, 4.0, 5.0):
        check('D18a', '16', 'adc_load', '高斯信号的 SNR（dB），载荷 A=%gσ' % A, db(pred_g(A)), db(sim(xg, A)), 0.25)
    for A in (3.0, 5.0, 7.0):
        check('D18b', '16', 'adc_load', '拉普拉斯信号（语音的常用模型）的 SNR（dB），A=%gσ' % A, db(pred_l(A)), db(sim(xl, A)), 0.25)
    grid = np.linspace(1.5, 9, 31)
    check('D18c', '16', 'adc_load', '最优载荷：闭式与仿真的网格 argmin（σ 的倍数）', grid[np.argmin([pred_l(a) for a in grid])], grid[np.argmin([sim(xl, a) for a in grid])], 0.5)


def d19():
    """Kaiser 窗设计：阶数与阻带衰减"""
    from scipy.signal import firwin, freqz
    for A in (60, 80, 100):
        dw = 0.05 * np.pi                                                       # 过渡带宽（rad/sample）
        Nt = int(np.ceil((A - 7.95) / (2.285 * dw))) + 1
        Nt += (Nt % 2 == 0)
        beta = 0.1102 * (A - 8.7) if A > 50 else 0
        fc = 0.5 * np.pi / np.pi
        h = firwin(Nt, 0.5, window=('kaiser', beta))                            # 截止 0.5（相对奈奎斯特）
        w, H = freqz(h, worN=8192)
        stop = np.abs(H[w >= 0.5 * np.pi + dw / 2])
        att = -20 * np.log10(stop.max())
        check('D19', '17', 'kaiser', '按 Kaiser 经验式设计 A=%d dB，实测阻带衰减不低于 A−2 dB（实测 %.1f）' % (A, att), A - 2, att, 0.0, 'ge')


def d20():
    """时钟漂移的估计：斜率估计量的方差"""
    g = rng(69); T = 0.02; reps = 6000
    for N, sig in ((200, 2e-4), (1000, 2e-4)):
        k = np.arange(N); tk = k * T
        pred = sig ** 2 / np.sum((tk - tk.mean()) ** 2)
        d = 30e-6
        est = []
        for _ in range(reps):
            ts = k * T * (1 + d) + g.standard_normal(N) * sig
            est.append(np.polyfit(tk, ts, 1)[0] - 1)
        est = np.array(est)
        check('D20a', '17', 'drift_est', '漂移估计的方差 σ²/Σ(t−t̄)²（ppm²，N=%d）' % N, pred * 1e12, est.var() * 1e12, 0.06, 'rel')
        check('D20b', '17', 'drift_est', '漂移估计无偏（N=%d，偏差/ppm）' % N, 30.0, est.mean() * 1e6, 3.0)


_old_run = run
def run():
    _old_run()
    for f in (d13, d14, d15, d16, d17, d18, d19, d20):
        f()


# ════════ 第三批（D21–D34）：架构、传输、文本中枢、文本前端、指标、算例复核 ════════
def d21():
    """STFT-OLA 流式处理的算法延迟 = W − H，级联相加"""
    g = rng(71)
    def ola_stream(x, W, H):
        w = np.sqrt(np.hanning(W + 1)[:-1])                                     # 周期 sqrt-Hann：分析×合成 = Hann，满足 COLA
        buf = np.zeros(W); ob = np.zeros(W); out = []
        for s in range(0, len(x) - H + 1, H):
            buf = np.concatenate((buf[H:], x[s:s + H]))
            fr = np.fft.irfft(np.fft.rfft(buf * w))                             # 恒等处理
            ob = ob + fr * w
            out.append(ob[:H].copy() * (2 * H / W))                      # Σ Hann(hop H) = W/(2H)，归一化
            ob = np.concatenate((ob[H:], np.zeros(H)))
        return np.concatenate(out)
    x = g.standard_normal(60000)
    def lag(y):
        n = min(len(x), len(y))
        c = np.correlate(y[:n], x[:n], 'full'); return int(np.argmax(c)) - (n - 1)
    y1 = ola_stream(x, 512, 256)
    check('D21a', '14', 'ola_delay', '单级 STFT-OLA（W=512, H=256）的延迟 = W−H（样点）', 256, lag(y1), 0.0)
    y2 = ola_stream(y1, 480, 160)
    check('D21b', '14', 'ola_delay', '两级级联（再接 W=480, H=160）的总延迟 = Σ(Wᵢ−Hᵢ)', 256 + 320, lag(y2), 0.0)
    n = min(len(x), len(y2)); sl = slice(2000, n - 2000)
    check('D21c', '14', 'ola_delay', '恒等处理的重建误差（延迟对齐后，dB）', -200.0, 10 * np.log10(np.mean((np.roll(y2, -(256 + 320))[:n][sl] - x[:n][sl]) ** 2) + 1e-30), 0.0, 'le')


def d22():
    """CUSUM：检测延迟 ≈ h/I，误报间隔 ≥ e^h"""
    g = rng(72); mu, sg = 1.0, 1.0; I = mu ** 2 / (2 * sg ** 2)
    def run(h, shift, maxn=200000):
        s = 0.0; t = 0
        while t < maxn:
            t += 1
            x = g.standard_normal() * sg + (mu if shift else 0.0)
            s = max(0.0, s + (mu / sg ** 2) * (x - mu / 2))
            if s > h: return t
        return maxn
    for h in (4.0, 6.0):
        d = np.mean([run(h, True) for _ in range(4000)])
        check('D22a', '14', 'cusum', '均值突变后的平均检测延迟 ≈ (h + 过冲)/I（h=%g）' % h, h / I, d, 0.35, 'rel')
    arl0 = np.mean([run(4.0, False) for _ in range(800)])
    check('D22b', '14', 'cusum', '误报的平均间隔不低于 e^h（h=4）', np.exp(4.0), arl0, 0.0, 'ge')


def d23():
    """抖动缓冲：延迟目标 μ+kσ 的迟到率"""
    g = rng(73); n = 6_000_000; mu, sg = 40.0, 10.0
    xg = g.normal(mu, sg, n)
    for k in (2.0, 3.0):
        check('D23a', '18', 'jit_late', '高斯抖动：迟到率 = Q(k)（k=%g）' % k, norm.sf(k), np.mean(xg > mu + k * sg), 0.06, 'rel')
    s2 = np.log(1 + (sg / mu) ** 2); m2 = np.log(mu) - s2 / 2
    xl = g.lognormal(m2, np.sqrt(s2), n)                                       # 与高斯同均值同标准差的重尾分布
    late = np.mean(xl > mu + 3 * sg)
    check('D23b', '18', 'jit_late', '重尾（对数正态）下，同一 μ+3σ 的迟到率明显高于 Q(3)（≥ 1.5 倍）', 1.5 * norm.sf(3.0), late, 0.0, 'ge')


def d24():
    """交织把突发丢包变成近似独立丢包"""
    g = rng(74); n = 4_000_000
    p, r = 0.02, 0.25; pi_b = p / (p + r)
    u = g.random(n); st = np.zeros(n, dtype=bool); s = False
    for i in range(n):
        s = (u[i] < p) if not s else (u[i] >= r)
        st[i] = s
    nn, kk = 10, 8
    pred = sum(comb(nn, i) * pi_b ** i * (1 - pi_b) ** (nn - i) for i in range(nn - kk + 1, nn + 1))
    def fail_rate(D):
        blk = nn * D; m = n // blk
        a = st[:m * blk].reshape(m, nn, D)                                    # 第 i 个码字取每隔 D 个包的 nn 个
        lost = a.sum(1)                                                       # [m, D]
        return np.mean(lost > nn - kk)
    f1, f64 = fail_rate(1), fail_rate(64)
    check('D24a', '18', 'interleave', '交织深度 64：失败率接近独立丢包的二项右尾', pred, f64, 0.15, 'rel')
    check('D24b', '18', 'interleave', '不交织（深度 1）：失败率与独立假设显著不同（相对差 ≥ 20%）', 0.2, abs(f1 - pred) / pred, 0.0, 'ge')


def d25():
    """n-best 置信度的温度标定：最大似然恢复真温度"""
    from scipy.optimize import minimize_scalar
    g = rng(75); U, Nb, tau = 60000, 5, 2.0
    s = g.normal(0, 3.0, (U, Nb))
    p = np.exp(s / tau); p /= p.sum(1, keepdims=True)
    y = np.array([g.choice(Nb, p=pi) for pi in p[:20000]]); s = s[:20000]
    def nll(T):
        z = s / T; z = z - z.max(1, keepdims=True)
        lp = z - np.log(np.exp(z).sum(1, keepdims=True))
        return -lp[np.arange(len(y)), y].mean()
    T = minimize_scalar(nll, bounds=(0.3, 10), method='bounded').x
    check('D25a', '9', 'temp_cal', '温度标定：NLL 最小化恢复真温度 τ=2', tau, T, 0.04, 'rel')
    check('D25b', '9', 'temp_cal', '标定后的 NLL 低于未标定（T=1）', nll(1.0), nll(T), 0.0, 'le')


def d26():
    """对话状态的贝叶斯更新 = HMM 前向滤波；与暴力枚举一致"""
    g = rng(76); S, T = 3, 4
    Tm = g.dirichlet(np.ones(S), S)                                          # T[s'->s]
    b0 = g.dirichlet(np.ones(S))
    L = g.random((T, S)) + 0.05                                              # 每步观测似然 P(o_t|s)
    b = b0.copy()
    for t in range(T):
        b = L[t] * (Tm.T @ b); b = b / b.sum()
    tot = np.zeros(S)
    for path in product(range(S), repeat=T):
        pr = b0[path[0]] * 1.0
        # 与滤波一致的约定：先转移再观测
        pr = 1.0; prev = None
        for t, st in enumerate(path):
            pr *= (b0 @ Tm[:, st] if t == 0 else Tm[prev, st]) * L[t, st]
            prev = st
        tot[path[-1]] += pr
    tot /= tot.sum()
    check('D26', '9', 'belief', '信念更新（滤波递推）与暴力枚举联合分布的最大偏差', 0.0, float(np.max(np.abs(b - tot))), 1e-12)


def d27():
    """时长控制：总时长约束下的最小二乘分配"""
    from scipy.optimize import minimize
    g = rng(77); m = 14
    mu = g.uniform(8, 30, m); var = g.uniform(2, 20, m); Ttot = 1.25 * mu.sum()
    dc = mu + var * (Ttot - mu.sum()) / var.sum()
    res = minimize(lambda d: np.sum((d - mu) ** 2 / var), mu, constraints=({'type': 'eq', 'fun': lambda d: d.sum() - Ttot},), method='SLSQP', options={'ftol': 1e-14, 'maxiter': 500})
    check('D27a', '10', 'dur_alloc', '闭式分配 d = μ + σ²(T−Σμ)/Σσ² 与数值约束优化的最大偏差', 0.0, float(np.max(np.abs(dc - res.x))), 1e-4)
    check('D27b', '10', 'dur_alloc', '闭式解满足总时长约束', Ttot, dc.sum(), 1e-9)


def d28():
    """多音字消歧：贝叶斯最优的准确率 Φ(d'/2)"""
    g = rng(78); n = 3_000_000
    for dp in (1.0, 2.0, 3.0):
        y = g.random(n) < 0.5
        x = np.where(y, dp / 2, -dp / 2) + g.standard_normal(n)
        check('D28a', '10', 'bayes_acc', '单特征：准确率 Φ(d\'/2)（d\'=%g）' % dp, norm.cdf(dp / 2), np.mean((x > 0) == y), 0.003)
    ds = np.array([1.0, 1.0, 1.5, 0.5])                                       # 四个独立的上下文特征
    y = g.random(n) < 0.5
    X = np.where(y[:, None], ds / 2, -ds / 2) + g.standard_normal((n, len(ds)))
    llr = (X * ds).sum(1)                                                     # 对数似然比 ∝ Σ dₖ xₖ
    check('D28b', '10', 'bayes_acc', '四个独立特征：d\'² 相加，准确率 Φ(√Σdₖ²/2)', norm.cdf(np.sqrt(np.sum(ds ** 2)) / 2), np.mean((llr > 0) == y), 0.003)


def d29():
    """相关系数的 Fisher z 置信区间覆盖率"""
    g = rng(79); rho, n, reps = 0.8, 30, 20000
    C = np.array([[1, rho], [rho, 1]]); L = np.linalg.cholesky(C)
    cov = 0
    for _ in range(reps):
        z = g.standard_normal((n, 2)) @ L.T
        r = np.corrcoef(z.T)[0, 1]
        zz = np.arctanh(r); h = 1.96 / np.sqrt(n - 3)
        cov += (np.tanh(zz - h) <= rho <= np.tanh(zz + h))
    check('D29', '20', 'fisher_z', 'Fisher z 的 95% 置信区间的实际覆盖率（n=30, ρ=0.8）', 0.95, cov / reps, 0.01)


def d30():
    """SI-SDR：对尺度不变，且等于 10lg(cos²/(1−cos²))"""
    g = rng(80); n = 16000
    s = g.standard_normal(n); sh = 0.7 * s + 0.4 * g.standard_normal(n)
    def sisdr(sh, s):
        a = (sh @ s) / (s @ s); t = a * s; e = sh - t
        return 10 * np.log10((t @ t) / (e @ e))
    base = sisdr(sh, s)
    worst = max(abs(sisdr(c * sh, s) - base) for c in (0.01, 0.3, 4.0, -2.0, 100.0))
    check('D30a', '20', 'sisdr', 'SI-SDR 对估计信号的任意缩放不变（最大偏差，dB）', 0.0, worst, 1e-9)
    cs = (sh @ s) / (np.linalg.norm(sh) * np.linalg.norm(s))
    check('D30b', '20', 'sisdr', 'SI-SDR = 10·lg[cos²/(1−cos²)]（dB）', 10 * np.log10(cs ** 2 / (1 - cs ** 2)), base, 1e-9)


def d31():
    """COLA 条件与 STFT 重建"""
    N = 512; w = np.hanning(N + 1)[:-1]
    def ola_sum(win, H, p=1):
        acc = np.zeros(N * 8)
        for s in range(0, len(acc) - N + 1, H):
            acc[s:s + N] += win ** p
        mid = acc[N * 2:N * 6]
        return 20 * np.log10(mid.max() / mid.min())
    check('D31a', '1', 'cola', 'Hann 窗、50% 重叠：Σw 恒定（纹波，dB）', 0.0, ola_sum(w, N // 2), 1e-9)
    check('D31b', '1', 'cola', 'Hann 窗、75% 重叠：Σw² 恒定（纹波，dB）', 0.0, ola_sum(w, N // 4, 2), 1e-9)
    check('D31c', '1', 'cola', 'Hann 窗平方、50% 重叠：Σw² 不恒定（纹波 > 1 dB）', 1.0, ola_sum(w, N // 2, 2), 0.0, 'ge')


def d32():
    """算例复核 1：弥散场中的 DAS 指向性指数（蒙特卡洛合成扩散场）"""
    g = rng(82); M, d, c = 4, 0.035, 343.0
    pos = d * np.arange(M); K = 40; reps = 40000
    table = {250: 0.05, 500: 0.18, 1000: 0.72, 2000: 2.5, 4000: 5.21}
    for f, pred in table.items():
        k = 2 * np.pi * f / c
        cosT = g.uniform(-1, 1, (reps, K))                                     # 各向同性：cosθ 均匀；每个实现独立抽方向
        amp = cn(g, reps, K)
        X = (np.exp(-1j * k * pos[None, :, None] * cosT[:, None, :]) * amp[:, None, :]).sum(2)   # [reps, M]
        pw = np.mean(np.abs(X.mean(1)) ** 2)                                    # 目标在侧向：DAS 权为 1/M（无相位补偿）
        p1 = np.mean(np.abs(X) ** 2)
        di = 10 * np.log10(p1 / pw)
        check('D32', '21', 'das_di', '算例表：弥散场 DAS 的 DI（dB），%d Hz' % f, pred, di, 0.15)


def d33():
    """算例复核 2：维纳 / LSA / MMSE-STSA 增益，对后验做数值积分得到"""
    from scipy.special import i0e, expn, i1e
    xis = {-10: 0.1, -5: 10 ** -0.5, 0: 1.0, 5: 10 ** 0.5, 10: 10.0, 20: 100.0}
    for dB, xi in xis.items():
        ln, ls = 1.0, xi; gam = 1 + xi; R = np.sqrt(gam * ln)
        A = np.linspace(1e-6, R + 12 * np.sqrt(ln) + 6 * np.sqrt(ls), 400001)
        # p(A|R) ∝ p(R|A) p(A)，对相位边缘化后含 I0；用 i0e 做稳定化
        logp = np.log(2 * A / ls) - A ** 2 / ls + np.log(i0e(2 * R * A / ln)) + 2 * R * A / ln - (R ** 2 + A ** 2) / ln
        p = np.exp(logp - logp.max()); p /= np.trapezoid(p, A)
        g_stsa = np.trapezoid(A * p, A) / R
        g_lsa = np.exp(np.trapezoid(np.log(A) * p, A)) / R
        # 闭式（Ephraim–Malah）
        v = xi / (1 + xi) * gam
        G_stsa = (np.sqrt(np.pi) / 2) * (np.sqrt(v) / gam) * ((1 + v) * i0e(v / 2) + v * i1e(v / 2))
        G_lsa = xi / (1 + xi) * np.exp(0.5 * expn(1, v))
        check('D33a', '21', 'gain3', 'MMSE-STSA 增益：闭式 vs 后验数值积分（ξ=%d dB）' % dB, G_stsa, g_stsa, 0.003)
        check('D33b', '21', 'gain3', 'LSA 增益：闭式 vs 后验数值积分（ξ=%d dB）' % dB, G_lsa, g_lsa, 0.003)


def d34():
    """算例复核 3：L=2048 的 NLMS，ERLE 上界 = 10lg(10⁴/M)，M=μ/(2−μ)"""
    g = rng(84); L = 2048; sv = 0.01
    h = g.standard_normal(L) * np.exp(-np.arange(L) / 600.0); h /= np.linalg.norm(h)        # ‖h‖²=1 → 回声功率 1，噪声 1e-4（40 dB）
    for mu in (0.1, 0.5, 1.0):
        tau = L / (mu * (2 - mu)); N = int(18 * tau)
        x = g.standard_normal(N + L); v = g.standard_normal(N) * sv
        w = np.zeros(L); acc = []
        xv = x[:L][::-1].copy()
        for n in range(N):
            xv = x[n:n + L][::-1]
            e = xv @ (h - w) + v[n]
            w += mu * e * xv / (xv @ xv + 1e-12)
            if n >= int(0.9 * N):
                acc.append(np.sum((h - w) ** 2))
        erle = 10 * np.log10(1.0 / np.mean(acc))
        M = mu / (2 - mu)
        check('D34', '21', 'erle_bound', '算例表：NLMS 稳态 ERLE（dB），μ=%g' % mu, 10 * np.log10(1e4 / M), erle, 1.5)


_old_run2 = run
def run():
    _old_run2()
    for f in (d21, d22, d23, d24, d25, d26, d27, d28, d29, d30, d31, d32, d33, d34):
        f()


# ════════ 第四批（D35–D40）：功效、增益分配、插值、排队、RNN-T 格、谱损失 ════════
def d35():
    """配对比较的样本量与功效"""
    g = rng(91); sd, delta, alpha, power = 0.05, 0.01, 0.05, 0.8
    zA, zB = norm.isf(alpha / 2), norm.isf(1 - power)
    n = int(np.ceil(((zA + zB) * sd / delta) ** 2))
    reps = 40000
    d = g.standard_normal((reps, n)) * sd + delta                               # 逐句差，真实差距 Δ
    z = d.mean(1) / (sd / np.sqrt(n))
    check('D35a', '15', 'power_n', '按公式取样本量 n 时，检验功效 ≈ 0.80', 0.80, np.mean(z > zA), 0.02)
    z0 = (g.standard_normal((reps, n)) * sd).mean(1) / (sd / np.sqrt(n))
    check('D35b', '15', 'power_n', '无真实差距时的假阳性率 = α/2（单侧）', alpha / 2, np.mean(z0 > zA), 0.1, 'rel')
    n2 = int(np.ceil(((zA + zB) * sd / (delta / 2)) ** 2))
    check('D35c', '15', 'power_n', '要分辨的差距减半，所需样本量约 ×4', 4.0, n2 / n, 0.05)


def d36():
    """增益分配：输入等效噪声 = σm² + σq²/G²"""
    g = rng(92); N, A = 8, 1.0; D = 2 * A / 2 ** N; sm = 0.006
    n = 3_000_000
    base = g.standard_normal(n) * sm
    for G in (1, 2, 4, 8):
        y = np.clip(np.round(G * base / D) * D, -A, A) / G
        pred = sm ** 2 + (D ** 2 / 12) / G ** 2
        check('D36', '16', 'gain_stage', '输入等效噪声（dB re 满量程），σm²+σq²/G²，G=%d' % G, 10 * np.log10(pred), 10 * np.log10(np.mean(y ** 2)), 0.1)


def d37():
    """线性插值的误差：SNR ≈ 10lg(120/ω⁴)"""
    g = rng(93); fs = 16000.0; n = 400000
    for f, tol in ((500, 0.6), (1000, 0.6), (2000, 1.0)):
        w = 2 * np.pi * f / fs
        k = g.integers(100, 100000, n); al = g.random(n)
        x = lambda t: np.sin(w * t + 0.3)
        true = x(k + al); lin = (1 - al) * x(k) + al * x(k + 1)
        snr = 10 * np.log10(np.mean(true ** 2) / np.mean((true - lin) ** 2))
        check('D37', '17', 'lin_interp', '线性插值重采样的信噪比（dB），%d Hz' % f, 10 * np.log10(120 / w ** 4), snr, tol)


def d38():
    """排队论：M/M/1 的逗留时间 ~ Exp(μ−λ)"""
    g = rng(94); n = 2_000_000; mu = 1.0
    for rho in (0.5, 0.8):
        lam = rho * mu
        A = g.exponential(1 / lam, n); S = g.exponential(1 / mu, n)
        W = np.zeros(n); w = 0.0
        for i in range(1, n):
            w = max(0.0, w + S[i - 1] - A[i]); W[i] = w
        T = W + S
        check('D38a', '18', 'mm1', 'M/M/1 平均逗留时间 1/(μ−λ)（ρ=%g）' % rho, 1 / (mu - lam), T.mean(), 0.04, 'rel')
        check('D38b', '18', 'mm1', 'M/M/1 逗留时间的 99 分位 = ln100/(μ−λ)（ρ=%g）' % rho, np.log(100) / (mu - lam), np.quantile(T, 0.99), 0.05, 'rel')


def d39():
    """RNN-T 格：路径数 C(T+U−1,U)，前向算法 = 暴力枚举"""
    g = rng(95); T, U, V = 4, 3, 4
    lab = [1, 3, 2]
    Pk = g.dirichlet(np.ones(V), (T, U + 1))                                      # P(k | t, u)
    # 暴力枚举：在 (t,u) 处发出 blank(0) → (t+1,u)；发出 lab[u] → (t,u+1)；终止：(T−1,U) 处发出 blank
    tot = 0.0; npaths = 0
    def rec(t, u, pr):
        nonlocal tot, npaths
        if t == T - 1 and u == U:
            tot += pr * Pk[t, u, 0]; npaths += 1; return
        if t < T - 1:
            rec(t + 1, u, pr * Pk[t, u, 0])
        if u < U:
            rec(t, u + 1, pr * Pk[t, u, lab[u]])
    rec(0, 0, 1.0)
    al = np.zeros((T, U + 1)); al[0, 0] = 1.0
    for t in range(T):
        for u in range(U + 1):
            if t == 0 and u == 0: continue
            v = 0.0
            if t > 0: v += al[t - 1, u] * Pk[t - 1, u, 0]
            if u > 0: v += al[t, u - 1] * Pk[t, u - 1, lab[u - 1]]
            al[t, u] = v
    fw = al[T - 1, U] * Pk[T - 1, U, 0]
    check('D39a', '23', 'rnnt_lat', 'RNN-T 前向递推 = 暴力枚举全部对齐路径的概率和', tot, fw, 1e-12)
    check('D39b', '23', 'rnnt_lat', '对齐路径数 = C(T+U−1, U)', comb(T + U - 1, U), npaths, 0.0)


def d40():
    """谱损失的尺度：Σ|STFT|² = N_fft·(Σw²/H)·‖x‖²"""
    g = rng(96); Nf, H = 1024, 256; w = np.hanning(Nf + 1)[:-1]
    x = g.standard_normal(800000)
    nfr = 1 + (len(x) - Nf) // H
    idx = np.arange(Nf)[None] + H * np.arange(nfr)[:, None]
    X = np.fft.fft(x[idx] * w, axis=1)
    lhs = np.sum(np.abs(X) ** 2)
    pred = Nf * (np.sum(w ** 2) / H) * np.sum(x ** 2)
    check('D40a', '23', 'stft_parseval', 'Σ|STFT|² = N_fft·(Σw²/H)·‖x‖²（边缘帧忽略，相对偏差）', pred, lhs, 0.01, 'rel')
    check('D40b', '23', 'stft_parseval', 'Hann：Σw² = 3W/8', 3 * Nf / 8, np.sum(w ** 2), 1e-9)
    y = 0.7 * x
    lm = lambda a: np.log(np.abs(np.fft.rfft(a[idx] * w, axis=1)) + 1e-9)
    check('D40c', '23', 'stft_parseval', '对数幅度损失对整体增益的响应：增益 c 引起的平移 = ln c', np.log(0.7), float(np.mean(lm(y) - lm(x))), 1e-3)


_old_run3 = run
def run():
    _old_run3()
    for f in (d35, d36, d37, d38, d39, d40):
        f()
