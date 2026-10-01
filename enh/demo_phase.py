#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""被忽略的那一半：相位；以及决定一切的那个约束：延迟。

   前两节所有的方法都只改幅度、把带噪相位原样放回去。
   这一节量一下这件事到底花了多少，以及为什么几十年里大家都觉得它不值得管。
   然后是延迟预算——它比任何算法选择都更能决定你能做到多好。
"""
import numpy as np, json
import enhlib as E
from enhlib import est_imcra, dd_xi, g_logmmse

OUT = {}
x, segs = E.make_speech(dur=6.0, seed=1)
m = E.speech_mask(segs, len(x))
v = E.make_noise('pink', len(x), seed=3)


def swap(mag_from, ph_from, nfft, hop, n):
    """用一个信号的幅度 + 另一个信号的相位重构"""
    A = np.abs(E.stft(mag_from, nfft, hop))
    P = np.angle(E.stft(ph_from, nfft, hop))
    return E.istft(A * np.exp(1j * P), nfft, hop, n=n)


# ══ ① 幅度和相位，哪个更值钱 ══════════════════════════════════
print('① 拿一个信号的幅度配另一个信号的相位')
NFFT, HOP = 512, 256
OUT['swap'] = []
for snr in (-5.0, 0.0, 5.0, 10.0, 15.0):
    y, vv = E.mix_at_snr(x, v, snr, m)
    n = len(y)
    a = swap(x[:n], y, NFFT, HOP, n)          # 干净幅度 + 带噪相位
    b = swap(y, x[:n], NFFT, HOP, n)          # 带噪幅度 + 干净相位
    r = {'snr': snr,
         'noisy': round(E.seg_snr(x, y, m), 2),
         'cm_np': round(E.seg_snr(x, a, m), 2),
         'nm_cp': round(E.seg_snr(x, b, m), 2),
         'cm_np_stoi': round(E.stoi_like(x, a, mask=m), 3),
         'nm_cp_stoi': round(E.stoi_like(x, b, mask=m), 3),
         'noisy_stoi': round(E.stoi_like(x, y, mask=m), 3)}
    OUT['swap'].append(r)
    print('  输入 %5.1f dB   带噪 %6.2f   干净幅度+带噪相位 %6.2f   带噪幅度+干净相位 %6.2f'
          % (snr, r['noisy'], r['cm_np'], r['nm_cp']))
lo, hi = OUT['swap'][0], OUT['swap'][-1]
print('  低信噪比时"只修幅度"几乎拿不到东西（%.2f dB），'
      '高信噪比时它几乎拿到全部（%.2f dB）。' % (lo['cm_np'], hi['cm_np']))
print('  <strong>相位的重要性随信噪比下降而上升</strong>——'
      '这正好和"只改幅度"这个传统做法冲突。')

# ══ ② 机制检验：重叠相加的冗余，真的能纠回错的相位吗 ═════════
print('\n② 我的解释是"重叠越多，错的相位越能被邻帧纠回来"。直接扫重叠率验证：')
OUT['overlap'] = []
y, vv = E.mix_at_snr(x, v, 5.0, m)
n = len(y)
for ov in (2, 4, 8, 16):
    nf = 512
    hp = nf // ov
    a = swap(x[:n], y, nf, hp, n)
    r = {'ov': ov, 'hop': hp, 'hop_ms': round(hp / E.SR * 1000, 1),
         'cm_np': round(E.seg_snr(x, a, m), 2),
         'stoi': round(E.stoi_like(x, a, mask=m), 3)}
    OUT['overlap'].append(r)
    print('   重叠 %2d× （帧移 %4.1f ms）  干净幅度+带噪相位 → %6.2f dB   STOI* %.3f'
          % (ov, r['hop_ms'], r['cm_np'], r['stoi']))
d = OUT['overlap'][-1]['cm_np'] - OUT['overlap'][0]['cm_np']
OUT['overlap_gain'] = round(d, 2)
print('   从 2× 到 16×，只拿到 %.2f dB。方向对，<strong>但量级太小</strong>——' % d)
print('   撑不起"短窗系统可以不管相位"这个说法。算力却要翻 8 倍，'
      '而且帧移变小并不降低算法延迟（延迟由窗长决定）。')

print('\n②b 换窗长（重叠固定 50%）：')
OUT['swap_win'] = []
for nf in (64, 128, 256, 512, 1024, 2048):
    hp = nf // 2
    a = swap(x[:n], y, nf, hp, n)
    b = swap(y, x[:n], nf, hp, n)
    r = {'nfft': nf, 'ms': round(nf / E.SR * 1000, 1),
         'cm_np': round(E.seg_snr(x, a, m), 2),
         'nm_cp': round(E.seg_snr(x, b, m), 2)}
    OUT['swap_win'].append(r)
    print('   窗 %5d 点 = %5.1f ms   干净幅度+带噪相位 %6.2f   带噪幅度+干净相位 %6.2f'
          % (nf, r['ms'], r['cm_np'], r['nm_cp']))
print('   <strong>窗长本身也几乎不影响</strong>（%.2f → %.2f dB，跨了 32 倍窗长）。'
      % (OUT['swap_win'][0]['cm_np'], OUT['swap_win'][-1]['cm_np']))
print('   合起来的结论和我原先的假说相反：相位重不重要，'
      '<strong>几乎只由信噪比决定</strong>（见 ①），')
print('   和变换参数关系很小。"短窗可以不管相位"这个流传很广的说法，在这里没被支持。')

# ══ ③ 幅度的天花板，和相位还值多少 ════════════════════════════
print('\n③ 只改幅度的方法，天花板在哪')
OUT['mask'] = []
for snr in (0.0, 5.0, 10.0):
    y2, vv2 = E.mix_at_snr(x, v, snr, m)
    n2 = len(y2)
    S = E.stft(x[:n2], NFFT, HOP); V = E.stft(vv2[:n2], NFFT, HOP)
    Y = E.stft(y2, NFFT, HOP)
    irm = np.sqrt(np.abs(S) ** 2 / (np.abs(S) ** 2 + np.abs(V) ** 2 + E.EPS))
    z_irm = E.istft(irm * Y, NFFT, HOP, n=n2)                  # 理想比值掩码 + 带噪相位
    z_irm_cp = E.istft(irm * np.abs(Y) * np.exp(1j * np.angle(S)), NFFT, HOP, n=n2)
    z_iam = E.istft(np.abs(S) * np.exp(1j * np.angle(Y)), NFFT, HOP, n=n2)
    z_iam_cp = E.istft(np.abs(S) * np.exp(1j * np.angle(S)), NFFT, HOP, n=n2)
    r = {'snr': snr,
         'irm': round(E.seg_snr(x, z_irm, m), 2),
         'irm_cp': round(E.seg_snr(x, z_irm_cp, m), 2),
         'iam': round(E.seg_snr(x, z_iam, m), 2),
         'irm_stoi': round(E.stoi_like(x, z_irm, mask=m), 3),
         'irm_cp_stoi': round(E.stoi_like(x, z_irm_cp, mask=m), 3),
         'iam_stoi': round(E.stoi_like(x, z_iam, mask=m), 3)}
    r['phase_worth'] = round(r['irm_cp'] - r['irm'], 2)
    OUT['mask'].append(r)
    print('  输入 %4.1f dB   理想比值掩码 %6.2f   理想幅度掩码 %6.2f   '
          '把相位也换成干净的 %6.2f   → 相位值 %.2f dB'
          % (snr, r['irm'], r['iam'], r['irm_cp'], r['phase_worth']))
print('  中间那一栏是<strong>所有只改幅度的方法的天花板</strong>——'
      '谱减、维纳、log-MMSE 都在它下面，')
print('  只预测幅度掩码的神经网络也在它下面。最后一栏是"把相位也做对"能再拿多少。')
pw = [r['phase_worth'] for r in OUT['mask']]
print('  相位在低信噪比时更值钱（%.2f dB @ 0 dB vs %.2f dB @ 10 dB）——'
      % (pw[0], pw[-1]))
print('  <strong>而低信噪比正是你最需要降噪的时候</strong>。这就是复数域方法的全部动机。')

# ══ ④ 延迟预算 ════════════════════════════════════════════════
print('\n④ 延迟预算：这是比算法选择更硬的约束')
print('  重叠相加的算法延迟 = 一个窗长（要等窗填满）+ 一个帧移（块处理）')
OUT['latency'] = []
for nf in (32, 64, 128, 256, 512, 1024):
    hp = nf // 2
    y, vv = E.mix_at_snr(x, v, 5.0, m)
    n = len(y)
    S = E.stft(x[:n], nf, hp); V = E.stft(vv[:n], nf, hp); Y = E.stft(y, nf, hp)
    irm = np.sqrt(np.abs(S) ** 2 / (np.abs(S) ** 2 + np.abs(V) ** 2 + E.EPS))
    z = E.istft(irm * Y, nf, hp, n=n)
    df = E.SR / nf
    r = {'nfft': nf, 'win_ms': round(nf / E.SR * 1000, 2),
         'hop_ms': round(hp / E.SR * 1000, 2),
         'lat_ms': round((nf + hp) / E.SR * 1000, 2),
         'df_hz': round(df, 1),
         'irm_segsnr': round(E.seg_snr(x, z, m), 2),
         'irm_lsd': round(E.lsd(x, z, nfft=512, hop=256, mask=m), 2),
         'irm_stoi': round(E.stoi_like(x, z, mask=m), 3)}
    OUT['latency'].append(r)
    print('  窗 %4d 点 = %5.2f ms   算法延迟 %6.2f ms   频率分辨率 %6.1f Hz'
          '   理想掩码能到 %6.2f dB' % (nf, r['win_ms'], r['lat_ms'], r['df_hz'],
                                 r['irm_segsnr']))
print('\n④b 同一个扫描，换成非平稳噪声（babble）：时频分辨率在这里才值钱')
OUT['latency_babble'] = []
vb = E.make_noise('babble', len(x), seed=3)
yb, vb2 = E.mix_at_snr(x, vb, 5.0, m)
nb = len(yb)
for nf in (32, 64, 128, 256, 512, 1024):
    hp = nf // 2
    Sb = E.stft(x[:nb], nf, hp); Vb = E.stft(vb2[:nb], nf, hp); Yb = E.stft(yb, nf, hp)
    irmb = np.sqrt(np.abs(Sb) ** 2 / (np.abs(Sb) ** 2 + np.abs(Vb) ** 2 + E.EPS))
    zb = E.istft(irmb * Yb, nf, hp, n=nb)
    r = {'nfft': nf, 'win_ms': round(nf / E.SR * 1000, 2),
         'lat_ms': round((nf + hp) / E.SR * 1000, 2),
         'irm_segsnr': round(E.seg_snr(x, zb, m), 2),
         'irm_stoi': round(E.stoi_like(x, zb, mask=m), 3)}
    OUT['latency_babble'].append(r)
    print('   窗 %4d 点 = %5.2f ms   延迟 %6.2f ms   理想掩码能到 %6.2f dB   STOI* %.3f'
          % (nf, r['win_ms'], r['lat_ms'], r['irm_segsnr'], r['irm_stoi']))
gp = OUT['latency_babble'][-1]['irm_segsnr'] - OUT['latency_babble'][0]['irm_segsnr']
gp2 = OUT['latency'][-1]['irm_segsnr'] - OUT['latency'][0]['irm_segsnr']
OUT['res_gain'] = {'pink': round(gp2, 2), 'babble': round(gp, 2)}
print('   2 ms → 64 ms 的窗：平稳粉噪多拿 %.2f dB，babble 多拿 %.2f dB。'
      % (gp2, gp))
print('   我本来预期 babble 会明显更依赖分辨率。<strong>没有</strong>——两条线几乎一样平。')
print('   原因是"理想掩码"这个上界太宽松：它知道每个时频点的真实信噪比，')
print('   哪怕一个 2 ms 的粗格子里语音和噪声混在一起，它也能给出最优的折中增益。')
print('   分辨率真正影响的不是上界，是<strong>现实中估得准不准</strong>——下面这张表才是。')

print('\n④c 换成现实方法（log-MMSE + IMCRA，什么真值都不给）：')
OUT['latency_real'] = []
for kind in ('pink', 'babble'):
    vk = E.make_noise(kind, len(x), seed=3)
    yk, vk2 = E.mix_at_snr(x, vk, 5.0, m)
    nk = len(yk)
    row = []
    for nf in (32, 64, 128, 256, 512, 1024):
        hp = nf // 2
        Yk = E.stft(yk, nf, hp)
        lam = est_imcra(np.abs(Yk) ** 2)
        xi, gam = dd_xi(Yk, lam, 0.98)
        G = g_logmmse(xi, gam)
        zk = E.istft(G * Yk, nf, hp, n=nk)
        row.append({'nfft': nf, 'win_ms': round(nf / E.SR * 1000, 2),
                    'lat_ms': round((nf + hp) / E.SR * 1000, 2),
                    'segsnr': round(E.seg_snr(x, zk, m), 2),
                    'stoi': round(E.stoi_like(x, zk, mask=m), 3),
                    'lsd': round(E.lsd(x, zk, mask=m), 2)})
    OUT['latency_real'].append({'kind': kind, 'rows': row})
    d = row[-1]['segsnr'] - row[0]['segsnr']
    print('   %-7s  ' % kind + '  '.join('%.0fms:%.2f' % (r['win_ms'], r['segsnr'])
                                         for r in row) + '   跨度 %.2f dB' % d)
pk = OUT['latency_real'][0]['rows']; bb = OUT['latency_real'][1]['rows']
bp = max(pk, key=lambda r: r['segsnr']); bb2 = max(bb, key=lambda r: r['segsnr'])
OUT['best_win'] = {'pink': bp['win_ms'], 'babble': bb2['win_ms'],
                   'pink_span': round(max(r['segsnr'] for r in pk)
                                      - min(r['segsnr'] for r in pk), 2),
                   'babble_span': round(max(r['segsnr'] for r in bb)
                                        - min(r['segsnr'] for r in bb), 2)}
print('   平稳噪声：窗越长越好，到 %g ms 饱和（跨度 %.2f dB）。'
      % (bp['win_ms'], OUT['best_win']['pink_span']))
print('   非平稳噪声：<strong>有最优点，在 %g ms</strong>，再长反而变差——'
      % bb2['win_ms'])
print('   窗长到一定程度就开始把噪声自己的时间结构抹平，估计器就跟不上了。')
print('   <strong>所以窗长买的不是"分得开"，是"估得准"</strong>；'
      '而对非平稳噪声，"估得准"和"跟得上"是矛盾的。')


f0 = 130.0
need = 4 * E.SR / f0                                 # 汉宁窗主瓣宽度 = 4·fs/N
OUT['resolve'] = {'f0': f0, 'need_pts': int(np.ceil(need)),
                  'need_ms': round(need / E.SR * 1000, 1)}
print('  要分辨基频 %g Hz 的相邻谐波，汉宁窗主瓣宽度 4·fs/N 必须小于 %g Hz，'
      % (f0, f0))
print('  也就是窗长至少 %d 点 = %.1f ms。'
      % (OUT['resolve']['need_pts'], OUT['resolve']['need_ms']))
tiers = [('耳机 / 助听 / 实时监听', 10.0), ('通话与会议', 40.0), ('识别 / 唤醒前端', 200.0)]
OUT['tiers'] = []
for tag, budget in tiers:
    ok = [r for r in OUT['latency'] if r['lat_ms'] <= budget]
    best = max(ok, key=lambda r: r['nfft']) if ok else None
    r = {'tag': tag, 'budget_ms': budget,
         'best_win_ms': best['win_ms'] if best else None,
         'best_lat_ms': best['lat_ms'] if best else None,
         'ceiling': best['irm_segsnr'] if best else None,
         'df_hz': best['df_hz'] if best else None,
         'resolves_f0': bool(best and best['win_ms'] >= OUT['resolve']['need_ms'])}
    OUT['tiers'].append(r)
    print('  %-18s 预算 %5.0f ms → 最长可用窗 %5.2f ms，'
          '理想掩码上限 %5.2f dB，%s分辨基频谐波'
          % (tag, budget, r['best_win_ms'], r['ceiling'],
             '能' if r['resolves_f0'] else '<strong>不能</strong>'))
t0, t2 = OUT['tiers'][0], OUT['tiers'][-1]
OUT['tier_gap'] = round(t2['ceiling'] - t0['ceiling'], 2)
print('  同一个<strong>完美</strong>的掩码，耳机档和前端档差 %.2f dB——'
      '而这一步还没开始谈算法。' % OUT['tier_gap'])

json.dump(OUT, open('demo_phase.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_phase.json')
