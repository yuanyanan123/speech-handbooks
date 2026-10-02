#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""37 节：蒸馏与压缩——小模型在标注不够时能从大模型学到什么，以及权重量化到几位还不坏。

   玩具声学世界（toylib）。教师：2×512 的 MLP，用带噪、混响、变速增强的全部数据训练，并带逐条 CMVN。
   学生：2×(16 / 32 / 64)，只允许看到很少的干净标注。
   ① 学生训练的三种做法：只用硬标签 / 同样的数据加上教师的软标签 / 再加一大批"没有标注的"增强数据让教师打标
   ② 蒸馏温度与权重 α 的扫描
   ③ 权重量化（对称均匀，只量化权重）：8 / 6 / 4 / 3 位，按张量与按输出通道各一
"""
import numpy as np, json, time
import enhlib as E
import toylib as T

OUT = {}
t0 = time.time()
SEEDS = (0, 1, 2)
SPK = list(range(12))
EPOCHS = 14
TR = T.corpus([1000 + i for i in range(60)], [SPK[i % 12] for i in range(60)])
TE = T.corpus([9000 + i for i in range(24)], [SPK[i % 12] for i in range(24)])
CLEAN_XY = T.make_xy(TR)
FALL = np.concatenate([a for a, _, _ in CLEAN_XY])
MU, SD = FALL.mean(0), FALL.std(0) + 1e-3
NLAB = 12                                      # 学生只有 12 条（36 s）干净标注

CONDS = [('clean', '干净', None),
         ('white10', '白噪 10 dB', lambda x, l, k: (T.add_noise(x, 'white', 10, 7000 + k), l)),
         ('babble10', 'babble 10 dB', lambda x, l, k: (T.add_noise(x, 'babble', 10, 7200 + k), l)),
         ('tel', '电话带宽', lambda x, l, k: (T.band_limit(x), l))]
TEST = {k: T.assemble(T.make_xy(TE, ch), 'utt', MU, SD) for k, _, ch in CONDS}


def aug_pool(rng, copies=3):
    xy = []
    for c in range(copies):
        def ch(x, l, k, rng=rng):
            x, l = T.speed(x, l, float(rng.choice([0.9, 1.0, 1.1])))
            if rng.random() < 0.5:
                x = T.reverb(x, float(rng.uniform(0.2, 0.9)), int(rng.integers(1 << 30)))
            if rng.random() < 0.7:
                x = T.add_noise(x, ['white', 'pink', 'car'][int(rng.integers(3))], float(rng.uniform(0, 20)),
                                int(rng.integers(1 << 30)))
            return x, l
        xy += T.make_xy(TR, ch)
    return xy


def evaluate(m):
    return {k: round(100 * m.acc(*TEST[k]), 1) for k, _, _ in CONDS}


def macs(m):
    return int(sum(w.shape[0] * w.shape[1] for w in m.W))


rows = {}
teacher_acc = {k: [] for k, _, _ in CONDS}
for sd in SEEDS:
    rng = np.random.default_rng(sd)
    pool = aug_pool(rng)
    Xp, Yp = T.assemble(CLEAN_XY + pool, 'utt', MU, SD, specaug=lambda F, r: T.spec_augment(F, r), rng=rng)
    teacher = T.MLP([Xp.shape[1], 512, 512, T.NCLS], seed=sd).fit(Xp, Yp, epochs=EPOCHS, seed=sd)
    for k, v in evaluate(teacher).items():
        teacher_acc[k].append(v)
    # 学生的数据：NLAB 条干净标注；无标注池 = 增强后的全部（教师打标，学生只拿软标签）
    Xl, Yl = T.assemble(CLEAN_XY[:NLAB], 'utt', MU, SD)
    Xu, _ = T.assemble(pool, 'utt', MU, SD, specaug=lambda F, r: T.spec_augment(F, r), rng=rng)
    soft_l = teacher.proba(Xl, T=4.0)
    soft_u = teacher.proba(Xu, T=4.0)
    for H in (16, 32, 64):
        cfg = {
            'hard': ('只用硬标签（12 条）', lambda: T.MLP([Xl.shape[1], H, H, T.NCLS], seed=sd).fit(Xl, Yl, epochs=EPOCHS * 3, seed=sd)),
            'kd': ('+ 教师软标签（同样 12 条）', lambda: T.MLP([Xl.shape[1], H, H, T.NCLS], seed=sd).fit(
                Xl, Yl, epochs=EPOCHS * 3, seed=sd, soft=soft_l, T=4.0, alpha=0.7)),
            'kd_u': ('+ 教师给无标注增强数据打标', lambda: T.MLP([Xl.shape[1], H, H, T.NCLS], seed=sd).fit(
                np.concatenate([Xl, Xu]), np.concatenate([Yl, teacher.proba(Xu).argmax(1)]),
                epochs=EPOCHS, seed=sd,
                soft=np.concatenate([soft_l, soft_u]), T=4.0, alpha=1.0)),
        }
        for key, (nm, fn) in cfg.items():
            m = fn()
            r = rows.setdefault((H, key), {'H': H, 'key': key, 'name': nm, 'params': m.nparams(), 'macs': macs(m),
                                           'acc': {k: [] for k, _, _ in CONDS}})
            for k, v in evaluate(m).items():
                r['acc'][k].append(v)
OUT['teacher'] = {'acc': {k: round(float(np.mean(v)), 1) for k, v in teacher_acc.items()},
                  'params': T.MLP([200, 512, 512, 9]).nparams(), 'macs': 200 * 512 + 512 * 512 + 512 * 9}
OUT['students'] = []
print('教师', OUT['teacher'])
for (H, key), r in sorted(rows.items()):
    r['acc'] = {k: round(float(np.mean(v)), 1) for k, v in r['acc'].items()}
    OUT['students'].append(r)
    print('  H=%2d %-24s 参数 %6d  ' % (H, r['name'], r['params']) + ' '.join('%s %.1f' % (k, r['acc'][k]) for k, _, _ in CONDS))

# ══ ② 温度与 α（学生 H=32，kd_u 配方）══════════════════════════
print('\n② 温度与 α（学生 H=32，12 条标注 + 无标注增强池）')
OUT['sweep'] = []
rng = np.random.default_rng(0)
pool = aug_pool(rng)
Xp, Yp = T.assemble(CLEAN_XY + pool, 'utt', MU, SD, specaug=lambda F, r: T.spec_augment(F, r), rng=rng)
teacher0 = T.MLP([Xp.shape[1], 512, 512, T.NCLS], seed=0).fit(Xp, Yp, epochs=EPOCHS, seed=0)
Xl, Yl = T.assemble(CLEAN_XY[:NLAB], 'utt', MU, SD)
Xu, _ = T.assemble(pool, 'utt', MU, SD)
for Tm in (1.0, 2.0, 4.0, 8.0):
    for alpha in (0.0, 0.5, 1.0):
        s_ = teacher0.proba(np.concatenate([Xl, Xu]), T=Tm)
        hard = np.concatenate([Yl, teacher0.proba(Xu).argmax(1)])
        m = T.MLP([Xl.shape[1], 32, 32, T.NCLS], seed=0).fit(
            np.concatenate([Xl, Xu]), hard, epochs=EPOCHS, seed=0, soft=s_, T=Tm, alpha=alpha)
        e = evaluate(m)
        OUT['sweep'].append({'T': Tm, 'alpha': alpha, 'acc': e})
        print('  T=%.0f α=%.1f  ' % (Tm, alpha) + ' '.join('%s %.1f' % (k, e[k]) for k in e))

# ══ ③ 量化 ═══════════════════════════════════════════════════
print('\n③ 权重量化（教师 2×512 与学生 2×64）')
OUT['quant'] = []
stu = T.MLP([200, 64, 64, T.NCLS], seed=0).fit(
    np.concatenate([Xl, Xu]), np.concatenate([Yl, teacher0.proba(Xu).argmax(1)]), epochs=EPOCHS, seed=0,
    soft=teacher0.proba(np.concatenate([Xl, Xu]), T=4.0), T=4.0, alpha=1.0)
for nm, m in (('教师 2×512', teacher0), ('学生 2×64', stu)):
    base = evaluate(m)
    OUT['quant'].append({'model': nm, 'bits': 32, 'per_channel': None, 'acc': base,
                         'kb': round(m.nparams() * 4 / 1024, 1)})
    print('  %s fp32  %s' % (nm, base))
    for bits in (8, 6, 4, 3):
        for pc in (False, True):
            q = T.quantize(m, bits, per_channel=pc)
            e = evaluate(q)
            OUT['quant'].append({'model': nm, 'bits': bits, 'per_channel': pc, 'acc': e,
                                 'kb': round(m.nparams() * bits / 8 / 1024, 1)})
            print('  %s int%d %-10s %s' % (nm, bits, '按通道' if pc else '按张量', e))

S = {(r['H'], r['key']): r for r in OUT['students']}
Q = {(q['model'], q['bits'], q['per_channel']): q for q in OUT['quant']}
OUT['note'] = {
    'teacher_clean': OUT['teacher']['acc']['clean'], 'teacher_babble': OUT['teacher']['acc']['babble10'],
    'teacher_params': OUT['teacher']['params'], 'student32_params': S[(32, 'hard')]['params'],
    'ratio_params': round(OUT['teacher']['params'] / S[(32, 'hard')]['params'], 1),
    'hard32_clean': S[(32, 'hard')]['acc']['clean'], 'kd32_clean': S[(32, 'kd')]['acc']['clean'],
    'kdu32_clean': S[(32, 'kd_u')]['acc']['clean'],
    'hard32_babble': S[(32, 'hard')]['acc']['babble10'], 'kd32_babble': S[(32, 'kd')]['acc']['babble10'],
    'kdu32_babble': S[(32, 'kd_u')]['acc']['babble10'],
    'hard32_white': S[(32, 'hard')]['acc']['white10'], 'kdu32_white': S[(32, 'kd_u')]['acc']['white10'],
    'hard16_clean': S[(16, 'hard')]['acc']['clean'], 'kdu16_clean': S[(16, 'kd_u')]['acc']['clean'],
    'kdu16_babble': S[(16, 'kd_u')]['acc']['babble10'], 'kdu64_babble': S[(64, 'kd_u')]['acc']['babble10'],
    'q8_pt': Q[('教师 2×512', 8, False)]['acc']['clean'], 'q4_pt': Q[('教师 2×512', 4, False)]['acc']['clean'],
    'q4_pc': Q[('教师 2×512', 4, True)]['acc']['clean'], 'q3_pc': Q[('教师 2×512', 3, True)]['acc']['clean'],
    'q3_pt': Q[('教师 2×512', 3, False)]['acc']['clean'],
    'sq4_pt': Q[('学生 2×64', 4, False)]['acc']['clean'], 'sq4_pc': Q[('学生 2×64', 4, True)]['acc']['clean'],
    'sq3_pc': Q[('学生 2×64', 3, True)]['acc']['clean'], 'sq3_pt': Q[('学生 2×64', 3, False)]['acc']['clean'],
    'sq8_pc': Q[('学生 2×64', 8, True)]['acc']['clean'], 'student_clean': Q[('学生 2×64', 32, None)]['acc']['clean'],
    'tq_kb': Q[('教师 2×512', 32, None)]['kb'], 'tq4_kb': Q[('教师 2×512', 4, True)]['kb'],
    'sq_kb': Q[('学生 2×64', 32, None)]['kb'],
}
OUT['const'] = {'seeds': list(SEEDS), 'nlab': NLAB, 'lab_s': NLAB * 3, 'epochs': EPOCHS, 'pool_utts': 180,
                'T': 4.0, 'alpha_kd': 0.7}
OUT['runtime_s'] = round(time.time() - t0, 1)
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_kd.json', 'w'), ensure_ascii=False)
print('写出 demo_kd.json  %.1f s' % OUT['runtime_s'])
