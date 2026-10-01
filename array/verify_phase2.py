#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确式 DI_real=(1+x)/(1/DI+x)，x=σ²/WNG；以及 1 dB 损失的预算式。"""
import numpy as np
rng = np.random.default_rng(7)
c = 343.0
def setup(M,d,f,eps):
    kd=2*np.pi*f/c*d
    G=np.array([[np.sinc(kd*abs(i-j)/np.pi) for j in range(M)] for i in range(M)])
    a=np.exp(1j*kd*np.arange(M))
    w=np.linalg.solve(G+eps*np.eye(M),a); w=w/(a.conj()@w)
    return G,a,w,abs(w.conj()@a)**2/np.real(w.conj()@G@w),abs(w.conj()@a)**2/np.real(w.conj()@w)

def mc(G,a,w,s,N=20000):
    M=len(w)
    wt=w[None,:]*(1+s*rng.standard_normal((N,M)))*np.exp(-1j*s*rng.standard_normal((N,M)))
    num=np.abs(np.einsum('ij,j->i',wt.conj(),a))**2
    den=np.real(np.einsum('ij,jk,ik->i',wt.conj(),G,wt))
    return 10*np.log10(np.mean(num)/np.mean(den))

print('══ A. 闭式 vs 蒙特卡洛（均值意义）══')
for M,d,f,eps in [(4,.035,1000,0.),(4,.035,1000,1e-2),(8,.030,700,1e-3),(2,.015,500,0.),(6,.04,2000,1e-1)]:
    G,a,w,di,wng=setup(M,d,f,eps)
    print('  M=%d f=%d ε=%-6g DI=%6.2f WNG=%7.2f' % (M,f,eps,10*np.log10(di),10*np.log10(wng)))
    for sd in [0.2,0.5,1,2,5]:
        s=np.radians(sd); x=2*s**2/wng*0.5   # σ²=σg²+σφ²，两者各 s
        x=(s**2+s**2)/wng
        pred=10*np.log10((1+x)/(1/di+x))
        print('     σ=%4.1f°  闭式 %6.2f dB   蒙特卡洛 %6.2f dB   差 %5.2f'
              % (sd,pred,mc(G,a,w,s),pred-mc(G,a,w,s)))

print('\n══ B. 1 dB 损失的预算式：σ°≈ K×10^((WNG−DI)/20) ══')
print('   （σ_g 与 σ_φ 同量级，合成 σ²=σ_g²+σ_φ²；此处 K 按"相位单独"定标）')
rows=[]
for M,d,f,eps in [(4,.035,1000,0.),(4,.035,1000,1e-3),(4,.035,1000,1e-2),(4,.035,1000,1e-1),
                  (8,.030,700,0.),(8,.030,700,1e-2),(2,.015,500,0.),(6,.04,2000,1e-2),
                  (4,.05,3000,1e-2),(3,.02,800,1e-3)]:
    G,a,w,di,wng=setup(M,d,f,eps)
    # 解 1 dB 损失的 σ：(1+x)/(1/di+x)=di/10^0.1
    r=10**0.1; x=(r-1)/(di-r)
    s=np.sqrt(x*wng/2)                     # σ_g=σ_φ=σ，σ²_total=2σ²
    K=np.degrees(s)/10**((10*np.log10(wng)-10*np.log10(di))/20)
    rows.append(K)
    print('  M=%d f=%4d ε=%-6g DI=%6.2f WNG=%7.2f → σ_1dB=%6.3f°  K=%.2f'
          % (M,f,eps,10*np.log10(di),10*np.log10(wng),np.degrees(s),K))
print('  K 的范围 %.2f–%.2f，中位 %.2f  → 取整用 20' % (min(rows),max(rows),np.median(rows)))

print('\n══ C. "2°" 落在哪个工作点 ══')
for di_db,wng_db in [(12,-10),(12,-6),(9,-5),(15,-15),(6,0)]:
    di=10**(di_db/10); wng=10**(wng_db/10)
    r=10**0.1; x=(r-1)/(di-r); s=np.degrees(np.sqrt(x*wng/2))
    print('  DI=%2d dB, WNG=%+3d dB → 1 dB 损失允许 σ = %5.2f°' % (di_db,wng_db,s))
