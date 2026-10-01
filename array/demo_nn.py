#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§20 算例：掩码估错了会怎样。
   同一份掩码，一条路直接拿去乘（纯神经增强的等价物），
   一条路只拿去估协方差再解 MVDR / GEV（mask-based 波束）。
   看两条路对掩码误差的敏感度差多少。"""
import numpy as np, json, math
import scipy.linalg as sla

rng = np.random.default_rng(20260930)
S = json.load(open('demo_scene.json'))['scene']
FS, M = S['fs'], S['M']
NFFT, HOP = 512, 256
xs, xi, xd = np.load('demo_xs.npy'), np.load('demo_xi.npy'), np.load('demo_xd.npy')
L = min(x.shape[1] for x in (xs, xi, xd))
xs, xi, xd = xs[:, :L], xi[:, :L], xd[:, :L]


def stft(z):
    w = np.hanning(NFFT + 1)[:-1]
    idx = np.arange(0, z.shape[1] - NFFT, HOP)
    return np.array([[np.fft.rfft(z[m, i:i + NFFT] * w) for i in idx]
                     for m in range(z.shape[0])]).transpose(0, 2, 1)


XS, XN = stft(xs), stft(xi + xd)
X = XS + XN
Mn, F, T = X.shape
ps, pn = np.abs(XS[0]) ** 2, np.abs(XN[0]) ** 2
IN_SNR = 10 * math.log10(ps.sum() / pn.sum())
OUT = {'in_snr': round(IN_SNR, 2), 'F': F, 'T': T}
print('输入 SNR（参考麦）%.2f dB   STFT %d×%d' % (IN_SNR, F, T))

# ══ 理想比值掩码，以及"网络出错"的模型 ═══════════════════════
irm = ps / (ps + pn + 1e-20)


def smooth2d(z, kt, kf):
    """在时频面上做一次矩形平滑，用来制造"成片错"的误差"""
    if kt > 1:
        z = np.apply_along_axis(lambda v: np.convolve(v, np.ones(kt) / kt, 'same'), 1, z)
    if kf > 1:
        z = np.apply_along_axis(lambda v: np.convolve(v, np.ones(kf) / kf, 'same'), 0, z)
    return z


def degrade(m, beta, seed, kt=1, kf=1):
    """β 混进一份随机掩码：β=0 是神仙掩码，β=1 等于瞎猜。
       kt/kf > 1 时误差在时频面上成片出现——这才像一个网络真正的错法"""
    g = np.random.default_rng(seed)
    u = g.random(m.shape)
    if kt > 1 or kf > 1:
        u = smooth2d(u, kt, kf)
        u = (u - u.mean()) / (u.std() + 1e-12) * 0.29 + 0.5     # 还原成 U(0,1) 的均值方差
        u = np.clip(u, 0, 1)
    return np.clip((1 - beta) * m + beta * u, 0.0, 1.0)


def snr_sd(ys, yn, ref):
    """输出 SNR，以及"目标被改成了什么样"（把最佳线性增益除掉后的残差）"""
    a = (ref.ravel().conj() @ ys.ravel()) / (ref.ravel().conj() @ ref.ravel())
    sd = 10 * math.log10(np.sum(np.abs(a * ref) ** 2) /
                         (np.sum(np.abs(ys - a * ref) ** 2) + 1e-20))
    return 10 * math.log10(np.sum(np.abs(ys) ** 2) / np.sum(np.abs(yn) ** 2)), sd


def run_mask(m):
    """① 直接乘：网络出什么就拿什么"""
    return snr_sd(m * XS[0], m * XN[0], XS[0])


def run_bf(m, kind='mvdr', eps=1e-6):
    """② 只拿掩码估协方差，滤波器本身是每频点一个固定的 w（线性时不变）"""
    ys = np.zeros((F, T), complex); yn = np.zeros((F, T), complex)
    for f in range(F):
        Xf = X[:, f, :]
        wa = m[f] / (m[f].sum() + 1e-9)
        wb = (1 - m[f]) / ((1 - m[f]).sum() + 1e-9)
        Rs = (Xf * wa) @ Xf.conj().T
        Rn = (Xf * wb) @ Xf.conj().T
        Rn += eps * np.trace(Rn).real / M * np.eye(M)
        if kind == 'mvdr':
            a = np.linalg.eigh(Rs)[1][:, -1]
            a = a * np.exp(-1j * np.angle(a[0]))
            Ri = np.linalg.solve(Rn, a)
            w = Ri / (a.conj() @ Ri)
        else:                                            # GEV + BAN
            w = sla.eigh(Rs, Rn)[1][:, -1]
            num = math.sqrt(abs(w.conj() @ Rn @ Rn @ w) / M)
            w = w * num / abs(w.conj() @ Rn @ w)
        ys[f] = w.conj() @ XS[:, f, :]
        yn[f] = w.conj() @ XN[:, f, :]
    return snr_sd(ys, yn, XS[0])


BETA = [0.0, 0.1, 0.2, 0.35, 0.5, 0.7, 1.0]
OUT['beta'] = BETA
for kind, kt, kf in [('iid', 1, 1), ('blk', 25, 9)]:
    OUT[kind] = {'macc': {}, 'mask': {}, 'mvdr': {}, 'gev': {}}
    print('\n【%s】β 混进随机掩码；"掩码误差"是 |m̂−m| 的平均'
          % ('逐格独立出错' if kind == 'iid' else '成片出错（25 帧 × 9 频点）'))
    print('  β    掩码误差   直接乘 SNR / 失真      MVDR SNR / 失真      GEV SNR / 失真')
    NS = 5                                              # 每个点跑 5 个随机实现取中位数
    for bt in BETA:
        er, A_, B_, C_ = [], [], [], []
        for sd in range(NS):
            mh = degrade(irm, bt, int(bt * 100) + 1 + 977 * sd, kt, kf)
            er.append(np.mean(np.abs(mh - irm)))
            A_.append(run_mask(mh)); B_.append(run_bf(mh, 'mvdr')); C_.append(run_bf(mh, 'gev'))
        err = float(np.median(er))
        a = np.median(np.array(A_), 0); b = np.median(np.array(B_), 0); c = np.median(np.array(C_), 0)
        OUT[kind]['macc'][bt] = round(err, 4)
        OUT[kind]['mask'][bt] = [round(a[0], 2), round(a[1], 2)]
        OUT[kind]['mvdr'][bt] = [round(b[0], 2), round(b[1], 2)]
        OUT[kind]['gev'][bt] = [round(c[0], 2), round(c[1], 2)]
        print('%4.2f    %6.3f   %7.2f / %6.2f      %7.2f / %6.2f     %7.2f / %6.2f'
              % (bt, err, a[0], a[1], b[0], b[1], c[0], c[1]))

# ══ 为什么波束那条线是平的：看导向向量动没动 ═══════════════
def steervec(m):
    A = np.zeros((F, M), complex)
    for f in range(F):
        Xf = X[:, f, :]; w = m[f] / m[f].sum()
        v = np.linalg.eigh((Xf * w) @ Xf.conj().T)[1][:, -1]
        A[f] = v * np.exp(-1j * np.angle(v[0]))
    return A


def steer_true():
    A = np.zeros((F, M), complex)
    for f in range(F):
        Sf = XS[:, f, :]
        v = np.linalg.eigh(Sf @ Sf.conj().T)[1][:, -1]
        A[f] = v * np.exp(-1j * np.angle(v[0]))
    return A


fr = np.fft.rfftfreq(NFFT, 1 / FS); bd = (fr >= 200) & (fr <= 4000)


def cosmed(A, B):
    c = np.abs(np.sum(A.conj() * B, 1)) / (np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1))
    return float(np.median(c[bd]))


A0, Ai = steer_true(), steervec(irm)
OUT['steer'] = {'ideal_vs_true': round(cosmed(Ai, A0), 4), 'cos': {}}
print('\n导向向量（R_s 的主特征向量）跟着掩码动了多少，200–4 kHz 中位 cos：')
print('   理想掩码 vs 纯目标协方差            %.4f' % OUT['steer']['ideal_vs_true'])
for bt in (0.2, 0.5, 1.0):
    A = steervec(degrade(irm, bt, 7))
    OUT['steer']['cos'][bt] = round(cosmed(A, Ai), 4)
    print('   β=%.1f 的掩码 vs 理想掩码            %.4f' % (bt, OUT['steer']['cos'][bt]))
Aadv = steervec(np.clip(1 - irm, 1e-3, 1))
OUT['steer']['adv'] = round(cosmed(Aadv, Ai), 4)
adv = run_bf(np.clip(1 - irm, 1e-3, 1), 'mvdr')
OUT['adv_mvdr'] = [round(adv[0], 2), round(adv[1], 2)]
print('   把掩码整个反过来（对抗性错法）         %.4f' % OUT['steer']['adv'])
print('   这时 MVDR 的 SNR / 失真：%.2f / %.2f dB ← 这才是它真正的边界'
      % (OUT['adv_mvdr'][0], OUT['adv_mvdr'][1]))

# ══ "线性" 到底是什么意思：把掩码换成固定权重后，失真为零 ═══
OUT['note'] = {}
m0 = degrade(irm, 0.5, 201)
ys_m = m0 * XS[0]
a = (XS[0].ravel().conj() @ ys_m.ravel()) / (XS[0].ravel().conj() @ XS[0].ravel())
OUT['note']['mask_artifact_pct'] = round(float(
    np.sum(np.abs(ys_m - a * XS[0]) ** 2) / np.sum(np.abs(ys_m) ** 2)) * 100, 1)
print('\nβ=0.5 时，直接乘的输出里有 %.1f%% 的能量无法用"对目标做一次线性滤波"解释'
      % OUT['note']['mask_artifact_pct'])
print('（波束那一路这个数恒为 0——每个频点只有一个固定的 w，定义上就是线性时不变）')

# ══ 算力对照 ═════════════════════════════════════════════════
OUT['cost'] = {'mvdr_mul_per_bin': M * M * 2 + M ** 3 // 3,
               'mask_mul_per_bin': 1}
json.dump(OUT, open('demo_nn.json', 'w'), ensure_ascii=False, indent=1)
