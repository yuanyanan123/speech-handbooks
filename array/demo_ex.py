#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全书统一算例：每个算法一份可手算复核的数值实例。"""
import numpy as np, json, math
np.set_printoptions(precision=4, suppress=True)
c = 343.0
E = {}

# ══ 共用参数 ═══════════════════════════════════════════════
M, d, fs = 4, 0.035, 16000
NFFT, HOP = 512, 256
TH_S, R_S, TH_I, R_I = 60.0, 1.5, 130.0, 2.2
V, RT60 = 99.0, 0.6
f = 1000.0
lam = c/f; k = 2*math.pi*f/c; kd = k*d
tau12 = d*math.cos(math.radians(TH_S))/c
E['par'] = dict(M=M, d_mm=d*1000, fs=fs, nfft=NFFT, hop=HOP,
    th_s=TH_S, r_s=R_S, th_i=TH_I, r_i=R_I, V=V, RT60=RT60,
    f=f, lam_mm=lam*1000, k=k, kd=kd,
    tau12_us=tau12*1e6, tau12_smp=tau12*fs,
    dphi_deg=math.degrees(2*math.pi*f*tau12),
    f_alias=c/(2*d), L_mm=M*d*1000, L_lam=M*d/lam,
    fresnel=2*((M-1)*d)**2/lam,
    rc=0.0566*math.sqrt(V/RT60),
    A=0.161*V/RT60, bin_=int(round(f/(fs/NFFT))))
E['par']['r_over_rc'] = R_S/E['par']['rc']
E['par']['DR_dB'] = 10*math.log10((E['par']['rc']/R_S)**2)

# ══ §13 分数延迟 ═══════════════════════════════════════════
frac = tau12*fs
E['s13'] = dict(tau_smp=frac, rounded=round(frac), err_smp=round(frac)-frac,
    err_us=(round(frac)-frac)/fs*1e6)
E['s13']['err_deg'] = {int(ff): abs(math.degrees(2*math.pi*ff*(round(frac)-frac)/fs))
                       for ff in (500,1000,2000,4000,8000)}

# ══ §16 DOA：从相位差反推角度（手算路径）═════════════════
dphi = 2*math.pi*f*tau12
E['s16'] = dict(dphi_rad=dphi, dphi_deg=math.degrees(dphi),
    tau_back_us=dphi/(2*math.pi*f)*1e6,
    cos_back=c*(dphi/(2*math.pi*f))/d,
    th_back=math.degrees(math.acos(c*(dphi/(2*math.pi*f))/d)),
    tau_max_us=d/c*1e6, tau_max_smp=d/c*fs,
    dth_per_smp=None)
# 一个采样点对应多少度（在 60° 附近）
def th_of_tau(t): return math.degrees(math.acos(np.clip(c*t/d,-1,1)))
E['s16']['dth_per_smp'] = abs(th_of_tau(tau12+1/fs)-th_of_tau(tau12))
E['s16']['th_of_pm1smp'] = [th_of_tau(tau12-1/fs), th_of_tau(tau12+1/fs)]

# ══ §17 波束：a、Γ、四种 w ════════════════════════════════
m_ = np.arange(M)-(M-1)/2
a = np.exp(1j*k*d*m_*math.cos(math.radians(TH_S)))
Dm = np.abs(np.arange(M)[:,None]-np.arange(M)[None,:])*d
G = np.sinc(2*f*Dm/c)
ai = np.exp(1j*k*d*m_*math.cos(math.radians(TH_I)))
def cx(z): return [[round(float(v.real),4), round(float(v.imag),4)] for v in z]
def pol(z): return [[round(float(abs(v)),4), round(float(np.degrees(np.angle(v))),2)] for v in z]
def di(w): return 10*math.log10(abs(w.conj()@a)**2/np.real(w.conj()@G@w))
def wng(w): return 10*math.log10(abs(w.conj()@a)**2/np.real(w.conj()@w))
def att(w): return 20*math.log10(max(abs(w.conj()@ai),1e-12))
E['s17'] = dict(a=cx(a), a_pol=pol(a),
    sinc=[round(float(np.sinc(2*f*x/c)),6) for x in (0,d,2*d,3*d)],
    Gamma=[[round(float(x),6) for x in r] for r in G],
    cond=float(np.linalg.cond(G)), ai=cx(ai))
W = {}
W['DAS'] = a/M
W['SD0'] = np.linalg.solve(G, a); W['SD0'] /= (a.conj()@W['SD0'])
for eps in (1e-3, 1e-2, 1e-1):
    w = np.linalg.solve(G+eps*np.trace(G)/M*np.eye(M), a)
    W['SD%g'%eps] = w/(a.conj()@w)
# MVDR：干扰为点源 + 小白噪
Rn = np.outer(ai, ai.conj()) + 0.01*np.eye(M)
w = np.linalg.solve(Rn+1e-2*np.trace(Rn)/M*np.eye(M), a); W['MVDR'] = w/(a.conj()@w)
E['s17']['Rn'] = [[[round(float(x.real),4),round(float(x.imag),4)] for x in r] for r in Rn]
for tag, w in W.items():
    E['s17'][tag] = dict(w=cx(w), w_pol=pol(w), di=di(w), wng=wng(w),
                         att_i=att(w), norm=float(np.real(w.conj()@w)))
# 中间量：Γ⁻¹a 与 aᴴΓ⁻¹a
gi = np.linalg.solve(G, a)
E['s17']['Ginv_a'] = cx(gi)
E['s17']['aHGinv_a'] = float(np.real(a.conj()@gi))
E['s17']['aHGinv_a_dB'] = 10*math.log10(float(np.real(a.conj()@gi)))
E['s17']['M2_dB'] = 20*math.log10(M)

# ══ §18 后置滤波：给定 φ_s、φ_n 直接走三条路 ═══════════════
phis, phin = 1.0, 1.0          # 输入 SNR = 0 dB
iu = np.triu_indices(M,1)
Phi_ij = phis + phin*G[iu]
Phi_ii = phis + phin
zel = Phi_ij.mean()/Phi_ii
mcc = np.mean((Phi_ij - G[iu]*Phi_ii)/(1-G[iu]))/Phi_ii
E['s18'] = dict(phis=phis, phin=phin, xi=phis/phin,
    Gamma_ij=[round(float(x),4) for x in G[iu]],
    gbar=float(G[iu].mean()),
    Phi_ij=[round(float(x),4) for x in Phi_ij], Phi_ii=Phi_ii,
    G_zel=float(zel), G_mcc=float(mcc), G_true=phis/(phis+phin),
    sup_zel=-20*math.log10(zel), sup_mcc=-20*math.log10(mcc),
    sup_true=-20*math.log10(phis/(phis+phin)))
# 逐对 McCowan
E['s18']['mcc_pair'] = [round(float((Phi_ij[i]-G[iu][i]*Phi_ii)/(1-G[iu][i])),4)
                        for i in range(len(Phi_ij))]

# ══ §02 / §03 的场景推论 ═══════════════════════════════════
E['s02'] = dict(rc=E['par']['rc'], r=R_S, ratio=R_S/E['par']['rc'],
    need_Q=(R_S/E['par']['rc'])**2, need_DI=10*math.log10((R_S/E['par']['rc'])**2))
E['s03'] = dict(f_alias=c/(2*d), L_lam=M*d/lam,
    mainlobe=None, di_das_1k=10*math.log10(M**2/np.real(G.sum())))
s3 = 0.443*lam/(M*d)
E['s03']['mainlobe'] = ('无' if s3>=1 else 2*math.degrees(math.asin(s3)))
E['s03']['s3_val'] = s3
for ff in (2000,4000,8000):
    ll = c/ff; ss = 0.443*ll/(M*d)
    E['s03']['ml_%d'%ff] = ('无' if ss>=1 else round(2*math.degrees(math.asin(ss)),1))

json.dump(E, open('demo_ex.json','w'), ensure_ascii=False, indent=1)

# ── 打印核对 ──────────────────────────────────────────────
P=E['par']
print('══ 共用参数 ══')
for kk in ['f','lam_mm','kd','tau12_us','tau12_smp','dphi_deg','f_alias','L_mm','L_lam',
           'fresnel','rc','r_over_rc','DR_dB','bin_']:
    print('  %-12s %s'%(kk, round(P[kk],4) if isinstance(P[kk],float) else P[kk]))
print('\n══ §13 分数延迟 ══'); print(' ',{kk:(round(v,4) if isinstance(v,float) else v) for kk,v in E['s13'].items()})
print('\n══ §16 ══'); print(' ',{kk:(round(v,4) if isinstance(v,float) else v) for kk,v in E['s16'].items() if kk!='th_of_pm1smp'})
print('   ±1 样点对应角度', [round(v,2) for v in E['s16']['th_of_pm1smp']])
print('\n══ §17 ══')
print('  sinc 三个值', E['s17']['sinc'])
print('  a（幅度,相位°）', E['s17']['a_pol'])
print('  aᴴΓ⁻¹a = %.4f = %.2f dB   （上限 20log₁₀4 = %.2f dB）'%(
    E['s17']['aHGinv_a'],E['s17']['aHGinv_a_dB'],E['s17']['M2_dB']))
print('  cond(Γ) = %.3e'%E['s17']['cond'])
for tag in ['DAS','SD0','SD0.001','SD0.01','SD0.1','MVDR']:
    v=E['s17'][tag]
    print('  %-8s DI %6.2f  WNG %8.2f  干扰衰减 %7.2f dB'%(tag,v['di'],v['wng'],v['att_i']))
print('\n══ §18 ══')
for kk,v in E['s18'].items():
    print('  %-10s %s'%(kk, [round(x,4) for x in v] if isinstance(v,list) else round(v,4)))
print('\n══ §02/§03 ══'); print(' ',{kk:(round(v,3) if isinstance(v,float) else v) for kk,v in E['s02'].items()})
print(' ',{kk:(round(v,3) if isinstance(v,float) else v) for kk,v in E['s03'].items()})
