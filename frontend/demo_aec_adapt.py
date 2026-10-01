#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自适应滤波的三角，以及真正决定它收敛的是什么。

   ① 步长 μ：收敛快一倍，稳态失调就差一截——两者的积是不是守恒
   ② 远端信号的谱：白噪 / 粉噪 / 语音，可用的步长范围差多少
   ③ 逐频点归一化（输入白化）值多少
   ④ 滤波器长度：路径的尾巴把 ERLE 的上界钉在哪
   ⑤ 分区块：块长和滤波器长度解耦之后，延迟能降到多少
"""
import numpy as np, json, time
import enhlib as E
import aeclib as A

OUT = {}
t0 = time.time()
SR = A.SR
T60 = 0.25
L_MS = 128
L = int(L_MS * SR / 1000)          # 2048 抽头
B = 256                            # 分区块长 16 ms
NP = L // B                        # 8 个分区
NEAR_SNR = 40.0                    # 近端底噪（相对回声），稳态失调的下界由它定
SEEDS = (0, 1, 2)


def mix(x, h, seed, near_snr=NEAR_SNR):
    d = np.convolve(x, h)[:len(x)]
    g = np.random.default_rng(100 + seed)
    v = g.standard_normal(len(d))
    v *= np.sqrt(np.mean(d ** 2) / 10 ** (near_snr / 10)) / (np.std(v) + A.EPS)
    return d + v, d


def mis_curve(snaps, h, step=1024):
    return np.array([A.misalign(w, h) for w in snaps])


# ══ ① 步长的三角（时域 NLMS，白噪远端）═════════════════════════
print('① 步长 μ：收敛快一倍，稳态失调就差一截')
MUS = (0.05, 0.1, 0.25, 0.5, 1.0)
DUR1 = 20.0                        # ① 的观测窗：小步长要这么久才到稳态
OUT['mu'] = []
for mu in MUS:
    tc, ms, er = [], [], []
    for sd in SEEDS:
        h = A.rir(T60, seed=sd)
        x = A.farend('white', DUR1, seed=sd + 1)
        y, d = mix(x, h, sd)
        e, w, snaps = A.nlms(x, y, L, mu=mu)
        mc = mis_curve(snaps, h)
        idx = np.where(mc <= -20.0)[0]
        tc.append(np.nan if len(idx) == 0 else idx[0] * 1024 / SR)
        ms.append(float(np.mean(mc[-20:])))   # 末尾 1.3 s 的平均
        c = A.erle_curve(d, e)
        er.append(float(np.mean(c[-int(len(c) * 0.25):])))
    r = {'mu': mu, 't20': round(float(np.nanmean(tc)), 3),
         'misalign': round(float(np.mean(ms)), 2),
         'erle': round(float(np.mean(er)), 2)}
    r['product'] = round(r['t20'] * 10 ** (r['misalign'] / 10) * 1000, 3)
    OUT['mu'].append(r)
    print('  μ=%4.2f  失调到 −20 dB 用 %5.2f s   稳态失调 %6.2f dB   稳态 ERLE %5.2f dB'
          % (mu, r['t20'], r['misalign'], r['erle']))
fast = OUT['mu'][-1]
slow = [r for r in OUT['mu'] if r['mu'] == 0.1][0]
OUT['mu_tradeoff'] = {
    'fast_mu': fast['mu'], 'slow_mu': slow['mu'],
    't_ratio': round(slow['t20'] / max(fast['t20'], 1e-9), 1),
    'mis_gain': round(fast['misalign'] - slow['misalign'], 2),
    'prod_spread': round(max(r['product'] for r in OUT['mu']) /
                         max(min(r['product'] for r in OUT['mu']), 1e-9), 1)}
print('  μ 从 %.2f 降到 %.2f：收敛慢 %.1f 倍，稳态失调低 %.2f dB；'
      '两者的积在 %.1f 倍以内。'
      % (fast['mu'], slow['mu'], OUT['mu_tradeoff']['t_ratio'],
         -OUT['mu_tradeoff']['mis_gain'], OUT['mu_tradeoff']['prod_spread']))

# ══ ② 远端的谱决定了步长能开多大 ═══════════════════════════════
print('\n② 换一种远端信号：可用的步长范围')
MUG = (0.8, 0.5, 0.25, 0.1, 0.05)
OUT['spec'] = []
for kind, nm in (('white', '白噪'), ('pink', '粉噪'), ('speech', '语音')):
    sp = float(np.mean([A.eig_spread(A.farend(kind, 4.0, seed=sd + 1))
                        for sd in SEEDS]))
    best = None
    rows = []
    for mu in MUG:
        ms = []
        for sd in SEEDS:
            h = A.rir(T60, seed=sd)
            x = A.farend(kind, 8.0, seed=sd + 1)
            y, d = mix(x, h, sd)
            e, w = A.pbfdaf(x, y, B, NP, mu=mu, reg=0.1)
            ms.append(A.misalign(w, h))
        m = float(np.mean(ms))
        rows.append({'mu': mu, 'misalign': round(m, 2),
                     'stable': bool(m < -3.0)})
        if m < -3.0 and best is None:
            best = {'mu': mu, 'misalign': round(m, 2)}
    r = {'kind': nm, 'spread': round(sp, 1), 'rows': rows,
         'mu_max': best['mu'] if best else None,
         'best_mis': best['misalign'] if best else None}
    OUT['spec'].append(r)
    print('  %-4s  特征值扩散 %8.1f   最大可用步长 %s   该步长下失调 %s dB'
          % (nm, r['spread'],
             ('%.2f' % r['mu_max']) if r['mu_max'] else '—',
             ('%.2f' % r['best_mis']) if r['best_mis'] is not None else '—'))
sw, ss = OUT['spec'][0], OUT['spec'][-1]
OUT['spec_note'] = {
    'spread_ratio': round(ss['spread'] / max(sw['spread'], 1e-9), 0),
    'mu_ratio': round(sw['mu_max'] / max(ss['mu_max'], 1e-9), 1)
    if (sw['mu_max'] and ss['mu_max']) else None,
    'mis_gap': round((ss['best_mis'] or 0) - (sw['best_mis'] or 0), 2)}
print('  语音远端的特征值扩散是白噪的 %.0f 倍；同一套设置下步长要小 %.1f 倍，'
      '失调还是差 %.2f dB。' % (OUT['spec_note']['spread_ratio'],
                               OUT['spec_note']['mu_ratio'] or 0,
                               OUT['spec_note']['mis_gap']))

# ══ ③ 逐频点归一化（输入白化）值多少 ═══════════════════════════
print('\n③ 逐频点归一化开 / 关')
OUT['white'] = []
for kind, nm in (('white', '白噪'), ('pink', '粉噪'), ('speech', '语音')):
    row = {'kind': nm}
    for norm in (True, False):
        ms, tc = [], []
        for sd in SEEDS:
            h = A.rir(T60, seed=sd)
            x = A.farend(kind, 8.0, seed=sd + 1)
            y, d = mix(x, h, sd)
            mu = 0.25 if kind == 'speech' else 0.5
            e, w = A.pbfdaf(x, y, B, NP, mu=mu, reg=0.1, bins_norm=norm)
            ms.append(A.misalign(w, h))
            c = A.erle_curve(d[:len(e)], e)
            t = A.t_converge(c, 20.0)
            tc.append(np.nan if t is None else t)
        row['on' if norm else 'off'] = round(float(np.mean(ms)), 2)
        row[('on' if norm else 'off') + '_t20'] = (
            None if np.all(np.isnan(tc)) else round(float(np.nanmean(tc)), 2))
    row['gain'] = round(row['off'] - row['on'], 2)
    OUT['white'].append(row)
    print('  %-4s  开 %7.2f dB   关 %7.2f dB   差 %6.2f dB'
          % (nm, row['on'], row['off'], row['gain']))
OUT['white_note'] = {k['kind']: k['gain'] for k in OUT['white']}

# ══ ④ 滤波器长度 vs 路径的尾巴 ═════════════════════════════════
print('\n④ 滤波器长度：尾巴里剩下的能量就是 ERLE 的上界')
OUT['length'] = []
for lms in (32, 64, 128, 256, 512):
    ll = int(lms * SR / 1000)
    th, er, ms = [], [], []
    for sd in SEEDS:
        h = A.rir(T60, seed=sd)
        th.append(A.tail_energy(h, lms))
        x = A.farend('white', 8.0, seed=sd + 1)
        y, d = mix(x, h, sd)
        e, w = A.pbfdaf(x, y, B, max(ll // B, 1), mu=0.5, reg=0.1)
        c = A.erle_curve(d[:len(e)], e)
        er.append(float(np.mean(c[-int(len(c) * 0.25):])))
        ms.append(A.misalign(w, h))
    tt = float(np.mean(th))
    cap_tail = -10 * np.log10(tt + 1e-9)
    r = {'l_ms': lms, 'taps': ll, 'tail': round(tt * 100, 2),
         'ceiling': round(min(cap_tail, 200.0), 2),
         'cap_tail': round(min(cap_tail, 200.0), 2),
         'cap_noise': NEAR_SNR,
         'cap': round(min(cap_tail, NEAR_SNR), 2),
         'bind': '尾巴' if cap_tail < NEAR_SNR else '近端底噪',
         'erle': round(float(np.mean(er)), 2),
         'misalign': round(float(np.mean(ms)), 2)}
    OUT['length'].append(r)
    print('  %3d ms（%5d 抽头）  尾巴 %5.2f%% → 截断上界 %6.2f dB   '
          '合上近端底噪后 %5.2f dB（%s 说了算）  实测 %5.2f dB'
          % (lms, ll, r['tail'], r['cap_tail'], r['cap'], r['bind'], r['erle']))
g = OUT['length']
OUT['length_note'] = {
    'd64_128': round(g[2]['erle'] - g[1]['erle'], 2),
    'd256_512': round(g[4]['erle'] - g[3]['erle'], 2),
    't60': T60, 'rt_ms': round(T60 * 1000, 0)}
print('  64→128 ms 涨 %.2f dB，256→512 ms 只涨 %.2f dB。'
      % (OUT['length_note']['d64_128'], OUT['length_note']['d256_512']))

# ══ ⑤ 分区块：延迟和滤波器长度解耦 ═════════════════════════════
print('\n⑤ 同样 128 ms 的滤波器，分区块长不同')
OUT['part'] = []
for b in (64, 128, 256, 512, 1024, 2048):
    npart = max(L // b, 1)
    ms, er = [], []
    for sd in SEEDS:
        h = A.rir(T60, seed=sd)
        x = A.farend('pink', 8.0, seed=sd + 1)
        y, d = mix(x, h, sd)
        e, w = A.pbfdaf(x, y, b, npart, mu=0.5, reg=0.1)
        ms.append(A.misalign(w, h))
        c = A.erle_curve(d[:len(e)], e)
        er.append(float(np.mean(c[-int(len(c) * 0.25):])))
    N = 2 * b
    fft_mac = int(N / 2 * np.log2(N)) * 2              # 一次 N 点实 FFT
    nfft_blk = 2 + 1 + 2 * npart                      # 正/反变换 + 误差 + 梯度约束
    cmac_blk = npart * (N // 2 + 1) * 4               # 滤波与更新里的复数乘加
    mac_s = (nfft_blk * fft_mac + cmac_blk) * SR / b
    r = {'b': b, 'b_ms': round(b / SR * 1000, 1), 'nparts': npart,
         'delay_ms': round(b / SR * 1000, 1),
         'misalign': round(float(np.mean(ms)), 2),
         'erle': round(float(np.mean(er)), 2),
         'ffts_per_s': round(SR / b * nfft_blk, 0),
         'mmac_s': round(mac_s / 1e6, 2)}
    OUT['part'].append(r)
    print('  块 %4d 点（%5.1f ms）× %2d 分区   延迟 %5.1f ms   失调 %6.2f dB   '
          'ERLE %5.2f dB   %6.0f 次 FFT/s   %6.2f MMAC/s'
          % (b, r['b_ms'], npart, r['delay_ms'], r['misalign'], r['erle'],
             r['ffts_per_s'], r['mmac_s']))
p0, p1 = OUT['part'][0], OUT['part'][-1]
OUT['part_note'] = {
    'delay_ratio': round(p1['delay_ms'] / max(p0['delay_ms'], 1e-9), 0),
    'mis_gain': round(p1['misalign'] - p0['misalign'], 2),
    'mac_ratio': round(p0['mmac_s'] / max(p1['mmac_s'], 1e-9), 1)}
print('  块从 %d 点缩到 %d 点：延迟降 %.0f 倍，失调反而好 %.2f dB，'
      '代价是算力涨 %.1f 倍。'
      % (p1['b'], p0['b'], OUT['part_note']['delay_ratio'],
         OUT['part_note']['mis_gain'], OUT['part_note']['mac_ratio']))

OUT['const'] = {'t60': T60, 'l_ms': L_MS, 'taps': L, 'b': B, 'nparts': NP,
                'near_snr': NEAR_SNR, 'sr': SR, 'seeds': list(SEEDS)}
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_aec_adapt.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_aec_adapt.json（%.0f s）' % OUT['runtime_s'])
