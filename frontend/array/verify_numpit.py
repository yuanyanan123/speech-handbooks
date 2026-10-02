#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数值实现的坑：逐条量化。"""
import numpy as np, mpmath as mp
mp.mp.dps=60
c=343.0
def Gam(M,d,f):
    m=np.arange(M); D=np.abs(m[:,None]-m[None,:])*d
    return np.sinc(2*f*D/c)
def steer(M,d,f): return np.exp(1j*2*np.pi*f/c*d*np.arange(M))

print('══ 1. inv() vs solve()：同一个式子，误差差多少 ══')
for M,d,f in [(4,.035,300),(6,.030,200),(8,.020,150)]:
    G=Gam(M,d,f); a=steer(M,d,f)
    # 高精度真值
    Gm=mp.matrix(M,M)
    kd=mp.mpf(2)*mp.pi*f/c*d
    for i in range(M):
        for j in range(M):
            x=kd*abs(i-j); Gm[i,j]=mp.mpf(1) if x==0 else mp.sin(x)/x
    am=mp.matrix([mp.e**(1j*kd*k) for k in range(M)])
    ex=np.array([complex(v) for v in mp.lu_solve(Gm,am)])
    vi=np.linalg.inv(G)@a; vs=np.linalg.solve(G,a)
    print('  M=%d f=%3d cond=%.1e | inv 相对误差 %.2e | solve %.2e | 差 %.1f 倍'
          %(M,f,np.linalg.cond(G),
            np.linalg.norm(vi-ex)/np.linalg.norm(ex),
            np.linalg.norm(vs-ex)/np.linalg.norm(ex),
            (np.linalg.norm(vi-ex)/max(np.linalg.norm(vs-ex),1e-300))))

print('\n══ 2. 对角加载必须"相对"，否则跟着音量走 ══')
M,d,f=4,.035,1000
G=Gam(M,d,f); a=steer(M,d,f)
def wng(w,a): return 10*np.log10(abs(w.conj()@a)**2/np.real(w.conj()@w))
for scale in [1e-4,1.0,1e4]:
    R=G*scale
    wa=np.linalg.solve(R+1e-2*np.eye(M),a); wa=wa/(a.conj()@wa)          # 绝对加载
    wr=np.linalg.solve(R+1e-2*np.trace(R)/M*np.eye(M),a); wr=wr/(a.conj()@wr)  # 相对加载
    print('  输入功率 ×%-6.0e  绝对加载 WNG %7.2f dB   相对加载 WNG %7.2f dB'
          %(scale,wng(wa,a),wng(wr,a)))

print('\n══ 3. np.sinc 不是 sin(x)/x ══')
x=1.234
print('  np.sinc(%.3f) = %.6f   而 sin(x)/x = %.6f   差 %.1f%%'
      %(x,np.sinc(x),np.sin(x)/x,abs(np.sinc(x)-np.sin(x)/x)/abs(np.sin(x)/x)*100))
kd=2*np.pi*1000/c*0.035
print('  扩散场相干 kd=%.4f：正确 %.6f（np.sinc(kd/π)）  写错成 np.sinc(kd) → %.6f'
      %(kd,np.sinc(kd/np.pi),np.sinc(kd)))
print('  → 写错时 35 mm 的一对麦在 1 kHz 的相干从 %.3f 变成 %.3f，DI 直接算飞'
      %(np.sinc(kd/np.pi),np.sinc(kd)))

print('\n══ 4. 角度不能算算术平均 ══')
ang=np.array([350.,355.,5.,10.])
cm=np.degrees(np.angle(np.mean(np.exp(1j*np.radians(ang)))))%360
print('  样本 %s'%ang)
print('  算术平均 %.1f°（错）   圆周平均 %.1f°（对）'%(ang.mean(),cm))

print('\n══ 5. float32 累积协方差 ══')
rng=np.random.default_rng(0)
M,N=8,200000
X=(rng.standard_normal((M,N))+1j*rng.standard_normal((M,N)))/np.sqrt(2)
X=X+3.0                                       # 加个直流，模拟未去均值的通道
R64=(X@X.conj().T)/N
R32=(X.astype(np.complex64)@X.astype(np.complex64).conj().T)/np.complex64(N)
print('  float64 vs float32 协方差相对误差 %.2e'%(np.linalg.norm(R32-R64)/np.linalg.norm(R64)))
print('  条件数 float64 %.3e   float32 %.3e'%(np.linalg.cond(R64),np.linalg.cond(R32.astype(complex))))

print('\n══ 6. 复数求导：对 w* 求，不是对 w 求 ══')
M=4; rng=np.random.default_rng(1)
A=rng.standard_normal((M,M))+1j*rng.standard_normal((M,M)); R=A@A.conj().T
w=(rng.standard_normal(M)+1j*rng.standard_normal(M))
J=lambda v: np.real(v.conj()@R@v)
h=1e-6; num=np.zeros(M,complex)
for i in range(M):
    e=np.zeros(M,complex); e[i]=h
    num[i]=((J(w+e)-J(w-e))/(2*h) + 1j*(J(w+1j*e)-J(w-1j*e))/(2*h))/2
print('  数值梯度（Wirtinger ∂/∂w*） %s'%np.array2string(num,precision=5))
print('  解析 R w                    %s'%np.array2string(R@w,precision=5))
print('  相对误差 %.2e  → ∂(wᴴRw)/∂w* = Rw，不是 2Rw 也不是 Rᵀw'
      %(np.linalg.norm(num-R@w)/np.linalg.norm(R@w)))
