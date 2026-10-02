#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""30 节算例：跨语种克隆——说话人嵌入里混着语言，怎么量，怎么去。

   在 20 节同一套"说话人 × 房间 × 内容"的梅尔谱上再加一个<strong>语言</strong>因子：
     · 音素使用频率不同（语言 Z 多用前四个音素，语言 E 多用后四个）
     · （口音，即系统性的实现偏移，这里不建模）
   24 个说话人都说两种语言（双语者），各 6 条 × 10 s。
   说话人嵌入仍是长时平均谱（和 x-vector 的一阶统计量同类）。
   ① 同语种 vs 跨语种：同一个人换语言，相似度掉多少，和"换人"比
   ② 评测协议：跨语种克隆的上限被评测低估多少
   ③ 两种嵌入：原始 / 音素均衡（按音素分别求均值再平均，需要音素对齐）
"""
import json
import numpy as np

rng = np.random.default_rng(11)
OUT = {}

NMEL, FPS = 80, 86.13
MHZ = 2595 * np.log10(1 + (np.arange(NMEL) / NMEL * 8000) / 700)
NSPK, NUTT = 24, 6
FRAMES = 860
VTL = rng.uniform(0.86, 1.16, NSPK)
F0C = rng.uniform(95, 205, NSPK)
TILT = rng.uniform(-0.45, 0.45, NSPK)
PHSET = np.array([[730, 1090, 2440], [270, 2290, 3010], [300, 870, 2240],
                  [530, 1840, 2480], [660, 1720, 2410], [490, 1350, 1690],
                  [400, 1900, 2600], [600, 1000, 2500]], float)
PRIOR = {0: np.array([.22, .20, .18, .16, .06, .06, .06, .06]),     # 语言 Z
         1: np.array([.05, .06, .07, .08, .20, .20, .17, .17])}     # 语言 E
ACCENT = 1.0     # 口音（系统性的实现偏移）这里不建模：只有音素使用频率这一个语言差异。设成 1.03 会让数字略变，叙事不变
LANG = {0: 'Z', 1: 'E'}


def make_mel(spk, utt, lang, frames=FRAMES, return_lab=False):
    r = np.random.default_rng(10000 + utt * 97 + 7 * lang)
    n = frames // 9 + 1
    seq = r.choice(len(PHSET), size=n, p=PRIOR[lang])
    dur = r.integers(6, 13, n)
    tgt = np.repeat(PHSET[seq], dur, axis=0)[:frames]
    lab = np.repeat(seq, dur)[:frames]
    if len(tgt) < frames:
        tgt = np.vstack([tgt, np.repeat(tgt[-1:], frames - len(tgt), axis=0)])
        lab = np.concatenate([lab, np.repeat(lab[-1:], frames - len(lab))])
    k = np.exp(-0.5 * (np.arange(-6, 7) / 2.4) ** 2)
    k /= k.sum()
    tgt = np.stack([np.convolve(tgt[:, i], k, 'same') for i in range(3)], 1)
    tgt = tgt * VTL[spk] * (ACCENT if lang == 1 else 1.0)
    m = np.zeros((NMEL, frames))
    for i in range(3):
        c = 2595 * np.log10(1 + tgt[:, i] / 700)
        m += (0.86 ** i) * np.exp(-0.5 * ((MHZ[:, None] - c[None, :]) / 88) ** 2)
    m += 0.04 * np.exp(-MHZ[:, None] / (700 + 3 * F0C[spk]))
    lm = np.log(m + 1e-3)
    lm += TILT[spk] * (MHZ[:, None] / MHZ[-1] - 0.5)
    return (lm, lab) if return_lab else lm


def emb_raw(lm, lab):
    return lm.mean(1)


def emb_balanced(lm, lab):
    ps = [lm[:, lab == p].mean(1) for p in range(len(PHSET)) if (lab == p).sum() >= 5]
    return np.mean(ps, 0)


MELS = {}
for s in range(NSPK):
    for lg in (0, 1):
        for u in range(NUTT):
            MELS[(s, lg, u)] = make_mel(s, u, lg, return_lab=True)


def build(kind):
    E = {k: (emb_raw if kind != 'balanced' else emb_balanced)(*v) for k, v in MELS.items()}
    # 去掉整体均值再归一化，保证余弦比的是形状
    out = {}
    for k, v in E.items():
        v = v - v.mean()
        out[k] = v / (np.linalg.norm(v) + 1e-12)
    return out


def cos(a, b):
    return float(a @ b)


def eer(tar, non):
    a, b = np.array(tar), np.array(non)
    ths = np.linspace(min(a.min(), b.min()), max(a.max(), b.max()), 2000)
    fr = np.array([(a < t).mean() for t in ths])
    fa = np.array([(b >= t).mean() for t in ths])
    i = int(np.argmin(np.abs(fr - fa)))
    return float((fr[i] + fa[i]) / 2 * 100)


KINDS = [('raw', '原始（长时平均谱）'), ('balanced', '音素均衡')]
OUT['kinds'] = []
print('同语种 vs 跨语种')
for key, nm in KINDS:
    E = build(key)
    g = {'同人同语种': [], '同人跨语种': [], '异人同语种': [], '异人跨语种': []}
    for s in range(NSPK):
        for lg in (0, 1):
            for u in range(NUTT):
                for u2 in range(u + 1, NUTT):
                    g['同人同语种'].append(cos(E[(s, lg, u)], E[(s, lg, u2)]))
                g['同人跨语种'].append(cos(E[(s, lg, u)], E[(s, 1 - lg, (u + 1) % NUTT)]))
    for s in range(NSPK):
        for s2 in range(s + 1, NSPK):
            for lg in (0, 1):
                g['异人同语种'].append(cos(E[(s, lg, 0)], E[(s2, lg, 1)]))
                g['异人跨语种'].append(cos(E[(s, lg, 0)], E[(s2, 1 - lg, 1)]))
    r = {'key': key, 'name': nm, 'mean': {k: round(float(np.mean(v)), 4) for k, v in g.items()}}
    r['eer_same'] = round(eer(g['同人同语种'], g['异人同语种']), 2)
    r['eer_cross'] = round(eer(g['同人跨语种'], g['异人跨语种']), 2)
    # 相似度评测的"偷懒协议"：目标用同语种、冒充者用跨语种（冒充者天然更不像）
    r['eer_lazy'] = round(eer(g['同人同语种'], g['异人跨语种']), 2)
    r['lang_gap'] = round(r['mean']['同人同语种'] - r['mean']['同人跨语种'], 4)
    r['spk_gap'] = round(r['mean']['同人同语种'] - r['mean']['异人同语种'], 4)
    OUT['kinds'].append(r)
    print('  %-14s 同人同语种 %.4f 同人跨语种 %.4f 异人同语种 %.4f 异人跨语种 %.4f | EER 同语种 %.2f%% 跨语种 %.2f%% 偷懒 %.2f%% | 语言差距 %.4f 说话人差距 %.4f'
          % (nm, r['mean']['同人同语种'], r['mean']['同人跨语种'], r['mean']['异人同语种'], r['mean']['异人跨语种'],
             r['eer_same'], r['eer_cross'], r['eer_lazy'], r['lang_gap'], r['spk_gap']))

# ══ 克隆系统的评分：完美的跨语种克隆，评测给它多少分 ═══════════════════
E = build('raw')
perfect_xl, perfect_sl, wrong_sl = [], [], []
for s in range(NSPK):
    ref = E[(s, 0, 0)]
    perfect_xl.append(cos(ref, E[(s, 1, 1)]))        # 完美克隆：同一个人说语言 E，参考是语言 Z
    perfect_sl.append(cos(ref, E[(s, 0, 1)]))        # 完美克隆：同一个人说语言 Z
    wrong_sl.append(cos(ref, E[((s + 1) % NSPK, 0, 1)]))   # 说语言 Z 的另一个人
OUT['clone'] = {'perfect_sl': round(float(np.mean(perfect_sl)), 4), 'perfect_xl': round(float(np.mean(perfect_xl)), 4),
                'wrong_sl': round(float(np.mean(wrong_sl)), 4),
                'xl_below_wrong': round(100 * float(np.mean(np.array(perfect_xl) < np.array(wrong_sl))), 1)}
print('完美克隆：同语种 %.4f，跨语种 %.4f；说同一语言的另一个人 %.4f；跨语种完美克隆比"另一个说同语言的人"还低的说话人占 %.1f%%'
      % (OUT['clone']['perfect_sl'], OUT['clone']['perfect_xl'], OUT['clone']['wrong_sl'], OUT['clone']['xl_below_wrong']))
# 用音素均衡后的同一个比较
Eb = build('balanced')
pxl = [cos(Eb[(s, 0, 0)], Eb[(s, 1, 1)]) for s in range(NSPK)]
wsl = [cos(Eb[(s, 0, 0)], Eb[((s + 1) % NSPK, 0, 1)]) for s in range(NSPK)]
OUT['clone']['bal_xl_below_wrong'] = round(100 * float(np.mean(np.array(pxl) < np.array(wsl))), 1)
OUT['clone']['bal_perfect_xl'] = round(float(np.mean(pxl)), 4)
OUT['clone']['bal_wrong_sl'] = round(float(np.mean(wsl)), 4)
print('音素均衡之后：', OUT['clone']['bal_xl_below_wrong'], '%')

K = {r['key']: r for r in OUT['kinds']}
OUT['note'] = {
    'raw_lang_gap': K['raw']['lang_gap'], 'raw_spk_gap': K['raw']['spk_gap'],
    'raw_ratio': round(K['raw']['lang_gap'] / K['raw']['spk_gap'], 2),
    'raw_eer_same': K['raw']['eer_same'], 'raw_eer_cross': K['raw']['eer_cross'], 'raw_eer_lazy': K['raw']['eer_lazy'],
    'bal_eer_cross': K['balanced']['eer_cross'], 'bal_eer_same': K['balanced']['eer_same'],
    'bal_lang_gap': K['balanced']['lang_gap'], 'bal_spk_gap': K['balanced']['spk_gap'],
    'perfect_sl': OUT['clone']['perfect_sl'], 'perfect_xl': OUT['clone']['perfect_xl'], 'wrong_sl': OUT['clone']['wrong_sl'],
    'xl_below_wrong': OUT['clone']['xl_below_wrong'], 'bal_xl_below_wrong': OUT['clone']['bal_xl_below_wrong'],
}
OUT['const'] = {'nspk': NSPK, 'nutt': NUTT, 'sec': round(FRAMES / FPS, 1), 'langs': ['Z', 'E']}
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_lang.json', 'w'), ensure_ascii=False)
print('写出 demo_lang.json')
