#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出什么：掩码 / 映射 / 复数——把"天花板"和"实际拿到的"分开量。

   三件事：
   ① 四种输出参数化的 oracle 上界（知道干净语音时能做到多好）。
      顺带回答一个我原以为不用问的问题：理想幅度掩码真的落在 [0,1] 里吗。
   ② 复数理想掩码的动态范围——为什么它"上界最高、最难学"。
   ③ 同一个容量的网络分别去回归这四个目标，看上界和实得的落差。
"""
import numpy as np, json, time
import enhlib as E
import nnlib as N
from nnlib import NFFT, HOP, NBIN, make_pair, featurize, train, fwd, sig

OUT = {}
SNRS = (-5.0, 0.0, 5.0, 10.0, 15.0)
TRAIN_NOISE = ('white', 'pink', 'car')
UNSEEN = 'babble'
t0 = time.time()


# ══ oracle：各种"理想掩码"直接拿去重建 ════════════════════════
def oracle(kind, snr, seed, which):
    x, y, m, S, V, Y = make_pair(seed, kind, snr)
    A = np.abs(Y) + E.EPS
    if which == 'irm':                      # 维纳式，天然落在 [0,1]
        G = np.sqrt(np.abs(S) ** 2 / (np.abs(S) ** 2 + np.abs(V) ** 2 + E.EPS))
        Z = G * Y
    elif which == 'iam':                    # 理想幅度掩码 |S|/|Y|，不设上界
        G = np.abs(S) / A
        Z = G * Y
    elif which == 'iam1':                   # 同上，但钳到 1——"有界掩码"的真实天花板
        G = np.minimum(np.abs(S) / A, 1.0)
        Z = G * Y
    elif which == 'cirm':                   # 复数理想掩码 S/Y
        Z = S
    z = E.istft(Z, NFFT, HOP, n=len(y))[:len(y)]
    fm = E.frame_mask(m, len(S), NFFT, HOP)
    return (E.seg_snr(x, z, m), E.lsd(x, z, mask=m), E.stoi_like(x, z, mask=m),
            np.abs(S) / A, fm)


print('① 四种理想掩码的上界（每档 3 种噪声 × 2 个随机种子）')
OUT['ceiling'] = []
for snr in SNRS:
    row = {'snr': snr}
    for which in ('irm', 'iam1', 'iam', 'cirm'):
        rs = [oracle(k, snr, sd, which)[:3]
              for k in TRAIN_NOISE for sd in (700, 701)]
        a = np.mean(rs, 0)
        row[which] = {'segsnr': round(float(a[0]), 2),
                      'lsd': round(float(a[1]), 2),
                      'stoi': round(float(a[2]), 3)}
    OUT['ceiling'].append(row)
    print('  %+5.1f dB  IRM %5.2f  IAM钳到1 %5.2f  IAM不钳 %5.2f  复数 %6.2f  (SegSNR)'
          % (snr, row['irm']['segsnr'], row['iam1']['segsnr'],
             row['iam']['segsnr'], row['cirm']['segsnr']))

# ══ ② 理想幅度掩码到底有多少落在 [0,1] 外 ═════════════════════
print('\n② 理想幅度掩码 |S|/|Y| 的分布——"它本来就在 [0,1] 里"对不对')
OUT['clip'] = []
for snr in SNRS:
    fr, p99, pmax, wsh = [], [], [], []
    for k in TRAIN_NOISE:
        for sd in (700, 701):
            _, _, _, G, fm = oracle(k, snr, sd, 'iam')
            g = G[fm > 0.5] if fm.sum() > 0 else G.ravel()
            fr.append(float(np.mean(g > 1.0)))
            p99.append(float(np.percentile(g, 99)))
            pmax.append(float(g.max()))
            # 被钳掉的那部分占了多少能量损失（dB）
            wsh.append(float(np.sum(np.maximum(g - 1.0, 0) ** 2) /
                             max(np.sum(g ** 2), 1e-12)))
    r = {'snr': snr, 'frac_gt1': round(float(np.mean(fr)) * 100, 2),
         'p99': round(float(np.mean(p99)), 2),
         'pmax': round(float(np.mean(pmax)), 1),
         'eshare': round(float(np.mean(wsh)) * 100, 2)}
    OUT['clip'].append(r)
    print('  %+5.1f dB  超过 1 的格子 %5.2f%%   99 分位 %4.2f   最大 %6.1f'
          % (snr, r['frac_gt1'], r['p99'], r['pmax']))
cl = {r['snr']: r for r in OUT['clip']}
ce = {r['snr']: r for r in OUT['ceiling']}
OUT['clip_cost'] = [{'snr': s,
                     'cost_db': round(ce[s]['iam']['segsnr'] - ce[s]['iam1']['segsnr'], 2),
                     'frac_gt1': cl[s]['frac_gt1']} for s in SNRS]
print('  钳到 1 的代价：' + '  '.join('%+.0f dB→%.2f dB' % (r['snr'], r['cost_db'])
                                      for r in OUT['clip_cost']))

# ══ ③ 复数理想掩码的动态范围 ══════════════════════════════════
print('\n③ 复数理想掩码 S/Y 的动态范围（和实数掩码对比）')
OUT['range'] = []
for snr in (0.0, 5.0):
    mg_i, mg_c, tail = [], [], []
    for k in TRAIN_NOISE:
        for sd in (700, 701):
            x, y, m, S, V, Y = make_pair(sd, k, snr)
            fm = E.frame_mask(m, len(S), NFFT, HOP)
            sel = fm > 0.5
            C = S / (Y + E.EPS)
            mc = np.abs(C[sel]); mi = (np.abs(S) / (np.abs(Y) + E.EPS))[sel]
            mg_c.append([float(np.percentile(mc, p)) for p in (50, 90, 99, 99.9)])
            mg_i.append([float(np.percentile(mi, p)) for p in (50, 90, 99, 99.9)])
            tail.append(float(np.mean(mc > 2.0)))
    c = np.mean(mg_c, 0); i_ = np.mean(mg_i, 0)
    r = {'snr': snr,
         'cirm': [round(float(v), 2) for v in c],
         'iam': [round(float(v), 2) for v in i_],
         'frac_gt2': round(float(np.mean(tail)) * 100, 2),
         'dyn_ratio': round(float(c[3] / max(c[0], 1e-9)), 1)}
    OUT['range'].append(r)
    print('  %+.0f dB  |cIRM| 分位 50/90/99/99.9 = %s   >2 的占 %.2f%%   动态范围 %.0f×'
          % (snr, '/'.join('%.2f' % v for v in c), r['frac_gt2'], r['dyn_ratio']))

# ══ ④ 同一容量的网络去回归这四个目标 ══════════════════════════
print('\n④ 上界 vs 实得：同一个网络（两隐层 128/96），只换输出参数化')


def build(nset, kinds, seed0, snrs=SNRS):
    Xs, Ss, Vs, Ys = [], [], [], []
    for i in range(nset):
        k = kinds[i % len(kinds)]
        snr = snrs[i % len(snrs)]
        _, _, _, S, V, Y = make_pair(seed0 + i, k, snr)
        Xs.append(featurize(Y)); Ss.append(S); Vs.append(V); Ys.append(Y)
    return (np.concatenate(Xs), np.concatenate(Ss),
            np.concatenate(Vs), np.concatenate(Ys))


Xtr, Str, Vtr, Ytr = build(36, TRAIN_NOISE, 100)
Atr = np.abs(Ytr) + E.EPS
T_IRM = np.sqrt(np.abs(Str) ** 2 / (np.abs(Str) ** 2 + np.abs(Vtr) ** 2 + E.EPS))
T_IAM1 = np.minimum(np.abs(Str) / Atr, 1.0)
T_IAM = np.clip(np.abs(Str) / Atr, 0, 4.0)
CK, CC = 10.0, 0.1                      # 压缩常数，取自 DCCRN 那一支的常用值
C_RAW = np.clip((Str / (Ytr + E.EPS)), -CK, CK)
T_CR = np.stack([C_RAW.real, C_RAW.imag], -1).reshape(len(Str), -1)
comp = lambda v: CK * (1 - np.exp(-CC * v)) / (1 + np.exp(-CC * v))
icomp = lambda u: -1.0 / CC * np.log(np.clip((CK - u) / (CK + u), 1e-6, None))
T_CC = comp(T_CR)
print('   压缩前后 99.9 分位：%.2f → %.2f' %
      (np.percentile(np.abs(T_CR), 99.9), np.percentile(np.abs(T_CC), 99.9)))


def mk_sig_loss(T):
    def f(o, i):
        p = sig(o); d = p - T[i]
        return float(np.mean(d ** 2)), 2 * d * p * (1 - p) / o.shape[1]
    return f


def mk_lin_loss(T):
    """线性输出。按目标自身的 RMS 归一化，使各参数化的梯度量级可比——
       否则比的是学习率，不是参数化。"""
    sc = float(np.std(T)) + 1e-9

    def f(o, i):
        d = (o - T[i]) / sc
        return float(np.mean(d ** 2)), 2 * d / sc / o.shape[1]
    return f


def mk_tanh_loss(T, k=CK):
    sc = float(np.std(T)) + 1e-9

    def f(o, i):
        th = np.tanh(np.clip(o, -10, 10))
        d = (k * th - T[i]) / sc
        return float(np.mean(d ** 2)), 2 * d / sc * k * (1 - th ** 2) / o.shape[1]
    return f


SPECS = [
    ('IRM（sigmoid，有界）', NBIN, mk_sig_loss(T_IRM), 'sig', 'irm'),
    ('IAM 钳到 1（sigmoid）', NBIN, mk_sig_loss(T_IAM1), 'sig', 'iam1'),
    ('IAM 不设上界（线性）', NBIN, mk_lin_loss(T_IAM), 'lin', 'iam'),
    ('复数掩码（线性，不压缩）', 2 * NBIN, mk_lin_loss(T_CR), 'cplx', 'cirm'),
    ('复数掩码（tanh 压缩）', 2 * NBIN, mk_tanh_loss(T_CC), 'cplxc', 'cirm'),
]


def apply_model(P, Y, mode):
    _, _, _, _, o = fwd(P, featurize(Y))
    if mode == 'sig':
        return sig(o) * Y
    if mode == 'lin':
        return np.clip(o, 0, 4.0) * Y
    if mode in ('cplx', 'cplxc'):
        u = o if mode == 'cplx' else CK * np.tanh(np.clip(o, -10, 10))
        v = u.reshape(len(Y), NBIN, 2)
        if mode == 'cplxc':
            v = icomp(np.clip(v, -CK + 1e-3, CK - 1e-3))
        return (v[..., 0] + 1j * v[..., 1]) * Y


def evaluate(P, mode, kinds, snr=5.0, seeds=(900, 901, 902)):
    rs = []
    for k in kinds:
        for sd in seeds:
            x, y, m, S, V, Y = make_pair(sd, k, snr)
            Z = apply_model(P, Y, mode)
            z = E.istft(Z, NFFT, HOP, n=len(y))[:len(y)]
            rs.append((E.seg_snr(x, z, m), E.lsd(x, z, mask=m),
                       E.stoi_like(x, z, mask=m)))
    a = np.mean(rs, 0)
    return dict(segsnr=round(float(a[0]), 2), lsd=round(float(a[1]), 2),
                stoi=round(float(a[2]), 3))


c5 = ce[5.0]
OUT['achieved'] = []
LRS = (1e-3, 3e-3, 1e-2)
for tag, dout, lf, mode, ckey in SPECS:
    cands = []
    for lr in LRS:                      # 每种参数化各给三个学习率，取它自己最好的那个
        P, npar = train(Xtr, dout, lf, lr=lr, tag='%s lr=%g' % (tag, lr),
                        out_zero=True)
        cands.append((evaluate(P, mode, TRAIN_NOISE, seeds=(910, 911)), lr, P, npar))
    dev, lr_best, P, npar = max(cands, key=lambda c: c[0]['segsnr'])
    seen = evaluate(P, mode, TRAIN_NOISE)
    unseen = evaluate(P, mode, (UNSEEN,))
    cap = c5[ckey]['segsnr']
    OUT['achieved'].append({
        'tag': tag, 'params': npar, 'ceiling': cap, 'seen': seen, 'unseen': unseen,
        'lr': lr_best, 'gap': round(cap - seen['segsnr'], 2),
        'realized': round(seen['segsnr'] / cap * 100, 1)})
print('  %-26s %7s %8s %8s %8s %7s' % ('输出参数化', '参数', '上界', '实得', '兑现率', 'lr'))
for r in OUT['achieved']:
    print('  %-26s %7d %8.2f %8.2f %7.1f%% %7g'
          % (r['tag'], r['params'], r['ceiling'], r['seen']['segsnr'],
             r['realized'], r['lr']))

best_ceil = max(OUT['achieved'], key=lambda r: r['ceiling'])
best_real = max(OUT['achieved'], key=lambda r: r['seen']['segsnr'])
OUT['summary'] = {
    'best_ceiling': best_ceil['tag'], 'best_achieved': best_real['tag'],
    'cirm_raw_gap': [r['gap'] for r in OUT['achieved'] if r['tag'].startswith('复数掩码（线性')][0],
    'cirm_comp_gap': [r['gap'] for r in OUT['achieved'] if r['tag'].startswith('复数掩码（tanh')][0],
    'irm_gap': OUT['achieved'][0]['gap'],
    'clip_cost_0db': [r['cost_db'] for r in OUT['clip_cost'] if r['snr'] == 0.0][0],
    'frac_gt1_0db': [r['frac_gt1'] for r in OUT['clip'] if r['snr'] == 0.0][0],
}
OUT['const'] = {'ck': CK, 'cc': CC, 'nbin': NBIN,
                'snrs': list(SNRS), 'train_noise': list(TRAIN_NOISE),
                'unseen': UNSEEN}
OUT['runtime_s'] = round(time.time() - t0, 1)
json.dump(OUT, open('demo_out.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_out.json（%.0f s）' % OUT['runtime_s'])
