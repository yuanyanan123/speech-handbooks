#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§14 算例：波束一动，AEC 的 ERLE 上限就被钉死在哪。"""
import numpy as np, json, math
import pyroomacoustics as pra
rng=np.random.default_rng(20260928)
c=343.0
S=json.load(open('demo_scene.json'))['scene']
ROOM=[6.0,5.0,3.3]; RT60=0.6; FS=S['fs']; M,D=S['M'],S['d_mm']/1000
CTR=np.array(S['ctr'])
mics=np.c_[[CTR+np.array([(m-(M-1)/2)*D,0,0]) for m in range(M)]].T
SPK=CTR+np.array([0.0,-0.08,0.02])              # 扬声器就在设备上，离阵列 8 cm
e_abs,mo=pra.inverse_sabine(RT60,ROOM)
room=pra.ShoeBox(ROOM,fs=FS,materials=pra.Material(e_abs),max_order=mo)
room.add_microphone_array(pra.MicrophoneArray(mics,FS))
room.add_source(list(SPK)); room.compute_rir()
g=[np.asarray(room.rir[m][0]) for m in range(M)]
Lg=max(len(r) for r in g); g=np.array([np.r_[r,np.zeros(Lg-len(r))] for r in g])
LA=int(0.128*FS)                                 # AEC 滤波器长 128 ms
g=g[:,:LA]
OUT={'spk_dist_cm':8,'aec_len_ms':128,'rir_len_ms':round(Lg/FS*1000,1)}

f=1000.0; k=2*math.pi*f/c
m_=np.arange(M)-(M-1)/2
Dm=np.abs(np.arange(M)[:,None]-np.arange(M)[None,:])*D
G=np.sinc(2*f*Dm/c)
def steer(th): return np.exp(1j*k*D*m_*math.cos(math.radians(th)))
def wmv(th,eps=1e-2):
    a=steer(th); w=np.linalg.solve(G+eps*np.trace(G)/M*np.eye(M),a); return w/(a.conj()@w)

def geff(w):
    """把复权近似成实权（取实部与相位对齐后的幅度）——时域等效回声路径"""
    return np.real(np.sum(np.conj(w)[:,None]*g,axis=0))

def erle_limit(w1,w2):
    """AEC 已收敛到 w1 的路径，波束换成 w2 后的瞬时 ERLE 上限"""
    h1,h2=geff(w1),geff(w2)
    return -20*math.log10(np.linalg.norm(h2-h1)/np.linalg.norm(h2))

w0=wmv(60.0)
OUT['dth']={}
print('AEC 收敛在 60° 的波束上，波束一变，ERLE 上限：')
for dth in (0.5,1,2,5,10,20):
    v=erle_limit(w0,wmv(60.0+dth)); OUT['dth'][dth]=round(v,2)
    print('  指向变 %4.1f°  →  ERLE 上限 %6.2f dB'%(dth,v))
OUT['deps']={}
print('\n或者指向不变、加载量变（自适应重估 R_n 时常见）：')
for e2 in (3e-3,5e-3,2e-2,5e-2):
    v=erle_limit(w0,wmv(60.0,e2)); OUT['deps'][e2]=round(v,2)
    print('  ε 从 1e-2 变到 %-7.0e →  ERLE 上限 %6.2f dB'%(e2,v))

OUT['wrel']={}
for dth in (0.5,1.0,2.0,5.0):
    OUT['wrel'][dth]=round(float(np.linalg.norm(wmv(60.0+dth)-w0)/np.linalg.norm(w0)),4)
print('\n权重本身只变了这么点：', {k:'%.1f%%'%(v*100) for k,v in OUT['wrel'].items()})

# ── 时域 NLMS 验证 ────────────────────────────────────────
def nlms(u,d,L,mu=0.5,eps=1e-6):
    N=len(u); w=np.zeros(L); e=np.zeros(N); ub=np.zeros(L)
    for n in range(N):
        ub[1:]=ub[:-1]; ub[0]=u[n]
        y=w@ub; e[n]=d[n]-y
        w+=mu*e[n]*ub/(ub@ub+eps)
    return e,w
N=FS*8
u=rng.standard_normal(N)*0.5                      # 远端参考
h_a=geff(w0); h_b=geff(wmv(65.0))                 # 指向 60° / 65°
TARGET_ERLE=35.0                                  # 近端底噪按现实 AEC 水平定标
ech=np.convolve(u,h_a)[:N]
NEAR=math.sqrt(np.mean(ech**2)/10**(TARGET_ERLE/10))
def erle(d,e,seg):
    return 10*math.log10(np.sum(d[seg]**2)/np.sum(e[seg]**2))
# A：波束固定（AEC 在波束后，但波束不动）
nz=rng.standard_normal(N)*NEAR
d_fix=ech+nz
e_fix,_=nlms(u,d_fix,LA)
# B：波束在 4 秒处从 60° 跳到 65°
d_var=np.r_[np.convolve(u,h_a)[:N//2],np.convolve(u,h_b)[:N][N//2:]]+nz
e_var,_=nlms(u,d_var,LA)
tail=slice(int(3.5*FS),int(4.0*FS)); after=slice(int(4.0*FS),int(4.5*FS))
inst=slice(int(4.0*FS),int(4.0*FS)+FS//20)          # 跳变后头 50 ms
late=slice(int(7.0*FS),int(8.0*FS))
OUT['nlms']={'fix_tail':round(erle(d_fix,e_fix,tail),2),
             'var_before':round(erle(d_var,e_var,tail),2),
             'var_inst':round(erle(d_var,e_var,inst),2),
             'var_after':round(erle(d_var,e_var,after),2),
             'var_late':round(erle(d_var,e_var,late),2),
             'target':TARGET_ERLE,
             'limit_5deg':round(erle_limit(w0,wmv(65.0)),2)}
print('\n时域 NLMS 验证（波束 4 s 处从 60° 跳到 65°）：')
print('  波束固定，3.5–4.0 s       ERLE %6.2f dB'%OUT['nlms']['fix_tail'])
print('  跳变前 3.5–4.0 s          ERLE %6.2f dB'%OUT['nlms']['var_before'])
print('  跳变后头 50 ms            ERLE %6.2f dB  ← 塌到解析上限'%OUT['nlms']['var_inst'])
print('  跳变后 4.0–4.5 s          ERLE %6.2f dB  （已在重收敛）'%OUT['nlms']['var_after'])
print('  重新收敛 7.0–8.0 s        ERLE %6.2f dB'%OUT['nlms']['var_late'])
print('  解析上限（5° 那一档）      %6.2f dB'%OUT['nlms']['limit_5deg'])
# ERLE 轨迹（100 ms 一块），给图用
B=FS//10; nb=N//B
trA=[];trB=[]
for b in range(nb):
    s=slice(b*B,(b+1)*B)
    trA.append(round(erle(d_fix,e_fix,s),2)); trB.append(round(erle(d_var,e_var,s),2))
OUT['trace']={'blk_ms':100,'fix':trA,'var':trB}
json.dump(OUT,open('demo_aec.json','w'),ensure_ascii=False,indent=1)
