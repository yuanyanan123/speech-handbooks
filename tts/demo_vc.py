#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""31 节算例：语音转换——"把内容和说话人拆开"这件事，瓶颈开多大才拆得开。

   同一套"说话人 × 内容"梅尔谱（20 节那套，不带房间）。真值是现成的：
   同一段内容、换成目标说话人，就是转换的标准答案（生成器是确定的）。

   模型：帧级自编码器——编码器 80→128→k（线性瓶颈），解码器 [k 维编码 ‖ 说话人嵌入]→128→80，
   纯 numpy、手写反传，用重建误差训练，20 个说话人 × 6 条 × 10 s。
   扫瓶颈维数 k：
     ① 编码里还剩多少说话人信息、多少内容信息（线性探针，留出的语音）
     ② 转换（A 的内容 + B 的嵌入）：输出像不像 B、还像不像 A、内容丢了没有、离标准答案多远
   没有对抗训练、没有说话人归一化，只有"瓶颈"这一个旋钮——这是最朴素的一种解耦。
"""
import json, time
import numpy as np

t0 = time.time()
OUT = {}
NMEL, FPS = 80, 86.13
MHZ = 2595 * np.log10(1 + (np.arange(NMEL) / NMEL * 8000) / 700)
NSPK, NTR, NTE = 20, 6, 3
FRAMES = 860
g0 = np.random.default_rng(5)
VTL = g0.uniform(0.86, 1.16, NSPK)
F0C = g0.uniform(95, 205, NSPK)
TILT = g0.uniform(-0.45, 0.45, NSPK)
PHSET = np.array([[730, 1090, 2440], [270, 2290, 3010], [300, 870, 2240],
                  [530, 1840, 2480], [660, 1720, 2410], [490, 1350, 1690],
                  [400, 1900, 2600], [600, 1000, 2500]], float)


def make_mel(spk, utt, frames=FRAMES):
    r = np.random.default_rng(10000 + utt * 97)
    seq = r.integers(0, len(PHSET), frames // 9 + 1)
    dur = r.integers(6, 13, len(seq))
    tgt = np.repeat(PHSET[seq], dur, axis=0)[:frames]
    lab = np.repeat(seq, dur)[:frames]
    if len(tgt) < frames:
        tgt = np.vstack([tgt, np.repeat(tgt[-1:], frames - len(tgt), axis=0)])
        lab = np.concatenate([lab, np.repeat(lab[-1:], frames - len(lab))])
    k = np.exp(-0.5 * (np.arange(-6, 7) / 2.4) ** 2)
    k /= k.sum()
    tgt = np.stack([np.convolve(tgt[:, i], k, 'same') for i in range(3)], 1) * VTL[spk]
    m = np.zeros((NMEL, frames))
    for i in range(3):
        c = 2595 * np.log10(1 + tgt[:, i] / 700)
        m += (0.86 ** i) * np.exp(-0.5 * ((MHZ[:, None] - c[None, :]) / 88) ** 2)
    m += 0.04 * np.exp(-MHZ[:, None] / (700 + 3 * F0C[spk]))
    lm = np.log(m + 1e-3) + TILT[spk] * (MHZ[:, None] / MHZ[-1] - 0.5)
    return lm.T, lab                                    # (frames, 80)


# ── 数据 ──
TR = {(s, u): make_mel(s, u) for s in range(NSPK) for u in range(NTR)}
TE = {(s, u): make_mel(s, 100 + u) for s in range(NSPK) for u in range(NTE)}
Xtr = np.concatenate([TR[(s, u)][0] for s in range(NSPK) for u in range(NTR)])
Str = np.concatenate([np.full(FRAMES, s) for s in range(NSPK) for u in range(NTR)])
Ytr = np.concatenate([TR[(s, u)][1] for s in range(NSPK) for u in range(NTR)])
MU, SD = Xtr.mean(0), Xtr.std(0) + 1e-6
nrm = lambda X: (X - MU) / SD


class Net:
    def __init__(self, k, seed, emb=8, h=128):
        g = np.random.default_rng(seed)
        self.k, self.emb = k, emb
        i = lambda a, b: g.standard_normal((a, b)) * np.sqrt(2.0 / a)
        self.W = [i(NMEL, h), i(h, k), i(k + emb, h), i(h, NMEL)]
        self.b = [np.zeros(h), np.zeros(k), np.zeros(h), np.zeros(NMEL)]
        self.E = g.standard_normal((NSPK, emb)) * 0.5

    def enc(self, X):
        a = np.maximum(X @ self.W[0] + self.b[0], 0)
        return a @ self.W[1] + self.b[1], a

    def dec(self, z, spk):
        inp = np.concatenate([z, self.E[spk]], 1)
        a = np.maximum(inp @ self.W[2] + self.b[2], 0)
        return a @ self.W[3] + self.b[3], a, inp

    def fit(self, X, S, epochs=30, bs=256, lr=2e-3, seed=0):
        g = np.random.default_rng(seed)
        params = self.W + self.b + [self.E]
        m = [np.zeros_like(p) for p in params]
        v = [np.zeros_like(p) for p in params]
        t = 0
        n = len(X)
        for ep in range(epochs):
            perm = g.permutation(n)
            for st in range(0, n, bs):
                idx = perm[st:st + bs]
                x, s = X[idx], S[idx]
                z, a1 = self.enc(x)
                y, a2, inp = self.dec(z, s)
                d = 2 * (y - x) / len(idx)
                gW3 = a2.T @ d
                gb3 = d.sum(0)
                da2 = (d @ self.W[3].T) * (a2 > 0)
                gW2 = inp.T @ da2
                gb2 = da2.sum(0)
                dinp = da2 @ self.W[2].T
                dz, dE = dinp[:, :self.k], dinp[:, self.k:]
                gW1 = a1.T @ dz
                gb1 = dz.sum(0)
                da1 = (dz @ self.W[1].T) * (a1 > 0)
                gW0 = x.T @ da1
                gb0 = da1.sum(0)
                gE = np.zeros_like(self.E)
                np.add.at(gE, s, dE)
                grads = [gW0, gW1, gW2, gW3, gb0, gb1, gb2, gb3, gE]
                t += 1
                for j, (p, gr) in enumerate(zip(params, grads)):
                    m[j] = 0.9 * m[j] + 0.1 * gr
                    v[j] = 0.999 * v[j] + 0.001 * gr * gr
                    p -= lr * (m[j] / (1 - 0.9 ** t)) / (np.sqrt(v[j] / (1 - 0.999 ** t)) + 1e-8)
        return self


def softmax_probe(X, y, ncls, epochs=40, lr=0.05, seed=0, l2=1e-3):
    """多类逻辑回归（线性探针），全批量 Adam"""
    g = np.random.default_rng(seed)
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xn = (X - mu) / sd
    W = np.zeros((X.shape[1], ncls))
    b = np.zeros(ncls)
    mW = np.zeros_like(W); vW = np.zeros_like(W); mb = np.zeros_like(b); vb = np.zeros_like(b)
    n = len(X)
    for ep in range(1, epochs + 1):
        perm = g.permutation(n)
        for st in range(0, n, 2048):
            idx = perm[st:st + 2048]
            z = Xn[idx] @ W + b
            z -= z.max(1, keepdims=True)
            p = np.exp(z); p /= p.sum(1, keepdims=True)
            p[np.arange(len(idx)), y[idx]] -= 1
            p /= len(idx)
            gW = Xn[idx].T @ p + l2 * W
            gb = p.sum(0)
            for (M, V, P_, G_) in ((mW, vW, W, gW), (mb, vb, b, gb)):
                M *= 0.9; M += 0.1 * G_
                V *= 0.999; V += 0.001 * G_ * G_
                P_ -= lr * (M / (1 - 0.9 ** ep)) / (np.sqrt(V / (1 - 0.999 ** ep)) + 1e-8)
    return lambda Z: np.argmax(((Z - mu) / sd) @ W + b, 1)


# 在真实梅尔帧上训的探针：谁在说 / 说的是什么——用来评判转换后的输出
SPK_PROBE = softmax_probe(nrm(Xtr), Str, NSPK, epochs=25)
PH_PROBE = softmax_probe(nrm(Xtr), Ytr, len(PHSET), epochs=25)
Xte = np.concatenate([TE[(s, u)][0] for s in range(NSPK) for u in range(NTE)])
Ste = np.concatenate([np.full(FRAMES, s) for s in range(NSPK) for u in range(NTE)])
Yte = np.concatenate([TE[(s, u)][1] for s in range(NSPK) for u in range(NTE)])
OUT['probe_real'] = {'spk': round(100 * float(np.mean(SPK_PROBE(nrm(Xte)) == Ste)), 1),
                     'ph': round(100 * float(np.mean(PH_PROBE(nrm(Xte)) == Yte)), 1)}
print('探针在真实留出帧上：说话人 %.1f%%，音素 %.1f%%（说话人随机 %.1f%%，音素随机 %.1f%%）'
      % (OUT['probe_real']['spk'], OUT['probe_real']['ph'], 100 / NSPK, 100 / len(PHSET)))

KS = (1, 2, 3, 4, 6, 8, 16, 32)
SEEDS = (0, 1)
OUT['rows'] = []
for K_ in KS:
    acc = {'recon': [], 'code_spk': [], 'code_ph': [], 'tgt_hit': [], 'src_keep': [], 'ph_keep': [], 'conv_mse': [], 'copy_mse': []}
    for sd in SEEDS:
        net = Net(K_, sd).fit(nrm(Xtr), Str, epochs=30, seed=sd)
        # 重建
        Z, _ = net.enc(nrm(Xte))
        Y, _, _ = net.dec(Z, Ste)
        acc['recon'].append(float(np.mean((Y - nrm(Xte)) ** 2)))
        # 编码里的信息（探针在训练编码上训、在留出编码上测）
        Ztr, _ = net.enc(nrm(Xtr))
        acc['code_spk'].append(float(np.mean(softmax_probe(Ztr, Str, NSPK, epochs=25)(Z) == Ste)))
        acc['code_ph'].append(float(np.mean(softmax_probe(Ztr, Ytr, len(PHSET), epochs=25)(Z) == Yte)))
        # 转换：每个源说话人，随机一个目标说话人，同一条内容
        g = np.random.default_rng(100 + sd)
        hit = keep = phk = cm = cp = 0.0
        npair = 0
        for s in range(NSPK):
            tgt = int((s + 1 + g.integers(NSPK - 1)) % NSPK)
            for u in range(NTE):
                Xs, lab = TE[(s, u)]
                Xt, _ = TE[(tgt, u)]                       # 标准答案：同一内容，目标说话人
                z, _ = net.enc(nrm(Xs))
                y, _, _ = net.dec(z, np.full(len(z), tgt))
                ym = y * SD + MU
                hit += np.mean(SPK_PROBE(nrm(ym)) == tgt)
                keep += np.mean(SPK_PROBE(nrm(ym)) == s)
                phk += np.mean(PH_PROBE(nrm(ym)) == lab)
                cm += np.mean((ym - Xt) ** 2)
                cp += np.mean((Xs - Xt) ** 2)
                npair += 1
        acc['tgt_hit'].append(hit / npair); acc['src_keep'].append(keep / npair); acc['ph_keep'].append(phk / npair)
        acc['conv_mse'].append(cm / npair); acc['copy_mse'].append(cp / npair)
    r = {'k': K_}
    for key, v in acc.items():
        r[key] = round(float(np.mean(v)), 4)
    OUT['rows'].append(r)
    print('  k=%2d  重建 %.3f | 编码里：说话人 %5.1f%% 音素 %5.1f%% | 转换：像目标 %5.1f%% 仍像源 %5.1f%% 内容保持 %5.1f%% 离答案 %.3f（直接拷贝源 %.3f）'
          % (K_, r['recon'], 100 * r['code_spk'], 100 * r['code_ph'], 100 * r['tgt_hit'], 100 * r['src_keep'],
             100 * r['ph_keep'], r['conv_mse'], r['copy_mse']))

R = {r['k']: r for r in OUT['rows']}
best = max(OUT['rows'], key=lambda r: r['tgt_hit'] * r['ph_keep'])
OUT['note'] = {
    'k1_ph': round(100 * R[1]['code_ph'], 1), 'k1_spk': round(100 * R[1]['code_spk'], 1),
    'k32_spk': round(100 * R[32]['code_spk'], 1), 'k32_hit': round(100 * R[32]['tgt_hit'], 1),
    'k32_keep': round(100 * R[32]['src_keep'], 1), 'k32_ph': round(100 * R[32]['ph_keep'], 1),
    'k2_hit': round(100 * R[2]['tgt_hit'], 1), 'k2_ph': round(100 * R[2]['ph_keep'], 1),
    'k4_hit': round(100 * R[4]['tgt_hit'], 1), 'k4_ph': round(100 * R[4]['ph_keep'], 1), 'k4_spk': round(100 * R[4]['code_spk'], 1),
    'k8_hit': round(100 * R[8]['tgt_hit'], 1), 'k8_ph': round(100 * R[8]['ph_keep'], 1), 'k8_spk': round(100 * R[8]['code_spk'], 1),
    'k16_hit': round(100 * R[16]['tgt_hit'], 1), 'k16_spk': round(100 * R[16]['code_spk'], 1),
    'best_k': best['k'], 'best_hit': round(100 * best['tgt_hit'], 1), 'best_ph': round(100 * best['ph_keep'], 1),
    'copy_mse': R[4]['copy_mse'], 'best_mse': best['conv_mse'], 'k32_mse': R[32]['conv_mse'],
    'chance_spk': round(100 / NSPK, 1), 'chance_ph': round(100 / len(PHSET), 1),
    'probe_spk': OUT['probe_real']['spk'], 'probe_ph': OUT['probe_real']['ph'],
    'k1_mse': R[1]['conv_mse'],
}
OUT['const'] = {'nspk': NSPK, 'ntr': NTR, 'nte': NTE, 'frames': FRAMES, 'sec': round(FRAMES / FPS, 1), 'seeds': list(SEEDS),
                'ks': list(KS), 'hidden': 128, 'emb': 8, 'epochs': 30}
OUT['runtime_s'] = round(time.time() - t0, 1)
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_vc.json', 'w'), ensure_ascii=False)
print('写出 demo_vc.json  %.1f s' % OUT['runtime_s'])
