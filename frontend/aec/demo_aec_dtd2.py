#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""不靠"检测器"的双讲对策，以及对 demo_aec_dtd.py 那个结论的复核。

   demo_aec_dtd.py 里最优阈值落在"误检 80%"——这个数字太高了，不该直接当工程建议。
   这里加一条对照：收敛期一过就再也不学（frozen）。如果它和"最优的在线 DTD"一样好，
   说明那个最优点其实只是"几乎不再学习"，而不是"检测得很好"。

   ① 静态路径、近端电平 = 回声：七种做法的单讲段 ERLE、双讲段近端保真、失调
   ② 路径在第 12 s 整条换掉：谁还能重新收敛
   ③ 近端电平扫描：−10 / 0 / +10 dB，谁对近端电平敏感
"""
import numpy as np, json, time
import aeclib as A
import aecadv as V

OUT = {}
t0 = time.time()
SEEDS = (10, 11, 12)          # 与调参用的种子（0、1）错开
KAP, THETA = 2.0, 0.8          # 在线 DTD 的阈值：取 demo_aec_dtd 扫描里 ERLE 最好的那一点附近
FD = dict(a=0.9995, lam=0.97)  # FDKF 的两个常数，在种子 0、1 上做过一次 3×3 网格
TP = dict(mu_b=0.2, thr=0.3)

METHODS = [
    ('none', '从不冻结', lambda s: V.run_pb(s['x'], s['y'], s['h'], mode='none')),
    ('frozen', '收敛期之后不再学', lambda s: V.run_pb(s['x'], s['y'], s['h'], mode='frozen')),
    ('energy', '能量比 DTD（κ=%g）' % KAP, lambda s: V.run_pb(s['x'], s['y'], s['h'], mode='energy', kappa=KAP)),
    ('coh', '相干性 DTD（θ=%g）' % THETA, lambda s: V.run_pb(s['x'], s['y'], s['h'], mode='coh', theta=THETA)),
    ('twopath', '双路径', lambda s: V.run_twopath(s['x'], s['y'], s['h'], **TP)),
    ('fdkf', '频域卡尔曼', lambda s: V.run_fdkf(s['x'], s['y'], s['h'], **FD)),
    ('oracle', '全知 DTD（上界）', lambda s: V.run_pb(s['x'], s['y'], s['h'], mode='oracle', oracle=s['dt'])),
]


def score(sc, r):
    f = sc['score_from']
    e = r['e']
    o = {'erle': V.far_erle(sc['d'], e, sc['dt'], f),
         'near': V.near_snr(sc['near'], e, sc['dt'], f),
         'mis': A.misalign(r['w'], sc['h'])}
    if 'froz' in r:
        o['miss'], o['fa'] = [100 * v for v in V.rates(r['froz'], sc['dt'], f)]
    return o


def table(**scene_kw):
    rows = []
    for key, name, fn in METHODS:
        acc = []
        for sd in SEEDS:
            sc = V.scene(sd, **scene_kw)
            acc.append(score(sc, fn(sc)))
        row = {'key': key, 'name': name}
        for k in ('erle', 'near', 'mis'):
            row[k] = round(float(np.mean([a[k] for a in acc])), 2)
        if 'miss' in acc[0]:
            row['miss'] = round(float(np.mean([a['miss'] for a in acc])), 1)
            row['fa'] = round(float(np.mean([a['fa'] for a in acc])), 1)
        rows.append(row)
    return rows


# ══ ① 静态路径 ═══════════════════════════════════════════════
print('① 静态路径，近端电平 = 回声')
OUT['static'] = table(ner_db=0.0)
for r in OUT['static']:
    print('  %-20s 单讲段 ERLE %6.2f   近端保真 %6.2f   失调 %7.2f   %s'
          % (r['name'], r['erle'], r['near'], r['mis'],
             ('漏检 %.1f%% 误检 %.1f%%' % (r['miss'], r['fa'])) if 'miss' in r else ''))

# ══ ② 路径整条换掉 ═══════════════════════════════════════════
print('\n② 第 12 s 路径整条换掉（统计从换路径后 4 s 开始）')
OUT['change'] = table(ner_db=0.0, change_s=12.0)
for r in OUT['change']:
    print('  %-20s 单讲段 ERLE %6.2f   近端保真 %6.2f   失调 %7.2f'
          % (r['name'], r['erle'], r['near'], r['mis']))

# ══ ③ 近端电平 ═══════════════════════════════════════════════
print('\n③ 近端电平扫描（相对回声）')
OUT['ner'] = []
for ner in (-10.0, 0.0, 10.0):
    rows = table(ner_db=ner)
    OUT['ner'].append({'ner': ner, 'rows': rows})
    print('  近端 %+.0f dB：' % ner + '   '.join('%s %.1f' % (r['key'], r['erle']) for r in rows))

# ══ 结论量 ═══════════════════════════════════════════════════
S = {r['key']: r for r in OUT['static']}
C = {r['key']: r for r in OUT['change']}
OUT['note'] = {
    'frozen_vs_energy': round(S['frozen']['erle'] - S['energy']['erle'], 2),
    'frozen_static': S['frozen']['erle'], 'energy_static': S['energy']['erle'],
    'frozen_change': C['frozen']['erle'], 'energy_change': C['energy']['erle'],
    'none_change': C['none']['erle'],
    'fdkf_static': S['fdkf']['erle'], 'fdkf_change': C['fdkf']['erle'],
    'fdkf_vs_none': round(S['fdkf']['erle'] - S['none']['erle'], 2),
    'fdkf_vs_energy': round(S['fdkf']['erle'] - S['energy']['erle'], 2),
    'oracle_static': S['oracle']['erle'], 'oracle_change': C['oracle']['erle'],
    'fdkf_gap_to_oracle': round(S['oracle']['erle'] - S['fdkf']['erle'], 2),
    'twopath_static': S['twopath']['erle'], 'twopath_change': C['twopath']['erle'],
}
OUT['const'] = {'seeds': list(SEEDS), 'kappa': KAP, 'theta': THETA, 'fdkf': FD, 'twopath': TP,
                'dur': 24.0, 'change_s': 12.0, 'B': V.B, 'nparts': V.NP, 'mu': V.MU,
                't60': 0.25, 'near_snr': 40.0}
print('\n结论量：', json.dumps(OUT['note'], ensure_ascii=False))
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_aec_dtd2.json', 'w'), ensure_ascii=False)
print('写出 demo_aec_dtd2.json  %.1f s' % OUT['runtime_s'])
