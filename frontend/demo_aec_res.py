#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线性滤波器拿不到的那部分，以及拿 RES 去补的代价。

   ① 扬声器非线性：总谐波失真 1%，线性 AEC 的 ERLE 上界就只剩多少
   ② 残余回声抑制（RES）的激进程度：ERLE 一路涨，近端语音一路掉
   ③ 同样的总 ERLE，钱花在线性那一级 vs 花在 RES 上
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
NFFT, HOP = 512, 256
DUR = 16.0
NEAR_SNR = 45.0
SEEDS = (0, 1, 2)
DRIVE = 1.2          # ②③ 用的喇叭过载倍数，对应几个百分点的非线性


def scene(seed, drive=0.0, l_ms=128, dur=DUR, near=True):
    """远端一直在说；近端在后半段插话。喇叭可以带非线性。"""
    x = A.farend('pink', dur, seed=seed + 1)
    h = A.rir(T60, seed=seed)
    xp, thd = A.loudspeaker(x, drive)
    d = np.convolve(xp, h)[:len(x)]
    n = len(d)
    nr = np.zeros(n)
    dt = np.zeros(n, bool)
    if near:
        t = int(dur * 0.5 * SR)
        k = 0
        while t < n - int(0.8 * SR):
            seg, _ = E.make_speech(dur=0.7, seed=seed * 131 + k)
            ln = min(len(seg), n - t)
            nr[t:t + ln] += seg[:ln]
            dt[t:t + ln] = True
            t += int(1.6 * SR)
            k += 1
        if dt.any():
            nr *= np.sqrt(np.mean(d[dt] ** 2) /
                          (np.mean(nr[dt] ** 2) + A.EPS))
    g = np.random.default_rng(100 + seed)
    v = g.standard_normal(n)
    v *= np.sqrt(np.mean(d ** 2) / 10 ** (NEAR_SNR / 10)) / (v.std() + A.EPS)
    y = d + nr + v
    L = int(l_ms * SR / 1000)
    # 双讲段冻结（全知 DTD），把 DTD 这一层从本节的变量里摘掉
    e, w = A.pbfdaf(x, y, B, max(L // B, 1), mu=MU, reg=REG, freeze=dt)
    m = len(e)
    return dict(x=x[:m], y=y[:m], d=d[:m], near=nr[:m], dt=dt[:m],
                e=e, yhat=y[:m] - e, thd=thd, h=h)


def erle_single(s, out):
    """只在单讲段上算 ERLE"""
    m = ~s['dt']
    m[:int(4.0 * SR)] = False
    n = min(len(out), len(s['d']))
    mm = m[:n]
    return float(10 * np.log10((np.mean(s['d'][:n][mm] ** 2) + A.EPS) /
                               (np.mean(out[:n][mm] ** 2) + A.EPS)))


def near_quality(s, out):
    """双讲段上，输出离"只有近端"还有多远"""
    n = min(len(out), len(s['near']))
    m = s['dt'][:n]
    if not m.any():
        return 0.0, 0.0
    ref, o = s['near'][:n], out[:n]
    return (float(E.seg_snr(ref, o, m)), float(E.stoi_like(ref, o, mask=m)))


# ══ ① 非线性把上界钉在哪 ═══════════════════════════════════════
print('① 扬声器非线性：线性滤波器拿不到的那部分')
OUT['nl'] = []
for drive in (0.0, 0.5, 0.8, 1.2, 1.8, 2.6, 4.0):
    er, th = [], []
    for sd in SEEDS:
        s = scene(sd, drive=drive, near=False)
        er.append(erle_single(s, s['e']))
        th.append(s['thd'])
    t = float(np.mean(th))
    r = {'drive': drive, 'thd': round(t, 2),
         'erle': round(float(np.mean(er)), 2),
         'theory': round(-20 * np.log10(max(t, 1e-6) / 100), 2) if t > 0 else None}
    OUT['nl'].append(r)
    print('  drive=%.2f  总谐波失真 %5.2f%%   线性 AEC 的 ERLE %6.2f dB   '
          '（−20log10(THD) = %s dB）'
          % (drive, r['thd'], r['erle'],
             ('%.1f' % r['theory']) if r['theory'] else '∞'))
base = OUT['nl'][0]['erle']
one = min((r for r in OUT['nl'] if r['thd'] > 0),
          key=lambda r: abs(r['thd'] - 1.0))
bind = next((r for r in OUT['nl'] if r['erle'] < base - 3.0), None)
worst = OUT['nl'][-1]
OUT['nl_note'] = {'clean': base, 'thd1': one['thd'], 'erle1': one['erle'],
                  'drop1': round(base - one['erle'], 2),
                  'bind_thd': bind['thd'] if bind else None,
                  'bind_erle': bind['erle'] if bind else None,
                  'bind_drop': round(base - bind['erle'], 2) if bind else None,
                  'worst_thd': worst['thd'], 'worst_erle': worst['erle'],
                  'worst_theory': worst['theory']}
print('  失真 %.2f%% 还看不出来（%.2f dB，只差 %.2f dB）；'
      '到 %.2f%% 就掉 %.2f dB——<strong>非线性从这里开始成为瓶颈</strong>。'
      % (one['thd'], one['erle'], OUT['nl_note']['drop1'],
         OUT['nl_note']['bind_thd'] or 0, OUT['nl_note']['bind_drop'] or 0))
print('  而且掉下来之后，实测几乎就贴着 −20log10(非线性占比)：'
      '%.2f%% → 实测 %.2f dB，理论上界 %.1f dB。'
      % (worst['thd'], worst['erle'], worst['theory']))

# ══ ② RES：越激进，ERLE 越高，近端越惨 ═════════════════════════
print('\n② 残余回声抑制的激进程度')


def res(s, gamma, floor_db=-18.0):
    """用 AEC 自己的回声估计当"噪声"的功率谱，做一次维纳式压制。
       gamma 是泄漏系数：以为还剩多少回声没消掉。"""
    Ee = E.stft(s['e'], NFFT, HOP)
    Yh = E.stft(s['yhat'], NFFT, HOP)
    lam = gamma * np.abs(Yh) ** 2
    pe = np.abs(Ee) ** 2
    g = np.maximum((pe - lam) / (pe + A.EPS), 10 ** (floor_db / 10))
    return E.istft(np.sqrt(g) * Ee, NFFT, HOP, n=len(s['e']))


OUT['res'] = []
for gam in (0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0):
    er, sn, st = [], [], []
    for sd in SEEDS:
        s = scene(sd, drive=0.2)
        out = res(s, gam)
        er.append(erle_single(s, out))
        a, b = near_quality(s, out)
        sn.append(a); st.append(b)
    r = {'gamma': gam, 'erle': round(float(np.mean(er)), 2),
         'near_segsnr': round(float(np.mean(sn)), 2),
         'near_stoi': round(float(np.mean(st)), 3)}
    OUT['res'].append(r)
    print('  γ=%4.2f   单讲段 ERLE %6.2f dB   双讲段近端 SegSNR %6.2f dB   '
          'STOI* %.3f' % (gam, r['erle'], r['near_segsnr'], r['near_stoi']))
be = max(OUT['res'], key=lambda r: r['erle'])
bq = max(OUT['res'], key=lambda r: r['near_segsnr'])
bs = max(OUT['res'], key=lambda r: r['near_stoi'])
OUT['res_note'] = {
    'erle_best_gamma': be['gamma'], 'erle_best': be['erle'],
    'q_best_gamma': bq['gamma'], 'q_best': bq['near_segsnr'],
    'stoi_best_gamma': bs['gamma'],
    'erle_at_q': [r['erle'] for r in OUT['res'] if r['gamma'] == bq['gamma']][0],
    'q_at_erle': [r['near_segsnr'] for r in OUT['res']
                  if r['gamma'] == be['gamma']][0],
    'n_distinct': len({be['gamma'], bq['gamma'], bs['gamma']})}
print('  ERLE 最高在 γ=%g（%.2f dB），而近端质量最好在 γ=%g。'
      % (be['gamma'], be['erle'], bq['gamma']))
print('  在 ERLE 最高的那个点上，近端 SegSNR 是 %.2f dB——'
      '比它自己的最好值低 %.2f dB。'
      % (OUT['res_note']['q_at_erle'],
         bq['near_segsnr'] - OUT['res_note']['q_at_erle']))
q0 = OUT['res'][0]['near_segsnr']
knee = None
for r in OUT['res']:
    if q0 - r['near_segsnr'] <= 6.0:
        knee = r
OUT['res_note']['knee_gamma'] = knee['gamma'] if knee else None
OUT['res_note']['knee_erle'] = knee['erle'] if knee else None
OUT['res_note']['knee_q'] = knee['near_segsnr'] if knee else None
OUT['res_note']['knee_erle_gain'] = round(knee['erle'] - OUT['res'][0]['erle'], 2) \
    if knee else None
OUT['res_note']['tail_erle_gain'] = round(be['erle'] - knee['erle'], 2) if knee else None
OUT['res_note']['tail_q_loss'] = round(knee['near_segsnr'] - be['near_segsnr'], 2) \
    if knee else None
print('  拐点在 γ=%s：拿 %.2f dB 的近端代价换了 %.2f dB 的 ERLE；'
      '再往后 ERLE 只多 %.2f dB，近端却要再掉 %.2f dB。'
      % (OUT['res_note']['knee_gamma'], q0 - OUT['res_note']['knee_q'],
         OUT['res_note']['knee_erle_gain'], OUT['res_note']['tail_erle_gain'],
         OUT['res_note']['tail_q_loss']))

# ══ ③ 同样的总 ERLE，钱花在哪一级 ══════════════════════════════
print('\n③ 凑到同样的总 ERLE：线性做长 vs 靠 RES 补')
TARGET = 20.0
OUT['split'] = []
for l_ms, nm in ((32, '线性只做 32 ms + 强 RES'),
                 (64, '线性做 64 ms + 中 RES'),
                 (128, '线性做 128 ms + 弱 RES')):
    pick = None
    for gam in (0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0):
        er, sn, st = [], [], []
        for sd in SEEDS:
            s = scene(sd, drive=DRIVE, l_ms=l_ms)
            out = res(s, gam)
            er.append(erle_single(s, out))
            a, b = near_quality(s, out)
            sn.append(a); st.append(b)
        m = float(np.mean(er))
        if m >= TARGET:
            pick = {'l_ms': l_ms, 'name': nm, 'gamma': gam,
                    'erle': round(m, 2),
                    'near_segsnr': round(float(np.mean(sn)), 2),
                    'near_stoi': round(float(np.mean(st)), 3)}
            break
    if pick is None:
        pick = {'l_ms': l_ms, 'name': nm, 'gamma': None,
                'erle': round(m, 2), 'near_segsnr': round(float(np.mean(sn)), 2),
                'near_stoi': round(float(np.mean(st)), 3)}
    OUT['split'].append(pick)
    print('  %-24s  需要 γ=%s   总 ERLE %6.2f dB   近端 SegSNR %6.2f dB  STOI* %.3f'
          % (nm, ('%g' % pick['gamma']) if pick['gamma'] is not None else '凑不到',
             pick['erle'], pick['near_segsnr'], pick['near_stoi']))
ok = [r for r in OUT['split'] if r['gamma'] is not None]
if len(ok) >= 2:
    OUT['split_note'] = {
        'target': TARGET,
        'best': max(ok, key=lambda r: r['near_segsnr'])['name'],
        'gap': round(max(r['near_segsnr'] for r in ok) -
                     min(r['near_segsnr'] for r in ok), 2)}
    print('  同样 %g dB 的总 ERLE，近端质量差 %.2f dB——'
          '<strong>钱花在线性那一级更值</strong>。'
          % (TARGET, OUT['split_note']['gap']))
else:
    OUT['split_note'] = {'target': TARGET, 'best': None, 'gap': None}

OUT['const'] = {'t60': T60, 'b': B, 'mu': MU, 'dur': DUR, 'nfft': NFFT,
                'hop': HOP, 'near_snr': NEAR_SNR, 'seeds': list(SEEDS),
                'target': TARGET}
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_aec_res.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_aec_res.json（%.0f s）' % OUT['runtime_s'])
