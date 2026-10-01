#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""贯穿全书的统一算例：一间会议室、一个阵列、一个目标、一个干扰。
   把同一个时频点的数字沿整条链路走一遍，每一级都留下可核对的中间量。"""
import numpy as np, json, math
import pyroomacoustics as pra
rng = np.random.default_rng(20260920)
c = 343.0

# ══ 场景 ═══════════════════════════════════════════════════
ROOM = [6.0, 5.0, 3.3]              # V = 99 m³
RT60 = 0.6
FS   = 16000
M, D = 4, 0.035
CTR  = np.array([3.0, 1.2, 1.1])    # 阵列中心，阵轴沿 x
TH_S, R_S = 60.0, 1.5               # 目标：60°、1.5 m
TH_I, R_I = 130.0, 2.2              # 干扰：130°、2.2 m
NFFT, HOP = 512, 256
FBIN = 32                           # 1000 Hz（16000/512×32）

def pos(th, r):
    return CTR + r*np.array([math.cos(math.radians(th)), math.sin(math.radians(th)), 0])

mics = np.c_[[CTR + np.array([(m-(M-1)/2)*D, 0, 0]) for m in range(M)]].T
P_S, P_I = pos(TH_S, R_S), pos(TH_I, R_I)

OUT = {'scene': {
    'room': ROOM, 'V': round(ROOM[0]*ROOM[1]*ROOM[2],1), 'RT60': RT60, 'fs': FS,
    'M': M, 'd_mm': D*1000, 'ctr': list(CTR), 'th_s': TH_S, 'r_s': R_S,
    'th_i': TH_I, 'r_i': R_I, 'nfft': NFFT, 'hop': HOP,
    'fbin': FBIN, 'f_hz': FS/NFFT*FBIN,
    'p_s': [round(x,3) for x in P_S], 'p_i': [round(x,3) for x in P_I],
    'mic_x': [round(x,4) for x in mics[0]]}}

# ══ 0. 纸面先算：这组几何必然给出的数 ═════════════════════
f = FS/NFFT*FBIN
lam = c/f
tau12 = D*math.cos(math.radians(TH_S))/c
A = 0.161*OUT['scene']['V']/RT60
rc = 0.0566*math.sqrt(1.0*OUT['scene']['V']/RT60)
OUT['paper'] = {
  'f': f, 'lam_mm': lam*1000, 'kd': 2*math.pi*f/c*D,
  'tau12_us': tau12*1e6, 'tau12_samples': tau12*FS,
  'dphi_deg': math.degrees(2*math.pi*f*tau12),
  'f_alias': c/(2*D), 'L_mm': M*D*1000, 'L_over_lam': M*D/lam,
  'A_sabine': A, 'rc_omni': rc,
  'fresnel_m': 2*((M-1)*D)**2/lam,
  'gamma_bar': None}

m_ = np.arange(M); Dm = np.abs(m_[:,None]-m_[None,:])*D
G = np.sinc(2*f*Dm/c)
iu = np.triu_indices(M,1)
OUT['paper']['gamma_bar'] = float(G[iu].mean())
OUT['paper']['Gamma'] = [[round(float(x),6) for x in row] for row in G]

# ══ 1. 仿真：目标 / 干扰 / 扩散噪声 分别跑 ═════════════════
e_abs, max_order = pra.inverse_sabine(RT60, ROOM)
def sim(src_list, sig_list, extra=None):
    room = pra.ShoeBox(ROOM, fs=FS, materials=pra.Material(e_abs), max_order=max_order)
    room.add_microphone_array(pra.MicrophoneArray(mics, FS))
    for p, s in zip(src_list, sig_list):
        room.add_source(list(p), signal=s)
    room.simulate()
    return room.mic_array.signals

N = FS*4
def voiced(n):
    """语音式：基频 + 谐波 + 时变包络"""
    t = np.arange(n)/FS
    env = np.zeros(n); i = 0
    while i < n:
        L = rng.integers(int(0.12*FS), int(0.45*FS))
        if rng.random() < 0.6: env[i:i+L] = 1.0
        i += L
    env = np.convolve(env, np.hanning(801)/np.hanning(801).sum(), 'same')
    f0 = 120 + 25*np.sin(2*np.pi*1.7*t)
    ph = 2*np.pi*np.cumsum(f0)/FS
    x = sum(np.sin(k*ph)/k for k in range(1, 26))
    return x*env/np.max(np.abs(x*env))

s_sig = voiced(N)
i_sig = rng.standard_normal(N)*0.12                 # 风扇：宽带稳态
xs = sim([P_S],[s_sig])
xi = sim([P_I],[i_sig])
L = min(xs.shape[1], xi.shape[1]); xs, xi = xs[:,:L], xi[:,:L]

# 扩散噪声：房间四周多个不相关源
NDIF = 24
dif_pos = [CTR + 2.0*np.array([math.cos(a), math.sin(a), 0.25*math.sin(3*a)])
           for a in np.linspace(0, 2*math.pi, NDIF, endpoint=False)]
dif_pos = [np.clip(p, 0.3, np.array(ROOM)-0.3) for p in dif_pos]
xd = sim(dif_pos, [rng.standard_normal(N)*0.05 for _ in range(NDIF)])
xd = xd[:, :L]

np.save('demo_xs.npy', xs); np.save('demo_xi.npy', xi); np.save('demo_xd.npy', xd)
json.dump(OUT, open('demo_scene.json','w'), ensure_ascii=False, indent=1)
print('仿真完成  xs %s  xi %s  xd %s' % (xs.shape, xi.shape, xd.shape))
for k,v in OUT['paper'].items():
    if k not in ('Gamma',): print('  %-14s %s'%(k, round(v,4) if isinstance(v,float) else v))
