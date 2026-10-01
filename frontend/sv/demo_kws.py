#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""13 / 12 / 15 节算例：唤醒词怎么选、误唤醒率的单位、级联的功耗最优点。"""
import numpy as np, json, math, collections
from pypinyin.constants import PHRASES_DICT
from pypinyin import pinyin, Style

rng = np.random.default_rng(0)
OUT = {}

# ══ ① 音节分布：唤醒词越长，撞上的机会指数下降 ═══════════════
cnt = collections.Counter()
for w, py in PHRASES_DICT.items():
    for p in py:
        if p:
            cnt[p[0]] += 1
tot = sum(cnt.values())
pr = {k: v / tot for k, v in cnt.items()}
H = -sum(p * math.log2(p) for p in pr.values())
OUT['syl'] = {'types': len(cnt), 'tokens': tot, 'entropy_bits': round(H, 3),
              'eff_types': round(2 ** H, 0)}
print('① 语料里有 %d 种带调音节、%d 个音节位' % (len(cnt), tot))
print('   音节分布的熵 %.3f bit → 等效 %.0f 种等概率音节'
      % (H, 2 ** H))
print('   （不是 %d 种——分布很偏，"的、一、不"这些占掉大半）' % len(cnt))

SYL_RATE = 4.0            # 连续说话时每秒约 4 个音节


def chance(word):
    py = [x[0] for x in pinyin(word, style=Style.TONE)]
    p = 1.0
    miss = []
    for s in py:
        q = pr.get(s)
        if q is None:
            q = 1.0 / tot
            miss.append(s)
        p *= q
    return py, p, miss


print('\n   几个真实唤醒词，按"音节独立"这个粗模型估的偶然撞上率：')
print('   唤醒词        音节数   序列概率      连续说话 1 小时的期望撞上次数')
OUT['words'] = []
for w in ('你好', '小爱', '小爱同学', '天猫精灵', '小度小度', '芝麻开门'):
    py, p, miss = chance(w)
    per_h = 3600 * SYL_RATE * p
    OUT['words'].append({'w': w, 'py': py, 'n': len(py), 'p': p,
                         'per_hour': per_h, 'per_day': per_h * 24})
    print('   %-8s %6d     %.3e    %10.2e  次/小时（%.2e 次/天）'
          % (w, len(py), p, per_h, per_h * 24))
w2 = next(r for r in OUT['words'] if r['w'] == '你好')
w4 = next(r for r in OUT['words'] if r['w'] == '小爱同学')
OUT['len_ratio'] = round(w2['per_hour'] / max(w4['per_hour'], 1e-30), 1)
print('   <strong>两个音节到四个音节，偶然撞上的机会差 %.0e 倍</strong>——'
      % OUT['len_ratio'])
print('   这就是几乎所有商用唤醒词都是三到四个音节的原因。')
print('   （这个模型假设音节独立，真实中文有很强的音节搭配约束，绝对值会差；')
print('    而且声学检测器是"近似匹配"不是"精确匹配"，实际误唤醒率要高得多。')
print('    可信的是<strong>随音节数指数下降</strong>这个形状。）')

# ══ ② 误唤醒率的单位 ═════════════════════════════════════════
HOP_MS = 30.0            # 每 30 ms 出一次判决
DEC_PER_DAY = 24 * 3600 * 1000 / HOP_MS
OUT['unit'] = {'hop_ms': HOP_MS, 'dec_per_day': int(DEC_PER_DAY)}
print('\n② 误唤醒率的单位：每 %.0f ms 出一次判决，一天 %s 次判决'
      % (HOP_MS, f'{int(DEC_PER_DAY):,}'))
print('   目标 FA/天   需要的单次判决虚警率')
OUT['fa_map'] = []
for fa_day in (10.0, 1.0, 0.5, 0.1):
    p = fa_day / DEC_PER_DAY
    OUT['fa_map'].append({'fa_day': fa_day, 'p_dec': p})
    print('   %8.1f      %.2e' % (fa_day, p))
print('   <strong>“误唤醒率 0.1%%”这种说法没有意义</strong>——')
print('   0.1%% 的单次判决虚警率等于每天 %s 次误唤醒。'
      % f'{int(0.001 * DEC_PER_DAY):,}')

# ══ ③ ROC：漏唤醒 vs 每天误唤醒 ══════════════════════════════
# 负样本用解析分布，不用抽样——要测每天 0.5 次，抽样得抽上亿个点。
from scipy.stats import norm
NEG_MIX = ((0.90, 0.0, 1.00),        # 普通背景
           (0.09, 2.6, 1.10),        # 一般语音
           (0.01, 4.2, 1.30))        # "很像唤醒词"的那一小撮
POS_MU, POS_SD = 13.5, 1.8
DEC_PER_H = 3600 * 1000 / HOP_MS


def p_fa(t):
    return sum(w * norm.sf(t, m, s_) for w, m, s_ in NEG_MIX)


def p_miss(t):
    return float(norm.cdf(t, POS_MU, POS_SD))


OUT['dist'] = {'neg_mix': NEG_MIX, 'pos_mu': POS_MU, 'pos_sd': POS_SD,
               'dec_per_h': DEC_PER_H}
ths = np.linspace(0, 12, 601)
fa_day = np.array([p_fa(t) * DEC_PER_H * 24 for t in ths])
miss = np.array([p_miss(t) for t in ths])
OUT['roc'] = {'fa_day': [round(float(x), 6) for x in fa_day[::6]],
              'miss': [round(float(x) * 100, 4) for x in miss[::6]],
              'thr': [round(float(x), 3) for x in ths[::6]]}
print('\n③ 工作点：漏唤醒率 vs 每天误唤醒次数')
print('   目标 FA/天    对应阈值   漏唤醒率')
OUT['op'] = []
for target in (10.0, 5.0, 1.0, 0.5, 0.2, 0.1):
    i2 = int(np.argmin(np.abs(fa_day - target)))
    OUT['op'].append({'fa_day': target, 'thr': round(float(ths[i2]), 2),
                      'miss': round(float(miss[i2]) * 100, 2)})
    print('   %8.1f     %7.2f    %6.2f%%' % (target, ths[i2], miss[i2] * 100))
o5 = OUT['op'][1]; o05 = OUT['op'][3]
print('   <strong>从每天 5 次压到每天 0.5 次，漏唤醒率从 %.2f%% 涨到 %.2f%%</strong>'
      % (o5['miss'], o05['miss']))
print('   这条曲线的斜率就是产品的取舍：用户讨厌误唤醒，但更讨厌叫不醒。')
print('   注意阈值只挪了 %.2f（不到一个 σ），FA/天 却降了十倍——'
      % (o05['thr'] - o5['thr']))
print('   <strong>尾部是指数衰减的，所以阈值这个旋钮极其敏感</strong>。')

# ══ ④ 要多少小时负样本才测得准 ═══════════════════════════════
def poisson_power(l1, l2, hours, reps=4000, seed=4):
    g2 = np.random.default_rng(seed)
    d = hours / 24.0
    hit = 0
    for _ in range(reps):
        a = g2.poisson(l1 * d); b = g2.poisson(l2 * d)
        se = math.sqrt(max(a + b, 1)) + 1e-9
        hit += abs(a - b) / se > 1.96
    return hit / reps


print('\n④ 要多少小时负样本')
OUT['hours'] = []
for l1, l2 in ((1.0, 0.5), (1.0, 0.7), (0.5, 0.25), (0.2, 0.1)):
    got = None
    for hrs in (24, 48, 120, 240, 480, 1200, 2400, 6000, 12000):
        if poisson_power(l1, l2, hrs) >= 0.8:
            got = hrs
            break
    OUT['hours'].append({'l1': l1, 'l2': l2, 'hours': got})
    print('   区分 %.2f 与 %.2f 次/天 → 需要 %s 小时负样本（≈ %s 天）'
          % (l1, l2, got if got else '>12000',
             ('%.0f' % (got / 24)) if got else '—'))
print('   <strong>这是唤醒最反直觉的一件事</strong>：'
      '把误唤醒从每天 1 次降到 0.5 次，')
print('   光是<em>证明</em>你做到了就要 %s 小时负样本。'
      % OUT['hours'][0]['hours'])

# ══ ⑤ 级联：功耗的最优点 ═════════════════════════════════════
P1, P2 = 0.35, 22.0
DUR2 = 0.6
T2 = OUT['op'][3]['thr']          # 二级工作在 0.5 次/天
M2 = OUT['op'][3]['miss'] / 100.0
print('\n⑤ 级联唤醒：一级阈值定在哪儿')
print('   一级常开 %.2f mW；二级 %.0f mW，每次跑 %.1f s；二级工作在 0.5 次/天'
      % (P1, P2, DUR2))
print('   一级阈值   一级触发     平均功耗    一级漏   总漏唤醒')
OUT['cascade'] = []
for t1 in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0):
    trig_h = p_fa(t1) * DEC_PER_H
    m1 = p_miss(t1)
    m_tot = 1 - (1 - m1) * (1 - M2)
    pwr = P1 + trig_h * DUR2 / 3600.0 * P2
    OUT['cascade'].append({'t1': t1, 'trig_h': round(float(trig_h), 1),
                           'mw': round(float(pwr), 3), 'm1': round(float(m1) * 100, 3),
                           'miss': round(float(m_tot) * 100, 2)})
    print('   %7.1f   %8.1f/时   %7.3f mW   %6.3f%%   %6.2f%%'
          % (t1, trig_h, pwr, m1 * 100, m_tot * 100))
# 膝点：在"总漏唤醒不超过二级自己 + 0.5 个百分点"的前提下功耗最低
ok = [r for r in OUT['cascade'] if r['miss'] <= OUT['op'][3]['miss'] + 0.5]
best = min(ok, key=lambda r: r['mw'])
OUT['cascade_best'] = best
print('   一级放太松 → 二级一直在跑，省不下电；放太紧 → 一级自己就漏了。')
print('   在"总漏唤醒不比二级自己差 0.5 个百分点"的约束下，最省电的是阈值 %.1f：'
      % best['t1'])
print('   <strong>%.3f mW，总漏唤醒 %.2f%%</strong>。' % (best['mw'], best['miss']))
OUT['casc_cfg'] = {'p1': P1, 'p2': P2, 'dur2': DUR2,
                   'duty': round(best['trig_h'] * DUR2 / 3600.0, 6),
                   'p2_share': round(best['trig_h'] * DUR2 / 3600.0 * P2, 4)}
OUT['nocascade_mw'] = P2
print('   不做级联（二级常开）是 %.0f mW —— 差 %.0f 倍。' % (P2, P2 / best['mw']))

# ══ ⑥ VAD 前置 ═══════════════════════════════════════════════
print('\n⑥ 前面再加一个 VAD：只有检测到人声才让一级跑')
OUT['vad'] = []
P_VAD = 0.04
for occ in (1.0, 0.30, 0.15, 0.05):
    pwr = P_VAD + occ * (best['mw'])
    OUT['vad'].append({'occ': occ, 'mw': round(float(pwr), 3),
                       'fa_day': round(0.5 * occ, 3)})
    print('   有人声时间占比 %4.0f%%   平均功耗 %6.3f mW   误唤醒 %.3f 次/天'
          % (occ * 100, pwr, 0.5 * occ))
print('   <strong>误唤醒率是按"暴露时间"算的</strong>：'
      'VAD 把暴露砍掉八成，误唤醒也跟着砍掉八成。')
print('   代价是 VAD 自己的漏检直接变成唤醒的漏检——它成了新的上限。')

# ══ ⑦ 端侧算力：一级能有多大 ════════════════════════════════
def dscnn_macs(t, f, c, blocks=4, k=3, nout=12):
    """DS-CNN：一个普通卷积 + blocks 个深度可分离块。返回每次推理的 MAC。"""
    m = t * f * c * k * k                       # 首层（输入 1 通道）
    for _ in range(blocks):
        m += t * f * c * k * k                  # depthwise
        m += t * f * c * c                      # pointwise
    m += c * nout
    return m


print('\n⑦ 一级模型能有多大（输入 49 帧 × 10 维 MFCC）')
print('   配置                         每次推理 MAC   10 次/秒   50 pJ/MAC  2 pJ/MAC')
OUT['edge'] = []
for tag, (t_, f_, c_, b_) in (
        ('S：首层 stride 2，16 通道，3 块', (25, 5, 16, 3)),
        ('M：首层 stride 2，32 通道，4 块', (25, 5, 32, 4)),
        ('L：不降采样，64 通道，4 块', (49, 10, 64, 4))):
    mac = dscnn_macs(t_, f_, c_, b_)
    mps = mac * 10
    w50 = mps * 50 / 1e9
    w2 = mps * 2 / 1e9
    OUT['edge'].append({'tag': tag, 'mac': int(mac), 'mmac_s': round(mps / 1e6, 2),
                        'mw50': round(w50, 3), 'mw2': round(w2, 3)})
    print('   %-30s %10s   %6.2f M   %7.3f mW %7.3f mW %s'
          % (tag, f'{mac:,}', mps / 1e6, w50, w2,
             '✓' if w50 < 1.0 else ('△' if w2 < 1.0 else '✗')))
print('   常开预算通常是 <strong>1 mW 量级</strong>。')
print('   所以：通用 MCU 上只能跑 S 档；要上 M/L 档，要么有 NPU，要么就得放到二级去。')

json.dump(OUT, open('demo_kws.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_kws.json')
