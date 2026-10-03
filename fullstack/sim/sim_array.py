# -*- coding: utf-8 -*-
"""2 节：阵列公式的仿真检验（DAS 的 WNG、弥散场 DI、MVDR 的输出噪声功率与无失真、LCMV 的零陷、GCC-PHAT、MUSIC、GSC）。"""
import numpy as np
from common import check, rng, cn

C = 343.0


def steer(pos, u, f):
    return np.exp(-2j * np.pi * f * (pos @ u) / C)


def run():
    g = rng(1)
    M, D = 4, 0.035
    pos = np.stack([np.arange(M) * D, np.zeros(M), np.zeros(M)], 1)         # 线阵，沿 x 轴

    # ① DAS 对白噪声的增益 = M
    f = 1000.0
    u = np.array([np.cos(np.radians(60)), np.sin(np.radians(60)), 0])
    a = steer(pos, u, f)
    w = a / M
    N = 400000
    v = cn(g, M, N)                                    # 各通道独立白噪声
    out = w.conj() @ v
    wng = 10 * np.log10(1.0 / np.mean(np.abs(out) ** 2))
    check('A1', '2', 'das', 'DAS 对不相关噪声的增益（dB）', 10 * np.log10(M), wng, 0.05, unit=' dB')

    # ② 弥散场 DI：随机平面波叠加（球面均匀），与 sinc 相干闭式比较
    nd = 6000
    th = np.arccos(1 - 2 * g.random(nd)); ph = 2 * np.pi * g.random(nd)
    dirs = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], 1)
    for f in (500.0, 2000.0, 4000.0):
        A = np.exp(-2j * np.pi * f * (pos @ dirs.T) / C)           # M × nd
        Rn = (A @ A.conj().T) / nd                                  # 弥散场空间协方差（Monte Carlo）
        w0 = np.ones(M) / M                                         # 侧向目标 τ=0
        di_sim = 10 * np.log10(1.0 / np.real(w0 @ Rn @ w0))
        dd = np.abs(np.subtract.outer(np.arange(M), np.arange(M))) * D
        x = 2 * np.pi * f * dd / C
        G = np.where(x == 0, 1.0, np.sin(x) / np.where(x == 0, 1, x))
        di_pred = 10 * np.log10(1.0 / (w0 @ G @ w0))
        check('A2', '2', 'diffuse', '弥散场 DI @%d Hz（dB）' % f, di_pred, di_sim, 0.15, unit=' dB')

    # ③ MVDR：无失真、输出噪声功率 = 1/(aᴴΦ⁻¹a)；对比 DAS（方向性干扰 + 白噪声）
    f = 1000.0
    a = steer(pos, u, f)
    ui = np.array([np.cos(np.radians(120)), np.sin(np.radians(120)), 0])
    ai = steer(pos, ui, f)
    Phi = 10.0 * np.outer(ai, ai.conj()) + 0.1 * np.eye(M)         # 干扰 10 dB 高于噪声 20 dB
    Pinv = np.linalg.inv(Phi)
    w_mv = Pinv @ a / (a.conj() @ Pinv @ a)
    check('A3', '2', 'mvdr_res', 'MVDR 无失真 wᴴa = 1', 1.0, np.real(w_mv.conj() @ a), 1e-9)
    pred = np.real(1.0 / (a.conj() @ Pinv @ a))
    sim = np.real(w_mv.conj() @ Phi @ w_mv)
    check('A3', '2', 'mvdr_res', 'MVDR 输出噪声功率（闭式 vs wᴴΦw）', pred, sim, 1e-9)
    w_das = a / M
    p_das = np.real(w_das.conj() @ Phi @ w_das)
    check('A3', '2', 'mvdr_deriv', 'MVDR 输出噪声 ≤ DAS（最小方差，dB）', 10 * np.log10(p_das), 10 * np.log10(pred), 0.0, kind='le', unit=' dB')
    # 有限快拍：样本协方差下的 MVDR 仍然 ≤ DAS
    X = np.linalg.cholesky(Phi) @ cn(g, M, 200)
    Rs = X @ X.conj().T / 200
    ws = np.linalg.inv(Rs) @ a; ws = ws / (a.conj() @ ws)
    check('A3', '2', 'mvdr_res', '200 快拍样本协方差 MVDR 输出噪声 ≤ DAS', p_das, np.real(ws.conj() @ Phi @ ws), 0.0, kind='le')

    # ④ LCMV：对干扰方向置零且目标无失真
    Cm = np.stack([a, ai], 1)
    fvec = np.array([1.0, 0.0])
    Phi2 = np.eye(M) + 0.3 * (g.standard_normal((M, M)) + 1j * g.standard_normal((M, M)))
    Phi2 = Phi2 @ Phi2.conj().T
    P2 = np.linalg.inv(Phi2)
    w_l = P2 @ Cm @ np.linalg.inv(Cm.conj().T @ P2 @ Cm) @ fvec
    check('A4', '2', 'lcmv', 'LCMV 目标响应 = 1', 1.0, abs(w_l.conj() @ a), 1e-9)
    check('A4', '2', 'lcmv', 'LCMV 干扰响应 = 0', 0.0, abs(w_l.conj() @ ai), 1e-9)

    # ⑤ GCC-PHAT：已知分数延迟的恢复
    fs = 16000
    n = 16000 * 2
    s = g.standard_normal(n)
    true_tau = 2.37 / fs                                            # 2.37 个样点
    S = np.fft.rfft(s)
    freqs = np.fft.rfftfreq(n, 1 / fs)
    x1 = s + 0.1 * g.standard_normal(n)
    x2 = np.fft.irfft(S * np.exp(-2j * np.pi * freqs * true_tau), n) + 0.1 * g.standard_normal(n)
    X1, X2 = np.fft.rfft(x1), np.fft.rfft(x2)
    cross = X1 * np.conj(X2)
    ph = cross / np.abs(cross)
    nfft = 8 * n
    cc = np.fft.irfft(ph, nfft)
    lag = np.argmax(np.concatenate([cc[-200:], cc[:200]])) - 200
    # 抛物线插值亚样点
    cc2 = np.concatenate([cc[-200:], cc[:200]])
    i = lag + 200
    d = 0.5 * (cc2[i - 1] - cc2[i + 1]) / (cc2[i - 1] - 2 * cc2[i] + cc2[i + 1])
    est = -(lag + d) / 8.0                                           # 过采样 8 倍；符号约定与 x1·x2* 一致
    check('A5', '2', 'gcc', 'GCC-PHAT 估计的延迟（样点）', 2.37, abs(est), 0.05, unit=' 样点')

    # ⑥ MUSIC：单源方向估计
    f = 2000.0
    th0 = 60.0
    a0 = steer(pos, np.array([np.cos(np.radians(th0)), np.sin(np.radians(th0)), 0]), f)
    T = 500
    sig = cn(g, 1, T)
    Xs = np.outer(a0, sig[0]) + 0.3 * cn(g, M, T)
    R = Xs @ Xs.conj().T / T
    ev, E = np.linalg.eigh(R)
    En = E[:, :-1]                                                   # 噪声子空间（单源）
    grid = np.arange(0, 180.5, 0.5)
    P = []
    for t_ in grid:
        at = steer(pos, np.array([np.cos(np.radians(t_)), np.sin(np.radians(t_)), 0]), f)
        P.append(1.0 / np.real(at.conj() @ En @ En.conj().T @ at))
    check('A6', '2', 'music', 'MUSIC 估计方向（度，真值 60°）', th0, grid[int(np.argmax(P))], 1.5, unit='°')
    # 噪声子空间与导向矢量正交（无噪声时严格）
    R0 = np.outer(a0, a0.conj())
    ev0, E0 = np.linalg.eigh(R0)
    check('A6', '2', 'music', '无噪声时 ‖Eₙᴴa‖² = 0', 0.0, np.linalg.norm(E0[:, :-1].conj().T @ a0) ** 2, 1e-12)

    # ⑦ GSC：阻塞矩阵挡住目标；自适应部分收敛后输出噪声功率不高于固定波束
    a = steer(pos, u, 1000.0)
    Q, _ = np.linalg.qr(np.concatenate([a[:, None], g.standard_normal((M, M - 1)) + 0j], 1))
    B = Q[:, 1:]                                                      # 列与 a 正交
    check('A7', '2', 'gsc', 'GSC 阻塞矩阵 Bᴴa = 0', 0.0, np.linalg.norm(B.conj().T @ a), 1e-9)
    ai = steer(pos, ui, 1000.0)
    Ns = 20000
    noise = 3.0 * np.outer(ai, cn(g, 1, Ns)[0]) + 0.3 * cn(g, M, Ns)
    wq = a / M
    wa = np.zeros(M - 1, complex)
    for k in range(Ns):
        r = B.conj().T @ noise[:, k]
        z = wq.conj() @ noise[:, k] - wa.conj() @ r
        wa = wa + 0.05 * r * np.conj(z) / (np.linalg.norm(r) ** 2 + 1e-9)
    zq = wq.conj() @ noise
    za = wq.conj() @ noise - wa.conj() @ (B.conj().T @ noise)
    check('A7', '2', 'gsc', 'GSC 输出噪声功率 ≤ 固定波束（dB）', 10 * np.log10(np.mean(np.abs(zq) ** 2)), 10 * np.log10(np.mean(np.abs(za) ** 2)), 0.0, kind='le', unit=' dB')


if __name__ == '__main__':
    import common
    run()
    for r in common.ROWS:
        print(r['id'], r['what'], r['pred'], r['sim'], r['dev'], '✓' if r['ok'] else '✗')
