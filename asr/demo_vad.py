#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""38 节：长音频切在哪里——固定切块会切到多少个词，VAD 切分要付出什么。

   一段 120 s 的连续合成语音（真值边界已知：每个音段的起止、哪些是"语音岛"——两段静音之间连续发声的那一串）。
   ① 固定切块（10 / 20 / 30 s，带或不带重叠）：有多少个语音岛被切断
   ② 能量 VAD + 自适应噪声底：在干净、20 / 10 / 0 dB 白噪、10 dB babble 下，语音召回、多送进去的非语音、被削掉头尾的语音岛
   ③ 补偿：两头各补 0 / 100 / 200 / 300 ms，召回涨多少、多送多少
"""
import numpy as np, json, time
import enhlib as E
import toylib as T

OUT = {}
t0 = time.time()
SR = T.SR
DUR = 120.0
HOP = 160
SEEDS = (0, 1, 2)


def long_audio(seed):
    """语音片段之间插入长短不一的停顿（0.25–3 s，对数正态），片段内部的短静音保留"""
    g = np.random.default_rng(seed)
    xs, labs, n = [], [], 0
    k = 0
    while n < int(DUR * SR):
        x, lab = T.utterance(seed * 1000 + k, spk=seed % 5, dur=float(g.uniform(1.6, 3.6)))
        sp = np.where(lab != 0)[0]
        x, lab = x[sp[0]:sp[-1] + 1], lab[sp[0]:sp[-1] + 1]            # 去掉首尾静音，停顿由下面统一插入
        gap = int(float(np.clip(np.exp(g.normal(-0.2, 0.7)), 0.25, 3.0)) * SR)
        floor = 10 ** (-55 / 20) * g.standard_normal(gap)
        xs += [x, floor]
        labs += [lab, np.zeros(gap, np.int8)]
        n += len(x) + gap
        k += 1
    return np.concatenate(xs)[:int(DUR * SR)], np.concatenate(labs)[:int(DUR * SR)]


def islands(lab):
    """语音岛：两段静音之间连续发声的区间（样点下标）"""
    sp = lab != 0
    d = np.diff(np.concatenate([[0], sp.astype(int), [0]]))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    return list(zip(st, en))


def frame_mask(lab):
    n = len(lab) // HOP
    return np.array([(lab[i * HOP:(i + 1) * HOP] != 0).mean() > 0.5 for i in range(n)])


def energy_db(x):
    n = len(x) // HOP
    f = x[:n * HOP].reshape(n, HOP)
    return 10 * np.log10(np.mean(f ** 2, 1) + 1e-12)


def vad(x, margin_db=9.0, hang=10, win=300, q=0.10):
    """自适应噪声底（过去 3 s 内帧能量的第 10 百分位）+ 固定余量 + 拖尾 hang 帧（默认 10 帧 = 100 ms）"""
    e = energy_db(x)
    out = np.zeros(len(e), bool)
    h = 0
    for i in range(len(e)):
        lo = max(0, i - win)
        floor = np.quantile(e[lo:i + 1], q)
        if e[i] > floor + margin_db:
            out[i] = True
            h = hang
        elif h > 0:
            out[i] = True
            h -= 1
    return out


def pad(m, k):
    if k == 0:
        return m.copy()
    c = np.convolve(m.astype(float), np.ones(2 * k + 1), 'same') > 0
    return c


def seg_cut_islands(isl, bounds):
    """被任一边界落在内部（离两端至少 1 帧）的语音岛个数"""
    n = 0
    for s, e in isl:
        if any(s + HOP < b < e - HOP for b in bounds):
            n += 1
    return n


def clipped(isl, keep, tol=3):
    """头或尾被削掉超过 tol 帧的语音岛个数。keep 是帧级 bool"""
    n = 0
    for s, e in isl:
        a, b = s // HOP, e // HOP
        if b - a < 4:
            continue
        head = np.argmax(keep[a:b]) if keep[a:b].any() else b - a
        tail = np.argmax(keep[a:b][::-1]) if keep[a:b].any() else b - a
        if head > tol or tail > tol:
            n += 1
    return n


OUT['fixed'] = []
print('① 固定切块')
for L in (10.0, 20.0, 30.0):
    for ov in (0.0, 1.0):
        cut, tot = [], []
        for sd in SEEDS:
            x, lab = long_audio(sd)
            isl = islands(lab)
            bounds = [int(t * SR) for t in np.arange(L - ov, DUR, L - ov)]       # 每块长 L，相邻重叠 ov
            # 带重叠时一个边界处的两块各自看到完整的岛，只要岛短于重叠；这里按"能被某一块完整包含"算
            if ov == 0:
                n = seg_cut_islands(isl, bounds)
            else:
                n = 0
                chunks = [(int(t * SR), int(min(t + L, DUR) * SR)) for t in np.arange(0, DUR - ov, L - ov)]
                for s, e in isl:
                    if not any(a <= s and e <= b for a, b in chunks):
                        n += 1
            cut.append(n)
            tot.append(len(isl))
        OUT['fixed'].append({'L': L, 'overlap': ov, 'cut': round(float(np.mean(cut)), 1),
                             'islands': round(float(np.mean(tot)), 1),
                             'pct': round(100 * float(np.mean(cut)) / float(np.mean(tot)), 1),
                             'cost': round((L / (L - ov)), 2)})
        print('  L=%2.0f s 重叠 %.0f s：%5.1f / %5.1f 个语音岛被切断（%.1f%%），算力 ×%.2f'
              % (L, ov, OUT['fixed'][-1]['cut'], OUT['fixed'][-1]['islands'], OUT['fixed'][-1]['pct'], OUT['fixed'][-1]['cost']))

# ══ ② ③ VAD ══════════════════════════════════════════════════
CONDS = [('clean', '干净', None), ('w20', '白噪 20 dB', ('white', 20)), ('w10', '白噪 10 dB', ('white', 10)),
         ('w0', '白噪 0 dB', ('white', 0)), ('b10', 'babble 10 dB', ('babble', 10))]
MARG = (3.0, 6.0, 9.0, 12.0)
PADS = (0, 5, 10, 20, 30)                    # 帧；10 ms/帧
OUT['vad'] = []
print('\n② ③ 能量 VAD：余量扫描与首尾补偿')
for ck, nm, nz in CONDS:
    acc = {(m, p): {'recall': [], 'fa': [], 'keep': [], 'clip': [], 'nisl': []} for m in MARG for p in PADS}
    for sd in SEEDS:
        x, lab = long_audio(sd)
        if nz:
            x = T.add_noise(x, nz[0], nz[1], 50 + sd)
        isl = islands(lab)
        fm = frame_mask(lab)
        for mg in MARG:
            v = vad(x, margin_db=mg)[:len(fm)]
            for p in PADS:
                k = pad(v, p)
                a_ = acc[(mg, p)]
                a_['recall'].append(float((k & fm).sum() / fm.sum()))
                a_['fa'].append(float((k & ~fm).sum() / max((~fm).sum(), 1)))
                a_['keep'].append(float(k.mean()))
                a_['clip'].append(clipped(isl, k))
                a_['nisl'].append(len(isl))
    row = {'key': ck, 'name': nm, 'cells': []}
    for (mg, p), a_ in acc.items():
        row['cells'].append({'margin': mg, 'pad_ms': p * 10,
                             'recall': round(100 * float(np.mean(a_['recall'])), 1),
                             'fa': round(100 * float(np.mean(a_['fa'])), 1),
                             'keep': round(100 * float(np.mean(a_['keep'])), 1),
                             'clip_pct': round(100 * float(np.mean(a_['clip'])) / float(np.mean(a_['nisl'])), 1)})
    OUT['vad'].append(row)
    c9 = {(c['margin'], c['pad_ms']): c for c in row['cells']}
    print('  %-14s ' % nm + '  '.join('余量 %2.0f dB: 召回 %5.1f 误报 %5.1f 削头尾 %5.1f%%' % (
        mg, c9[(mg, 0)]['recall'], c9[(mg, 0)]['fa'], c9[(mg, 0)]['clip_pct']) for mg in MARG))

V = {r['key']: {(c['margin'], c['pad_ms']): c for c in r['cells']} for r in OUT['vad']}
F = {(r['L'], r['overlap']): r for r in OUT['fixed']}
_isl = [(e - s_) / SR for s_, e in islands(long_audio(0)[1])]
OUT['note'] = {
    'isl_med_s': round(float(np.median(_isl)), 2), 'isl_max_s': round(float(np.max(_isl)), 2),
    'fix10_pct': F[(10.0, 0.0)]['pct'], 'fix30_pct': F[(30.0, 0.0)]['pct'], 'fix10_cut': F[(10.0, 0.0)]['cut'],
    'fix20_pct': F[(20.0, 0.0)]['pct'],
    'fix10ov_pct': F[(10.0, 1.0)]['pct'], 'fix10ov_cost': F[(10.0, 1.0)]['cost'],
    'fix20ov_pct': F[(20.0, 1.0)]['pct'], 'fix30ov_pct': F[(30.0, 1.0)]['pct'],
    'islands': F[(10.0, 0.0)]['islands'],
    'clean_recall': V['clean'][(9.0, 0)]['recall'], 'clean_fa': V['clean'][(9.0, 0)]['fa'],
    'clean_clip0': V['clean'][(9.0, 0)]['clip_pct'], 'clean_clip100': V['clean'][(9.0, 100)]['clip_pct'],
    'w10_recall': V['w10'][(9.0, 0)]['recall'], 'w10_fa': V['w10'][(9.0, 0)]['fa'],
    'w10_clip0': V['w10'][(9.0, 0)]['clip_pct'], 'w10_clip100': V['w10'][(9.0, 100)]['clip_pct'],
    'w10_clip300': V['w10'][(9.0, 300)]['clip_pct'],
    'w0_recall9': V['w0'][(9.0, 0)]['recall'], 'w0_fa9': V['w0'][(9.0, 0)]['fa'],
    'w0_recall3': V['w0'][(3.0, 0)]['recall'], 'w0_fa3': V['w0'][(3.0, 0)]['fa'],
    'b10_recall9': V['b10'][(9.0, 0)]['recall'], 'b10_fa9': V['b10'][(9.0, 0)]['fa'],
    'b10_fa3': V['b10'][(3.0, 0)]['fa'], 'b10_recall3': V['b10'][(3.0, 0)]['recall'],
    'w10_keep0': V['w10'][(9.0, 0)]['keep'], 'w10_keep300': V['w10'][(9.0, 300)]['keep'],
    'clean_keep0': V['clean'][(9.0, 0)]['keep'], 'clean_keep100': V['clean'][(9.0, 100)]['keep'],
    'w10_recall100': V['w10'][(9.0, 100)]['recall'],
}
OUT['const'] = {'dur': DUR, 'seeds': list(SEEDS), 'margins_db': list(MARG), 'hang_ms': 100, 'floor_win_s': 3.0,
                'pads_ms': [p * 10 for p in PADS]}
OUT['runtime_s'] = round(time.time() - t0, 1)
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_vad.json', 'w'), ensure_ascii=False)
print('写出 demo_vad.json  %.1f s' % OUT['runtime_s'])
