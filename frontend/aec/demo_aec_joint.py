#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C10 节的端到端联合实验：阵列 → 回声消除 → 残余抑制 → 单通道降噪，四段按不同顺序串起来跑。

   场景：4 麦线阵（间距 35 mm），喇叭紧挨阵列，近端说话人在 60° 方向，房间噪声（粉噪）；
         回声路径和近端混响都是每个麦克风各自的指数衰减冲激响应（T60 0.25 s）。
         喇叭带 tanh 软限幅（轻度非线性）。远端语音连续播放，近端每 1.6 s 说 0.7 s，近端与回声同电平（0 dB），
         噪声比近端语音低 10 dB。
   六种串法（C = 回声消除，A = 波束，R = 残余抑制，N = 单通道降噪）：
     ① 只做 N（参考麦克风）           ② C→R→N（单麦）
     ③ A(固定 DAS)→C→R→N              ④ A(自适应 MVDR)→C→R→N     ← A14 说"波束在前会让 AEC 追不上"
     ⑤ C(每麦一个)→A(固定 DAS)→R→N    ⑥ C(每麦一个)→A(自适应 MVDR)→R→N   ← 本书推荐的顺序
   MVDR：每个频点的噪声协方差用"近端没说话"的帧递推（λ=0.97），权重随远端能量的起伏而变，是真的时变。
   指标：只有回声的段里，输出相对参考麦克风上回声的下降；近端说话段里，输出相对"近端语音在参考麦克风上的<strong>直达声</strong>"的分段信噪比与 STOI（波束会去混响，拿带混响的当标准答案会罚波束）。
"""
import numpy as np, json, time
import enhlib as E
import aeclib as A
import aecadv as V

t0 = time.time()
OUT = {}
SR = A.SR
M, DSP = 4, 0.035
THETA = np.deg2rad(60.0)
C0 = 343.0
NFFT, HOP = 512, 256
SEEDS = (0, 1, 2)
DUR = 20.0
DRIVE = 0.8
NER_DB, NOISE_DB = 0.0, -10.0
LAM = 0.97
TAU = np.arange(M) * DSP * np.cos(THETA) / C0 * SR          # 近端平面波到各麦的延迟（采样点，相对 0 号麦）


def frac_delay(x, d):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x))
    return np.fft.irfft(X * np.exp(-2j * np.pi * f * d), len(x))


def scene(seed):
    g = np.random.default_rng(seed)
    n = int(DUR * SR)
    x = A.farend('speech', DUR, seed=seed + 1)
    xp, thd = A.loudspeaker(x, DRIVE)
    he = [A.rir(0.25, seed=seed * 10 + m, pre_ms=4.0 + 0.05 * m) for m in range(M)]
    hn = [A.rir(0.25, seed=seed * 10 + m + 500, pre_ms=3.0, direct=0.45) for m in range(M)]
    echo = np.stack([np.convolve(xp, h)[:n] for h in he])
    s = np.zeros(n)
    dt = np.zeros(n, bool)
    t = int(3.0 * SR)
    k = 0
    while t < n - int(0.8 * SR):
        seg, _ = E.make_speech(dur=0.7, seed=seed * 131 + k)
        ln = min(len(seg), n - t)
        s[t:t + ln] += seg[:ln]
        dt[t:t + ln] = True
        t += int(1.6 * SR)
        k += 1
    near = np.stack([np.convolve(frac_delay(s, TAU[m]), hn[m])[:n] for m in range(M)])
    sc_ = np.sqrt(np.mean(echo[0][dt] ** 2) / (np.mean(near[0][dt] ** 2) + 1e-12)) * 10 ** (NER_DB / 20)
    near *= sc_
    hd = np.zeros_like(hn[0])                      # 目标：近端语音在参考麦克风上的<strong>直达声</strong>部分（波束会去混响，不能拿带混响的当标准答案）
    i0 = int(np.argmax(np.abs(hn[0])))
    hd[i0] = hn[0][i0]
    near_dir = np.convolve(s, hd)[:n] * sc_
    nz = np.stack([E.make_noise('pink', n, seed=seed * 7 + 40 + m) for m in range(M)])
    nz *= np.sqrt(np.mean(near[0][dt] ** 2) * 10 ** (NOISE_DB / 10)) / (nz[0].std() + 1e-12)
    tiny = g.standard_normal((M, n)) * np.sqrt(np.mean(echo[0] ** 2) / 1e4)
    y = echo + near + nz + tiny
    return dict(x=x, y=y, echo=echo, near=near, near_dir=near_dir, noise=nz, dt=dt, he=he, thd=thd)


# ── 频域工具 ──
def stft_all(Y):
    return np.stack([E.stft(y, NFFT, HOP) for y in Y])               # (M, T, K)


def steering():
    f = np.fft.rfftfreq(NFFT, 1 / SR)
    return np.exp(-2j * np.pi * f[None, :] * (TAU[:, None] / SR))     # (M, K)


STEER = steering()


def beam_das(Ys):
    return (np.conj(STEER)[:, None, :] * Ys).sum(0) / M


def beam_mvdr(Ys, noise_frames):
    """逐频点、逐帧更新的 MVDR：噪声协方差在 noise_frames（近端没说话的帧）上递推，近端说话时保持"""
    Mn, T_, K = Ys.shape
    R = np.zeros((K, M, M), complex) + 1e-3 * np.eye(M)[None]
    out = np.zeros((T_, K), complex)
    Ws = np.zeros((T_, M, K), complex)
    d = STEER.T                                                       # (K, M)
    for t in range(T_):
        yt = Ys[:, t, :].T                                            # (K, M)
        if noise_frames[t]:
            R = LAM * R + (1 - LAM) * (yt[:, :, None] * np.conj(yt[:, None, :]))
        tr = np.real(np.trace(R, axis1=1, axis2=2))[:, None, None] / M
        Ri = np.linalg.inv(R + 1e-2 * tr * np.eye(M)[None])
        num = np.einsum('kmn,kn->km', Ri, d)
        den = np.einsum('km,km->k', np.conj(d), num)
        w = num / den[:, None]
        Ws[t] = w.T
        out[t] = (np.conj(w) * yt).sum(1)
    return out, Ws


def apply_w(Ys, Ws):
    return (np.conj(Ws).transpose(1, 0, 2) * Ys).sum(0) if Ws.ndim == 3 and Ws.shape[0] == Ys.shape[1] and False else \
        np.einsum('tmk,mtk->tk', np.conj(Ws), Ys)


def istft1(Z, n):
    return E.istft(Z, NFFT, HOP, n=n)


def ns_stage(sig):
    Y = E.stft(sig, NFFT, HOP)
    P = np.abs(Y) ** 2
    lam = E.est_ms(P)
    xi, gam = E.dd_xi(Y, lam, 0.98)
    G = np.maximum(E.g_logmmse(xi, gam), 10 ** (-18 / 20))
    return E.istft(Y * G, NFFT, HOP, n=len(sig))


def res_stage(sig, yhat, gamma=0.2):
    Ee, Yh = E.stft(sig, NFFT, HOP), E.stft(yhat, NFFT, HOP)
    pe = np.abs(Ee) ** 2
    g = np.maximum((pe - gamma * np.abs(Yh) ** 2) / (pe + 1e-12), 10 ** (-18 / 10))
    return E.istft(Ee * np.sqrt(g), NFFT, HOP, n=len(sig))


def aec(x, y):
    r = V.run_fdkf(x, y, None, a=0.9995, lam=0.97)
    e = r['e']
    return e, y[:len(e)] - e


def pad(a, n):
    return np.pad(a[:n], (0, max(0, n - len(a))))


def pipelines(sc):
    n = len(sc['x'])
    x = sc['x']
    Y = sc['y']
    nfr = 1 + (n - NFFT) // HOP + 1
    dtf = np.array([sc['dt'][min(i * HOP, n - 1):min(i * HOP + NFFT, n)].any() for i in range(len(E.stft(Y[0], NFFT, HOP)))])
    quiet = ~dtf                                                        # 近端没说话的帧（MVDR 协方差更新用）
    out = {}
    # ① 只 N
    out['n_only'] = ns_stage(Y[0])
    # ② 单麦 C→R→N
    e0, yh0 = aec(x, Y[0])
    out['c_single'] = ns_stage(res_stage(pad(e0, n), pad(yh0, n)))
    Ys = stft_all(Y)
    # ③ DAS→C→R→N
    zb = istft1(beam_das(Ys), n)
    eb, ybh = aec(x, zb)
    out['das_c'] = ns_stage(res_stage(pad(eb, n), pad(ybh, n)))
    # ④ MVDR→C→R→N
    zm, _ = beam_mvdr(Ys, quiet)
    zb = istft1(zm, n)
    eb, ybh = aec(x, zb)
    out['mvdr_c'] = ns_stage(res_stage(pad(eb, n), pad(ybh, n)))
    # ⑤⑥ C×M → A → R → N
    Es, Yhs = [], []
    for m in range(M):
        e, yh = aec(x, Y[m])
        Es.append(pad(e, n)); Yhs.append(pad(yh, n))
    Es_, Yh_ = stft_all(np.stack(Es)), stft_all(np.stack(Yhs))
    zd = beam_das(Es_)
    out['c_das'] = ns_stage(res_stage(istft1(zd, n), istft1(beam_das(Yh_), n)))
    zm, Ws = beam_mvdr(Es_, quiet)
    out['c_mvdr'] = ns_stage(res_stage(istft1(zm, n), istft1(np.einsum('tmk,mtk->tk', np.conj(Ws), Yh_), n)))
    return out, Ws


def score(sc, o):
    n = min(len(o), len(sc['x']))
    o = o[:n]
    k = int(4.0 * SR)
    m1 = ~sc['dt'][:n].copy(); m1[:k] = False
    echo_down = 10 * np.log10((np.mean(sc['echo'][0][:n][m1] ** 2) + 1e-12) / (np.mean(o[m1] ** 2) + 1e-12))
    m2 = sc['dt'][:n]
    ref = sc['near_dir'][:n]
    return {'echo': float(echo_down), 'near': float(E.seg_snr(ref, o, m2)), 'stoi': float(E.stoi_like(ref, o, mask=m2))}


NAMES = [('n_only', '① 只做降噪（参考麦克风）'), ('c_single', '② 回声消除 → 残余抑制 → 降噪（单麦）'),
         ('das_c', '③ 固定波束 → 回声消除 → R → N'), ('mvdr_c', '④ 自适应波束 → 回声消除 → R → N'),
         ('c_das', '⑤ 每麦回声消除 → 固定波束 → R → N'), ('c_mvdr', '⑥ 每麦回声消除 → 自适应波束 → R → N')]
acc = {k: [] for k, _ in NAMES}
base = []
wch = []
for sd in SEEDS:
    sc = scene(sd)
    base.append({'echo': 0.0, 'near': float(E.seg_snr(sc['near_dir'], sc['y'][0], sc['dt'])),
                 'stoi': float(E.stoi_like(sc['near_dir'], sc['y'][0], mask=sc['dt']))})
    outs, Ws = pipelines(sc)
    # 权重的时变程度：相邻帧权重向量的相对变化（近端不说话的帧）
    dW = np.linalg.norm(Ws[1:] - Ws[:-1], axis=(1, 2)) / (np.linalg.norm(Ws[:-1], axis=(1, 2)) + 1e-12)
    wch.append(float(np.median(dW)))
    for k, _ in NAMES:
        acc[k].append(score(sc, outs[k]))
    print('seed %d 完成 %.0f s' % (sd, time.time() - t0))
OUT['rows'] = []
OUT['base'] = {k: round(float(np.mean([b[k] for b in base])), 2) for k in ('near', 'stoi')}
for k, nm in NAMES:
    r = {'key': k, 'name': nm}
    for m_ in ('echo', 'near', 'stoi'):
        r[m_] = round(float(np.mean([a[m_] for a in acc[k]])), 3 if m_ == 'stoi' else 2)
    OUT['rows'].append(r)
    print('  %-34s 回声下降 %6.2f dB   近端 segSNR %6.2f dB   STOI %.3f' % (nm, r['echo'], r['near'], r['stoi']))
R = {r['key']: r for r in OUT['rows']}
OUT['note'] = {
    'base_near': OUT['base']['near'], 'base_stoi': OUT['base']['stoi'],
    'n_echo': R['n_only']['echo'], 'c1_echo': R['c_single']['echo'], 'c1_near': R['c_single']['near'],
    'das_echo': R['das_c']['echo'], 'mvdr_echo': R['mvdr_c']['echo'], 'cdas_echo': R['c_das']['echo'], 'cmvdr_echo': R['c_mvdr']['echo'],
    'das_near': R['das_c']['near'], 'mvdr_near': R['mvdr_c']['near'], 'cdas_near': R['c_das']['near'], 'cmvdr_near': R['c_mvdr']['near'],
    'cmvdr_stoi': R['c_mvdr']['stoi'], 'mvdr_stoi': R['mvdr_c']['stoi'],
    'order_gap_echo': round(R['c_mvdr']['echo'] - R['mvdr_c']['echo'], 2),
    'order_gap_near': round(R['c_mvdr']['near'] - R['mvdr_c']['near'], 2),
    'fixed_gap_echo': round(R['c_das']['echo'] - R['das_c']['echo'], 2),
    'w_change': round(float(np.mean(wch)), 4), 'thd': round(float(np.mean([scene(0)['thd']])), 2),
    'mvdr_vs_das_near': round(R['c_mvdr']['near'] - R['c_das']['near'], 2),
}
OUT['const'] = {'m': M, 'spacing_mm': DSP * 1000, 'theta_deg': 60, 'seeds': list(SEEDS), 'dur': DUR, 'drive': DRIVE,
                'ner_db': NER_DB, 'noise_db': NOISE_DB, 'lam': LAM, 'nfft': NFFT}
OUT['runtime_s'] = round(time.time() - t0, 1)
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_aec_joint.json', 'w'), ensure_ascii=False)
print('写出 demo_aec_joint.json  %.1f s' % OUT['runtime_s'])
