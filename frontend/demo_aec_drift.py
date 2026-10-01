#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追不上的那一部分：时钟漂移、整块延迟、路径突变。

   ① 播放端和采集端差几个 ppm，ERLE 的上界就掉到哪
   ② 加长滤波器能不能补偿漂移（我以为能）
   ③ 整块延迟估偏了多少还救得回来
   ④ 路径突变之后要多久重收敛，以及双讲冻结会不会把它卡死
"""
import numpy as np, json, time
import enhlib as E
import aeclib as A

OUT = {}
t0 = time.time()
SR = A.SR
T60 = 0.25
B = 256
MU = 0.5
REG = 0.1
DUR = 16.0
NEAR_SNR = 40.0
SEEDS = (0, 1, 2)
L_MS = 128


def build(seed, ppm=0.0, l_ms=L_MS, pre_ms=4.0, dur=DUR, h=None):
    """x_ref 是 AEC 看到的参考；x_play 是真正推到喇叭上的那一路。
       时钟不同步的后果就是这两路不是同一个时间轴。"""
    x = A.farend('pink', dur, seed=seed + 1)
    if h is None:
        h = A.rir(T60, seed=seed, pre_ms=pre_ms)
    x_play = A.drift(x, ppm)
    d = np.convolve(x_play, h)[:len(x)]
    g = np.random.default_rng(100 + seed)
    v = g.standard_normal(len(d))
    v *= np.sqrt(np.mean(d ** 2) / 10 ** (NEAR_SNR / 10)) / (v.std() + A.EPS)
    return x, d + v, d, h


def erle_of(x, y, d, l_ms, mu=MU):
    L = int(l_ms * SR / 1000)
    e, w = A.pbfdaf(x, y, B, max(L // B, 1), mu=mu, reg=REG)
    c = A.erle_curve(d[:len(e)], e)
    return float(np.mean(c[-int(len(c) * 0.3):])), w, c


# ══ ① 漂移几个 ppm ════════════════════════════════════════════
print('① 播放端和采集端的时钟差几个 ppm')
OUT['ppm'] = []
for ppm in (0, 1, 2, 5, 10, 20, 50, 100):
    er = []
    for sd in SEEDS:
        x, y, d, h = build(sd, ppm=ppm)
        e, _, _ = erle_of(x, y, d, L_MS)
        er.append(e)
    r = {'ppm': ppm, 'erle': round(float(np.mean(er)), 2),
         'slip_ms': round(ppm * 1e-6 * DUR * 1000, 3),
         'slip_samp': round(ppm * 1e-6 * DUR * SR, 2)}
    OUT['ppm'].append(r)
    print('  %4d ppm  %5.1f s 里累计滑 %6.2f 个采样点   稳态 ERLE %6.2f dB'
          % (ppm, DUR, r['slip_samp'], r['erle']))
p0 = OUT['ppm'][0]
half = next((r for r in OUT['ppm'] if r['erle'] < p0['erle'] - 6.0), None)
OUT['ppm_note'] = {'clean': p0['erle'],
                   'ppm_6db': half['ppm'] if half else None,
                   'erle_100': OUT['ppm'][-1]['erle'],
                   'drop_100': round(p0['erle'] - OUT['ppm'][-1]['erle'], 2)}
print('  %s；100 ppm 时比同步情况差 %.2f dB。'
      % (('掉 6 dB 的拐点在 %d ppm' % half['ppm']) if half else '扫到 100 ppm 还没掉 6 dB',
         OUT['ppm_note']['drop_100']))

# ══ ② 加长滤波器能不能补偿漂移 ═════════════════════════════════
print('\n② 同样的漂移，把滤波器加长')
OUT['len_drift'] = []
for lms in (32, 64, 128, 256):
    row = {'l_ms': lms, 'cells': []}
    for ppm in (0, 10, 50):
        er = []
        for sd in SEEDS:
            x, y, d, h = build(sd, ppm=ppm)
            e, _, _ = erle_of(x, y, d, lms)
            er.append(e)
        row['cells'].append({'ppm': ppm, 'erle': round(float(np.mean(er)), 2)})
    row['loss50'] = round(row['cells'][0]['erle'] - row['cells'][2]['erle'], 2)
    OUT['len_drift'].append(row)
    print('  %3d ms  ' % lms + '   '.join(
        '%3d ppm→%6.2f dB' % (c['ppm'], c['erle']) for c in row['cells'])
        + '    50 ppm 的代价 %5.2f dB' % row['loss50'])
OUT['len_drift_note'] = {
    'short': OUT['len_drift'][0]['loss50'], 'long': OUT['len_drift'][-1]['loss50'],
    'short_ms': OUT['len_drift'][0]['l_ms'], 'long_ms': OUT['len_drift'][-1]['l_ms']}
print('  滤波器 %d ms 时漂移的代价 %.2f dB，%d ms 时 %.2f dB——'
      % (OUT['len_drift_note']['short_ms'], OUT['len_drift_note']['short'],
         OUT['len_drift_note']['long_ms'], OUT['len_drift_note']['long']))

# ══ ③ 整块延迟估偏了 ══════════════════════════════════════════
print('\n③ 参考和采集之间的整块延迟，估偏多少还救得回来')
OUT['delay'] = []
L = int(L_MS * SR / 1000)
for off_ms in (0, 8, 32, 64, 96, 128, 160):
    er = []
    for sd in SEEDS:
        # 真实延迟 = off_ms（纯时延藏在路径里），AEC 以为是 0
        x, y, d, h = build(sd, pre_ms=off_ms + 4.0)
        e, _, _ = erle_of(x, y, d, L_MS)
        er.append(e)
    r = {'off_ms': off_ms, 'erle': round(float(np.mean(er)), 2),
         'head_left_ms': round(L_MS - off_ms, 1)}
    OUT['delay'].append(r)
    print('  延迟 %3d ms（滤波器 %d ms，留给路径的只剩 %4.0f ms）  ERLE %6.2f dB'
          % (off_ms, L_MS, r['head_left_ms'], r['erle']))
d0 = OUT['delay'][0]
cliff = next((r for r in OUT['delay'] if r['erle'] < d0['erle'] - 10.0), None)
OUT['delay_note'] = {'clean': d0['erle'],
                     'cliff_ms': cliff['off_ms'] if cliff else None,
                     'last': OUT['delay'][-1]['erle'], 'l_ms': L_MS}
print('  %s——<strong>延迟估计错了，滤波器再长也白搭</strong>。'
      % (('超过 %d ms 就掉 10 dB 以上' % cliff['off_ms']) if cliff else '没出现悬崖'))

# ══ ④ 路径突变 ════════════════════════════════════════════════
print('\n④ 路径中途变了：重收敛要多久')
OUT['change'] = []
for mixf, nm in ((0.1, '轻微（挪一下手）'), (0.3, '中等（转个身）'),
                 (1.0, '完全换一条（挡住喇叭）')):
    rec, dip = [], []
    for sd in SEEDS:
        h1 = A.rir(T60, seed=sd)
        h2 = A.rir(T60, seed=sd + 50)
        n = min(len(h1), len(h2))
        hm = (1 - mixf) * h1[:n] + mixf * h2[:n]
        hm /= np.linalg.norm(hm)
        x = A.farend('pink', DUR, seed=sd + 1)
        half_n = len(x) // 2
        d = np.r_[np.convolve(x[:half_n], h1)[:half_n],
                  np.convolve(x[half_n:], hm)[:len(x) - half_n]]
        g = np.random.default_rng(100 + sd)
        v = g.standard_normal(len(d))
        v *= np.sqrt(np.mean(d ** 2) / 10 ** (NEAR_SNR / 10)) / (v.std() + A.EPS)
        e, w = A.pbfdaf(x, d + v, B, L // B, mu=MU, reg=REG)
        c = A.erle_curve(d[:len(e)], e)
        bh = half_n // int(0.064 * SR)
        pre = float(np.mean(c[max(bh - 20, 0):bh]))
        post = c[bh:]
        dip.append(pre - float(np.min(post[:8])))
        back = np.where(post >= pre - 3.0)[0]
        rec.append(float(back[0] * 0.064) if len(back) else np.nan)
    r = {'mix': mixf, 'name': nm,
         'dip': round(float(np.nanmean(dip)), 2),
         'recover': round(float(np.nanmean(rec)), 2)}
    OUT['change'].append(r)
    print('  %-18s ERLE 瞬间掉 %5.2f dB，%5.2f s 之后回到原来的 3 dB 以内'
          % (nm, r['dip'], r['recover']))
OUT['change_note'] = {'worst_dip': max(r['dip'] for r in OUT['change']),
                      'worst_rec': max(r['recover'] for r in OUT['change'])}

OUT['const'] = {'t60': T60, 'b': B, 'mu': MU, 'l_ms': L_MS, 'dur': DUR,
                'near_snr': NEAR_SNR, 'seeds': list(SEEDS)}
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_aec_drift.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_aec_drift.json（%.0f s）' % OUT['runtime_s'])
