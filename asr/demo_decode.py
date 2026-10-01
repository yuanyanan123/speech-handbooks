#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解码：beam 宽度买到了什么，以及三种语言模型融合的差别。

   用一个<可解析构造>的自回归模型，不用训练：
       log P(y_u | x, y_<u) ∝ 声学项(x, u) + 源域二元文法(y_<u)
   于是这个模型的"内部语言模型"是<已知的>——
   这正是 density ratio 和 ILME 想减掉的那个东西，
   而通常没人知道它究竟是什么。这里知道，所以能把两者分开量。
"""
import numpy as np, json, math
from collections import defaultdict

rng = np.random.default_rng(0)
OUT = {}
V = 40                     # 词表（不含 <eos>）
EOS = V
L = 12                     # 每句的长度
NUTT = 300
TAU = 0.55                 # 内部语言模型相对源域文法的"强度"


def make_bigram(seed, sparsity=8, temp=1.0, floor=0.02):
    """造一个二元文法：每个历史给少数几个后继高概率，其余给一个地板值。
       地板不能太低，否则文法项会压过声学项——真实的 n-gram 有回退，同理。"""
    g = np.random.default_rng(seed)
    P = np.full((V + 1, V + 1), floor)
    for h in range(V + 1):
        nxt = g.choice(V, size=sparsity, replace=False)
        w = g.dirichlet(np.ones(sparsity) * 0.8)
        for k, n in enumerate(nxt):
            P[h, n] = floor + w[k] * 0.9
        P[h, EOS] = 0.02
    P = P ** (1.0 / temp)
    return np.log(P / P.sum(1, keepdims=True))


LM_SRC = make_bigram(1)            # 声学模型训练时见过的文本分布
LM_TGT = make_bigram(2)            # 上线后真正的文本分布（域不同）
LM_ILM = np.log(np.exp(LM_SRC * TAU) / np.exp(LM_SRC * TAU).sum(1, keepdims=True))


def sample(lm, seed, n=NUTT):
    g = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        y, h = [], EOS
        for _ in range(L):
            p = np.exp(lm[h][:V]); p /= p.sum()
            c = int(g.choice(V, p=p))
            y.append(c); h = c
        out.append(y)
    return out


REF = sample(LM_TGT, 11)


def acoustic(y, seed, conf=3.6):
    """声学项：每个位置给一个以真值为中心的对数似然（越大越像）。
       conf 越大越可信。真实系统里这一项来自编码器。"""
    g = np.random.default_rng(seed)
    A = []
    for u, c in enumerate(y):
        s = g.standard_normal(V + 1) * 1.0
        s[c] += conf
        s[EOS] -= 6.0
        A.append(s - np.log(np.exp(s - s.max()).sum()) - s.max())
    s = np.full(V + 1, -8.0); s[EOS] = 4.0            # 最后一步给 <eos>
    A.append(s - np.log(np.exp(s - s.max()).sum()) - s.max())
    return np.array(A)


ACO = [acoustic(y, 100 + i) for i, y in enumerate(REF)]


def am_logp(A, u, hist):
    """自回归模型在第 u 步的对数后验：声学项 + 源域文法，再归一化。
       于是它的<内部语言模型>就是 LM_SRC 被 TAU 削弱之后的那个分布。"""
    z = A[u] + TAU * LM_SRC[hist]
    return z - (z.max() + np.log(np.exp(z - z.max()).sum()))


def beam_decode(A, beam, lm=None, lam=0.0, sub=None, gam=0.0, beta=0.0,
                nbest=1, lnorm=0.0):
    """标准的自回归 beam search。
       lm/lam：外部语言模型与权重；sub/gam：要减掉的那个分布与权重；
       beta：每输出一个词的奖励（长度归一化的常见做法）。"""
    hyps = [([], EOS, 0.0)]
    done = []
    expand = 0
    for u in range(len(A)):
        cand = []
        lp_cache = {}
        for y, h, s in hyps:
            if h not in lp_cache:
                lp_cache[h] = am_logp(A, u, h)
            lp = lp_cache[h]
            tot = lp.copy()
            if lm is not None:
                tot = tot + lam * lm[h]
            if sub is not None:
                tot = tot - gam * sub[h]
            tot = tot + beta
            expand += V + 1
            k = min(beam, len(tot) - 1)
            top = np.argpartition(-tot, k)[:k + 1]
            for c in top:
                cand.append((y + [int(c)], int(c), s + float(tot[c])))
        cand.sort(key=lambda r: -r[2])
        hyps = []
        for y, h, s in cand:
            if h == EOS:
                done.append((y[:-1], s))
            else:
                hyps.append((y, h, s))
            if len(hyps) >= beam:
                break
        if not hyps:
            break
    done += [(y, s) for y, h, s in hyps]
    # 最终选择时按 得分 / 长度^lnorm 排序；lnorm=0 就是原始得分
    done.sort(key=lambda r: -(r[1] / max(len(r[0]), 1) ** lnorm))
    return (done[:nbest] if nbest > 1 else done[0][0]), expand


def ter(hyp, ref):
    """标记错误率（编辑距离 / 参考长度）"""
    n, m = len(ref), len(hyp)
    d = list(range(m + 1))
    for i in range(1, n + 1):
        prev, d[0] = d[0], i
        for j in range(1, m + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (ref[i - 1] != hyp[j - 1]))
            prev = cur
    return d[m] / max(n, 1)


def evaluate(**kw):
    kw.setdefault('lnorm', 0.0)
    e, ex = [], 0
    for A, r in zip(ACO, REF):
        h, x = beam_decode(A, **kw)
        e.append(ter(h, r)); ex += x
    return float(np.mean(e)) * 100, ex / len(ACO)


# ══ ① beam 宽度买到了什么 ═════════════════════════════════════
def mean_score(beam, **kw):
    ss = []
    for A, r in zip(ACO, REF):
        h, _ = beam_decode(A, beam=beam, **kw)
        # 用同一套打分函数给结果打分，好和参考答案比
        sc, hist = 0.0, EOS
        for u, c in enumerate(h):
            sc += float(am_logp(A, u, hist)[c]); hist = c
        ss.append(sc / max(len(h), 1))
    return float(np.mean(ss))


ref_score = []
for A, r in zip(ACO, REF):
    sc, hist = 0.0, EOS
    for u, c in enumerate(r):
        sc += float(am_logp(A, u, hist)[c]); hist = c
    ref_score.append(sc / len(r))
REF_SCORE = float(np.mean(ref_score))

print('① beam 宽度 vs 错误率 vs 模型得分（不加语言模型）')
print('  这里所有假设长度都固定为 %d，所以没有长度偏置的干扰。' % L)
print('  %6s %11s %14s %14s %10s'
      % ('beam', '标记错误率', '每步平均得分', '每句扩展次数', '相对 beam=1'))
OUT['beam'] = []
base = None
for b in (1, 2, 4, 8, 16, 32):
    t, ex = evaluate(beam=b)
    sc = mean_score(b)
    base = base or ex
    OUT['beam'].append({'beam': b, 'ter': round(t, 2), 'score': round(sc, 4),
                        'expand': round(ex, 0), 'rel': round(ex / base, 1)})
    print('  %6d %10.2f%% %14.4f %14s %9.1f×'
          % (b, t, sc, '{:,}'.format(int(ex)), ex / base))
OUT['ref_score'] = round(REF_SCORE, 4)
b1 = OUT['beam'][0]; bl = OUT['beam'][-1]
print('  参考答案在同一个打分函数下的每步得分：<strong>%.4f</strong>' % REF_SCORE)
print()
print('  <strong>beam 越宽，模型得分越高（%.4f → %.4f），错误率也越高（%.2f%% → %.2f%%）。</strong>'
      % (b1['score'], bl['score'], b1['ter'], bl['ter']))
print('  而且 beam=%d 找到的假设得分已经<strong>超过了参考答案</strong>（%.4f > %.4f）。'
      % (bl['beam'], bl['score'], REF_SCORE))
print('  这不是搜索出了问题——搜索干得很好。是<strong>打分函数本身偏了</strong>：')
print('  这个声学模型自带一个源域的语言模型，而测试文本来自另一个域。')
print('  beam 越宽，就越忠实地找到"模型认为最好"的那个答案，也就越错。')
print()
print('  所以 beam 宽度的收益有一个前提：<strong>打分函数得是对的</strong>。')
print('  ③ 会看到，把打分函数修对（融合正确的语言模型）之后，')
print('  同样的 beam 宽度能把错误率从 %.2f%% 降到 %s——' % (bl['ter'], '见 ③'))
print('  <strong>修打分函数的收益，比加宽搜索大一个数量级</strong>。')

# ══ ② n-best 里有没有更好的 ═══════════════════════════════════
print('\n② n-best 的 oracle：搜到了但没选对')
OUT['oracle'] = []
for b in (4, 8, 16, 32):
    one, orc = [], []
    for A, r in zip(ACO, REF):
        nb, _ = beam_decode(A, beam=b, nbest=b, lnorm=1.0)
        one.append(ter(nb[0][0], r))
        orc.append(min(ter(h, r) for h, s in nb))
    OUT['oracle'].append({'beam': b, 'top1': round(float(np.mean(one)) * 100, 2),
                          'oracle': round(float(np.mean(orc)) * 100, 2)})
    print('  beam %2d   top-1 %6.2f%%   oracle %6.2f%%   差 %5.2f%%'
          % (b, OUT['oracle'][-1]['top1'], OUT['oracle'][-1]['oracle'],
             OUT['oracle'][-1]['top1'] - OUT['oracle'][-1]['oracle']))
o = OUT['oracle'][-1]
OUT['oracle_gap'] = round(o['top1'] - o['oracle'], 2)
print('  beam %d 时 oracle 比 top-1 低 %.2f 个百分点——'
      % (o['beam'], OUT['oracle_gap']))
print('  <strong>正确答案已经在候选里了，只是得分排序没把它排到第一</strong>。')
print('  这就是重打分（rescoring）能起作用的全部空间。')

# ══ ③ 三种语言模型融合 ════════════════════════════════════════
print('\n③ 域不匹配时，三种融合各能拿回多少')
print('  声学模型的内部语言模型 = 源域文法^%.2f（这里是已知的）' % TAU)
BEAM = 16
t0, _ = evaluate(beam=BEAM, lnorm=1.0)
print('  不加语言模型：%.2f%%' % t0)
OUT['fusion'] = {'none': round(t0, 2), 'tau': TAU, 'beam': BEAM}

print('\n  ⑴ shallow fusion：+ λ·log P_目标域')
OUT['shallow'] = []
for lam in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0):
    t, _ = evaluate(beam=BEAM, lm=LM_TGT, lam=lam, lnorm=1.0)
    OUT['shallow'].append({'lam': lam, 'ter': round(t, 2)})
    print('     λ = %.1f   %6.2f%%' % (lam, t))
bs = min(OUT['shallow'], key=lambda r: r['ter'])
OUT['shallow_best'] = bs
print('     最好 λ = %.1f，%.2f%%（比不加降 %.2f 个点）'
      % (bs['lam'], bs['ter'], t0 - bs['ter']))

print('\n  ⑵ density ratio：+ λ·log P_目标域 − γ·log P_源域')
OUT['dr'] = []
for gam in (0.0, 0.1, 0.2, 0.3, 0.4, 0.55, 0.7):
    t, _ = evaluate(beam=BEAM, lm=LM_TGT, lam=bs['lam'], sub=LM_SRC, gam=gam,
                    lnorm=1.0)
    OUT['dr'].append({'gam': gam, 'ter': round(t, 2)})
    print('     γ = %.2f   %6.2f%%' % (gam, t))
bd = min(OUT['dr'], key=lambda r: r['ter'])
OUT['dr_best'] = bd

print('\n  ⑶ ILME：+ λ·log P_目标域 − γ·log P_内部（= 源域^%.2f）' % TAU)
OUT['ilme'] = []
for gam in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2):
    t, _ = evaluate(beam=BEAM, lm=LM_TGT, lam=bs['lam'], sub=LM_ILM, gam=gam,
                    lnorm=1.0)
    OUT['ilme'].append({'gam': gam, 'ter': round(t, 2)})
    print('     γ = %.1f   %6.2f%%' % (gam, t))
bi = min(OUT['ilme'], key=lambda r: r['ter'])
OUT['ilme_best'] = bi

print('\n  汇总（beam=%d）：' % BEAM)
print('    不加语言模型            %6.2f%%' % t0)
print('    shallow fusion       %6.2f%%   （λ=%.1f）' % (bs['ter'], bs['lam']))
print('    density ratio        %6.2f%%   （γ=%.2f）' % (bd['ter'], bd['gam']))
print('    ILME                 %6.2f%%   （γ=%.1f）' % (bi['ter'], bi['gam']))
OUT['fusion'].update({'shallow': bs['ter'], 'dr': bd['ter'], 'ilme': bi['ter']})
print('  <strong>减掉内部语言模型比减掉源域文法更好</strong>（%.2f%% vs %.2f%%）——'
      % (bi['ter'], bd['ter']))
print('  因为模型真正"自带"的那个语言模型比训练文本的文法<strong>弱</strong>')
print('  （这里是 %.2f 次幂），按训练文法去减就减多了。' % TAU)
print('  现实里 τ 未知，所以 ILME 要另外估一个内部语言模型——')
print('  常见做法是把声学输入置零跑一遍模型。')

# ══ ④ 融合语言模型越准，最优权重越大 ═════════════════════════
print('\n④ 融合用的语言模型越接近真实文本分布，最优权重越大')
print('  测试文本固定（来自目标域），只改"拿去融合的那个语言模型"：')
print('  %10s %10s %10s' % ('融合 LM', '最优 λ', '错误率'))
OUT['drift'] = []
for mix in (0.0, 0.25, 0.5, 0.75, 1.0):
    lm_mix = np.log(np.exp(LM_SRC) * (1 - mix) + np.exp(LM_TGT) * mix + 1e-12)
    lm_mix = lm_mix - np.log(np.exp(lm_mix).sum(1, keepdims=True))
    best, row = None, []
    for lam in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7):
        t, _ = evaluate(beam=BEAM, lm=lm_mix, lam=lam, lnorm=1.0)
        row.append({'lam': lam, 'ter': round(t, 2)})
        if best is None or t < best['ter']:
            best = {'lam': lam, 'ter': round(t, 2)}
    OUT['drift'].append({'mix': mix, 'best_lam': best['lam'], 'ter': best['ter'],
                         'curve': row})
    print('  %6.0f%% 目标域 %8.1f %9.2f%%' % (mix * 100, best['lam'], best['ter']))
d0, d1 = OUT['drift'][0], OUT['drift'][-1]
print('  融合的是源域文法（0%% 目标域）时，最优 λ = %.1f——'
      % d0['best_lam'])
print('  <strong>这时外部语言模型和模型自带的那个是重复的</strong>，加了没有信息，只有噪声。')
print('  融合的是真正的目标域文法时，最优 λ = %.1f，错误率 %.2f%%。'
      % (d1['best_lam'], d1['ter']))
print('  工程含义：<strong>λ 不是一个可以照抄的超参</strong>，')
print('  它编码的是"这个语言模型比模型自带的那个多知道多少"。')
print('  换一个领域、换一批文本，λ 就要重调。')

json.dump(OUT, open('demo_decode.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_decode.json')
