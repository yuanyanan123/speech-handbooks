#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§16 算例：同一段录音，三种做法三个结果。"""
import numpy as np, json, math
c=343.0
S=json.load(open('demo_scene.json')); sc=S['scene']; pp=S['paper']
FS,NFFT,HOP,M,D=sc['fs'],sc['nfft'],sc['hop'],sc['M'],sc['d_mm']/1000
xs,xi,xd=(np.load('demo_%s.npy'%k) for k in ('xs','xi','xd'))
x=xs+xi+xd
fr=np.fft.rfftfreq(NFFT,1/FS)
def stft(z):
    w=np.hanning(NFFT+1)[:-1]; idx=np.arange(0,z.shape[1]-NFFT,HOP)
    return np.array([[np.fft.rfft(z[m,i:i+NFFT]*w) for i in idx] for m in range(z.shape[0])])
X,Xs=stft(x),stft(xs)
env=np.mean(np.abs(Xs[0])**2,axis=1)
act=np.where(env>np.percentile(env,70))[0]
mx=np.array([(m-(M-1)/2)*D for m in range(M)])

def pair_gcc(band,W=4096,interp=16):
    on=int(np.argmax(np.diff(np.convolve(xs[0]**2,np.ones(256)/256,'same'))[FS//2:-FS//2]))+FS//2
    taus=[]
    for m in range(M-1):
        a_,b_=x[m,on:on+W],x[m+1,on:on+W]
        n=1<<int(np.ceil(np.log2(W*2)))
        R=np.fft.rfft(a_,n)*np.conj(np.fft.rfft(b_,n)); R/=np.maximum(np.abs(R),1e-12)
        f2=np.fft.rfftfreq(n,1/FS)
        if band: R*= ((f2>=band[0])&(f2<=band[1]))
        cc=np.fft.irfft(R,n*interp); ms=min(int(interp*(D/c)*FS),n*interp//2)
        cc=np.concatenate((cc[-ms:],cc[:ms+1])); k=int(np.argmax(np.abs(cc)))
        taus.append((k-ms)/float(interp*FS))
    tm=float(np.mean(taus)); cv=np.clip(c*tm/D,-1,1)
    return tm*1e6, math.degrees(math.acos(cv)), [round(t*1e6,1) for t in taus]

def srp(frames,band,step=0.5):
    sel=(fr>=band[0])&(fr<=band[1])
    th=np.arange(1,180,step)
    Z=X[:,frames][:,:,sel]; Z=Z/np.maximum(np.abs(Z),1e-12)
    Pw=np.zeros(len(th))
    for i,t in enumerate(th):
        tau=-mx*math.cos(math.radians(t))/c
        st=np.exp(-2j*np.pi*fr[sel][None,:]*tau[:,None])
        Pw[i]=np.sum(np.abs(np.einsum('mtf,mf->tf',Z,np.conj(st)))**2)
    k=int(np.argmax(Pw))
    Pn=(Pw-Pw.min())/(Pw.max()-Pw.min())
    # −3 dB 宽度（归一化功率 0.5 处）
    lo=k; hi=k
    while lo>0 and Pn[lo]>0.5: lo-=1
    while hi<len(th)-1 and Pn[hi]>0.5: hi+=1
    return th[k], th[hi]-th[lo], th.tolist(), Pn.tolist()

R={}
R['pair_full']=pair_gcc(None)
R['pair_band']=pair_gcc((300,3000))
for nf in (4,16,64):
    pk,wd,th,Pn=srp(act[:nf],(300,4900))
    R['srp_%d'%nf]={'peak':round(pk,2),'w3db':round(wd,1)}
    if nf==4: R['srp_curve']={'th':th,'P':[round(v,4) for v in Pn]}
R['truth']={'th_s':sc['th_s'],'th_i':sc['th_i'],'tau_true_us':round(pp['tau12_us'],2)}
json.dump(R,open('demo_doa.json','w'),ensure_ascii=False)
for k,v in R.items():
    if k!='srp_curve': print('  %-12s %s'%(k,v))
