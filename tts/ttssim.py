#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全书统一的"合成语音"模拟器与共用工具。

   为什么不用真录音：这本手册里每个数都要能复算，而真语料既不能随书分发、
   也没有精确的基频 / 共振峰 / 音素边界真值。这里用源-滤波模型自己造一段，
   基频曲线、每个共振峰的轨迹、每个音素的起止样点全部是已知的——
   于是"梅尔谱丢了多少"、"对齐对了没有"这类问题才有客观答案。
"""
import numpy as np

SR = 22050          # 全书统一采样率（LJSpeech / HiFi-GAN 的标准）
NFFT = 1024         # 帧长 46.4 ms
HOP = 256           # 帧移 11.6 ms → 帧率 86.13 Hz
NMEL = 80
FMIN, FMAX = 0.0, 8000.0

# 五个元音的前三共振峰（Hz），男声中值
VOWELS = {
    'a': (730, 1090, 2440), 'i': (270, 2290, 3010), 'u': (300, 870, 2240),
    'e': (530, 1840, 2480), 'o': (570, 840, 2410),
}


def hz_to_mel(f):
    return 2595.0 * np.log10(1.0 + np.asarray(f, float) / 700.0)


def mel_to_hz(m):
    return 700.0 * (10.0 ** (np.asarray(m, float) / 2595.0) - 1.0)


def mel_fb(sr=SR, nfft=NFFT, nmel=NMEL, fmin=FMIN, fmax=FMAX, norm='slaney'):
    """标准三角梅尔滤波器组，(nmel, nfft//2+1)。"""
    fftf = np.fft.rfftfreq(nfft, 1.0 / sr)
    m = np.linspace(hz_to_mel(fmin), hz_to_mel(fmax), nmel + 2)
    f = mel_to_hz(m)
    fb = np.zeros((nmel, len(fftf)))
    for i in range(nmel):
        lo, ce, hi = f[i], f[i + 1], f[i + 2]
        left = (fftf - lo) / max(ce - lo, 1e-9)
        right = (hi - fftf) / max(hi - ce, 1e-9)
        fb[i] = np.maximum(0.0, np.minimum(left, right))
    if norm == 'slaney':                       # 等面积归一化
        fb *= (2.0 / (f[2:nmel + 2] - f[:nmel]))[:, None]
    return fb


def stft(x, nfft=NFFT, hop=HOP):
    w = np.hanning(nfft + 1)[:-1]
    idx = np.arange(0, len(x) - nfft + 1, hop)
    return np.array([np.fft.rfft(x[i:i + nfft] * w) for i in idx]).T   # (F,T)


def istft(S, nfft=NFFT, hop=HOP):
    w = np.hanning(nfft + 1)[:-1]
    T = S.shape[1]
    n = (T - 1) * hop + nfft
    y = np.zeros(n); wsum = np.zeros(n)
    for t in range(T):
        fr = np.fft.irfft(S[:, t], nfft) * w
        y[t * hop:t * hop + nfft] += fr
        wsum[t * hop:t * hop + nfft] += w ** 2
    return y / np.maximum(wsum, 1e-8)


def formant_filter(x, F, BW, sr=SR):
    """把信号过一串二阶共振峰（每个共振峰一个极点对），F/BW 可随时间变化。"""
    y = x.copy()
    n = len(x)
    for k in range(F.shape[0]):
        out = np.zeros(n)
        z1 = z2 = 0.0
        f = F[k]; bw = BW[k]
        r = np.exp(-np.pi * bw / sr)
        th = 2 * np.pi * f / sr
        a1 = 2 * r * np.cos(th); a2 = -(r ** 2)
        g = (1 - a1 - a2)                      # 直流增益归一
        for i in range(n):
            v = g[i] * y[i] + a1[i] * z1 + a2[i] * z2
            z2 = z1; z1 = v
            out[i] = v
        y = out
    return y


def glottal(n, f0, sr=SR, jitter=0.012, seed=0):
    """声门脉冲串：按瞬时基频打脉冲，带一点抖动；返回 (信号, 脉冲位置)。"""
    g = np.random.default_rng(seed)
    x = np.zeros(n); pos = []
    t = 0.0
    while t < n - 2:
        i = int(t)
        x[i] += 1.0
        pos.append(i)
        T0 = sr / max(f0[min(i, n - 1)], 50.0)
        t += T0 * (1.0 + jitter * g.standard_normal())
    # 声门波的低通性质：-12 dB/oct 的一阶积分两次，再去直流
    x = np.cumsum(np.cumsum(x))
    x -= np.linspace(x[0], x[-1], n)
    x /= np.max(np.abs(x)) + 1e-12
    return x, np.array(pos)


def utterance(phones=None, sr=SR, seed=7, f0_mean=120.0):
    """造一句话：一串音素，每个有指定时长与类型。
       返回 dict：波形 x、基频曲线 f0、每个音素的起止样点、共振峰轨迹。"""
    g = np.random.default_rng(seed)
    if phones is None:
        #  (音素, 类型, 时长 ms)   类型 v=元音  f=清擦音  p=爆破闭塞  n=静音
        phones = [('sil', 'n', 180), ('sh', 'f', 130), ('a', 'v', 190),
                  ('n', 'v', 90),  ('t', 'p', 70),  ('i', 'v', 210),
                  ('sil', 'n', 90), ('h', 'f', 90),  ('o', 'v', 230),
                  ('u', 'v', 160), ('s', 'f', 140), ('e', 'v', 250),
                  ('sil', 'n', 200)]
    dur = np.array([p[2] for p in phones]) / 1000.0
    bnd = np.r_[0, np.cumsum(np.round(dur * sr)).astype(int)]
    n = bnd[-1]

    # 基频：整句一条下倾的语调线 + 句中一个重音抬头 + 微抖
    t = np.arange(n) / sr
    dec = np.exp(-t / (t[-1] * 1.4))
    f0 = f0_mean * (0.82 + 0.34 * dec) + 10 * np.sin(2 * np.pi * 0.9 * t)
    f0 += 2.5 * np.convolve(g.standard_normal(n), np.ones(801) / 801, 'same')

    # 共振峰轨迹：在元音目标之间平滑过渡
    Ft = np.zeros((5, n))
    Ft[3] = 3500.0; Ft[4] = 4500.0            # F4/F5 固定，填上高频包络
    cur = np.array(VOWELS['a'], float)
    for (ph, ty, _), a, b in zip(phones, bnd[:-1], bnd[1:]):
        tgt = np.array(VOWELS.get(ph, (500.0, 1500.0, 2500.0)), float)
        if ty != 'v':
            tgt = cur
        L = b - a
        ramp = np.linspace(0, 1, L) ** 0.7
        for k in range(3):
            Ft[k, a:b] = cur[k] + (tgt[k] - cur[k]) * ramp
        cur = tgt
    sm = np.ones(int(0.02 * sr)) / int(0.02 * sr)
    for k in range(3):
        Ft[k] = np.convolve(Ft[k], sm, 'same')
    BW = np.vstack([np.full(n, 60.0), np.full(n, 90.0), np.full(n, 130.0),
                    np.full(n, 220.0), np.full(n, 300.0)])

    src, pulses = glottal(n, f0, sr, seed=seed)
    voiced = np.zeros(n)
    noise = g.standard_normal(n)
    for (ph, ty, _), a, b in zip(phones, bnd[:-1], bnd[1:]):
        if ty == 'v':
            voiced[a:b] = 1.0
    env = np.convolve(voiced, np.hanning(int(0.012 * sr)), 'same')
    env /= env.max() + 1e-12
    x = formant_filter(src * env, Ft, BW, sr)
    x = np.diff(np.r_[0.0, x])                 # 唇辐射：+6 dB/oct，把总倾斜拉到 -6
    x /= np.max(np.abs(x)) + 1e-12

    # 清擦音：按音素给不同的频带；爆破：一小段闭塞 + 一个冲激
    BAND = {'s': (3800, 9000), 'sh': (1800, 6500), 'f': (1200, 8000),
            'h': (400, 3500), 'x': (2500, 8000)}
    for (ph, ty, _), a, b in zip(phones, bnd[:-1], bnd[1:]):
        if ty == 'f':
            lo, hi = BAND.get(ph, (2000, 8000))
            L = b - a
            nz = np.fft.rfft(noise[a:b])
            fr = np.fft.rfftfreq(L, 1 / sr)
            nz *= 1.0 / (1 + ((fr - (lo + hi) / 2) / ((hi - lo) / 2)) ** 8)
            nz = np.fft.irfft(nz, L)
            nz /= np.std(nz) + 1e-12
            w = np.hanning(L)
            x[a:b] += 0.085 * nz * w
        elif ty == 'p':
            x[a:b] *= 0.02
            k = a + int((b - a) * 0.72)
            L = min(int(0.008 * sr), b - k)
            x[k:k + L] += 0.7 * noise[k:k + L] * np.hanning(L)
    x /= np.max(np.abs(x)) + 1e-12
    return {'x': x, 'sr': sr, 'f0': f0, 'voiced': voiced, 'F': Ft,
            'phones': phones, 'bnd': bnd, 'pulses': pulses}


def melspec(x, fb=None, nfft=NFFT, hop=HOP, log=True, floor=1e-5):
    S = np.abs(stft(x, nfft, hop))
    if fb is None:
        fb = mel_fb(nfft=nfft)
    M = fb @ S
    return np.log(np.maximum(M, floor)) if log else M


if __name__ == '__main__':
    u = utterance()
    print('句长 %.2f s (%d 样点)，音素 %d 个' % (len(u['x']) / SR, len(u['x']), len(u['phones'])))
    M = melspec(u['x'])
    print('梅尔谱 %s，帧率 %.2f Hz' % (M.shape, SR / HOP))
    print('F0 范围 %.0f–%.0f Hz' % (u['f0'].min(), u['f0'].max()))
    print('边界（样点）:', u['bnd'])
