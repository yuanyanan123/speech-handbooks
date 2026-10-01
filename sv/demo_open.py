#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""16 节：自定义唤醒词。几条注册样本够？比专训模型差多少？别人能不能唤醒？

三条曲线：
  ① 注册条数 1→10，漏唤醒怎么降（和 10 节那条声纹注册曲线放在一起看）
  ② 自定义（几条注册）vs 专训（几百人的数据）差多少
  ③ 本人注册、别人来喊——跨说话人掉多少；以及安静注册、噪声使用掉多少
"""
import json, math
import numpy as np

rng = np.random.default_rng(31)
OUT = {}

NB, FPS = 40, 100.0
MHZ = 2595 * np.log10(1 + (np.arange(NB) / NB * 8000) / 700)
NSYL, FR_PER_SYL = 4, 15
WLEN = NSYL * FR_PER_SYL
PRE = 30

PHSET = np.array([[730, 1090, 2440], [270, 2290, 3010], [300, 870, 2240],
                  [530, 1840, 2480], [660, 1720, 2410], [490, 1350, 1690],
                  [400, 1900, 2600], [600, 1000, 2500], [350, 1600, 2300],
                  [700, 1200, 2700]], float)
KEYSEQ = [1, 6, 3, 8]

NSPK = 40
VTL = rng.uniform(0.87, 1.15, NSPK)         # 声道长度：说话人之间最大的差异
RATE = rng.uniform(0.82, 1.20, NSPK)        # 习惯语速
TILT = rng.uniform(-0.35, 0.35, NSPK)       # 谱倾斜


def utter(seq, spk, seed, jit=0.32):
    """某个说话人说一串音节。说话人参数固定，句内再加一点随机"""
    r = np.random.default_rng(seed)
    tgt = []
    for u in seq:
        d = max(4, int(round(FR_PER_SYL * RATE[spk] * (1 + jit * r.normal()))))
        f = PHSET[u] * VTL[spk] * (1 + 0.04 * jit * r.normal())
        tgt += [f] * d
    tgt = np.array(tgt)
    k = np.exp(-0.5 * (np.arange(-4, 5) / 1.6) ** 2)
    k /= k.sum()
    tgt = np.stack([np.convolve(tgt[:, i], k, 'same') for i in range(3)], 1)
    S = np.zeros((NB, len(tgt)))
    for i in range(3):
        c = 2595 * np.log10(1 + tgt[:, i] / 700)
        S += (0.8 ** i) * np.exp(-0.5 * ((MHZ[:, None] - c[None, :]) / 75) ** 2)
    S += 0.02 * np.exp(-MHZ[:, None] / 900)
    S *= np.exp(TILT[spk] * (MHZ[:, None] / MHZ[-1] - 0.5))
    return S


def noise_spec(n, seed, kind='babble'):
    r = np.random.default_rng(seed)
    acc = np.zeros((NB, n))
    for _ in range(6):
        sp = int(r.integers(0, NSPK))
        seq = list(r.integers(0, len(PHSET), n // FR_PER_SYL + 2))
        s = utter(seq, sp, int(r.integers(1e9)), jit=0.7)
        acc += s[:, :n] if s.shape[1] >= n else np.pad(s, ((0, 0), (0, n - s.shape[1])))
    return acc / 6


def mix(S, N, snr_db):
    g = S.mean() / (N.mean() * 10 ** (snr_db / 10) + 1e-20)
    return S + g * N


def logmel(S):
    L = np.log(S + 1e-6)
    return (L - L.mean(1, keepdims=True)) / (L.std(1, keepdims=True) + 1e-9)


def obs(S, snr, seed):
    """加前导噪声 → 混噪 → 切掉前导 → log-mel。snr=None 表示干净"""
    if snr is None:
        return logmel(S)
    Sp = np.hstack([np.full((NB, PRE), 1e-4), S])
    Y = mix(Sp, noise_spec(Sp.shape[1], seed), snr)
    return logmel(Y[:, PRE:])


def warp(L):
    idx = np.linspace(0, L.shape[1] - 1, WLEN)
    return np.stack([np.interp(idx, np.arange(L.shape[1]), L[b]) for b in range(NB)])


def template(Ls):
    return np.mean([warp(L) for L in Ls], axis=0)


def sc(L, tpl):
    w = warp(L)
    return float((w * tpl).sum() / (np.linalg.norm(w) * np.linalg.norm(tpl) + 1e-9))


def stream_scores(L, tpl, step=3):
    o = []
    for t in range(0, max(L.shape[1] - WLEN, 0) + 1, step):
        w = L[:, t:t + WLEN]
        o.append(float((w * tpl).sum() / (np.linalg.norm(w) * np.linalg.norm(tpl) + 1e-9)))
    return o or [-1.0]


# ══ 背景流：用来定阈值（固定误唤醒次数） ═════════════════════
NBG, BG_LEN = 70, 600
TEST_SNR = 5
bg = []
for i in range(NBG):
    r = np.random.default_rng(600 + i)
    seq = list(r.integers(0, len(PHSET), BG_LEN // FR_PER_SYL + 2))
    bg.append(utter(seq, int(r.integers(0, NSPK)), 600 + i, jit=0.7)[:, :BG_LEN])
BGO = [obs(S[:, :BG_LEN], TEST_SNR, 3000 + i) for i, S in enumerate(bg)]
K_FA = 1                                       # 允许的误唤醒次数（定阈值用）
STEP = 4


def windows(L):
    """把一条流切成归一化的窗口矩阵，建一次就能反复打分"""
    idx = range(0, max(L.shape[1] - WLEN, 0) + 1, STEP)
    W = np.stack([L[:, t:t + WLEN].ravel() for t in idx]).astype(np.float32)
    W /= (np.linalg.norm(W, axis=1, keepdims=True) + 1e-9)
    return W


BGW = [windows(L) for L in BGO]                # 背景窗口，只建一次


def neg_scores(tpl):
    t = (tpl.ravel() / (np.linalg.norm(tpl) + 1e-9)).astype(np.float32)
    return np.concatenate([W @ t for W in BGW])


def neg_scores_bank(bank):
    ts = np.stack([(t.ravel() / (np.linalg.norm(t) + 1e-9)).astype(np.float32)
                   for t in bank]).T
    return np.concatenate([(W @ ts).max(1) for W in BGW])


def frr_at_fa(tpl, pos_obs, thr=None):
    if thr is None:
        thr = np.sort(neg_scores(tpl))[-K_FA]
    pos = np.array([sc(L, tpl) for L in pos_obs])
    return float((pos < thr).mean()) * 100


def frr_at_fa_bank(bank, pos_obs, thr):
    """一组模板取最大相似度——这才是"见过很多人"的模型该有的样子，
       而不是把所有人平均成一个模板（那样等于抹掉了说话人变异）"""
    pos = np.array([max(sc(L, t) for t in bank) for L in pos_obs])
    return float((pos < thr).mean()) * 100


# ══ ① 注册条数 ═══════════════════════════════════════════════
ENROLL_SPK = list(range(12))                   # 12 个"设备主人"，各自注册各自测
NTEST = 20

print('① 注册几条够（本人注册、本人使用，测试 SNR %d dB）' % TEST_SNR)
print('  %8s %14s %14s' % ('注册条数', '漏唤醒', '相对 1 条'))
OUT['enroll'] = []
base1 = None
for n in (1, 2, 3, 5, 10):
    vals = []
    for spk in ENROLL_SPK:
        enr = [obs(utter(KEYSEQ, spk, 10000 + spk * 50 + j), None, 0) for j in range(n)]
        tpl = template(enr)
        pos = [obs(utter(KEYSEQ, spk, 20000 + spk * 50 + t), TEST_SNR, 4000 + spk * 50 + t)
               for t in range(NTEST)]
        vals.append(frr_at_fa(tpl, pos))
    m = float(np.mean(vals))
    if base1 is None:
        base1 = m
    r = {'n': n, 'frr': round(m, 2), 'sd': round(float(np.std(vals)), 2),
         'rel': round(m / base1, 3)}
    OUT['enroll'].append(r)
    print('  %8d %12.2f%% %13.2f' % (n, r['frr'], r['rel']))

# ══ ② 自定义 vs 专训 ═════════════════════════════════════════
print('\n② 自定义（几条注册）vs 专训（很多人的数据）')
train_spk = list(range(12, NSPK))
BANK = [template([obs(utter(KEYSEQ, s, 30000 + s * 7 + j), None, 0)
                  for j in range(6)]) for s in train_spk]   # 每个训练说话人一个模板
allpos = [(spk, [obs(utter(KEYSEQ, spk, 20000 + spk * 50 + t), TEST_SNR,
                     4000 + spk * 50 + t) for t in range(NTEST)])
          for spk in ENROLL_SPK]
THR_BANK = np.sort(neg_scores_bank(BANK))[-K_FA]
frr_big = float(np.mean([frr_at_fa_bank(BANK, p, THR_BANK) for _, p in allpos]))
e5 = [r for r in OUT['enroll'] if r['n'] == 5][0]
OUT['vs_trained'] = {'trained': round(frr_big, 2), 'custom5': e5['frr'],
                     'nspk_train': len(train_spk), 'nutt_train': len(train_spk) * 6,
                     'ratio': round(e5['frr'] / max(frr_big, 1e-9), 2)}
print('  专训（%d 个训练说话人各一个模板，取最大相似度）：漏唤醒 %.2f%%'
      % (len(train_spk), frr_big))
print('  自定义（本人 5 条）：            漏唤醒 %.2f%%' % e5['frr'])
print('  → 自定义是专训的 %.2f 倍' % OUT['vs_trained']['ratio'])

# ══ ③ 跨说话人 / 注册环境失配 ════════════════════════════════
print('\n③ 两种失配')
cross = []
for spk in ENROLL_SPK:
    enr = [obs(utter(KEYSEQ, spk, 10000 + spk * 50 + j), None, 0) for j in range(5)]
    tpl = template(enr)
    others = [s for s in ENROLL_SPK if s != spk][:6]
    pos = [obs(utter(KEYSEQ, o, 21000 + o * 50 + t), TEST_SNR, 4500 + o * 50 + t)
           for o in others for t in range(4)]
    cross.append(frr_at_fa(tpl, pos))
CROSS_BIG = float(np.mean([frr_at_fa_bank(BANK, [
    obs(utter(KEYSEQ, o, 21000 + o * 50 + t), TEST_SNR, 4500 + o * 50 + t)
    for t in range(4)], THR_BANK) for o in ENROLL_SPK]))
OUT['cross'] = {'self': e5['frr'], 'other': round(float(np.mean(cross)), 2)}
print('  本人注册、本人喊：漏唤醒 %.2f%%' % e5['frr'])
print('  本人注册、别人喊：漏唤醒 %.2f%%（%.1f 倍）'
      % (OUT['cross']['other'], OUT['cross']['other'] / max(e5['frr'], 1e-9)))
print('  专训、别人喊：    漏唤醒 %.2f%%（专训对谁都一样）' % CROSS_BIG)
OUT['cross']['trained_other'] = round(CROSS_BIG, 2)

ENV = []
for enr_snr in (None, 20, 10, 5):
    vals = []
    for spk in ENROLL_SPK:
        enr = [obs(utter(KEYSEQ, spk, 10000 + spk * 50 + j), enr_snr,
                   5500 + spk * 50 + j) for j in range(5)]
        tpl = template(enr)
        pos = [obs(utter(KEYSEQ, spk, 20000 + spk * 50 + t), TEST_SNR,
                   4000 + spk * 50 + t) for t in range(NTEST)]
        vals.append(frr_at_fa(tpl, pos))
    ENV.append({'enroll_snr': ('安静' if enr_snr is None else '%d dB' % enr_snr),
                'frr': round(float(np.mean(vals)), 2)})
OUT['enroll_env'] = ENV
print('  注册时的信噪比（统一在 %d dB 使用，本人 5 条注册）' % TEST_SNR)
for r in ENV:
    print('    注册 %-8s → 漏唤醒 %.2f%%' % (r['enroll_snr'], r['frr']))

OUT['setup'] = {'nsyl': NSYL, 'wlen': WLEN, 'nspk': NSPK, 'nenroll_spk': len(ENROLL_SPK),
                'ntest': NTEST, 'test_snr': TEST_SNR, 'k_fa': K_FA,
                'nbg': NBG, 'bg_sec': BG_LEN / FPS}

en = {r['n']: r for r in OUT['enroll']}
print('\n结论')
print('  ① 注册曲线是个断崖：1 条 %.2f%%，3 条 %.2f%%，5 条 %.2f%%，10 条 %.2f%%。'
      % (en[1]['frr'], en[3]['frr'], en[5]['frr'], en[10]['frr']))
print('     5 条之后基本不再降——<strong>产品上要 3–5 条，要更多也没用</strong>。')
print('     这和 10 节那条声纹注册曲线是同一个形状，原因也一样：')
print('     前几条补的是"这个人这句话的随机变异"，补完就到头了。')
print('  ② <strong>"自定义一定比专训差"这个说法要看谁在说话</strong>：')
print('     注册的那个人自己喊，自定义 %.2f%% 反而比专训的 %.2f%% 好——'
      % (e5['frr'], frr_big))
print('     因为模板正好长成他的样子，而专训要同时覆盖几十种口音。')
print('     换个人喊就反过来了：自定义 %.2f%%，专训 %.2f%%。'
      % (OUT['cross']['other'], CROSS_BIG))
print('     所以真正的差距不在平均精度，在<strong>覆盖面</strong>。')
print('     注意这里的"专训"只是 %d 个说话人的最近邻，没有判别训练也没有加噪增广，'
      % len(train_spk))
print('     所以它的 %.2f%% 是偏悲观的——真实的专训模型会更好，结论的方向不变。'
      % frr_big)
print('  ③ <strong>自定义唤醒词最大的坑不在精度，在"只认注册的那个人"</strong>：')
print('     本人喊 %.2f%%，别人喊 %.2f%%——差 %.1f 倍。'
      % (e5['frr'], OUT['cross']['other'],
         OUT['cross']['other'] / max(e5['frr'], 1e-9)))
print('     而专训对本人 %.2f%%、对别人 %.2f%%，基本一视同仁。'
      % (frr_big, CROSS_BIG))
print('     家里第二个人喊不醒，是自定义这条路线的结构性代价，不是调参能解决的。')
print('  ④ 注册环境的规律不是"越干净越好"：')
for r in ENV:
    print('     注册 %-8s → %.2f%%' % (r['enroll_snr'], r['frr']))
best_env = min(ENV[1:], key=lambda r: r['frr'])
print('     <strong>在绝对安静里注册是最差的一档</strong>：%.2f%%，'
      % ENV[0]['frr'])
print('     而只要带一点真实环境声（%s）就降到 %.2f%%——差 %.1f 倍。'
      % (best_env['enroll_snr'], best_env['frr'],
         ENV[0]['frr'] / max(best_env['frr'], 1e-9)))
print('     注意不需要精确匹配：20 dB、10 dB、5 dB 三档差别不大（%.2f/%.2f/%.2f%%），'
      % (ENV[1]['frr'], ENV[2]['frr'], ENV[3]['frr']))
print('     真正要避免的是"无菌"注册——它让模板学到了一个现实中不存在的条件。')
print('     所以产品上该说的不是"请在安静环境注册"，')
print('     是"请在你平时用它的那个地方注册"。')

json.dump(OUT, open('demo_open.json', 'w'), ensure_ascii=False)
print('\n→ demo_open.json')
