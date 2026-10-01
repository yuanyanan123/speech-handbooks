#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三档场景的完整预算：把延迟预算一路算到"还剩多少 dB"。

   三档各给一个延迟预算，由它定下窗长与帧移，
   然后在<strong>同一批信号</strong>上把经典法和小网络各跑一遍，
   同时结算算力、内存和实得的增益。
   目的是看清：每一档真正卡住的是哪一个约束。
"""
import numpy as np, json, time
import enhlib as E
from enhlib import g_logmmse, dd_xi, est_imcra

OUT = {}
t0 = time.time()
SR = E.SR
NB = 32
CTX = 6
H1, H2 = 128, 96
NOISES = ('white', 'pink', 'car')
UNSEEN = 'babble'
SNRS = (0.0, 5.0, 10.0)

TIERS = [
    dict(key='ear', name='耳机 / 助听', budget_ms=8.0, nfft=64, hop=32, look=0,
         why='戴着它听自己的声音，骨导和气导要对齐'),
    dict(key='call', name='通话 / 车载', budget_ms=40.0, nfft=256, hop=128, look=0,
         why='双向对话，单向超过 40 ms 就开始互相打断'),
    dict(key='meet', name='会议录制 / 后处理', budget_ms=200.0, nfft=1024, hop=256,
         look=2, why='单向收听或离线出稿，可以攒一点未来帧'),
]


# ══ 随窗长走的频带与特征 ══════════════════════════════════════
def bands(nbin, nb=NB, sr=SR):
    f = np.linspace(0, sr / 2, nbin)
    mel = lambda x: 2595 * np.log10(1 + x / 700)
    imel = lambda x: 700 * (10 ** (x / 2595) - 1)
    e = imel(np.linspace(mel(50), mel(sr / 2 - 100), nb + 2))
    W = np.zeros((nb, nbin))
    for b in range(nb):
        lo, c, hi = e[b], e[b + 1], e[b + 2]
        up = (f >= lo) & (f <= c); dn = (f > c) & (f <= hi)
        W[b, up] = (f[up] - lo) / max(c - lo, 1e-9)
        W[b, dn] = (hi - f[dn]) / max(hi - c, 1e-9)
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    return W


def featurize(Y, W, look):
    P = np.maximum((np.abs(Y) ** 2) @ W.T, 1e-10)
    L = 10 * np.log10(P)
    mu = np.zeros_like(L); sd = np.zeros_like(L)
    a, m_, s_ = 0.98, L[0].copy(), np.ones(NB) * 10.0
    for l in range(len(L)):
        m_ = a * m_ + (1 - a) * L[l]
        s_ = a * s_ + (1 - a) * np.abs(L[l] - m_)
        mu[l], sd[l] = m_, np.maximum(s_, 1.0)
    Z = (L - mu) / sd
    D = np.vstack([np.zeros((1, NB)), np.diff(Z, axis=0)])
    F = np.concatenate([Z, D], 1)
    sh = [np.vstack([np.repeat(F[:1], k, 0), F[:len(F) - k]]) for k in range(CTX)]
    for k in range(1, look + 1):           # 未来帧：只有允许前瞻的那一档才有
        sh.append(np.vstack([F[k:], np.repeat(F[-1:], k, 0)]))
    return np.concatenate(sh, 1).astype(np.float64)


sig = lambda z: 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def init(din, dout, seed=0):
    g = np.random.default_rng(seed)
    return {'W1': g.standard_normal((din, H1)) / np.sqrt(din), 'b1': np.zeros(H1),
            'W2': g.standard_normal((H1, H2)) / np.sqrt(H1), 'b2': np.zeros(H2),
            'W3': g.standard_normal((H2, dout)) / np.sqrt(H2), 'b3': np.zeros(dout)}


def fwd(P, X):
    a1 = X @ P['W1'] + P['b1']; h1 = np.maximum(a1, 0)
    a2 = h1 @ P['W2'] + P['b2']; h2 = np.maximum(a2, 0)
    return a1, h1, a2, h2, h2 @ P['W3'] + P['b3']


def fit(X, T, steps=2500, bs=128, lr=3e-3, seed=0):
    P = init(X.shape[1], T.shape[1], seed)
    M = {k: np.zeros_like(v) for k, v in P.items()}
    Vv = {k: np.zeros_like(v) for k, v in P.items()}
    g = np.random.default_rng(seed + 5)
    for it in range(steps):
        i = g.integers(0, len(X), bs)
        a1, h1, a2, h2, o = fwd(P, X[i])
        p = sig(o); d = p - T[i]
        do = 2 * d * p * (1 - p) / o.shape[1] / bs
        G = {}
        G['W3'] = h2.T @ do; G['b3'] = do.sum(0)
        d2 = (do @ P['W3'].T) * (a2 > 0)
        G['W2'] = h1.T @ d2; G['b2'] = d2.sum(0)
        d1 = (d2 @ P['W2'].T) * (a1 > 0)
        G['W1'] = X[i].T @ d1; G['b1'] = d1.sum(0)
        for k in P:
            M[k] = 0.9 * M[k] + 0.1 * G[k]
            Vv[k] = 0.999 * Vv[k] + 0.001 * G[k] ** 2
            P[k] -= lr * (M[k] / (1 - 0.9 ** (it + 1))) / \
                (np.sqrt(Vv[k] / (1 - 0.999 ** (it + 1))) + 1e-8)
    return P


def pair(seed, kind, snr, nfft, hop):
    x, segs = E.make_speech(dur=3.0, seed=seed)
    m = E.speech_mask(segs, len(x))
    v = E.make_noise(kind, len(x), seed=seed * 7 + 11)
    y, vv = E.mix_at_snr(x, v, snr, m)
    n = len(y)
    return (x[:n], y, m[:n], E.stft(x[:n], nfft, hop),
            E.stft(vv[:n], nfft, hop), E.stft(y, nfft, hop))


def run_tier(t):
    nfft, hop, look = t['nfft'], t['hop'], t['look']
    nbin = nfft // 2 + 1
    W = bands(nbin)
    alg_ms = (nfft + hop) / SR * 1000
    look_ms = look * hop / SR * 1000
    tot_ms = alg_ms + look_ms
    # 训练集
    Xs, Ts = [], []
    for i in range(30):
        _, _, _, S, V, Y = pair(300 + i, NOISES[i % 3], SNRS[i % 3], nfft, hop)
        Xs.append(featurize(Y, W, look))
        Ts.append(np.sqrt(np.abs(S) ** 2 / (np.abs(S) ** 2 + np.abs(V) ** 2 + E.EPS)))
    P = fit(np.concatenate(Xs), np.concatenate(Ts))
    din = CTX * 2 * NB + look * 2 * NB
    mac = din * H1 + H1 * H2 + H2 * nbin
    fps = SR / hop
    fft_mac = int(nfft / 2 * np.log2(nfft)) * 2

    def ev(kinds, how):
        rs = []
        for k in kinds:
            for sd in (900, 901, 902):
                x, y, m, S, V, Y = pair(sd, k, 5.0, nfft, hop)
                if how == 'noisy':
                    z = y
                elif how == 'classic':
                    lam = est_imcra(np.abs(Y) ** 2, D=max(16, int(0.5 * SR / hop)))
                    xi, gam = dd_xi(Y, lam, 0.98)
                    z = E.istft(g_logmmse(xi, gam) * Y, nfft, hop, n=len(y))
                else:
                    _, _, _, _, o = fwd(P, featurize(Y, W, look))
                    z = E.istft(sig(o) * Y, nfft, hop, n=len(y))
                z = z[:len(y)]
                rs.append((E.seg_snr(x, z, m), E.stoi_like(x, z, mask=m),
                           E.lsd(x, z, mask=m)))
        a = np.mean(rs, 0)
        return dict(segsnr=round(float(a[0]), 2), stoi=round(float(a[1]), 3),
                    lsd=round(float(a[2]), 2))

    r = dict(t)
    r.update({'nbin': nbin, 'alg_ms': round(alg_ms, 1), 'look_ms': round(look_ms, 1),
              'total_ms': round(tot_ms, 1), 'fits': tot_ms <= t['budget_ms'],
              'win_ms': round(nfft / SR * 1000, 1),
              'df_hz': round(SR / nfft, 1),
              'mac': int(mac), 'mmac_s': round(mac * fps / 1e6, 2),
              'fft_mmac_s': round(fft_mac * fps / 1e6, 2),
              'mw50': round(mac * fps * 50e-12 * 1e3, 3),
              'params': int(din * H1 + H1 + H1 * H2 + H2 + H2 * nbin + nbin),
              'noisy': ev(NOISES, 'noisy'), 'classic': ev(NOISES, 'classic'),
              'nn': ev(NOISES, 'nn'), 'nn_unseen': ev((UNSEEN,), 'nn'),
              'classic_unseen': ev((UNSEEN,), 'classic')})
    r['gain_classic'] = round(r['classic']['segsnr'] - r['noisy']['segsnr'], 2)
    r['gain_nn'] = round(r['nn']['segsnr'] - r['noisy']['segsnr'], 2)
    return r


print('三档场景，每档按延迟预算定窗长，再把两套方法跑一遍')
OUT['tiers'] = []
for t in TIERS:
    r = run_tier(t)
    OUT['tiers'].append(r)
    print('  %-14s 预算 %5.1f ms  窗 %4.1f ms(%d 点, Δf %.0f Hz)  '
          '延迟 %5.1f ms %s  算力 %5.2f MMAC/s  经典 %+.2f dB  网络 %+.2f dB'
          % (r['name'], r['budget_ms'], r['win_ms'], r['nfft'], r['df_hz'],
             r['total_ms'], '✓' if r['fits'] else '✗', r['mmac_s'],
             r['gain_classic'], r['gain_nn']))

# ══ 谐波可分性：每一档的窗能不能分开谐波 ══════════════════════
F0_LO = 110.0
for r in OUT['tiers']:
    r['resolves_f0'] = bool(r['df_hz'] <= F0_LO / 2)
    r['need_win_ms'] = round(2.0 / F0_LO * 1000, 1)
print('\n要分开 %g Hz 的谐波，Δf 得 ≤ %g Hz，也就是窗 ≥ %.1f ms：'
      % (F0_LO, F0_LO / 2, 2.0 / F0_LO * 1000)
      + '  '.join('%s %s' % (r['name'], '✓' if r['resolves_f0'] else '✗')
                  for r in OUT['tiers']))

# ══ 把三档的配置互相换一换：延迟够不够、算力多少 ═══════════════
print('\n三种配置 × 三档预算（延迟 ms / 是否塞得进）')
OUT['cross'] = []
for cfg in OUT['tiers']:
    row = {'cfg': cfg['name'], 'total_ms': cfg['total_ms'],
           'mmac_s': cfg['mmac_s'], 'gain_nn': cfg['gain_nn'], 'fit': []}
    for b in OUT['tiers']:
        row['fit'].append({'budget': b['name'], 'budget_ms': b['budget_ms'],
                           'ok': bool(cfg['total_ms'] <= b['budget_ms'])})
    OUT['cross'].append(row)
    print('  %-14s 延迟 %6.1f ms  算力 %5.2f MMAC/s  增益 %+.2f dB   %s'
          % (row['cfg'], row['total_ms'], row['mmac_s'], row['gain_nn'],
             '  '.join('%s %s' % (f['budget'], '✓' if f['ok'] else '✗')
                       for f in row['fit'])))

# ══ 卡住的是哪一条 ════════════════════════════════════════════
ear, call, meet = OUT['tiers']
OUT['bind'] = [
    {'tier': ear['name'],
     'binding': '延迟 → 频率分辨率',
     'detail': 'Δf %.0f Hz，分不开谐波，经典法只拿到 %+.2f dB'
               % (ear['df_hz'], ear['gain_classic']),
     'headroom': '算力只用 %.2f MMAC/s，远不是瓶颈' % ear['mmac_s']},
    {'tier': call['name'],
     'binding': '泛化 → 数据',
     'detail': '见过的噪声上网络比经典法好 %+.2f dB，没见过的只好 %+.2f dB'
               % (call['nn']['segsnr'] - call['classic']['segsnr'],
                  call['nn_unseen']['segsnr'] - call['classic_unseen']['segsnr']),
     'headroom': '延迟 %.1f ms / 预算 %.0f ms，还有余量'
                 % (call['total_ms'], call['budget_ms'])},
    {'tier': meet['name'],
     'binding': '指标 → 要什么',
     'detail': '网络 SegSNR %+.2f dB、LSD %.2f；经典法 SegSNR %+.2f dB、LSD %.2f'
               % (meet['gain_nn'], meet['nn']['lsd'],
                  meet['gain_classic'], meet['classic']['lsd']),
     'headroom': '延迟与算力都有大把余量（%.1f ms / %.2f MMAC/s）'
                 % (meet['total_ms'], meet['mmac_s'])},
]
print('\n每一档真正卡住的：')
for b in OUT['bind']:
    print('  %-14s ← %-16s %s' % (b['tier'], b['binding'], b['detail']))

OUT['summary'] = {
    'ear_df': ear['df_hz'], 'ear_gain': ear['gain_classic'],
    'call_gain': call['gain_nn'], 'meet_gain': meet['gain_nn'],
    'ear_vs_meet': round(meet['gain_nn'] - ear['gain_nn'], 2),
    'mmac_spread': round(ear['mmac_s'] / max(meet['mmac_s'], 1e-9), 1),
    'f0_lo': F0_LO,
}
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_tier.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_tier.json（%.0f s）' % OUT['runtime_s'])
