#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§15 WPE：为什么"加权"和"延迟"缺一不可。频域逐频点实现。"""
import numpy as np
rng = np.random.default_rng(20260916)

M, K, NF, T = 4, 10, 1, 4000        # 通道、预测阶、频点、帧数
def make_rir(M, Lt=40, T60_frames=12.0, direct=1.0):
    """频域每个频点上的房间'脉冲响应'（沿帧轴）：直达 + 指数衰减尾巴。"""
    h = np.zeros((M, Lt), complex)
    dec = np.exp(-np.arange(Lt)*3*np.log(10)/T60_frames)
    for m in range(M):
        h[m] = (rng.standard_normal(Lt)+1j*rng.standard_normal(Lt))/np.sqrt(2)*dec
        h[m, 0] = direct*np.exp(1j*rng.uniform(0, 2*np.pi))
    return h

def synth(h, T, lam):
    Lt = h.shape[1]
    s = (rng.standard_normal(T)+1j*rng.standard_normal(T))/np.sqrt(2)*np.sqrt(lam)
    x = np.zeros((h.shape[0], T), complex)
    for m in range(h.shape[0]):
        x[m] = np.convolve(s, h[m])[:T]
    early = np.zeros_like(x)
    for m in range(h.shape[0]):
        early[m] = np.convolve(s, np.r_[h[m,:D_EARLY], np.zeros(Lt-D_EARLY)])[:T]
    return s, x, early

def wpe(x, K, D, iters=5, weighted=True):
    M, T = x.shape
    d = x.copy()
    for it in range(iters):
        lam = np.maximum(np.mean(np.abs(d)**2, axis=0), 1e-8) if weighted else np.ones(T)
        X = np.zeros((M*K, T), complex)
        for k in range(K):
            t0 = D+k
            X[k*M:(k+1)*M, t0:] = x[:, :T-t0]
        Wt = 1.0/lam
        R = (X*Wt)@X.conj().T
        P = (X*Wt)@x.conj().T
        G = np.linalg.solve(R+1e-8*np.trace(R)/len(R)*np.eye(M*K), P)
        d = x - G.conj().T@X
    return d

D_EARLY = 3
lam = np.exp(rng.standard_normal(T)*1.2)          # 语音式的时变功率
lam = np.convolve(lam, np.ones(8)/8, 'same')
h = make_rir(M)
s, x, early = synth(h, T, lam)

def srr(y, ref):
    """以 early 为目标，算"目标 / 残余"比（先做最小二乘尺度对齐）"""
    a = (ref.conj()@y)/(ref.conj()@ref)
    return 10*np.log10(np.sum(np.abs(a*ref)**2)/np.sum(np.abs(y-a*ref)**2))

print('══ 1. 混响前后：以"直达+早期"为目标的信混比 ══')
print('  输入（含混响）          %6.2f dB' % srr(x[0], early[0]))
for D in [0, 1, 2, 3, 5]:
    y = wpe(x, K, D, weighted=True)
    print('  WPE 加权   延迟 D=%d      %6.2f dB' % (D, srr(y[0], early[0])))
print()
for D in [0, 3]:
    y = wpe(x, K, D, weighted=False)
    print('  普通线性预测（不加权）D=%d  %6.2f dB' % (D, srr(y[0], early[0])))

print('\n══ 2. 不加权会把语音本身也白化 ══')
def flat(z, lam):
    """输出包络与真实包络的相关：越接近 1 说明时变结构保住了"""
    e = np.abs(z)**2
    e = np.convolve(e, np.ones(8)/8, 'same')
    return np.corrcoef(e, lam)[0,1]
print('  输入 x            包络相关 %.4f' % flat(x[0], lam))
yw = wpe(x, K, 3, weighted=True); yu = wpe(x, K, 3, weighted=False)
print('  WPE 加权          包络相关 %.4f' % flat(yw[0], lam))
print('  不加权线性预测    包络相关 %.4f  ← 语音的时变结构被预测器吃掉了' % flat(yu[0], lam))
print('  理想 early        包络相关 %.4f' % flat(early[0], lam))

print('\n══ 3. 延迟 D 的作用：D=0 会连直达一起削 ══')
print('   D    残余混响(dB)   直达增益 |a|（1 = 没动直达）')
for D in [0,1,2,3,4,6,8]:
    y = wpe(x, K, D, weighted=True)
    a = (early[0].conj()@y[0])/(early[0].conj()@early[0])
    print('   %d      %6.2f         %.4f' % (D, srr(y[0], early[0]), abs(a)))

print('\n══ 4. 预测阶 K 的作用（D=3）══')
for K_ in [2,5,10,20,30]:
    y = wpe(x, K_, 3, weighted=True)
    print('   K=%2d   %6.2f dB' % (K_, srr(y[0], early[0])))

print('\n══ 5. 通道数 M 的作用（K=10, D=3）══')
for M_ in [1,2,4]:
    y = wpe(x[:M_], 10, 3, weighted=True)
    print('   M=%d    %6.2f dB' % (M_, srr(y[0], early[0])))
