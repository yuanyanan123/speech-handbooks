#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双讲检测：漏检和误检根本不是一回事。

   ① 不设 DTD、在线 DTD、全知 DTD 三条线放一起
   ② 阈值扫描：漏检率、误检率，以及最后拿到的 ERLE——
      最优工作点在不在"两种错误大致相等"那里
   ③ 把两种错误各自单独注入，量它们的代价换算成秒
   ④ 近端比回声响多少，决定 DTD 要多灵敏
"""
import numpy as np, json, time
import enhlib as E
import aeclib as A

OUT = {}
t0 = time.time()
SR = A.SR
T60 = 0.25
L = int(0.128 * SR)
B = 256
NP = L // B
MU = 0.3
REG = 0.1
DUR = 24.0
NEAR_SNR = 40.0
SEEDS = (0, 1, 2)
NER_DB = 0.0            # 近端相对回声的电平（双讲段内）


# ══ 造一段"远端一直在说、近端偶尔插话"的信号 ═══════════════════
_SC = {}


def scene(seed, ner_db=NER_DB, duty=0.25, dur=DUR):
    key = (seed, ner_db, dur)
    if key in _SC:
        return _SC[key]
    x = A.farend('speech', dur, seed=seed + 1)
    h = A.rir(T60, seed=seed)
    d = np.convolve(x, h)[:len(x)]
    g = np.random.default_rng(500 + seed)
    n = len(d)
    near = np.zeros(n)
    dt = np.zeros(n, bool)
    # 近端插话：每 2 s 一段，每段 0.6 s，前 4 s 留给滤波器先收敛
    t = int(4.0 * SR)
    k = 0
    while t < n - int(0.8 * SR):
        seg, _ = E.make_speech(dur=0.6, seed=seed * 97 + k)
        ln = min(len(seg), n - t)
        near[t:t + ln] += seg[:ln]
        dt[t:t + ln] = True
        t += int(2.0 * SR)
        k += 1
    if near.std() > 0:
        pe = np.mean(d[dt] ** 2) if dt.any() else np.mean(d ** 2)
        near *= np.sqrt(pe / (np.mean(near[dt] ** 2) + A.EPS)) * \
            10 ** (ner_db / 20)
    v = g.standard_normal(n)
    v *= np.sqrt(np.mean(d ** 2) / 10 ** (NEAR_SNR / 10)) / (v.std() + A.EPS)
    y = d + near + v
    _SC[key] = (x, y, d, near, dt, h)
    return _SC[key]


# ══ 带在线 DTD 的分区块频域自适应 ══════════════════════════════
WARM = 2.0            # 前 2 s 先让滤波器收敛，DTD 不参与——真实系统也这么做


def run(x, y, h, mode='online', kappa=4.0, oracle=None, force=None, hang=0):
    """mode: none（从不冻结）/ online（在线 DTD）/ oracle（已知真值）
       force: 和 y 等长的布尔数组，True 处<strong>强制冻结</strong>（用来注入误检）"""
    N, K = 2 * B, B + 1
    nb = len(y) // B
    W = np.zeros((NP, K), complex)
    Xb = np.zeros((NP, K), complex)
    Pw = np.zeros(K)
    e = np.zeros(nb * B)
    froz = np.zeros(nb, bool)
    mis = np.zeros(nb)
    xprev = np.zeros(B)
    pref = 1e-20
    xi_s = 1.0
    hcnt = 0
    for b in range(nb):
        xb = x[b * B:(b + 1) * B]
        X = np.fft.rfft(np.concatenate([xprev, xb]), N)
        xprev = xb
        Xb = np.roll(Xb, 1, axis=0)
        Xb[0] = X
        yh = np.fft.irfft((Xb * W).sum(0), N)[B:]
        yb = y[b * B:(b + 1) * B]
        eb = yb - yh
        e[b * B:(b + 1) * B] = eb
        Pw = 0.9 * Pw + 0.1 * (np.abs(Xb) ** 2).sum(0)
        pb = float(np.mean(np.abs(X) ** 2))
        pref = max(pref * 0.9995, pb)
        # ── 判决：麦克风收到的，比滤波器预测的回声大多少 ──────────
        xi = float((np.mean(yb ** 2) + A.EPS) / (np.mean(yh ** 2) + A.EPS))
        xi_s = 0.6 * xi_s + 0.4 * xi
        if mode == 'none':
            hold = False
        elif mode == 'oracle':
            hold = bool(oracle[b * B:(b + 1) * B].any())
        else:
            hold = (b * B / SR > WARM) and (xi_s > kappa)
        if force is not None and force[b * B:(b + 1) * B].any():
            hold = True
        if hold:
            hcnt = hang                       # 挂起：判完之后再多冻结几块
        elif hcnt > 0:
            hcnt -= 1
            hold = True
        froz[b] = hold
        mis[b] = A.misalign(np.fft.irfft(W, N, axis=-1)[:, :B].reshape(-1), h)
        if hold or pb < pref * 1e-3:
            continue
        Eb = np.fft.rfft(np.concatenate([np.zeros(B), eb]), N)
        G = np.conj(Xb) * Eb[None, :] / ((Pw + REG * NP * pref)[None, :] + 1e-20)
        g = np.fft.irfft(G, N, axis=-1)
        g[:, B:] = 0.0
        W = W + 2.0 * MU * np.fft.rfft(g, N, axis=-1)
    w = np.fft.irfft(W, N, axis=-1)[:, :B].reshape(-1)
    return e, w, froz, mis


def rates(froz, dt):
    """按块统计漏检（双讲块没冻结）与误检（单讲块冻结了）"""
    nb = len(froz)
    dtb = np.array([dt[b * B:(b + 1) * B].any() for b in range(nb)])
    act = np.arange(nb) >= int(4.0 * SR / B)        # 只统计收敛期之后
    d_, s_ = dtb & act, (~dtb) & act
    miss = float(np.mean(~froz[d_])) if d_.any() else 0.0
    fa = float(np.mean(froz[s_])) if s_.any() else 0.0
    return miss, fa


def far_erle(d, e, dt):
    """只在<strong>单讲</strong>段上算 ERLE——双讲段的 e 本来就该有近端"""
    n = min(len(d), len(e))
    m = ~dt[:n]
    m[:int(4.0 * SR)] = False
    return float(10 * np.log10((np.mean(d[:n][m] ** 2) + A.EPS) /
                               (np.mean(e[:n][m] ** 2) + A.EPS)))


# ══ ① 三条线 ══════════════════════════════════════════════════
print('① 不设 DTD / 在线 DTD / 全知 DTD')
OUT['modes'] = []
TRACE = None
for mode, nm, kw in (('none', '从不冻结', {}),
                     ('online', '在线 DTD（κ=4）', {'kappa': 4.0}),
                     ('oracle', '全知 DTD', {})):
    er, ms, mi, fa = [], [], [], []
    for sd in SEEDS:
        x, y, d, near, dt, h = scene(sd)
        e, w, froz, mis = run(x, y, h, mode=mode, oracle=dt, **kw)
        er.append(far_erle(d, e, dt))
        ms.append(A.misalign(w, h))
        a, b_ = rates(froz, dt)
        mi.append(a); fa.append(b_)
        if sd == SEEDS[0]:
            TRACE = TRACE or {}
            TRACE[nm] = [round(float(v), 2) for v in mis[::4]]
    r = {'mode': nm, 'erle': round(float(np.mean(er)), 2),
         'misalign': round(float(np.mean(ms)), 2),
         'miss': round(float(np.mean(mi)) * 100, 1),
         'fa': round(float(np.mean(fa)) * 100, 1)}
    OUT['modes'].append(r)
    print('  %-16s 单讲段 ERLE %6.2f dB   最终失调 %6.2f dB   漏检 %5.1f%%  误检 %5.1f%%'
          % (nm, r['erle'], r['misalign'], r['miss'], r['fa']))
OUT['trace'] = TRACE
OUT['trace_step_ms'] = round(4 * B / SR * 1000, 1)
n0, n2 = OUT['modes'][0], OUT['modes'][2]
OUT['no_dtd_cost'] = round(n2['erle'] - n0['erle'], 2)
print('  不设 DTD 比全知差 %.2f dB——而这两者唯一的区别就是双讲时停不停更新。'
      % OUT['no_dtd_cost'])

# ══ ② 阈值扫描 ════════════════════════════════════════════════
print('\n② 在线 DTD 的阈值 κ：两种错误和最后的 ERLE')
OUT['sweep'] = []
for kap in (1.05, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 30.0):
    er, mi, fa = [], [], []
    for sd in SEEDS:
        x, y, d, near, dt, h = scene(sd)
        e, w, froz, mis = run(x, y, h, mode='online', kappa=kap)
        er.append(far_erle(d, e, dt))
        a, b_ = rates(froz, dt)
        mi.append(a); fa.append(b_)
    r = {'kappa': kap, 'miss': round(float(np.mean(mi)) * 100, 1),
         'fa': round(float(np.mean(fa)) * 100, 1),
         'erle': round(float(np.mean(er)), 2)}
    OUT['sweep'].append(r)
    print('  κ=%5.1f  漏检 %5.1f%%   误检 %5.1f%%   单讲段 ERLE %6.2f dB'
          % (kap, r['miss'], r['fa'], r['erle']))
best = max(OUT['sweep'], key=lambda r: r['erle'])
eer = min(OUT['sweep'], key=lambda r: abs(r['miss'] - r['fa']))
OUT['best'] = best
OUT['eer_point'] = eer
OUT['eer_cost'] = round(best['erle'] - eer['erle'], 2)
print('  最优工作点 κ=%g：漏检 %.1f%%、误检 %.1f%%——<strong>两者差 %.0f 倍</strong>。'
      % (best['kappa'], best['miss'], best['fa'],
         max(best['fa'], best['miss']) / max(min(best['fa'], best['miss']), 1e-9)))
print('  如果按"两种错误相等"去定（κ=%g），ERLE 要低 %.2f dB。'
      % (eer['kappa'], OUT['eer_cost']))

# ══ ③ 把两种错误单独注入，换算成秒 ═════════════════════════════
print('\n③ 一次漏检值几秒，一次误检值几秒')
OUT['inject'] = {'miss': [], 'fa': []}
for ms_dur in (0.05, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8):
    rec, jump = [], []
    for sd in SEEDS + (3, 4):
        x, y, d, near, dt, h = scene(sd)
        # 全知 DTD，但在第一段双讲上"漏检" ms_dur 秒
        orc = dt.copy()
        idx = np.where(dt)[0]
        st = idx[0]
        orc[st:st + int(ms_dur * SR)] = False
        e, w, froz, mis = run(x, y, h, mode='oracle', oracle=orc)
        b0 = st // B
        nmb = int(np.ceil(ms_dur * SR / B))
        pre = float(np.mean(mis[max(b0 - 8, 0):b0]))
        bend = b0 + nmb                      # 漏检窗结束的那一块
        post = float(np.max(mis[b0:bend + 2]))
        after = mis[bend:]
        back = np.where(after <= pre + 1.0)[0]
        rec.append(float(back[0] * B / SR) if len(back) else np.nan)
        jump.append(post - pre)
    OUT['inject']['miss'].append(
        {'dur': ms_dur, 'jump': round(float(np.nanmean(jump)), 2),
         'recover': round(float(np.nanmean(rec)), 2)})
    print('  漏检 %.2f s → 失调恶化 %5.2f dB，要 %5.2f s 才回到原来的水平'
          % (ms_dur, OUT['inject']['miss'][-1]['jump'],
             OUT['inject']['miss'][-1]['recover']))
for frac in (0.1, 0.3, 0.5, 0.8):
    ms_, er = [], []
    for sd in SEEDS + (3, 4):
        x, y, d, near, dt, h = scene(sd)
        g = np.random.default_rng(900 + sd)
        force = np.zeros(len(y), bool)
        nb = len(y) // B
        pick = g.random(nb) < frac
        for b in np.where(pick)[0]:
            force[b * B:(b + 1) * B] = True
        e, w, froz, mis = run(x, y, h, mode='oracle', oracle=dt, force=force)
        ms_.append(A.misalign(w, h))
        er.append(far_erle(d, e, dt))
    OUT['inject']['fa'].append(
        {'frac': frac, 'misalign': round(float(np.mean(ms_)), 2),
         'erle': round(float(np.mean(er)), 2)})
    print('  误检覆盖 %.0f%% 的单讲时间 → 最终失调 %6.2f dB，ERLE %6.2f dB'
          % (frac * 100, OUT['inject']['fa'][-1]['misalign'],
             OUT['inject']['fa'][-1]['erle']))
m02 = [r for r in OUT['inject']['miss'] if r['dur'] == 0.4][0]
f50 = [r for r in OUT['inject']['fa'] if r['frac'] == 0.5][0]
base_er = OUT['modes'][2]['erle']
short = [r for r in OUT['inject']['miss'] if r['dur'] <= 0.2]
OUT['miss_knee'] = {'free_up_to': max(r['dur'] for r in short if r['jump'] < 0.5)
                    if any(r['jump'] < 0.5 for r in short) else None,
                    'free_jump': round(max(r['jump'] for r in short), 2)}
OUT['asym'] = {
    'miss_dur': m02['dur'], 'miss_jump': m02['jump'], 'miss_recover': m02['recover'],
    'fa_frac': f50['frac'], 'fa_cost': round(base_er - f50['erle'], 2),
    'ratio': round(m02['recover'] / max(m02['dur'], 1e-9), 0)}
print('  一次 %.1f s 的漏检要 %.1f s 才还清（%.0f 倍）；'
      '而误检掉一半的更新机会，只让 ERLE 少 %.2f dB。'
      % (m02['dur'], m02['recover'], OUT['asym']['ratio'], OUT['asym']['fa_cost']))

# ══ ④ 阈值和挂起：两个旋钮一起看 ═══════════════════════════════
print('\n④ 阈值 κ × 挂起块数：两个旋钮一起扫')
OUT['grid'] = []
for kap in (2.0, 3.0, 5.0, 10.0, 30.0):
    row = {'kappa': kap, 'cells': []}
    for hb in (0, 2, 4, 8):
        er, mi, fa = [], [], []
        for sd in SEEDS:
            x, y, d, near, dt, h = scene(sd)
            e, w, froz, mis = run(x, y, h, mode='online', kappa=kap, hang=hb)
            er.append(far_erle(d, e, dt))
            a, b_ = rates(froz, dt)
            mi.append(a); fa.append(b_)
        row['cells'].append({'hang': hb, 'ms': round(hb * B / SR * 1000, 1),
                             'miss': round(float(np.mean(mi)) * 100, 1),
                             'fa': round(float(np.mean(fa)) * 100, 1),
                             'erle': round(float(np.mean(er)), 2)})
    b = max(row['cells'], key=lambda c: c['erle'])
    row['best_hang'] = b['hang']
    row['best_erle'] = b['erle']
    row['gain'] = round(b['erle'] - row['cells'][0]['erle'], 2)
    OUT['grid'].append(row)
    print('  κ=%5.1f  ' % kap + '  '.join(
        '%d块→%5.2f' % (c['hang'], c['erle']) for c in row['cells'])
        + '   最好 %d 块（%+.2f dB）' % (b['hang'], row['gain']))
cells = [(r['kappa'], c) for r in OUT['grid'] for c in r['cells']]
bk, bc = max(cells, key=lambda t: t[1]['erle'])
OUT['grid_best'] = {'kappa': bk, 'hang': bc['hang'], 'ms': bc['ms'],
                    'miss': bc['miss'], 'fa': bc['fa'], 'erle': bc['erle']}
loose = [r for r in OUT['grid'] if r['kappa'] == 10.0][0]
OUT['hang_note'] = {'loose_kappa': 10.0, 'gain': loose['gain'],
                    'best_hang': loose['best_hang'],
                    'miss0': loose['cells'][0]['miss'],
                    'missb': [c for c in loose['cells']
                              if c['hang'] == loose['best_hang']][0]['miss']}
print('  全局最好：κ=%g + 挂起 %d 块（%.0f ms），漏检 %.1f%%、误检 %.1f%%、'
      'ERLE %.2f dB。' % (bk, bc['hang'], bc['ms'], bc['miss'], bc['fa'],
                          bc['erle']))
print('  阈值放松到 κ=10 时，挂起能补回 %+.2f dB（漏检 %.1f%%→%.1f%%）——'
      '<strong>挂起是比调阈值更便宜的那个旋钮</strong>。'
      % (loose['gain'], OUT['hang_note']['miss0'], OUT['hang_note']['missb']))

OUT['const'] = {'t60': T60, 'taps': L, 'b': B, 'nparts': NP, 'mu': MU,
                'dur': DUR, 'near_snr': NEAR_SNR, 'ner_db': NER_DB,
                'seeds': list(SEEDS), 'blk_ms': round(B / SR * 1000, 1),
                'warm_s': WARM}
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_aec_dtd.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_aec_dtd.json（%.0f s）' % OUT['runtime_s'])
