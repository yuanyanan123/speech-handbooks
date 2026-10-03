# -*- coding: utf-8 -*-
"""4 节与 19 节：单通道降噪公式的蒙特卡洛检验（维纳最优、高斯后验、STSA/LSA 增益、语音存在概率、掩蔽目标、子空间）。"""
import numpy as np
from scipy import special as sp
from common import check, rng, cn


def g_w(xi):
    return xi / (1 + xi)


def g_stsa(xi, gam):
    v = xi / (1 + xi) * gam
    return (np.sqrt(np.pi) / 2) * (np.sqrt(v) / gam) * np.exp(-v / 2) * ((1 + v) * sp.i0(v / 2) + v * sp.i1(v / 2))


def g_lsa(xi, gam):
    v = xi / (1 + xi) * gam
    return xi / (1 + xi) * np.exp(0.5 * sp.exp1(v))


def run():
    g = rng(11)
    N = 3_000_000
    for xi_db in (-5.0, 0.0, 10.0):
        xi = 10 ** (xi_db / 10)
        S = np.sqrt(xi) * cn(g, N); Nn = cn(g, N); Y = S + Nn
        # ① 维纳：均方误差的极小点
        Gs = np.linspace(0.0, 1.0, 201)
        mse = np.array([np.mean(np.abs(S - G * Y) ** 2) for G in Gs])
        check('C1', '4,19', 'wiener_deriv', '维纳增益 argmin MSE @ξ=%+g dB' % xi_db, g_w(xi), Gs[np.argmin(mse)], 0.01)
        # ② 后验：条件均值系数与条件方差
        c = np.real(np.mean(S * np.conj(Y)) / np.mean(np.abs(Y) ** 2))
        check('C2', '19', 'gausscond', '后验均值系数 E[SY*]/E|Y|² = ξ/(1+ξ) @ξ=%+g dB' % xi_db, g_w(xi), c, 0.005)
        check('C2', '19', 'gausscond', '后验方差 E|S−G·Y|² = G·Φₙ @ξ=%+g dB' % xi_db, g_w(xi) * 1.0, np.mean(np.abs(S - c * Y) ** 2), 0.01)
        # ③ STSA / LSA 增益：在 |Y|² ≈ γ 的窄带内估计 E[|S|]/|Y| 与 exp(E[ln|S|])/|Y|
        for gam in (0.5, 1 + xi, 4.0):
            m = (np.abs(Y) ** 2 > gam * 0.95) & (np.abs(Y) ** 2 < gam * 1.05)
            if m.sum() < 5000:
                continue
            gs_sim = np.mean(np.abs(S[m])) / np.mean(np.abs(Y[m]))
            gl_sim = np.exp(np.mean(np.log(np.abs(S[m])) - np.log(np.abs(Y[m]))))
            check('C3', '4,19', 'mmse_stsa', 'STSA 增益 @ξ=%+g dB, γ=%.2f' % (xi_db, gam), g_stsa(xi, gam), gs_sim, 0.03, kind='rel')
            check('C3', '4,19', 'lsa_deriv', 'LSA 增益 @ξ=%+g dB, γ=%.2f' % (xi_db, gam), g_lsa(xi, gam), gl_sim, 0.03, kind='rel')
        # ④ 各增益的最优性：STSA 的幅度 MSE 最小，LSA 的对数幅度 MSE 最小；并检验 Wiener ≤ LSA ≤ STSA
        gam = np.abs(Y) ** 2
        A = np.abs(S); Ay = np.abs(Y)
        est = {'W': g_w(xi) * Ay, 'STSA': g_stsa(xi, gam) * Ay, 'LSA': g_lsa(xi, gam) * Ay}
        amp = {k: np.mean((A - v) ** 2) for k, v in est.items()}
        lg = {k: np.mean((np.log(A) - np.log(v + 1e-30)) ** 2) for k, v in est.items()}
        check('C4', '4', 'mmse_stsa', 'STSA 的幅度 MSE ≤ 维纳 @ξ=%+g dB' % xi_db, amp['W'], amp['STSA'], 1e-4, kind='le')
        check('C4', '4', 'lsa_deriv', 'LSA 的对数幅度 MSE ≤ 维纳、STSA @ξ=%+g dB' % xi_db, min(lg['W'], lg['STSA']), lg['LSA'], 1e-4, kind='le')
        ok_order = bool(np.all(g_w(xi) <= g_lsa(xi, gam) + 1e-12) and np.all(g_lsa(xi, gam) <= g_stsa(xi, gam) + 1e-9))
        check('C4', '4', 'lsa_deriv', '逐样本 维纳 ≤ LSA ≤ STSA 成立（1=是）@ξ=%+g dB' % xi_db, 1.0, 1.0 if ok_order else 0.0, 0.0)

    # ⑤ 语音存在概率：模拟 H0/H1 混合，在 γ 的分箱里统计 H1 的比例
    q, xi1 = 0.3, 10 ** (1.0)                                     # 先验 q，H1 下先验信噪比 10 dB
    Nn = 2_000_000
    h1 = g.random(Nn) < q
    Y = cn(g, Nn) * np.where(h1, np.sqrt(1 + xi1), 1.0)
    gam = np.abs(Y) ** 2
    for lo, hi in ((0.5, 0.7), (1.5, 2.0), (4.0, 5.0), (8.0, 10.0)):
        m = (gam > lo) & (gam < hi)
        gm = np.mean(gam[m])
        Lam = np.exp(xi1 / (1 + xi1) * gam[m]) / (1 + xi1)
        pred = np.mean(q * Lam / (q * Lam + 1 - q))
        check('C5', '4', 'spp', '语音存在概率，γ∈(%.1f,%.1f)' % (lo, hi), pred, np.mean(h1[m]), 0.02)

    # ⑥ 掩蔽目标：cIRM 精确还原；PSM 误差 ≤ IRM（带噪相位）
    S = cn(g, 200000); Nn = 0.7 * cn(g, 200000); Y = S + Nn
    cirm = S / Y
    check('C6', '4', 'masks', 'cIRM·Y 精确还原 S', 0.0, np.max(np.abs(cirm * Y - S)), 1e-9)
    irm = np.abs(S) ** 2 / (np.abs(S) ** 2 + np.abs(Nn) ** 2)
    psm = np.abs(S) / np.abs(Y) * np.cos(np.angle(S) - np.angle(Y))
    e_irm = np.mean(np.abs(S - irm * Y) ** 2); e_psm = np.mean(np.abs(S - psm * Y) ** 2)
    check('C6', '4', 'masks', 'PSM 的复谱误差 ≤ IRM(β=1)', e_irm, e_psm, 0.0, kind='le')
    ibm = (np.abs(S) ** 2 > np.abs(Nn) ** 2).astype(float)
    check('C6', '4', 'masks', 'IRM 的复谱误差 ≤ IBM', np.mean(np.abs(S - ibm * Y) ** 2), e_irm, 0.0, kind='le')

    # ⑦ 子空间法：μ=1 时等于 KLT 域维纳（逐特征值增益 λs/(λs+σ²)），且 μ>1 的误差更大
    d, r, T = 24, 4, 20000
    Bm = g.standard_normal((d, r))
    Rs = Bm @ Bm.T
    sig2 = 0.5
    s = np.linalg.cholesky(Rs + 1e-9 * np.eye(d)) @ g.standard_normal((d, T))
    y = s + np.sqrt(sig2) * g.standard_normal((d, T))
    lam, U = np.linalg.eigh(Rs)
    lam = np.maximum(lam, 0)
    def est(mu_):
        Gd = lam / (lam + mu_ * sig2)
        return U @ (Gd[:, None] * (U.T @ y))
    W = Rs @ np.linalg.inv(Rs + sig2 * np.eye(d))
    check('C7', '4', 'subspace', '子空间(μ=1)与矩阵维纳 Rs(Rs+σ²I)⁻¹ 的估计差', 0.0, np.max(np.abs(est(1.0) - W @ y)), 1e-8)
    check('C7', '4', 'subspace', 'μ=3 的 MSE ≥ μ=1 的 MSE', np.mean((est(1.0) - s) ** 2), np.mean((est(3.0) - s) ** 2), 0.0, kind='ge')


if __name__ == '__main__':
    import common
    run()
    for r in common.ROWS:
        print(r['id'], r['what'], r['pred'], r['sim'], r['dev'], '✓' if r['ok'] else '✗')
