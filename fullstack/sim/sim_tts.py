# -*- coding: utf-8 -*-
"""11–12 节与 19 节：合成与声码器公式的数值检验（回归到条件均值、流匹配边缘向量场与采样、DDPM 后验、ELBO、GAN 最优判别器、RVQ、WaveNet 感受野、μ 律、Griffin–Lim）。"""
import numpy as np
from scipy import signal, integrate, stats
from common import check, rng


def run():
    g = rng(31)

    # ① 回归到条件均值：双峰目标下 MSE 最优的确定性输出是均值，且 MSE = 方差 + 偏差²
    x = np.concatenate([g.normal(-1.5, 0.2, 50000), g.normal(1.5, 0.2, 50000)])
    fs = np.linspace(-2, 2, 801)
    mse = np.array([np.mean((x - f) ** 2) for f in fs])
    check('E1', '11', 'mse', 'MSE 回归的最优常数输出 = 条件均值', np.mean(x), fs[np.argmin(mse)], 0.01)
    f0 = 0.7
    check('E1', '11', 'mse', 'E(x−f)² = Var + (E x − f)²', np.var(x) + (np.mean(x) - f0) ** 2, np.mean((x - f0) ** 2), 1e-9)
    near = np.mean(np.abs(x - np.mean(x)) < 0.5)
    check('E1', '11', 'mse', '均值输出落在任一真实模式附近的比例（"糊"：几乎没有样本在均值附近）≤ 0.01', 0.01, near, 0.0, kind='le')

    # ② 流匹配：一维混合高斯。边缘向量场 v(x,t)=E[x1−x0|x_t=x]；回归估计 vs 数值积分；沿向量场积分得到数据分布
    w_k, m_k, s_k = np.array([0.5, 0.5]), np.array([-2.0, 2.0]), np.array([0.4, 0.4])
    X1 = np.linspace(-5, 5, 501)
    Q1 = sum(w * stats.norm.pdf(X1, m, s_) for w, m, s_ in zip(w_k, m_k, s_k))
    def v_marg(x, t):
        """向量化：对 x1 的数值积分计算 E[(x1−x)/(1−t) | x_t = x]（x_t=(1−t)x0+t·x1，x0~N(0,1)）"""
        x = np.atleast_1d(x).astype(float)
        out = np.empty_like(x)
        for i0 in range(0, len(x), 4000):
            xc = x[i0:i0 + 4000, None]
            lik = stats.norm.pdf(xc, t * X1[None, :], 1 - t)
            post = lik * Q1[None, :]
            post = post / np.trapezoid(post, X1, axis=1)[:, None]
            out[i0:i0 + 4000] = np.trapezoid(post * (X1[None, :] - xc) / (1 - t), X1, axis=1)
        return out
    # 样本回归（分箱）与积分的对比
    Ns = 600000
    x1s = np.where(g.random(Ns) < 0.5, g.normal(-2, 0.4, Ns), g.normal(2, 0.4, Ns))
    x0s = g.standard_normal(Ns)
    for t0 in (0.3, 0.7):
        xt = (1 - t0) * x0s + t0 * x1s; u = x1s - x0s
        for xc in ((-1.0, 0.0, 1.0) if t0 < 0.5 else (-1.4, 0.7, 1.4)):
            m = np.abs(xt - xc) < 0.05
            assert m.sum() >= 2000, '分箱样本太少'
            check('E2', '19', 'fm_marg', '边缘向量场 t=%.1f, x=%+.1f：分箱回归 vs 数值积分' % (t0, xc), float(v_marg(np.array([xc]), t0)[0]), np.mean(u[m]), 0.08, unit='')
    # 沿 v 积分（欧拉）：粒子分布 vs 目标
    P = 20000
    xp = g.standard_normal(P)
    for nfe in (4, 16, 64):
        z = xp.copy(); dt = 1.0 / nfe
        for k in range(nfe):
            t = k * dt
            z = z + dt * v_marg(z, min(t, 0.999))
        # 与目标混合高斯的 1-Wasserstein 近似（排序样本对比）
        tgt = np.where(g.random(P) < 0.5, g.normal(-2, 0.4, P), g.normal(2, 0.4, P))
        w1 = np.mean(np.abs(np.sort(z) - np.sort(tgt)))
        if nfe == 4: w4 = w1
        if nfe == 64: w64 = w1
        if nfe == 16: w16 = w1
        check('E2', '11', 'cfm', '流匹配采样 NFE=%d 的 W₁ 距离 ≤ 0.35' % nfe, 0.35, w1, 0.0, kind='le')
    check('E2', '11', 'cfm', 'NFE 增大，采样误差不增（W₁(64) ≤ W₁(4)）', w4, w64, 0.02, kind='le')

    # ③ DDPM 后验均值公式
    T = 50; betas = np.linspace(1e-3, 0.2, T); al = 1 - betas; ab = np.cumprod(al)
    t = 30
    N = 800000
    x0 = g.standard_normal(N) * 1.7 + 0.4
    eps = g.standard_normal(N)
    xt = np.sqrt(ab[t]) * x0 + np.sqrt(1 - ab[t]) * eps
    xprev = np.sqrt(ab[t - 1]) * x0 + np.sqrt(1 - ab[t - 1]) * g.standard_normal(N)
    xt2 = np.sqrt(al[t]) * xprev + np.sqrt(betas[t]) * g.standard_normal(N)       # 一步正向：x_{t-1} → x_t
    # 线性回归 x_{t-1} ~ a·x_t + b·x0 + c（联合高斯下条件均值精确线性）
    Xm = np.stack([xt2, x0, np.ones(N)], 1)
    coef = np.linalg.lstsq(Xm, xprev, rcond=None)[0]
    # 公式：μ̃ = (1/√α_t)(x_t − β_t/√(1−ᾱ_t) ε)，ε = (x_t − √ᾱ_t x0)/√(1−ᾱ_t)
    a_th = (1 / np.sqrt(al[t])) * (1 - betas[t] / (1 - ab[t]))
    b_th = (1 / np.sqrt(al[t])) * (betas[t] * np.sqrt(ab[t]) / (1 - ab[t]))
    check('E3', '19', 'ddpm_post', '后验均值对 xₜ 的系数', a_th, coef[0], 0.01)
    check('E3', '19', 'ddpm_post', '后验均值对 x₀ 的系数', b_th, coef[1], 0.01)
    res = xprev - Xm @ coef
    bt = betas[t] * (1 - ab[t - 1]) / (1 - ab[t])
    check('E3', '19', 'ddpm_post', '后验方差 β̃ₜ = βₜ(1−ᾱₜ₋₁)/(1−ᾱₜ)', bt, np.var(res), 0.02, kind='rel')

    # ④ ELBO：线性高斯模型，ELBO ≤ log p(x)，真后验处取等
    sig = 0.6
    def elbo(xv, a, s2):
        mu_q = a * xv
        e_loglik = -0.5 * np.log(2 * np.pi * sig ** 2) - ((xv - mu_q) ** 2 + s2) / (2 * sig ** 2)
        kl = 0.5 * (s2 + mu_q ** 2 - 1 - np.log(s2))
        return e_loglik - kl
    xv = 0.9
    logp = stats.norm.logpdf(xv, 0, np.sqrt(1 + sig ** 2))
    a_true, s2_true = 1 / (1 + sig ** 2), sig ** 2 / (1 + sig ** 2)
    check('E4', '11', 'elbo', 'ELBO 在真后验处等于 log p(x)', logp, elbo(xv, a_true, s2_true), 1e-12)
    worst = max(elbo(xv, a, s2) for a in np.linspace(-1, 2, 61) for s2 in np.linspace(0.05, 2, 40))
    check('E4', '11', 'elbo', '任意 q 下 ELBO ≤ log p(x)', logp, worst, 1e-12, kind='le')

    # ⑤ GAN 最优判别器与散度：D* = p/(p+q)；C(G) = −log4 + 2·JS
    xg = np.linspace(-12, 12, 40001)
    p = stats.norm.pdf(xg, 0, 1); qd = stats.norm.pdf(xg, 1.5, 1.2)
    Dst = p / (p + qd)
    val = lambda D: np.trapezoid(p * np.log(D) + qd * np.log(1 - D), xg)
    check('E5', '19', 'gan_opt', 'V(D*,G) = −log4 + 2·JS（数值积分）', -np.log(4) + 2 * (0.5 * np.trapezoid(p * np.log(2 * p / (p + qd)), xg) + 0.5 * np.trapezoid(qd * np.log(2 * qd / (p + qd)), xg)), val(Dst), 1e-6)
    check('E5', '19', 'gan_opt', '扰动判别器后 V 变小（D* 是最大化点）', val(Dst), val(np.clip(Dst * 0.9 + 0.05, 1e-9, 1 - 1e-9)), 0.0, kind='le')

    # ⑥ RVQ：逐级量化，残差能量逐级下降；码率算术
    d, Nv, K, Ncode = 16, 6000, 4, 64
    Z = g.standard_normal((Nv, d))
    res = Z.copy(); en = [np.mean(res ** 2)]
    for k in range(K):
        cb = res[g.choice(Nv, Ncode, replace=False)].copy()
        for _ in range(8):
            idx = np.argmin(((res[:, None, :] - cb[None]) ** 2).sum(2), 1)
            for c in range(Ncode):
                if np.any(idx == c):
                    cb[c] = res[idx == c].mean(0)
        idx = np.argmin(((res[:, None, :] - cb[None]) ** 2).sum(2), 1)
        res = res - cb[idx]; en.append(np.mean(res ** 2))
    check('E6', '12,19', 'rvq', 'RVQ 残差能量逐级下降（最小相邻降幅）', 0.0, min(-np.diff(en)), 0.0, kind='ge')
    check('E6', '12', 'bits', '码率算术：8 码本 × log₂1024 × 75 Hz', 6000.0, 8 * np.log2(1024) * 75, 1e-9)

    # ⑦ WaveNet 感受野 R = 1 + Σ(k−1)d_l：对扩张因果卷积堆叠做脉冲扰动
    def rf(kern, dils):
        n = 12000
        x = np.zeros(n); x[1000] = 1.0
        h = x.copy()
        for dl in dils:
            out = np.zeros(n)
            for j in range(kern):
                sh = j * dl
                out[sh:] += h[:n - sh] if sh > 0 else h
            h = out
        return int(np.count_nonzero(h > 0))
    dils = [2 ** i for i in range(10)]
    check('E7', '12', 'wavenet', '感受野：k=2，膨胀 1…512', 1 + sum((2 - 1) * d_ for d_ in dils), rf(2, dils), 0.0)
    dils3 = dils * 2
    check('E7', '12', 'wavenet', '感受野：k=3，膨胀 1…512 重复两次', 1 + sum((3 - 1) * d_ for d_ in dils3), rf(3, dils3), 0.0)

    # ⑧ μ 律：小幅信号下信噪比高于等间隔 8 位量化
    def quant_uniform(xv, bits):
        step = 2.0 / 2 ** bits
        return np.clip(np.round(xv / step) * step, -1, 1)
    def mu_c(xv, mu=255): return np.sign(xv) * np.log1p(mu * np.abs(xv)) / np.log1p(mu)
    def mu_e(yv, mu=255): return np.sign(yv) * ((1 + mu) ** np.abs(yv) - 1) / mu
    xs = np.clip(g.laplace(0, 0.02, 200000), -1, 1)
    snr = lambda a, b: 10 * np.log10(np.mean(a ** 2) / np.mean((a - b) ** 2))
    s_u = snr(xs, quant_uniform(xs, 8)); s_m = snr(xs, mu_e(quant_uniform(mu_c(xs), 8)))
    check('E8', '12', 'wavenet', 'μ 律 8 位 SNR ≥ 等间隔 8 位（小幅拉普拉斯信号，dB）', s_u, s_m, 0.0, kind='ge', unit=' dB')

    # ⑨ Griffin–Lim：谱一致性误差不增
    fs_ = 16000
    xr = g.standard_normal(fs_)
    _, _, X = signal.stft(xr, fs_, nperseg=512, noverlap=384)
    mag = np.abs(X)
    ph = np.exp(2j * np.pi * g.random(mag.shape))
    errs = []
    for it in range(40):
        Z = mag * ph
        _, z = signal.istft(Z, fs_, nperseg=512, noverlap=384)
        _, _, Zn = signal.stft(z, fs_, nperseg=512, noverlap=384)
        Zn = Zn[:, :mag.shape[1]]
        errs.append(np.linalg.norm(np.abs(Zn) - mag) / np.linalg.norm(mag))
        ph = np.exp(1j * np.angle(Zn))
    check('E9', '12', 'gl', 'Griffin–Lim 谱收敛误差不增（最大逆向增量）', 0.0, max(np.diff(errs)), 1e-6, kind='le')
    check('E9', '12', 'gl', 'Griffin–Lim 40 次迭代后误差低于首次的 70%', 0.7, errs[-1] / errs[0], 0.0, kind='le')


if __name__ == '__main__':
    import common
    run()
    for r in common.ROWS:
        print(r['id'], r['what'], r['pred'], r['sim'], r['dev'], '✓' if r['ok'] else '✗')
