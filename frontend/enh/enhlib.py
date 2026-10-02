#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《单通道增强手册》的公共件。

   设计原则和姊妹篇一致：干净语音是<用源-滤波模型合成>的，
   基频曲线、共振峰轨迹、每个音素的起止都是已知真值，
   所以"增强丢了什么"才有客观答案。代价是它不是真录音——
   绝对数值不能直接和 DNS 上的结果比，可比的是形状和量级。
"""
import numpy as np

SR = 16000
EPS = 1e-12


# ══════════════════════════════════════════════════════════════
# STFT：平方根汉宁窗 + 50% 重叠 → 满足 COLA，可完美重构
# ══════════════════════════════════════════════════════════════
def sqrthann(n):
    return np.sqrt(np.hanning(n + 1)[:n] + EPS)


def stft(x, nfft=512, hop=None, win=None):
    hop = hop or nfft // 2
    w = sqrthann(nfft) if win is None else win
    nfr = 1 + (len(x) - nfft) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(nfr)[:, None]
    return np.fft.rfft(x[idx] * w, axis=1)                     # (帧, 频)


def istft(X, nfft=512, hop=None, win=None, n=None):
    hop = hop or nfft // 2
    w = sqrthann(nfft) if win is None else win
    fr = np.fft.irfft(X, n=nfft, axis=1) * w
    L = (len(X) - 1) * hop + nfft
    y = np.zeros(L)
    nrm = np.zeros(L)
    for i in range(len(X)):
        y[i * hop:i * hop + nfft] += fr[i]
        nrm[i * hop:i * hop + nfft] += w ** 2
    y /= np.maximum(nrm, 1e-8)
    return y[:n] if n else y


def check_pr(nfft=512, hop=None, seed=0):
    """完美重构自检：返回重构误差的 dB"""
    g = np.random.default_rng(seed)
    x = g.standard_normal(SR // 2)
    y = istft(stft(x, nfft, hop), nfft, hop, n=len(x))
    m = slice(nfft, len(x) - nfft)                             # 去掉两端的爬坡
    return 10 * np.log10(np.mean((y[m] - x[m]) ** 2) / np.mean(x[m] ** 2) + 1e-32)


# ══════════════════════════════════════════════════════════════
# 干净语音：源-滤波模型
# ══════════════════════════════════════════════════════════════
# (共振峰中心 Hz, 带宽 Hz) —— 五个元音 + 两个近似的辅音位形
VOWELS = {
    'a': [(730, 90), (1090, 110), (2440, 140), (3400, 250)],
    'i': [(270, 60), (2290, 110), (3010, 140), (3700, 250)],
    'u': [(300, 60), (870, 90), (2240, 140), (3400, 250)],
    'e': [(530, 80), (1840, 100), (2480, 140), (3600, 250)],
    'o': [(570, 80), (840, 100), (2410, 140), (3400, 250)],
}
FRIC = {'s': (5200, 2600), 'sh': (3000, 1800), 'f': (7000, 3000)}


def _formant_filter(x, formants, sr=SR):
    """级联二阶共振器"""
    y = x.copy()
    for f, bw in formants:
        r = np.exp(-np.pi * bw / sr)
        th = 2 * np.pi * f / sr
        a1, a2 = -2 * r * np.cos(th), r * r
        b0 = (1 - r) * np.sqrt(1 - 2 * r * np.cos(2 * th) + r * r)
        out = np.zeros_like(y)
        z1 = z2 = 0.0
        for n in range(len(y)):
            v = b0 * y[n] - a1 * z1 - a2 * z2
            out[n] = v
            z2, z1 = z1, v
        y = out
    return y


def spk_params(spk, base_lo=110.0, base_hi=165.0):
    """说话人身份：声道长度（共振峰整体缩放）+ 基频区间。
       同一个 spk 的两段语音是"同一个人"，不同 spk 是不同人。"""
    g = np.random.default_rng(10000 + spk)
    vtl = float(np.exp(g.normal(0.0, 0.15)))          # 声道长度因子，约 ±15%
    f0c = float(base_lo * np.exp(g.normal(0.0, 0.22)))
    return {'vtl': vtl, 'f0_lo': f0c, 'f0_hi': f0c * (base_hi / base_lo)}


def make_speech(dur=4.0, sr=SR, seed=1, f0_lo=110.0, f0_hi=165.0, spk=None,
                text_seed=None):
    """合成一段带静音、浊音、清音的语音，返回 (波形, 每个音段的真值表)。
       给 spk 就按那个说话人的声道长度和基频区间来合成。
       给 text_seed 就固定音素序列和时长（"同一句话"），
       用来做<strong>文本相关</strong>的说话人实验——否则音素内容会把说话人差异淹没。"""
    if spk is not None:
        pp = spk_params(spk)
        f0_lo, f0_hi, _vtl = pp['f0_lo'], pp['f0_hi'], pp['vtl']
    else:
        _vtl = 1.0
    g = np.random.default_rng(seed)
    gt = np.random.default_rng(text_seed) if text_seed is not None else g
    n = int(dur * sr)
    x = np.zeros(n)
    segs = []
    t = 0.0
    order = ['sil', 'a', 'i', 's', 'u', 'sil', 'e', 'sh', 'o', 'a', 'sil',
             'i', 'f', 'u', 'e', 'sil', 'o', 's', 'a', 'i', 'sil']
    k = 0
    while t < dur - 0.25:
        ph = order[k % len(order)]
        k += 1
        ln = (0.18 + 0.12 * gt.random()) if ph == 'sil' else (0.09 + 0.13 * gt.random())
        i0, i1 = int(t * sr), min(n, int((t + ln) * sr))
        m = i1 - i0
        if m < 64:
            break
        if ph == 'sil':
            pass
        elif ph in FRIC:                                        # 清擦音：带通噪声
            f, bw = FRIC[ph]
            seg = _formant_filter(g.standard_normal(m) * 0.35, [(f * _vtl, bw)])
            x[i0:i1] = seg / (np.std(seg) + EPS) * 0.12
        else:                                                   # 浊音：脉冲串 + 共振峰
            f0 = f0_lo + (f0_hi - f0_lo) * g.random()
            drift = np.linspace(1.0, 1.0 + 0.10 * (g.random() - 0.5), m)
            ph_acc = np.cumsum(2 * np.pi * f0 * drift / sr)
            # 带轻微抖动的准脉冲源（谐波丰富、有自然的谱倾斜）
            src = np.zeros(m)
            pos = 0.0
            while pos < m:
                i = int(pos)
                if i < m:
                    src[i] = 1.0
                pos += sr / (f0 * drift[min(i, m - 1)]) * (1 + 0.012 * g.standard_normal())
            src = np.convolve(src, np.exp(-np.arange(64) / 9.0), 'same')
            # 气声：真实浊音的高频不是纯谐波，加一层噪声源（−28 dB）
            src = src / (np.std(src) + EPS)
            src = src + _shape(g.standard_normal(m), 3.0) * 10 ** (-28 / 20) * 1.0
            seg = _formant_filter(src, [(f * _vtl, b) for f, b in VOWELS[ph]])
            env = np.minimum(1.0, np.minimum(np.arange(m), m - 1 - np.arange(m)) / (0.02 * sr))
            seg = seg * env
            x[i0:i1] = seg / (np.std(seg) + EPS) * 0.30
        segs.append({'ph': ph, 'i0': i0, 'i1': i1,
                     'voiced': ph not in FRIC and ph != 'sil'})
        t += ln
    x = x / (np.max(np.abs(x)) + EPS) * 0.8
    return x, segs


def speech_mask(segs, n):
    """样点级的"有语音"真值"""
    m = np.zeros(n, bool)
    for s in segs:
        if s['ph'] != 'sil':
            m[s['i0']:s['i1']] = True
    return m


# ══════════════════════════════════════════════════════════════
# 噪声
# ══════════════════════════════════════════════════════════════
def _shape(x, slope_db_oct, sr=SR, nfft=1024):
    """给白噪声加一个 dB/倍频程的谱倾斜"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / sr)
    f = np.maximum(f, 20.0)
    g = 10 ** (slope_db_oct * np.log2(f / 1000.0) / 20.0)
    return np.fft.irfft(X * g, n=len(x))


def make_noise(kind, n, seed=2, sr=SR):
    g = np.random.default_rng(seed)
    w = g.standard_normal(n)
    if kind == 'white':
        y = w
    elif kind == 'pink':                                        # −3 dB/oct
        y = _shape(w, -3.0, sr)
    elif kind == 'car':                                         # 低频为主，很平稳
        y = _shape(w, -9.0, sr)
    elif kind == 'babble':                                      # 多人叠加：非平稳，谱像语音
        y = np.zeros(n)
        for k in range(6):
            s, _ = make_speech(dur=n / sr + 0.4, seed=100 + k + 7 * seed)
            y += s[:n] * (0.6 + 0.4 * g.random())
        y = _shape(y, -2.0, sr)
    elif kind == 'step':                                        # 中途突然变大 12 dB
        y = _shape(w, -3.0, sr)
        y[n // 2:] *= 10 ** (12 / 20)
    else:
        raise ValueError(kind)
    return y / (np.std(y) + EPS)


def mix_at_snr(s, v, snr_db, mask=None):
    """按<语音段>的能量对齐信噪比（全局对齐会被静音段稀释）"""
    m = mask if mask is not None else np.ones(len(s), bool)
    ps = np.mean(s[m] ** 2) + EPS
    pv = np.mean(v ** 2) + EPS
    a = np.sqrt(ps / pv / 10 ** (snr_db / 10))
    return s + a * v, a * v


# ══════════════════════════════════════════════════════════════
# 指标
# ══════════════════════════════════════════════════════════════
def seg_snr(s, y, mask=None, frame=512, hop=256, lo=-10.0, hi=35.0):
    """分段信噪比，只在有语音的帧上算，并按惯例做上下限截断"""
    n = min(len(s), len(y))
    s, y = s[:n], y[:n]
    e = y - s
    out = []
    for i in range(0, n - frame, hop):
        if mask is not None and mask[i:i + frame].mean() < 0.5:
            continue
        ps = np.sum(s[i:i + frame] ** 2)
        pe = np.sum(e[i:i + frame] ** 2)
        if ps < EPS:
            continue
        out.append(np.clip(10 * np.log10(ps / (pe + EPS)), lo, hi))
    return float(np.mean(out)) if out else float('nan')


def lsd(s, y, nfft=512, hop=256, mask=None, dyn_db=45.0):
    """对数谱距离 dB。每一帧各自把下限压到"本帧谱峰往下 dyn_db"——
       否则谐波之间的深谷（合成语音比真语音深得多）会让对数差发散，
       指标就只在量"噪声把谷填了多少"，不再有意义。"""
    n = min(len(s), len(y))
    S, Y = stft(s[:n], nfft, hop), stft(y[:n], nfft, hop)
    a = 20 * np.log10(np.abs(S) + EPS)
    b = 20 * np.log10(np.abs(Y) + EPS)
    fl = a.max(axis=1, keepdims=True) - dyn_db
    a = np.maximum(a, fl)
    b = np.maximum(b, fl)
    d = np.sqrt(np.mean((a - b) ** 2, axis=1))
    if mask is not None:
        fm = np.array([mask[i * hop:i * hop + nfft].mean() > 0.5 for i in range(len(S))])
        if fm.any():
            d = d[fm]
    return float(np.mean(d))


def si_sdr(s, y):
    """尺度不变信噪比 dB"""
    n = min(len(s), len(y))
    s, y = s[:n] - s[:n].mean(), y[:n] - y[:n].mean()
    a = np.dot(y, s) / (np.dot(s, s) + EPS)
    t = a * s
    return float(10 * np.log10((np.dot(t, t) + EPS) / (np.dot(y - t, y - t) + EPS)))


def stoi_like(s, y, nfft=512, hop=256, nband=15, frames=30, mask=None):
    """简化的可懂度代理：1/3 倍频程子带包络在短时窗内的相关系数均值。

       不是标准 STOI（没有做归一化截断和 8 kHz 重采样），
       但它抓住了同一个东西——<包络的相关性>，而不是波形的相似度。
    """
    n = min(len(s), len(y))
    S, Y = np.abs(stft(s[:n], nfft, hop)), np.abs(stft(y[:n], nfft, hop))
    f = np.fft.rfftfreq(nfft, 1 / SR)
    edges = 150 * 2 ** (np.arange(nband + 1) / 3.0)
    rs = []
    for b in range(nband):
        sel = (f >= edges[b]) & (f < edges[b + 1])
        if sel.sum() == 0:
            continue
        a = np.sqrt(np.sum(S[:, sel] ** 2, 1))
        c = np.sqrt(np.sum(Y[:, sel] ** 2, 1))
        for i in range(0, len(a) - frames, frames // 2):
            u, v = a[i:i + frames], c[i:i + frames]
            if mask is not None:
                fm = np.array([mask[(i + k) * hop:(i + k) * hop + nfft].mean()
                               for k in range(frames)])
                if fm.mean() < 0.5:
                    continue
            u = u - u.mean(); v = v - v.mean()
            d = np.sqrt(np.sum(u ** 2) * np.sum(v ** 2))
            if d < EPS:
                continue
            rs.append(np.dot(u, v) / d)
    return float(np.mean(rs)) if rs else float('nan')


# ══════════════════════════════════════════════════════════════
# 误差的正交分解：语音失真 vs 残留噪声
# ══════════════════════════════════════════════════════════════
def decompose(S, V, G):
    """给定干净语音谱 S、噪声谱 V 和实数增益 G，把误差拆成两块。

       Ŝ = G·(S+V) = G·S + G·V
       误差 = (G−1)·S  +  G·V
              ↑语音失真   ↑残留噪声
       两项在统计上正交（S 与 V 独立），所以功率可以直接相加。
    """
    dist = np.sum(np.abs((G - 1.0) * S) ** 2)
    resid = np.sum(np.abs(G * V) ** 2)
    sig = np.sum(np.abs(S) ** 2) + EPS
    return {'sd_db': float(10 * np.log10(dist / sig + EPS)),
            'nr_db': float(10 * np.log10(resid / sig + EPS)),
            'tot_db': float(10 * np.log10((dist + resid) / sig + EPS))}


# ══════════════════════════════════════════════════════════════
# 音乐噪声的量化
# ══════════════════════════════════════════════════════════════
def musical(R, mask_fr=None, ref=None, floor_db=-40.0):
    """音乐噪声度量 ①：残差功率在<非语音帧>上的帧间起伏（dB）。

       物理图像：音乐噪声就是"同一个频点上，功率在帧与帧之间跳得太厉害"——
       大的那些残差被听成孤立的纯音。

       这个量有一个<理论零点>：平稳高斯噪声的周期图服从 χ²₂（指数分布），
       10·log₁₀ 之后的标准差是
           10/ln10 · π/√6 = 5.57 dB
       与处理无关。所以 5.57 dB 是"没有音乐噪声"的下限，
       读数高出多少，就是多出来的起伏。

       增益把大量频点压成 0 会让对数发散，那属于<过度抑制>而不是音乐噪声，
       所以取一个相对于输入噪声功率的下限（默认 −40 dB）再取对数。
    """
    P = np.abs(R) ** 2
    if mask_fr is not None:
        P = P[~mask_fr]
    if len(P) < 4:
        return float('nan')
    base = np.mean(np.abs(ref if ref is not None else R) ** 2) + EPS
    L = 10 * np.log10(np.maximum(P, base * 10 ** (floor_db / 10)) + EPS)
    return float(np.mean(np.std(L, axis=0)))


MUS_FLOOR_DB = 10 / np.log(10) * np.pi / np.sqrt(6)      # 5.57 dB，χ²₂ 的理论值


def kurt_ratio(R, V, mask_fr=None):
    """音乐噪声度量 ②：残差功率的峰度，相对输入噪声的峰度。

       文献里更常用的一个量。平稳高斯噪声的功率服从指数分布，峰度 = 9；
       处理之后若只剩下稀疏的孤立峰，峰度会显著上升。
       取比值是为了不受尺度影响。
    """
    def k(A):
        p = (np.abs(A) ** 2)
        if mask_fr is not None:
            p = p[~mask_fr]
        p = p.ravel()
        c = p - p.mean()
        return float(np.mean(c ** 4) / (np.mean(c ** 2) ** 2 + EPS))
    return k(R) / max(k(V), EPS)


def nonstat(V, nsm=8):
    """噪声的<非平稳度>：先在时间上平滑 nsm 帧把 χ²₂ 的随机起伏平掉，
       剩下的 dB 起伏就是功率谱本身随时间的变化。按各频点能量加权平均。
       平稳噪声不会读到 0：χ²₂ 的起伏经 nsm 帧平滑后还剩
    约 5.57/√nsm dB（帧间有重叠，实测略低）。
    读数明显高过这个基线，才是真的非平稳。"""
    P = np.abs(V) ** 2
    k = np.ones(nsm) / nsm
    Ps = np.apply_along_axis(lambda c: np.convolve(c, k, 'same'), 0, P)
    L = 10 * np.log10(Ps + EPS)
    sd = np.std(L[nsm:-nsm], axis=0)
    w = P.mean(axis=0)
    return float(np.sum(sd * w) / (np.sum(w) + EPS))


def frame_mask(mask, nfr, nfft=512, hop=256):
    return np.array([mask[i * hop:i * hop + nfft].mean() > 0.5 for i in range(nfr)])


# ══════════════════════════════════════════════════════════════
# 经典增强的几个部件（02–04 节共用）
# ══════════════════════════════════════════════════════════════
from scipy.special import exp1 as _exp1


def g_logmmse(xi, gam):
    nu = np.clip(xi / (1.0 + xi) * gam, 1e-8, 500.0)
    return xi / (1.0 + xi) * np.exp(0.5 * _exp1(nu))


def dd_xi(Y, lam, alpha, xi_min_db=-25.0):
    gam = np.abs(Y) ** 2 / np.maximum(lam, EPS)
    xi = np.zeros_like(gam)
    xi_min = 10 ** (xi_min_db / 10)
    prev = np.maximum(gam[0] - 1.0, 0.0)
    for l in range(len(gam)):
        ml = np.maximum(gam[l] - 1.0, 0.0)
        xi[l] = np.maximum(alpha * prev + (1 - alpha) * ml, xi_min)
        g = xi[l] / (1.0 + xi[l])
        prev = g ** 2 * gam[l]
    return xi, gam


def est_ms(P, D=48, alpha=0.85, bias=1.5):
    """最小统计量：在长度 D 帧的滑窗里取平滑周期图的最小值，再乘偏差补偿"""
    Ps = np.zeros_like(P)
    s = P[0].copy()
    for l in range(len(P)):
        s = alpha * s + (1 - alpha) * P[l]
        Ps[l] = s
    lam = np.zeros_like(P)
    for l in range(len(P)):
        lo = max(0, l - D + 1)
        lam[l] = Ps[lo:l + 1].min(axis=0) * bias
    return lam


def est_mcra(P, D=48, a_s=0.85, a_d=0.95, a_p=0.2, delta=5.0):
    """MCRA：先用"局部最小值的多少倍"判语音在不在，再按语音存在概率做递归平均"""
    n = len(P)
    lam = np.zeros_like(P)
    s = P[0].copy()
    smin = P[0].copy()
    stmp = P[0].copy()
    d = P[0].copy()
    p = np.zeros(P.shape[1])
    for l in range(n):
        s = a_s * s + (1 - a_s) * P[l]
        if l % D == 0 and l > 0:
            smin = np.minimum(stmp, s)
            stmp = s.copy()
        else:
            smin = np.minimum(smin, s)
            stmp = np.minimum(stmp, s)
        I = (s / np.maximum(smin, EPS) < delta).astype(float)   # 1 = 判为"无语音"
        p = a_p * p + (1 - a_p) * (1.0 - I)                       # 语音存在概率
        ad = a_d + (1 - a_d) * p                                  # 有语音时几乎不更新
        d = ad * d + (1 - ad) * P[l]
        lam[l] = d
    return lam


def est_imcra(P, D=64, thr=3.0, a=0.92, bias=1.08):
    """IMCRA 的核心是<两轮>：第一轮的结果用来标出语音帧，
       第二轮只在"判为无语音"的帧上做递归平均——
       取均值而不是再取一次最小值，所以偏差小得多。"""
    lam1 = est_mcra(P, D=D)
    gam = P / np.maximum(lam1, EPS)
    keep = gam < thr                                              # True = 大概没语音
    lam = np.zeros_like(P)
    d = np.mean(P[:8], axis=0)
    for l in range(len(P)):
        upd = keep[l]
        d = np.where(upd, a * d + (1 - a) * P[l], d)              # 有语音的频点不更新
        lam[l] = d * bias
    return lam


if __name__ == '__main__':
    print('完美重构误差 %.1f dB（应当 < −250）' % check_pr())
    x, segs = make_speech()
    m = speech_mask(segs, len(x))
    print('合成语音 %.2f s，语音段占 %.1f%%，音段 %d 个'
          % (len(x) / SR, m.mean() * 100, len(segs)))
    for k in ('white', 'pink', 'car', 'babble'):
        v = make_noise(k, len(x), seed=3)
        y, vv = mix_at_snr(x, v, 5.0, m)
        print('  %-7s 混到 5 dB → SegSNR %.2f  LSD %.2f  SI-SDR %.2f  STOI* %.3f'
              % (k, seg_snr(x, y, m), lsd(x, y, mask=m), si_sdr(x, y),
                 stoi_like(x, y, mask=m)))
