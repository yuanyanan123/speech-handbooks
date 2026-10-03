#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《全栈音频链路手册》第 21 节"数值算例"用到的全部数字。
   这里没有任何实验：每个数都是把公式代入给定参数的算术结果。正文从 calc.json 里取数。"""
import json, math
import numpy as np
from scipy import special as sp

C = 343.0
FS = 16000
O = {}

# ── 场景 ─────────────────────────────────────────────────────────
M, D, THETA = 4, 0.035, 60.0                       # 4 麦线阵，间距 3.5 cm，目标方向 60°（与阵列轴的夹角）
T_S = 3.0
O['scene'] = dict(M=M, d_cm=3.5, theta=THETA, fs=FS, dur=T_S)

# ── 1. 到达时延与导向矢量 ───────────────────────────────────────
tau = [m * D * math.cos(math.radians(THETA)) / C for m in range(M)]
O['delay'] = dict(tau_us=[round(t * 1e6, 2) for t in tau], tau_samples=[round(t * FS, 3) for t in tau],
                  alias_hz=round(C / (2 * D), 0),
                  phase_1k=[round(2 * math.pi * 1000 * t, 4) for t in tau])

# ── 2. DAS 的白噪声增益与弥散场 DI（broadside，τ=0）─────────────
def gamma(f, d):
    x = 2 * math.pi * f * d / C
    return 1.0 if x == 0 else math.sin(x) / x

def di_das(f):
    G = np.array([[gamma(f, abs(i - j) * D) for j in range(M)] for i in range(M)])
    w = np.ones(M) / M
    return float(10 * np.log10(abs(w @ np.ones(M)) ** 2 / (w @ G @ w)))

O['das'] = dict(wng_db=round(10 * math.log10(M), 2),
                di={str(f): round(di_das(f), 2) for f in (250, 500, 1000, 2000, 4000)})

# ── 3. 梅尔刻度 ─────────────────────────────────────────────────
mel = lambda f: 2595 * math.log10(1 + f / 700)
imel = lambda m: 700 * (10 ** (m / 2595) - 1)
fmin, fmax, J = 60.0, 7600.0, 80
edges = [imel(mel(fmin) + (mel(fmax) - mel(fmin)) * i / (J + 1)) for i in range(J + 2)]
O['mel'] = dict(mel8k=round(mel(8000), 1), first_center=round(edges[1], 1), last_center=round(edges[J], 1),
                step_mel=round((mel(fmax) - mel(fmin)) / (J + 1), 2),
                width_first=round(edges[2] - edges[0], 1), width_last=round(edges[J + 1] - edges[J - 1], 1))

# ── 4. NLMS 的收敛与稳态 ───────────────────────────────────────
L = 2048
nl = {}
for mu in (0.1, 0.5, 1.0):
    tau_n = L / (mu * (2 - mu))
    Mx = mu / (2 - mu)
    erle_max = 10 * math.log10(1e4 / Mx)           # 回声对噪声 40 dB 时，稳态额外误差限制的 ERLE
    nl[str(mu)] = dict(tau_samples=round(tau_n), tau_ms=round(tau_n / FS * 1000, 1), M=round(Mx, 4), erle_db=round(erle_max, 1))
O['nlms'] = dict(L=L, L_ms=L / FS * 1000, rows=nl)

# ── 5. 回声的电平：距离与 SER ───────────────────────────────────
spl = lambda p: 20 * math.log10(p / 20e-6)
O['spl'] = dict(p1pa=round(spl(1.0), 1), double_dist_db=round(20 * math.log10(2), 2),
                tv1m=60.0, user2m=60.0, ser_db=round(20 * math.log10(2.0 / 1.0), 2))

# ── 6. 时钟漂移 ─────────────────────────────────────────────────
ppm = 50
O['drift'] = dict(ppm=ppm, slip_per_s=round(FS * ppm * 1e-6, 3), slip_10min=round(FS * ppm * 1e-6 * 600),
                  ms_10min=round(FS * ppm * 1e-6 * 600 / FS * 1000, 1))

# ── 7. 维纳 / STSA / LSA 增益（γ = 1+ξ，即观测功率等于期望）─────
def gains(xi_db):
    xi = 10 ** (xi_db / 10)
    gam = 1 + xi
    v = xi / (1 + xi) * gam
    gw = xi / (1 + xi)
    e1 = sp.exp1(v)
    glsa = gw * math.exp(0.5 * e1)
    gstsa = (math.sqrt(math.pi) / 2) * (math.sqrt(v) / gam) * math.exp(-v / 2) * ((1 + v) * sp.i0(v / 2) + v * sp.i1(v / 2))
    return dict(xi_db=xi_db, gw=round(gw, 3), glsa=round(glsa, 3), gstsa=round(gstsa, 3),
                gw_db=round(20 * math.log10(gw), 1), glsa_db=round(20 * math.log10(glsa), 1), gstsa_db=round(20 * math.log10(gstsa), 1))
O['gain'] = [gains(x) for x in (-10, -5, 0, 5, 10, 20)]

# ── 8. 形状与帧 ─────────────────────────────────────────────────
N = int(T_S * FS)
T_stft = 1 + (N - 512) // 256
T_mel = 1 + (N - 400) // 160
T_enc = -(-T_mel // 4)
O['shape'] = dict(N=N, T_stft=T_stft, F=257, T_mel=T_mel, T_enc=T_enc, stft_complex=M * 257 * T_stft)

# ── 9. CTC 路径数（所有帧概率为 1 时，映射到标签的路径个数）──────
def ctc_paths(T, labels):
    ext = [0]
    for c in labels:
        ext += [c, 0]
    S = len(ext)
    a = [0] * S
    a[0] = 1
    if S > 1:
        a[1] = 1
    for _ in range(T - 1):
        n = [0] * S
        for s in range(S):
            v = a[s] + (a[s - 1] if s >= 1 else 0)
            if s >= 2 and ext[s] != 0 and ext[s] != ext[s - 2]:
                v += a[s - 2]
            n[s] = v
        a = n
    return a[-1] + (a[-2] if S >= 2 else 0)

U = 7                                                   # "今天天气怎么样"：7 个字
labels = [1, 2, 2, 3, 4, 5, 6]                          # 今 天 天 气 怎 么 样（两个"天"相同）
P = ctc_paths(T_enc, labels)
O['ctc'] = dict(T=T_enc, U=U, log10_paths=round(math.log10(P), 1))

# ── 10. WER ──────────────────────────────────────────────────────
O['wer'] = dict(N=10, S=1, D=1, I=1, wer=0.3)

# ── 11. TTS 的帧、时长、码率 ────────────────────────────────────
fs_tts, hop = 22050, 256
T_tts = round(T_S * fs_tts / hop)
phones = 14
O['tts'] = dict(fs=fs_tts, hop=hop, frames=T_tts, samples=int(T_S * fs_tts), phones=phones, avg_dur_frames=round(T_tts / phones, 1),
                fps=round(fs_tts / hop, 2), nfe=10, forwards_cfg=20,
                codec_frames=int(T_S * 75), codec_tokens=int(T_S * 75) * 8, codec_bits=int(T_S * 6000), codec_bytes=int(T_S * 6000 / 8),
                upsample=[8, 8, 2, 2], upsample_prod=8 * 8 * 2 * 2)
O['resample'] = dict(ratio_num=320, ratio_den=441, ref_samples=T_S * FS)

# ── 12. 帧延迟（纯算术）─────────────────────────────────────────
O['lat'] = dict(stft_win_ms=512 / FS * 1000, stft_hop_ms=256 / FS * 1000, mel_win_ms=400 / FS * 1000, mel_hop_ms=10.0, enc_frame_ms=40.0)

# ── 13. 网络带宽算术 ─────────────────────────────────────────────
br, tf = 24000, 0.020
payload = br * tf / 8
O['net'] = dict(bitrate=br, frame_ms=20, payload_bytes=int(payload), header=40, bw_kbps=round((payload + 40) * 8 / tf / 1000, 1),
                pkts_per_s=int(1 / tf), g711_kbps=64, g711_payload=int(64000 * tf / 8), g711_bw_kbps=round((64000 * tf / 8 + 40) * 8 / tf / 1000, 1),
                zoh_droop_db=round(20 * math.log10(2 / math.pi), 2), sqnr16=round(6.02 * 16 + 1.76, 1), sqnr24=round(6.02 * 24 + 1.76, 1),
                ds_gain_osr64_L1=round(30 * math.log10(64), 1))

json.dump(O, open('calc.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(O, ensure_ascii=False)[:1500])
