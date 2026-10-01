#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""17 节：前端降噪对唤醒到底是帮是害。

这是《单通道增强手册》19 节那个实验的唤醒版：那边测的是说话人确认（EER），
这边测的是检测任务（固定误唤醒率下的漏唤醒率）——两者的失效方式不一样。

做法：在功率谱域合成"唤醒词 + 背景语音 + 噪声"，
过一遍不同激进程度的谱减，再用模板匹配做检测。
两种条件各测一遍：
  失配——模板取自干净语音（也就是模型没见过增强后的数据）
  匹配——模板在同样处理过的数据上重估（也就是拿增强后的数据重训/重调）
"""
import json, math
import numpy as np

rng = np.random.default_rng(23)
OUT = {}

NB, FPS = 40, 100.0                      # 40 维 log-mel，10 ms 帧移
MHZ = 2595 * np.log10(1 + (np.arange(NB) / NB * 8000) / 700)
NSYL = 4                                  # 四音节唤醒词
FR_PER_SYL = 15
WLEN = NSYL * FR_PER_SYL                  # 唤醒词 60 帧 = 0.6 s

PHSET = np.array([[730, 1090, 2440], [270, 2290, 3010], [300, 870, 2240],
                  [530, 1840, 2480], [660, 1720, 2410], [490, 1350, 1690],
                  [400, 1900, 2600], [600, 1000, 2500], [350, 1600, 2300],
                  [700, 1200, 2700]], float)
KEYSEQ = [1, 6, 3, 8]                      # 唤醒词的四个音节


def spec_from_seq(seq, jitter=0.0, seed=None, dur=FR_PER_SYL):
    """一串音节 → 功率谱（线性域），jitter 控制说话人/语速的随机扰动"""
    r = np.random.default_rng(seed)
    tgt = []
    for u in seq:
        d = max(4, int(round(dur * (1 + jitter * r.normal()))))
        f = PHSET[u] * (1 + 0.06 * jitter * r.normal())
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
    gain = 10 ** (0.12 * jitter * r.normal() )
    return S * gain


def noise_spec(n, kind='babble', seed=None):
    r = np.random.default_rng(seed)
    if kind == 'pink':
        base = np.exp(-MHZ / 2600)[:, None] * np.ones((1, n))
        return base * (0.6 + 0.8 * r.random((NB, n)))
    # babble：几条随机语音叠起来，所以它在时频上和语音一样"忽有忽无"
    acc = np.zeros((NB, n))
    for _ in range(6):
        seq = list(r.integers(0, len(PHSET), n // FR_PER_SYL + 2))
        s = spec_from_seq(seq, jitter=0.9, seed=int(r.integers(1e9)))
        acc += s[:, :n] if s.shape[1] >= n else np.pad(s, ((0, 0), (0, n - s.shape[1])))
    return acc / 6


def mix(S, N, snr_db):
    ps, pn = S.mean(), N.mean()
    g = ps / (pn * 10 ** (snr_db / 10) + 1e-20)
    return S + g * N, g * N


PRE = 30                                  # 每条样本前面 0.3 s 的纯噪声（真实系统里总有）


def specsub(Y, alpha, floor=0.02, npre=PRE):
    """谱减：用前导的纯噪声段估噪声，过减 alpha 倍，留 floor 的谱底"""
    if alpha <= 0:
        return Y
    Nh = Y[:, :npre].mean(1, keepdims=True)
    D = Y - alpha * Nh
    return np.maximum(D, floor * Y)


def logmel(S):
    L = np.log(S + 1e-6)
    return (L - L.mean(1, keepdims=True)) / (L.std(1, keepdims=True) + 1e-9)


def segsnr(Sclean, Shat):
    """分段信噪比（dB），作为"给人听"那一侧的代理指标"""
    e = (np.sqrt(Shat) - np.sqrt(Sclean)) ** 2
    num = Sclean.sum(0)
    den = e.sum(0) + 1e-20
    v = 10 * np.log10(num / den)
    return float(np.clip(v, -10, 35).mean())


# ══ 造数据 ═══════════════════════════════════════════════════
NPOS, NBG = 240, 90                      # 正样本条数、背景流段数
BG_LEN = 600                             # 每段背景 6 s
SNRS = (0, 5, 10, 20)
ALPHAS = (0.0, 1.0, 2.0, 4.0, 6.0)

pos_clean = [spec_from_seq(KEYSEQ, jitter=0.85, seed=100 + i) for i in range(NPOS)]
bg_clean = []
for i in range(NBG):
    r = np.random.default_rng(500 + i)
    seq = list(r.integers(0, len(PHSET), BG_LEN // FR_PER_SYL + 2))
    bg_clean.append(spec_from_seq(seq, jitter=0.9, seed=500 + i)[:, :BG_LEN])
tpl_clean = [spec_from_seq(KEYSEQ, jitter=0.35, seed=9000 + i) for i in range(12)]


def make_template(specs):
    """把若干条样例对齐到统一长度后平均，得到 log-mel 模板"""
    acc = np.zeros((NB, WLEN))
    for s in specs:
        L = logmel(s)
        idx = np.linspace(0, L.shape[1] - 1, WLEN)
        acc += np.stack([np.interp(idx, np.arange(L.shape[1]), L[b]) for b in range(NB)])
    return acc / len(specs)


def score_stream(L, tpl, step=3):
    """滑窗打分，返回每个窗口的相似度"""
    out = []
    for t in range(0, max(L.shape[1] - WLEN, 0) + 1, step):
        w = L[:, t:t + WLEN]
        out.append(float((w * tpl).sum() / (np.linalg.norm(w) * np.linalg.norm(tpl) + 1e-9)))
    return np.array(out) if out else np.array([-1.0])


def score_one(L, tpl):
    idx = np.linspace(0, L.shape[1] - 1, WLEN)
    w = np.stack([np.interp(idx, np.arange(L.shape[1]), L[b]) for b in range(NB)])
    return float((w * tpl).sum() / (np.linalg.norm(w) * np.linalg.norm(tpl) + 1e-9))


FA_TARGET = 0.5 / 24 / 3600 * (BG_LEN / FPS)   # 0.5 次/天 折算到每段背景的期望次数


def prep(S, snr, alpha, kind, seed):
    """前面接 PRE 帧纯噪声 → 混噪 → 谱减 → 切掉前导 → log-mel"""
    Sp = np.hstack([np.full((NB, PRE), 1e-4), S])
    N = noise_spec(Sp.shape[1], kind, seed=seed)
    Y, _ = mix(Sp, N, snr)
    H = specsub(Y, alpha)
    return H[:, PRE:], Sp[:, PRE:]


def run(snr, alpha, matched, kind='babble'):
    proc_pos, proc_bg, ss = [], [], []
    for i, S in enumerate(pos_clean):
        H, C = prep(S, snr, alpha, kind, 2000 + i)
        proc_pos.append(logmel(H))
        if i < 60:
            ss.append(segsnr(C, H))
    for i, S in enumerate(bg_clean):
        H, _ = prep(S, snr, alpha, kind, 7000 + i)
        proc_bg.append(logmel(H))
    if matched:                      # 模板在同样处理过的数据上重估
        tp = [prep(S, snr, alpha, kind, 8100 + i)[0]
              for i, S in enumerate(tpl_clean)]
        tpl = make_template(tp)
    else:                            # 失配：模板来自干净语音
        tpl = make_template(tpl_clean)
    neg = np.concatenate([score_stream(L, tpl) for L in proc_bg])
    pos = np.array([score_one(L, tpl) for L in proc_pos])
    # 固定误唤醒次数：每段背景允许 FA_TARGET 次 → 总共 k 次
    k = max(1, int(round(FA_TARGET * NBG)))
    thr = np.sort(neg)[-k]
    frr = float((pos < thr).mean()) * 100
    return {'frr': round(frr, 2), 'segsnr': round(float(np.mean(ss)), 2),
            'thr': round(thr, 4)}


print('唤醒的检测任务：固定误唤醒次数下的漏唤醒率')
print('  唤醒词 %d 音节 / %d 帧，正样本 %d 条，背景 %d 段 × %.0f s'
      % (NSYL, WLEN, NPOS, NBG, BG_LEN / FPS))
print('  噪声：babble（和语音一样忽有忽无，这是唤醒最难的一类）')

OUT['grid'] = []
for kind in ('babble',):
    for snr in SNRS:
        print('\n  SNR %d dB' % snr)
        print('  %8s %12s %16s %16s'
              % ('过减 α', '分段信噪比', '漏唤醒（失配）', '漏唤醒（匹配）'))
        for a in ALPHAS:
            mm = run(snr, a, matched=False, kind=kind)
            mt = run(snr, a, matched=True, kind=kind)
            r = {'kind': kind, 'snr': snr, 'alpha': a,
                 'segsnr': mm['segsnr'],
                 'frr_mismatch': mm['frr'], 'frr_matched': mt['frr']}
            OUT['grid'].append(r)
            print('  %8.1f %10.2f dB %14.2f%% %15.2f%%'
                  % (a, r['segsnr'], r['frr_mismatch'], r['frr_matched']))

# ══ 汇总 ═════════════════════════════════════════════════════
def pick(snr, key):
    rows = [r for r in OUT['grid'] if r['snr'] == snr]
    return min(rows, key=lambda r: r[key]) if 'frr' in key else \
        max(rows, key=lambda r: r[key])


OUT['best'] = {}
for snr in SNRS:
    rows = [r for r in OUT['grid'] if r['snr'] == snr]
    base = [r for r in rows if r['alpha'] == 0][0]
    OUT['best'][str(snr)] = {
        'base_mismatch': base['frr_mismatch'], 'base_matched': base['frr_matched'],
        'best_segsnr_alpha': max(rows, key=lambda r: r['segsnr'])['alpha'],
        'best_mismatch': min(rows, key=lambda r: r['frr_mismatch']),
        'best_matched': min(rows, key=lambda r: r['frr_matched']),
    }

print('\n结论')
for snr in SNRS:
    b = OUT['best'][str(snr)]
    print('  SNR %2d dB：不处理时漏唤醒 失配 %.2f%% / 匹配 %.2f%%；'
          % (snr, b['base_mismatch'], b['base_matched']))
    print('            分段信噪比最好的是 α=%.0f，'
          '而漏唤醒最低的是 失配 α=%.0f（%.2f%%）/ 匹配 α=%.0f（%.2f%%）'
          % (b['best_segsnr_alpha'], b['best_mismatch']['alpha'],
             b['best_mismatch']['frr_mismatch'], b['best_matched']['alpha'],
             b['best_matched']['frr_matched']))
OUT['setup'] = {'nsyl': NSYL, 'wlen': WLEN, 'npos': NPOS, 'nbg': NBG,
                'bg_sec': BG_LEN / FPS, 'fa_day': 0.5, 'nb': NB}


g5 = {r['alpha']: r for r in OUT['grid'] if r['snr'] == 5}
g10 = {r['alpha']: r for r in OUT['grid'] if r['snr'] == 10}
OUT['summary'] = {
    'help_mismatch_5db': round(g5[0.0]['frr_mismatch'] / g5[2.0]['frr_mismatch'], 2),
    'matched_gain_5db': round(g5[2.0]['frr_mismatch'] / g5[2.0]['frr_matched'], 2),
    'alpha_gap': [{'snr': snr,
                   'best_segsnr': max([r for r in OUT['grid'] if r['snr'] == snr],
                                      key=lambda r: r['segsnr'])['alpha'],
                   'best_frr': min([r for r in OUT['grid'] if r['snr'] == snr],
                                   key=lambda r: r['frr_matched'])['alpha']}
                  for snr in SNRS],
}
print('\n  把这四张表读成三句话：')
print('  ① <strong>增强对唤醒是有用的</strong>——这和增强手册 19 节的结论相反。')
print('     那边测的是说话人确认，每一档增强都让 EER 变差；')
print('     这边 5 dB 时漏唤醒从 %.2f%% 降到 %.2f%%（%.1f 倍）。'
      % (g5[0.0]['frr_mismatch'], g5[2.0]['frr_mismatch'],
         OUT['summary']['help_mismatch_5db']))
print('     机制不一样：说话人身份藏在谱的精细结构里，谱减恰好把那一层抹掉；')
print('     而唤醒只要那条粗粒度的音素轨迹，它扛得住。')
print('  ② <strong>感知指标和下游任务的最优过减量不是同一个</strong>，而且分歧随信噪比拉大：')
for r in OUT['summary']['alpha_gap']:
    print('     SNR %2d dB：分段信噪比最好 α=%.0f，漏唤醒最好 α=%.0f'
          % (r['snr'], r['best_segsnr'], r['best_frr']))
print('     信噪比越高，下游越吃得消激进的过减，而感知指标一直停在 α=1。')
print('  ③ <strong>但这两件事加起来都不如"用增强后的数据重估模板"值钱</strong>：')
print('     5 dB、α=2 时，失配 %.2f%% vs 匹配 %.2f%%，差 %.1f 倍；'
      % (g5[2.0]['frr_mismatch'], g5[2.0]['frr_matched'],
         OUT['summary']['matched_gain_5db']))
print('     而调 α 带来的改善只有 %.1f 倍。'
      % OUT['summary']['help_mismatch_5db'])
print('     训练与推理的信号链必须一致——这一条和增强手册那边是同一个结论。')

json.dump(OUT, open('demo_fe.json', 'w'), ensure_ascii=False)
print('\n→ demo_fe.json')
