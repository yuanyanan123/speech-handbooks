#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""02 / 03 节算例：EER、DCF、校准，以及"要多少试验才测得准"。"""
import numpy as np, json, math
from svlib import det_curve, eer, dcf, bayes_thr, cllr

rng = np.random.default_rng(0)
OUT = {}
tar = np.load('sc_tar.npy')            # PLDA 对数似然比（模型正确，所以天然校准）
non = np.load('sc_non.npy')
e, thr_e = eer(tar, non)
OUT['base'] = {'n_tar': len(tar), 'n_non': len(non), 'eer': round(e * 100, 3)}
print('基准系统：%d 目标 / %d 冒充，EER %.2f%%' % (len(tar), len(non), e * 100))

# ══ ① 工作点：EER 那个点几乎没人用 ═══════════════════════════
print('\n① 不同应用的工作点差得有多远')
print('  P_target   贝叶斯阈值   minDCF   该点的 Pmiss / Pfa')
OUT['ops'] = []
for p in (0.5, 0.1, 0.05, 0.01, 0.001):
    m, th = dcf(tar, non, p_tar=p)
    bt = bayes_thr(p)
    pm = float(np.mean(tar < th)); pf = float(np.mean(non >= th))
    OUT['ops'].append({'p': p, 'bayes_thr': round(bt, 2), 'mindcf': round(m, 4),
                       'pmiss': round(pm * 100, 2), 'pfa': round(pf * 100, 3),
                       'thr': round(th, 2)})
    print('  %7.3f   %8.2f    %6.4f   %5.2f%% / %6.3f%%' % (p, bt, m, pm * 100, pf * 100))
print('  EER 那个点对应的阈值是 %.2f；而 P_target=0.001 的最优阈值是 %.2f。'
      % (thr_e, OUT['ops'][-1]['thr']))
print('  <strong>差了 %.1f 个自然对数单位</strong>——报 EER 等于报一个没人用的工作点。'
      % abs(OUT['ops'][-1]['thr'] - thr_e))

# ══ ② 校准：minDCF 好看不代表能用 ═════════════════════════════
print('\n② 同一套分数，只做单调变换，minDCF 一点不变，actDCF 天差地别')
OUT['calib'] = []
for tag, f in (('原样（模型正确，天然校准）', lambda s: s),
               ('整体平移 +3', lambda s: s + 3.0),
               ('整体平移 −3', lambda s: s - 3.0),
               ('缩放 ×0.3（过于保守）', lambda s: s * 0.3),
               ('缩放 ×3（过于自信）', lambda s: s * 3.0)):
    t2, n2 = f(tar), f(non)
    p = 0.01
    md, _ = dcf(t2, n2, p_tar=p)
    ad, _ = dcf(t2, n2, p_tar=p, thr=bayes_thr(p))
    e2, _ = eer(t2, n2)
    r = {'tag': tag, 'eer': round(e2 * 100, 2), 'mindcf': round(md, 4),
         'actdcf': round(ad, 4), 'cllr': round(cllr(t2, n2), 3)}
    OUT['calib'].append(r)
    print('  %-24s EER %5.2f%%  minDCF %6.4f  actDCF %6.4f  Cllr %.3f'
          % (tag, r['eer'], r['mindcf'], r['actdcf'], r['cllr']))
print('  EER 和 minDCF 完全不动（单调变换不改变排序），'
      '而 <strong>actDCF 最多差 %.1f 倍</strong>。'
      % (max(r['actdcf'] for r in OUT['calib']) / OUT['calib'][0]['actdcf']))
print('  上线时你只能用一个固定阈值——所以真正决定体验的是 actDCF，不是 minDCF。')

# ══ ③ 要多少试验才测得准 ═════════════════════════════════════
def boot_eer(t, n, reps=400, seed=0):
    g = np.random.default_rng(seed)
    out = []
    for _ in range(reps):
        a = t[g.integers(0, len(t), len(t))]
        b = n[g.integers(0, len(n), len(n))]
        out.append(eer(a, b)[0])
    return np.array(out)


print('\n③ EER 的置信区间：自助法，目标对与冒充对同比例缩放')
OUT['ci'] = []
for f in (0.02, 0.05, 0.1, 0.25, 0.5, 1.0):
    nt, nn = int(len(tar) * f), int(len(non) * f)
    t = tar[:nt]; n = non[:nn]
    b = boot_eer(t, n, reps=300, seed=3) * 100
    lo, hi = np.percentile(b, [2.5, 97.5])
    OUT['ci'].append({'n_tar': nt, 'n_non': nn, 'eer': round(float(b.mean()), 3),
                      'lo': round(float(lo), 3), 'hi': round(float(hi), 3),
                      'width': round(float(hi - lo), 3)})
    print('  %6d 目标 / %7d 冒充   EER %.2f%%   95%% 区间 [%.2f, %.2f]  宽 %.2f'
          % (nt, nn, b.mean(), lo, hi, hi - lo))
print('  <strong>目标对的数量决定了 EER 的精度</strong>：'
      '它是个比例，误差 ∝ 1/√(错误个数)。')

# 经验法则：要看到 k 个错误，需要多少试验
print('\n  "三十法则"：要让某个比例的估计有意义，至少要看到 ~30 个错误')
OUT['rule30'] = []
for p in (0.10, 0.05, 0.02, 0.01, 0.005, 0.001):
    OUT['rule30'].append({'rate': p, 'n': int(math.ceil(30 / p))})
    print('    要测 %.1f%% 的错误率 → 至少 %s 个试验' % (p * 100, f'{int(30/p):,}'))

# 两个系统差多少才算"真的更好"
def power_eer(e1, e2, n_tar, reps=600, seed=5):
    """两套系统在同一批试验上比 EER：多大差距能以 80% 把握检出"""
    g = np.random.default_rng(seed)
    hit = 0
    for _ in range(reps):
        a = g.binomial(n_tar, e1) / n_tar
        b = g.binomial(n_tar, e2) / n_tar
        se = math.sqrt(e1 * (1 - e1) / n_tar + e2 * (1 - e2) / n_tar) + 1e-12
        hit += abs(a - b) / se > 1.96
    return hit / reps


print('\n  两套系统的 EER 差多少才算真的不同（同一批试验，80%% 功效）：')
OUT['power'] = []
for e1, e2 in ((0.02, 0.022), (0.02, 0.025), (0.02, 0.03), (0.02, 0.04)):
    got = None
    for n in (1000, 2000, 5000, 10000, 20000, 50000, 100000):
        if power_eer(e1, e2, n) >= 0.8:
            got = n
            break
    OUT['power'].append({'e1': e1, 'e2': e2, 'n_tar': got})
    print('    %.1f%% vs %.1f%%   需要 %s 个目标对'
          % (e1 * 100, e2 * 100, f'{got:,}' if got else '>100,000'))
print('    <strong>2.0%% 和 2.2%% 的差别，要几万个目标对才分得开</strong>——')
print('    而常见的评测集只有几千对。榜单上相邻几名的差距通常没有统计意义。')

# ══ ④ DET 曲线的数据 ═════════════════════════════════════════
s, miss, fa = det_curve(tar, non)
k = np.linspace(0, len(s) - 1, 400).astype(int)
OUT['det'] = {'miss': [round(float(x), 6) for x in miss[k]],
              'fa': [round(float(x), 6) for x in fa[k]]}
OUT['hist'] = {'tar': np.histogram(tar, bins=60, range=(-40, 60))[0].tolist(),
               'non': np.histogram(non, bins=60, range=(-40, 60))[0].tolist(),
               'lo': -40, 'hi': 60}
json.dump(OUT, open('demo_metric.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_metric.json')
