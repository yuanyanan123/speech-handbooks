#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据与泛化：把"训练数据配方"那张定性的表，换成一张按 dB 排序的表。

   做法是<strong>消融</strong>：先用一个覆盖六个维度的配方训一个参考模型，
   然后每次只把其中一个维度收窄成"常见的疏漏"，重训，
   在同一个固定的测试条件上量掉多少 dB。
   这样得到的是"漏掉这一维的代价"，可以直接排序。

   最后单独量一件事：电平这一维的代价，到底是数据问题还是特征问题。
"""
import numpy as np, json, time
import enhlib as E
import nnlib as N
from nnlib import NFFT, HOP, NBIN, NB, CTX, WB, DIN, train, fwd, sig

OUT = {}
t0 = time.time()
rng = np.random.default_rng(7)

TRAIN_NOISE = ('white', 'pink', 'car', 'step')
TEST_NOISE = 'babble'                      # 所有配方都没见过它
TRAIN_SNR = (-5.0, 0.0, 5.0, 10.0, 15.0)
TRAIN_SPK = tuple(range(0, 10))
TEST_SPK = 50                              # 所有配方都没见过他
TRAIN_T60 = (0.0, 0.2, 0.4)
TRAIN_LVL = (-24.0, -16.0, -8.0, 0.0)      # 输入电平（dBFS 量级）
NSET = 32

# 基准测试条件：训练覆盖得到的那一档（干净、满量程、无混响、无编解码、见过的说话人）
EASY = dict(noise='pink', snr=5.0, spk=0, t60=0.0, lvl=0.0, codec=False)
# 每一维单独加一个失配，其余维保持在基准档——这样量到的是<strong>这一维自己</strong>的代价
STRESS = {
    '噪声类型': dict(noise=TEST_NOISE),
    '信噪比范围': dict(snr=-5.0),
    '混响': dict(t60=0.35),
    '电平': dict(lvl=-18.0),
    '编解码': dict(codec=True),
    '说话人': dict(spk=TEST_SPK),
}


# ══ 房间冲激响应与"编解码" ════════════════════════════════════
def rir(t60, seed, sr=E.SR):
    if t60 <= 0:
        return np.array([1.0])
    g = np.random.default_rng(seed)
    n = int(min(t60 * 1.5, 0.8) * sr)
    tau = t60 * sr / (3 * np.log(10))
    h = g.standard_normal(n) * np.exp(-np.arange(n) / tau)
    h[0] = 1.0 + abs(h[0])
    return h / h[0]


def codec(x, sr=E.SR):
    """窄带编解码的粗糙代理：限带到 3.4 kHz + 8 bit μ-律量化。
       不是任何真实编解码器，只是把"带限 + 量化噪声"这两件事放进信号里。"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / sr)
    X[f > 3400] *= 0.02
    X[f < 90] *= 0.1
    y = np.fft.irfft(X, len(x))
    a = np.max(np.abs(y)) + E.EPS
    mu = 255.0
    c = np.sign(y / a) * np.log1p(mu * np.abs(y / a)) / np.log1p(mu)
    q = np.round(c * 127) / 127
    d = np.sign(q) * ((1 + mu) ** np.abs(q) - 1) / mu
    return d * a


def conv(x, h):
    return x if len(h) == 1 else np.convolve(x, h, 'full')[:len(x)]


# ══ 一条样本 ══════════════════════════════════════════════════
def make(seed, noise, snr, spk, t60, lvl, use_codec):
    p = E.spk_params(spk)
    x, segs = E.make_speech(dur=3.0, seed=seed, spk=spk,
                            f0_lo=p['f0_lo'], f0_hi=p['f0_hi'])
    m = E.speech_mask(segs, len(x))
    h = rir(t60, seed * 13 + 3)
    xr = conv(x, h)                        # 参考信号 = 带混响的干净语音（不要求网络去混响）
    v = E.make_noise(noise, len(x), seed=seed * 7 + 11)
    vr = conv(v, rir(t60, seed * 13 + 97))
    y, vv = E.mix_at_snr(xr, vr, snr, m)
    g = 10 ** (lvl / 20.0) / (np.max(np.abs(y)) + E.EPS)
    y, xr, vv = y * g, xr * g, vv * g
    if use_codec:
        yc = codec(y)
        vv = vv + (yc - y)                 # 量化与带限的差额记在"噪声"里
        y = yc
    n = len(y)
    return xr[:n], y, m[:n], E.stft(xr[:n], NFFT, HOP), E.stft(vv[:n], NFFT, HOP), \
        E.stft(y, NFFT, HOP)


# ══ 特征：带归一化 / 不带归一化 ════════════════════════════════
def feats(Y, norm=True):
    P = np.maximum((np.abs(Y) ** 2) @ WB.T, 1e-10)
    L = 10 * np.log10(P)
    if norm:
        return N.featurize(Y)
    Z = (L + 60.0) / 20.0                  # 只做固定偏移，不做逐句自适应
    D = np.vstack([np.zeros((1, NB)), np.diff(Z, axis=0)])
    F = np.concatenate([Z, D], 1)
    ctx = [np.vstack([np.repeat(F[:1], k, 0), F[:len(F) - k]]) for k in range(CTX)]
    return np.concatenate(ctx, 1).astype(np.float64)


# ══ 配方 ══════════════════════════════════════════════════════
def recipe(**kw):
    r = dict(noise=TRAIN_NOISE, snr=TRAIN_SNR, spk=TRAIN_SPK,
             t60=TRAIN_T60, lvl=TRAIN_LVL, codec=(False, True))
    r.update(kw)
    return r


def build(rc, seed0=200, nset=NSET, norm=True):
    Xs, Ts = [], []
    for i in range(nset):
        xr, y, m, S, V, Y = make(
            seed0 + i, rc['noise'][i % len(rc['noise'])],
            rc['snr'][i % len(rc['snr'])], rc['spk'][i % len(rc['spk'])],
            rc['t60'][i % len(rc['t60'])], rc['lvl'][i % len(rc['lvl'])],
            rc['codec'][i % len(rc['codec'])])
        Xs.append(feats(Y, norm))
        Ts.append(np.sqrt(np.abs(S) ** 2 / (np.abs(S) ** 2 + np.abs(V) ** 2 + E.EPS)))
    return np.concatenate(Xs), np.concatenate(Ts)


def fit(rc, tag, norm=True, seed=0, nset=NSET):
    X, T = build(rc, norm=norm, nset=nset)

    def lf(o, i):
        p = sig(o); d = p - T[i]
        return float(np.mean(d ** 2)), 2 * d * p * (1 - p) / o.shape[1]
    return train(X, NBIN, lf, tag=tag, seed=seed)[0]


def test(P, norm=True, seeds=(901, 902, 903, 904), **over):
    """返回处理后的指标，以及<strong>相对不处理的增益</strong>——
       不同测试条件下不处理的基线不同，只看绝对值会读错。"""
    cond = dict(EASY); cond.update(over)
    rs = []
    for sd in seeds:
        xr, y, m, S, V, Y = make(sd, cond['noise'], cond['snr'], cond['spk'],
                                 cond['t60'], cond['lvl'], cond['codec'])
        _, _, _, _, o = fwd(P, feats(Y, norm))
        z = E.istft(sig(o) * Y, NFFT, HOP, n=len(y))[:len(y)]
        rs.append((E.seg_snr(xr, z, m), E.stoi_like(xr, z, mask=m),
                   E.lsd(xr, z, mask=m), E.seg_snr(xr, y, m),
                   E.stoi_like(xr, y, mask=m)))
    a = np.mean(rs, 0)
    return dict(segsnr=round(float(a[0]), 2), stoi=round(float(a[1]), 3),
                lsd=round(float(a[2]), 2), noisy=round(float(a[3]), 2),
                noisy_stoi=round(float(a[4]), 3),
                gain=round(float(a[0] - a[3]), 2))


# ══ ① 全配方参考模型 ══════════════════════════════════════════
print('① 全配方参考模型（噪声 %d 种 / 信噪比 %g–%g dB / 说话人 %d 个 / '
      'T60 %s / 电平 %g–%g dB / 编解码 有+无）'
      % (len(TRAIN_NOISE), TRAIN_SNR[0], TRAIN_SNR[-1], len(TRAIN_SPK),
         '/'.join('%g' % t for t in TRAIN_T60), TRAIN_LVL[0], TRAIN_LVL[-1]))
Pfull = fit(recipe(), '全配方')
easy = test(Pfull)
print('   基准档（%s 噪声 / %g dB / 见过的说话人 / 无混响 / 满量程 / 无编解码）：'
      % (EASY['noise'], EASY['snr']))
print('   不处理 %.2f dB → 处理后 %.2f dB，增益 %+.2f dB   STOI* %.3f'
      % (easy['noisy'], easy['segsnr'], easy['gain'], easy['stoi']))
OUT['easy'] = easy
OUT['setup'] = {'nset': NSET, 'noise': list(TRAIN_NOISE), 'test_noise': TEST_NOISE,
                'snr': list(TRAIN_SNR), 'nspk': len(TRAIN_SPK),
                't60': list(TRAIN_T60), 'lvl': list(TRAIN_LVL),
                'easy': dict(EASY)}

# ══ ② 一维一维地量：盖住 vs 没盖住，在同一个失配条件上比 ═══════
print('\n② 每一维单独加一个失配；同一个失配条件上，比"训练盖住了"和"没盖住"')
ABL = [
    ('噪声类型', '只用一种平稳噪声', dict(noise=('white',))),
    ('信噪比范围', '只训 0–10 dB', dict(snr=(0.0, 5.0, 10.0))),
    ('混响', '全用无混响的干净录音', dict(t60=(0.0,))),
    ('电平', '训练数据全部归一化到满量程', dict(lvl=(0.0,))),
    ('编解码', '训练时不过编解码', dict(codec=(False,))),
    ('说话人', '只用一个说话人', dict(spk=(0,))),
]
OUT['ablate'] = []
for name, how, kw in ABL:
    st = STRESS[name]
    Pn = fit(recipe(**kw), '收窄：' + name)
    rf, rn = test(Pfull, **st), test(Pn, **st)
    OUT['ablate'].append({
        'axis': name, 'how': how,
        'stress': '、'.join('%s=%s' % (k, v) for k, v in st.items()),
        'noisy': rf['noisy'], 'full': rf['gain'], 'narrow': rn['gain'],
        'drop': round(rf['gain'] - rn['gain'], 2),
        'stress_cost': round(easy['gain'] - rf['gain'], 2),
        'stoi_drop': round(rf['stoi'] - rn['stoi'], 3)})
OUT['ablate'].sort(key=lambda r: -r['drop'])
print('  %-10s %-20s %9s %9s %8s %9s'
      % ('维度', '收窄成', '盖住了', '没盖住', '漏掉的代价', '失配本身'))
for r in OUT['ablate']:
    print('  %-10s %-20s %+8.2f %+9.2f %8.2f %+9.2f'
          % (r['axis'], r['how'], r['full'], r['narrow'], r['drop'],
             -r['stress_cost']))
top = OUT['ablate'][0]
OUT['spread'] = round(top['drop'] - OUT['ablate'][-1]['drop'], 2)
print('  最贵的一维是<strong>%s</strong>（%.2f dB），最便宜的 %.2f dB。'
      % (top['axis'], top['drop'], OUT['ablate'][-1]['drop']))

# ══ ③ 电平这一维：数据问题还是特征问题 ════════════════════════
print('\n③ 电平：把特征的逐句自适应归一化关掉，再量同一件事')
OUT['level'] = []
for norm, nm in ((True, '有逐句归一化'), (False, '无逐句归一化')):
    Pa = fit(recipe(), '%s · 全电平' % nm, norm=norm)
    Pb = fit(recipe(lvl=(0.0,)), '%s · 只训满量程' % nm, norm=norm)
    ra = test(Pa, norm=norm, **STRESS['电平'])
    rb = test(Pb, norm=norm, **STRESS['电平'])
    OUT['level'].append({'front': nm, 'full': ra['gain'], 'narrow': rb['gain'],
                         'drop': round(ra['gain'] - rb['gain'], 2)})
    print('  %-14s  全电平训 %+.2f dB   只训满量程 %+.2f dB   漏掉的代价 %.2f dB'
          % (nm, ra['gain'], rb['gain'], OUT['level'][-1]['drop']))
OUT['level_ratio'] = round(OUT['level'][1]['drop'] - OUT['level'][0]['drop'], 2)
print('  关掉归一化之后，电平这一维的代价多了 %.2f dB——'
      '<strong>它是不是数据问题，取决于前端</strong>。' % OUT['level_ratio'])

# ══ ④ 总时长 vs 多样性 ════════════════════════════════════════
print('\n④ 同样的总时长，一种噪声 vs 四种噪声（测在没见过的 babble 上）')
OUT['amount'] = []
for nset in (8, 32):
    P1 = fit(recipe(noise=('white',)), '一种 × %d 段' % nset, nset=nset)
    P4 = fit(recipe(), '四种 × %d 段' % nset, nset=nset)
    r1 = test(P1, **STRESS['噪声类型'])
    r4 = test(P4, **STRESS['噪声类型'])
    OUT['amount'].append({'nset': nset, 'one': r1['gain'], 'four': r4['gain'],
                          'gain': round(r4['gain'] - r1['gain'], 2)})
    print('  %2d 段：一种噪声 %+.2f dB   四种噪声 %+.2f dB   差 %.2f dB'
          % (nset, r1['gain'], r4['gain'], r4['gain'] - r1['gain']))
a0, a2 = OUT['amount'][0], OUT['amount'][-1]
OUT['amount_note'] = {'one_gain_4x': round(a2['one'] - a0['one'], 2),
                      'div_gain': a0['gain'], 'ratio': a2['nset'] // a0['nset']}
print('  单一噪声的数据量翻 %d 倍带来 %.2f dB；'
      '而在最小数据量上把噪声换成四种就带来 %.2f dB。'
      % (OUT['amount_note']['ratio'], OUT['amount_note']['one_gain_4x'],
         OUT['amount_note']['div_gain']))

OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_gen.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_gen.json（%.0f s）' % OUT['runtime_s'])
