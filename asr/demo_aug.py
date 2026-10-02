#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""34 节：数据增强到底在买什么——噪声、混响、变速、SpecAugment、逐条归一化各自覆盖哪一块。

   玩具声学世界（toylib）：9 类帧级音素分类器。训练集的每种做法都是"同样的 60 条底料 × 4 份"，
   只在每一份怎么处理上不同。测试条件里故意放了训练里从没出现过的几种：
   · 没见过的噪声类型（babble：多人叠加，谱像语音）
   · 没见过的信道（电话带宽 300–3400 Hz）
   · 超出训练范围的混响与语速
"""
import numpy as np, json, time
import toylib as T

OUT = {}
t0 = time.time()
SEEDS = (0, 1, 2)
NSPK = 12
NTR, NTE = 60, 24
COPIES = 4
EPOCHS = 14
H = 128


def corpus(sd0, n, spks):
    return T.corpus([sd0 + i for i in range(n)], [spks[i % len(spks)] for i in range(n)])


SPK = list(range(NSPK))
TR = corpus(1000, NTR, SPK)
TE = corpus(9000, NTE, SPK)


# ══ 训练集的各种做法 ══════════════════════════════════════════
def chan_for(name, rng):
    def noise(x, l, k):
        return T.add_noise(x, ['white', 'pink', 'car'][int(rng.integers(3))], float(rng.uniform(0, 20)), int(rng.integers(1 << 30))), l

    def rev(x, l, k):
        return T.reverb(x, float(rng.uniform(0.2, 0.9)), int(rng.integers(1 << 30))), l

    def spd(x, l, k):
        return T.speed(x, l, float(rng.choice([0.9, 1.0, 1.1])))

    def combo(x, l, k):
        x, l = spd(x, l, k)
        if rng.random() < 0.5:
            x, l = rev(x, l, k)
        if rng.random() < 0.7:
            x, l = noise(x, l, k)
        return x, l
    return {'noise': noise, 'reverb': rev, 'speed': spd, 'all': combo}.get(name)


VARIANTS = [
    ('clean', '只用干净的', dict(chan=None, sa=False, norm='glob')),
    ('cmvn', '干净 + 逐条 CMVN', dict(chan=None, sa=False, norm='utt')),
    ('noise', '+ 加噪', dict(chan='noise', sa=False, norm='glob')),
    ('reverb', '+ 混响', dict(chan='reverb', sa=False, norm='glob')),
    ('speed', '+ 变速', dict(chan='speed', sa=False, norm='glob')),
    ('specaug', '+ SpecAugment', dict(chan=None, sa=True, norm='glob')),
    ('all', '全部叠加', dict(chan='all', sa=True, norm='glob')),
    ('allcmvn', '全部叠加 + 逐条 CMVN', dict(chan='all', sa=True, norm='utt')),
]

CONDS = [
    ('clean', '干净', None),
    ('white10', '白噪 10 dB（见过类型）', lambda x, l, k: (T.add_noise(x, 'white', 10, 7000 + k), l)),
    ('white0', '白噪 0 dB', lambda x, l, k: (T.add_noise(x, 'white', 0, 7100 + k), l)),
    ('babble10', 'babble 10 dB（没见过）', lambda x, l, k: (T.add_noise(x, 'babble', 10, 7200 + k), l)),
    ('babble0', 'babble 0 dB（没见过）', lambda x, l, k: (T.add_noise(x, 'babble', 0, 7300 + k), l)),
    ('rev05', '混响 T60=0.5 s', lambda x, l, k: (T.reverb(x, 0.5, 7400 + k), l)),
    ('rev12', '混响 T60=1.2 s（超范围）', lambda x, l, k: (T.reverb(x, 1.2, 7500 + k), l)),
    ('spd09', '语速 ×0.9', lambda x, l, k: T.speed(x, l, 0.9)),
    ('spd125', '语速 ×1.25（超范围）', lambda x, l, k: T.speed(x, l, 1.25)),
    ('tel', '电话带宽（没见过）', lambda x, l, k: (T.band_limit(x), l)),
]
COND_FEATS = {}
for key, nm, ch in CONDS:
    COND_FEATS[key] = T.make_xy(TE, ch)

# 全局归一化统计量：来自干净的训练特征（上线时没人会拿噪声去算它）
CLEAN_XY = T.make_xy(TR)
FALL = np.concatenate([a for a, _, _ in CLEAN_XY])
MU, SD = FALL.mean(0), FALL.std(0) + 1e-3


def build_train(spec, seed):
    rng = np.random.default_rng(seed)
    xy = []
    for c in range(COPIES):
        ch = chan_for(spec['chan'], rng) if spec['chan'] else None
        # 第 0 份永远是干净的原样（真实流程里干净数据不会被丢掉）
        xy += T.make_xy(TR, None if c == 0 else ch)
    sa = (lambda F, r: T.spec_augment(F, r)) if spec['sa'] else None
    return T.assemble(xy, spec['norm'], MU, SD, specaug=sa, rng=rng)


OUT['rows'] = []
print('训练集的各种做法 × 测试条件（帧准确率 %%，%d 个种子的均值）' % len(SEEDS))
for key, nm, spec in VARIANTS:
    accs = {c[0]: [] for c in CONDS}
    for sd in SEEDS:
        X, Y = build_train(spec, sd)
        m = T.MLP([X.shape[1], H, H, T.NCLS], seed=sd).fit(X, Y, epochs=EPOCHS, seed=sd)
        for ck, _, _ in CONDS:
            Xt, Yt = T.assemble(COND_FEATS[ck], spec['norm'], MU, SD)
            accs[ck].append(m.acc(Xt, Yt))
    row = {'key': key, 'name': nm, 'acc': {k: round(100 * float(np.mean(v)), 1) for k, v in accs.items()}}
    OUT['rows'].append(row)
    print('  %-14s ' % nm + ' '.join('%5.1f' % row['acc'][c[0]] for c in CONDS))
print('  ' + ' ' * 14 + ' ' + ' '.join('%5s' % c[0][:5] for c in CONDS))

R = {r['key']: r for r in OUT['rows']}
SEEN = ('white10', 'white0', 'rev05', 'spd09')
UNSEEN = ('babble10', 'babble0', 'rev12', 'spd125', 'tel')
for r in OUT['rows']:
    r['seen'] = round(float(np.mean([r['acc'][k] for k in SEEN])), 1)
    r['unseen'] = round(float(np.mean([r['acc'][k] for k in UNSEEN])), 1)
    r['all'] = round(float(np.mean([r['acc'][c[0]] for c in CONDS[1:]])), 1)
OUT['note'] = {
    'clean_clean': R['clean']['acc']['clean'], 'all_clean': R['all']['acc']['clean'],
    'clean_white10': R['clean']['acc']['white10'], 'noise_white10': R['noise']['acc']['white10'],
    'noise_babble10': R['noise']['acc']['babble10'], 'clean_babble10': R['clean']['acc']['babble10'],
    'noise_rev05': R['noise']['acc']['rev05'], 'rev_rev05': R['reverb']['acc']['rev05'],
    'noise_tel': R['noise']['acc']['tel'], 'all_tel': R['all']['acc']['tel'],
    'cmvn_tel': R['cmvn']['acc']['tel'], 'cmvn_white10': R['cmvn']['acc']['white10'],
    'cmvn_rev05': R['cmvn']['acc']['rev05'],
    'speed_spd125': R['speed']['acc']['spd125'], 'clean_spd125': R['clean']['acc']['spd125'],
    'specaug_babble10': R['specaug']['acc']['babble10'], 'specaug_clean': R['specaug']['acc']['clean'],
    'all_unseen': R['all']['unseen'], 'clean_unseen': R['clean']['unseen'],
    'allcmvn_unseen': R['allcmvn']['unseen'], 'allcmvn_clean': R['allcmvn']['acc']['clean'],
    'allcmvn_tel': R['allcmvn']['acc']['tel'], 'allcmvn_babble0': R['allcmvn']['acc']['babble0'],
    'cmvn_unseen': R['cmvn']['unseen'], 'cmvn_babble10': R['cmvn']['acc']['babble10'],
    'all_babble0': R['all']['acc']['babble0'], 'all_white0': R['all']['acc']['white0'],
    'rev_rev12': R['reverb']['acc']['rev12'], 'all_rev12': R['all']['acc']['rev12'],
}
OUT['conds'] = [{'key': k, 'name': n} for k, n, _ in CONDS]
OUT['const'] = {'ntr': NTR, 'nte': NTE, 'nspk': NSPK, 'copies': COPIES, 'epochs': EPOCHS, 'hidden': H,
                'seeds': list(SEEDS), 'seen': list(SEEN), 'unseen': list(UNSEEN), 'dur_s': 3.0,
                'train_min': round(NTR * 3.0 * COPIES / 60, 1), 'nparams': T.MLP([200, H, H, 9]).nparams()}
OUT['runtime_s'] = round(time.time() - t0, 1)
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_aug.json', 'w'), ensure_ascii=False)
print('写出 demo_aug.json  %.1f s' % OUT['runtime_s'])
