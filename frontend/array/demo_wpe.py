#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§15 算例：把 WPE 跑在 12 节那个真实房间上。"""
import numpy as np, json, math
import pyroomacoustics as pra
rng = np.random.default_rng(20260928)
c=343.0
S=json.load(open('demo_scene.json'))['scene']
ROOM=[6.0,5.0,3.3]; RT60=0.6; FS=S['fs']; M,D=S['M'],S['d_mm']/1000
CTR=np.array(S['ctr']); P_S=np.array(S['p_s'])
NFFT,HOP=512,256
EARLY_MS=50.0                                  # 早期/晚期分界
mics=np.c_[[CTR+np.array([(m-(M-1)/2)*D,0,0]) for m in range(M)]].T
e_abs,mo=pra.inverse_sabine(RT60,ROOM)
room=pra.ShoeBox(ROOM,fs=FS,materials=pra.Material(e_abs),max_order=mo)
room.add_microphone_array(pra.MicrophoneArray(mics,FS))
room.add_source(list(P_S)); room.compute_rir()
rir=[np.asarray(room.rir[m][0]) for m in range(M)]
L=max(len(r) for r in rir)
rir=[np.r_[r,np.zeros(L-len(r))] for r in rir]
d0=int(np.argmax(np.abs(rir[0])))              # 直达到达点
ne=d0+int(EARLY_MS/1000*FS)
print('RIR 长 %d（%.0f ms），直达在 %d，早期窗到 %d（%.0f ms）'%(L,L/FS*1000,d0,ne,EARLY_MS))
early=[np.r_[r[:ne],np.zeros(L-ne)] for r in rir]
# 直达/早期 与 晚期 的能量比
e_e=sum(np.sum(x**2) for x in early); e_l=sum(np.sum(r**2)-np.sum(x**2) for r,x in zip(rir,early))
print('早期/晚期能量比 %.2f dB'%(10*math.log10(e_e/e_l)))

def voiced(n):
    t=np.arange(n)/FS; env=np.zeros(n); i=0
    while i<n:
        Ln=rng.integers(int(0.12*FS),int(0.45*FS))
        if rng.random()<0.6: env[i:i+Ln]=1.0
        i+=Ln
    env=np.convolve(env,np.hanning(801)/np.hanning(801).sum(),'same')
    f0=120+25*np.sin(2*np.pi*1.7*t); ph=2*np.pi*np.cumsum(f0)/FS
    x=sum(np.sin(k*ph)/k for k in range(1,26))
    return x*env/np.max(np.abs(x*env))
N=FS*6; s=voiced(N)
x   =np.array([np.convolve(s,rir[m])[:N] for m in range(M)])
tgt =np.array([np.convolve(s,early[m])[:N] for m in range(M)])

def stft(z):
    w=np.hanning(NFFT+1)[:-1]; idx=np.arange(0,z.shape[1]-NFFT,HOP)
    return np.array([[np.fft.rfft(z[m,i:i+NFFT]*w) for i in idx] for m in range(z.shape[0])]).transpose(0,2,1)
X,T_=stft(x),stft(tgt)                          # (M,F,T)

def wpe(X,taps,delay,iters=5,weighted=True,eps=1e-8):
    M,F,T=X.shape; Y=X.copy()
    for _ in range(iters):
        lam=np.maximum(np.mean(np.abs(Y)**2,axis=0),eps) if weighted else np.ones((F,T))
        for f in range(F):
            Xb=np.zeros((M*taps,T),complex)
            for k in range(taps):
                t0=delay+k; Xb[k*M:(k+1)*M,t0:]=X[:,f,:T-t0]
            w=1.0/lam[f]
            R=(Xb*w)@Xb.conj().T; Pm=(Xb*w)@X[:,f].conj().T
            R+=eps*np.trace(R)/len(R)*np.eye(M*taps)
            G=np.linalg.solve(R,Pm); Y[:,f]=X[:,f]-G.conj().T@Xb
    return Y
def srr(Y,R):
    y,r=Y[0].ravel(),R[0].ravel()
    a=(r.conj()@y)/(r.conj()@r)
    return 10*math.log10(np.sum(np.abs(a*r)**2)/np.sum(np.abs(y-a*r)**2))

OUT={'rir':{'len_ms':round(L/FS*1000,1),'direct':d0,'early_ms':EARLY_MS,
            'ER_dB':round(10*math.log10(e_e/e_l),2)},
     'in':round(srr(X,T_),2),
     'frame_ms':round(NFFT/FS*1000,1),'hop_ms':round(HOP/FS*1000,1)}
print('\n输入（含混响）  %.2f dB'%OUT['in'])
K0=10                                           # 扫 Δ 时固定的阶数
OUT['delay']={}
for dl in (0,1,2,3,4,6):
    v=srr(wpe(X,K0,dl),T_); OUT['delay'][dl]=round(v,2)
    print('  Δ=%d（%.0f ms）  %7.2f dB'%(dl,dl*HOP/FS*1000,v))
D0=max(OUT['delay'],key=lambda k:OUT['delay'][k])   # 后面两个扫描都停在最优 Δ
OUT['best_delay']=D0
print('  → 后面两组都固定 Δ=%d'%D0)
OUT['taps']={}
for tp in (2,5,10,20,30):
    v=srr(wpe(X,tp,D0),T_); OUT['taps'][tp]=round(v,2)
    print('  K=%-3d %7.2f dB'%(tp,v))
K1=int(max(OUT['taps'],key=lambda k:OUT['taps'][k]))
OUT['best_taps']=K1
OUT['M']={}
for mm in (1,2,3,4):
    v=srr(wpe(X[:mm],K1,D0),T_[:mm]); OUT['M'][mm]=round(v,2)
    print('  M=%d  %7.2f dB'%(mm,v))
OUT['best']=OUT['M'][M]
OUT['unw']=round(srr(wpe(X,K1,D0,weighted=False),T_),2)
OUT['unw_delay']={}
for dl in (1,2,3,4):
    OUT['unw_delay'][dl]=round(srr(wpe(X,K1,dl,weighted=False),T_),2)
print('  不加权随 Δ：',OUT['unw_delay'])
print('  最优组合 Δ=%d K=%d M=%d → %.2f dB'%(D0,K1,M,OUT['best']))
print('  同一组合不加权            %7.2f dB'%OUT['unw'])
json.dump(OUT,open('demo_wpe.json','w'),ensure_ascii=False,indent=1)
