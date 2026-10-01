#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""36 节：置信度与校准——模型说"我有 95% 把握"的时候，对的比例是多少；失配时这个数怎么变；拒识买到什么。

   玩具声学世界（toylib）。两个模型：只见过干净语音的 / 带噪 + 混响 + 变速增强并做逐条 CMVN 的。
   条件：干净、白噪 10 dB、babble 10 dB、电话带宽、没见过的说话人（v=+0.30）。
   ① 准确率 vs 平均置信度 vs ECE
   ② 温度缩放：在干净验证集上拟合一个温度，搬到失配条件上还管不管用
   ③ 拒识：只收置信度最高的那一部分，准确率能到多少；以及用什么量当置信度（最大概率 / 间隔 / 熵）
   ④ 句子级：用句子的平均置信度去预测"这句在这批里错得最多（最差的三分之一）"，AUROC 多少
"""
import numpy as np, json, time
import enhlib as E
import toylib as T

OUT = {}
t0 = time.time()
SEEDS = (0, 1, 2)
H = 128
EPOCHS = 14
SPK = list(range(12))
TR = T.corpus([1000 + i for i in range(60)], [SPK[i % 12] for i in range(60)])
VA = T.corpus([5000 + i for i in range(20)], [SPK[i % 12] for i in range(20)])
TE = T.corpus([9000 + i for i in range(30)], [SPK[i % 12] for i in range(30)])
TE_SHIFT = T.corpus([9500 + i for i in range(30)], [155] * 30)       # v = −0.38，训练说话人只覆盖约 ±15%
CLEAN_XY = T.make_xy(TR)
FALL = np.concatenate([a for a, _, _ in CLEAN_XY])
MU, SD = FALL.mean(0), FALL.std(0) + 1e-3

CONDS = [
    ('clean', '干净', TE, None),
    ('white10', '白噪 10 dB', TE, lambda x, l, k: (T.add_noise(x, 'white', 10, 7000 + k), l)),
    ('babble10', 'babble 10 dB', TE, lambda x, l, k: (T.add_noise(x, 'babble', 10, 7200 + k), l)),
    ('tel', '电话带宽', TE, lambda x, l, k: (T.band_limit(x), l)),
    ('shift', '没见过的说话人（v=−0.38）', TE_SHIFT, None),
]


def train(kind, sd):
    rng = np.random.default_rng(sd)
    if kind == 'plain':
        xy = T.make_xy(TR)
        X, Y = T.assemble(xy, 'glob', MU, SD)
    else:
        xy = T.make_xy(TR)
        for c in range(3):
            def ch(x, l, k, rng=rng):
                x, l = T.speed(x, l, float(rng.choice([0.9, 1.0, 1.1])))
                if rng.random() < 0.5:
                    x = T.reverb(x, float(rng.uniform(0.2, 0.9)), int(rng.integers(1 << 30)))
                if rng.random() < 0.7:
                    x = T.add_noise(x, ['white', 'pink', 'car'][int(rng.integers(3))], float(rng.uniform(0, 20)),
                                    int(rng.integers(1 << 30)))
                return x, l
            xy += T.make_xy(TR, ch)
        X, Y = T.assemble(xy, 'utt', MU, SD, specaug=lambda F, r: T.spec_augment(F, r), rng=rng)
    return T.MLP([X.shape[1], H, H, T.NCLS], seed=sd).fit(X, Y, epochs=EPOCHS, seed=sd)


def fit_temperature(z, y):
    best, bt = 1e9, 1.0
    for t in np.linspace(0.5, 6.0, 56):
        zz = z / t
        zz = zz - zz.max(1, keepdims=True)
        lp = zz - np.log(np.exp(zz).sum(1, keepdims=True))
        nll = -lp[np.arange(len(y)), y].mean()
        if nll < best:
            best, bt = nll, t
    return float(bt)


def softmax(z, t=1.0):
    z = z / t
    z = z - z.max(1, keepdims=True)
    p = np.exp(z)
    return p / p.sum(1, keepdims=True)


def auroc(score, pos):
    """pos 为真的样本，score 应该更高"""
    o = np.argsort(score)
    r = np.empty(len(score))
    r[o] = np.arange(1, len(score) + 1)
    n1, n0 = pos.sum(), (~pos).sum()
    return float((r[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def risk_cov(conf, ok, cov):
    k = max(int(len(conf) * cov), 1)
    idx = np.argsort(-conf)[:k]
    return float(ok[idx].mean())


def aurc(conf, ok):
    o = np.argsort(-conf)
    c = np.cumsum(~ok[o]) / np.arange(1, len(o) + 1)
    return float(c.mean())


OUT['models'] = {}
for kind in ('plain', 'robust'):
    acc = {c[0]: [] for c in CONDS}
    conf = {c[0]: [] for c in CONDS}
    ec = {c[0]: [] for c in CONDS}
    ecT = {c[0]: [] for c in CONDS}
    ecM = {c[0]: [] for c in CONDS}
    Tcl = []
    at50 = {c[0]: [] for c in CONDS}
    at80 = {c[0]: [] for c in CONDS}
    ar = {c[0]: [] for c in CONDS}
    sc_auc = {c[0]: {'maxp': [], 'margin': [], 'entropy': []} for c in CONDS}
    utt_auc = {c[0]: [] for c in CONDS}
    reli = {c[0]: None for c in CONDS}
    for sd in SEEDS:
        m = train(kind, sd)
        norm = 'glob' if kind == 'plain' else 'utt'
        Xv, Yv = T.assemble(T.make_xy(VA), norm, MU, SD)
        t_clean = fit_temperature(m.logits(Xv), Yv)
        Tcl.append(t_clean)
        for ck, nm, corp, ch in CONDS:
            xy = T.make_xy(corp, ch)
            X, Y = T.assemble(xy, norm, MU, SD)
            z = m.logits(X)
            p = softmax(z)
            ok = p.argmax(1) == Y
            acc[ck].append(ok.mean())
            conf[ck].append(p.max(1).mean())
            ec[ck].append(T.ece(p, Y))
            ecT[ck].append(T.ece(softmax(z, t_clean), Y))
            tm = fit_temperature(z, Y)                     # 在失配条件自己的数据上拟合（偷看答案的上界）
            ecM[ck].append(T.ece(softmax(z, tm), Y))
            c1 = p.max(1)
            ps = np.sort(p, 1)
            marg = ps[:, -1] - ps[:, -2]
            ent = -(p * np.log(p + 1e-12)).sum(1)
            at50[ck].append(risk_cov(c1, ok, 0.5))
            at80[ck].append(risk_cov(c1, ok, 0.8))
            ar[ck].append(aurc(c1, ok))
            sc_auc[ck]['maxp'].append(auroc(c1, ok) if (~ok).any() else float('nan'))
            sc_auc[ck]['margin'].append(auroc(marg, ok) if (~ok).any() else float('nan'))
            sc_auc[ck]['entropy'].append(auroc(-ent, ok) if (~ok).any() else float('nan'))
            # 句子级
            off, ua, uc = 0, [], []
            for F, Yu, _ in xy:
                n = len(Yu)
                ua.append(ok[off:off + n].mean())
                uc.append(c1[off:off + n].mean())
                off += n
            ua, uc = np.array(ua), np.array(uc)
            bad = ua <= np.quantile(ua, 1 / 3)            # 这一批里错得最多的三分之一句子
            utt_auc[ck].append(auroc(-uc, bad) if bad.any() and (~bad).any() else float('nan'))
            if sd == SEEDS[0]:
                bins = np.linspace(0, 1, 11)
                rl = []
                for b in range(10):
                    mk = (c1 > bins[b]) & (c1 <= bins[b + 1])
                    if mk.sum() >= 20:
                        rl.append((round(float((bins[b] + bins[b + 1]) / 2), 2), round(float(ok[mk].mean()), 3),
                                   round(float(mk.mean()), 3)))
                reli[ck] = rl
    mean = lambda d, k: round(float(np.nanmean(d[k])), 4)
    OUT['models'][kind] = {
        'T_clean': round(float(np.mean(Tcl)), 2),
        'conds': {ck: {'acc': round(100 * mean(acc, ck), 1), 'conf': round(100 * mean(conf, ck), 1),
                       'ece': round(100 * mean(ec, ck), 1), 'ece_T': round(100 * mean(ecT, ck), 1),
                       'ece_Tm': round(100 * mean(ecM, ck), 1),
                       'at50': round(100 * mean(at50, ck), 1), 'at80': round(100 * mean(at80, ck), 1),
                       'aurc': round(100 * mean(ar, ck), 2),
                       'auc_maxp': round(float(np.nanmean(sc_auc[ck]['maxp'])), 3),
                       'auc_margin': round(float(np.nanmean(sc_auc[ck]['margin'])), 3),
                       'auc_entropy': round(float(np.nanmean(sc_auc[ck]['entropy'])), 3),
                       'utt_auc': round(float(np.nanmean(utt_auc[ck])), 3), 'reli': reli[ck]}
                  for ck, _, _, _ in CONDS}}
    print('\n[%s] 在干净验证集上拟合的温度 T = %.2f' % (kind, OUT['models'][kind]['T_clean']))
    for ck, nm, _, _ in CONDS:
        c = OUT['models'][kind]['conds'][ck]
        print('  %-22s 准确率 %5.1f  置信度 %5.1f  ECE %4.1f → 干净T %4.1f → 自拟合 %4.1f   50%%覆盖 %5.1f  AUROC 最大概率 %.3f 间隔 %.3f 熵 %.3f  句子级 %.3f'
              % (nm, c['acc'], c['conf'], c['ece'], c['ece_T'], c['ece_Tm'], c['at50'], c['auc_maxp'], c['auc_margin'], c['auc_entropy'], c['utt_auc']))

P, Rb = OUT['models']['plain']['conds'], OUT['models']['robust']['conds']
OUT['note'] = {
    'clean_acc': P['clean']['acc'], 'clean_conf': P['clean']['conf'], 'clean_ece': P['clean']['ece'],
    'w10_acc': P['white10']['acc'], 'w10_conf': P['white10']['conf'], 'w10_ece': P['white10']['ece'],
    'w10_eceT': P['white10']['ece_T'], 'w10_eceTm': P['white10']['ece_Tm'],
    'w10_at50': P['white10']['at50'], 'w10_auc': P['white10']['auc_maxp'],
    'shift_acc': P['shift']['acc'], 'shift_conf': P['shift']['conf'], 'shift_ece': P['shift']['ece'],
    'shift_auc': P['shift']['auc_maxp'],
    'tel_acc': P['tel']['acc'], 'tel_conf': P['tel']['conf'], 'tel_ece': P['tel']['ece'],
    'T_clean': OUT['models']['plain']['T_clean'],
    'rob_w10_acc': Rb['white10']['acc'], 'rob_w10_ece': Rb['white10']['ece'],
    'rob_tel_acc': Rb['tel']['acc'], 'rob_tel_conf': Rb['tel']['conf'], 'rob_tel_ece': Rb['tel']['ece'],
    'rob_tel_at50': Rb['tel']['at50'], 'rob_tel_auc': Rb['tel']['auc_maxp'],
    'clean_utt_auc': P['clean']['utt_auc'], 'w10_utt_auc': P['white10']['utt_auc'],
    'margin_vs_maxp': round(float(np.mean([P[k]['auc_margin'] - P[k]['auc_maxp'] for k in P])), 3),
    'shift_at50': P['shift']['at50'],
}
OUT['conds'] = [{'key': k, 'name': n} for k, n, _, _ in CONDS]
OUT['const'] = {'seeds': list(SEEDS), 'hidden': H, 'epochs': EPOCHS, 'ntr': 60, 'nva': 20, 'nte': 30}
OUT['runtime_s'] = round(time.time() - t0, 1)
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_conf.json', 'w'), ensure_ascii=False)
print('写出 demo_conf.json  %.1f s' % OUT['runtime_s'])
