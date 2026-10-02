#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回声消除之后的那一级：残余回声抑制（RES）与单通道降噪（NS）谁先谁后，能不能只留一个。

   AEC（频域卡尔曼）之后，输出里还剩三样东西：近端语音、残余回声、近端房间噪声。
   · RES 知道回声估计 ŷ，用它去压残余回声——但它不管稳态噪声
   · NS（最小统计量 + 判决引导 + log-MMSE，来自单通道那一部分）假设噪声平稳——
     回声一点都不平稳，所以它会把残余回声当语音留下来
   这里量：把 NS 单独用、RES 单独用、两种先后顺序串起来用，各自的结果。
"""
import numpy as np, json, time
import enhlib as E
import aeclib as A
import aecadv as V

OUT = {}
t0 = time.time()
SR = A.SR
NFFT, HOP = 512, 256
SEEDS = (0, 1, 2)
DUR = 20.0
DRIVE = 1.8                  # 喇叭非线性（THD ≈ 9%）：残余回声里有线性 AEC 拿不到的那部分
NOISE_SNR = 10.0             # 近端房间噪声相对近端语音
FLOOR_DB = -18.0
GAM = 0.2


def scene(seed, kind='all'):
    """kind: echo（只有回声）/ noise（只有近端语音 + 房间噪声，远端不播）/ all（三样都有）"""
    x = A.farend('speech', DUR, seed=seed + 1)
    h = A.rir(0.25, seed=seed)
    xp, thd = A.loudspeaker(x, DRIVE)
    d = np.convolve(xp, h)[:len(x)]
    n = len(d)
    near = np.zeros(n)
    dt = np.zeros(n, bool)
    t = int(4.0 * SR)
    k = 0
    while t < n - int(0.8 * SR):
        seg, _ = E.make_speech(dur=0.7, seed=seed * 131 + k)
        ln = min(len(seg), n - t)
        near[t:t + ln] += seg[:ln]
        dt[t:t + ln] = True
        t += int(1.6 * SR)
        k += 1
    near *= np.sqrt(np.mean(d[dt] ** 2) / (np.mean(near[dt] ** 2) + 1e-12))     # 近端 = 回声（0 dB）
    noise = E.make_noise('pink', n, seed=seed + 40)
    noise *= np.sqrt(np.mean(near[dt] ** 2) / 10 ** (NOISE_SNR / 10)) / (noise.std() + 1e-12)
    g = np.random.default_rng(1500 + seed)
    tiny = g.standard_normal(n) * np.sqrt(np.mean(d ** 2) / 1e4) / 1.0      # 底噪 −40 dB，三种都有
    if kind == 'echo':
        near = np.zeros(n)
        noise = np.zeros(n)
        dt = np.zeros(n, bool)
    elif kind == 'noise':
        d = np.zeros(n)
        x = np.zeros(n)
    y = d + near + noise + tiny
    if kind == 'noise':
        e, yh = y.copy(), np.zeros(n)
    else:
        r = V.run_fdkf(x, y, h, a=0.9995, lam=0.97)
        e = r['e']
        yh = y[:len(e)] - e
    m = len(e)
    return dict(x=x[:m], y=y[:m], d=d[:m], near=near[:m], noise=noise[:m], dt=dt[:m], e=e, yhat=yh[:m], thd=thd)


def ns(sig, floor_db=-18.0):
    """单通道那一部分的标准配方：最小统计量 + 判决引导 + log-MMSE"""
    Y = E.stft(sig, NFFT, HOP)
    P = np.abs(Y) ** 2
    lam = E.est_ms(P)
    xi, gam = E.dd_xi(Y, lam, 0.98)
    G = np.maximum(E.g_logmmse(xi, gam), 10 ** (floor_db / 20))
    return E.istft(Y * G, NFFT, HOP, n=len(sig))


def res(sig, yhat, gamma=GAM, floor_db=FLOOR_DB):
    Ee = E.stft(sig, NFFT, HOP)
    Yh = E.stft(yhat, NFFT, HOP)
    pe = np.abs(Ee) ** 2
    g = np.maximum((pe - gamma * np.abs(Yh) ** 2) / (pe + 1e-12), 10 ** (floor_db / 10))
    return E.istft(Ee * np.sqrt(g), NFFT, HOP, n=len(sig))


def echo_down(s, out):
    """只有回声的场景：单讲段里输出相对原回声下降了多少 dB（4 s 之后）"""
    n = min(len(out), len(s['d']))
    k = int(4.0 * SR)
    return float(10 * np.log10((np.mean(s['d'][k:n] ** 2) + 1e-12) / (np.mean(out[k:n] ** 2) + 1e-12)))


def near_q(s, out):
    """有近端语音的场景：近端语音保住多少（相对"只有近端"的 segSNR 与 STOI）"""
    n = min(len(out), len(s['near']))
    m2 = s['dt'][:n]
    return float(E.seg_snr(s['near'][:n], out[:n], m2)), float(E.stoi_like(s['near'][:n], out[:n], mask=m2))


PIPES = [
    ('aec', '只有 AEC', lambda s: s['e']),
    ('ns', 'AEC → NS', lambda s: ns(s['e'])),
    ('res', 'AEC → RES', lambda s: res(s['e'], s['yhat'])),
    ('res_ns', 'AEC → RES → NS', lambda s: ns(res(s['e'], s['yhat']))),
    ('ns_res', 'AEC → NS → RES', lambda s: res(ns(s['e']), s['yhat'])),
]
print('AEC（频域卡尔曼）之后的一级：')
OUT['rows'] = []
SCE = [scene(sd, 'echo') for sd in SEEDS]
SCN = [scene(sd, 'noise') for sd in SEEDS]
SCA = [scene(sd, 'all') for sd in SEEDS]
OUT['thd'] = round(float(np.mean([s['thd'] for s in SCA])), 2)
# 不做任何处理时，各场景的基线
OUT['base'] = {
    'noise_near': round(float(np.mean([near_q(s, s['y'])[0] for s in SCN])), 2),
    'all_near': round(float(np.mean([near_q(s, s['y'])[0] for s in SCA])), 2),
}
for key, nm, fn in PIPES:
    r = {'key': key, 'name': nm,
         'echo': round(float(np.mean([echo_down(s, fn(s)) for s in SCE])), 2)}
    qn = [near_q(s, fn(s)) for s in SCN]
    qa = [near_q(s, fn(s)) for s in SCA]
    r['noise_near'] = round(float(np.mean([q[0] for q in qn])), 2)
    r['noise_stoi'] = round(float(np.mean([q[1] for q in qn])), 3)
    r['all_near'] = round(float(np.mean([q[0] for q in qa])), 2)
    r['all_stoi'] = round(float(np.mean([q[1] for q in qa])), 3)
    OUT['rows'].append(r)
    print('  %-16s 只有回声：下降 %6.2f dB | 只有噪声：近端 %6.2f dB (STOI %.3f) | 三样都有：近端 %6.2f dB (STOI %.3f)'
          % (nm, r['echo'], r['noise_near'], r['noise_stoi'], r['all_near'], r['all_stoi']))
R = {r['key']: r for r in OUT['rows']}
OUT['note'] = {
    'ns_echo': R['ns']['echo'], 'res_echo': R['res']['echo'], 'aec_echo': R['aec']['echo'],
    'resns_echo': R['res_ns']['echo'], 'nsres_echo': R['ns_res']['echo'],
    'ns_noise': R['ns']['noise_near'], 'res_noise': R['res']['noise_near'], 'aec_noise': R['aec']['noise_near'],
    'base_noise': OUT['base']['noise_near'],
    'aec_all': R['aec']['all_near'], 'ns_all': R['ns']['all_near'], 'res_all': R['res']['all_near'],
    'resns_all': R['res_ns']['all_near'], 'nsres_all': R['ns_res']['all_near'],
    'order_gap': round(R['res_ns']['all_near'] - R['ns_res']['all_near'], 2),
    'base_all': OUT['base']['all_near'],
}
OUT['const'] = {'seeds': list(SEEDS), 'dur': DUR, 'drive': DRIVE, 'noise_snr': NOISE_SNR,
                'gamma': GAM, 'floor_db': FLOOR_DB, 'nfft': NFFT, 'hop': HOP, 'ner_db': 0.0}
OUT['runtime_s'] = round(time.time() - t0, 1)
print('结论量：', json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_aec_chain.json', 'w'), ensure_ascii=False)
print('写出 demo_aec_chain.json  %.1f s' % OUT['runtime_s'])
