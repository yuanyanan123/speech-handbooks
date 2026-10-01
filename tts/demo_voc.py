#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""17 节算例：声码器为什么会"发糊、有电音"。
   两件事可以精确量出来：① 逐点非线性产生的混叠 ② 转置卷积的棋盘伪影。"""
import numpy as np, json, math
from ttssim import SR

OUT = {}
N = 1 << 15
t = np.arange(N) / SR


def spec(x):
    w = np.hanning(len(x))
    X = np.abs(np.fft.rfft(x * w))
    return X, np.fft.rfftfreq(len(x), 1 / SR)


def snake(x, a=1.0):
    """BigVGAN 的 snake 激活：x + sin²(ax)/a，周期性偏置，适合建模谐波"""
    return x + np.sin(a * x) ** 2 / a


def lrelu(x, s=0.1):
    return np.where(x > 0, x, s * x)


# ══ ① 逐点非线性 = 造谐波；超过奈奎斯特的那些会折回来 ══════
F0 = 3000.0
x = np.sin(2 * np.pi * F0 * t)
OUT['alias'] = {'sr': SR, 'f0': F0, 'nyq': SR / 2}
print('输入：%.0f Hz 纯音，采样率 %d（奈奎斯特 %.0f Hz）' % (F0, SR, SR / 2))
print('非线性会造出 2f、3f、4f…… 超过 %.0f Hz 的部分<strong>不会消失，会折回来</strong>'
      % (SR / 2))
for k in range(2, 8):
    f = k * F0
    fold = f
    while fold > SR / 2:
        fold = abs(SR - fold) if fold < SR else abs(fold % SR)
        if fold > SR / 2:
            fold = SR - fold
    print('   %d 次谐波 %5.0f Hz → 实际出现在 %5.0f Hz %s'
          % (k, f, fold, '（就是它）' if f > SR / 2 else ''))


def alias_ratio(y, f0=F0, tol=40.0):
    """把"落在谐波位置上"的能量算作信号，其余算混叠"""
    X, f = spec(y)
    P = X ** 2
    sig = np.zeros(len(f), bool)
    k = 1
    while k * f0 < SR / 2:
        sig |= np.abs(f - k * f0) < tol
        k += 1
    sig |= f < 60
    return 10 * math.log10(P[~sig].sum() / max(P[sig].sum(), 1e-20))


def upfirdn(x, up, taps=257, cut=0.45):
    """零插值 + 低通 = 理想上采样；cut 相对于<strong>原</strong>奈奎斯特"""
    y = np.zeros(len(x) * up)
    y[::up] = x * up
    n = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * cut * n / up) * np.hanning(taps)
    h /= h.sum()
    return np.convolve(y, h, 'same')


def downfir(y, dn, taps=257, cut=0.45):
    n = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * cut * n / dn) * np.hanning(taps)
    h /= h.sum()
    return np.convolve(y, h, 'same')[::dn]


OUT['alias']['cases'] = []
print('\n同一个非线性，三种用法：')
for name, fn in (('leaky ReLU', lrelu), ('snake', snake)):
    naive = fn(x)
    r0 = alias_ratio(naive)
    # 反混叠：上采样 → 非线性 → 低通 → 下采样
    best = {}
    for up in (2, 4):
        y = downfir(fn(upfirdn(x, up)), up)
        best[up] = alias_ratio(y[:N])
    OUT['alias']['cases'].append({'act': name, 'naive': round(r0, 2),
                                  'up2': round(best[2], 2), 'up4': round(best[4], 2)})
    print('   %-11s 直接做 %7.2f dB   上采 2× 再做 %7.2f dB   上采 4× %7.2f dB'
          % (name, r0, best[2], best[4]))
print('   （数字是"混叠能量 / 谐波能量"，越负越好）')
print('   <strong>这就是 BigVGAN 那套 anti-aliased 激活在买的东西</strong>，'
      '代价是内部采样率翻倍、算力翻倍。')

# ══ ② 转置卷积的棋盘伪影 ═════════════════════════════════════
# 步长 s、核长 k 的转置卷积：输出第 p 个相位上叠加的权重个数是 ceil((k-p)/s)。
# k 不能被 s 整除时，各相位的权重个数不同 → 输出功率被一个周期为 s 的方波调制。
OUT['checker'] = []
print('\n转置卷积的棋盘伪影：各输出相位上叠加的权重个数')
for stride, ks in ((2, 4), (2, 3), (2, 5), (4, 8), (4, 6), (8, 16), (8, 12), (8, 11)):
    cnt = np.array([math.ceil((ks - p) / stride) for p in range(stride)], float)
    # 随机权重下，各相位的输出功率 ∝ 权重个数；换成 dB 就是调制深度
    mod = 10 * math.log10(cnt.max() / cnt.min())
    ok = ks % stride == 0
    OUT['checker'].append({'stride': stride, 'k': ks, 'divisible': bool(ok),
                           'counts': [int(c) for c in cnt], 'mod_db': round(mod, 2)})
    print('   stride %d，核长 %2d %s 各相位权重数 %-14s 功率调制 %4.2f dB'
          % (stride, ks, '（整除 ✓）' if ok else '（不整除 ✗）',
             str([int(c) for c in cnt]), mod))
print('   整除时各相位一样多，调制为 0；不整除时输出带上周期为 stride 的调制，')
print('   在谱上就是 <strong>SR/stride 处的一根固定亮线</strong>——听感是固定音高的电流声。')
# 实测一遍验证上面的推导
g = np.random.default_rng(1)
for stride, ks in ((2, 3), (8, 11)):
    acc = np.zeros(stride)
    for s_ in range(1500):
        gg = np.random.default_rng(s_)
        w = gg.standard_normal(ks) / math.sqrt(ks)
        x_ = gg.standard_normal(2048)
        y = np.zeros(len(x_) * stride + ks)
        for i_, v in enumerate(x_):
            y[i_ * stride:i_ * stride + ks] += v * w
        y = y[:len(x_) * stride].reshape(-1, stride)
        acc += (y ** 2).mean(0)
    acc /= 1500
    print('   实测 stride %d 核长 %2d：各相位功率比 %.2f dB（推导 %.2f dB）'
          % (stride, ks, 10 * math.log10(acc.max() / acc.min()),
             [c['mod_db'] for c in OUT['checker'] if c['stride'] == stride and c['k'] == ks][0]))

# ══ ③ 相位：波形域的目标函数为什么必须是对抗的 ═══════════════
f = 200.0
a = np.sin(2 * np.pi * f * t)
OUT['phase'] = []
print('\n为什么声码器不能用 L2 训波形：同一个"听起来一样"的信号，相位一变 L2 就爆炸')
for ph in (0.0, math.pi / 8, math.pi / 4, math.pi / 2, math.pi):
    b = np.sin(2 * np.pi * f * t + ph)
    mse = 10 * math.log10(max(np.mean((a - b) ** 2), 1e-12) / np.mean(a ** 2))
    A, _ = spec(a); B, _ = spec(b)
    pk = A > A.max() * 1e-3                       # 只比有能量的那几根谱线
    sd = float(np.sqrt(np.mean((20 * np.log10(A[pk]) - 20 * np.log10(B[pk])) ** 2)))
    OUT['phase'].append({'deg': round(math.degrees(ph)), 'wave_db': round(mse, 2),
                         'spec_db': round(sd, 3)})
    print('   相位差 %3.0f°  波形 L2 %6.2f dB   幅度谱距离 %.3f dB  ← 听起来完全一样'
          % (math.degrees(ph), mse, sd))
print('   <strong>波形 L2 惩罚的是相位，而人耳几乎不听相位</strong>——')
print('   所以 HiFi-GAN 的损失里没有波形 L2，只有多尺度谱损失 + 判别器。')

json.dump(OUT, open('demo_voc.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_voc.json')
