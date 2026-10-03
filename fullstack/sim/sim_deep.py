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
