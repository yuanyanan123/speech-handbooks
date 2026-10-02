# -*- coding: utf-8 -*-
"""3 节与 19 节：回声消除公式的仿真检验（NLMS 收敛与稳态、AP/RLS 等价关系、卡尔曼增益、相干性上界、时钟漂移估计）。"""
import numpy as np
from scipy import signal
from scipy.interpolate import CubicSpline
from common import check, rng, cn


def nlms_runs(L, mu, sv, iters, R=96, seed=3):
    g = rng(seed)
    h = g.standard_normal((R, L)) / np.sqrt(L)
    w = np.zeros((R, L))
    x = g.standard_normal((R, iters + L))
    v = sv * g.standard_normal((R, iters))
    mis = np.zeros(iters); mse = np.zeros(iters)
    for n in range(iters):
        xv = x[:, n:n + L][:, ::-1]
        e = np.sum(xv * (h - w), 1) + v[:, n]
        w = w + mu * (e / (np.sum(xv * xv, 1) + 1e-9))[:, None] * xv
        mis[n] = np.mean(np.sum((h - w) ** 2, 1)); mse[n] = np.mean(e ** 2)
    return mis, mse


def run():
    g = rng(2)
    # ① NLMS：时间常数与稳态额外误差（σᵥ 取 0.3，迭代 14τ，保证已到稳态）
    L, sv = 128, 0.3
    meas = {}
    for mu in (0.05, 0.1, 0.2, 0.5, 1.0):
        tau_th = L / (mu * (2 - mu))
        iters = int(14 * tau_th)
        mis, mse = nlms_runs(L, mu, sv, iters)
        d0 = mis[0]
        tau_sim = int(np.argmax(mis < d0 / np.e)) + 1
        ss_mse = np.mean(mse[-iters // 6:]) - sv ** 2
        meas[mu] = (tau_sim, ss_mse / sv ** 2)
        check('B1', '3,19', 'nlms_perf', 'NLMS 时间常数 μ=%g（样点）' % mu, tau_th, tau_sim, 0.12, kind='rel')
        check('B1', '3,19', 'nlms_rec', 'NLMS 稳态额外均方误差 μ=%g（相对 σᵥ²）' % mu, mu / (2 - mu), ss_mse / sv ** 2, 0.15, kind='rel')
    # ② 快与准的积：用仿真测得的 τ 与 M 相乘，比较不同 μ 之间的比值与公式预测的比值
    sim_prod = {mu: meas[mu][0] * meas[mu][1] for mu in (0.05, 0.1, 0.2)}
    th_prod = {mu: (L / (mu * (2 - mu))) * (mu / (2 - mu)) for mu in (0.05, 0.1, 0.2)}
    check('B2', '3,19', 'nlms_perf', 'τ·M 的最大/最小（μ 从 0.05 到 0.2，仿真 vs 公式）', max(th_prod.values()) / min(th_prod.values()),
          max(sim_prod.values()) / min(sim_prod.values()), 0.12, kind='rel')

    # ③ AP(P=1) 与 NLMS 逐步完全相同
    L2 = 16
    h = g.standard_normal(L2); xs = g.standard_normal(400 + L2); mu = 0.7
    wa = np.zeros(L2); wn = np.zeros(L2)
    for n in range(400):
        xv = xs[n:n + L2][::-1]
        y = xv @ h
        wn = wn + mu * (y - xv @ wn) / (xv @ xv + 1e-3) * xv
        X = xv[:, None]
        e = np.array([y]) - X.T @ wa
        wa = wa + mu * (X @ np.linalg.inv(X.T @ X + 1e-3 * np.eye(1)) @ e)
    check('B3', '3', 'ap', 'AP(P=1) 与 NLMS 的权重差', 0.0, np.linalg.norm(wa - wn), 1e-9)

    # ④ RLS（λ=1）等于批量最小二乘
    L3, N3 = 12, 600
    h = g.standard_normal(L3); xs = g.standard_normal(N3 + L3); noise = 0.1 * g.standard_normal(N3)
    Xm = np.stack([xs[n:n + L3][::-1] for n in range(N3)]); y = Xm @ h + noise
    w = np.zeros(L3); P = 1e6 * np.eye(L3)
    for n in range(N3):
        xv = Xm[n]; k = P @ xv / (1.0 + xv @ P @ xv)
        w = w + k * (y[n] - xv @ w); P = P - np.outer(k, xv @ P)
    w_ls = np.linalg.lstsq(Xm, y, rcond=None)[0]
    check('B4', '3', 'rls', 'RLS(λ=1) 与批量最小二乘的权重差', 0.0, np.linalg.norm(w - w_ls), 1e-4)

    # ⑤ 卡尔曼增益：数值最小化后验方差得到的 K 与闭式一致
    Pm, x, Phiv = 0.37, 0.8 + 0.6j, 0.5
    Ks = np.linspace(-2, 2, 801) + 0j
    Kg = np.array([a + 1j * b for a in np.linspace(-1.5, 1.5, 301) for b in np.linspace(-1.5, 1.5, 301)])
    Pk = np.abs(1 - Kg * x) ** 2 * Pm + np.abs(Kg) ** 2 * Phiv
    K_num = Kg[np.argmin(Pk)]
    K_th = Pm * np.conj(x) / (abs(x) ** 2 * Pm + Phiv)
    check('B5', '19', 'kalman_der', '卡尔曼增益：网格最小化 vs 闭式', 0.0, abs(K_num - K_th), 0.01)
    check('B5', '19', 'kalman_der', '更新后方差 P=(1−Kx)P⁻ vs 直接代入', (1 - K_th * x).real * Pm, np.min(Pk), 1e-3)
    # 跟踪一致性：随机游走路径，经验 MSE 与滤波器自报的 P 一致
    T = 60000; q = 1e-4; A = 1.0
    xs = cn(g, T); vs = np.sqrt(0.5) * cn(g, T); ws = np.sqrt(q) * cn(g, T)
    h = 0j; hh = 0j; P = 1.0; err = []; Ps = []
    for t in range(T):
        h = A * h + ws[t]
        Pp = A * A * P + q; hp = A * hh
        y = xs[t] * h + vs[t]
        K = Pp * np.conj(xs[t]) / (abs(xs[t]) ** 2 * Pp + 0.5)
        hh = hp + K * (y - xs[t] * hp); P = (1 - K * xs[t]).real * Pp
        if t > 2000:
            err.append(abs(h - hh) ** 2); Ps.append(P)
    check('B5', '19', 'kalman', '卡尔曼：经验 MSE / 滤波器自报方差', 1.0, np.mean(err) / np.mean(Ps), 0.06, kind='rel')

    # ⑥ 相干性上界：非线性回声下，最优线性滤波的 ERLE 与 −10log(1−γ²) 一致
    fs, N = 16000, 2 ** 19
    x = g.standard_normal(N)
    hr = g.standard_normal(64) * np.exp(-np.arange(64) / 20)
    xn = np.tanh(1.2 * x)                                              # 喇叭软限幅
    d = signal.lfilter(hr, [1], xn)
    Lf = 96
    Xm = np.stack([np.roll(x, k) for k in range(Lf)], 1)
    wls = np.linalg.lstsq(Xm[:200000], d[:200000], rcond=None)[0]
    dh = Xm @ wls
    erle_lin = 10 * np.log10(np.sum(d[Lf:] ** 2) / np.sum((d[Lf:] - dh[Lf:]) ** 2))
    f, Cxy = signal.coherence(x, d, fs=fs, nperseg=2048)
    f2, Sdd = signal.welch(d, fs=fs, nperseg=2048)
    bound = 10 * np.log10(np.sum(Sdd) / np.sum(Sdd * (1 - Cxy)))
    check('B6', '3,19', 'erle', '线性 ERLE 与相干性上界（dB）', bound, erle_lin, 0.7, unit=' dB')

    # ⑦ 时钟漂移：延迟随时间线性漂移，斜率 = ε·f_s（样点/秒）
    fs = 16000; T_s = 24; n = fs * T_s
    s = g.standard_normal(n + 200)
    eps = 50e-6
    t = np.arange(n) * (1 + eps) + 40                                  # 第二路的采样时刻被拉伸
    cs = CubicSpline(np.arange(len(s)), s)
    s2 = cs(t)
    s1 = s[40:40 + n]
    def delay(a, b):
        A, B = np.fft.rfft(a, 2 * len(a)), np.fft.rfft(b, 2 * len(b))
        cc = np.fft.irfft(A * np.conj(B) / (np.abs(A * B) + 1e-12))
        cc = np.concatenate([cc[-50:], cc[:50]]); i = int(np.argmax(cc))
        dd = 0.5 * (cc[i - 1] - cc[i + 1]) / (cc[i - 1] - 2 * cc[i] + cc[i + 1])
        return -(i - 50 + dd)
    seg = fs * 2
    d_early = delay(s1[:seg], s2[:seg]); d_late = delay(s1[-seg:], s2[-seg:])
    slope = (d_late - d_early) / ((n - seg) / fs)
    check('B7', '17', 'drift2', '时钟漂移 50 ppm 时延迟斜率（样点/秒）', eps * fs, abs(slope), 0.02, unit=' 样点/秒')


if __name__ == '__main__':
    import common
    run()
    for r in common.ROWS:
        print(r['id'], r['what'], r['pred'], r['sim'], r['dev'], '✓' if r['ok'] else '✗')
