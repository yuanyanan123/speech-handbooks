#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§19 算例：两个说话人同时说，在 12 节那间房间里。
   量四件事：① W-disjoint 到底成不成立 ② 理想二值掩码的 SIR 天花板
             ③ 盲空间聚类为什么会翻车（排列问题）④ GSS 的先验值多少 dB"""
import numpy as np, json, math
import pyroomacoustics as pra
rng = np.random.default_rng(20260929)
c = 343.0
S = json.load(open('demo_scene.json'))['scene']
ROOM = [6.0, 5.0, 3.3]; RT60 = 0.6; FS = S['fs']
M, D = S['M'], S['d_mm'] / 1000
CTR = np.array(S['ctr'])
NFFT, HOP = 512, 256
TH_A, R_A = 60.0, 1.5          # 说话人 A（就是全书那个目标）
TH_B, R_B = 130.0, 2.2         # 说话人 B（原来放风扇的位置，现在坐了个人）


def pos(th, r):
    return CTR + r * np.array([math.cos(math.radians(th)), math.sin(math.radians(th)), 0])


mics = np.c_[[CTR + np.array([(m - (M - 1) / 2) * D, 0, 0]) for m in range(M)]].T
e_abs, mo = pra.inverse_sabine(RT60, ROOM)


def sim(p, sig):
    room = pra.ShoeBox(ROOM, fs=FS, materials=pra.Material(e_abs), max_order=mo)
    room.add_microphone_array(pra.MicrophoneArray(mics, FS))
    room.add_source(list(p), signal=sig)
    room.simulate()
    return room.mic_array.signals


def carrier(n, f0b, seed):
    """浊音载体：基频 + 25 次谐波 + 音节级起伏"""
    g = np.random.default_rng(seed)
    t = np.arange(n) / FS
    f0 = f0b + 0.2 * f0b * np.sin(2 * np.pi * (1.3 + 0.4 * g.random()) * t + g.random() * 6)
    ph = 2 * np.pi * np.cumsum(f0) / FS
    x = sum(np.sin(k * ph) / k for k in range(1, 26))
    syl = 0.35 + 0.65 * np.abs(np.sin(2 * np.pi * 3.4 * t + g.random() * 6))   # 音节
    return x * syl


def turns(n, want_overlap=0.25, seed=5):
    """会话式轮次：A、B 交替说，按 want_overlap 的比例故意重叠"""
    g = np.random.default_rng(seed)
    ea, eb = np.zeros(n), np.zeros(n)
    i, who = 0, 0
    while i < n:
        L = int(g.uniform(1.0, 2.6) * FS)                     # 一个轮次 1–2.6 s
        (ea if who == 0 else eb)[i:i + L] = 1.0
        if g.random() < want_overlap * 2:                      # 抢话：下一轮提前开口
            i += int(L * g.uniform(0.45, 0.8))
        else:
            i += L + int(g.uniform(0.1, 0.5) * FS)             # 正常换手留个间隙
        who ^= 1
    sm = np.hanning(1601) / np.hanning(1601).sum()
    return np.convolve(ea, sm, 'same'), np.convolve(eb, sm, 'same')


N = FS * 24
ea, eb = turns(N)
sa = carrier(N, 115.0, 11) * ea
sb = carrier(N, 190.0, 22) * eb
sa /= np.max(np.abs(sa)); sb /= np.max(np.abs(sb))       # 男声 / 女声基频
xa, xb = sim(pos(TH_A, R_A), sa), sim(pos(TH_B, R_B), sb)
L = min(xa.shape[1], xb.shape[1], N); xa, xb = xa[:, :L], xb[:, :L]
xa /= np.sqrt(np.mean(xa ** 2)); xb /= np.sqrt(np.mean(xb ** 2))   # 等响
x = xa + xb

# 重叠率：两人同时有能量的帧占比
def act(z, thr_db=-25):
    e = np.array([np.mean(z[0, i:i + NFFT] ** 2) for i in range(0, L - NFFT, HOP)])
    return e > 10 ** (thr_db / 10) * np.mean(e)


aA, aB = act(xa), act(xb)
OUT = {'scene': {'th_a': TH_A, 'th_b': TH_B, 'r_a': R_A, 'r_b': R_B,
                 'dur_s': round(L / FS, 1), 'nfft': NFFT, 'hop': HOP},
       'overlap': round(float(np.mean(aA & aB) / max(np.mean(aA | aB), 1e-9)) * 100, 1),
       'act_a': round(float(np.mean(aA)) * 100, 1), 'act_b': round(float(np.mean(aB)) * 100, 1)}
print('说话人 A 有声 %.1f%%，B 有声 %.1f%%，重叠占"有人说话"的 %.1f%%'
      % (OUT['act_a'], OUT['act_b'], OUT['overlap']))


def stft(z):
    w = np.hanning(NFFT + 1)[:-1]
    idx = np.arange(0, z.shape[1] - NFFT, HOP)
    return np.array([[np.fft.rfft(z[m, i:i + NFFT] * w) for i in idx]
                     for m in range(z.shape[0])]).transpose(0, 2, 1)   # (M,F,T)


XA, XB = stft(xa), stft(xb)
X = XA + XB
Mn, F, T = X.shape
print('STFT: %d 频点 × %d 帧' % (F, T))

# ══ ① W-disjoint orthogonality ══════════════════════════════
pa, pb = np.abs(XA[0]) ** 2, np.abs(XB[0]) ** 2
tot = pa + pb
live = tot > 1e-6 * tot.mean()                     # 只看有能量的格子
rdb = 10 * np.log10((pa[live] + 1e-20) / (pb[live] + 1e-20))
OUT['wdo'] = {}
for thr in (0, 3, 6, 10, 20):
    OUT['wdo'][thr] = round(float(np.mean(np.abs(rdb) > thr)) * 100, 1)
print('\n① W-disjoint：主导源领先对方 >X dB 的格子占比')
for k, v in OUT['wdo'].items():
    print('   >%2d dB : %5.1f%%' % (k, v))

# ══ ② 理想二值掩码的天花板 ═══════════════════════════════════
def sir(est_a, ref_a, ref_b):
    """把估计投影到 a 上，算剩下的 b 占多少"""
    num = np.sum(np.abs(est_a * (ref_a != 0)) ** 2)
    return num


def mask_sir(msk):
    """掩码作用在混合上，A 分量 / B 分量"""
    ya, yb = msk * XA[0], msk * XB[0]
    return 10 * math.log10(np.sum(np.abs(ya) ** 2) / np.sum(np.abs(yb) ** 2))


def mask_sdr(msk):
    """掩码输出对"干净 A"的失真：投影后残差"""
    y = (msk * X[0]).ravel(); r = XA[0].ravel()
    a = (r.conj() @ y) / (r.conj() @ r)
    return 10 * math.log10(np.sum(np.abs(a * r) ** 2) / np.sum(np.abs(y - a * r) ** 2))


ibm = (pa > pb).astype(float)
irm = pa / (tot + 1e-20)
OUT['in_sir'] = round(10 * math.log10(np.sum(pa) / np.sum(pb)), 2)
OUT['ibm'] = {'sir': round(mask_sir(ibm), 2), 'sdr': round(mask_sdr(ibm), 2)}
OUT['irm'] = {'sir': round(mask_sir(irm), 2), 'sdr': round(mask_sdr(irm), 2)}
print('\n② 掩码天花板（单通道，只靠掩码）')
print('   不处理           SIR %6.2f dB' % OUT['in_sir'])
print('   理想二值掩码 IBM SIR %6.2f dB   SDR %6.2f dB' % (OUT['ibm']['sir'], OUT['ibm']['sdr']))
print('   理想比值掩码 IRM SIR %6.2f dB   SDR %6.2f dB' % (OUT['irm']['sir'], OUT['irm']['sdr']))

# ══ 掩码 → MVDR ══════════════════════════════════════════════
def mask_mvdr(gA, gB, ref=0, eps=1e-6):
    """按掩码估协方差，主特征向量当导向，解 MVDR；返回 (F,T) 输出"""
    Y = np.zeros((F, T), complex)
    for f in range(F):
        Xf = X[:, f, :]                                   # (M,T)
        wa = gA[f] / (gA[f].sum() + 1e-9)
        wb = gB[f] / (gB[f].sum() + 1e-9)
        Ra = (Xf * wa) @ Xf.conj().T
        Rn = (Xf * wb) @ Xf.conj().T
        Rn += eps * np.trace(Rn).real / M * np.eye(M)
        ev, V = np.linalg.eigh(Ra)
        a = V[:, -1]
        a = a * np.exp(-1j * np.angle(a[ref]))            # 参考通道定相
        Ri = np.linalg.solve(Rn, a)
        w = Ri / (a.conj() @ Ri)
        Y[f] = w.conj() @ Xf
    return Y


def sep_gev(gA, gB, ban=True):
    """放弃 rank-1：直接解广义特征问题 max w^H Ra w / w^H Rb w"""
    import scipy.linalg as sla
    ya = np.zeros((F, T), complex); yb = np.zeros((F, T), complex)
    for f in range(F):
        Xf = X[:, f, :]
        wa = gA[f] / (gA[f].sum() + 1e-9); wb = gB[f] / (gB[f].sum() + 1e-9)
        Ra = (Xf * wa) @ Xf.conj().T
        Rn = (Xf * wb) @ Xf.conj().T
        Rn += 1e-6 * np.trace(Rn).real / M * np.eye(M)
        w = sla.eigh(Ra, Rn)[1][:, -1]
        if ban:                                   # 17 节那个 BAN 盲解析归一化
            num = math.sqrt(abs(w.conj() @ Rn @ Rn @ w) / M)
            w = w * num / abs(w.conj() @ Rn @ w)
        ya[f] = w.conj() @ XA[:, f, :]
        yb[f] = w.conj() @ XB[:, f, :]
    return 10 * math.log10(np.sum(np.abs(ya) ** 2) / np.sum(np.abs(yb) ** 2))


def oracle_cov_sir(rank1, ban=True):
    """连掩码都不估了，直接拿纯 A / 纯 B 的协方差：空间上的绝对上限"""
    import scipy.linalg as sla
    ya = np.zeros((F, T), complex); yb = np.zeros((F, T), complex)
    lam1 = []
    for f in range(F):
        A_, B_ = XA[:, f, :], XB[:, f, :]
        Ra = A_ @ A_.conj().T / T; Rb = B_ @ B_.conj().T / T
        lam1.append(np.linalg.eigvalsh(Ra)[::-1])
        Rb = Rb + 1e-6 * np.trace(Rb).real / M * np.eye(M)
        if rank1:
            a = np.linalg.eigh(Ra)[1][:, -1]; a = a * np.exp(-1j * np.angle(a[0]))
            Ri = np.linalg.solve(Rb, a); w = Ri / (a.conj() @ Ri)
        else:
            w = sla.eigh(Ra, Rb)[1][:, -1]
            if ban:                                             # BAN：定住每个频点的尺度
                num = math.sqrt(abs(w.conj() @ Rb @ Rb @ w) / M)
                w = w * num / abs(w.conj() @ Rb @ w)
        ya[f] = w.conj() @ A_; yb[f] = w.conj() @ B_
    lam1 = np.array(lam1)
    r1 = float(np.median(lam1[:, 0] / lam1.sum(1)))
    fr = np.fft.rfftfreq(NFFT, 1 / FS); bd = (fr >= 200) & (fr <= 4000)
    full = 10 * math.log10(np.sum(np.abs(ya) ** 2) / np.sum(np.abs(yb) ** 2))
    band = 10 * math.log10(np.sum(np.abs(ya[bd]) ** 2) / np.sum(np.abs(yb[bd]) ** 2))
    return full, r1, band


def sep_sir(Y, gA, gB):
    """把同一个权重作用在纯 A / 纯 B 上，才是真 SIR"""
    ya = np.zeros((F, T), complex); yb = np.zeros((F, T), complex)
    for f in range(F):
        Xf = X[:, f, :]
        wa = gA[f] / (gA[f].sum() + 1e-9); wb = gB[f] / (gB[f].sum() + 1e-9)
        Ra = (Xf * wa) @ Xf.conj().T
        Rn = (Xf * wb) @ Xf.conj().T
        Rn += 1e-6 * np.trace(Rn).real / M * np.eye(M)
        ev, V = np.linalg.eigh(Ra); a = V[:, -1]; a = a * np.exp(-1j * np.angle(a[0]))
        Ri = np.linalg.solve(Rn, a); w = Ri / (a.conj() @ Ri)
        ya[f] = w.conj() @ XA[:, f, :]
        yb[f] = w.conj() @ XB[:, f, :]
    return 10 * math.log10(np.sum(np.abs(ya) ** 2) / np.sum(np.abs(yb) ** 2))


# ══ ③ CACGMM 空间聚类 ═══════════════════════════════════════
def cacgmm(seedmat=None, iters=30, prior=None, K=2, seed=0):
    """每个频点独立跑一个 2 分量复角中心高斯混合；
       prior: (K,T) 的时间先验（GSS 用 diarization 结果钉住排列），None = 盲"""
    g = np.random.default_rng(seed)
    G = np.zeros((K, F, T))
    Z = X / (np.linalg.norm(X, axis=0, keepdims=True) + 1e-12)      # (M,F,T)
    for f in range(F):
        Zf = Z[:, f, :]
        B = np.array([np.eye(M, dtype=complex) * (1 + 0.1 * g.standard_normal())
                      for _ in range(K)])
        if seedmat is not None:                                      # 用导向向量起手
            for k in range(K):
                v = seedmat[k][:, f]
                B[k] = np.eye(M) * 0.1 + np.outer(v, v.conj())
        al = np.ones(K) / K
        for _ in range(iters):
            lp = np.zeros((K, T))
            for k in range(K):
                Bi = np.linalg.inv(B[k] + 1e-9 * np.eye(M))
                q = np.real(np.einsum('mt,mn,nt->t', Zf.conj(), Bi, Zf)) + 1e-12
                sgn, ld = np.linalg.slogdet(B[k] + 1e-9 * np.eye(M))
                lp[k] = -ld - M * np.log(q)
            lp += np.log(al[:, None] + 1e-12)
            if prior is not None:
                lp += np.log(prior + 1e-6)
            lp -= lp.max(0, keepdims=True)
            gam = np.exp(lp); gam /= gam.sum(0, keepdims=True)
            al = gam.mean(1)
            for k in range(K):
                Bi = np.linalg.inv(B[k] + 1e-9 * np.eye(M))
                q = np.real(np.einsum('mt,mn,nt->t', Zf.conj(), Bi, Zf)) + 1e-12
                wgt = gam[k] / q
                B[k] = M * (Zf * wgt) @ Zf.conj().T / (gam[k].sum() + 1e-9)
                B[k] /= np.trace(B[k]).real / M
        G[:, f, :] = gam
    return G


def steer(th, r):
    """近场几何导向（每个频点）"""
    p = pos(th, r)
    d = np.linalg.norm(mics.T - p, axis=1)
    fr = np.fft.rfftfreq(NFFT, 1 / FS)
    a = np.exp(-2j * np.pi * fr[None, :] * (d[:, None] - d[0]) / c) / math.sqrt(M)
    return a                                                        # (M,F)


AA, AB = steer(TH_A, R_A), steer(TH_B, R_B)

# 盲聚类（随机起手，无先验）——排列问题
Gb = cacgmm(seed=7)
# 每个频点自己决定谁是 0 号，所以要看"对不对得上"
truth = (pa > pb)
agree = np.array([max(np.mean((Gb[0, f] > 0.5) == truth[f]),
                      np.mean((Gb[1, f] > 0.5) == truth[f])) for f in range(F)])
align = np.array([np.mean((Gb[0, f] > 0.5) == truth[f]) > 0.5 for f in range(F)])
OUT['blind'] = {'bin_acc': round(float(agree.mean()) * 100, 1),
                'perm_ok': round(float(align.mean()) * 100, 1)}
print('\n③ 盲空间聚类（随机起手）')
print('   每个频点内部分对了 %.1f%% 的格子' % OUT['blind']['bin_acc'])
print('   但只有 %.1f%% 的频点把"0 号"指给了同一个人 ← 排列问题' % OUT['blind']['perm_ok'])
OUT['blind']['sir'] = round(sep_sir(None, Gb[0], Gb[1]), 2)
Gfix = np.stack([np.where(align[:, None], Gb[0], Gb[1]),
                 np.where(align[:, None], Gb[1], Gb[0])])
OUT['blind']['sir_oracleperm'] = round(sep_sir(None, Gfix[0], Gfix[1]), 2)
print('   直接拿去解 MVDR：SIR %6.2f dB' % OUT['blind']['sir'])
print('   若有神仙帮它对齐排列：SIR %6.2f dB' % OUT['blind']['sir_oracleperm'])

# ══ ④ GSS：用 diarization 先验钉住 ═══════════════════════════
def diar_prior(err=0.0, seed=3):
    g = np.random.default_rng(seed)
    P = np.stack([aA.astype(float), aB.astype(float)])[:, :T] + 0.05
    if err > 0:
        flip = g.random(T) < err
        P[:, flip] = P[::-1][:, flip]
    return P / P.sum(0, keepdims=True)


OUT['gss'] = {}
for err in (0.0, 0.05, 0.10, 0.20, 0.40):
    G = cacgmm(prior=diar_prior(err), seed=7)
    v = sep_sir(None, G[0], G[1])
    OUT['gss'][err] = round(v, 2)
    print('   GSS，diarization 错 %4.0f%% → SIR %6.2f dB' % (err * 100, v))

# 理想掩码 → MVDR 的天花板
gA = np.stack([irm] * 1)[0]; gB = 1 - gA
OUT['oracle_mvdr'] = round(sep_sir(None, gA, gB), 2)
OUT['ibm_mvdr'] = round(sep_sir(None, ibm, 1 - ibm), 2)
# 纯几何（不聚类）：直接用导向向量做 MVDR，干扰协方差用 B 的
Rn_geo = np.zeros((F, T)); Rn_geo[:] = 0
gA_geo = np.zeros((F, T)); gB_geo = np.zeros((F, T))
for f in range(F):
    gA_geo[f] = np.abs(AA[:, f].conj() @ X[:, f, :]) ** 2
    gB_geo[f] = np.abs(AB[:, f].conj() @ X[:, f, :]) ** 2
tt = gA_geo + gB_geo + 1e-20
OUT['geo_mvdr'] = round(sep_sir(None, gA_geo / tt, gB_geo / tt), 2)
print('\n④ 各种掩码解出来的 MVDR，真 SIR')
print('   纯几何（只用 DOA 不聚类）  %6.2f dB' % OUT['geo_mvdr'])
print('   盲聚类                    %6.2f dB' % OUT['blind']['sir'])
print('   GSS（先验全对）            %6.2f dB' % OUT['gss'][0.0])
print('   理想二值掩码 IBM          %6.2f dB' % OUT['ibm_mvdr'])
print('   理想比值掩码 IRM          %6.2f dB' % OUT['oracle_mvdr'])
OUT['oracle_r1'], r1frac, OUT['oracle_r1_band'] = oracle_cov_sir(True)
OUT['oracle_gev'], _, OUT['oracle_gev_band'] = oracle_cov_sir(False)
OUT['oracle_r1_band'] = round(OUT['oracle_r1_band'], 2)
OUT['oracle_gev_band'] = round(OUT['oracle_gev_band'], 2)
nb, _, nbb = oracle_cov_sir(False, ban=False)
OUT['oracle_gev_noban'] = round(nb, 2); OUT['oracle_gev_noban_band'] = round(nbb, 2)
print('   （同一个 GEV 不做 BAN：全带 %.2f dB，200–4k 带内 %.2f dB ← 全带那个是假的）'
      % (OUT['oracle_gev_noban'], OUT['oracle_gev_noban_band']))
OUT['oracle_r1'] = round(OUT['oracle_r1'], 2); OUT['oracle_gev'] = round(OUT['oracle_gev'], 2)
OUT['rank1_frac'] = round(r1frac * 100, 1)
OUT['gss_gev'] = {}
for err in (0.0, 0.10, 0.20, 0.40):
    G = cacgmm(prior=diar_prior(err), seed=7)
    OUT['gss_gev'][err] = round(sep_gev(G[0], G[1]), 2)
OUT['ibm_gev'] = round(sep_gev(ibm, 1 - ibm), 2)
OUT['blind_gev'] = round(sep_gev(Gb[0], Gb[1]), 2)
# 每频点的 GEV 最大特征值（空间可分度随频率的分布）
import scipy.linalg as _sla
lamf = []
for f in range(F):
    A_, B_ = XA[:, f, :], XB[:, f, :]
    Ra = A_ @ A_.conj().T / T; Rb = B_ @ B_.conj().T / T
    Rb = Rb + 1e-6 * np.trace(Rb).real / M * np.eye(M)
    lamf.append(float(10 * math.log10(_sla.eigh(Ra, Rb, eigvals_only=True)[-1])))
OUT['lam_f'] = [round(v, 2) for v in lamf]
OUT['freqs'] = [round(v, 1) for v in np.fft.rfftfreq(NFFT, 1 / FS)]
print('\n⑤ 瓶颈在哪：放弃 rank-1 假设能多拿多少')
print('   目标协方差的第一特征值只占 %.1f%% 的能量 ← 它不是秩一' % OUT['rank1_frac'])
print('   神仙协方差 + rank-1 MVDR   %6.2f dB' % OUT['oracle_r1'])
print('   神仙协方差 + GEV           %6.2f dB  ← 空间上真正的上限' % OUT['oracle_gev'])
print('   盲聚类   + GEV+BAN         %6.2f dB' % OUT['blind_gev'])
print('   IBM 掩码 + GEV+BAN         %6.2f dB' % OUT['ibm_gev'])
for k, v in OUT['gss_gev'].items():
    print('   GSS 掩码 + GEV+BAN，错 %3.0f%%  %6.2f dB' % (k * 100, v))
json.dump(OUT, open('demo_sep.json', 'w'), ensure_ascii=False, indent=1)
