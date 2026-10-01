#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""12 / 20 节：误唤醒率是个泊松率，所以"跑了一天没误唤醒"几乎什么都没证明。

① 零事件时能给出的上界（三法则），以及要证明一个指标得跑多久
② 观测到 k 次时的精确置信区间，以及"要看到几次才算测准"
③ 比较两个系统：要跑多久才能分辨出 1.5 倍 / 2 倍的差别
④ 蒙特卡洛验证上面三条的覆盖率
⑤ 同一个系统，换一套负样本素材，测出来的 FA/小时差多少
"""
import json, math
import numpy as np
from scipy import stats

rng = np.random.default_rng(11)
OUT = {}
CONF = 0.95


def pois_ci(k, T, conf=CONF):
    """观测到 k 次、观测 T 小时，率 λ 的精确（Garwood）置信区间"""
    a = 1 - conf
    lo = 0.0 if k == 0 else stats.chi2.ppf(a / 2, 2 * k) / 2 / T
    hi = stats.chi2.ppf(1 - a / 2, 2 * (k + 1)) / 2 / T
    return lo, hi


# ══ ① 零事件：三法则 ═════════════════════════════════════════
print('① 一次误唤醒都没观测到，能说明什么')
print('  观测 T 小时、0 次事件 → 95%% 上界 λ ≤ %.1f/T（精确值 %.4f/T）'
      % (3, stats.chi2.ppf(CONF, 2) / 2))
print('  %10s %14s %16s' % ('观测时长', '95% 上界（次/小时）', '换算成 次/天'))
OUT['zero'] = []
for T in (1, 8, 24, 100, 720, 2400):
    _, hi = pois_ci(0, T)
    r = {'hours': T, 'hi_hour': round(hi, 5), 'hi_day': round(hi * 24, 4)}
    OUT['zero'].append(r)
    print('  %8d h %16.5f %16.3f' % (T, hi, hi * 24))

SPECS = [('0.5 次/天', 0.5), ('0.2 次/天', 0.2), ('0.1 次/天', 0.1),
         ('0.05 次/天', 0.05), ('0.02 次/天', 0.02)]
print('\n  反过来：要"零事件地"证明一个指标，得跑多久')
print('  %12s %16s %14s' % ('目标', '所需负样本时长', '折合天数'))
OUT['spec'] = []
z = stats.chi2.ppf(CONF, 2) / 2
for name, per_day in SPECS:
    lam = per_day / 24.0
    T = z / lam
    r = {'spec': name, 'per_day': per_day, 'hours': round(T, 1),
         'days': round(T / 24, 1)}
    OUT['spec'].append(r)
    print('  %12s %14.0f 小时 %12.1f 天' % (name, T, T / 24))

# ══ ② 有事件：要看到几次才算测准 ═════════════════════════════
print('\n② 观测到 k 次时，置信区间有多宽')
print('  %6s %18s %16s' % ('k', '95% 区间（相对 k/T）', '相对宽度'))
OUT['kwidth'] = []
for k in (1, 3, 5, 10, 20, 30, 50, 100, 300):
    lo, hi = pois_ci(k, 1.0)
    rel = (hi - lo) / max(k, 1e-9)
    r = {'k': k, 'lo': round(lo / max(k, 1e-9), 3), 'hi': round(hi / max(k, 1e-9), 3),
         'rel': round(rel, 3)}
    OUT['kwidth'].append(r)
    print('  %6d   [%.2f, %.2f] × 点估计 %13.1f%%' % (k, r['lo'], r['hi'], rel * 100))
need = next(r for r in OUT['kwidth'] if r['rel'] <= 0.8)
OUT['k_ok'] = need
print('  → 要把相对宽度压到 ±40%%（总宽 80%%），至少要观测到 %d 次事件。' % need['k'])

print('\n  把这两件事合起来：想把一个指标"测准"（而不只是给上界）')
print('  %12s %14s %14s' % ('目标', '要观测到的次数', '所需时长'))
OUT['measure'] = []
for name, per_day in SPECS:
    lam = per_day / 24.0
    T = need['k'] / lam
    r = {'spec': name, 'k': need['k'], 'hours': round(T, 1),
         'days': round(T / 24, 1)}
    OUT['measure'].append(r)
    print('  %12s %12d 次 %12.0f 小时（%.0f 天）' % (name, need['k'], T, T / 24))

# ══ ③ 比较两个系统 ═══════════════════════════════════════════
def hours_to_detect(lam_a, ratio, power=0.8, alpha=0.05):
    """两个泊松率之比为 ratio 时，各跑 T 小时能以 power 的功效检出差异。
       用方差稳定变换 2(√(λT)) 近似，再用蒙特卡洛核对。"""
    lam_b = lam_a / ratio
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    # Var[2√(kT)] ≈ 1，差值的方差 = 2
    d = 2 * (math.sqrt(lam_a) - math.sqrt(lam_b))
    return 2 * ((za + zb) / d) ** 2


def mc_power(lam_a, ratio, T, n=20000, alpha=0.05):
    lam_b = lam_a / ratio
    ka = rng.poisson(lam_a * T, n)
    kb = rng.poisson(lam_b * T, n)
    with np.errstate(invalid='ignore'):
        zstat = (2 * np.sqrt(ka) - 2 * np.sqrt(kb)) / math.sqrt(2)
    return float((np.abs(zstat) > stats.norm.ppf(1 - alpha / 2)).mean())


print('\n③ 想说"新版比旧版好"，要跑多久')
print('  旧版 0.5 次/天，新版好 R 倍；80% 功效、双侧 5%')
print('  %8s %16s %14s %14s' % ('R', '每套所需时长', '折合天数', '蒙特卡洛功效'))
OUT['compare'] = []
lam0 = 0.5 / 24
for R in (1.2, 1.5, 2.0, 3.0, 5.0):
    T = hours_to_detect(lam0, R)
    p = mc_power(lam0, R, T)
    r = {'ratio': R, 'hours': round(T, 1), 'days': round(T / 24, 1),
         'mc_power': round(p, 3)}
    OUT['compare'].append(r)
    print('  %8.1f %13.0f 小时 %12.1f 天 %14.3f' % (R, T, T / 24, p))

# ══ ④ 蒙特卡洛验证覆盖率 ═════════════════════════════════════
print('\n④ 蒙特卡洛核对：上面那些区间真的有 95% 的覆盖率吗')
print('  %14s %14s %14s' % ('真实 λ（次/天）', '观测时长', '区间覆盖率'))
OUT['cover'] = []
for per_day, T in ((0.5, 240), (0.2, 720), (0.1, 1440)):
    lam = per_day / 24
    k = rng.poisson(lam * T, 20000)
    lo = np.where(k == 0, 0.0, stats.chi2.ppf(0.025, 2 * np.maximum(k, 1)) / 2 / T)
    hi = stats.chi2.ppf(0.975, 2 * (k + 1)) / 2 / T
    cov = float(((lo <= lam) & (lam <= hi)).mean())
    r = {'per_day': per_day, 'hours': T, 'cover': round(cov * 100, 2),
         'zero_frac': round(float((k == 0).mean()) * 100, 2)}
    OUT['cover'].append(r)
    print('  %12.2f %12d h %13.2f%%  （其中 %.1f%% 的重复实验一次都没观测到）'
          % (per_day, T, cov * 100, r['zero_frac']))

# ══ ⑤ 同一个系统，换一套素材 ═════════════════════════════════
print('\n⑤ 同一个系统，换一套负样本素材，测出来的 FA/天 差多少')
print('  模型：误唤醒只在"像语音"的片段上发生，所以率 ∝ 语音占比 × 该素材的难度')
CORP = [('安静房间（偶有人声）', 0.05, 1.0),
        ('办公室背景', 0.25, 1.2),
        ('电视剧对白', 0.75, 1.8),
        ('播客 / 有声书', 0.95, 2.1),
        ('商场嘈杂人声', 0.60, 2.6)]
base = 0.5          # 在"语音占比 1.0、难度 1.0"下的基准 次/天
OUT['corpus'] = []
print('  %20s %10s %10s %14s' % ('素材', '语音占比', '难度', '测出的 次/天'))
for name, occ, hard in CORP:
    v = base * occ * hard
    OUT['corpus'].append({'name': name, 'occ': occ, 'hard': hard,
                          'fa_day': round(v, 3)})
    print('  %20s %9.2f %10.1f %14.3f' % (name, occ, hard, v))
vals = [r['fa_day'] for r in OUT['corpus']]
OUT['corpus_spread'] = round(max(vals) / min(vals), 1)
print('  最难的素材和最容易的差 <strong>%.0f 倍</strong>——'
      % OUT['corpus_spread'])
print('  这还只是素材，模型一个字没改。')

OUT['conf'] = CONF
OUT['rule3'] = round(float(z), 3)

print('\n结论')
z0 = {r['hours']: r for r in OUT['zero']}
print('  ① 跑 24 小时、一次没误唤醒，只能说明 λ ≤ %.3f 次/天（95%%）——'
      % z0[24]['hi_day'])
sp = {r['per_day']: r for r in OUT['spec']}
print('     而常见的指标是 0.1 次/天。要"零事件地"证明它，得跑 %.0f 小时（%.0f 天）。'
      % (sp[0.1]['hours'], sp[0.1]['days']))
print('     <strong>"跑了一天没问题"和"达标"之间差 %.0f 倍的时长</strong>。'
      % (sp[0.1]['hours'] / 24))
me = {r['spec']: r for r in OUT['measure']}
print('  ② 想把它"测准"而不只是给上界，要观测到 %d 次事件——'
      % need['k'])
print('     0.1 次/天 的系统，那就是 %.0f 天的负样本。'
      % me['0.1 次/天']['days'])
cp = {r['ratio']: r for r in OUT['compare']}
print('  ③ 想说新版把 0.5 次/天 降到了 0.25（好 2 倍），'
      '每套要跑 %.0f 天；只好 1.2 倍的话要 %.0f 天。'
      % (cp[2.0]['days'], cp[1.2]['days']))
print('     <strong>大多数"我们优化了误唤醒"的结论，样本量根本不够支撑</strong>。')
print('  ④ 覆盖率核对通过（%.1f%%–%.1f%%，名义 95%%）——'
      % (min(r['cover'] for r in OUT['cover']),
         max(r['cover'] for r in OUT['cover'])))
print('     略高于名义值是对的：事件数是离散的，精确泊松区间必然偏保守。')
print('     顺带一个巧合：这里"要观测到 30 次"和 04 节里估错误率的"30 法则"')
print('     是同一个数，但来路不同——那边是二项分布的变异系数，这边是泊松的。')
print('  ⑤ 而且这一切的前提是素材固定：换一套素材，同一个模型的 FA/天 差 %.0f 倍。'
      % OUT['corpus_spread'])
print('     <strong>没有说明负样本构成的 FA/天，是个没有单位的数</strong>。')

json.dump(OUT, open('demo_fa.json', 'w'), ensure_ascii=False)
print('\n→ demo_fa.json')
