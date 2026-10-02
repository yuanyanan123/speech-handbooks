#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目标抵消的真正机理：导向矢量误差 × 目标进协方差。"""
import numpy as np
rng = np.random.default_rng(5)
c=343.0
def steer(M,d,f,th): return np.exp(1j*2*np.pi*f/c*d*np.arange(M)*np.cos(th))
M,d,f = 6,0.035,1500
a_true = steer(M,d,f,np.radians(0))
ai     = steer(M,d,f,np.radians(70))
phii, phiw = 1.0, 0.01
Rn_true = phii*np.outer(ai,ai.conj()) + phiw*np.eye(M)

print('══ A. a 精确时：目标进 R_n 完全无害（矩阵反演引理）══')
for p in [0,0.1,1,10,100]:
    Rs = p*np.outer(a_true,a_true.conj())
    R  = Rn_true + Rs
    w  = np.linalg.solve(R,a_true); w=w/(a_true.conj()@w)
    w0 = np.linalg.solve(Rn_true,a_true); w0=w0/(a_true.conj()@w0)
    print('   目标功率 p=%6.1f  ‖w−w_clean‖=%.2e   输出噪声 %.4f dB'
          % (p, np.linalg.norm(w-w0), 10*np.log10(np.real(w.conj()@Rn_true@w))))

print('\n══ B. a 有误差 + 目标进 R_n：SINR 随目标功率崩塌 ══')
print('   （假设方向偏 θ_err，真实目标在 0°）')
print('   θ_err   SNR_in(dB)   R_n 干净时 SINR   R_n 含目标时 SINR    损失')
for th_err in [0.0, 1.0, 3.0, 5.0]:
    a_asm = steer(M,d,f,np.radians(th_err))
    for phis_db in [-10,0,10,20]:
        phis = 10**(phis_db/10)
        Rs = phis*np.outer(a_true,a_true.conj())
        def sinr(R):
            w=np.linalg.solve(R,a_asm); w=w/(a_asm.conj()@w)
            return 10*np.log10(np.real(w.conj()@Rs@w)/np.real(w.conj()@Rn_true@w))
        s_clean = sinr(Rn_true); s_dirty = sinr(Rn_true+Rs)
        print('   %4.1f°   %+6.0f        %7.2f           %7.2f          %6.2f'
              % (th_err, phis_db, s_clean, s_dirty, s_clean-s_dirty))
    print()

print('══ C. 对角加载能救多少（θ_err=3°，SNR_in=10 dB）══')
th_err=3.0; phis=10.0
a_asm=steer(M,d,f,np.radians(th_err)); Rs=phis*np.outer(a_true,a_true.conj())
for eps in [0,1e-3,1e-2,1e-1,1,10]:
    R = Rn_true+Rs+eps*np.eye(M)
    w=np.linalg.solve(R,a_asm); w=w/(a_asm.conj()@w)
    print('   ε=%-6g  SINR=%7.2f dB   |wᴴa_true|=%.4f'
          % (eps,10*np.log10(np.real(w.conj()@Rs@w)/np.real(w.conj()@Rn_true@w)),
             abs(w.conj()@a_true)))
print('   （干净 R_n、无加载时的参考：%.2f dB）'
      % (10*np.log10(np.real((lambda w:(w.conj()@Rs@w))(
          (lambda v: v/(a_asm.conj()@v))(np.linalg.solve(Rn_true,a_asm))))
         /np.real((lambda w:(w.conj()@Rn_true@w))(
          (lambda v: v/(a_asm.conj()@v))(np.linalg.solve(Rn_true,a_asm)))))))
