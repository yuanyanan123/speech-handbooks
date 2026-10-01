#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""沿链路把同一个时频点走一遍，记录每一级的中间量。"""
import numpy as np, json, math
c=343.0
S=json.load(open('demo_scene.json')); sc=S['scene']; pp=S['paper']
FS,NFFT,HOP,M,D,FBIN = sc['fs'],sc['nfft'],sc['hop'],sc['M'],sc['d_mm']/1000,sc['fbin']
f = pp['f']
xs,xi,xd = (np.load('demo_%s.npy'%k) for k in ('xs','xi','xd'))
R={}

def stft(x):
    w=np.hanning(NFFT+1)[:-1]
    idx=np.arange(0,x.shape[1]-NFFT,HOP)
    return np.array([[np.fft.rfft(x[m,i:i+NFFT]*w) for i in idx] for m in range(x.shape[0])])
Xs,Xi,Xd = stft(xs),stft(xi),stft(xd)
T=Xs.shape[1]

# ── 选一帧：目标在该频点最活跃 ────────────────────────────
pwr = np.abs(Xs[0,:,FBIN])**2
t0 = int(np.argmax(pwr[20:T-20]))+20
R['frame']={'t':t0,'of':T,'t_sec':round(t0*HOP/FS,3)}

X = Xs+Xi+Xd
def fmt(z): return [[round(float(v.real),4),round(float(v.imag),4)] for v in z]
R['tf']={'f':f,'x':fmt(X[:,t0,FBIN]),'xs':fmt(Xs[:,t0,FBIN]),
         'xi':fmt(Xi[:,t0,FBIN]),'xd':fmt(Xd[:,t0,FBIN])}
# 幅度/相位表示
z=X[:,t0,FBIN]
R['tf']['mag']=[round(float(abs(v)),4) for v in z]
R['tf']['ph_deg']=[round(float(np.degrees(np.angle(v))),2) for v in z]
R['tf']['dph_deg']=[round(float(np.degrees(np.angle(z[m+1]/z[m]))),2) for m in range(M-1)]
zs=Xs[:,t0,FBIN]
R['tf']['s_dph_deg']=[round(float(np.degrees(np.angle(zs[m+1]/zs[m]))),2) for m in range(M-1)]

# ── 1. GCC-PHAT：用全段时域信号估 DOA ────────────────────
def gcc_phat(x1,x2,fs,max_tau=None,interp=16,band=None):
    """τ = t1 − t2（1 号麦比 2 号麦晚到多少秒）。band=(lo,hi) 时限频带积分。"""
    n=1<<int(np.ceil(np.log2(len(x1)+len(x2))))
    X1,X2=np.fft.rfft(x1,n),np.fft.rfft(x2,n)
    Ra=X1*np.conj(X2)
    Ra/=np.maximum(np.abs(Ra),1e-12)
    if band:
        fr=np.fft.rfftfreq(n,1/fs)
        Ra=Ra*((fr>=band[0])&(fr<=band[1]))
    cc=np.fft.irfft(Ra,n*interp); ms=n*interp//2
    if max_tau: ms=min(int(interp*n*max_tau*fs/n),ms)
    cc=np.concatenate((cc[-ms:],cc[:ms+1])); k=int(np.argmax(np.abs(cc)))
    return (k-ms)/float(interp*fs), float(np.abs(cc[k]))
xt = xs+xi+xd
seg = slice(t0*HOP-NFFT*4, t0*HOP+NFFT*4)
BAND=(300.,3000.)
def doa(band):
    taus=[];peaks=[]
    for m in range(M-1):
        tt,pk=gcc_phat(xt[m,seg],xt[m+1,seg],FS,max_tau=D/c,band=band)
        taus.append(tt);peaks.append(pk)
    tm=float(np.mean(taus)); cv=c*tm/D
    return taus,peaks,tm,cv,math.degrees(math.acos(np.clip(cv,-1,1)))
taus,peaks,tau_mean,cosv,th_hat = doa(BAND)
_,_,tm_full,cv_full,th_full = doa(None)
R['doa']={'band':list(BAND),
          'tau_us':[round(t*1e6,2) for t in taus],'peak':[round(p,4) for p in peaks],
          'tau_mean_us':round(tau_mean*1e6,2),'cos':round(cosv,4),
          'th_hat':round(th_hat,2),'th_true':sc['th_s'],
          'tau_true_us':round(pp['tau12_us'],2),
          'full_tau_us':round(tm_full*1e6,2),'full_th':round(th_full,2)}

# ── 2. 波束：三种权 ──────────────────────────────────────
def steer(th):
    m=np.arange(M)
    return np.exp(1j*2*np.pi*f/c*D*(m-(M-1)/2)*math.cos(math.radians(th)))
m_=np.arange(M); Dm=np.abs(m_[:,None]-m_[None,:])*D
G=np.sinc(2*f*Dm/c)
a=steer(th_hat); a_true=steer(sc['th_s'])
W={}
W['DAS']=a/M
for eps,tag in [(0.0,'SD0'),(1e-2,'SD2'),(1e-1,'SD1')]:
    w=np.linalg.solve(G+eps*np.trace(G)/M*np.eye(M),a); W[tag]=w/(a.conj()@w)
# MVDR：用"只有干扰+扩散"的帧估 R_n（门控正确的情形）
sil = np.abs(Xs[0,:,FBIN])**2 < np.percentile(np.abs(Xs[0,:,FBIN])**2,25)
Zn = (Xi+Xd)[:,sil,FBIN]
Rn = (Zn@Zn.conj().T)/Zn.shape[1]
Rn_r = Rn + 1e-2*np.trace(Rn)/M*np.eye(M)
w=np.linalg.solve(Rn_r,a); W['MVDR']=w/(a.conj()@w)
# 门控失败：R_n 里混进目标
Zall=(Xs+Xi+Xd)[:,:,FBIN]
Rall=(Zall@Zall.conj().T)/Zall.shape[1]
w=np.linalg.solve(Rall+1e-2*np.trace(Rall)/M*np.eye(M),a); W['MVDR_bad']=w/(a.conj()@w)

def metrics(w):
    ps=np.mean(np.abs(Xs[:,:,FBIN].T@w.conj())**2)
    pi=np.mean(np.abs(Xi[:,:,FBIN].T@w.conj())**2)
    pd=np.mean(np.abs(Xd[:,:,FBIN].T@w.conj())**2)
    di=abs(w.conj()@a_true)**2/np.real(w.conj()@G@w)
    wng=abs(w.conj()@a_true)**2/np.real(w.conj()@w)
    return dict(sinr=10*math.log10(ps/(pi+pd)), di=10*math.log10(di),
                wng=10*math.log10(wng), gain=abs(w.conj()@a_true))
ps0=np.mean(np.abs(Xs[0,:,FBIN])**2); pn0=np.mean(np.abs((Xi+Xd)[0,:,FBIN])**2)
R['bf']={'in_sinr':round(10*math.log10(ps0/pn0),2),
         'Gamma':[[round(float(x),4) for x in r] for r in G],
         'a':fmt(a), 'a_deg':[round(float(np.degrees(np.angle(v))),2) for v in a]}
for k,w in W.items():
    mm=metrics(w)
    R['bf'][k]={'w':fmt(w),'w_mag':[round(float(abs(v)),4) for v in w],
                'w_deg':[round(float(np.degrees(np.angle(v))),2) for v in w],
                **{kk:round(vv,2) for kk,vv in mm.items()}}

# ── 3. 后置滤波：Zelinski vs McCowan ─────────────────────
Zt = (Xs+Xi+Xd)[:,:,FBIN]
Phi = (Zt@Zt.conj().T)/Zt.shape[1]
iu=np.triu_indices(M,1)
Pii=np.real(np.diag(Phi)).mean()
zel=np.real(Phi[iu]).mean()/Pii
mcc=np.mean((np.real(Phi[iu])-G[iu]*Pii)/(1-G[iu]))/Pii
true_xi = ps0/pn0
R['pf']={'Phi_ii':round(float(Pii),4),
         'Phi_ij':[round(float(v),4) for v in np.real(Phi[iu])],
         'Gamma_ij':[round(float(v),4) for v in G[iu]],
         'gamma_bar':round(float(G[iu].mean()),4),
         'G_zel':round(float(np.clip(zel,0,1)),4),
         'G_mcc':round(float(np.clip(mcc,0,1)),4),
         'G_true':round(float(true_xi/(1+true_xi)),4),
         'sup_zel':round(-20*math.log10(max(np.clip(zel,1e-6,1),1e-6)),2),
         'sup_mcc':round(-20*math.log10(max(np.clip(mcc,1e-6,1),1e-6)),2),
         'sup_true':round(-20*math.log10(true_xi/(1+true_xi)),2)}
json.dump(R,open('demo_res.json','w'),ensure_ascii=False,indent=1)
print(json.dumps({k:(v if k!='bf' else {kk:(vv if not isinstance(vv,dict) else
  {k3:v3 for k3,v3 in vv.items() if k3 in ('sinr','di','wng','gain')}) for kk,vv in v.items() if kk!='Gamma'})
  for k,v in R.items()}, ensure_ascii=False, indent=1)[:3000])
