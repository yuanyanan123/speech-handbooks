#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全双工与打断（barge-in）：设备正在播，用户开口，多快能发现、多轻的声音能发现。

   设备一直在播一段远端语音（TTS 之类）；第 6 s 起用户插话 2 s。
   检测量：s(t) = 10·log10(残差功率 / 回声估计功率)。只有回声时它等于 −ERLE，
   用户开口后它抬到 ≈ 近端相对回声的电平。阈值 θ 用"只有回声"的校准段定
   （校准段里一次都不误触发），然后在插话段里看：多快触发、多轻的声音触发不了。

   ① 四种前端：不做 AEC / 能量比 DTD 的 AEC / 频域卡尔曼 AEC / 全知 DTD 的 AEC
   ② 最小可检测的近端电平，与前端的 ERLE 的关系——每多 6 dB ERLE，能听见的声音轻 6 dB 吗
   ③ 用户听上去的代价：半双工（播的时候关麦）与全双工的取舍
"""
import numpy as np, json, time
import enhlib as E
import aeclib as A
import aecadv as V

OUT = {}
t0 = time.time()
SR = A.SR
B = V.B
DUR = 12.0
T_ON, T_LEN = 6.0, 2.0
HOLD_BLK = 6                      # 连续 6 块（96 ms）超过阈值才算
SM = 4                            # 平滑 4 块
CAL = (20, 21, 22, 23, 24, 25)                # 校准用的只有回声的场景
TEST = (0, 1, 2, 3, 4, 5)
NERS = (-15.0, -10.0, -5.0, 0.0, 5.0, 10.0)
WARM = 3.0
ONSET_HOLD = 12                   # 起音之后屏蔽 12 块（约 190 ms）


def scene(seed, ner_db=None):
    x = A.farend('speech', DUR, seed=seed + 1)
    h = A.rir(0.25, seed=seed)
    d = np.convolve(x, h)[:len(x)]
    g = np.random.default_rng(700 + seed)
    near = np.zeros(len(d))
    dt = np.zeros(len(d), bool)
    if ner_db is not None:
        a = int(T_ON * SR)
        seg, _ = E.make_speech(dur=T_LEN, seed=seed * 131 + 7)
        ln = min(len(seg), len(d) - a)
        near[a:a + ln] = seg[:ln]
        dt[a:a + ln] = True
        near *= np.sqrt(np.mean(d[dt] ** 2) / (np.mean(near[dt] ** 2) + 1e-12)) * 10 ** (ner_db / 20)
    v = g.standard_normal(len(d))
    v *= np.sqrt(np.mean(d ** 2) / 1e4) / (v.std() + 1e-12)
    return dict(x=x, y=d + near + v, d=d, near=near, dt=dt, h=h)


def smooth(p, k):
    c = np.cumsum(np.insert(p, 0, 0.0))
    out = np.zeros_like(p)
    for i in range(len(p)):
        a = max(0, i - k + 1)
        out[i] = (c[i + 1] - c[a]) / (i + 1 - a)
    return out


def stat(s, kind):
    """逐块的检测量 s(t)，单位 dB"""
    x, y = s['x'], s['y']
    nb = len(y) // B
    if kind == 'raw':
        # 不做 AEC：先用开头（只有回声）估一个回声增益，之后拿麦克风功率去比"参考功率 × 增益"
        px = np.array([np.mean(x[i * B:(i + 1) * B] ** 2) for i in range(nb)])
        py = np.array([np.mean(y[i * B:(i + 1) * B] ** 2) for i in range(nb)])
        k = int(2.0 * SR / B)
        g2 = py[:k].sum() / (px[:k].sum() + 1e-12)
        pe, ph = smooth(py, SM), smooth(g2 * px, SM)
    else:
        if kind == 'energy':
            r = V.run_pb(x, y, s['h'], mode='energy', kappa=2.0)
        elif kind in ('fdkf', 'fdkf_mask'):
            r = V.run_fdkf(x, y, s['h'], a=0.9995, lam=0.97)
        elif kind == 'oracle':
            r = V.run_pb(x, y, s['h'], mode='oracle', oracle=s['dt'])
        e = r['e']
        yh = y[:len(e)] - e
        pe = smooth(np.array([np.mean(e[i * B:(i + 1) * B] ** 2) for i in range(nb)]), SM)
        ph = smooth(np.array([np.mean(yh[i * B:(i + 1) * B] ** 2) for i in range(nb)]), SM)
        s['_e'] = e
    ph = np.maximum(ph, 1e-3 * ph.mean())          # 远端静音时分母别掉到零
    out = 10 * np.log10((pe + 1e-12) / (ph + 1e-12))
    if kind.endswith('_mask'):
        # 远端起音屏蔽：远端功率比前 8 块的平均突然高出 4 倍，之后 ONSET_HOLD 块里这个统计量不参与判决
        px = np.array([np.mean(x[i * B:(i + 1) * B] ** 2) for i in range(nb)])
        for i in range(8, nb):
            if px[i] > 4 * (px[i - 8:i].mean() + 1e-12):
                out[i:i + ONSET_HOLD] = -99.0
    return out


def triggers(sv, theta, hold=HOLD_BLK):
    """第一个"连续 hold 块都超过 theta"的块下标；没有返回 None"""
    over = sv > theta
    run = 0
    for i, o in enumerate(over):
        run = run + 1 if o else 0
        if run >= hold:
            return i - hold + 1
    return None


KINDS = [('raw', '不做 AEC'), ('energy', 'AEC + 能量比 DTD'), ('fdkf', 'AEC（频域卡尔曼）'),
         ('oracle', 'AEC + 全知 DTD'), ('fdkf_mask', '卡尔曼 + 远端起音屏蔽')]
w0 = int(WARM * SR / B)
OUT['kinds'] = []
print('校准（只有回声）→ 阈值；再看各近端电平下的检测')
for kind, nm in KINDS:
    cal_max, cal_med, erle_cal = [], [], []
    for sd in CAL:
        sc = scene(sd, None)
        sv = stat(sc, kind)
        cal_max.append(sv[w0:].max())
        cal_med.append(np.median(sv[w0:]))
        if kind != 'raw':
            e = sc['_e']
            m = slice(int(WARM * SR), len(e))
            erle_cal.append(10 * np.log10(np.mean(sc['d'][m] ** 2) / np.mean(e[m] ** 2)))
    theta = float(np.max(cal_max)) + 1.0            # 校准段里最高的一次 + 1 dB 余量
    row = {'kind': kind, 'name': nm, 'theta': round(theta, 2), 'floor': round(float(np.mean(cal_med)), 2),
           'erle': round(float(np.mean(erle_cal)), 2) if erle_cal else 0.0, 'by_ner': []}
    for ner in NERS:
        det, lat = 0, []
        for sd in TEST:
            sc = scene(sd, ner)
            sv = stat(sc, kind)
            on = int(T_ON * SR / B)
            i = triggers(sv[on:], theta)           # 误触发另算，这里只看插话开始之后
            if i is not None and i * B / SR <= 1.5:
                det += 1
                lat.append((i + HOLD_BLK - 1) * B / SR * 1000)
        row['by_ner'].append({'ner': ner, 'det': round(100 * det / len(TEST), 1),
                              'lat_ms': round(float(np.median(lat)), 0) if lat else None})
    # 误触发：只有回声的测试段（与校准不同的种子）
    fa = 0
    for sd in TEST:
        sc = scene(sd + 100, None)
        sv = stat(sc, kind)
        fa += triggers(sv[w0:], theta) is not None
    row['fa_runs'] = fa
    ok = [c['ner'] for c in row['by_ner'] if c['det'] >= 90]
    row['min_ner'] = min(ok) if ok else None
    OUT['kinds'].append(row)
    print('  %-18s ERLE %5.1f  回声底 %6.1f dB  阈值 %6.1f dB  误触发 %d/%d  最轻可检 %s'
          % (nm, row['erle'], row['floor'], row['theta'], fa, len(TEST),
             ('%+.0f dB' % row['min_ner']) if row['min_ner'] is not None else '检不出'))
    print('      ' + '  '.join('%+.0f:%3.0f%%/%s' % (c['ner'], c['det'], ('%dms' % c['lat_ms']) if c['lat_ms'] is not None else '—')
                               for c in row['by_ner']))

# ══ ③ 半双工 vs 全双工：用户开口之后，被"听见"之前损失了多少 ═════════
K = {r['kind']: r for r in OUT['kinds']}
def lat_at(kind, ner):
    c = [c for c in K[kind]['by_ner'] if c['ner'] == ner][0]
    return c['lat_ms']
OUT['note'] = {
    'raw_min': K['raw']['min_ner'], 'energy_min': K['energy']['min_ner'],
    'fdkf_min': K['fdkf']['min_ner'], 'oracle_min': K['oracle']['min_ner'],
    'raw_erle': K['raw']['erle'], 'energy_erle': K['energy']['erle'],
    'fdkf_erle': K['fdkf']['erle'], 'oracle_erle': K['oracle']['erle'],
    'fdkf_lat0': lat_at('fdkf', 0.0), 'oracle_lat0': lat_at('oracle', 0.0),
    'raw_lat10': lat_at('raw', 10.0), 'fdkf_lat10': lat_at('fdkf', 10.0),
    'raw_fa': K['raw']['fa_runs'], 'fdkf_fa': K['fdkf']['fa_runs'],
}
OUT['const'] = {'dur': DUR, 't_on': T_ON, 't_len': T_LEN, 'hold_ms': HOLD_BLK * B / SR * 1000,
                'smooth_ms': SM * B / SR * 1000, 'cal_seeds': list(CAL), 'test_seeds': list(TEST),
                'ners': list(NERS), 'warm': WARM, 'margin_db': 1.0}
OUT['runtime_s'] = round(time.time() - t0, 1)
print('\n结论量：', json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_aec_duplex.json', 'w'), ensure_ascii=False)
print('写出 demo_aec_duplex.json  %.1f s' % OUT['runtime_s'])
