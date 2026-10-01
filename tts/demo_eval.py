#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""25 节算例：MOS 到底要多少人多少句才测得出来；以及延迟和算力预算。

   说明：下面的方差参数（评分噪声、评分人偏置、句子难度）是<strong>假设</strong>，
   取自公开听测里常见的量级。给定这组假设之后，功效计算本身是精确的蒙特卡洛，
   换一组参数把脚本改一行重跑即可——重点是那个量级，不是小数点后一位。"""
import numpy as np, json, math

rng = np.random.default_rng(0)
OUT = {}

SD_NOISE = 0.85      # 同一个人对同一条音频重复打分的波动
SD_RATER = 0.45      # 评分人之间的松紧差异（有人普遍打高分）
SD_SENT = 0.35       # 句子本身的难易
OUT['assume'] = {'sd_noise': SD_NOISE, 'sd_rater': SD_RATER, 'sd_sent': SD_SENT}
print('假设：评分噪声 σ=%.2f，评分人偏置 σ=%.2f，句子难度 σ=%.2f（五分制）'
      % (SD_NOISE, SD_RATER, SD_SENT))


def trial_abs(delta, n_rater, n_sent, g, paired):
    """绝对 MOS。paired=True 表示同一批人同时听两套系统（组内设计）"""
    rb = g.standard_normal(n_rater) * SD_RATER
    se = g.standard_normal(n_sent) * SD_SENT
    base = 3.9
    def score(mu, rb_, se_):
        s = base + mu + rb_[:, None] + se_[None, :] \
            + g.standard_normal((n_rater, n_sent)) * SD_NOISE
        return np.clip(np.round(np.clip(s, 1, 5)), 1, 5)      # 五分制、整数
    if paired:
        a = score(0.0, rb, se); b = score(delta, rb, se)
    else:
        rb2 = g.standard_normal(n_rater) * SD_RATER
        se2 = g.standard_normal(n_sent) * SD_SENT
        a = score(0.0, rb, se); b = score(delta, rb2, se2)
    return b.mean() - a.mean(), a, b


def power_abs(delta, n_rater, n_sent, paired, reps=3000, alpha=0.05):
    g = np.random.default_rng(7)
    hit = 0
    for _ in range(reps):
        d, a, b = trial_abs(delta, n_rater, n_sent, g, paired)
        # 以评分人为单位做配对 / 独立 t 检验
        if paired:
            x = b.mean(1) - a.mean(1)
            se = x.std(ddof=1) / math.sqrt(len(x)) + 1e-12
            t = x.mean() / se
        else:
            xa, xb = a.mean(1), b.mean(1)
            se = math.sqrt(xa.var(ddof=1) / len(xa) + xb.var(ddof=1) / len(xb)) + 1e-12
            t = (xb.mean() - xa.mean()) / se
        hit += abs(t) > 1.96
    return hit / reps


print('\n① 绝对 MOS：要看出 ΔMOS 才需要多少人 × 多少句（功效 = 检出率，目标 80%）')
OUT['mos'] = []
for delta in (0.05, 0.10, 0.20, 0.30):
    row = {'delta': delta, 'paired': {}, 'indep': {}}
    for n_sent in (10, 20, 50):
        for n_rater in (10, 20, 40, 80, 160):
            p = power_abs(delta, n_rater, n_sent, True, reps=1200)
            if p >= 0.8:
                row['paired']['%d句' % n_sent] = n_rater
                break
        else:
            row['paired']['%d句' % n_sent] = None
        for n_rater in (10, 20, 40, 80, 160, 320):
            p = power_abs(delta, n_rater, n_sent, False, reps=1200)
            if p >= 0.8:
                row['indep']['%d句' % n_sent] = n_rater
                break
        else:
            row['indep']['%d句' % n_sent] = None
    OUT['mos'].append(row)
    print('   ΔMOS=%.2f  组内设计需要 %s   独立设计需要 %s'
          % (delta, row['paired'], row['indep']))
print('   <strong>同一批人同时听两套系统</strong>，人数需求差一个量级——')
print('   因为评分人偏置被差分掉了。这是听测设计里最省钱的一招。')

# ══ ② CMOS ══════════════════════════════════════════════════
SD_CMOS = 1.10       # 七分制 (-3..+3) 上的评分噪声


def power_cmos(delta, n_rater, n_sent, reps=3000):
    g = np.random.default_rng(9)
    hit = 0
    for _ in range(reps):
        s = delta + g.standard_normal((n_rater, n_sent)) * SD_CMOS
        s = np.clip(np.round(s), -3, 3)
        x = s.mean(1)
        se = x.std(ddof=1) / math.sqrt(n_rater) + 1e-12
        hit += abs(x.mean() / se) > 1.96
    return hit / reps


print('\n② CMOS（直接比 A/B，七分制），同样要 80%% 功效：')
OUT['cmos'] = []
for delta in (0.05, 0.10, 0.20, 0.30):
    got = None
    for n_rater in (5, 10, 20, 40, 80, 160):
        if power_cmos(delta, n_rater, 20, reps=1500) >= 0.8:
            got = n_rater
            break
    OUT['cmos'].append({'delta': delta, 'raters_20sent': got})
    print('   Δ=%.2f 分  20 句时需要 %s 位评分人' % (delta, got if got else '>160'))
print('   CMOS 把"两套系统的共同难度"直接消掉了，所以它才是迭代时该用的指标。')

# ══ ③ 可懂度：ASR 回环要多少句 ═══════════════════════════════
def power_wer(w1, w2, n_sent, chars_per_sent=18, reps=4000):
    g = np.random.default_rng(3)
    n = n_sent * chars_per_sent
    hit = 0
    for _ in range(reps):
        a = g.binomial(n, w1) / n
        b = g.binomial(n, w2) / n
        p = (a + b) / 2
        se = math.sqrt(2 * p * (1 - p) / n) + 1e-12
        hit += abs(a - b) / se > 1.96
    return hit / reps


print('\n③ 用 ASR 回环测可懂度（假设每句 18 个字）：')
OUT['wer'] = []
for w1, w2 in ((0.03, 0.035), (0.03, 0.04), (0.03, 0.05), (0.03, 0.06)):
    got = None
    for n in (50, 100, 200, 500, 1000, 2000, 5000):
        if power_wer(w1, w2, n) >= 0.8:
            got = n
            break
    OUT['wer'].append({'w1': w1, 'w2': w2, 'sents': got})
    print('   CER %.1f%% vs %.1f%%  需要 %s 句' % (w1 * 100, w2 * 100,
                                                 got if got else '>5000'))
print('   <strong>客观指标便宜得多</strong>：几百句就能测出 1 个百分点的可懂度差，')
print('   而同等把握的 MOS 要几十个人。所以：客观指标守底线，主观指标定成败。')

# ══ ④ 首包延迟预算 ═══════════════════════════════════════════
def budget(name, items):
    tot = sum(v for _, v in items)
    OUT.setdefault('latency', []).append({'name': name, 'items': items,
                                          'total': round(tot, 1)})
    print('\n   %s' % name)
    for k, v in items:
        print('      %-26s %6.1f ms' % (k, v))
    print('      %-26s %6.1f ms  %s' % ('合计', tot,
                                        '✓ 够快' if tot < 300 else '✗ 能感觉到'))


print('\n④ 首包延迟预算（从"文本到齐"到"第一个音频包出声"）')
budget('服务端 · 流匹配 16 步 + HiFi-GAN', [
    ('文本归一化 + G2P', 8.0), ('韵律 / 时长预测', 4.0),
    ('声学模型 16 步 × 3 ms', 48.0), ('声码器（0.5 s 块）', 12.0),
    ('音频封包与抖动缓冲', 40.0), ('网络单程', 30.0)])
budget('服务端 · LLM-TTS 自回归 8 级 token', [
    ('文本归一化 + G2P', 8.0), ('首 token 前填充（prefill）', 60.0),
    ('凑够解码首块 25 帧 × 8 级 × 1.2 ms', 240.0),
    ('声码器', 15.0), ('音频封包与抖动缓冲', 40.0), ('网络单程', 30.0)])
budget('端侧 · 小模型 + 轻量声码器', [
    ('文本归一化 + G2P', 12.0), ('韵律 / 时长预测', 6.0),
    ('声学模型 4 步 × 9 ms', 36.0), ('声码器（0.25 s 块）', 55.0),
    ('音频输出缓冲', 30.0)])

# ══ ⑤ 算力：按结构把乘加数点出来 ════════════════════════════
# 不引用任何"别人测的 RTF"，直接按 HiFi-GAN V1 的结构数乘加。
def hifigan_macs(ch0=512, ups=(8, 8, 2, 2), k_pre=7, k_post=7,
                 res_k=(3, 7, 11), res_d=(1, 3, 5), nmel=80, hop=256):
    """返回 (每个输出样点的 MAC 数, 各段占比)。
       约定：转置卷积核长 = 2×步长；MRF 每个 kernel 有 3 个 dilation，
       每个 dilation 两层卷积（HiFi-GAN 的 ResBlock1）。"""
    parts = {}
    rate = 1.0 / hop                                   # 相对输出采样率
    ch = ch0
    parts['conv_pre'] = nmel * ch * k_pre * rate
    for u in ups:
        # 转置卷积：ch → ch/2，核长 2u，输出率 = rate*u
        parts.setdefault('upsample', 0.0)
        parts['upsample'] += ch * (ch // 2) * (2 * u) * rate
        rate *= u
        ch //= 2
        mrf = 0.0
        for k in res_k:
            for d in res_d:
                mrf += 2 * ch * ch * k * rate          # 两层：dilated + 普通
        parts.setdefault('MRF', 0.0)
        parts['MRF'] += mrf
    parts['conv_post'] = ch * 1 * k_post * rate
    tot = sum(parts.values())
    return tot, {k: round(v / tot * 100, 1) for k, v in parts.items()}, parts


tot, frac, parts = hifigan_macs()
OUT['flops'] = {'hifigan_v1_mac_per_sample': round(tot, 0),
                'hifigan_v1_gmac_22k': round(tot * 22050 / 1e9, 2),
                'frac': frac}
print('\n⑤ 算力：直接按 HiFi-GAN V1 的结构数乘加')
print('   每个输出样点 %.0f MAC → 22.05 kHz 下 %.2f GMAC/s（≈ %.1f GFLOP/s）'
      % (tot, tot * 22050 / 1e9, tot * 22050 * 2 / 1e9))
for k, v in sorted(frac.items(), key=lambda x: -x[1]):
    print('      %-10s %5.1f%%   (%.0f MAC/样点)' % (k, v, parts[k]))
print('   <strong>算力几乎全在 MRF 上</strong>——那些并行的多尺度空洞卷积。')

OUT['variants'] = []
for name, kw in (('V1（ch 512，MRF 3×3）', {}),
                 ('V2（ch 128）', {'ch0': 128}),
                 ('V3（ch 256，MRF 只留一个核宽）', {'ch0': 256, 'res_k': (3,)}),
                 ('BigVGAN 式（反混叠，内部 2×）', {})):
    t_, f_, _ = hifigan_macs(**kw)
    if name.startswith('BigVGAN'):
        t_ *= 2.0                                      # 上采 2× 做激活再降回来
    gf = t_ * 22050 * 2 / 1e9
    OUT['variants'].append({'name': name, 'mac': round(t_, 0),
                            'gflops': round(gf, 2), 'rtf8': round(gf / 8.0, 2)})
    print('   %-32s %8.0f MAC/样点  %6.2f GFLOP/s  8 GFLOPS 的手机大核上 RTF %.2f'
          % (name, t_, gf, gf / 8.0))
print('   （RTF < 1 才跑得动，实时还要留余量；这也解释了端侧为什么用 V3 而不是 V1。）')

json.dump(OUT, open('demo_eval.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_eval.json')
