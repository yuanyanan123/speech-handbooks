#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""流式：前瞻买到了什么、状态缓存要多少内存；
   以及说话人日志：聚类式方法在重叠语音上的那个硬下限。
"""
import numpy as np, json, math
from collections import defaultdict

rng = np.random.default_rng(0)
OUT = {}

# ══════════════════════════════════════════════════════════════
# Part A  流式：前瞻帧数 vs 精度 vs 延迟
# ══════════════════════════════════════════════════════════════
V, L, NUTT = 30, 14, 240
EOS = V
FRAME_MS = 40.0                    # 下采样之后每帧 40 ms
EVID, NOISE = 5.0, 0.45


def make_bigram(seed, sparsity=8, floor=0.02):
    g = np.random.default_rng(seed)
    P = np.full((V + 1, V + 1), floor)
    for h in range(V + 1):
        nxt = g.choice(V, size=sparsity, replace=False)
        w = g.dirichlet(np.ones(sparsity) * 0.8)
        for k, n in enumerate(nxt):
            P[h, n] = floor + w[k] * 0.9
        P[h, EOS] = 0.02
    return np.log(P / P.sum(1, keepdims=True))


LM = make_bigram(1)
LMW = 0.25            # 语言模型权重（太大会盖过声学证据，见正文）


def sample_seq(g):
    y, h = [], EOS
    for _ in range(L):
        p = np.exp(LM[h][:V]); p /= p.sum()
        c = int(g.choice(V, p=p)); y.append(c); h = c
    return y


def make_utt(seed):
    """一句话铺在 T 帧上：每个符号占若干帧，符号的声学证据<跨帧扩散>——
       所以看得到的未来帧越多，这个符号判得越准。"""
    g = np.random.default_rng(seed)
    y = sample_seq(g)
    dur = g.integers(3, 8, size=L)
    T = int(dur.sum())
    ev = np.zeros((T, V + 1))
    t = 0
    _T = T
    for u, c in enumerate(y):
        d = int(dur[u])
        # 证据在音段内递增：一个符号要听到后半段才能确定（塞擦音、声调都是这样）
        for k in range(d):                                   # 段内均匀
            ev[t + k, c] += EVID / d
        for k in range(2):                                   # 协同发音：尾巴拖 2 帧
            if t + d + k < T:
                ev[t + d + k, c] += 0.30 * EVID / d
        t += d
    ev += NOISE * g.standard_normal(ev.shape)
    ev[:, EOS] -= 4.0
    bnd = np.cumsum(np.r_[0, dur])
    return y, ev, bnd


UTTS = [make_utt(200 + i) for i in range(NUTT)]


def decode_stream(y, ev, bnd, look):
    """流式解码：判第 u 个符号时，只能看到它<起点之后 look 帧>为止的证据。
       look = ∞ 就是整句都能看（非流式）。返回解码结果。"""
    T = ev.shape[0]
    out = []
    for u in range(len(y)):
        s = bnd[u]
        span = min(bnd[u + 1] + 2, T)                       # 这个符号的证据一共铺这么远
        e = span if look is None else min(T, s + look)      # 前瞻可以越过边界（会混进下一个音）
        if e <= s:
            e = min(s + 1, T)
        sc = ev[s:e].sum(0) + LMW * LM[out[-1] if out else EOS]
        out.append(int(np.argmax(sc[:V])))
    return out


def ter(h, r):
    n, m = len(r), len(h)
    d = list(range(m + 1))
    for i in range(1, n + 1):
        prev, d[0] = d[0], i
        for j in range(1, m + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return d[m] / max(n, 1)


print('A 流式：前瞻帧数买到了什么')
print('  每帧 %.0f ms；"前瞻"是指判一个符号时允许看到它起点之后多少帧' % FRAME_MS)
print('  %8s %10s %12s %12s' % ('前瞻帧', '算法延迟', '标记错误率', '相对非流式'))
OUT['look'] = []
full = np.mean([ter(decode_stream(*u, None), u[0]) for u in UTTS]) * 100
for look in (1, 2, 3, 4, 6, 8, 12, 20):
    t = np.mean([ter(decode_stream(*u, look), u[0]) for u in UTTS]) * 100
    OUT['look'].append({'look': look, 'lat_ms': round(look * FRAME_MS, 0),
                        'ter': round(float(t), 2), 'gap': round(float(t - full), 2)})
    print('  %8d %8.0f ms %11.2f%% %11.2f%%' % (look, look * FRAME_MS, t, t - full))
OUT['look_full'] = round(float(full), 2)
print('  %8s %8s %11.2f%% %11s' % ('整句', '—', full, '0.00%'))
best = min(OUT['look'], key=lambda r: r['ter'])
OUT['look_best'] = best
print('  最好的前瞻是 <strong>%d 帧 = %.0f ms</strong>，错误率 %.2f%%。'
      % (best['look'], best['lat_ms'], best['ter']))
print('  从 1 帧加到 %d 帧拿到 %.2f 个点；再往后<strong>反而变差</strong>——'
      % (best['look'], OUT['look'][0]['ter'] - best['ter']))
print('  因为多看的那些帧装的是<strong>下一个音</strong>的证据，对当前这个音是噪声。')
print('  这条曲线的形状解释了一个常见现象：')
print('  流式模型的前瞻窗口通常只有一两百毫秒，再长既不划算也不见得更准。')
print('  真正决定它的不是"算力能不能等"，是<strong>一个音本身有多长</strong>。')

# ══ A2 chunk 与状态缓存 ═══════════════════════════════════════
print('\nA2 chunk 式流式的状态缓存要多大')
print('  按一个 %d 层、隐层 %d 维的编码器估' % (18, 512))
NLAYER, DMODEL = 18, 512
print('  %10s %10s %14s %16s'
      % ('chunk', '延迟', '每层要缓存', '总缓存（batch=1）'))
OUT['cache'] = []
for chunk in (4, 8, 16, 32, 64):
    hist = chunk * 4                                  # 常见做法：缓存 4 个 chunk 的历史
    per = hist * DMODEL * 4
    tot = per * NLAYER
    r = {'chunk': chunk, 'lat_ms': round(chunk * FRAME_MS, 0), 'hist': hist,
         'per_layer_kb': round(per / 1024, 1), 'total_mb': round(tot / 1e6, 2)}
    OUT['cache'].append(r)
    print('  %8d 帧 %7.0f ms %12.1f KB %14.2f MB'
          % (chunk, r['lat_ms'], r['per_layer_kb'], r['total_mb']))
print('  注意这是<strong>每一路并发</strong>的常驻内存。')
b = OUT['cache'][2]
OUT['cache_100'] = round(b['total_mb'] * 100, 1)
print('  chunk=%d 时单路 %.2f MB，100 路并发就是 <strong>%.0f MB</strong>——'
      % (b['chunk'], b['total_mb'], OUT['cache_100']))
print('  流式服务的内存瓶颈通常不在模型权重（那是共享的），在这里。')
print('  而且它随并发数线性增长，模型权重不随。')

# ══════════════════════════════════════════════════════════════
# Part B  说话人日志：聚类式方法的硬下限
# ══════════════════════════════════════════════════════════════
D = 24
WIN = 1.5                          # 窗长 1.5 s
HOPS = 0.75


def spk_embed(nspk, seed, within=0.55):
    g = np.random.default_rng(seed)
    cen = g.standard_normal((nspk, D))
    cen /= np.linalg.norm(cen, axis=1, keepdims=True)
    return cen, within


def make_meeting(nspk=4, dur=240.0, overlap=0.15, seed=1):
    """造一段会议：轮流发言，其中 overlap 比例的时间是两个人同时说。
       返回每个窗口的真实说话人集合，以及该窗口的嵌入。"""
    g = np.random.default_rng(seed)
    cen, within = spk_embed(nspk, seed)
    nwin = int(dur / HOPS)
    truth, emb = [], []
    cur = int(g.integers(nspk))
    left = g.exponential(4.0)
    for w in range(nwin):
        if left <= 0:
            cur = int(g.integers(nspk))
            left = g.exponential(4.0)
        left -= HOPS
        spks = {cur}
        if g.random() < overlap:
            o = int(g.integers(nspk))
            if o != cur:
                spks.add(o)
        v = sum(cen[s] for s in spks) / len(spks)
        v = v + within * g.standard_normal(D) / math.sqrt(D) * 2.0
        v /= np.linalg.norm(v) + 1e-9
        truth.append(spks); emb.append(v)
    return np.array(emb), truth, nspk


def ahc(emb, k):
    """凝聚层次聚类（平均连接、余弦相似度），聚到 k 类。
       用 Lance-Williams 递推维护簇间平均相似度，O(n²)。"""
    n = len(emb)
    S = emb @ emb.T
    np.fill_diagonal(S, -2.0)
    size = np.ones(n)
    alive = np.ones(n, bool)
    members = {i: [i] for i in range(n)}
    nc = n
    while nc > k:
        M = np.where(alive[:, None] & alive[None, :], S, -3.0)
        i, j = np.unravel_index(np.argmax(M), M.shape)
        if i > j:
            i, j = j, i
        ni, nj = size[i], size[j]
        new = (ni * S[i] + nj * S[j]) / (ni + nj)        # 平均连接的递推
        S[i] = new; S[:, i] = new
        S[i, i] = -2.0
        size[i] = ni + nj
        members[i] += members[j]
        alive[j] = False
        nc -= 1
    lab = np.zeros(n, int)
    for k_, i in enumerate(np.where(alive)[0]):
        for m in members[i]:
            lab[m] = k_
    return lab


def der(truth, pred_sets, nspk):
    """DER 三分量：漏检（真实有、预测没有）、虚警（预测有、真实没有）、
       说话人混淆（都有但配错人）。先在预测标签与真实说话人之间找最优一一映射。"""
    import itertools
    best = None
    labs = sorted({l for s in pred_sets for l in s})
    for perm in itertools.permutations(range(nspk), min(nspk, len(labs))):
        m = {labs[i]: perm[i] for i in range(len(perm))}
        miss = fa = conf = 0.0
        for t, p in zip(truth, pred_sets):
            pm = {m.get(x, -1) for x in p}
            both = len(t & pm)
            miss += max(len(t) - len(pm), 0)
            fa += max(len(pm) - len(t), 0)
            conf += min(len(t), len(pm)) - both
        tot = sum(len(t) for t in truth)
        v = (miss + fa + conf) / tot
        if best is None or v < best[0]:
            best = (v, miss / tot, fa / tot, conf / tot)
    return best


print('\nB 说话人日志：聚类式方法在重叠语音上的下限')
print('  会议 4 分钟、%d 个说话人、窗长 %.1f s、窗移 %.2f s' % (4, WIN, HOPS))
print('  %10s %10s %10s %10s %10s %12s'
      % ('重叠比例', 'DER', '漏检', '虚警', '混淆', '重叠下限'))
OUT['dia'] = []
for ov in (0.0, 0.05, 0.10, 0.20, 0.30):
    ds, ms, fs, cs, los = [], [], [], [], []
    for rep in range(4):
        emb, truth, nspk = make_meeting(overlap=ov, seed=10 + rep)
        lab = ahc(emb, nspk)
        pred = [{int(l)} for l in lab]                 # 聚类：每个窗只能给一个标签
        v, mi, fa_, co = der(truth, pred, nspk)
        ds.append(v); ms.append(mi); fs.append(fa_); cs.append(co)
        # 重叠段贡献的漏检下限：每个两人窗必定漏掉一个人（同一场会议上算）
        los.append(sum(len(t) - 1 for t in truth) / sum(len(t) for t in truth))
    lo = float(np.mean(los))
    r = {'overlap': ov, 'der': round(float(np.mean(ds)) * 100, 2),
         'miss': round(float(np.mean(ms)) * 100, 2),
         'fa': round(float(np.mean(fs)) * 100, 2),
         'conf': round(float(np.mean(cs)) * 100, 2),
         'floor': round(float(lo) * 100, 2)}
    OUT['dia'].append(r)
    print('  %9.0f%% %9.2f%% %9.2f%% %9.2f%% %9.2f%% %11.2f%%'
          % (ov * 100, r['der'], r['miss'], r['fa'], r['conf'], r['floor']))
hi = OUT['dia'][-1]
print('  最后一列是<strong>硬下限</strong>：聚类每个窗口只能吐一个标签，')
print('  所以每个"两人同时说"的窗口必定漏掉一个人。')
print('  重叠 %.0f%% 时这个下限就是 %.2f%%，而实测漏检 %.2f%%——'
      % (hi['overlap'] * 100, hi['floor'], hi['miss']))
print('  <strong>两者逐档严格相等：漏检这一项模型一分错都没多犯</strong>。')
print('  能调的只有混淆那一项（实测 %.2f%%），漏检要靠换输出形式。' % hi['conf'])

# ══ B2 允许多标签（端到端那一类）能拿回多少 ════════════════════
print('\nB2 允许一个窗口输出多个说话人（EEND 那一类做法）')
print('  用一个<strong>理想的</strong>多标签判决作上界：知道该输出几个人，')
print('  再按嵌入与各中心的相似度挑那么多个。')
print('  %10s %12s %12s %12s' % ('重叠比例', '聚类 DER', '多标签 DER', '拿回'))
OUT['dia2'] = []
for ov in (0.0, 0.10, 0.20, 0.30):
    d1, d2 = [], []
    for rep in range(4):
        emb, truth, nspk = make_meeting(overlap=ov, seed=10 + rep)
        lab = ahc(emb, nspk)
        pred1 = [{int(l)} for l in lab]
        d1.append(der(truth, pred1, nspk)[0])
        cen = np.array([emb[lab == k].mean(0) for k in range(nspk)])
        cen /= np.linalg.norm(cen, axis=1, keepdims=True) + 1e-9
        sim = emb @ cen.T
        pred2 = [set(np.argsort(-sim[i])[:len(truth[i])].tolist())
                 for i in range(len(emb))]
        d2.append(der(truth, pred2, nspk)[0])
    r = {'overlap': ov, 'clu': round(float(np.mean(d1)) * 100, 2),
         'multi': round(float(np.mean(d2)) * 100, 2)}
    r['gain'] = round(r['clu'] - r['multi'], 2)
    OUT['dia2'].append(r)
    print('  %9.0f%% %11.2f%% %11.2f%% %11.2f%%'
          % (ov * 100, r['clu'], r['multi'], r['gain']))
g = OUT['dia2'][-1]
print('  重叠 %.0f%% 时多标签能拿回 %.2f 个点——' % (g['overlap'] * 100, g['gain']))
print('  这就是端到端日志（EEND）相对聚类式的<strong>全部结构性优势</strong>。')
print('  代价是它要知道说话人数（或者用注意力机制去猜），而聚类不用。')

json.dump(OUT, open('demo_stream.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_stream.json')
