#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""21 节：温度、top-p 与重复惩罚，到底各自在修什么。

做法：
  ① 造一个"真实过程"——音素序列 + 每个音素的时长分布 + 每个音素的发声 token 分布。
     它是一个 (音素, 已停留帧数) 上的 HMM，所以任何前缀下的
     真实下一 token 分布都能用前向算法精确算出来（= 完美校准的参考）。
  ② 从它采一批序列，训一个小的自回归模型（看前 k 个 token，纯 numpy + Adam）。
  ③ 用不同温度 / top-p / 重复惩罚去采样，量四件事：
       复读率、越界率（采到真实概率极低的 token）、多样性、时长保真度。
"""
import json, math
import numpy as np

rng = np.random.default_rng(7)
OUT = {}

# ══ ① 真实过程 ═══════════════════════════════════════════════
V = 24                      # token 词表
EOS = V                     # 结束符
PH = [0, 1, 2, 3, 4, 5]     # 一句话的音素序列（固定文本）
MEAN_D = [6, 10, 7, 12, 8, 9]
DMAX = 26
SD_FRAC = 0.25

# 每个音素的发声分布：4 个 token，且相邻音素共享 token（这才有歧义）
EMIT = np.zeros((len(PH), V + 1))
for u in PH:
    base = (u * 3) % V
    for j, p in enumerate((0.45, 0.25, 0.18, 0.12)):
        EMIT[u, (base + j) % V] += p
EMIT /= EMIT.sum(1, keepdims=True)

# 时长 pmf → 危险率 a(u,d) = P(第 d 帧后离开 | 已待了 d 帧)
DUR = np.zeros((len(PH), DMAX + 1))
for u in PH:
    m, s = MEAN_D[u], MEAN_D[u] * SD_FRAC
    d = np.arange(1, DMAX + 1)
    w = np.exp(-0.5 * ((d - m) / s) ** 2)
    DUR[u, 1:] = w / w.sum()
HAZ = np.zeros((len(PH), DMAX + 1))
for u in PH:
    tail = DUR[u, ::-1].cumsum()[::-1]          # P(D >= d)
    for d in range(1, DMAX + 1):
        HAZ[u, d] = DUR[u, d] / tail[d] if tail[d] > 1e-12 else 1.0

NSTATE = len(PH) * DMAX + 1                      # (u,d) 加一个终止态
TERM = NSTATE - 1


def sid(u, d):
    return u * DMAX + (d - 1)


# 状态转移矩阵与状态发声矩阵，建一次就够
TMAT = np.zeros((NSTATE, NSTATE))
ESTATE = np.zeros((NSTATE, V + 1))
for u in PH:
    for d in range(1, DMAX + 1):
        s0 = sid(u, d)
        ESTATE[s0] = EMIT[u]
        h = HAZ[u, d]
        if d < DMAX:
            TMAT[s0, sid(u, d + 1)] = 1 - h
        if u + 1 < len(PH):
            TMAT[s0, sid(u + 1, 1)] = h
        else:
            TMAT[s0, TERM] = h
ESTATE[TERM] = 0.0
A0 = np.zeros(NSTATE)
A0[sid(0, 1)] = 1.0


class Fwd:
    """增量前向：喂一个 token 更新一次，随时可以问"下一 token 的真实分布" """

    def __init__(self):
        self.a = A0.copy()
        self.dead = False

    def next_dist(self):
        if self.dead:
            return None
        p = self.a @ ESTATE
        p[EOS] += self.a[TERM]
        z = p.sum()
        return None if z <= 0 else p / z

    def feed(self, tok):
        if self.dead:
            return
        b = (self.a * ESTATE[:, tok]) @ TMAT
        z = b.sum()
        if z <= 0:
            self.dead = True
        else:
            self.a = b / z


def true_sample(n):
    """从真实过程采 n 条 token 序列"""
    seqs = []
    for _ in range(n):
        s = []
        for u in PH:
            d = int(rng.choice(np.arange(1, DMAX + 1), p=DUR[u, 1:]))
            for _ in range(d):
                s.append(int(rng.choice(V + 1, p=EMIT[u])))
        s.append(EOS)
        seqs.append(s)
    return seqs


# ══ ② 训一个小的自回归模型 ═══════════════════════════════════
K = 4                                            # 看前 K 个 token
H = 96
NSTEP = 5000
PAD = V + 1                                      # 起始填充
D_IN = (V + 2) * K


def onehot(idx):
    z = np.zeros((len(idx), D_IN))
    for j in range(K):
        z[np.arange(len(idx)), j * (V + 2) + idx[:, j]] = 1.0
    return z


def make_data(seqs):
    X, Y = [], []
    for sq in seqs:
        hist = [PAD] * K
        for tok in sq:
            X.append(list(hist))
            Y.append(tok)
            hist = hist[1:] + [tok]
    return np.array(X), np.array(Y)


def train_model(nseq, seed, nstep=NSTEP):
    r = np.random.default_rng(seed)
    X, Y = make_data(true_sample(nseq))
    W1 = r.normal(0, 0.1, (D_IN, H)); b1 = np.zeros(H)
    W2 = r.normal(0, 0.1, (H, V + 1)); b2 = np.zeros(V + 1)
    par = [W1, b1, W2, b2]
    mom = [np.zeros_like(q) for q in par]
    vel = [np.zeros_like(q) for q in par]
    LR, B1, B2, EPS, BS = 4e-3, 0.9, 0.999, 1e-8, 512
    for step in range(1, nstep + 1):
        idx = r.integers(0, len(X), BS)
        z = onehot(X[idx]); y = Y[idx]
        h = np.tanh(z @ par[0] + par[1])
        o = h @ par[2] + par[3]
        o -= o.max(1, keepdims=True)
        pr = np.exp(o); pr /= pr.sum(1, keepdims=True)
        g = pr.copy(); g[np.arange(BS), y] -= 1.0; g /= BS
        gs = [z.T @ ((g @ par[2].T) * (1 - h ** 2)),
              ((g @ par[2].T) * (1 - h ** 2)).sum(0),
              h.T @ g, g.sum(0)]
        for k2 in range(4):
            mom[k2] = B1 * mom[k2] + (1 - B1) * gs[k2]
            vel[k2] = B2 * vel[k2] + (1 - B2) * gs[k2] ** 2
            par[k2] -= LR * (mom[k2] / (1 - B1 ** step)) / (
                np.sqrt(vel[k2] / (1 - B2 ** step)) + EPS)
    return par


NBIG, NSMALL = 3000, 120
print('① 真实过程：%d 音素、词表 %d、上下文 %d token' % (len(PH), V, K))
print('   训两个模型：数据充足 %d 句 vs 数据饥饿 %d 句' % (NBIG, NSMALL))
PAR_BIG = train_model(NBIG, 11)
PAR_SMALL = train_model(NSMALL, 12)
PAR = PAR_BIG


def model_next(hist, par=None):
    par = par or PAR
    z = onehot(np.array([hist]))
    h = np.tanh(z @ par[0] + par[1])
    o = (h @ par[2] + par[3])[0]
    o -= o.max()
    p = np.exp(o)
    return p / p.sum()


# 模型和真实分布差多少（在真实前缀上）
def calib(par, n=160):
    kls, conf, hit = [], [], []
    for sq in true_sample(n):
        hist = [PAD] * K
        f = Fwd()
        for t, tok in enumerate(sq):
            if t >= 3 and t % 5 == 0:
                q = f.next_dist()
                if q is not None:
                    pm = model_next(hist, par)
                    m = q > 1e-9
                    kls.append(float((q[m] * np.log(q[m] / np.maximum(pm[m], 1e-12))).sum()))
                    conf.append(float(pm.max()))
                    hit.append(float(q[int(pm.argmax())]))
            f.feed(tok)
            hist = hist[1:] + [tok]
    return {'kl': round(float(np.mean(kls)), 4),
            'conf': round(float(np.mean(conf)), 4),
            'true_p_of_argmax': round(float(np.mean(hit)), 4)}


OUT['calib'] = {'big': calib(PAR_BIG), 'small': calib(PAR_SMALL)}
for nm, lab in (('big', '数据充足'), ('small', '数据饥饿')):
    c = OUT['calib'][nm]
    print('   %s：KL %.4f nat，平均最高概率 %.3f，而它指的那个 token 真实概率只有 %.3f'
          % (lab, c['kl'], c['conf'], c['true_p_of_argmax']))
OUT['model_kl'] = OUT['calib']['big']['kl']

# ══ ③ 采样# ══ ③ 采样：温度 / top-p / 重复惩罚 ══════════════════════════
MAXLEN = 200
TRUE_LEN = np.array([len(s) for s in true_sample(600)])
REP_RUN = 9          # 真实过程里几乎不会出现的连续同 token 长度
LOWP = 0.02          # "越界"：真实概率低于这个值的 token


def gen(temp, topp=1.0, reppen=1.0, n=240, seed=0, par=None):
    r = np.random.default_rng(1000 + seed)
    outs = []
    for _ in range(n):
        hist = [PAD] * K
        seq = []
        counts = np.zeros(V + 1)
        for _ in range(MAXLEN):
            p = model_next(hist, par).astype(float)
            if reppen > 1.0:
                p = p / np.where(counts > 0, reppen ** counts, 1.0)
                p /= p.sum()
            if temp <= 1e-6:
                nxt = int(p.argmax())
            else:
                q = np.log(np.maximum(p, 1e-30)) / temp
                q -= q.max()
                q = np.exp(q)
                q /= q.sum()
                if topp < 1.0:
                    order = np.argsort(-q)
                    c = q[order].cumsum()
                    keep = order[:max(1, int(np.searchsorted(c, topp) + 1))]
                    m = np.zeros_like(q)
                    m[keep] = q[keep]
                    q = m / m.sum()
                nxt = int(r.choice(V + 1, p=q))
            if nxt == EOS:
                break
            seq.append(nxt)
            counts[nxt] += 1
            hist = hist[1:] + [nxt]
        outs.append(seq)
    return outs


def longest_run(s):
    best = cur = 1
    for i in range(1, len(s)):
        cur = cur + 1 if s[i] == s[i - 1] else 1
        best = max(best, cur)
    return best if s else 0


TRUE_BG = np.zeros((V + 1, V + 1))
for _sq in true_sample(800):
    for _a, _b in zip(_sq[:-1], _sq[1:]):
        TRUE_BG[_a, _b] += 1
TRUE_BG += 0.5
TRUE_BG /= TRUE_BG.sum()


def bigram_skl(outs):
    bg = np.zeros((V + 1, V + 1))
    for sq in outs:
        for a_, b_ in zip(sq[:-1], sq[1:]):
            bg[a_, b_] += 1
    bg += 0.5
    bg /= bg.sum()
    return float(((bg - TRUE_BG) * np.log(bg / TRUE_BG)).sum())


def measure(outs, tag):
    rep = np.mean([1.0 if (longest_run(s) >= REP_RUN or len(s) >= MAXLEN) else 0.0
                   for s in outs])
    # 越界率：采出来的 token 在真实分布下概率有多低
    off, tot = 0, 0
    for sq in outs[:60]:
        f = Fwd()
        for t in range(min(len(sq), 60)):
            q = f.next_dist()
            if q is None:
                n_left = min(len(sq), 60) - t
                off += n_left
                tot += n_left
                break
            tot += 1
            if q[sq[t]] < LOWP:
                off += 1
            f.feed(sq[t])
    # 多样性：两两之间同位置 token 不同的比例
    div = []
    for i in range(0, min(len(outs), 200) - 1, 2):
        a, b = outs[i], outs[i + 1]
        n = min(len(a), len(b))
        if n:
            div.append(np.mean([a[j] != b[j] for j in range(n)]))
    lens = np.array([len(s) for s in outs])
    return {'tag': tag,
            'skl': round(bigram_skl(outs), 4),
            'rep': round(float(rep) * 100, 2),
            'off': round(off / max(tot, 1) * 100, 2),
            'div': round(float(np.mean(div)) * 100, 2) if div else 0.0,
            'len_mean': round(float(lens.mean()), 1),
            'len_sd': round(float(lens.std()), 2),
            'len_bias': round(float(lens.mean() - TRUE_LEN.mean()), 1),
            'len_sd_ratio': round(float(lens.std() / TRUE_LEN.std()), 3)}


def sweep_temp(par, key, label, temps=(0.0, 0.3, 0.5, 0.7, 0.85, 1.0, 1.2, 1.5)):
    print('\n%s（真实序列：长度 %.1f ± %.1f 帧）'
          % (label, TRUE_LEN.mean(), TRUE_LEN.std()))
    print('  %6s %10s %10s %10s %12s %12s'
          % ('温度', '复读率', '越界率', '多样性', '长度均值', '二元对称KL'))
    OUT[key] = []
    for i2, T in enumerate(temps):
        r = measure(gen(T, seed=i2 + (0 if key == 'temp' else 400), par=par), '%.2f' % T)
        r['temp'] = T
        OUT[key].append(r)
        print('  %6.2f %9.1f%% %9.1f%% %9.1f%% %11.1f %11.4f'
              % (T, r['rep'], r['off'], r['div'], r['len_mean'], r['skl']))
    ok = [r for r in OUT[key] if r['rep'] < 20.0]
    best = min(ok, key=lambda r: r['skl']) if ok else OUT[key][-1]
    OUT[key + '_best'] = best
    print('  → 不崩的档里二元分布最像真实的是温度 %.2f（对称 KL %.4f，越界率 %.1f%%）'
          % (best['temp'], best['skl'], best['off']))
    return best


b_big = sweep_temp(PAR_BIG, 'temp', '② 温度扫描 · 数据充足的模型')
b_small = sweep_temp(PAR_SMALL, 'temp_small', '③ 温度扫描 · 数据饥饿的模型')

print('\n④ top-p 扫描（温度固定 1.0，两个模型各扫一遍）')
for par, key, lab in ((PAR_BIG, 'topp', '数据充足'), (PAR_SMALL, 'topp_small', '数据饥饿')):
    print('  %s' % lab)
    print('  %8s %10s %10s %10s' % ('top-p', '复读率', '越界率', '多样性'))
    OUT[key] = []
    for i2, P in enumerate((0.7, 0.8, 0.9, 0.95, 1.0)):
        r = measure(gen(1.0, topp=P, seed=50 + i2 + (0 if key == 'topp' else 200),
                        par=par), 'p=%.2f' % P)
        r['topp'] = P
        OUT[key].append(r)
        print('  %8.2f %9.1f%% %9.1f%% %9.1f%% %11.4f'
              % (P, r['rep'], r['off'], r['div'], r['skl']))
    ok = [r for r in OUT[key] if r['rep'] < 20.0]
    OUT[key + '_best'] = min(ok, key=lambda r: r['skl']) if ok else OUT[key][-1]

print('\n⑤ 重复惩罚（温度固定 0，也就是贪心，数据充足的模型）')
print('  %8s %10s %10s' % ('惩罚', '复读率', '长度均值'))
OUT['reppen'] = []
for i2, R in enumerate((1.0, 1.05, 1.1, 1.2)):
    r = measure(gen(0.0, reppen=R, n=120, seed=90 + i2), 'r=%.2f' % R)
    r['reppen'] = R
    OUT['reppen'].append(r)
    print('  %8.2f %9.1f%% %11.1f' % (R, r['rep'], r['len_mean']))

OUT['true_len'] = {'mean': round(float(TRUE_LEN.mean()), 1),
                   'sd': round(float(TRUE_LEN.std()), 2)}
OUT['setup'] = {'V': V, 'nphone': len(PH), 'K': K, 'hidden': H,
                'nbig': NBIG, 'nsmall': NSMALL, 'nstep': NSTEP,
                'rep_run': REP_RUN, 'lowp': LOWP, 'maxlen': MAXLEN}

t = {r['temp']: r for r in OUT['temp']}
ts = {r['temp']: r for r in OUT['temp_small']}
tp = {r['topp']: r for r in OUT['topp']}
tps = {r['topp']: r for r in OUT['topp_small']}
rp = {r['reppen']: r for r in OUT['reppen']}
print('\n结论（有两条是我原本猜错、被这组数据否掉的）')
print('  ① 贪心（温度 0）的复读率 %.1f%%，温度 0.7 %.1f%%，温度 1.0 %.1f%%。'
      % (t[0.0]['rep'], t[0.7]['rep'], t[1.0]['rep']))
print('     降温不是"更稳"：<strong>降到底是最不稳的一档</strong>，而且是结构性的——')
print('     贪心在稳态 token 上会停不下来，每一条都撞到长度上限。')
print('  ② 数据充足的模型，二元分布最接近真实的是温度 %.2f（对称 KL %.4f）。'
      % (b_big['temp'], b_big['skl']))
print('     它校准得好（KL %.4f nat），所以最优采样温度就该是 1.0——这一条符合预期。'
      % OUT['calib']['big']['kl'])
print('  ③ <strong>猜错的第一条</strong>：我以为把模型训成过自信，最优温度会被压到 0.7 附近。')
print('     数据饥饿的模型确实过自信（平均最高概率 %.3f，而那个 token 的真实概率只有 %.3f），'
      % (OUT['calib']['small']['conf'], OUT['calib']['small']['true_p_of_argmax']))
print('     但它的最优温度仍然是 %.2f。过自信是<strong>结构性的错模态</strong>，'
      % b_small['temp'])
print('     不是均匀地把分布削尖了——所以用一个全局温度去压它，压不回来。')
print('  ④ <strong>猜错的第二条</strong>：我以为 top-p 是比降温更便宜的旋钮。')
print('     两个模型上都不是：p=1.0 的二元对称 KL %.4f / %.4f，'
      % (tp[1.0]['skl'], tps[1.0]['skl']))
print('     p=0.9 反而是 %.4f / %.4f。<strong>截尾和降温是同一件事</strong>，'
      % (tp[0.9]['skl'], tps[0.9]['skl']))
print('     都是把概率质量往众数上挤，也就都会把分布推向退化。')
print('  ⑤ 重复惩罚才是复读的对症药，但有代价：')
for r in OUT['reppen']:
    print('     惩罚 %.2f → 复读率 %.1f%%，长度 %.1f（真实 %.1f）'
          % (r['reppen'], r['rep'], r['len_mean'], TRUE_LEN.mean()))
print('     压住复读的那一档，时长已经被压短了——它是在"扣掉已经用过的 token"，')
print('     而 TTS 里重复的 token 本来就是合法的（元音要持续好几帧）。')

json.dump(OUT, open('demo_temp.json', 'w'), ensure_ascii=False)
print('\n→ demo_temp.json')
