#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""20 节：零样本克隆的参考音频里，到底有几样东西纠缠在一起。

造一批"说话人 × 房间 × 内容"的梅尔谱：
  说话人 = 声道长度（共振峰整体缩放）+ 基频区间 + 谱倾斜
  房间   = 混响拖尾（在 log 梅尔域上是沿时间的前向平滑）+ 一条信道曲线
  内容   = 一串音素目标
再用一个"说话人嵌入"（长时平均谱，和 x-vector 的一阶统计量是同一类东西）去打分，
量四件事：
  ① 换房间掉多少分，换人掉多少分——两者可比吗
  ② 合成结果带着参考的房间时，相似度虚高多少
  ③ 倒谱均值归一化能收回多少
  ④ 参考音频要几秒才够
"""
import json, math
import numpy as np

rng = np.random.default_rng(5)
OUT = {}

NMEL, FPS = 80, 86.13          # 80 维梅尔，11.6 ms 帧移
MHZ = 2595 * np.log10(1 + (np.arange(NMEL) / NMEL * 8000) / 700)

NSPK, NROOM, NUTT = 24, 4, 6
FRAMES = 860                   # 约 10 s

# ── 说话人：声道长度 / 基频 / 谱倾斜 ─────────────────────────
VTL = rng.uniform(0.86, 1.16, NSPK)            # 声道长度因子
F0C = rng.uniform(95, 205, NSPK)
TILT = rng.uniform(-0.45, 0.45, NSPK)

# ── 房间：RT60 与信道曲线 ────────────────────────────────────
RT60 = np.array([0.0, 0.25, 0.5, 0.8])[:NROOM]
CHAN = np.stack([np.zeros(NMEL)] +
                [rng.normal(0, 0.55, NMEL) for _ in range(NROOM - 1)])
for i in range(1, NROOM):                       # 信道是平滑的，不是白噪
    k = np.exp(-0.5 * (np.arange(-12, 13) / 5.0) ** 2)
    k /= k.sum()
    CHAN[i] = np.convolve(CHAN[i], k, 'same')

# ── 内容：一串音素目标（三个共振峰的基准位置） ────────────────
PHSET = np.array([[730, 1090, 2440], [270, 2290, 3010], [300, 870, 2240],
                  [530, 1840, 2480], [660, 1720, 2410], [490, 1350, 1690],
                  [400, 1900, 2600], [600, 1000, 2500]], float)


def make_mel(spk, room, utt, frames=FRAMES):
    r = np.random.default_rng(10000 + utt * 97)
    seq = r.integers(0, len(PHSET), frames // 9 + 1)
    dur = r.integers(6, 13, len(seq))
    tgt = np.repeat(PHSET[seq], dur, axis=0)[:frames]
    if len(tgt) < frames:
        tgt = np.vstack([tgt, np.repeat(tgt[-1:], frames - len(tgt), axis=0)])
    # 平滑成轨迹（协同发音）
    k = np.exp(-0.5 * (np.arange(-6, 7) / 2.4) ** 2)
    k /= k.sum()
    tgt = np.stack([np.convolve(tgt[:, i], k, 'same') for i in range(3)], 1)
    tgt = tgt * VTL[spk]                                    # 说话人：共振峰缩放
    m = np.zeros((NMEL, frames))
    for i in range(3):
        c = 2595 * np.log10(1 + tgt[:, i] / 700)
        m += (0.86 ** i) * np.exp(-0.5 * ((MHZ[:, None] - c[None, :]) / 88) ** 2)
    m += 0.04 * np.exp(-MHZ[:, None] / (700 + 3 * F0C[spk]))  # 基频相关的低频底
    lm = np.log(m + 1e-3)
    lm += TILT[spk] * (MHZ[:, None] / MHZ[-1] - 0.5)          # 说话人：谱倾斜
    # 房间：沿时间的前向指数拖尾 + 信道
    rt = RT60[room]
    if rt > 0:
        n = int(rt * FPS)
        h = np.exp(-np.arange(n + 1) / max(rt * FPS / 3, 1e-6))
        h /= h.sum()
        e = np.exp(lm)
        e = np.stack([np.convolve(e[j], h)[:frames] for j in range(NMEL)])
        lm = np.log(e + 1e-6)
    lm += CHAN[room][:, None]
    return lm


def emb(lm, cmn=False):
    """说话人嵌入：长时平均谱（可选做倒谱均值归一化）"""
    v = lm.mean(1)
    if cmn:
        v = v - v.mean()
    return v / (np.linalg.norm(v) + 1e-12)


def cos(a, b):
    return float(a @ b)


# ══ ① 换房间 vs 换人 ═════════════════════════════════════════
def table(cmn):
    E = {}
    for s in range(NSPK):
        for r in range(NROOM):
            for u in range(NUTT):
                E[(s, r, u)] = emb(make_mel(s, r, u), cmn)
    same_spk_same_room, same_spk_diff_room = [], []
    diff_spk_same_room, diff_spk_diff_room = [], []
    for s in range(NSPK):
        for r in range(NROOM):
            for u in range(NUTT):
                for u2 in range(u + 1, NUTT):
                    same_spk_same_room.append(cos(E[(s, r, u)], E[(s, r, u2)]))
                for r2 in range(NROOM):
                    if r2 != r:
                        same_spk_diff_room.append(cos(E[(s, r, 0)], E[(s, r2, 1)]))
    for s in range(NSPK):
        for s2 in range(s + 1, NSPK):
            for r in range(NROOM):
                diff_spk_same_room.append(cos(E[(s, r, 0)], E[(s2, r, 1)]))
            diff_spk_diff_room.append(cos(E[(s, 0, 0)], E[(s2, 1, 1)]))
    return E, {'同人同室': same_spk_same_room, '同人异室': same_spk_diff_room,
               '异人同室': diff_spk_same_room, '异人异室': diff_spk_diff_room}


def eer(tar, non):
    a = np.array(tar)
    b = np.array(non)
    ths = np.linspace(min(a.min(), b.min()), max(a.max(), b.max()), 2000)
    fr = np.array([(a < t).mean() for t in ths])
    fa = np.array([(b >= t).mean() for t in ths])
    i = int(np.argmin(np.abs(fr - fa)))
    return float((fr[i] + fa[i]) / 2 * 100)


print('① 参考音频里纠缠着什么：换房间和换人，各掉多少分')
OUT['pairs'] = {}
for cmn, lab in ((False, '原始'), (True, '倒谱均值归一化后')):
    E, g = table(cmn)
    print('  %s' % lab)
    print('    %-10s %10s %10s' % ('配对', '余弦均值', '标准差'))
    rec = {}
    for k, v in g.items():
        rec[k] = {'mean': round(float(np.mean(v)), 4), 'sd': round(float(np.std(v)), 4)}
        print('    %-10s %10.4f %10.4f' % (k, np.mean(v), np.std(v)))
    # 正确的协议：目标 = 同人异室（换一场录音），冒充者 = 异人
    e_ok = eer(g['同人异室'], g['异人异室'])
    # 被骗的协议：目标 = 同人同室，冒充者 = 异人异室
    e_bad = eer(g['同人同室'], g['异人异室'])
    rec['eer_strict'] = round(e_ok, 2)
    rec['eer_naive'] = round(e_bad, 2)
    rec['room_gap'] = round(rec['同人同室']['mean'] - rec['同人异室']['mean'], 4)
    rec['spk_gap'] = round(rec['同人同室']['mean'] - rec['异人同室']['mean'], 4)
    OUT['pairs']['cmn' if cmn else 'raw'] = rec
    print('    换房间掉 %.4f，换人掉 %.4f —— 比值 %.2f'
          % (rec['room_gap'], rec['spk_gap'], rec['room_gap'] / max(rec['spk_gap'], 1e-9)))
    print('    EER：严谨协议（参考换一场录音）%.2f%%，'
          '偷懒协议（拿那段参考本身比）%.2f%%' % (e_ok, e_bad))

raw, cm = OUT['pairs']['raw'], OUT['pairs']['cmn']

# ══ ② 合成结果带着参考的房间，相似度虚高多少 ═════════════════
print('\n② 合成结果带着参考的房间时，相似度虚高多少')
E, _ = table(False)
infl = []
for s in range(NSPK):
    ref = E[(s, 2, 0)]                       # 参考：说话人 s 在房间 2
    with_room = cos(ref, E[(s, 2, 3)])       # 合成结果也带房间 2
    without = cos(ref, E[(s, 0, 3)])         # 合成结果是干净的
    infl.append(with_room - without)
OUT['inflation'] = {'mean': round(float(np.mean(infl)), 4),
                    'sd': round(float(np.std(infl)), 4),
                    'pos_frac': round(float(np.mean(np.array(infl) > 0)) * 100, 1)}
print('   带房间 − 不带房间 = %+.4f ± %.4f，%.0f%% 的说话人上是正的。'
      % (OUT['inflation']['mean'], OUT['inflation']['sd'], OUT['inflation']['pos_frac']))
print('   也就是说：<strong>把房间一起学走，相似度反而更高</strong>。')

# ══ ③ 参考音频要几秒 ═════════════════════════════════════════
print('\n③ 参考音频要几秒才够')
print('  %8s %12s %12s %12s' % ('参考时长', '同人余弦', '标准差', 'EER'))
OUT['dur'] = []
for sec in (1, 2, 3, 5, 10):
    fr = int(sec * FPS)
    Es = {(s, u): emb(make_mel(s, 0, u, fr)) for s in range(NSPK) for u in (0, 1)}
    tar = [cos(Es[(s, 0)], Es[(s, 1)]) for s in range(NSPK)]
    non = [cos(Es[(s, 0)], Es[(s2, 1)])
           for s in range(NSPK) for s2 in range(NSPK) if s != s2]
    e = eer(tar, non)
    r_ = {'sec': sec, 'mean': round(float(np.mean(tar)), 4),
          'sd': round(float(np.std(tar)), 4), 'eer': round(e, 2)}
    OUT['dur'].append(r_)
    print('  %6d s %12.4f %12.4f %11.2f%%' % (sec, r_['mean'], r_['sd'], e))

OUT['setup'] = {'nspk': NSPK, 'nroom': NROOM, 'nutt': NUTT,
                'rt60': [float(x) for x in RT60], 'nmel': NMEL,
                'frames': FRAMES, 'sec': round(FRAMES / FPS, 1)}

print('\n结论（第一条是我猜错、被数据否掉的）')
print('  ① <strong>猜错的一条</strong>：我以为在这种一阶统计量的嵌入上，'
      '房间会盖过说话人。')
print('     实测没有：换房间掉 %.4f，换人掉 %.4f，房间只有说话人的 %.2f 倍。'
      % (raw['room_gap'], raw['spk_gap'], raw['room_gap'] / raw['spk_gap']))
print('     "同室陌生人比异室同人更像"也不成立：异人同室 %.4f < 同人异室 %.4f。'
      % (raw['异人同室']['mean'], raw['同人异室']['mean']))
print('  ② 但评测协议的乐观仍然是量级上的：拿那段参考本身去比，EER %.2f%%；'
      % raw['eer_naive'])
print('     换一场录音再比，EER %.2f%%——<strong>差 %.0f 倍</strong>。'
      % (raw['eer_strict'], raw['eer_strict'] / max(raw['eer_naive'], 1e-9)))
print('     关键在于 EER 比的不是绝对差距，是<strong>两个分布重叠多少</strong>：')
print('     同人异室的标准差 %.4f，异人异室的标准差 %.4f——'
      % (raw['同人异室']['sd'], raw['异人异室']['sd']))
print('     冒充者那一堆散得多，所以一点点房间偏置就足以把两堆推到一起。')
print('  ③ 房间确实会把分数顶上去：合成结果带着参考的房间时，'
      '相似度 %+.4f ± %.4f，'
      % (OUT['inflation']['mean'], OUT['inflation']['sd']))
print('     %.0f%% 的说话人上都是正的。这个量和"换房间"本身是同一个量级（%.4f）——'
      % (OUT['inflation']['pos_frac'], raw['room_gap']))
print('     不大，但方向一致、无一例外，所以它是系统性偏置而不是噪声。')
print('  ④ 倒谱均值归一化有用，但不是我以为的那个机制：')
print('     换房间的代价并没有变小（%.4f → %.4f），'
      % (raw['room_gap'], cm['room_gap']))
print('     <strong>是换人的差距被放大了 %.1f 倍</strong>（%.4f → %.4f），'
      % (cm['spk_gap'] / raw['spk_gap'], raw['spk_gap'], cm['spk_gap']))
print('     房间/说话人的比值从 %.2f 降到 %.2f，严谨协议的 EER 从 %.2f%% 降到 %.2f%%。'
      % (raw['room_gap'] / raw['spk_gap'], cm['room_gap'] / cm['spk_gap'],
         raw['eer_strict'], cm['eer_strict']))
print('     去掉全局电平之后，剩下的谱形状才是说话人信息密集的地方。')
d = {r['sec']: r for r in OUT['dur']}
print('  ⑤ 参考时长是个断崖，不是斜坡：'
      'EER 1 s %.1f%% → 3 s %.1f%% → 5 s %.1f%% → 10 s %.1f%%。'
      % (d[1]['eer'], d[3]['eer'], d[5]['eer'], d[10]['eer']))
print('     5 秒之后基本不再涨。短参考掉的是<strong>均值和方差两头</strong>'
      '（%.4f ± %.4f → %.4f ± %.4f）——'
      % (d[1]['mean'], d[1]['sd'], d[5]['mean'], d[5]['sd']))
print('     同样 2 秒的参考，能不能用取决于那 2 秒里说了什么。')
print('\n  这个嵌入是长时平均谱，比真的 ECAPA 粗得多，')
print('  所以绝对 EER 不能和公开结果比。可比的是<strong>协议之间的倍数关系</strong>。')

json.dump(OUT, open('demo_clone.json', 'w'), ensure_ascii=False)
print('\n→ demo_clone.json')
