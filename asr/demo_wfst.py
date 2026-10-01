#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HCLG 构图：状态数和边数是怎么爆炸的，determinize / minimize 又收回来多少。

   真造四级 FST 并真做合成——书里那些数是数出来的。
   词表是合成的中文音节词，发音表由声母韵母拼出来，
   语法是从一个马尔可夫链采样的语料上统计的二元文法。
"""
import json, math, time
import numpy as np
from collections import defaultdict
from fstlib import (FST, EPS, compose, determinize, determinize_input,
                    minimize, count_eps)

OUT = {}
rng = np.random.default_rng(0)

# ══ 音素表与词表 ══════════════════════════════════════════════
INITIALS = ['b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h', 'zh', 'ch', 'sh']
FINALS = ['a', 'o', 'e', 'i', 'u', 'ai', 'ei', 'ao', 'ou', 'an', 'en', 'ang', 'eng']
PHONES = ['<sil>'] + INITIALS + FINALS
PH_ID = {p: k + 1 for k, p in enumerate(PHONES)}        # 0 留给 ε
NPH = len(PHONES)


def make_lexicon(nword, seed=1, homo_frac=0.25):
    """造一个词表：每个词 1–2 个音节，每个音节 = 声母 + 韵母。
       其中 homo_frac 的词<刻意>和前面某个词同音——
       同音词正是确定化必须加消歧符的原因，真实词典里到处都是。"""
    g = np.random.default_rng(seed)
    lex = {}
    prons = []
    nhomo = 0
    for w in range(nword):
        name = 'w%03d' % w
        if prons and g.random() < homo_frac:
            lex[name] = list(prons[g.integers(len(prons))])   # 同音
            nhomo += 1
            continue
        nsyl = 1 if g.random() < 0.55 else 2
        ph = []
        for _ in range(nsyl):
            ph += [INITIALS[g.integers(len(INITIALS))], FINALS[g.integers(len(FINALS))]]
        lex[name] = ph
        prons.append(tuple(ph))
    return lex, nhomo


def build_G(words, seed=2, nsent=600, order=2):
    """二元文法 FST：状态 = 上一个词，边 = 下一个词，权重 = −log p"""
    g = np.random.default_rng(seed)
    W = list(words)
    # 用一个稀疏的马尔可夫链采样语料，这样二元文法才有结构
    nxt = {w: g.choice(W, size=min(6, len(W)), replace=False) for w in W}
    cnt = defaultdict(lambda: defaultdict(int))
    uni = defaultdict(int)
    for _ in range(nsent):
        h = '<s>'
        for _ in range(int(g.integers(4, 12))):
            w = (W[g.integers(len(W))] if h == '<s>'
                 else nxt[h][g.integers(len(nxt[h]))])
            cnt[h][w] += 1
            uni[w] += 1
            h = w
        cnt[h]['</s>'] += 1
    f = FST('G')
    sid = {'<s>': f.add_state()}
    f.start = sid['<s>']
    for w in W:
        sid[w] = f.add_state()
    tot_uni = sum(uni.values()) + 1
    for h in cnt:
        for w, c in cnt[h].items():
            p = c / sum(cnt[h].values())
            if w == '</s>':
                f.set_final(sid[h], -math.log(p))
            else:
                f.add_arc(sid[h], WID[w], WID[w], -math.log(p), sid[w])
    # 回退边：没见过的二元组走回退（这会引入 ε 输入，是真实 G 的样子）
    for h in list(sid):
        if h == '<s>':
            continue
        seen = set(cnt[h])
        for w in W:
            if w not in seen:
                p = 0.3 * (uni[w] + 1) / tot_uni
                f.add_arc(sid[h], WID[w], WID[w], -math.log(p), sid[w])
    f.set_final(sid['<s>'], 0.0)
    return f.trim()


def build_L(lex, disambig=True):
    """发音词典 FST：输入音素，输出词（只在第一个音素上输出，其余输出 ε）。
       disambig=True 时给同音词加消歧符 #1 #2 …（真实系统必须加）。"""
    f = FST('L')
    loop = f.add_state()
    f.start = loop
    f.set_final(loop, 0.0)
    bykey = defaultdict(list)
    for w, ph in lex.items():
        bykey[tuple(ph)].append(w)
    dis = 0
    for key, ws in bykey.items():
        for k, w in enumerate(ws):
            s = loop
            for j, p in enumerate(key):
                d = f.add_state()
                f.add_arc(s, PH_ID[p], WID[w] if j == 0 else EPS, 0.0, d)
                s = d
            if disambig and len(ws) > 1:
                dis = max(dis, k + 1)
                d = f.add_state()
                f.add_arc(s, DIS_ID + k, EPS, 0.0, d)   # 消歧符占一个输入标签
                s = d
            f.add_arc(s, EPS, EPS, 0.0, loop)
    return f.trim(), dis


def build_C(phones=NPH):
    """上下文相关：输入三音子 id，输出中心音素。
       状态 = (左, 中) 两个音素的记忆 → 状态数 ≈ |音素|²。"""
    f = FST('C')
    idx = {}

    def st(a, b):
        if (a, b) not in idx:
            idx[(a, b)] = f.add_state()
        return idx[(a, b)]

    f.start = st(0, 0)
    for a in range(phones + 1):
        for b in range(phones + 1):
            s = st(a, b)
            for c in range(1, phones + 1):
                tri = ((a * (phones + 1) + b) * (phones + 1) + c) + 1
                f.add_arc(s, tri, b if b else EPS, 0.0, st(b, c))
            f.set_final(s, 0.0)
    return f.trim()


def build_H(ntri, nstate=3):
    """HMM：每个三音子一个 nstate 状态的左到右模型，带自环。
       输入 = 绑定后的 senone id，输出 = 三音子 id。"""
    f = FST('H')
    loop = f.add_state()
    f.start = loop
    f.set_final(loop, 0.0)
    for t in range(1, ntri + 1):
        s = loop
        for j in range(nstate):
            d = f.add_state()
            sen = ((t - 1) % NSENONE) + 1               # 绑定：多个三音子共享 senone
            f.add_arc(s, sen, t if j == 0 else EPS, 0.7, d)
            f.add_arc(d, sen, EPS, 0.7, d)              # 自环
            s = d
        f.add_arc(s, EPS, EPS, 0.0, loop)
    return f.trim()


def sz(f):
    return '%d 态 / %d 边' % (f.nstate, f.narc)


# ══ ① 逐级合成 ═══════════════════════════════════════════════
NW = 24
NSENONE = 200
LEX, NHOMO = make_lexicon(NW, seed=1)
WORDS = sorted(LEX)
WID = {w: k + 1 for k, w in enumerate(WORDS)}
WID['</s>'] = len(WORDS) + 1
DIS_ID = NPH + 100                                      # 消歧符的标签起点

print('词表 %d 个词，其中同音词 %d 个；音素 %d 个' % (NW, NHOMO, NPH))
OUT['setup'] = {'nword': NW, 'nhomo': NHOMO, 'nphone': NPH, 'nsenone': NSENONE}

t0 = time.time()
G = build_G(WORDS)
L, NDIS = build_L(LEX, disambig=True)
print('\n① 逐级合成（带消歧符）')
print('  %-12s %s' % ('G（二元文法）', sz(G)))
print('  %-12s %s' % ('L（发音词典）', sz(L)))
LG = compose(L, G)
print('  %-12s %s' % ('L∘G', sz(LG)))
LGd = determinize_input(LG)
LGdm = minimize(LGd)
print('  %-12s %s   →  minimize 后 %s' % ('det(L∘G)', sz(LGd), sz(LGdm)))

C = build_C()
print('  %-12s %s' % ('C（三音子）', sz(C)))
CLG = compose(C, LGdm)
print('  %-12s %s' % ('C∘L∘G', sz(CLG)))
CLGd = determinize_input(CLG)
CLGdm = minimize(CLGd)
print('  %-12s %s   →  minimize 后 %s' % ('det(C∘L∘G)', sz(CLGd), sz(CLGdm)))

# H 只对实际用到的三音子建，否则 |三音子| = |音素|³ 会把内存吃光
used = set()
for s in list(CLGdm.arcs):
    for i, o, w, d in CLGdm.arcs[s]:
        if i != EPS:
            used.add(i)
TRI = sorted(used)
TRI_MAP = {t: k + 1 for k, t in enumerate(TRI)}
print('  实际用到的三音子 %d 个（全集是 %d³ = %s 个）'
      % (len(TRI), NPH + 1, '{:,}'.format((NPH + 1) ** 3)))

CLG2 = FST('CLG')                                       # 把三音子 id 重编号
CLG2.nstate, CLG2.start, CLG2.final = CLGdm.nstate, CLGdm.start, dict(CLGdm.final)
for s in list(CLGdm.arcs):
    for i, o, w, d in CLGdm.arcs[s]:
        CLG2.add_arc(s, TRI_MAP.get(i, EPS), o, w, d)
H = build_H(len(TRI))
print('  %-12s %s' % ('H（HMM）', sz(H)))
HCLG = compose(H, CLG2)
print('  %-12s %s' % ('H∘C∘L∘G', sz(HCLG)))
HCLGd = determinize_input(HCLG)
HCLGdm = minimize(HCLGd)
print('  %-12s %s   →  minimize 后 %s' % ('det(HCLG)', sz(HCLGd), sz(HCLGdm)))
print('  用时 %.1f s' % (time.time() - t0))

stages = [('G 二元文法', G), ('L 发音词典', L), ('L∘G', LG), ('det(L∘G)', LGd),
          ('min·det(L∘G)', LGdm), ('C 三音子', C), ('C∘L∘G', CLG),
          ('det(C∘L∘G)', CLGd), ('min·det(C∘L∘G)', CLGdm), ('H HMM', H),
          ('H∘C∘L∘G', HCLG), ('det(HCLG)', HCLGd), ('min·det(HCLG)', HCLGdm)]
OUT['stages'] = [{'tag': t, **f.stats(), **count_eps(f)} for t, f in stages]
OUT['ntri_used'] = len(TRI)
OUT['ntri_all'] = (NPH + 1) ** 3

# ══ ② 确定化收了多少、最小化又收了多少 ═════════════════════════
print('\n② 两步优化各自收回多少')
print('  %-16s %10s %10s %10s' % ('', '状态', '边', '相对合成后'))
for tag, a, b, c in (('L∘G', LG, LGd, LGdm), ('C∘L∘G', CLG, CLGd, CLGdm),
                     ('H∘C∘L∘G', HCLG, HCLGd, HCLGdm)):
    print('  %-16s %10d %10d' % (tag + ' 合成后', a.nstate, a.narc))
    print('  %-16s %10d %10d   %9.1f%%'
          % ('  determinize', b.nstate, b.narc, b.narc / a.narc * 100))
    print('  %-16s %10d %10d   %9.1f%%'
          % ('  + minimize', c.nstate, c.narc, c.narc / a.narc * 100))
OUT['opt'] = [{'tag': t, 'raw': a.stats(), 'det': b.stats(), 'min': c.stats(),
               'det_pct': round(b.narc / a.narc * 100, 1),
               'min_pct': round(c.narc / a.narc * 100, 1)}
              for t, a, b, c in (('L∘G', LG, LGd, LGdm), ('C∘L∘G', CLG, CLGd, CLGdm),
                                 ('H∘C∘L∘G', HCLG, HCLGd, HCLGdm))]

# ══ ③ 不加消歧符会怎样 ════════════════════════════════════════
print('\n③ 不加消歧符：确定化还能不能收敛')
Lnd, _ = build_L(LEX, disambig=False)
LGnd = compose(Lnd, G)
print('  L∘G（无消歧符） %s' % sz(LGnd))
res = {'ok': False}
try:
    t1 = time.time()
    d = determinize_input(LGnd, cap=60000, maxres=40)
    res = {'ok': True, 'states': d.nstate, 'arcs': d.narc, 'sec': round(time.time() - t1, 2)}
    print('  确定化成功：%s' % sz(d))
except MemoryError as e:
    res = {'ok': False, 'why': str(e), 'cap': 60000}
    print('  <strong>确定化在 60000 态上被迫中止</strong>：%s' % e)
print('  对照：带消歧符时确定化结果是 %s' % sz(LGd))
OUT['nodisambig'] = res
OUT['disambig'] = {'states': LGd.nstate, 'arcs': LGd.narc, 'ndis': NDIS}
print('  <strong>消歧符不是工程细节，是可确定化的前提</strong>——')
print('  两个同音词让子集构造无法在有限步内分辨出该输出哪个词。')

# ══ ④ 词表规模扫描 ════════════════════════════════════════════
print('\n④ 词表变大时，HCLG 怎么长')
OUT['scale'] = []
for nw in (8, 12, 16, 24, 32, 48):
    LEX, nh = make_lexicon(nw, seed=1)
    WORDS = sorted(LEX)
    WID = {w: k + 1 for k, w in enumerate(WORDS)}
    WID['</s>'] = len(WORDS) + 1
    g = build_G(WORDS)
    l, _ = build_L(LEX, disambig=True)
    lg = minimize(determinize_input(compose(l, g)))
    clg = minimize(determinize_input(compose(build_C(), lg)))
    used = {i for s in list(clg.arcs) for i, o, w, d in clg.arcs[s] if i != EPS}
    tm = {t: k + 1 for k, t in enumerate(sorted(used))}
    c2 = FST('CLG'); c2.nstate, c2.start, c2.final = clg.nstate, clg.start, dict(clg.final)
    for s in list(clg.arcs):
        for i, o, w, d in clg.arcs[s]:
            c2.add_arc(s, tm.get(i, EPS), o, w, d)
    hclg = minimize(determinize_input(compose(build_H(len(used)), c2)))
    r = {'nword': nw, 'g_arcs': g.narc, 'lg_arcs': lg.narc, 'clg_arcs': clg.narc,
         'hclg_states': hclg.nstate, 'hclg_arcs': hclg.narc, 'ntri': len(used)}
    OUT['scale'].append(r)
    print('  词表 %3d   G %5d 边   min(L∘G) %5d   min(C∘L∘G) %6d   '
          'min(HCLG) %6d 态 / %6d 边   三音子 %4d'
          % (nw, r['g_arcs'], r['lg_arcs'], r['clg_arcs'],
             r['hclg_states'], r['hclg_arcs'], r['ntri']))
a, b = OUT['scale'][0], OUT['scale'][-1]
sl = math.log(b['hclg_arcs'] / a['hclg_arcs']) / math.log(b['nword'] / a['nword'])
OUT['scale_slope'] = round(sl, 2)
print('  词表 ×%.0f，HCLG 边数 ×%.1f —— 对数斜率 %.2f'
      % (b['nword'] / a['nword'], b['hclg_arcs'] / a['hclg_arcs'], sl))
print('  这里的 G 是<strong>全连接回退</strong>的二元文法，所以 |G| ∝ 词表²，')
print('  HCLG 跟着 G 走。真实系统靠剪枝把 G 压稀，这条斜率才降到 1 附近。')

# ══ ⑤ 全量展开省不省内存：一个我猜错了的问题 ═════════════════
BPA = 16                                                 # 每条边约 16 字节（OpenFst 量级）
sc = OUT['scale']
print('\n⑤ on-the-fly 到底省多少：我原以为是数量级，实测不是')
print('  %8s %12s %12s %10s' % ('词表', 'min(L∘G) 边', 'min(HCLG) 边', 'H∘C 展开倍数'))
exp = []
for r in sc:
    e = r['hclg_arcs'] / r['lg_arcs']
    exp.append(e)
    print('  %8d %12d %12d %9.1f×' % (r['nword'], r['lg_arcs'], r['hclg_arcs'], e))
OUT['expand'] = [round(e, 2) for e in exp]
OUT['expand_mean'] = round(float(np.mean(exp)), 2)
print('  展开倍数在 %.1f–%.1f 之间，<strong>不随词表增长</strong>（均值 %.1f×）。'
      % (min(exp), max(exp), np.mean(exp)))
print('  原因很直接：HCLG 就是 L∘G 里每条音素边被 H∘C 展成几条 HMM 边，')
print('  而这个展开系数只由"每个音素几个 HMM 状态"决定，和词表无关。')
print()
print('  所以 on-the-fly 省下的是这个<strong>常数倍</strong>，不是数量级。')
print('  我原本按 ④ 的斜率外推，以为词表上到十万会差几十倍——')
print('  <strong>那个外推是错的</strong>：HCLG 和 L∘G 的斜率几乎一样（%.2f vs %.2f），'
      % (OUT['scale_slope'],
         float(np.polyfit(np.log([r['nword'] for r in sc]),
                          np.log([r['lg_arcs'] for r in sc]), 1)[0])))
print('  因为两者都被 |G| 支配。')
print()
print('  按需合成真正值钱的是另外两件事：')
print('    ① <strong>换 G 不用重建</strong>。改一次语言模型，全量方案要离线重跑几小时。')
print('    ② 峰值内存。离线构图时的中间结果（未确定化的 H∘C∘L∘G）'
      '比最终的 HCLG 大 %.1f 倍，' % (HCLG.narc / HCLGdm.narc))
print('       而它必须一次性放进内存——实测 %s → %s 边。'
      % ('{:,}'.format(HCLG.narc), '{:,}'.format(HCLGdm.narc)))
OUT['peak'] = {'raw_arcs': HCLG.narc, 'final_arcs': HCLGdm.narc,
               'ratio': round(HCLG.narc / HCLGdm.narc, 2),
               'c_arcs': C.narc, 'bytes_per_arc': BPA}

json.dump(OUT, open('demo_wfst.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_wfst.json')
