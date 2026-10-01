#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""15 节算例：梅尔谱到底丢了什么。
   ① 滤波器组的秩与条件数 ② 从哪个频率开始看不见谐波
   ③ 没有相位：Griffin-Lim 能补回多少 ④ 信息预算"""
import numpy as np, json, math
from ttssim import (SR, NFFT, HOP, NMEL, FMIN, FMAX, mel_fb, stft, istft,
                    melspec, utterance, hz_to_mel, mel_to_hz)

OUT = {'cfg': {'sr': SR, 'nfft': NFFT, 'hop': HOP, 'nmel': NMEL,
               'frame_ms': round(NFFT / SR * 1000, 2),
               'hop_ms': round(HOP / SR * 1000, 3),
               'fps': round(SR / HOP, 2), 'nbin': NFFT // 2 + 1}}
fb = mel_fb()
print('配置 %d Hz，nfft %d（%.1f ms），hop %d（%.2f ms，%.2f 帧/秒），%d 维梅尔'
      % (SR, NFFT, OUT['cfg']['frame_ms'], HOP, OUT['cfg']['hop_ms'],
         OUT['cfg']['fps'], NMEL))

# ══ ① 滤波器组本身 ══════════════════════════════════════════
r = np.linalg.matrix_rank(fb)
sv = np.linalg.svd(fb, compute_uv=False)
OUT['fb'] = {'shape': list(fb.shape), 'rank': int(r),
             'cond': round(float(sv[0] / sv[r - 1]), 1),
             'compress': round((NFFT // 2 + 1) / NMEL, 2)}
print('\n① 滤波器组 %s，秩 %d，条件数 %.1f，把 %d 维压到 %d 维（%.2f:1）'
      % (fb.shape, r, OUT['fb']['cond'], NFFT // 2 + 1, NMEL, OUT['fb']['compress']))
print('   它是满行秩的，所以"丢信息"不是因为秩亏，是因为 513→80 本来就不可逆')

# ══ ② 谐波什么时候看不见了 ═══════════════════════════════════
fftf = np.fft.rfftfreq(NFFT, 1 / SR)
m = np.linspace(hz_to_mel(FMIN), hz_to_mel(FMAX), NMEL + 2)
fc = mel_to_hz(m)
width = fc[2:] - fc[:-2]                      # 每个三角的 -6 dB 全宽
cen = fc[1:-1]
OUT['harm'] = {}
for f0 in (90.0, 120.0, 200.0, 300.0):
    idx = np.where(width > f0)[0]
    fcross = float(cen[idx[0]]) if len(idx) else float('nan')
    OUT['harm']['f0_%d' % int(f0)] = round(fcross, 0)
    print('   F0 = %3d Hz → 从约 %4.0f Hz（第 %d 个梅尔带）起，一个带里装进 >1 根谐波'
          % (f0, fcross, idx[0] + 1))
# 8 kHz 处一个梅尔带里有几根谐波
w8 = width[np.argmin(np.abs(cen - 7000))]
OUT['harm']['bins_at_7k'] = round(float(w8 / 120.0), 1)
OUT['harm']['width_at_7k'] = round(float(w8), 0)
print('   7 kHz 附近一个梅尔带宽 %.0f Hz，F0=120 时里面有 %.1f 根谐波——'
      % (w8, w8 / 120.0))
print('   <strong>高频的谐波结构在梅尔谱里根本不存在，声码器必须自己编出来</strong>')
# 分辨率也受帧长限制
OUT['harm']['dft_res'] = round(SR / NFFT, 1)
print('   另外 DFT 本身的分辨率是 %.1f Hz，F0 低于它时连线性谱都分不开谐波'
      % (SR / NFFT))

# ══ ③ 相位：Griffin-Lim ═════════════════════════════════════
u = utterance()
x = u['x']
S = stft(x)
A = np.abs(S)


def gl(mag, iters, seed=0, init='random'):
    g = np.random.default_rng(seed)
    if init == 'random':
        ph = np.exp(2j * np.pi * g.random(mag.shape))
    else:
        ph = np.ones_like(mag, dtype=complex)
    y = istft(mag * ph)
    for _ in range(iters):
        C = stft(y)
        ph = C / np.maximum(np.abs(C), 1e-9)
        y = istft(mag * ph)
    return y


def spec_snr(y, ref_mag):
    """只比幅度谱——相位重建本来就不可能对齐波形，比波形 SNR 没有意义"""
    B = np.abs(stft(y[:len(y)]))
    n = min(B.shape[1], ref_mag.shape[1])
    a, b = ref_mag[:, :n], B[:, :n]
    return 10 * math.log10(np.sum(a ** 2) / np.sum((a - b) ** 2))


OUT['gl'] = {}
print('\n③ 相位：从"正确的线性幅度谱"出发做 Griffin-Lim')
for it in (0, 1, 3, 10, 32, 100):
    y = gl(A, it)
    v = spec_snr(y, A)
    OUT['gl'][it] = round(v, 2)
    print('   %3d 次迭代  谱一致性 %6.2f dB' % (it, v))
print('   注意这是<strong>幅度谱已知</strong>的理想情形，仍然收敛到有限值——')
print('   因为"每一帧的幅度"这组约束和"相邻帧要拼得上"这组约束一般不相容')

# 从梅尔谱出发：先用伪逆回到线性谱
inv = np.linalg.pinv(fb)
M = fb @ A
A_hat = np.maximum(inv @ M, 0.0)
OUT['melinv'] = {'lsd_db': round(float(np.sqrt(np.mean(
    (20 * np.log10(np.maximum(A, 1e-6)) - 20 * np.log10(np.maximum(A_hat, 1e-6))) ** 2))), 2)}
print('\n   从 80 维梅尔用伪逆回到 513 维线性谱：对数谱距离 %.2f dB'
      % OUT['melinv']['lsd_db'])
for it in (32, 100):
    y = gl(A_hat, it)
    OUT['melinv']['gl_%d' % it] = round(spec_snr(y, A), 2)
    print('   再做 %d 次 Griffin-Lim，对真实幅度谱的一致性 %.2f dB'
          % (it, OUT['melinv']['gl_%d' % it]))
print('   <strong>这就是 Griffin-Lim 声码器听起来"有金属音"的全部来源</strong>')

# ══ ④ 信息预算 ═══════════════════════════════════════════════
fps = SR / HOP
OUT['budget'] = {
    'pcm_kbps': round(SR * 16 / 1000, 1),
    'mel_f32_kbps': round(NMEL * fps * 32 / 1000, 1),
    'mel_i8_kbps': round(NMEL * fps * 8 / 1000, 1),
    'vals_per_s': round(NMEL * fps, 0),
    'ratio_val': round(SR / (NMEL * fps), 2),
    'ratio_bit': round(SR * 16 / (NMEL * fps * 32), 2)}
print('\n④ 信息预算（每秒）')
print('   16 bit PCM        %.1f kbps' % OUT['budget']['pcm_kbps'])
print('   80 维梅尔 float32 %.1f kbps  ← 数值个数少 %.2f 倍，但比特只少 %.2f 倍'
      % (OUT['budget']['mel_f32_kbps'], OUT['budget']['ratio_val'],
         OUT['budget']['ratio_bit']))
print('   80 维梅尔 int8    %.1f kbps' % OUT['budget']['mel_i8_kbps'])
print('   所以梅尔谱的价值<strong>不是压缩</strong>——是它平滑、可预测、')
print('   相邻帧强相关，适合让一个网络去回归。真正的压缩要等到 18 节的 RVQ。')

json.dump(OUT, open('demo_mel.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_mel.json')
