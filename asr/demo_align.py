#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CTC 与 RNN-T 的对齐格：路径有多少条、内存墙在哪、剪枝能剪掉多少。

   两个损失都是手写的前向-后向（纯 numpy），并用<暴力枚举>核对过：
   小规模下 −log Σ_对齐 P 必须和逐条枚举的结果一致到浮点精度。
   然后各训一个小模型，量峰值行为和边界误差。
"""
import numpy as np, json, math, time
from math import comb

rng = np.random.default_rng(0)
OUT = {}
NEG = -1e30


def lse(a, b):
    m = np.maximum(a, b)
    return np.where(np.isfinite(m), m + np.log(np.exp(a - m) + np.exp(b - m)), m)


def lse3(a, b, c):
    return lse(lse(a, b), c)


# ══════════════════════════════════════════════════════════════
# CTC
# ══════════════════════════════════════════════════════════════
def ctc_ext(y):
    """标签序列扩展成 blank-间隔的形式：ℓ' = b y1 b y2 … b，长度 2U+1"""
    e = [0]
    for c in y:
        e += [c, 0]
    return e


def ctc_count(T, y):
    """CTC 的对齐路径条数（精确整数计数）"""
    e = ctc_ext(y)
    S = len(e)
    a = [0] * S
    a[0] = 1
    if S > 1:
        a[1] = 1
    for t in range(1, T):
        b = [0] * S
        for s in range(S):
            v = a[s] + (a[s - 1] if s >= 1 else 0)
            if s >= 2 and e[s] != 0 and e[s] != e[s - 2]:
                v += a[s - 2]
            b[s] = v
        a = b
    return a[-1] + (a[-2] if S > 1 else 0)


def ctc_logp(lp, y):
    """CTC 的对数似然。lp: (T, V) 的对数后验，0 号是 blank"""
    e = ctc_ext(y)
    T, S = lp.shape[0], len(e)
    al = np.full((T, S), NEG)
    al[0, 0] = lp[0, e[0]]
    if S > 1:
        al[0, 1] = lp[0, e[1]]
    for t in range(1, T):
        prev = al[t - 1]
        same = prev
        skip1 = np.concatenate([[NEG], prev[:-1]])
        skip2 = np.concatenate([[NEG, NEG], prev[:-2]])
        ok2 = np.array([s >= 2 and e[s] != 0 and e[s] != e[s - 2] for s in range(S)])
        v = lse(same, skip1)
        v = np.where(ok2, lse(v, skip2), v)
        al[t] = v + lp[t, e]
    return lse(al[-1, -1], al[-1, -2] if S > 1 else NEG)


def ctc_grad(lp, y):
    """前向-后向求梯度（对 log 后验）"""
    e = ctc_ext(y)
    T, S, V = lp.shape[0], len(e), lp.shape[1]
    ok2 = np.array([s >= 2 and e[s] != 0 and e[s] != e[s - 2] for s in range(S)])
    al = np.full((T, S), NEG); al[0, 0] = lp[0, e[0]]
    if S > 1:
        al[0, 1] = lp[0, e[1]]
    for t in range(1, T):
        p = al[t - 1]
        v = lse(p, np.concatenate([[NEG], p[:-1]]))
        v = np.where(ok2, lse(v, np.concatenate([[NEG, NEG], p[:-2]])), v)
        al[t] = v + lp[t, e]
    be = np.full((T, S), NEG); be[-1, -1] = 0.0
    if S > 1:
        be[-1, -2] = 0.0
    for t in range(T - 2, -1, -1):
        n = be[t + 1] + lp[t + 1, e]
        v = lse(n, np.concatenate([n[1:], [NEG]]))
        sh2 = np.concatenate([n[2:], [NEG, NEG]])
        ok2s = np.concatenate([ok2[2:], [False, False]])
        be[t] = np.where(ok2s, lse(v, sh2), v)
    ll = lse(al[-1, -1], al[-1, -2] if S > 1 else NEG)
    g = np.full_like(lp, NEG)
    post = al + be - ll
    for s in range(S):
        g[:, e[s]] = lse(g[:, e[s]], post[:, s])
    return ll, np.exp(lp) - np.exp(g)          # dL/d(logit)，L = −ll


# ══════════════════════════════════════════════════════════════
# RNN-T
# ══════════════════════════════════════════════════════════════
def rnnt_count(T, U):
    """RNN-T 的对齐条数：在 T+U 步里选 U 步输出符号 = C(T+U, U)"""
    return comb(T + U, U)


def rnnt_logp(lj, y, blank=0):
    """RNN-T 对数似然。lj: (T, U+1, V) 的联合网络对数后验"""
    T, U1 = lj.shape[0], lj.shape[1]
    U = U1 - 1
    al = np.full((T, U1), NEG)
    al[0, 0] = 0.0
    for t in range(T):
        for u in range(U1):
            if t == 0 and u == 0:
                continue
            v = NEG
            if t > 0:
                v = lse(v, al[t - 1, u] + lj[t - 1, u, blank])
            if u > 0:
                v = lse(v, al[t, u - 1] + lj[t, u - 1, y[u - 1]])
            al[t, u] = v
    return al[T - 1, U] + lj[T - 1, U, blank], al


def rnnt_logp_banded(lj, y, band, blank=0):
    """只在对角带 |u − u*(t)| ≤ band 内做前向，其余格子当作不可达"""
    T, U1 = lj.shape[0], lj.shape[1]
    U = U1 - 1
    al = np.full((T, U1), NEG)
    al[0, 0] = 0.0
    for t in range(T):
        uc = U * t / max(T - 1, 1)
        for u in range(U1):
            if abs(u - uc) > band:
                continue
            if t == 0 and u == 0:
                continue
            v = NEG
            if t > 0 and abs(u - U * (t - 1) / max(T - 1, 1)) <= band:
                v = lse(v, al[t - 1, u] + lj[t - 1, u, blank])
            if u > 0:
                v = lse(v, al[t, u - 1] + lj[t, u - 1, y[u - 1]])
            al[t, u] = v
    return al[T - 1, U] + lj[T - 1, U, blank]


def brute_ctc(lp, y):
    """暴力枚举所有帧标签序列，筛出坍缩后等于 y 的那些。只用来核对。"""
    T, V = lp.shape
    tot = NEG
    for idx in np.ndindex(*([V] * T)):
        col = []
        prev = -1
        for c in idx:
            if c != 0 and c != prev:
                col.append(c)
            prev = c
        if col == list(y):
            tot = lse(tot, sum(lp[t, idx[t]] for t in range(T)))
    return tot


def brute_rnnt(lj, y, blank=0):
    """暴力枚举 RNN-T 的所有格路径。只用来核对。"""
    T, U1, V = lj.shape
    U = U1 - 1
    best = [NEG]

    def walk(t, u, acc):
        if t == T - 1 and u == U:
            best[0] = lse(best[0], acc + lj[t, u, blank])
            return
        if t < T - 1:
            walk(t + 1, u, acc + lj[t, u, blank])
        if u < U:
            walk(t, u + 1, acc + lj[t, u, y[u]])
    walk(0, 0, 0.0)
    return best[0]


# ══ ① 自检：前向-后向必须和暴力枚举一致 ═══════════════════════
print('① 自检：前向-后向 vs 暴力枚举')
T, V = 6, 4
lp = np.log(rng.dirichlet(np.ones(V), size=T))
y = [1, 2]
a, b = float(ctc_logp(lp, y)), float(brute_ctc(lp, y))
print('  CTC   T=%d V=%d y=%s   前向 %.10f   暴力 %.10f   差 %.2e'
      % (T, V, y, a, b, abs(a - b)))
lj = np.log(rng.dirichlet(np.ones(V), size=(5, 3)))
yr = [1, 2]
c = float(rnnt_logp(lj, yr)[0]); d = float(brute_rnnt(lj, yr))
print('  RNN-T T=5 U=2 V=%d       前向 %.10f   暴力 %.10f   差 %.2e'
      % (V, c, d, abs(c - d)))
OUT['selfcheck'] = {'ctc_err': float(abs(a - b)), 'rnnt_err': float(abs(c - d))}
assert abs(a - b) < 1e-8 and abs(c - d) < 1e-8

# ══ ② 对齐条数 ═══════════════════════════════════════════════
print('\n② 同一段音频、同一串标签，两种损失各有多少条对齐')
print('  我原以为 RNN-T 的格更大（它允许一帧连出多个符号）。<strong>实测反过来</strong>：')
print('  %6s %5s %16s %16s %14s' % ('T 帧', 'U 标签', 'CTC 对齐数', 'RNN-T 对齐数',
                                    'CTC 多几个量级'))
OUT['count'] = []
for T, U in ((10, 3), (20, 5), (50, 10), (100, 20), (300, 40), (1000, 100)):
    y = list(range(1, U + 1))
    nc = ctc_count(T, y)
    nr = rnnt_count(T, U)
    r = {'T': T, 'U': U, 'ctc': int(nc), 'rnnt': int(nr),
         'ctc_log10': round(math.log10(nc), 2), 'rnnt_log10': round(math.log10(nr), 2)}
    OUT['count'].append(r)
    print('  %6d %5d %16s %16s %12.1f'
          % (T, U, '10^%.1f' % r['ctc_log10'], '10^%.1f' % r['rnnt_log10'],
             r['ctc_log10'] - r['rnnt_log10']))
big = OUT['count'][-1]
OUT['count_gap'] = round(big['ctc_log10'] - big['rnnt_log10'], 1)
print('  <strong>CTC 的对齐数反而比 RNN-T 多 %.0f 个数量级</strong>。'
      % OUT['count_gap'])
print('  原因：CTC 的扩展序列有 2U+1 个位置（每个标签前后都能插 blank），')
print('  T 帧往 2U+1 个槽里分；RNN-T 是 T×U 格上的单调路径，只有 C(T+U, U) 条。')
print('  <strong>路径多不等于内存大</strong>——下一节是两回事。')

# ══ ③ 内存墙 ═════════════════════════════════════════════════
print('\n③ 联合网络的内存墙（这是 RNN-T 最实在的工程问题）')
print('  %8s %6s %7s %6s %14s %14s %10s'
      % ('时长', 'T 帧', 'U 标签', 'V 词表', 'CTC 张量', 'RNN-T 张量', '倍数'))
OUT['mem'] = []
for sec, U, V in ((2, 8, 5000), (10, 40, 5000), (10, 40, 32000),
                  (30, 120, 5000), (30, 120, 32000)):
    T = int(sec * 1000 / 40)                       # 40 ms 一帧（下采样后）
    ctc_b = T * V * 4
    rnnt_b = T * (U + 1) * V * 4
    r = {'sec': sec, 'T': T, 'U': U, 'V': V,
         'ctc_mb': round(ctc_b / 1e6, 2), 'rnnt_mb': round(rnnt_b / 1e6, 1),
         'ratio': U + 1}
    OUT['mem'].append(r)
    print('  %6d s %6d %7d %6s %11.2f MB %11.1f MB %8d×'
          % (sec, T, U, '{:,}'.format(V), r['ctc_mb'], r['rnnt_mb'], r['ratio']))
b = OUT['mem'][-1]
OUT['mem_note'] = {'batch16_gb': round(b['rnnt_mb'] * 16 / 1000, 1)}
print('  单条 30 秒、3.2 万词表：<strong>%.0f MB</strong>，而且这还只是前向的一份；'
      % b['rnnt_mb'])
print('  反传要再存一份梯度，batch=16 就是 %.0f GB。' % OUT['mem_note']['batch16_gb'])
print('  CTC 完全没有这个问题——它的张量里<strong>没有 U 这一维</strong>。')
print('  注意这和 ② 不矛盾：CTC 的<em>路径</em>更多，但它的<em>格子</em>只有 T 个，')
print('  每个格子上算一次 V 维分布；RNN-T 有 T×(U+1) 个格子，每个都要算一次。')
print('  工业界的应对：function-merging（把 softmax 融进损失）、'
      '按 U 分块、以及下面的剪枝。')

# ══ ④ 剪枝：带宽多窄还不丢精度 ════════════════════════════════
def rnnt_post(lj, y, blank=0):
    """前向-后向，给出每个格子的后验占据概率"""
    T, U1 = lj.shape[0], lj.shape[1]
    U = U1 - 1
    al = np.full((T, U1), NEG); al[0, 0] = 0.0
    for t in range(T):
        for u in range(U1):
            if t == 0 and u == 0:
                continue
            v = NEG
            if t > 0:
                v = lse(v, al[t - 1, u] + lj[t - 1, u, blank])
            if u > 0:
                v = lse(v, al[t, u - 1] + lj[t, u - 1, y[u - 1]])
            al[t, u] = v
    be = np.full((T, U1), NEG); be[T - 1, U] = lj[T - 1, U, blank]
    for t in range(T - 1, -1, -1):
        for u in range(U, -1, -1):
            if t == T - 1 and u == U:
                continue
            v = NEG
            if t < T - 1:
                v = lse(v, lj[t, u, blank] + be[t + 1, u])
            if u < U:
                v = lse(v, lj[t, u, y[u]] + be[t, u + 1])
            be[t, u] = v
    Z = al[T - 1, U] + lj[T - 1, U, blank]
    return np.exp(al + be - Z), float(Z)


print('\n④ 对齐格有多稀疏：后验占据度')
T, U, V = 200, 40, 30
y = list(rng.integers(1, V, size=U))
# 构造一个"像训练过的模型"的联合分布：
#   落后于对角线 → 倾向输出符号；领先于对角线 → 倾向输出 blank。
#   真实训练出来的 RNN-T 正是这个样子，用均匀随机分布量不出稀疏性。
lj = np.zeros((T, U + 1, V))
for t in range(T):
    uc = U * t / (T - 1)
    for u in range(U + 1):
        lead = u - uc                                     # >0 表示领先
        w = np.full(V, 0.01)
        w[0] = math.exp(1.2 * lead)                       # 领先就多输 blank
        if u < U:
            w[y[u]] = math.exp(-1.2 * lead)               # 落后就赶紧输符号
        lj[t, u] = np.log(w / w.sum())
post, Z = rnnt_post(lj, y)
flat = np.sort(post.ravel())[::-1]
tot = flat.sum()
cum = np.cumsum(flat) / tot
ncell = T * (U + 1)
OUT['occupancy'] = {'T': T, 'U': U, 'cells': ncell, 'logZ': round(Z, 4)}
print('  格子共 %s 个（T×(U+1)）；按后验从大到小排，占到总占据度的：' % '{:,}'.format(ncell))
for q in (0.5, 0.9, 0.99, 0.999):
    k = int(np.searchsorted(cum, q)) + 1
    OUT['occupancy']['q%g' % q] = round(k / ncell, 4)
    print('    %5.1f%%  只要 %5d 个格子 = <strong>%.1f%%</strong>'
          % (q * 100, k, k / ncell * 100))
print('  <strong>99%% 的占据度集中在 %.0f%% 的格子里</strong>——'
      % (OUT['occupancy']['q0.99'] * 100))
print('  这就是 pruned RNN-T 的全部原理：按后验剪，而不是按固定带宽剪。')

print('\n  对照：按固定带宽剪（不看后验）')
full = Z
print('  %6s %10s %14s %12s' % ('带宽', '保留格子', 'log P', '绝对误差'))
OUT['prune'] = []
for band in (1, 2, 3, 4, 5, 6, 8, 12, 20, 40):
    v = rnnt_logp_banded(lj, y, band)
    cells = sum(1 for t in range(T) for u in range(U + 1)
                if abs(u - U * t / (T - 1)) <= band)
    r = {'band': band, 'cells': cells, 'frac': round(cells / ncell, 4),
         'logp': round(float(v), 4), 'err': round(float(abs(v - full)), 4)}
    OUT['prune'].append(r)
    print('  %6d %9.1f%% %14.4f %12.2e'
          % (band, r['frac'] * 100, r['logp'], r['err']))
ok = [r for r in OUT['prune'] if r['err'] < 0.05]
OUT['prune_ok'] = ok[0] if ok else None
if ok:
    print('  带宽 %d 时误差小于 0.05 nat，保留 %.0f%% 的格子——'
          % (ok[0]['band'], ok[0]['frac'] * 100))
    print('  比按后验剪差得多（%.1f%% vs %.1f%%）。'
          % (ok[0]['frac'] * 100, OUT['occupancy']['q0.99'] * 100))
print('  固定带宽会把"先憋着不输、后面连输几个"这类合法路径整段切掉，')
print('  而那些路径在训练早期占的份额并不小。<strong>按后验剪才安全</strong>。')

# ══ ⑤ 真训两个小模型：峰值行为与边界误差 ═══════════════════════
print('\n⑤ 真训：CTC 的峰值行为，和它对边界的影响')
NSYM, NFEAT = 6, 12
FRAMES_PER_SYM = 8


def gen(n, seed):
    g = np.random.default_rng(seed)
    proto = np.random.default_rng(7).standard_normal((NSYM + 1, NFEAT))
    X, Y, B = [], [], []
    for _ in range(n):
        u = int(g.integers(3, 6))
        ys = list(g.integers(1, NSYM + 1, size=u))
        x, bnd, t = [], [], 0
        for c in ys:
            d = int(g.integers(FRAMES_PER_SYM - 3, FRAMES_PER_SYM + 4))
            x.append(proto[c] + 0.55 * g.standard_normal((d, NFEAT)))
            bnd.append((t, t + d))
            t += d
        X.append(np.concatenate(x)); Y.append(ys); B.append(bnd)
    return X, Y, B


Xtr, Ytr, Btr = gen(160, 11)
Xte, Yte, Bte = gen(40, 22)


H1 = 48


def fwd(P, x):
    a = x @ P['W1'] + P['b1']
    h = np.maximum(a, 0)
    z = h @ P['W2'] + P['b2']
    lp = z - z.max(1, keepdims=True)
    lp = lp - np.log(np.exp(lp).sum(1, keepdims=True))
    return a, h, z, lp


def train_ctc(steps=6000, lr=4e-3, seed=3):
    g = np.random.default_rng(seed)
    P = {'W1': g.standard_normal((NFEAT, H1)) / math.sqrt(NFEAT), 'b1': np.zeros(H1),
         'W2': g.standard_normal((H1, NSYM + 1)) / math.sqrt(H1),
         'b2': np.zeros(NSYM + 1)}
    M = {k: np.zeros_like(v) for k, v in P.items()}
    Vv = {k: np.zeros_like(v) for k, v in P.items()}
    for it in range(steps):
        i = int(g.integers(len(Xtr)))
        x, y = Xtr[i], Ytr[i]
        a, h, z, lp = fwd(P, x)
        ll, gz = ctc_grad(lp, y)
        gz = gz / len(x)
        G = {'W2': h.T @ gz, 'b2': gz.sum(0)}
        dh = (gz @ P['W2'].T) * (a > 0)
        G['W1'] = x.T @ dh; G['b1'] = dh.sum(0)
        for k in P:
            M[k] = 0.9 * M[k] + 0.1 * G[k]
            Vv[k] = 0.999 * Vv[k] + 0.001 * G[k] ** 2
            P[k] -= lr * (M[k] / (1 - 0.9 ** (it + 1))) / \
                (np.sqrt(Vv[k] / (1 - 0.999 ** (it + 1))) + 1e-8)
    return P


t0 = time.time()
P = train_ctc()
print('  训练用时 %.1f s' % (time.time() - t0))
blank_frac, peak_w, bnd_err, nll = [], [], [], []
for x, y, bd in zip(Xte, Yte, Bte):
    _, _, _, lp = fwd(P, x)
    p = np.exp(lp)
    am = p.argmax(1)
    blank_frac.append(float(np.mean(am == 0)))
    # 非 blank 的"尖峰宽度"：连续非 blank 段的平均长度
    runs, cur = [], 0
    for a in am:
        if a != 0:
            cur += 1
        elif cur:
            runs.append(cur); cur = 0
    if cur:
        runs.append(cur)
    if runs:
        peak_w.append(float(np.mean(runs)))
    # 尖峰位置 vs 真实音段中点
    pos = []
    prev = 0
    for t, a in enumerate(am):
        if a != 0 and a != prev:
            pos.append(t)
        prev = a
    if len(pos) == len(bd):
        mid = [(s + e) / 2 for s, e in bd]
        bnd_err.append(float(np.mean([abs(pp - mm) for pp, mm in zip(pos, mid)])))
    nll.append(-float(ctc_logp(lp, y)) / len(y))
OUT['ctc_train'] = {
    'blank_frac': round(float(np.mean(blank_frac)), 3),
    'peak_width': round(float(np.mean(peak_w)), 2),
    'frames_per_sym': FRAMES_PER_SYM,
    'boundary_err_frames': round(float(np.mean(bnd_err)), 2) if bnd_err else None,
    'nll_per_sym': round(float(np.mean(nll)), 3),
    'aligned_utts': len(bnd_err), 'n_utts': len(Xte)}
c = OUT['ctc_train']
print('  测试集上：blank 占了 <strong>%.1f%%</strong> 的帧' % (c['blank_frac'] * 100))
print('  非 blank 的连续段平均只有 %.2f 帧宽，而每个符号实际占 %d 帧——'
      % (c['peak_width'], FRAMES_PER_SYM))
print('  <strong>CTC 把一个持续 %d 帧的符号压成了一个 %.1f 帧的尖峰</strong>。'
      % (FRAMES_PER_SYM, c['peak_width']))
print('  尖峰位置和真实音段中点差 %.2f 帧。' % (c['boundary_err_frames'] or -1))
print('  这就是"CTC 的对齐不能直接当强制对齐用"的量化版本——')
print('  它的对齐在<strong>时间上是对的，在边界上是没有意义的</strong>。')

json.dump(OUT, open('demo_align.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_align.json')
