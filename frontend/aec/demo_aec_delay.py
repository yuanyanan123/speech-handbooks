#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""延迟估计：参考与回声之间差多少毫秒，估得准不准，估偏了往哪边偏代价才小。

   ① GCC-PHAT 的精度：窗长、近端插话、回声/底噪比、混响时间各自拖垮它多少
   ② 估偏之后 AEC 的 ERLE：高估和低估不对称——高估是悬崖，低估只是少了点尾巴
   ③ 留 8 ms 余量（故意往低估的一侧偏）值多少
"""
import numpy as np, json, time
import enhlib as E
import aeclib as A

OUT = {}
t0 = time.time()
SR = A.SR
PRE_MS = 60.0                  # 真实的纯时延：缓冲 + 声程 + 蓝牙等
B = 256
NP = 8                         # 128 ms
L_MS = 128
SEEDS = (0, 1, 2)
TRIALS = 24


def gcc_phat(x, y, max_ms=250.0, early=None):
    """返回 y 相对 x 的延迟（采样点）。PHAT 加权：只留相位，抹掉谱的强弱。
       early=None：取全局最大峰；early=0.4：取"第一个高过最大峰 40%% 的峰"——
       直达声弱、反射更强时，全局最大峰会落在反射上，也就是高估。"""
    n = 1
    while n < len(x) + len(y):
        n *= 2
    X = np.fft.rfft(x, n)
    Y = np.fft.rfft(y, n)
    R = np.conj(X) * Y
    R /= np.abs(R) + 1e-12
    r = np.fft.irfft(R, n)
    m = int(max_ms * SR / 1000)
    r = r[:m]
    k = int(np.argmax(r))
    if early is None:
        return k
    idx = np.where(r >= early * r[k])[0]
    return int(idx[0])


def make(seed, t60, ner_db=None, echo_noise_db=40.0, dur=8.0, direct=0.35, nl_drive=0.0):
    x = A.farend('speech', dur, seed=seed + 1)
    h = A.rir(t60, seed=seed, pre_ms=PRE_MS, direct=direct)
    xp = A.loudspeaker(x, nl_drive)[0] if nl_drive > 0 else x
    d = np.convolve(xp, h)[:len(x)]
    g = np.random.default_rng(900 + seed)
    y = d.copy()
    if ner_db is not None:                      # 近端持续插话（50% 占空）
        near = np.zeros(len(d))
        t, k = 0, 0
        while t < len(d):
            seg, _ = E.make_speech(dur=1.0, seed=seed * 53 + k)
            ln = min(len(seg), len(d) - t)
            near[t:t + ln] = seg[:ln]
            t += int(2.0 * SR)
            k += 1
        near *= np.sqrt(np.mean(d ** 2) / (np.mean(near ** 2) + 1e-12)) * 10 ** (ner_db / 20)
        y = y + near
    v = g.standard_normal(len(d))
    v *= np.sqrt(np.mean(d ** 2) / 10 ** (echo_noise_db / 10)) / (v.std() + 1e-12)
    return x, y + v, d, h


# ══ ① GCC-PHAT 的精度 ═════════════════════════════════════════
print('① GCC-PHAT：估对的比例（误差 ≤ 2 ms；左：全局最大峰 / 右：最早的显著峰）')
CONDS = [
    ('干净（回声/底噪 40 dB）', dict(t60=0.25)),
    ('近端插话 0 dB', dict(t60=0.25, ner_db=0.0)),
    ('近端插话 +10 dB', dict(t60=0.25, ner_db=10.0)),
    ('回声/底噪 −10 dB', dict(t60=0.25, echo_noise_db=-10.0)),
    ('混响 T60 = 0.6 s', dict(t60=0.6)),
    ('喇叭非线性 THD ≈ 15%', dict(t60=0.25, nl_drive=2.6)),
    ('直达声很弱（反射更强）', dict(t60=0.6, direct=0.02)),
]
WINS = (0.25, 0.5, 1.0, 2.0, 4.0)
OUT['acc'] = []
for nm, kw in CONDS:
    row = {'cond': nm, 'wins': []}
    for w in WINS:
        ok, ok2, errs = 0, 0, []
        for tr in range(TRIALS):
            sd = tr % 6
            x, y, d, h = make(sd, **kw)
            nsamp = int(w * SR)
            st = (tr * 7919) % max(1, len(x) - nsamp)
            est = gcc_phat(x[st:st + nsamp], y[st:st + nsamp])
            est2 = gcc_phat(x[st:st + nsamp], y[st:st + nsamp], early=0.4)
            # 真值：RIR 的直达声位置
            tru = int(PRE_MS * SR / 1000)
            err = (est - tru) * 1000.0 / SR
            errs.append(err)
            ok += abs(err) <= 2.0
            ok2 += abs((est2 - tru) * 1000.0 / SR) <= 2.0
        row['wins'].append({'win': w, 'ok': round(100 * ok / TRIALS, 1),
                            'ok_early': round(100 * ok2 / TRIALS, 1),
                            'med': round(float(np.median(np.abs(errs))), 2)})
    OUT['acc'].append(row)
    print('  %-22s' % nm + '  '.join('%.2fs:%3.0f/%3.0f%%' % (c['win'], c['ok'], c['ok_early']) for c in row['wins']))


# ══ ② 估偏之后：高估 vs 低估 ═════════════════════════════════════
def erle_tail(x, y, d, shift_ms):
    """参考提前/延后 shift_ms 之后喂给 AEC（正 = 把参考多延迟这么多）"""
    s = int(round(shift_ms * SR / 1000))
    xa = np.concatenate([np.zeros(s), x])[:len(x)] if s >= 0 else np.concatenate([x[-s:], np.zeros(-s)])
    e, _ = A.pbfdaf(xa, y, B, NP, mu=0.3, reg=0.1)
    n = len(e)
    k = n // 2
    return float(10 * np.log10((np.mean(d[k:n] ** 2) + 1e-12) / (np.mean(e[k:n] ** 2) + 1e-12)))


print('\n② 估偏之后的 ERLE（估计 − 真值 = 误差；负 = 低估）')
ERRS = (-48, -32, -16, -8, -4, 0, 4, 8, 16, 32)
OUT['err'] = []
for m in (0.0, 8.0):
    row = {'margin_ms': m, 'cells': []}
    for er in ERRS:
        v = []
        for sd in SEEDS:
            x, y, d, h = make(sd, 0.25, dur=8.0)
            # 对齐点 = 真值 + 误差 − 余量；参考被延迟这么多
            v.append(erle_tail(x, y, d, PRE_MS + er - m - 2.0))   # −2 ms：留出滤波器前端 2 ms
        row['cells'].append({'err_ms': er, 'erle': round(float(np.mean(v)), 2)})
    OUT['err'].append(row)
    print('  余量 %2.0f ms：' % m + '  '.join('%+d:%.1f' % (c['err_ms'], c['erle']) for c in row['cells']))

E0 = {c['err_ms']: c['erle'] for c in OUT['err'][0]['cells']}
E8 = {c['err_ms']: c['erle'] for c in OUT['err'][1]['cells']}
ACC = {r['cond']: r for r in OUT['acc']}
w1 = WINS.index(1.0)
OUT['note'] = {
    'clean_ok_1s': ACC['干净（回声/底噪 40 dB）']['wins'][w1]['ok'],
    'weak_direct_ok_1s': ACC['直达声很弱（反射更强）']['wins'][w1]['ok'],
    'weak_direct_early_1s': ACC['直达声很弱（反射更强）']['wins'][w1]['ok_early'],
    'worst_cond_ok_1s': min(r['wins'][w1]['ok'] for r in OUT['acc']),
    'ok_short': OUT['acc'][0]['wins'][0]['ok'],
    'ok_long': OUT['acc'][0]['wins'][-1]['ok'],
    'erle_exact': E0[0], 'over16': E0[16], 'under16': E0[-16], 'over8': E0[8], 'under8': E0[-8],
    'over32': E0[32], 'under32': E0[-32], 'under48': E0[-48],
    'm8_over8': E8[8], 'm8_over16': E8[16], 'm8_under16': E8[-16], 'm8_exact': E8[0],
    'asym_16': round(E0[-16] - E0[16], 2),
}
OUT['const'] = {'pre_ms': PRE_MS, 'l_ms': L_MS, 'trials': TRIALS, 'seeds': list(SEEDS), 'b': B,
                'nparts': NP, 'wins': list(WINS)}
print('\n结论量：', json.dumps(OUT['note'], ensure_ascii=False))
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_aec_delay.json', 'w'), ensure_ascii=False)
print('写出 demo_aec_delay.json  %.1f s' % OUT['runtime_s'])
