#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""35 节：说话人自适应——失配有多大、要多少标注数据、改哪一层、会不会把原来的忘掉。

   玩具声学世界（toylib）里"换说话人"是真的共振峰整体缩放（声道长度因子 exp(v)，
   v>0 声道短、共振峰整体往高频走，像小孩；v<0 反过来）。
   源模型只见过 |v|<0.10 的说话人；目标说话人 |v|≈0.3–0.4。
   ① 源模型的准确率随 |v| 怎么掉
   ② 给目标说话人 3–90 秒的有标注数据：全部微调 / 只调最后一层 / 只调第一层 / 逐条 CMVN
   ③ 完全没有标注：用源模型的高置信预测当伪标签，自训练一轮
   ④ 微调之后，原说话人的准确率还剩多少（遗忘）
"""
import numpy as np, json, time
import enhlib as E
import toylib as T

OUT = {}
t0 = time.time()
SEEDS = (0, 1, 2)
H = 128
EPOCHS = 14

vtl = {i: float(np.log(E.spk_params(i)['vtl'])) for i in range(200)}
SRC = [i for i in range(200) if abs(vtl[i]) < 0.10][:10]
TGT = [155, 25, 176, 32]                     # v = −0.38, −0.36, +0.32, +0.30
SRC_TEST = SRC[:6]
BINS = [-0.38, -0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.30]
CURVE_SPK = []
for b in BINS:
    cand = [i for i in range(200) if i not in SRC and abs(vtl[i] - b) < 0.03] if abs(b) > 0.1 else \
           [i for i in range(200) if abs(vtl[i] - b) < 0.03]
    CURVE_SPK.append(cand[0])

TR = T.corpus([2000 + i for i in range(40)], [SRC[i % len(SRC)] for i in range(40)])
XY_TR = T.make_xy(TR)
F_ALL = np.concatenate([a for a, _, _ in XY_TR])
MU, SD = F_ALL.mean(0), F_ALL.std(0) + 1e-3


def spk_corpus(spk, n, sd0):
    return T.corpus([sd0 + i for i in range(n)], [spk] * n)


def xy_of(spk, n, sd0):
    return T.make_xy(spk_corpus(spk, n, sd0))


def train_base(norm, seed):
    X, Y = T.assemble(XY_TR, norm, MU, SD)
    return T.MLP([X.shape[1], H, H, T.NCLS], seed=seed).fit(X, Y, epochs=EPOCHS, seed=seed)


# ══ ① 失配曲线 ═══════════════════════════════════════════════
print('① 源模型的准确率 vs 目标说话人的声道长度因子 v')
OUT['curve'] = []
for sp in CURVE_SPK:
    a = []
    for sd in SEEDS:
        m = train_base('glob', sd)
        Xt, Yt = T.assemble(xy_of(sp, 10, 80000 + sp), 'glob', MU, SD)
        a.append(m.acc(Xt, Yt))
    OUT['curve'].append({'spk': sp, 'v': round(vtl[sp], 3), 'acc': round(100 * float(np.mean(a)), 1)})
    print('  v=%+.2f  %.1f%%' % (vtl[sp], OUT['curve'][-1]['acc']))

# ══ ② ③ ④ 自适应 ═════════════════════════════════════════════
NUTT = (1, 3, 6, 15, 30)                     # 每条 3 s
METHODS = ['none', 'cmvn', 'all', 'mix', 'last', 'first', 'pseudo']
NAMES = {'none': '不自适应', 'cmvn': '逐条 CMVN（无标注，重训基座）', 'all': '全部微调', 'mix': '全部微调 + 混入等量源数据', 'last': '只调最后一层',
         'first': '只调第一层（输入变换）', 'pseudo': '无标注：伪标签自训练'}
res = {m_: {n: [] for n in NUTT} for m_ in METHODS}
forget = {m_: {n: [] for n in NUTT} for m_ in ('none', 'all', 'mix', 'last', 'first')}
src_xy = [x for sp in SRC_TEST for x in xy_of(sp, 4, 70000 + sp)]
Xs, Ys = T.assemble(src_xy, 'glob', MU, SD)
F_SRC_X, F_SRC_Y = T.assemble(XY_TR, 'glob', MU, SD)
for sd in SEEDS:
    base = train_base('glob', sd)
    base_cmvn = train_base('utt', sd)
    for sp in TGT:
        te = xy_of(sp, 15, 60000 + sp)
        Xt, Yt = T.assemble(te, 'glob', MU, SD)
        Xtc, Ytc = T.assemble(te, 'utt', MU, SD)
        pool = xy_of(sp, 30, 50000 + sp)
        for n in NUTT:
            ad = pool[:n]
            Xa, Ya = T.assemble(ad, 'glob', MU, SD)
            Xac, Yac = T.assemble(ad, 'utt', MU, SD)
            res['none'][n].append(base.acc(Xt, Yt))
            forget['none'][n].append(base.acc(Xs, Ys))
            res['cmvn'][n].append(base_cmvn.acc(Xtc, Ytc))            # CMVN 基座不需要标注，数据量无关
            for key, frz in (('all', ()), ('last', (0, 1)), ('first', (1, 2))):
                m_ = base.copy().fit(Xa, Ya, epochs=12, lr=1e-3, seed=sd, freeze=frz)
                res[key][n].append(m_.acc(Xt, Yt))
                if key in forget:
                    forget[key][n].append(m_.acc(Xs, Ys))
            # 混入等量源数据（复习），看遗忘能不能压住
            rs = np.random.default_rng(sd * 7 + n)
            ii = rs.choice(len(F_SRC_X), size=len(Xa), replace=False)
            m_ = base.copy().fit(np.concatenate([Xa, F_SRC_X[ii]]), np.concatenate([Ya, F_SRC_Y[ii]]),
                                 epochs=12, lr=1e-3, seed=sd)
            res['mix'][n].append(m_.acc(Xt, Yt))
            forget['mix'][n].append(m_.acc(Xs, Ys))
            # 伪标签：只用源模型自己的高置信预测，没有任何人工标注
            P = base.proba(Xa)
            keep = P.max(1) > 0.9
            if keep.sum() > 20:
                m_ = base.copy().fit(Xa[keep], P.argmax(1)[keep], epochs=12, lr=1e-3, seed=sd)
                res['pseudo'][n].append(m_.acc(Xt, Yt))
            else:
                res['pseudo'][n].append(base.acc(Xt, Yt))
OUT['rows'] = []
print('\n目标说话人 %s（v = %s）' % (TGT, [round(vtl[s], 2) for s in TGT]))
print('%-26s' % '' + ' '.join('%6ds' % (3 * n) for n in NUTT))
for m_ in METHODS:
    r = {'key': m_, 'name': NAMES[m_], 'acc': {str(3 * n): round(100 * float(np.mean(res[m_][n])), 1) for n in NUTT}}
    OUT['rows'].append(r)
    print('%-26s' % NAMES[m_] + ' '.join('%7.1f' % r['acc'][str(3 * n)] for n in NUTT))
OUT['forget'] = {k: {str(3 * n): round(100 * float(np.mean(v[n])), 1) for n in NUTT} for k, v in forget.items()}
print('\n微调之后原说话人（源域）的准确率')
for k, v in OUT['forget'].items():
    print('%-8s' % k + ' '.join('%7.1f' % v[str(3 * n)] for n in NUTT))

R = {r['key']: r['acc'] for r in OUT['rows']}
c = {x['spk']: x for x in OUT['curve']}
OUT['note'] = {
    'src_acc': OUT['curve'][4]['acc'], 'far_acc': min(x['acc'] for x in OUT['curve']),
    'none_tgt': R['none']['3'], 'cmvn_tgt': R['cmvn']['3'],
    'all_3': R['all']['3'], 'all_90': R['all']['90'], 'last_3': R['last']['3'], 'last_90': R['last']['90'],
    'first_3': R['first']['3'], 'first_9': R['first']['9'], 'first_90': R['first']['90'],
    'all_9': R['all']['9'], 'last_9': R['last']['9'],
    'pseudo_9': R['pseudo']['9'], 'pseudo_90': R['pseudo']['90'],
    'mix_3': R['mix']['3'], 'mix_90': R['mix']['90'], 'forget_mix_3': OUT['forget']['mix']['3'],
    'forget_mix_90': OUT['forget']['mix']['90'],
    'forget_all_3': OUT['forget']['all']['3'], 'forget_all_90': OUT['forget']['all']['90'],
    'forget_last_90': OUT['forget']['last']['90'], 'forget_none': OUT['forget']['none']['3'],
    'forget_first_90': OUT['forget']['first']['90'],
}
OUT['const'] = {'src': SRC, 'tgt': TGT, 'tgt_v': [round(vtl[s], 2) for s in TGT], 'seeds': list(SEEDS),
                'nutt': list(NUTT), 'sec_per_utt': 3, 'hidden': H, 'src_utts': 40, 'test_utts': 15,
                'adapt_epochs': 12, 'adapt_lr': 1e-3, 'pseudo_thr': 0.9}
OUT['runtime_s'] = round(time.time() - t0, 1)
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_adapt.json', 'w'), ensure_ascii=False)
print('写出 demo_adapt.json  %.1f s' % OUT['runtime_s'])
