#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一个够用的加权有限状态转换器（WFST）实现，热带半环（min, +）。

   够用的意思是：合成、ε 过滤、加权确定化、划分最小化都是<真的>，
   不是示意——所以书里那些状态数和边数是数出来的，不是估的。

   没实现的：权重推送（因此最小化是"不推送的最小化"，
   等价状态的判据是 (输入标签, 输出标签, 权重, 目标类)）。
   OpenFst 的 minimize 会先做权重推送再最小化，收缩率比这里高一些。
"""
from collections import defaultdict, deque

EPS = 0                      # 0 号标签固定表示 ε
INF = float('inf')


class FST:
    def __init__(self, name=''):
        self.name = name
        self.arcs = defaultdict(list)          # src -> [(ilab, olab, w, dst)]
        self.start = 0
        self.final = {}                        # state -> 终止权重
        self.nstate = 0

    def add_state(self):
        s = self.nstate
        self.nstate += 1
        return s

    def add_arc(self, s, i, o, w, d):
        self.arcs[s].append((i, o, w, d))

    def set_final(self, s, w=0.0):
        self.final[s] = w

    @property
    def narc(self):
        return sum(len(v) for v in self.arcs.values())

    def reachable(self):
        """从初始态可达、且能到达某个终止态的状态集"""
        fwd, q = {self.start}, deque([self.start])
        while q:
            s = q.popleft()
            for _, _, _, d in self.arcs[s]:
                if d not in fwd:
                    fwd.add(d); q.append(d)
        back = defaultdict(list)
        for s in fwd:
            for _, _, _, d in self.arcs[s]:
                back[d].append(s)
        co = {s for s in self.final if s in fwd}
        q = deque(co)
        while q:
            s = q.popleft()
            for p in back[s]:
                if p not in co:
                    co.add(p); q.append(p)
        return co

    def trim(self):
        """去掉不可达和不能到达终止态的部分"""
        keep = self.reachable()
        if self.start not in keep:
            keep.add(self.start)
        idx = {s: i for i, s in enumerate(sorted(keep))}
        g = FST(self.name)
        g.nstate = len(idx)
        g.start = idx[self.start]
        for s in keep:
            for i, o, w, d in self.arcs[s]:
                if d in keep:
                    g.add_arc(idx[s], i, o, w, idx[d])
            if s in self.final:
                g.final[idx[s]] = self.final[s]
        return g

    def stats(self):
        return {'states': self.nstate, 'arcs': self.narc}


# ══════════════════════════════════════════════════════════════
def compose(A, B, eps_filter=True, cap=400000):
    """A ∘ B：匹配 A 的输出标签与 B 的输入标签。

       ε 过滤用 Mohri 的三态过滤器，保证每条 (ε 输出, ε 输入) 的组合
       只被计入一次——否则会产生指数多条冗余路径。
    """
    out = FST('%s∘%s' % (A.name, B.name))
    # A 的出边按输出标签建索引，B 的出边按输入标签建索引
    Aout = defaultdict(lambda: defaultdict(list))
    for s in list(A.arcs):
        for i, o, w, d in A.arcs[s]:
            Aout[s][o].append((i, o, w, d))
    Bin = defaultdict(lambda: defaultdict(list))
    for s in list(B.arcs):
        for i, o, w, d in B.arcs[s]:
            Bin[s][i].append((i, o, w, d))

    start = (A.start, B.start, 0)
    idx = {start: out.add_state()}
    q = deque([start])
    while q:
        st = q.popleft()
        a, b, f = st
        s = idx[st]
        cand = []
        # ① 正常匹配：A 的非 ε 输出 与 B 的同名输入
        for lab, alist in Aout[a].items():
            if lab == EPS:
                continue
            for ai, ao, aw, ad in alist:
                for bi, bo, bw, bd in Bin[b].get(lab, ()):
                    cand.append((ai, bo, aw + bw, (ad, bd, 0)))
        # ② A 输出 ε（A 单独走）：过滤态 0 或 1 允许，走完记为 1
        if (not eps_filter) or f in (0, 1):
            for ai, ao, aw, ad in Aout[a].get(EPS, ()):
                cand.append((ai, EPS, aw, (ad, b, 1 if eps_filter else 0)))
        # ③ B 输入 ε（B 单独走）：任意过滤态都允许，走完记为 2
        #    于是同一段 ε 只保留"A 的先走、B 的后走"这一种顺序，
        #    既不丢路径，也不产生重复路径。
        for bi, bo, bw, bd in Bin[b].get(EPS, ()):
            cand.append((EPS, bo, bw, (a, bd, 2 if eps_filter else 0)))
        for i, o, w, nxt in cand:
            if nxt not in idx:
                idx[nxt] = out.add_state()
                q.append(nxt)
                if out.nstate > cap:
                    raise MemoryError('合成超过 %d 个状态' % cap)
            out.add_arc(s, i, o, w, idx[nxt])
        if a in A.final and b in B.final:
            out.set_final(s, A.final[a] + B.final[b])
    return out.trim()


# ══════════════════════════════════════════════════════════════
def determinize(A, cap=400000, maxiter=2000000):
    """加权确定化（热带半环上的子集构造）。

       子集里每个状态带一个"剩余权重"。若 A 不是可确定化的
       （典型原因：词典里有同音词而没有加消歧符），
       子集会不断产生新的剩余权重组合而不终止——
       这里用 cap 兜住，并把它当成一个<可报告的结果>。
    """
    def norm(sub):
        m = min(w for _, w in sub)
        return tuple(sorted((s, round(w - m, 9)) for s, w in sub)), m

    out = FST('det(%s)' % A.name)
    s0, w0 = norm([(A.start, 0.0)])
    idx = {s0: out.add_state()}
    q = deque([s0])
    it = 0
    while q:
        it += 1
        if it > maxiter:
            raise MemoryError('确定化迭代超限')
        sub = q.popleft()
        s = idx[sub]
        # 按 (输入标签, 输出标签) 分组
        grp = defaultdict(list)
        for st, rw in sub:
            for i, o, w, d in A.arcs[st]:
                grp[(i, o)].append((d, rw + w))
        for (i, o), lst in grp.items():
            best = {}
            for d, w in lst:
                if d not in best or w < best[d]:
                    best[d] = w
            nxt, mw = norm(list(best.items()))
            if nxt not in idx:
                idx[nxt] = out.add_state()
                q.append(nxt)
                if out.nstate > cap:
                    raise MemoryError('确定化超过 %d 个状态' % cap)
            out.add_arc(s, i, o, mw, idx[nxt])
        fw = [rw + A.final[st] for st, rw in sub if st in A.final]
        if fw:
            out.set_final(s, min(fw))
    return out.trim()


def determinize_input(A, cap=200000, maxres=40):
    """<真正的> WFST 确定化：只在<输入>侧确定化，输出串作为残留携带。

       子集里每个元素是 (状态, 残留输出串, 残留权重)。
       每一步把所有残留串的最长公共前缀吐出去，剩下的继续背着。

       同音词而没有消歧符时，残留串会随着词数指数增长——
       子集再也合不拢，算法不终止。这不是实现问题，
       是<strong>这个转换器根本不可确定化</strong>。
    """
    def lcp(strs):
        if not strs:
            return ()
        m = min(len(x) for x in strs)
        k = 0
        while k < m and len(set(x[k] for x in strs)) == 1:
            k += 1
        return strs[0][:k]

    def norm(items):
        w0 = min(w for _, _, w in items)
        pre = lcp([r for _, r, _ in items])
        n = len(pre)
        sub = tuple(sorted((st, r[n:], round(w - w0, 9)) for st, r, w in items))
        return sub, pre, w0

    out = FST('detI(%s)' % A.name)
    sub0, pre0, w0 = norm([(A.start, (), 0.0)])
    idx = {sub0: out.add_state()}
    q = deque([sub0])
    maxlen = 0
    while q:
        sub = q.popleft()
        s = idx[sub]
        grp = defaultdict(list)
        for st, res, rw in sub:
            for i, o, w, d in A.arcs[st]:
                grp[i].append((d, res + ((o,) if o != EPS else ()), rw + w))
        for i, lst in grp.items():
            best = {}
            for d, r, w in lst:
                k = (d, r)
                if k not in best or w < best[k]:
                    best[k] = w
            items = [(d, r, w) for (d, r), w in best.items()]
            nxt, pre, mw = norm(items)
            maxlen = max(maxlen, max((len(r) for _, r, _ in nxt), default=0))
            if maxlen > maxres:
                raise MemoryError('残留输出串长到 %d 个词，子集合不拢' % maxlen)
            if nxt not in idx:
                idx[nxt] = out.add_state()
                q.append(nxt)
                if out.nstate > cap:
                    raise MemoryError('确定化超过 %d 个状态' % cap)
            # 公共前缀在这条边上吐出来（多于一个符号时串成一条链）
            if len(pre) <= 1:
                out.add_arc(s, i, pre[0] if pre else EPS, mw, idx[nxt])
            else:
                cur = s
                for k, o in enumerate(pre):
                    d2 = out.add_state() if k < len(pre) - 1 else idx[nxt]
                    out.add_arc(cur, i if k == 0 else EPS, o,
                                mw if k == 0 else 0.0, d2)
                    cur = d2
        fin = [rw + A.final[st] for st, r, rw in sub if st in A.final and not r]
        bad = [1 for st, r, rw in sub if st in A.final and r]
        if fin:
            out.set_final(s, min(fin))
        elif bad:
            # 到了终止态还背着没吐出去的输出：这条路径的输出不唯一
            fin2 = [rw + A.final[st] for st, r, rw in sub if st in A.final]
            out.set_final(s, min(fin2))
    return out.trim()


def minimize(A):
    """划分最小化（不做权重推送）。

       等价判据：两个状态的出边多重集 (输入, 输出, 权重, 目标所在类)
       完全相同，且终止权重相同。对确定化过的机器这是精确的。
    """
    sig0 = {}
    for s in range(A.nstate):
        sig0[s] = A.final.get(s, INF)
    part = {}
    for s, f in sig0.items():
        part.setdefault(f, []).append(s)
    cls = {}
    for k, (f, lst) in enumerate(sorted(part.items(), key=lambda kv: str(kv[0]))):
        for s in lst:
            cls[s] = k
    while True:
        sig = {}
        for s in range(A.nstate):
            sig[s] = (cls[s], tuple(sorted((i, o, round(w, 9), cls[d])
                                           for i, o, w, d in A.arcs[s])))
        groups = defaultdict(list)
        for s, g in sig.items():
            groups[g].append(s)
        if len(groups) == len(set(cls.values())):        # 划分不再细化
            break
        new = {}
        for k, g in enumerate(sorted(groups, key=str)):
            for s in groups[g]:
                new[s] = k
        cls = new
    out = FST('min(%s)' % A.name)
    out.nstate = max(cls.values()) + 1
    out.start = cls[A.start]
    seen = set()
    for s in range(A.nstate):
        c = cls[s]
        if c in seen:
            continue
        seen.add(c)
        for i, o, w, d in A.arcs[s]:
            out.add_arc(c, i, o, w, cls[d])
        if s in A.final:
            out.final[c] = A.final[s]
    for s in A.final:
        out.final[cls[s]] = A.final[s]
    return out.trim()


def rm_eps_output(A):
    """把输出侧的 ε 去掉（只在输出是最终符号流时用）。这里只统计代价。"""
    n = sum(1 for s in list(A.arcs) for i, o, w, d in A.arcs[s] if o == EPS)
    return n


def count_eps(A):
    ie = oe = 0
    for s in list(A.arcs):
        for i, o, w, d in A.arcs[s]:
            ie += (i == EPS)
            oe += (o == EPS)
    return {'in_eps': ie, 'out_eps': oe}
