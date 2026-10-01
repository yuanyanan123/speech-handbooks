import numpy as np, json, math
c=343.0
S=json.load(open('demo_scene.json')); sc=S['scene']; pp=S['paper']
FS,NFFT,HOP,M,D=sc['fs'],sc['nfft'],sc['hop'],sc['M'],sc['d_mm']/1000
xs,xi,xd=(np.load('demo_%s.npy'%k) for k in ('xs','xi','xd'))
x=xs+xi+xd
def gccp(a,b,n,band,interp=16):
    A,B=np.fft.rfft(a,n),np.fft.rfft(b,n)
    R=A*np.conj(B); R/=np.maximum(np.abs(R),1e-12)
    fr=np.fft.rfftfreq(n,1/FS)
    if band: R*=((fr>=band[0])&(fr<=band[1]))
    return R
def peak(Rsum,n,interp=16,max_tau=None):
    cc=np.fft.irfft(Rsum,n*interp); ms=n*interp//2
    if max_tau: ms=min(int(interp*max_tau*FS),ms)
    cc=np.concatenate((cc[-ms:],cc[:ms+1])); k=int(np.argmax(np.abs(cc)))
    return (k-ms)/float(interp*FS)
# 找语音起始（能量上升沿）
env=np.convolve(xs[0]**2,np.ones(256)/256,'same')
d=np.diff(env); on=int(np.argmax(d[FS//2:-FS//2]))+FS//2
print('true tau12 = %.2f µs   onset at %.3f s'%(pp['tau12_us'],on/FS))
for W,tag in [(512,'32 ms'),(1024,'64 ms'),(2048,'128 ms')]:
    for NF,lab in [(1,'单帧'),(8,'8 帧累加'),(32,'32 帧累加')]:
        for band in [(300,3000),(500,3500),None]:
            Rs=[np.zeros(W//2+1,complex) for _ in range(M-1)]
            for k in range(NF):
                s0=on+k*W//2
                for m in range(M-1):
                    Rs[m]+=gccp(x[m,s0:s0+W],x[m+1,s0:s0+W],W,band)
            taus=[peak(Rs[m],W,max_tau=D/c) for m in range(M-1)]
            tm=float(np.mean(taus)); cv=c*tm/D
            th=math.degrees(math.acos(np.clip(cv,-1,1)))
            print('  W=%-6s %-8s band=%-10s τ=%7.2f µs  θ=%6.2f°  (每对 %s)'
                  %(tag,lab,str(band),tm*1e6,th,[round(t*1e6,1) for t in taus]))
