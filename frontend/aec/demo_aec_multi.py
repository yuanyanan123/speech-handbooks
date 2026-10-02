#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多参考通道（立体声）：非唯一性，以及去相关要花多大代价。

   远端是立体声，但两路来自同一个说话人，只差一个时延和增益（x2 = c * x1）。
   这时麦克风里的回声 y = (h1 + h2*c) * x1，滤波器只能辨识出 h1 + h2*c 这一个组合，
   不是 h1、h2 本身。远端说话人一换，c 变了，原来"凑出来"的那组解就不对了。

   ① 换人之前 ERLE 很好，失调却很差；换人之后 ERLE 掉多少
   ② 两种去相关：播放前加半波整流（非线性）或加独立噪声——各自换来多少、付出什么
"""
import numpy as np, json, time
import aeclib as A
import aecadv as V

OUT = {}
t0 = time.time()
SR = A.SR
DUR, CHG = 24.0, 12.0
SEEDS = (0, 1, 2)
BANDLO, BANDHI = 300, 3400


def scene(seed, nl_alpha=0.0, noise_db=None):
    n = int(DUR * SR)
    xa = A.farend('speech', CHG, seed=seed + 1)
    xb = A.farend('speech', DUR - CHG, seed=seed + 50)
    x1 = np.concatenate([xa, xb])

    def c(dl, gn):
        k = np.zeros(24)
        k[dl] = gn
        return k
    cA, cB = c(2, 0.9), c(14, 0.6)          # 两个说话人的位置：时延与增益都不同
    x2 = np.concatenate([np.convolve(xa, cA)[:len(xa)], np.convolve(xb, cB)[:len(xb)]])
    x1p, x2p = x1.copy(), x2.copy()
    if nl_alpha > 0:                          # Benesty 的半波整流去相关：两路用相反的半波
        x1p = x1 + nl_alpha * (x1 + np.abs(x1)) / 2
        x2p = x2 + nl_alpha * (x2 - np.abs(x2)) / 2
    g = np.random.default_rng(900 + seed)
    if noise_db is not None:
        x1p = x1p + g.standard_normal(n) * np.std(x1) * 10 ** (noise_db / 20)
        x2p = x2p + g.standard_normal(n) * np.std(x2) * 10 ** (noise_db / 20)
    h1, h2 = A.rir(0.25, seed=seed), A.rir(0.25, seed=seed + 77)
    d = np.convolve(x1p, h1)[:n] + np.convolve(x2p, h2)[:n]
    v = g.standard_normal(n)
    v *= np.sqrt(np.mean(d ** 2) / 1e4) / (v.std() + 1e-12)
    return dict(x1=x1p, x2=x2p, x1o=x1, x2o=x2, y=d + v, d=d, h1=h1, h2=h2)


def coherence(a, b, nfft=512):
    nseg = len(a) // nfft
    S11 = S22 = 0
    S12 = 0
    w = np.hanning(nfft)
    for i in range(nseg):
        A_ = np.fft.rfft(a[i * nfft:(i + 1) * nfft] * w)
        B_ = np.fft.rfft(b[i * nfft:(i + 1) * nfft] * w)
        S11 = S11 + np.abs(A_) ** 2
        S22 = S22 + np.abs(B_) ** 2
        S12 = S12 + A_ * np.conj(B_)
    c = np.abs(S12) ** 2 / (S11 * S22 + 1e-20)
    f = np.fft.rfftfreq(nfft, 1 / SR)
    return float(c[(f >= BANDLO) & (f <= BANDHI)].mean())


def erle(d, e, a, b):
    a, b = int(a * SR), int(b * SR)
    return float(10 * np.log10((np.mean(d[a:b] ** 2) + 1e-12) / (np.mean(e[a:b] ** 2) + 1e-12)))


def mis_at(snaps, s, t):
    bn = int(t * SR / V.B)
    k = [q for q in sorted(snaps) if q <= bn][-1]
    w = snaps[k]
    L = V.L
    hh = np.zeros((2, L))
    hh[0, :min(L, len(s['h1']))] = s['h1'][:L]
    hh[1, :min(L, len(s['h2']))] = s['h2'][:L]
    return float(20 * np.log10(np.linalg.norm(w - hh) / np.linalg.norm(hh)))


CASES = [('不去相关', {}),
         ('半波整流 α=0.1', dict(nl_alpha=0.1)), ('半波整流 α=0.3', dict(nl_alpha=0.3)),
         ('半波整流 α=0.5', dict(nl_alpha=0.5)),
         ('加噪 −30 dB', dict(noise_db=-30.0)), ('加噪 −20 dB', dict(noise_db=-20.0)),
         ('加噪 −10 dB', dict(noise_db=-10.0))]
OUT['rows'] = []
print('立体声回声：说话人在第 12 s 换人（c 变了）')
for nm, kw in CASES:
    acc = []
    for sd in SEEDS:
        s = scene(sd, **kw)
        e, sn = V.run_pb2([s['x1'], s['x2']], s['y'])
        # 播放被改了多少：先去掉最佳的整体增益（单纯变响不算失真），再量剩下的与原信号的信噪比
        def resid(xp, xo):
            gg = float(np.dot(xp, xo) / (np.dot(xo, xo) + 1e-20))
            return np.mean((xp - gg * xo) ** 2)
        dist = 10 * np.log10((np.mean(s['x1o'] ** 2) + np.mean(s['x2o'] ** 2)) /
                             (resid(s['x1'], s['x1o']) + resid(s['x2'], s['x2o']) + 1e-20))
        acc.append((erle(s['d'], e, 8, 12), erle(s['d'], e, 12, 14), erle(s['d'], e, 20, 24),
                    mis_at(sn, s, 11.9), min(dist, 60.0), coherence(s['x1'][:int(CHG * SR)], s['x2'][:int(CHG * SR)])))
    m = np.mean(acc, 0)
    r = {'name': nm, 'erle_before': round(float(m[0]), 2), 'erle_after2s': round(float(m[1]), 2),
         'erle_late': round(float(m[2]), 2), 'mis': round(float(m[3]), 2),
         'play_snr': round(float(m[4]), 1), 'coh': round(float(m[5]), 3)}
    r['drop'] = round(r['erle_before'] - r['erle_after2s'], 2)
    OUT['rows'].append(r)
    print('  %-14s 换人前 %5.1f  换人后 2 s %5.1f（掉 %5.1f）  重收敛后 %5.1f  失调 %6.1f  播放信噪比 %5.1f  相干性 %.3f'
          % (nm, r['erle_before'], r['erle_after2s'], r['drop'], r['erle_late'], r['mis'], r['play_snr'], r['coh']))
R = {r['name']: r for r in OUT['rows']}
b0 = R['不去相关']
OUT['note'] = {
    'base_before': b0['erle_before'], 'base_after': b0['erle_after2s'], 'base_drop': b0['drop'],
    'base_mis': b0['mis'], 'base_coh': b0['coh'],
    'hw05_drop': R['半波整流 α=0.5']['drop'], 'hw05_before': R['半波整流 α=0.5']['erle_before'],
    'hw05_snr': R['半波整流 α=0.5']['play_snr'], 'hw05_mis': R['半波整流 α=0.5']['mis'],
    'n10_drop': R['加噪 −10 dB']['drop'], 'n10_mis': R['加噪 −10 dB']['mis'],
    'n10_snr': R['加噪 −10 dB']['play_snr'], 'n20_mis': R['加噪 −20 dB']['mis'],
    'n20_snr': R['加噪 −20 dB']['play_snr'], 'n20_drop': R['加噪 −20 dB']['drop'],
    'n30_snr': R['加噪 −30 dB']['play_snr'],
}
OUT['const'] = {'seeds': list(SEEDS), 'dur': DUR, 'change_s': CHG, 'mu': 0.15,
                'b': V.B, 'nparts': V.NP, 'cA': '时延 2 采样点、增益 0.9', 'cB': '时延 14 采样点、增益 0.6',
                'band': [BANDLO, BANDHI]}
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_aec_multi.json', 'w'), ensure_ascii=False)
print('写出 demo_aec_multi.json  %.1f s' % OUT['runtime_s'])
