import numpy as np, json, math
c=343.0
S=json.load(open('demo_scene.json')); sc=S['scene']; pp=S['paper']
FS,NFFT,HOP,M,D=sc['fs'],sc['nfft'],sc['hop'],sc['M'],sc['d_mm']/1000
xs,xi,xd=(np.load('demo_%s.npy'%k) for k in ('xs','xi','xd'))
x=xs+xi+xd
def stft(x,n=NFFT,hop=HOP):
    w=np.hanning(n+1)[:-1]; idx=np.arange(0,x.shape[1]-n,hop)
    return np.array([[np.fft.rfft(x[m,i:i+n]*w) for i in idx] for m in range(x.shape[0])])
X=stft(x); Xs=stft(xs)
fr=np.fft.rfftfreq(NFFT,1/FS)
mx=np.array([(m-(M-1)/2)*D for m in range(M)])
def srp(X,frames,band):
    sel=(fr>=band[0])&(fr<=band[1])
    th=np.arange(1,180,0.5); P=np.zeros(len(th))
    Z=X[:,frames][:,:,sel]                                   # (M,T,F)
    Z=Z/np.maximum(np.abs(Z),1e-12)                          # PHAT 白化
    for i,t in enumerate(th):
        tau=-mx*math.cos(math.radians(t))/c                  # 相对中心
        st=np.exp(-2j*np.pi*fr[sel][None,:]*tau[:,None])     # (M,F)
        y=np.einsum('mtf,mf->tf',Z,np.conj(st))
        P[i]=np.sum(np.abs(y)**2)
    return th,P
env=np.mean(np.abs(Xs[0])**2,axis=1)
act=np.where(env>np.percentile(env,70))[0]
print('真值 60°，干扰 130°')
for band in [(300,3000),(500,3500),(300,4900),(80,8000)]:
    for nf,lab in [(4,'4 帧'),(16,'16 帧'),(len(act),'全部语音帧')]:
        fs_=act[:nf] if nf<len(act) else act
        th,P=srp(X,fs_,band)
        k=int(np.argmax(P)); pk=th[k]
        # 次峰
        m2=P.copy(); m2[max(0,k-20):k+20]=0; k2=int(np.argmax(m2))
        print('  band=%-10s %-10s 峰 %6.2f°  次峰 %6.2f°  峰/次 %.2f'
              %(str(band),lab,pk,th[k2],P[k]/P[k2]))
