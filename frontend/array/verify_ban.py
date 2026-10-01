#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§17：BAN 的推导核对，以及目标抵消的定量仿真。"""
import numpy as np
rng = np.random.default_rng(20260916)
c = 343.0

def steer(M,d,f,th): return np.exp(1j*2*np.pi*f/c*d*np.arange(M)*np.cos(th))

print('══ 1. BAN 的两个中间量（w = R_n⁻¹a 时）══')
for M,f,d in [(6,1500,0.035),(4,800,0.05),(8,3000,0.02)]:
    A = rng.standard_normal((M,M))+1j*rng.standard_normal((M,M))
    Rn = A@A.conj().T + 2*np.eye(M); Rn = Rn/np.trace(Rn)*M
    a = steer(M,d,f,np.radians(35))
    w = np.linalg.solve(Rn,a)
    t1 = np.real(w.conj()@Rn@w); t2 = np.real(w.conj()@Rn@Rn@w)
    print('  M=%d f=%4d | wᴴR_nw=%.6f  aᴴR_n⁻¹a=%.6f | wᴴR_nR_nw/M=%.6f  aᴴa/M=%.6f'
          % (M,f,t1,np.real(a.conj()@np.linalg.solve(Rn,a)),t2/M,np.real(a.conj()@a)/M))

print('\n══ 2. BAN 之后 = MVDR（幅度精确相等，相位由特征向量决定）══')
for M,f,d in [(6,1500,0.035),(4,800,0.05),(8,3000,0.02)]:
    A = rng.standard_normal((M,M))+1j*rng.standard_normal((M,M))
    Rn = A@A.conj().T + 2*np.eye(M); Rn = Rn/np.trace(Rn)*M
    a = steer(M,d,f,np.radians(35)); phis = 2.7
    Rs = phis*np.outer(a,a.conj())
    # GEV
    import scipy.linalg as sla
    ev, V = sla.eigh(Rs, Rn)
    wg = V[:, -1]                          # 任意尺度、任意相位
    wg = wg*np.exp(1j*rng.uniform(0,2*np.pi))*rng.uniform(0.1,10)   # 人为再乱一个尺度和相位
    ban = np.sqrt(np.real(wg.conj()@Rn@Rn@wg)/M)/np.real(wg.conj()@Rn@wg)
    wb = ban*wg
    wm = np.linalg.solve(Rn,a); wm = wm/(a.conj()@wm)
    print('  M=%d f=%4d | |wᴴa| BAN=%.10f MVDR=%.10f | 幅度比 %.10f | 相位差 %+.1f°'
          % (M,f,abs(wb.conj()@a),abs(wm.conj()@a),
             np.linalg.norm(wb)/np.linalg.norm(wm),
             np.degrees(np.angle((wb.conj()@a)/(wm.conj()@a)))))

print('\n══ 3. 相位不定性的后果：拼回时域会怎样 ══')
M,d = 6,0.035
a0 = None; dev = []
for f in np.linspace(200,4000,32):
    A = rng.standard_normal((M,M))+1j*rng.standard_normal((M,M))
    Rn = A@A.conj().T+2*np.eye(M); Rn=Rn/np.trace(Rn)*M
    a = steer(M,d,f,np.radians(35)); Rs=2.7*np.outer(a,a.conj())
    import scipy.linalg as sla
    ev,V = sla.eigh(Rs,Rn); wg=V[:,-1]
    ban=np.sqrt(np.real(wg.conj()@Rn@Rn@wg)/M)/np.real(wg.conj()@Rn@wg)
    dev.append(np.degrees(np.angle(ban*wg.conj()@a)))
dev=np.array(dev)
print('   BAN 后各频点 ∠(wᴴa)：std %.1f°  范围 %.0f°..%.0f°  —— 幅度对齐了，相位没有'
      % (dev.std(), dev.min(), dev.max()))
print('   （实现上要再钉一个相位约定，例如令参考通道分量为正实数）')

print('\n══ 4. 目标抵消：R_n 里混进多少目标，就掉多少 ══')
M,d,f = 6,0.035,1500
a = steer(M,d,f,np.radians(0))           # 目标端射
ai = steer(M,d,f,np.radians(70))         # 点干扰
phis, phii, phiw = 1.0, 1.0, 0.01
Rn_true = phii*np.outer(ai,ai.conj()) + phiw*np.eye(M)
Rs = phis*np.outer(a,a.conj())
print('   混入比例 p   输出 SINR(dB)   |wᴴa|(目标增益)   目标失真(dB)')
for p in [0, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0]:
    Rn = Rn_true + p*Rs
    w = np.linalg.solve(Rn,a); w = w/(a.conj()@np.linalg.solve(Rn,a))  # MVDR 用被污染的 Rn
    ps = np.real(w.conj()@Rs@w); pn = np.real(w.conj()@Rn_true@w)
    print('    %6.3f      %8.2f        %.6f        %+.2f'
          % (p, 10*np.log10(ps/pn), abs(w.conj()@a), 20*np.log10(abs(w.conj()@a))))
print('   （w 仍按无失真约束归一化，所以 |wᴴa| 恒为 1；真正掉的是输出 SINR）')

print('\n══ 5. 更贴近现实：Rn 在含目标的帧上估计，w 不做无失真重归一化 ══')
print('   （门控失败比例 p → 目标被当噪声压掉多少）')
for p in [0, 0.01, 0.03, 0.1, 0.3, 1.0]:
    Rn = Rn_true + p*Rs
    Rin = Rn_true + Rs
    w = np.linalg.solve(Rn, a)               # 不归一化，看相对变化
    w = w/np.linalg.norm(w)
    ps = np.real(w.conj()@Rs@w); pn = np.real(w.conj()@Rn_true@w)
    w0 = np.linalg.solve(Rn_true,a); w0=w0/np.linalg.norm(w0)
    ps0 = np.real(w0.conj()@Rs@w0)
    print('    p=%5.2f  输出 SINR %7.2f dB   目标功率相对干净解 %+6.2f dB'
          % (p, 10*np.log10(ps/pn), 10*np.log10(ps/ps0)))
