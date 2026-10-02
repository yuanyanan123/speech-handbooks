# -*- coding: utf-8 -*-
"""6–8 节与 19 节：识别与语言模型公式的数值检验（HMM 前向/Viterbi/EM、CTC 前向与梯度、RNN-T 格子、注意力缩放、Kneser–Ney、GMM-EM、LPC、MLPG）。"""
import itertools
import numpy as np
from scipy import optimize
from common import check, rng


# ── HMM ───────────────────────────────────────────────────────────
def hmm_forward(pi, A, B, obs):
    T = len(obs); N = len(pi)
    al = np.zeros((T, N)); al[0] = pi * B[:, obs[0]]
    for t in range(1, T):
        al[t] = (al[t - 1] @ A) * B[:, obs[t]]
    return al


def hmm_backward(A, B, obs):
    T = len(obs); N = A.shape[0]
    be = np.ones((T, N))
    for t in range(T - 2, -1, -1):
        be[t] = A @ (B[:, obs[t + 1]] * be[t + 1])
    return be


def hmm_brute(pi, A, B, obs):
    N, T = len(pi), len(obs)
    tot, best, bp = 0.0, -1.0, None
    for path in itertools.product(range(N), repeat=T):
        p = pi[path[0]] * B[path[0], obs[0]]
        for t in range(1, T):
            p *= A[path[t - 1], path[t]] * B[path[t], obs[t]]
        tot += p
        if p > best:
            best, bp = p, path
    return tot, best, bp


def viterbi(pi, A, B, obs):
    T, N = len(obs), len(pi)
    de = np.zeros((T, N)); ps = np.zeros((T, N), int)
    de[0] = pi * B[:, obs[0]]
    for t in range(1, T):
        cand = de[t - 1][:, None] * A
        ps[t] = np.argmax(cand, 0); de[t] = cand.max(0) * B[:, obs[t]]
    path = [int(np.argmax(de[-1]))]
    for t in range(T - 1, 0, -1):
        path.append(int(ps[t, path[-1]]))
    return de[-1].max(), tuple(path[::-1])


# ── CTC ───────────────────────────────────────────────────────────
def collapse(path):
    out, prev = [], None
    for c in path:
        if c != prev and c != 0:
            out.append(c)
        prev = c
    return tuple(out)


def ctc_ab(Y, labels):
    """Y: (T,V) softmax 输出，空白=0。返回 α、β（都含当帧发射）与 P。"""
    T = Y.shape[0]
    ext = [0]
    for c in labels:
        ext += [c, 0]
    S = len(ext)
    al = np.zeros((T, S)); be = np.zeros((T, S))
    al[0, 0] = Y[0, 0]
    if S > 1:
        al[0, 1] = Y[0, ext[1]]
    for t in range(1, T):
        for s in range(S):
            v = al[t - 1, s] + (al[t - 1, s - 1] if s >= 1 else 0)
            if s >= 2 and ext[s] != 0 and ext[s] != ext[s - 2]:
                v += al[t - 1, s - 2]
            al[t, s] = v * Y[t, ext[s]]
    be[T - 1, S - 1] = Y[T - 1, 0]
    if S > 1:
        be[T - 1, S - 2] = Y[T - 1, ext[S - 2]]
    for t in range(T - 2, -1, -1):
        for s in range(S):
            v = be[t + 1, s] + (be[t + 1, s + 1] if s + 1 < S else 0)
            if s + 2 < S and ext[s + 2] != 0 and ext[s + 2] != ext[s]:
                v += be[t + 1, s + 2]
            be[t, s] = v * Y[t, ext[s]]
    P = al[-1, -1] + (al[-1, -2] if S > 1 else 0)
    return al, be, P, ext


def softmax(U):
    E = np.exp(U - U.max(1, keepdims=True))
    return E / E.sum(1, keepdims=True)


def ctc_paths_dp(T, labels):
    Y = np.ones((T, max(labels) + 1))
    return ctc_ab(Y, labels)[2]


# ── RNN-T ─────────────────────────────────────────────────────────
def rnnt_alpha(bl, lab, T, U):
    al = np.zeros((T + 1, U + 1)); al[0, 0] = 1.0
    for t in range(T + 1):
        for u in range(U + 1):
            if t == 0 and u == 0:
                continue
            v = 0.0
            if t >= 1:
                v += al[t - 1, u] * bl[t - 1, u]
            if u >= 1:
                v += al[t, u - 1] * lab[t, u - 1]
            al[t, u] = v
    return al[T, U] * bl[T, U]


def rnnt_brute(bl, lab, T, U):
    tot = 0.0
    def go(t, u, p):
        nonlocal tot
        if t == T and u == U:
            tot += p * bl[t, u]; return
        if t < T:
            go(t + 1, u, p * bl[t, u])
        if u < U:
            go(t, u + 1, p * lab[t, u])
    go(0, 0, 1.0)
    return tot


def run():
    g = rng(21)
    # ① HMM：前向 = 暴力枚举；Viterbi = 最优路径；α·β 的和与 t 无关；EM 似然单调不降
    N, K, T = 3, 3, 6
    pi = g.dirichlet(np.ones(N)); A = g.dirichlet(np.ones(N), N); B = g.dirichlet(np.ones(K), N)
    obs = list(g.integers(0, K, T))
    tot, best, bp = hmm_brute(pi, A, B, obs)
    al = hmm_forward(pi, A, B, obs); be = hmm_backward(A, B, obs)
    check('D1', '7', 'hmm', 'HMM 前向总概率 vs 暴力枚举', tot, al[-1].sum(), 1e-12)
    vb, vp = viterbi(pi, A, B, obs)
    check('D1', '7', 'hmm', 'Viterbi 最优路径概率 vs 暴力枚举', best, vb, 1e-12)
    check('D1', '7', 'hmm', 'Viterbi 路径与暴力最优路径一致（1=是）', 1.0, 1.0 if tuple(vp) == tuple(bp) else 0.0, 0.0)
    sums = [np.sum(al[t] * be[t]) for t in range(T)]
    check('D1', '19', 'bw_hmm', 'Σᵢαₜ(i)βₜ(i) 与 t 无关（最大偏差）', 0.0, max(abs(np.array(sums) - tot)), 1e-12)
    # Baum–Welch
    pi_, A_, B_ = g.dirichlet(np.ones(N)), g.dirichlet(np.ones(N), N), g.dirichlet(np.ones(K), N)
    obs2 = list(g.integers(0, K, 60))
    lls = []
    for it in range(40):
        a = hmm_forward(pi_, A_, B_, obs2); b = hmm_backward(A_, B_, obs2); P = a[-1].sum(); lls.append(np.log(P))
        gam = a * b / P
        xi = np.zeros((len(obs2) - 1, N, N))
        for t in range(len(obs2) - 1):
            xi[t] = a[t][:, None] * A_ * (B_[:, obs2[t + 1]] * b[t + 1])[None, :] / P
        check_gamma = np.max(np.abs(gam.sum(1) - 1))
        pi_ = gam[0]; A_ = xi.sum(0) / gam[:-1].sum(0)[:, None]
        B_ = np.stack([np.array([gam[np.array(obs2) == k, i].sum() for k in range(K)]) / gam[:, i].sum() for i in range(N)])
    check('D2', '19', 'bw_hmm', 'Baum–Welch：γ 逐帧和为 1（最大偏差）', 0.0, check_gamma, 1e-12)
    check('D2', '19', 'bw_hmm', 'Baum–Welch：对数似然单调不降（最小增量）', 0.0, min(np.diff(lls)), 1e-9, kind='ge')

    # ② CTC：前向 = 暴力枚举；梯度公式 = 数值梯度；路径数 DP = 暴力
    V, T = 4, 7
    labels = [1, 2, 2]
    U = g.standard_normal((T, V))
    Y = softmax(U)
    al, be, P, ext = ctc_ab(Y, labels)
    brute = 0.0
    for path in itertools.product(range(V), repeat=T):
        if collapse(path) == tuple(labels):
            brute += np.prod([Y[t, path[t]] for t in range(T)])
    check('D3', '7', 'ctc', 'CTC 前向 P(y|x) vs 暴力枚举所有路径', brute, P, 1e-12)
    # 任意 t：P = Σ_s α_t(s)β_t(s)/y_t(l'_s)
    t0 = 3
    P2 = sum(al[t0, s] * be[t0, s] / Y[t0, ext[s]] for s in range(len(ext)))
    check('D3', '19', 'ctc_grad', 'P = Σₛ αₜ(s)βₜ(s)/yₜ(l′ₛ)', P, P2, 1e-12)
    grad = np.zeros_like(U)
    for t in range(T):
        for k in range(V):
            ssum = sum(al[t, s] * be[t, s] for s in range(len(ext)) if ext[s] == k)
            grad[t, k] = Y[t, k] - ssum / (Y[t, k] * P)
    num = np.zeros_like(U); eps = 1e-6
    def Lval(Uv):
        return -np.log(ctc_ab(softmax(Uv), labels)[2])
    for t in range(T):
        for k in range(V):
            Up = U.copy(); Up[t, k] += eps; Um = U.copy(); Um[t, k] -= eps
            num[t, k] = (Lval(Up) - Lval(Um)) / (2 * eps)
    check('D3', '19', 'ctc_grad', 'CTC 梯度公式 vs 数值梯度（最大偏差）', 0.0, np.max(np.abs(grad - num)), 1e-6)
    # 路径数
    Tq, lab = 7, [1, 2, 2]
    bc = sum(1 for path in itertools.product(range(3), repeat=Tq) if collapse(path) == tuple(lab))
    check('D3', '21', 'ctc', '映射到标签的路径数：递推 vs 暴力', bc, ctc_paths_dp(Tq, lab), 0.0)

    # ③ RNN-T：α 递推 = 暴力枚举所有格子路径
    Tt, Uu, Vv = 4, 3, 5
    raw = g.dirichlet(np.ones(Vv), size=(Tt + 1, Uu + 1))        # 每个格点一个 softmax：空白 + 4 个标签
    bl = raw[:, :, 0]
    labs = [1, 2, 3]
    lab = np.zeros((Tt + 1, Uu + 1))
    for u in range(Uu):
        lab[:, u] = raw[:, u, labs[u]]
    check('D4', '7', 'rnnt', 'RNN-T 格子递推 vs 暴力枚举路径', rnnt_brute(bl, lab, Tt, Uu), rnnt_alpha(bl, lab, Tt, Uu), 1e-12)

    # ④ 注意力：Var(qᵀk)=d_k；缩放后方差为 1；未缩放时 softmax 饱和；雅可比公式
    for dk in (16, 64, 256):
        q = g.standard_normal((200000, dk)); k = g.standard_normal((200000, dk))
        v = np.sum(q * k, 1)
        check('D5', '19', 'softmaxj', 'Var(qᵀk) @d_k=%d' % dk, dk, np.var(v), 0.03, kind='rel')
        check('D5', '19', 'softmaxj', '除以 √d_k 后的方差 @d_k=%d' % dk, 1.0, np.var(v / np.sqrt(dk)), 0.03, kind='rel')
    dk, nk = 256, 32
    Q = g.standard_normal((4000, dk)); Kk = g.standard_normal((4000, nk, dk))
    z = np.einsum('bd,bnd->bn', Q, Kk)
    mx_un = np.mean(softmax(z).max(1)); mx_sc = np.mean(softmax(z / np.sqrt(dk)).max(1))
    check('D5', '19', 'softmaxj', '未缩放时 softmax 最大概率（d_k=256, 32 个键）≥ 0.9', 0.9, mx_un, 0.0, kind='ge')
    check('D5', '19', 'softmaxj', '缩放后 softmax 最大概率 ≤ 0.5', 0.5, mx_sc, 0.0, kind='le')
    z0 = g.standard_normal(6); s0 = np.exp(z0) / np.exp(z0).sum()
    Jn = np.zeros((6, 6))
    for j in range(6):
        zp = z0.copy(); zp[j] += 1e-6; zm = z0.copy(); zm[j] -= 1e-6
        Jn[:, j] = (np.exp(zp) / np.exp(zp).sum() - np.exp(zm) / np.exp(zm).sum()) / 2e-6
    Jf = np.diag(s0) - np.outer(s0, s0)
    check('D5', '19', 'softmaxj', 'softmax 雅可比 sᵢ(δᵢⱼ−sⱼ) vs 数值', 0.0, np.max(np.abs(Jn - Jf)), 1e-8)

    # ⑤ Kneser–Ney：二元概率归一；续接概率与词频的区别
    corpus = []
    for _ in range(150):
        corpus += ['san', 'francisco']
    words = ['the', 'a', 'dog', 'cat', 'ran', 'saw', 'big', 'red']
    g2 = rng(5)
    for _ in range(300):
        corpus += [words[g2.integers(0, 8)] for _ in range(2)]
    vocab = sorted(set(corpus))
    from collections import Counter, defaultdict
    bi = Counter(zip(corpus[:-1], corpus[1:])); c1 = Counter(corpus[:-1])
    n1p_v = defaultdict(int); n1p_w = defaultdict(int)
    for (v_, w_), c in bi.items():
        n1p_v[v_] += 1; n1p_w[w_] += 1
    tot_types = len(bi); d = 0.75
    def pkn(w_, v_):
        return max(bi[(v_, w_)] - d, 0) / c1[v_] + d * n1p_v[v_] / c1[v_] * (n1p_w[w_] / tot_types)
    ms = max(abs(sum(pkn(w_, v_) for w_ in vocab) - 1.0) for v_ in vocab if c1[v_] > 0)
    check('D6', '8', 'kn', 'Kneser–Ney 二元分布归一（最大偏差）', 0.0, ms, 1e-9)
    uni = Counter(corpus)
    check('D6', '8', 'kn', '"francisco" 的续接概率 < "dog"（虽然它频次更高，1=是）', 1.0, 1.0 if (uni['francisco'] > uni['dog'] and n1p_w['francisco'] / tot_types < n1p_w['dog'] / tot_types) else 0.0, 0.0)

    # ⑥ GMM-EM 对数似然单调不降
    x = np.concatenate([g.normal(-2, 0.7, 400), g.normal(1.5, 1.0, 600)])
    mu = np.array([-0.5, 0.5]); sd = np.array([1.0, 1.0]); c = np.array([0.5, 0.5]); ll = []
    for _ in range(50):
        pdf = c * np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        ll.append(np.sum(np.log(pdf.sum(1)))); gm = pdf / pdf.sum(1, keepdims=True)
        mu = gm.T @ x / gm.sum(0); sd = np.sqrt((gm * (x[:, None] - mu) ** 2).sum(0) / gm.sum(0)); c = gm.mean(0)
    check('D7', '7', 'gmm', 'GMM-EM 对数似然单调不降（最小增量）', 0.0, min(np.diff(ll)), 1e-9, kind='ge')
    check('D7', '7', 'gmm', 'GMM-EM 恢复均值（真值 −2、1.5）', 0.0, max(abs(np.sort(mu) - np.array([-2, 1.5]))), 0.15)

    # ⑦ LPC（Yule–Walker）恢复 AR(2) 系数
    a1, a2 = 1.2, -0.6
    n = 200000
    e = g.standard_normal(n); xs = np.zeros(n)
    for i in range(2, n):
        xs[i] = a1 * xs[i - 1] + a2 * xs[i - 2] + e[i]
    r = np.array([np.mean(xs[k:] * xs[:n - k]) for k in range(3)])
    R = np.array([[r[0], r[1]], [r[1], r[0]]])
    a_est = np.linalg.solve(R, r[1:3])
    check('D8', '6', 'lpc', 'Yule–Walker 估计的 AR(2) 系数（最大偏差）', 0.0, np.max(np.abs(a_est - np.array([a1, a2]))), 0.02)

    # ⑧ MLPG：闭式解 = 数值最优
    Tn = 10
    Wm = np.zeros((2 * Tn, Tn))
    for t in range(Tn):
        Wm[2 * t, t] = 1.0
        Wm[2 * t + 1, min(t + 1, Tn - 1)] += 0.5; Wm[2 * t + 1, max(t - 1, 0)] -= 0.5
    mu_o = g.standard_normal(2 * Tn); Sg = np.diag(g.uniform(0.2, 2.0, 2 * Tn))
    Si = np.linalg.inv(Sg)
    c_cf = np.linalg.solve(Wm.T @ Si @ Wm, Wm.T @ Si @ mu_o)
    f = lambda c_: 0.5 * (Wm @ c_ - mu_o) @ Si @ (Wm @ c_ - mu_o)
    c_num = optimize.minimize(f, np.zeros(Tn), method='BFGS', options={'gtol': 1e-10}).x
    check('D9', '11', 'mlpg', 'MLPG 闭式解 vs 数值最优（最大偏差）', 0.0, np.max(np.abs(c_cf - c_num)), 1e-5)

    # ⑨ 编辑距离 DP = 暴力递归
    def lev(a, b):
        if not a: return len(b)
        if not b: return len(a)
        return min(lev(a[1:], b) + 1, lev(a, b[1:]) + 1, lev(a[1:], b[1:]) + (a[0] != b[0]))
    ok = True
    for _ in range(30):
        ra = list(g.integers(0, 4, g.integers(1, 7))); hb = list(g.integers(0, 4, g.integers(1, 7)))
        D = np.zeros((len(ra) + 1, len(hb) + 1)); D[:, 0] = range(len(ra) + 1); D[0, :] = range(len(hb) + 1)
        for i in range(1, len(ra) + 1):
            for j in range(1, len(hb) + 1):
                D[i, j] = min(D[i - 1, j - 1] + (ra[i - 1] != hb[j - 1]), D[i - 1, j] + 1, D[i, j - 1] + 1)
        ok &= (D[-1, -1] == lev(ra, hb))
    check('D10', '7', 'wer', '编辑距离 DP vs 暴力递归（30 组随机序列，1=全部一致）', 1.0, 1.0 if ok else 0.0, 0.0)


if __name__ == '__main__':
    import common
    run()
    for r in common.ROWS:
        print(r['id'], r['what'], r['pred'], r['sim'], r['dev'], '✓' if r['ok'] else '✗')
