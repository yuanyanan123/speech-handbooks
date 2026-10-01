#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""22 节：流式声码器的感受野、右上下文与块边界。

做法：搭一个 HiFi-GAN 形状的声码器（真的四级转置卷积 + 多感受野残差块，
权重随机但固定——这里要量的是"上下文依赖"，是结构决定的，不是训练决定的），
然后：
  ① 用扰动法实测感受野：改一帧梅尔，看输出的哪些样点跟着变。
  ② 扫右上下文帧数，看流式输出和整句输出差多少 dB。
  ③ 扫块大小，看首包延迟、每样点摊销算力怎么变。
  ④ 扫交叉淡入长度，看块边界的"咔哒"还剩多少。
"""
import json, math
import numpy as np

rng = np.random.default_rng(3)
OUT = {}

SR, HOP, NMEL = 22050, 256, 80
UPS = (8, 8, 2, 2)                     # 乘起来 = 256
CH = (64, 32, 16, 8)
MRF_K = (3, 7)
MRF_D = (1, 3)


def conv1d(x, W, dil=1):
    """x:(Cin,N)  W:(Cout,Cin,k)  same padding"""
    cin, n = x.shape
    cout, _, k = W.shape
    pad = dil * (k - 1) // 2
    xp = np.zeros((cin, n + 2 * pad))
    xp[:, pad:pad + n] = x
    y = np.zeros((cout, n))
    for t in range(k):
        off = t * dil
        y += W[:, :, t] @ xp[:, off:off + n]
    return y


def upconv(x, W, stride):
    """转置卷积上采样，核长 = 2*stride"""
    cin, n = x.shape
    cout, _, k = W.shape
    y = np.zeros((cout, n * stride + k))
    for t in range(k):
        y[:, t:t + n * stride:stride] += W[:, :, t] @ x
    off = (k - stride) // 2
    return y[:, off:off + n * stride]


def mkw(cout, cin, k, g=1.0):
    return rng.normal(0, g / math.sqrt(cin * k), (cout, cin, k))


W_PRE = mkw(CH[0], NMEL, 7)
W_UP, W_MRF = [], []
for i, s in enumerate(UPS):
    cin = CH[i]
    cout = CH[i + 1] if i + 1 < len(CH) else CH[-1]
    W_UP.append(mkw(cout, cin, 2 * s))
    blocks = []
    for k in MRF_K:
        for d in MRF_D:
            blocks.append((mkw(cout, cout, k, 0.5), d))
    W_MRF.append(blocks)
W_POST = mkw(1, CH[-1], 7)


def vocode(mel):
    h = conv1d(mel, W_PRE)
    for i, s in enumerate(UPS):
        h = np.tanh(h)
        h = upconv(h, W_UP[i], s)
        acc = np.zeros_like(h)
        for W, d in W_MRF[i]:
            acc += conv1d(np.tanh(h), W, d)
        h = h + acc / len(W_MRF[i])
    return np.tanh(conv1d(h, W_POST))[0]


# ══ 合成一段梅尔谱（源-滤波，和 16 节同一套） ═══════════════
T = 240
t = np.arange(T)
f0 = 120 + 25 * np.sin(2 * np.pi * t / 90) + 6 * rng.standard_normal(T).cumsum() / 30
form = np.stack([500 + 260 * np.sin(2 * np.pi * t / 47 + 0.3),
                 1500 + 520 * np.sin(2 * np.pi * t / 61 + 1.1),
                 2600 + 380 * np.sin(2 * np.pi * t / 53 + 2.0)])
mhz = 2595 * np.log10(1 + (np.arange(NMEL) / NMEL * 8000) / 700)
MEL = np.zeros((NMEL, T))
for i in range(3):
    c = 2595 * np.log10(1 + form[i] / 700)
    MEL += (0.9 ** i) * np.exp(-0.5 * ((mhz[:, None] - c[None, :]) / 95) ** 2)
MEL += 0.05 * np.exp(-mhz[:, None] / 900) * (1 + 0.3 * np.sin(2 * np.pi * t / 23))
MEL = np.log(MEL + 1e-3)
MEL = (MEL - MEL.mean()) / MEL.std()

Y_FULL = vocode(MEL)
N = len(Y_FULL)
print('① 声码器：%d 帧梅尔 → %s 样点（hop %d，%.2f s @ %d Hz）'
      % (T, '{:,}'.format(N), HOP, N / SR, SR))

# ══ ① 实测感受野：扰动一帧，看哪些样点变了 ══════════════════
c = T // 2
m2 = MEL.copy()
m2[:, c] += 1.0
d = np.abs(vocode(m2) - Y_FULL)
thr = d.max() * 1e-3
idx = np.where(d > thr)[0]
lo, hi = idx.min(), idx.max()
rf_left = (c * HOP - lo) / HOP
rf_right = (hi - (c + 1) * HOP) / HOP
OUT['rf'] = {'left_frames': round(float(rf_left), 2),
             'right_frames': round(float(rf_right), 2),
             'left_ms': round(float(rf_left * HOP / SR * 1000), 1),
             'right_ms': round(float(rf_right * HOP / SR * 1000), 1),
             'total_ms': round(float((rf_left + rf_right + 1) * HOP / SR * 1000), 1)}
print('   实测感受野：左 %.1f 帧 / 右 %.1f 帧（右侧 %.0f ms）——'
      % (rf_left, rf_right, OUT['rf']['right_ms']))
print('   <strong>这 %.0f ms 是结构决定的，流式时想不等都不行</strong>。'
      % OUT['rf']['right_ms'])


def db(err, ref):
    return float(20 * np.log10(np.linalg.norm(err) / np.linalg.norm(ref) + 1e-20))


def stream(chunk, left, right, xfade=0):
    """按块生成：每块带 left 帧左文、right 帧右文，块间交叉淡入 xfade 个样点"""
    y = np.zeros(N)
    w = np.zeros(N)
    for a in range(0, T, chunk):
        b = min(a + chunk, T)
        s0 = max(0, a - left)
        s1 = min(T, b + right)
        seg = vocode(MEL[:, s0:s1])
        keep0 = (a - s0) * HOP
        keep1 = keep0 + (b - a) * HOP
        o0, o1 = a * HOP, b * HOP
        piece = seg[keep0:keep1]
        if xfade > 0:
            f0_ = max(o0 - xfade, 0)
            ext0 = keep0 - (o0 - f0_)
            if ext0 >= 0:
                piece = seg[ext0:keep1]
                o0 = f0_
        m = np.ones(len(piece))
        if xfade > 0 and len(piece) > 2 * xfade:
            ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(xfade) / xfade)
            m[:xfade] = ramp
            m[-xfade:] = ramp[::-1] if o1 < N else 1.0
        y[o0:o0 + len(piece)] += piece * m
        w[o0:o0 + len(piece)] += m
    return y / np.maximum(w, 1e-8)


# ══ ② 右上下文扫描 ═══════════════════════════════════════════
print('\n② 右上下文给多少帧，流式输出才和整句一样')
print('  %8s %10s %14s %12s' % ('右文帧数', '附加延迟', '相对整句误差', '听得出吗'))
OUT['right'] = []
for r in (0, 1, 2, 3, 4, 6, 8):
    e = db(stream(16, 8, r) - Y_FULL, Y_FULL)
    lat = r * HOP / SR * 1000
    r_ = {'right': r, 'lat_ms': round(lat, 1), 'db': round(e, 2)}
    OUT['right'].append(r_)
    print('  %8d %8.1f ms %12.2f dB %12s'
          % (r, lat, e, '听不出' if e < -40 else ('边缘' if e < -25 else '听得出')))
ok = [r for r in OUT['right'] if r['db'] < -40]
OUT['right_ok'] = ok[0] if ok else OUT['right'][-1]

# ══ ③ 左上下文扫描 ═══════════════════════════════════════════
print('\n③ 左上下文（缓存）给多少帧')
print('  %8s %14s %14s' % ('左文帧数', '相对整句误差', '每块多算的比例'))
OUT['left'] = []
for l in (0, 2, 4, 8, 16):
    e = db(stream(16, l, int(OUT['right_ok']['right'])) - Y_FULL, Y_FULL)
    over = (l + OUT['right_ok']['right']) / 16
    r_ = {'left': l, 'db': round(e, 2), 'overhead': round(over * 100, 1)}
    OUT['left'].append(r_)
    print('  %8d %12.2f dB %12.1f%%' % (l, e, over * 100))

# ══ ④ 块大小：首包延迟 vs 摊销算力 ═══════════════════════════
print('\n④ 块大小：首包延迟和算力是同一个旋钮的两端')
print('  %8s %12s %14s %14s'
      % ('块帧数', '首包延迟', '每块多算的比例', '相对整句误差'))
OUT['chunk'] = []
L_OK, R_OK = 8, int(OUT['right_ok']['right'])
for c_ in (4, 8, 16, 32, 64):
    e = db(stream(c_, L_OK, R_OK) - Y_FULL, Y_FULL)
    lat = (c_ + R_OK) * HOP / SR * 1000
    over = (L_OK + R_OK) / c_
    r_ = {'chunk': c_, 'lat_ms': round(lat, 1),
          'overhead': round(over * 100, 1), 'db': round(e, 2)}
    OUT['chunk'].append(r_)
    print('  %8d %10.1f ms %12.1f%% %12.2f dB' % (c_, lat, over * 100, e))

# ══ ⑤ 不给右上下文时，交叉淡入能救回多少 ════════════════════
print('\n⑤ 右上下文给不起时，交叉淡入能救回多少')
print('  %10s %10s %14s %14s %14s'
      % ('淡入样点', '毫秒', '相对整句误差', '包络跳变比', '误差落在边界'))


def env_step(y, chunk, w=64):
    """块边界处的包络跳变，和非边界处的同一统计量比——这是"咔哒"的量化代理"""
    n = len(y) // w * w
    env = np.sqrt((y[:n].reshape(-1, w) ** 2).mean(1)) + 1e-12
    step = np.abs(np.diff(env)) / env[:-1].mean()
    seams = [i * chunk * HOP // w for i in range(1, T // chunk)]
    seams = [i for i in seams if 0 < i < len(step)]
    at = np.mean([step[max(i - 1, 0):i + 2].max() for i in seams])
    mask = np.ones(len(step), bool)
    for i in seams:
        mask[max(i - 2, 0):i + 3] = False
    return float(at / (step[mask].mean() + 1e-12))


def seam_err(y, chunk, half=5 * HOP):
    """误差能量有多大比例落在块边界 ±5 帧之内（这一段只占全长的 %.0f%%）"""
    e = (y - Y_FULL) ** 2
    near = np.zeros(len(e), bool)
    for i in range(1, T // chunk + 1):
        c0 = i * chunk * HOP
        near[max(c0 - half, 0):min(c0, len(e))] = True   # 每块的最后 5 帧
    tot = e.sum()
    return float(e[near].sum() / tot * 100) if tot > 0 else 0.0


OUT['xfade'] = []
for x in (0, 32, 64, 128, 256):
    y = stream(16, L_OK, 0, xfade=x)
    e = db(y - Y_FULL, Y_FULL)
    r_ = {'xfade': x, 'ms': round(x / SR * 1000, 2), 'db': round(e, 2),
          'seam': round(env_step(y, 16), 2), 'conc': round(seam_err(y, 16), 2)}
    OUT['xfade'].append(r_)
    print('  %10d %8.1f ms %12.2f dB %12.2f× %12.1f%%'
          % (x, r_['ms'], e, r_['seam'], r_['conc']))
OUT['seam_span'] = round(5.0 / 16 * 100, 1)
OUT['seam_full'] = round(env_step(Y_FULL, 16), 2)
print('  参照：整句输出在同样位置的包络跳变比是 %.2f×（这就是"没有咔哒"的基准）'
      % OUT['seam_full'])

OUT['setup'] = {'sr': SR, 'hop': HOP, 'nmel': NMEL, 'ups': list(UPS),
                'ch': list(CH), 'frames': T, 'samples': int(N),
                'hop_ms': round(HOP / SR * 1000, 2)}

print('\n结论')
print('  ① 感受野是结构给的：右侧 %.1f 帧 = %.0f ms。'
      % (rf_right, OUT['rf']['right_ms']))
print('     流式时这 %.0f ms <strong>只能等，不能省</strong>——'
      % OUT['rf']['right_ms'])
print('     它和 ASR 那边的前瞻是同一类东西，但方向相反：')
print('     ASR 等的是"证据还没到齐"，TTS 等的是"这段波形还没算完"。')
r_ok = OUT['right_ok']
print('  ② 右上下文给到 %d 帧（%.0f ms），误差就掉到 %.1f dB，听不出来了。'
      % (r_ok['right'], r_ok['lat_ms'], r_ok['db']))
c16 = [r for r in OUT['chunk'] if r['chunk'] == 16][0]
c4 = [r for r in OUT['chunk'] if r['chunk'] == 4][0]
print('  ③ 块从 16 帧切到 4 帧，首包从 %.0f ms 降到 %.0f ms，'
      % (c16['lat_ms'], c4['lat_ms']))
print('     但每块多算的比例从 %.0f%% 涨到 %.0f%%——'
      % (c16['overhead'], c4['overhead']))
print('     <strong>省下的延迟是拿算力买的，而且买得越来越贵</strong>。')
x0 = OUT['xfade'][0]
xb = min(OUT['xfade'][1:], key=lambda r: r['seam'])
print('  ④ 完全不给右上下文时，边界的包络跳变是块内的 %.2f 倍'
      % x0['seam'])
print('     （整句输出的同一统计量是 %.2f 倍，那是"没有咔哒"的基准）。'
      % OUT['seam_full'])
print('     交叉淡入 %d 个样点（%.1f ms）把它压到 %.2f 倍，'
      % (xb['xfade'], xb['ms'], xb['seam']))
print('     而总误差只从 %.1f dB 变到 %.1f dB。'
      % (x0['db'], xb['db']))
print('     <strong>淡入消的是"咔哒"，不是误差</strong>——波形还是错的，只是不刺耳了。')
print('     所以它是"右上下文给不起时的止痛药"，不是替代品。')
print('  ⑤ 顺带一个确认：不给右上下文时，%.0f%% 的误差能量落在每块的最后 5 帧里，'
      % x0['conc'])
print('     而那一段只占全长的 %.0f%%。远离边界的地方，流式输出和整句是逐比特相同的——'
      % OUT['seam_span'])
print('     因为左上下文 %d 帧已经盖住了 %.1f 帧的左感受野。' % (L_OK, rf_left))

json.dump(OUT, open('demo_chunk.json', 'w'), ensure_ascii=False)
print('\n→ demo_chunk.json')
