#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两件让这一族方法真正能用的事：判决引导，和噪声功率谱估计。

   上一节把噪声功率谱当成已知真值。现实里它必须估，
   而且要在<有语音的时候>估。这一节量两件事：
   ① 判决引导的 α 在换什么（音乐噪声 ↔ 瞬态拖尾）
   ② MS / MCRA / IMCRA 的追踪延迟、偏差，以及它们各自要花掉多少 dB
"""
import numpy as np, json
from scipy.special import exp1
import enhlib as E
from enhlib import g_logmmse, dd_xi, est_ms, est_mcra, est_imcra

OUT = {}
NFFT, HOP = 512, 256
FR_MS = HOP / E.SR * 1000.0
x, segs = E.make_speech(dur=8.0, seed=1)
m = E.speech_mask(segs, len(x))
OUT['fr_ms'] = round(FR_MS, 1)


# ══ ① 判决引导的 α ════════════════════════════════════════════
v = E.make_noise('pink', len(x), seed=3)
y, vv = E.mix_at_snr(x, v, 5.0, m)
lam_true = np.mean(np.abs(E.stft(vv, NFFT, HOP)) ** 2, axis=0)[None, :]
S = E.stft(x[:len(y)], NFFT, HOP)
V = E.stft(vv[:len(y)], NFFT, HOP)
Y = E.stft(y, NFFT, HOP)
fm = E.frame_mask(m, len(S), NFFT, HOP)

def onset_probe(alpha, gam_hi_db=6.0, n=600):
    """受控实验，<把窗的影响完全去掉>：直接喂判决引导一段确定性的 γ 序列——
       前 20 帧 γ=1（纯噪声），之后跳到 γ_hi 并保持。量两件事：

       ① 上升时间：增益爬到<它自己的>稳态 90% 要几帧；
       ② 稳态偏差：这个稳态离"信噪比完全已知"时的增益差多少 dB。

       第二件事常被忽略，但它才是判决引导真正的代价——
       递归的不动点满足 ξ = α·ξ²γ/(1+ξ)² + (1−α)(γ−1)，
       而 ξ²γ/(1+ξ)² < γ−1，所以 <strong>ξ̂ 系统性地偏小</strong>。
    """
    gh = 10 ** (gam_hi_db / 10)
    gam = np.concatenate([np.ones(20), np.full(n, gh)])
    xi_min = 10 ** (-25 / 10)
    xi = np.zeros(len(gam))
    prev = 0.0
    for l in range(len(gam)):
        ml = max(gam[l] - 1.0, 0.0)
        xi[l] = max(alpha * prev + (1 - alpha) * ml, xi_min)
        g = xi[l] / (1.0 + xi[l])
        prev = g ** 2 * gam[l]
    G = g_logmmse(xi, gam)
    lo, hi = G[:18].mean(), G[-20:].mean()
    thr = lo + 0.9 * (hi - lo)
    k = int(np.argmax(G[20:] >= thr)) if (G[20:] >= thr).any() else -1
    ideal = float(g_logmmse(np.array([gh - 1.0]), np.array([gh]))[0])
    bias = float(20 * np.log10(max(hi, 1e-6) / ideal))
    xbias = float(10 * np.log10(max(xi[-20:].mean(), 1e-9) / (gh - 1.0)))
    return k, bias, xbias, [round(float(20 * np.log10(max(v, 1e-4))), 2) for v in G[:110]]


def onset_probe_stft(alpha, bin_snr_db=6.0, f=700.0, seed=5):
    """同一件事，但走完整的 STFT 通路——用来看窗本身贡献了多少拖尾"""
    sil, tone = 0.6, 0.7
    n = int((sil + tone) * E.SR)
    t = np.arange(n) / E.SR
    k0 = int(sil * E.SR)
    nz = E.make_noise('white', n, seed=seed + 1) * 0.1
    Vp = E.stft(nz, NFFT, HOP)
    kf = int(round(f / E.SR * NFFT))
    lam_k = float(np.mean(np.abs(Vp[:, kf]) ** 2))
    sig = np.zeros(n); sig[k0:] = np.sin(2 * np.pi * f * t[k0:])
    Sp = E.stft(sig, NFFT, HOP)
    p_k = float(np.mean(np.abs(Sp[len(Sp) // 2:, kf]) ** 2)) + E.EPS
    obs = np.sqrt(lam_k * 10 ** (bin_snr_db / 10) / p_k) * sig + nz
    lam = np.full((1, NFFT // 2 + 1), np.mean(np.abs(Vp) ** 2))
    Yp = E.stft(obs, NFFT, HOP)
    xi, gam = dd_xi(Yp, lam, alpha)
    tr = g_logmmse(xi, gam)[:, kf]
    o = int(k0 / HOP)
    lo, hi = tr[max(0, o - 8):o - 2].mean(), tr[-12:].mean()
    if hi - lo < 1e-3:
        return float('nan')
    thr = lo + 0.9 * (hi - lo)
    return int(np.argmax(tr[o:] >= thr)) if (tr[o:] >= thr).any() else -1


print('① 判决引导（decision-directed）的 α 在换什么')
print('  %6s %9s %9s %8s %7s %7s %9s'
      % ('α', '语音失真', '残留噪声', 'SegSNR', 'LSD', 'STOI*', '起伏dB'))
OUT['alpha'] = []
for a in (0.0, 0.5, 0.9, 0.95, 0.98, 0.99, 0.995):
    xi, gam = dd_xi(Y, lam_true, a)
    G = g_logmmse(xi, gam)
    z = E.istft(G * Y, NFFT, HOP, n=len(y))
    d = E.decompose(S, V, G)
    dly, _b, _xb, _t = onset_probe(a)
    r = {'alpha': a, 'sd_db': round(d['sd_db'], 2), 'nr_db': round(d['nr_db'], 2),
         'segsnr': round(E.seg_snr(x, z, m), 2), 'lsd': round(E.lsd(x, z, mask=m), 2),
         'stoi': round(E.stoi_like(x, z, mask=m), 3),
         'mus': round(E.musical(G * V, fm), 2),
         'kurt': round(E.kurt_ratio(G * V, V, fm), 2),
         'onset_fr': round(dly, 2), 'onset_ms': round(dly * FR_MS, 1)}
    OUT['alpha'].append(r)
    print('  %6.3f %8.1f %8.1f %8.2f %7.2f %7.3f %8.2f   起始拖尾 %.1f 帧 = %.0f ms'
          % (a, r['sd_db'], r['nr_db'], r['segsnr'], r['lsd'], r['stoi'],
             r['mus'], r['onset_fr'], r['onset_ms']))
a0 = OUT['alpha'][0]; a98 = [r for r in OUT['alpha'] if r['alpha'] == 0.98][0]
print('  α=0（纯瞬时最大似然）起伏 %.1f dB；α=0.98 降到 %.1f dB——'
      % (a0['mus'], a98['mus']))
print('  <strong>音乐噪声几乎全部是"ξ 跟着当前帧的噪声实现抖"造成的</strong>。')
print('  代价在下一张表，而且不是"变慢"这么简单——见 ⑴ 的稳态偏差列。')

# 为什么有效：直接量噪声段里"增益本身"抖得有多厉害
print('\n  机制：噪声段里增益自己的帧间起伏（dB）')
OUT['gvar'] = []
nz = ~fm
for a in (0.0, 0.5, 0.9, 0.95, 0.98, 0.995):
    xi, gam = dd_xi(Y, lam_true, a)
    G = g_logmmse(xi, gam)
    gl = 20 * np.log10(np.maximum(G[nz], 1e-4))
    sd = float(np.mean(np.std(gl, axis=0)))
    k, bias, xbias, tr = onset_probe(a)
    ks = onset_probe_stft(a)
    OUT['gvar'].append({'alpha': a, 'g_sd_db': round(sd, 2),
                        'onset_fr': int(k), 'onset_ms': round(k * FR_MS, 1),
                        'gain_bias_db': round(bias, 2), 'xi_bias_db': round(xbias, 2),
                        'stft_fr': (int(ks) if ks == ks else None),
                        'traj': tr})
    print('    α = %.3f   增益起伏 %5.2f dB   上升 %2d 帧 = %4.0f ms'
          '   稳态 ξ 偏差 %+5.2f dB   增益偏差 %+5.2f dB'
          % (a, sd, k, k * FR_MS, xbias, bias))
print('    增益越平稳，残差就越像原来的噪声（听着像"底噪"而不是"音乐"）。')
print('    但同一个平稳性也让它<strong>跟不上语音的起始</strong>——这是同一枚硬币。')

# ══ ①b 判决引导其实是一个"开关" ═══════════════════════════════
def dd_fix(alpha, gam_db, n=4000, xi0=0.0, xi_min_db=-25.0):
    """固定 γ 时判决引导递归的不动点"""
    gh = 10 ** (gam_db / 10)
    xi_min = 10 ** (xi_min_db / 10)
    prev = xi0
    xi = xi_min
    for _ in range(n):
        xi = max(alpha * prev + (1 - alpha) * max(gh - 1.0, 0.0), xi_min)
        g = xi / (1.0 + xi)
        prev = g * g * gh
    return xi


print('\n①b 一个没料到的性质：判决引导不是平滑的估计器，是一个<strong>开关</strong>')
print('   固定 γ，看递归收敛到哪里（从静音状态启动）')
OUT['capture'] = {}
for a in (0.9, 0.95, 0.98, 0.99):
    row = []
    for gdb in np.arange(1.0, 16.1, 0.25):
        xi = dd_fix(a, float(gdb))
        row.append({'gam_db': round(float(gdb), 2),
                    'xi_db': round(float(10 * np.log10(max(xi, 1e-9))), 3),
                    'true_db': round(float(10 * np.log10(max(10 ** (gdb / 10) - 1, 1e-9))), 3)})
    # 捕获阈值：ξ̂ 第一次进到真值 3 dB 以内的那个 γ
    thr = None
    for r in row:
        if r['xi_db'] > r['true_db'] - 3.0:
            thr = r['gam_db']
            break
    OUT['capture'][str(a)] = {'curve': row, 'thr_db': thr}
    print('   α = %.2f   捕获阈值 γ ≈ %s dB' % (a, ('%.2f' % thr) if thr else '—'))
print('   低于这个阈值的频点，ξ̂ 直接塌到下限（增益 ≈ −25 dB），语音成分被整个抹掉；')
print('   高于它，ξ̂ 几乎等于真值。<strong>中间没有过渡带</strong>。')
print('   这解释了三件一直被当成"调参玄学"的事：')
print('     ① 为什么 α=0.98 的降噪听起来特别干净——弱分量根本没留下；')
print('     ② 为什么它"吃掉气声和辅音尾巴"——那些正好在阈值以下；')
print('     ③ 为什么 ξ 下限（xi_min）这个参数的影响那么大——它就是被抹掉那部分的增益。')

# ══ ② 噪声功率谱估计 ══════════════════════════════════════════
print('\n② 噪声功率谱怎么估：三个经典做法，在同一段信号上比')
OUT['est'] = []
P = np.abs(Y) ** 2
lam_ref = np.abs(V) ** 2                                          # 逐帧真值
lam_ref_s = np.zeros_like(lam_ref)
ss = lam_ref[0].copy()
for l in range(len(lam_ref)):                                     # 真值也平滑一下再比
    ss = 0.85 * ss + 0.15 * lam_ref[l]
    lam_ref_s[l] = ss
print('  %-10s %10s %10s %9s %8s %7s' %
      ('估计器', '静音段偏差', '语音段偏差', 'SegSNR', 'LSD', '起伏dB'))
for tag, f in (('最小统计量 MS', est_ms), ('MCRA', est_mcra), ('IMCRA', est_imcra)):
    lam = f(P)
    b_sil = float(np.mean(10 * np.log10((lam[~fm] + E.EPS) / (lam_ref_s[~fm] + E.EPS))))
    b_spc = float(np.mean(10 * np.log10((lam[fm] + E.EPS) / (lam_ref_s[fm] + E.EPS))))
    xi, gam = dd_xi(Y, lam, 0.98)
    G = g_logmmse(xi, gam)
    z = E.istft(G * Y, NFFT, HOP, n=len(y))
    r = {'tag': tag, 'bias_sil': round(b_sil, 2), 'bias_spc': round(b_spc, 2),
         'segsnr': round(E.seg_snr(x, z, m), 2), 'lsd': round(E.lsd(x, z, mask=m), 2),
         'stoi': round(E.stoi_like(x, z, mask=m), 3),
         'mus': round(E.musical(G * V, fm), 2)}
    OUT['est'].append(r)
    print('  %-10s %+9.2f dB %+9.2f dB %8.2f %8.2f %7.2f'
          % (tag, b_sil, b_spc, r['segsnr'], r['lsd'], r['mus']))
xi, gam = dd_xi(Y, lam_true, 0.98)
G = g_logmmse(xi, gam)
z = E.istft(G * Y, NFFT, HOP, n=len(y))
OUT['oracle'] = {'tag': '真值（上一节用的）', 'bias_sil': 0.0, 'bias_spc': 0.0,
                 'segsnr': round(E.seg_snr(x, z, m), 2),
                 'lsd': round(E.lsd(x, z, mask=m), 2),
                 'stoi': round(E.stoi_like(x, z, mask=m), 3),
                 'mus': round(E.musical(G * V, fm), 2)}
print('  %-10s %+9.2f dB %+9.2f dB %8.2f %8.2f %7.2f   ← 上一节的上界'
      % ('真值', 0.0, 0.0, OUT['oracle']['segsnr'], OUT['oracle']['lsd'],
         OUT['oracle']['mus']))
best = max(OUT['est'], key=lambda r: r['segsnr'])
OUT['est_cost'] = round(OUT['oracle']['segsnr'] - best['segsnr'], 2)
print('  <strong>噪声估计这一步就花掉 %.2f dB</strong>（最好的估计器 vs 真值）。'
      % OUT['est_cost'])

# ══ ②b 噪声估计的代价，取决于噪声平不平稳 ═════════════════════
print('\n②b 上面那 %.2f dB 是在平稳粉噪上量的。换成非平稳噪声呢？' % OUT['est_cost'])
OUT['est_by_noise'] = []
for kind in ('car', 'pink', 'white', 'babble'):
    vk = E.make_noise(kind, len(x), seed=3)
    yk, vk2 = E.mix_at_snr(x, vk, 5.0, m)
    Yk = E.stft(yk, NFFT, HOP)
    Vk = E.stft(vk2, NFFT, HOP)
    Pk = np.abs(Yk) ** 2
    lam_o = np.mean(np.abs(Vk) ** 2, axis=0)[None, :]
    res = {}
    for tag, lam in (('oracle', lam_o), ('imcra', est_imcra(Pk)), ('ms', est_ms(Pk))):
        xi, gam = dd_xi(Yk, lam, 0.98)
        G = g_logmmse(xi, gam)
        z = E.istft(G * Yk, NFFT, HOP, n=len(yk))
        res[tag] = round(E.seg_snr(x, z, m), 2)
    r = {'kind': kind, 'nonstat': round(E.nonstat(Vk), 2),
         'oracle': res['oracle'], 'imcra': res['imcra'], 'ms': res['ms'],
         'cost': round(res['oracle'] - max(res['imcra'], res['ms']), 2)}
    OUT['est_by_noise'].append(r)
    print('   %-7s 非平稳度 %5.2f dB   真值 %5.2f  IMCRA %5.2f  MS %5.2f   '
          '→ 估计代价 %.2f dB' % (kind, r['nonstat'], r['oracle'], r['imcra'],
                              r['ms'], r['cost']))
print('   <strong>噪声越不平稳，"估不准"这件事越贵</strong>——'
      '而真实场景里的噪声全都在右边那一栏。')

# ══ ③ 追踪延迟：噪声突然变大 12 dB ═════════════════════════════
print('\n③ 噪声阶跃上升 12 dB，各估计器要多久才跟上')
vst = E.make_noise('step', len(x), seed=3)
yst, vst2 = E.mix_at_snr(x, vst, 5.0, m)
Yst = E.stft(yst, NFFT, HOP)
Pst = np.abs(Yst) ** 2
Vst = E.stft(vst2, NFFT, HOP)
step_fr = len(Pst) // 2
OUT['step'] = {'step_fr': int(step_fr), 'jump_db': 12.0, 'traj': {}}
true_lo = float(np.mean(np.abs(Vst[:step_fr - 20]) ** 2))
true_hi = float(np.mean(np.abs(Vst[step_fr + 20:]) ** 2))
OUT['step']['true_jump_db'] = round(10 * np.log10(true_hi / true_lo), 2)
for tag, f in (('ms', est_ms), ('mcra', est_mcra), ('imcra', est_imcra)):
    lam = f(Pst)
    tr = np.mean(lam, axis=1)
    OUT['step']['traj'][tag] = [round(float(10 * np.log10(t + E.EPS)), 3) for t in tr]
    tgt = np.mean(lam[-40:])
    base = np.mean(lam[step_fr - 60:step_fr - 10])
    thr = base * 10 ** ((10 * np.log10(tgt / base) - 3) / 10)     # 到"差 3 dB"为止
    k = np.argmax(tr[step_fr:] >= thr)
    OUT['step'][tag + '_delay_fr'] = int(k)
    OUT['step'][tag + '_delay_ms'] = round(k * FR_MS, 1)
    print('  %-6s 追上（差 3 dB 以内）用了 %3d 帧 = %5.0f ms' % (tag, k, k * FR_MS))
OUT['step']['true_traj'] = [round(float(10 * np.log10(np.mean(np.abs(Vst[l]) ** 2) + E.EPS)), 3)
                            for l in range(len(Vst))]
print('  这段延迟里增益是<strong>按旧的、偏小的噪声算的</strong>，所以噪声会整个漏出来。')
print('  这就是"开窗、开空调、走进地铁"时降噪会失灵一两秒的原因。')

json.dump(OUT, open('demo_dd.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_dd.json')
