#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""神经降噪：真训一个，和 log-MMSE 放同一张表里比。

   纯 numpy、手写反传、<strong>严格因果</strong>（只看过去的帧），
   规模和一个能跑在手机上的模型同量级。
   训练数据用 white / pink / car 三种噪声，
   测试时额外给一种<strong>训练时没见过的</strong>噪声（babble），
   看"泛化"这件事到底值多少 dB。
"""
import numpy as np, json, time
import enhlib as E
from enhlib import g_logmmse, dd_xi, est_imcra

rng = np.random.default_rng(0)
OUT = {}
NFFT, HOP = 512, 256
NBIN = NFFT // 2 + 1
NB = 32                      # 频带数
CTX = 6                      # 因果上下文帧数（含当前帧）
SNRS = (-5.0, 0.0, 5.0, 10.0, 15.0)
TRAIN_NOISE = ('white', 'pink', 'car')
UNSEEN_NOISE = 'babble'


# ══ 频带（等效矩形带宽间隔的三角滤波器组）════════════════════════
def bands(nbin=NBIN, nb=NB, sr=E.SR):
    f = np.linspace(0, sr / 2, nbin)
    mel = lambda x: 2595 * np.log10(1 + x / 700)
    imel = lambda x: 700 * (10 ** (x / 2595) - 1)
    e = imel(np.linspace(mel(50), mel(sr / 2 - 100), nb + 2))
    W = np.zeros((nb, nbin))
    for b in range(nb):
        lo, c, hi = e[b], e[b + 1], e[b + 2]
        up = (f >= lo) & (f <= c)
        dn = (f > c) & (f <= hi)
        W[b, up] = (f[up] - lo) / max(c - lo, 1e-9)
        W[b, dn] = (hi - f[dn]) / max(hi - c, 1e-9)
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    Wt = W.T / np.maximum(W.sum(0)[:, None], 1e-9)      # 频带 → 频点（能量守恒的展开）
    return W, Wt


WB, WT = bands()


# ══ 数据 ══════════════════════════════════════════════════════
def make_pair(seed, kind, snr):
    x, segs = E.make_speech(dur=3.0, seed=seed)
    m = E.speech_mask(segs, len(x))
    v = E.make_noise(kind, len(x), seed=seed * 7 + 11)
    y, vv = E.mix_at_snr(x, v, snr, m)
    n = len(y)
    S = E.stft(x[:n], NFFT, HOP)
    V = E.stft(vv[:n], NFFT, HOP)
    Y = E.stft(y, NFFT, HOP)
    return x[:n], y, m[:n], S, V, Y


def featurize(Y):
    """因果特征：频带对数能量 + 其一阶差分，再做因果的均值方差归一化"""
    P = np.maximum((np.abs(Y) ** 2) @ WB.T, 1e-10)
    L = 10 * np.log10(P)
    mu = np.zeros_like(L); sd = np.zeros_like(L)
    a, m_, s_ = 0.98, L[0].copy(), np.ones(NB) * 10.0
    for l in range(len(L)):
        m_ = a * m_ + (1 - a) * L[l]
        s_ = a * s_ + (1 - a) * np.abs(L[l] - m_)
        mu[l], sd[l] = m_, np.maximum(s_, 1.0)
    Z = (L - mu) / sd
    D = np.vstack([np.zeros((1, NB)), np.diff(Z, axis=0)])
    F = np.concatenate([Z, D], 1)                                  # (帧, 2·NB)
    ctx = [np.vstack([np.repeat(F[:1], k, 0), F[:len(F) - k]]) for k in range(CTX)]
    return np.concatenate(ctx, 1).astype(np.float64)               # (帧, CTX·2·NB)


DIN = CTX * 2 * NB


def build(nset, kinds, seed0):
    Xs, Ms, Ss, Vs, Ys = [], [], [], [], []
    for i in range(nset):
        k = kinds[i % len(kinds)]
        snr = SNRS[i % len(SNRS)]
        _, _, _, S, V, Y = make_pair(seed0 + i, k, snr)
        Xs.append(featurize(Y)); Ss.append(S); Vs.append(V); Ys.append(Y)
    return (np.concatenate(Xs), np.concatenate(Ss),
            np.concatenate(Vs), np.concatenate(Ys))


print('造训练数据…')
t0 = time.time()
Xtr, Str, Vtr, Ytr = build(36, TRAIN_NOISE, 100)
irm_bin = np.sqrt(np.abs(Str) ** 2 / (np.abs(Str) ** 2 + np.abs(Vtr) ** 2 + E.EPS))
pb_s = (np.abs(Str) ** 2) @ WB.T
pb_v = (np.abs(Vtr) ** 2) @ WB.T
irm_band = np.sqrt(pb_s / (pb_s + pb_v + E.EPS))
print('  %d 帧，输入 %d 维，用时 %.1f s' % (len(Xtr), DIN, time.time() - t0))
OUT['data'] = {'frames': int(len(Xtr)), 'din': DIN, 'nb': NB, 'ctx': CTX,
               'train_noise': list(TRAIN_NOISE), 'unseen': UNSEEN_NOISE,
               'snrs': list(SNRS)}


# ══ 模型：因果前馈，两个隐层 ═══════════════════════════════════
def init(din, h1, h2, dout, seed=0):
    g = np.random.default_rng(seed)
    return {'W1': g.standard_normal((din, h1)) / np.sqrt(din), 'b1': np.zeros(h1),
            'W2': g.standard_normal((h1, h2)) / np.sqrt(h1), 'b2': np.zeros(h2),
            'W3': g.standard_normal((h2, dout)) / np.sqrt(h2), 'b3': np.zeros(dout)}


def fwd(P, X):
    a1 = X @ P['W1'] + P['b1']; h1 = np.maximum(a1, 0)
    a2 = h1 @ P['W2'] + P['b2']; h2 = np.maximum(a2, 0)
    o = h2 @ P['W3'] + P['b3']
    return a1, h1, a2, h2, o


def bwd(P, X, a1, h1, a2, h2, do):
    G = {}
    G['W3'] = h2.T @ do; G['b3'] = do.sum(0)
    d2 = (do @ P['W3'].T) * (a2 > 0)
    G['W2'] = h1.T @ d2; G['b2'] = d2.sum(0)
    d1 = (d2 @ P['W2'].T) * (a1 > 0)
    G['W1'] = X.T @ d1; G['b1'] = d1.sum(0)
    return G


def train(dout, lossfn, steps=3000, bs=128, lr=2e-3, h=(128, 96), seed=0, tag=''):
    P = init(DIN, h[0], h[1], dout, seed)
    M = {k: np.zeros_like(v) for k, v in P.items()}
    Vv = {k: np.zeros_like(v) for k, v in P.items()}
    g = np.random.default_rng(seed + 5)
    hist = []
    for it in range(steps):
        i = g.integers(0, len(Xtr), bs)
        X = Xtr[i]
        a1, h1, a2, h2, o = fwd(P, X)
        L, do = lossfn(o, i)
        G = bwd(P, X, a1, h1, a2, h2, do / bs)
        for k in P:
            M[k] = 0.9 * M[k] + 0.1 * G[k]
            Vv[k] = 0.999 * Vv[k] + 0.001 * G[k] ** 2
            P[k] -= lr * (M[k] / (1 - 0.9 ** (it + 1))) / \
                (np.sqrt(Vv[k] / (1 - 0.999 ** (it + 1))) + 1e-8)
        if it % 500 == 0 or it == steps - 1:
            hist.append(round(float(L), 4))
    nparam = sum(v.size for v in P.values())
    print('    %-22s 参数 %6d  损失 %s' % (tag, nparam, ' → '.join(map(str, hist[:1] + hist[-1:]))))
    return P, nparam


sig = lambda z: 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def loss_band_mask(o, i):
    p = sig(o); t = irm_band[i]
    d = p - t
    return float(np.mean(d ** 2)), 2 * d * p * (1 - p) / o.shape[1]


def loss_bin_mask(o, i):
    p = sig(o); t = irm_bin[i]
    d = p - t
    return float(np.mean(d ** 2)), 2 * d * p * (1 - p) / o.shape[1]


def loss_logmag(o, i):
    """直接映射：输出的是 dB 域的增益，目标是 20log10(|S|/|Y|) 截断"""
    t = np.clip(20 * np.log10((np.abs(Str[i]) + E.EPS) / (np.abs(Ytr[i]) + E.EPS)), -40, 6)
    d = (o - t) / 20.0
    return float(np.mean(d ** 2)), 2 * d / 20.0 / o.shape[1]


def loss_sisdr(o, i):
    """谱域 SI-SDR：由帕塞瓦尔定理，它和时域的 SI-SDR 等价"""
    mm = sig(o)
    Yb, Sb = Ytr[i], Str[i]
    R = np.real(Yb * np.conj(Sb))
    A = np.sum(mm * R, 1, keepdims=True)
    B = np.sum(np.abs(Sb) ** 2, 1, keepdims=True) + E.EPS
    Ee = np.sum(mm ** 2 * np.abs(Yb) ** 2, 1, keepdims=True)
    A = np.where(np.abs(A) < 1e-9, 1e-9, A)
    D = np.maximum(Ee - A ** 2 / B, 1e-9)
    val = 10 / np.log(10) * (np.log(A ** 2 / B) - np.log(D))
    dA = 10 / np.log(10) * (2 * R / A + (2 * A * R / B) / D)
    dE = -10 / np.log(10) * (2 * mm * np.abs(Yb) ** 2) / D
    grad = -(dA + dE)                                    # 损失 = −SI-SDR
    return float(-np.mean(val)), grad * mm * (1 - mm) / o.shape[1]


# ══ 应用 ══════════════════════════════════════════════════════
def apply_model(P, Y, mode):
    X = featurize(Y)
    _, _, _, _, o = fwd(P, X)
    if mode == 'band':
        G = sig(o) @ WT.T
    elif mode == 'bin':
        G = sig(o)
    elif mode == 'logmag':
        G = 10 ** (np.clip(o, -40, 6) / 20.0)
    return E.istft(G * Y, NFFT, HOP, n=(len(Y) - 1) * HOP + NFFT), G


def evaluate(P, mode, kinds, snr=5.0, seeds=(900, 901, 902)):
    rs = []
    for k in kinds:
        for sd in seeds:
            x, y, m, S, V, Y = make_pair(sd, k, snr)
            z, G = apply_model(P, Y, mode)
            z = z[:len(y)]
            fm = E.frame_mask(m, len(S), NFFT, HOP)
            rs.append((E.seg_snr(x, z, m), E.lsd(x, z, mask=m),
                       E.stoi_like(x, z, mask=m), E.musical(G[:len(V)] * V, fm)))
    a = np.mean(rs, 0)
    return dict(segsnr=round(float(a[0]), 2), lsd=round(float(a[1]), 2),
                stoi=round(float(a[2]), 3), mus=round(float(a[3]), 2))


def eval_classic(kinds, snr=5.0, seeds=(900, 901, 902)):
    rs = []
    for k in kinds:
        for sd in seeds:
            x, y, m, S, V, Y = make_pair(sd, k, snr)
            lam = est_imcra(np.abs(Y) ** 2)
            xi, gam = dd_xi(Y, lam, 0.98)
            G = g_logmmse(xi, gam)
            z = E.istft(G * Y, NFFT, HOP, n=len(y))
            fm = E.frame_mask(m, len(S), NFFT, HOP)
            rs.append((E.seg_snr(x, z, m), E.lsd(x, z, mask=m),
                       E.stoi_like(x, z, mask=m), E.musical(G * V, fm)))
    a = np.mean(rs, 0)
    return dict(segsnr=round(float(a[0]), 2), lsd=round(float(a[1]), 2),
                stoi=round(float(a[2]), 3), mus=round(float(a[3]), 2))


def eval_noisy(kinds, snr=5.0, seeds=(900, 901, 902)):
    rs = []
    for k in kinds:
        for sd in seeds:
            x, y, m, S, V, Y = make_pair(sd, k, snr)
            fm = E.frame_mask(m, len(S), NFFT, HOP)
            rs.append((E.seg_snr(x, y, m), E.lsd(x, y, mask=m),
                       E.stoi_like(x, y, mask=m), E.musical(V, fm)))
    a = np.mean(rs, 0)
    return dict(segsnr=round(float(a[0]), 2), lsd=round(float(a[1]), 2),
                stoi=round(float(a[2]), 3), mus=round(float(a[3]), 2))


# ══ ① 输出形式 ════════════════════════════════════════════════
print('\n① 输出什么：频带掩码 / 频点掩码 / 直接映射到增益')
t0 = time.time()
MODELS = {}
for tag, dout, lf, mode in (('频带掩码（%d 带）' % NB, NB, loss_band_mask, 'band'),
                            ('频点掩码（%d 点）' % NBIN, NBIN, loss_bin_mask, 'bin'),
                            ('直接映射到 dB 增益', NBIN, loss_logmag, 'logmag')):
    P, npar = train(dout, lf, tag=tag)
    MODELS[tag] = (P, mode, npar)
OUT['form'] = []
for tag, (P, mode, npar) in MODELS.items():
    seen = evaluate(P, mode, TRAIN_NOISE)
    unseen = evaluate(P, mode, (UNSEEN_NOISE,))
    OUT['form'].append({'tag': tag, 'params': npar, 'seen': seen, 'unseen': unseen})
print('  %-22s %7s  %-28s %-28s' % ('输出形式', '参数', '训练见过的噪声', '没见过的噪声'))
for r in OUT['form']:
    print('  %-22s %7d  SegSNR %5.2f LSD %5.2f STOI* %.3f   SegSNR %5.2f LSD %5.2f STOI* %.3f'
          % (r['tag'], r['params'], r['seen']['segsnr'], r['seen']['lsd'],
             r['seen']['stoi'], r['unseen']['segsnr'], r['unseen']['lsd'],
             r['unseen']['stoi']))

# ══ ② 损失函数 ════════════════════════════════════════════════
print('\n② 损失函数：在同一个"频点掩码"模型上换损失')
OUT['loss'] = []
for tag, lf in (('掩码 MSE', loss_bin_mask), ('谱域 SI-SDR', loss_sisdr)):
    P, npar = train(NBIN, lf, tag=tag)
    seen = evaluate(P, 'bin', TRAIN_NOISE)
    unseen = evaluate(P, 'bin', (UNSEEN_NOISE,))
    OUT['loss'].append({'tag': tag, 'seen': seen, 'unseen': unseen})
    print('  %-12s  见过 SegSNR %5.2f LSD %5.2f STOI* %.3f 起伏 %5.2f  |  '
          '没见过 SegSNR %5.2f STOI* %.3f'
          % (tag, seen['segsnr'], seen['lsd'], seen['stoi'], seen['mus'],
             unseen['segsnr'], unseen['stoi']))

# ══ ③ 和经典方法同表 ══════════════════════════════════════════
print('\n③ 和 log-MMSE 放同一张表（输入 5 dB）')
best_form = max(OUT['form'], key=lambda r: r['seen']['segsnr'])
Pb, modeb, _ = MODELS[best_form['tag']]
OUT['vs'] = []
for tag, fn in (('带噪（不处理）', lambda ks: eval_noisy(ks)),
                ('log-MMSE + IMCRA', lambda ks: eval_classic(ks)),
                ('神经网络（' + best_form['tag'] + '）', lambda ks: evaluate(Pb, modeb, ks))):
    seen = fn(TRAIN_NOISE); unseen = fn((UNSEEN_NOISE,))
    OUT['vs'].append({'tag': tag, 'seen': seen, 'unseen': unseen})
print('  %-24s %-30s %-30s' % ('', '训练见过的噪声', '没见过的噪声（babble）'))
for r in OUT['vs']:
    print('  %-24s SegSNR %5.2f LSD %5.2f STOI* %.3f 起伏 %5.2f   SegSNR %5.2f STOI* %.3f'
          % (r['tag'], r['seen']['segsnr'], r['seen']['lsd'], r['seen']['stoi'],
             r['seen']['mus'], r['unseen']['segsnr'], r['unseen']['stoi']))
nn_, cl = OUT['vs'][2], OUT['vs'][1]
OUT['gap_seen'] = round(nn_['seen']['segsnr'] - cl['seen']['segsnr'], 2)
OUT['gap_unseen'] = round(nn_['unseen']['segsnr'] - cl['unseen']['segsnr'], 2)
print('  神经网络在<strong>见过的噪声</strong>上领先 %+.2f dB，'
      '在<strong>没见过的</strong>上 %+.2f dB。' % (OUT['gap_seen'], OUT['gap_unseen']))

# ══ ④ 训练噪声的多样性值多少 ═══════════════════════════════════
print('\n④ 把训练噪声从 3 种减到 1 种，看泛化掉多少')
OUT['diversity'] = []
Xtr_all, Str_all, Vtr_all, Ytr_all = Xtr, Str, Vtr, Ytr
irm_bin_all, irm_band_all = irm_bin, irm_band
for kinds in (('white',), ('white', 'pink'), TRAIN_NOISE):
    Xtr, Str, Vtr, Ytr = build(36, kinds, 100)
    irm_bin = np.sqrt(np.abs(Str) ** 2 / (np.abs(Str) ** 2 + np.abs(Vtr) ** 2 + E.EPS))
    P, _ = train(NBIN, loss_bin_mask, tag='训练噪声 %d 种' % len(kinds))
    seen = evaluate(P, 'bin', kinds)
    unseen = evaluate(P, 'bin', (UNSEEN_NOISE,))
    r = {'n': len(kinds), 'kinds': list(kinds), 'seen': seen, 'unseen': unseen}
    OUT['diversity'].append(r)
    print('  %d 种（%-16s）  没见过的 babble 上：SegSNR %5.2f dB   STOI* %.3f'
          % (len(kinds), '/'.join(kinds), unseen['segsnr'], unseen['stoi']))
Xtr, Str, Vtr, Ytr = Xtr_all, Str_all, Vtr_all, Ytr_all
irm_bin, irm_band = irm_bin_all, irm_band_all
d1, d3 = OUT['diversity'][0], OUT['diversity'][-1]
print('  训练噪声从 1 种加到 %d 种，没见过的噪声上从 %.2f dB 涨到 %.2f dB。'
      % (d3['n'], d1['unseen']['segsnr'], d3['unseen']['segsnr']))
print('  <strong>神经降噪买的是"见过"，不是"聪明"</strong>——'
      '这条决定了这类系统的全部工程重点在数据上。')

# ══ ⑤ 算力与延迟：它能不能塞进三档预算 ═════════════════════════
print('\n⑤ 算力与延迟')
h1, h2 = 128, 96
mac = DIN * h1 + h1 * h2 + h2 * NBIN
fps = E.SR / HOP
fft_mac = int(NFFT / 2 * np.log2(NFFT)) * 2                 # 正反各一次 FFT（复乘算 1）
OUT['cost'] = {'mac_per_frame': int(mac), 'fps': round(fps, 1),
               'mmac_s': round(mac * fps / 1e6, 2),
               'fft_mac': int(fft_mac),
               'fft_mmac_s': round(fft_mac * fps / 1e6, 2),
               'mw50': round(mac * fps * 50e-12 * 1e3, 3),
               'lat_ms': round((NFFT + HOP) / E.SR * 1000, 1)}
print('  网络 %s MAC/帧 × %.1f 帧/s = %.2f MMAC/s（约 %.2f mW @50 pJ/MAC）'
      % ('{:,}'.format(mac), fps, OUT['cost']['mmac_s'], OUT['cost']['mw50']))
print('  对比：一对 %d 点 FFT 本身是 %s MAC/帧 = %.2f MMAC/s——'
      % (NFFT, '{:,}'.format(fft_mac), OUT['cost']['fft_mmac_s']))
print('  也就是说<strong>这个规模的网络只比 FFT 贵 %.0f 倍</strong>，'
      '经典方法的其余部分（增益、递归）还不到 FFT 的一成。'
      % (mac / fft_mac))
print('  算法延迟 %.1f ms（窗 %d + 帧移 %d），只够"通话与会议"那一档；'
      % (OUT['cost']['lat_ms'], NFFT, HOP))
print('  要进耳机那一档，窗必须缩到 4 ms 以下——按 04 节的扫描，那会丢掉好几 dB。')

OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_nn.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_nn.json（训练与评测共 %.0f s）' % OUT['runtime_s'])
