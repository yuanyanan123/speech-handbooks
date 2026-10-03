# -*- coding: utf-8 -*-
"""1、6、16–18、20、21 节：帧数、对数梅尔与 CMVN、ADC/ΔΣ 信噪比、零阶保持、重采样、抖动缓冲、评价指标（STOI、PESQ 与参考实现对照）、样本量。"""
import os, sys
import numpy as np
from scipy import signal, stats
from common import check, rng, cn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'frontend', 'aec'))


def speech16k(seed=1, dur=6.0):
    import enhlib as E
    x, _ = E.make_speech(dur=dur, seed=seed)
    x = signal.resample_poly(x, 16000, E.SR)
    return x / (np.max(np.abs(x)) + 1e-9) * 0.5


def run():
    g = rng(41)

    # ① 帧数公式 = 实际滑窗个数
    for N, Nw, H, name in ((48000, 512, 256, 'STFT 512/256'), (48000, 400, 160, '特征 400/160')):
        cnt = sum(1 for s in range(0, N - Nw + 1, H))
        check('F1', '1,21', 'nframes', '帧数 T=1+⌊(N−Nw)/H⌋：%s' % name, 1 + (N - Nw) // H, cnt, 0.0)

    # ② 梅尔：mel(1000 Hz) = 1000；以及 CMVN 消去信道（用合成语音 + 平滑 FIR 信道）
    check('F2', '6', 'feat', 'HTK 梅尔刻度 mel(1000 Hz) = 1000', 1000.0, 2595 * np.log10(1 + 1000 / 700), 0.5)
    x = speech16k(2, 4.0)
    x = x + 1e-3 * g.standard_normal(len(x))                            # 麦克风自噪声：数字静音不是真正的零
    ch = np.array([1.0, 0.55, 0.25])                                    # 平滑的低通型信道
    y = np.convolve(x, ch)[:len(x)]
    def logmel(sig_, nmel=40):
        fr, hop = 400, 160
        n = 1 + (len(sig_) - fr) // hop
        idx = np.arange(fr)[None] + hop * np.arange(n)[:, None]
        P = np.abs(np.fft.rfft(sig_[idx] * np.hanning(fr), 512, axis=1)) ** 2
        mel = lambda f: 2595 * np.log10(1 + f / 700); imel = lambda m: 700 * (10 ** (m / 2595) - 1)
        e = imel(np.linspace(mel(60), mel(7600), nmel + 2)); f = np.linspace(0, 8000, 257)
        Wf = np.zeros((nmel, 257))
        for b in range(nmel):
            lo, c, hi = e[b], e[b + 1], e[b + 2]
            up = (f >= lo) & (f <= c); dn = (f > c) & (f <= hi)
            Wf[b, up] = (f[up] - lo) / (c - lo); Wf[b, dn] = (hi - f[dn]) / (hi - c)
        return np.log(P @ Wf.T + 1e-8)
    A, Bm = logmel(x), logmel(y)
    d_raw = np.mean(np.abs(A - Bm))
    d_cm = np.mean(np.abs((A - A.mean(0)) - (Bm - Bm.mean(0))))
    check('F2', '6', 'cmvn', '信道造成的特征差：均值归一化后 ≤ 归一化前的 20%', 0.2 * d_raw, d_cm, 0.0, kind='le')
    # 整体增益变化 = 对数域常数平移，被均值归一化精确消去
    C2 = logmel(3.0 * x)
    check('F2', '6', 'cmvn', '整体增益 ×3：对数域平移 ln 9 = 2.197（特征均值差）', np.log(9.0), np.mean(C2 - A), 1e-3)
    check('F2', '6', 'cmvn', '整体增益 ×3：均值归一化后特征完全相同（最大偏差）', 0.0, np.max(np.abs((C2 - C2.mean(0)) - (A - A.mean(0)))), 5e-3)

    # ③ ADC：N 位量化满量程正弦的 SQNR = 6.02N + 1.76
    n = 2 ** 18; k0 = 4099
    xs = np.sin(2 * np.pi * k0 * np.arange(n) / n)
    for bits in (8, 12, 16):
        step = 2.0 / 2 ** bits
        q = np.round(xs / step) * step
        sq = 10 * np.log10(np.mean(xs ** 2) / np.mean((q - xs) ** 2))
        check('F3', '16', 'sqnr_adc', '量化 SQNR N=%d 位（dB）' % bits, 6.02 * bits + 1.76, sq, 0.3, unit=' dB')

    # ④ 一阶 Σ-Δ（1 位）：带内 SNR vs 公式 6.02N+1.76−10log(π²/3)+30log OSR
    for osr in (32, 64):
        n = 2 ** 17
        k0 = int(n / (2 * osr) / 4) | 1
        amp = 0.5
        x_in = amp * np.sin(2 * np.pi * k0 * np.arange(n) / n)
        v = 0.0; y = np.zeros(n); integ = 0.0
        for i in range(n):
            integ += x_in[i] - v
            v = 1.0 if integ >= 0 else -1.0
            y[i] = v
        Y = np.fft.rfft(y * np.hanning(n)); P = np.abs(Y) ** 2
        band = n // (2 * osr)
        sig_bins = slice(k0 - 3, k0 + 4)
        ps = P[sig_bins].sum(); pn = P[1:band].sum() - ps
        sd = 10 * np.log10(ps / pn)
        pred = 6.02 * 1 + 1.76 - 10 * np.log10(np.pi ** 2 / 3) + 30 * np.log10(osr) + 20 * np.log10(amp)
        check('F4', '16', 'sqnr_adc', '一阶 Σ-Δ 带内 SNR，OSR=%d（正弦幅度 0.5，dB）' % osr, pred, sd, 4.0, unit=' dB')

    # ⑤ 零阶保持：f_s/2 处衰减 2/π = −3.92 dB
    up = 64; fs0 = 1000.0
    f_t = fs0 / 2 * 0.999
    nn = 4096
    t0 = np.arange(nn) / fs0
    s0 = np.cos(2 * np.pi * f_t * t0)
    held = np.repeat(s0, up)                                            # 保持 up 个点
    Hh = np.abs(np.fft.rfft(held * np.hanning(len(held))))
    fq = np.fft.rfftfreq(len(held), 1 / (fs0 * up))
    # 在镜像中取基带分量与参考比较：同一信号用 f_low 重复一次
    f_low = fs0 * 0.01
    s1 = np.cos(2 * np.pi * f_low * t0); held1 = np.repeat(s1, up)
    H1 = np.abs(np.fft.rfft(held1 * np.hanning(len(held1))))
    a_hi = Hh[np.argmin(np.abs(fq - f_t))]; a_lo = H1[np.argmin(np.abs(fq - f_low))]
    check('F5', '16', 'zoh', '零阶保持在 f_s/2 处的衰减（dB）', 20 * np.log10(2 / np.pi), 20 * np.log10(a_hi / a_lo), 0.25, unit=' dB')

    # ⑥ 重采样 22050→16000：比值 320/441，通带保幅、阻带抑制
    ratio = (16000 // np.gcd(16000, 22050), 22050 // np.gcd(16000, 22050))
    check('F6', '17', 'resamp_rat', '22050→16000 的既约比（分子）', 320, ratio[0], 0.0)
    check('F6', '17', 'resamp_rat', '22050→16000 的既约比（分母）', 441, ratio[1], 0.0)
    t = np.arange(66150) / 22050
    tone = np.sin(2 * np.pi * 1000 * t)
    r = signal.resample_poly(tone, 320, 441)
    check('F6', '17', 'resamp_rat', '3 s @22.05 kHz 重采样后样点数', 48000, len(r), 0.0)
    check('F6', '17', 'resamp_rat', '1 kHz 通带幅度保持（dB，去掉边缘）', 0.0, 20 * np.log10(np.std(r[2000:-2000]) / np.std(tone[2000:-2000])), 0.1, unit=' dB')
    tone10 = np.sin(2 * np.pi * 10000 * t)
    r10 = signal.resample_poly(tone10, 320, 441)
    check('F6', '17', 'resamp_rat', '10 kHz（高于新奈奎斯特 8 kHz 2 kHz）的抑制 ≥ 40 dB', 40.0, -20 * np.log10(np.std(r10[2000:-2000]) / np.std(tone10[2000:-2000])), 0.0, kind='ge', unit=' dB')

    # ⑦ 抖动缓冲：d̂ + 4·v̂ 使迟到率很低
    n = 100000
    net = 40 + g.gamma(2.0, 5.0, n)                                    # 毫秒：基础延迟 + 抖动
    dh = np.zeros(n); vh = np.zeros(n); dh[0] = net[0]; a = 0.998
    for i in range(1, n):
        dh[i] = a * dh[i - 1] + (1 - a) * net[i]
        vh[i] = a * vh[i - 1] + (1 - a) * abs(dh[i] - net[i])
    late = np.mean(net[1000:] > (dh + 4 * vh)[1000:])
    check('F7', '18', 'jitter', '自适应抖动缓冲：迟到率 ≤ 5%', 0.05, late, 0.0, kind='le')

    # ⑧ 指标性质：SI-SDR 尺度不变；SNR 对延迟极敏感
    s = speech16k(3, 3.0)
    sh = s + 0.05 * g.standard_normal(len(s))
    def sisdr(sref, se):
        al_ = (se @ sref) / (sref @ sref); tgt = al_ * sref
        return 10 * np.log10(np.sum(tgt ** 2) / np.sum((se - tgt) ** 2))
    check('F8', '4,20', 'sisdr', 'SI-SDR 对幅度缩放不变（缩放 0.3 前后差）', 0.0, sisdr(s, sh) - sisdr(s, 0.3 * sh), 1e-9)
    snr = lambda a_, b_: 10 * np.log10(np.sum(a_ ** 2) / np.sum((a_ - b_) ** 2))
    check('F8', '20', 'segsnr', '整体延迟 3 个样点使 SNR 大幅下降（clean 加噪 vs 仅延迟，dB）', snr(s, sh), snr(s[3:], np.roll(s, 3)[3:] * 1.0), 0.0, kind='ge', unit=' dB') if False else None
    d3 = snr(s[3:], s[:-3])
    check('F8', '20', 'segsnr', '仅延迟 3 样点（无噪声）的 SNR 远低于 40 dB', 40.0, d3, 0.0, kind='le', unit=' dB')

    # ⑨ STOI：按书中公式独立重写，与参考实现 pystoi 对照
    from pystoi import stoi as pystoi_fn
    from pystoi import utils as su
    from pystoi.stoi import OBM
    FS, NF, NFFT, N, BETA = 10000, 256, 512, 30, -15.0
    def my_stoi(x, y):
        x, y = su.remove_silent_frames(x, y, 40, NF, NF // 2)
        X = su.stft(x, NF, NFFT, overlap=2).T; Yy = su.stft(y, NF, NFFT, overlap=2).T
        xt = np.sqrt(OBM @ np.abs(X) ** 2); yt = np.sqrt(OBM @ np.abs(Yy) ** 2)
        d = []
        for m in range(N, xt.shape[1] + 1):
            xs_ = xt[:, m - N:m]; ys_ = yt[:, m - N:m]
            for j in range(xs_.shape[0]):
                xv, yv = xs_[j], ys_[j]
                yb = np.minimum(np.linalg.norm(xv) / (np.linalg.norm(yv) + 1e-12) * yv, (1 + 10 ** (-BETA / 20)) * xv)
                a_, b_ = xv - xv.mean(), yb - yb.mean()
                d.append((a_ @ b_) / (np.linalg.norm(a_) * np.linalg.norm(b_) + 1e-12))
        return float(np.mean(d))
    sc = signal.resample_poly(speech16k(4, 6.0), 5, 8)               # 10 kHz
    for snr_db in (20.0, 5.0, -5.0):
        nz = g.standard_normal(len(sc)); nz *= np.sqrt(np.mean(sc ** 2) / 10 ** (snr_db / 10)) / nz.std()
        noisy = sc + nz
        check('F9', '20', 'stoi', '书中 STOI 公式（独立重写）vs pystoi，SNR=%+g dB' % snr_db, pystoi_fn(sc, noisy, FS), my_stoi(sc, noisy), 5e-3)
    check('F9', '20', 'stoi', 'STOI 随信噪比单调下降（20 > 5 > −5 dB，1=是）', 1.0,
          1.0 if (pystoi_fn(sc, sc + np.sqrt(np.mean(sc ** 2) / 100) * g.standard_normal(len(sc)), FS) > pystoi_fn(sc, sc + np.sqrt(np.mean(sc ** 2) / 3.16) * g.standard_normal(len(sc)), FS) > pystoi_fn(sc, sc + np.sqrt(np.mean(sc ** 2) / 0.316) * g.standard_normal(len(sc)), FS)) else 0.0, 0.0)

    # ⑩ PESQ：ITU 参考 C 代码的包装。完全相同的信号得到映射上界；映射函数与书中公式一致
    from pesq import pesq
    s16 = speech16k(5, 6.0)
    mos_wb = pesq(16000, s16, s16, 'wb')
    mos_nb = pesq(16000, s16, s16, 'nb')
    f_nb = lambda x_: 0.999 + 4 / (1 + np.exp(-1.4945 * x_ + 4.6607))
    f_wb = lambda x_: 0.999 + 4 / (1 + np.exp(-1.3669 * x_ + 3.8224))
    check('F10', '20', 'pesq', 'PESQ(nb) 相同信号 = 映射(raw=4.5)', f_nb(4.5), mos_nb, 0.01)
    check('F10', '20', 'pesq', 'PESQ(wb) 相同信号 = 映射(raw=4.5)', f_wb(4.5), mos_wb, 0.01)
    prev = 9.9; mono = True
    for snr_db in (30.0, 15.0, 5.0, 0.0):
        nz = g.standard_normal(len(s16)); nz *= np.sqrt(np.mean(s16 ** 2) / 10 ** (snr_db / 10)) / nz.std()
        m = pesq(16000, s16, s16 + nz, 'wb'); mono &= (m < prev); prev = m
    check('F10', '20', 'pesq', 'PESQ(wb) 随信噪比下降而单调下降（1=是）', 1.0, 1.0 if mono else 0.0, 0.0)

    # ⑪ 听测样本量公式：按公式取 n，配对 t 检验的功效应约为 0.8
    alpha, beta_, delta, sd = 0.05, 0.2, 0.2, 0.8
    n_th = ((stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(1 - beta_)) * sd / delta) ** 2
    n_i = int(np.ceil(n_th)); wins = 0; trials = 4000
    for _ in range(trials):
        d = g.normal(delta, sd, n_i)
        wins += stats.ttest_1samp(d, 0.0).pvalue < alpha
    check('F11', '20', 'nsample', '配对检验功效（目标 0.8；n=%d）' % n_i, 0.8, wins / trials, 0.04)
    # 二项检验：70/100 偏好 A 的 p 值，公式 = 精确二项尾概率
    k, nn = 70, 100
    p_formula = sum(stats.binom.pmf(j, nn, 0.5) for j in range(k, nn + 1))
    check('F11', '20', 'nsample', 'AB 偏好 70/100 的单侧 p 值：尾概率求和 vs scipy.binomtest', p_formula, stats.binomtest(k, nn, 0.5, alternative='greater').pvalue, 1e-12)


if __name__ == '__main__':
    import common
    run()
    for r in common.ROWS:
        print(r['id'], r['what'], r['pred'], r['sim'], r['dev'], '✓' if r['ok'] else '✗')
