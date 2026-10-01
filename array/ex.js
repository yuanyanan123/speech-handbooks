// 各节算例的公式：数字直接写进式子，读者能逐步复核
const katex = require('katex'), fs = require('fs');
const E = JSON.parse(fs.readFileSync('demo_ex.json', 'utf8'));
const P = E.par, S17 = E.s17, S18 = E.s18, S13 = E.s13, S16 = E.s16;
const r = (x, n) => Number(x).toFixed(n);

const D = {
// ── 场景直接派生（§12 标准算例卡）────────────────────────
ex_geo: String.raw`\begin{aligned}
 \tau_{12}&=\frac{d\cos\theta_s}{c}
 =\frac{0.035\times\cos 60^{\circ}}{343}
 =\frac{0.0175}{343}=${r(P.tau12_us,2)}\ \mu\text{s}\\[8pt]
 \tau_{12}f_s&=${r(P.tau12_us,2)}\times10^{-6}\times16000
 =\underbrace{${r(P.tau12_smp,4)}\ \text{样点}}_{\text{不是整数——13 节要处理它}}
 \end{aligned}`,

ex_phase: String.raw`\Delta\varphi_{12}=2\pi f\tau_{12}
 =2\pi\times1000\times${r(P.tau12_us,2)}\times10^{-6}
 =${r(2*Math.PI*1000*P.tau12_us*1e-6,4)}\ \text{rad}
 =${r(P.dphi_deg,2)}^{\circ}`,

// ── §13 分数延迟 ─────────────────────────────────────────
ex_frac: String.raw`\underbrace{${r(P.tau12_smp,4)}\ \xrightarrow{\ \text{取整}\ }\ 1}
 _{\text{误差 }${r(Math.abs(S13.err_smp),4)}\text{ 样点}}
 \quad\Longrightarrow\quad
 \Delta\varphi_{\text{误差}}(f)=2\pi f\cdot\frac{${r(Math.abs(S13.err_smp),4)}}{f_s}
 \quad\Longrightarrow\quad
 \underbrace{${r(S13.err_deg['4000'],1)}^{\circ}\ @\ 4\ \text{kHz}}
 _{\text{预算是 }2^{\circ}}`,

// ── §16 DOA 反推 ────────────────────────────────────────
ex_doa: String.raw`\underbrace{\Delta\varphi_{12}=${r(P.dphi_deg,2)}^{\circ}}_{\text{测到的}}
 \;\xrightarrow{\ \tau=\Delta\varphi/2\pi f\ }\;
 ${r(P.tau12_us,2)}\ \mu\text{s}
 \;\xrightarrow{\ \cos\theta=c\tau/d\ }\;
 \frac{343\times${r(P.tau12_us,2)}\times10^{-6}}{0.035}=${r(S16.cos_back,4)}
 \;\Longrightarrow\;
 \theta=${r(S16.th_back,1)}^{\circ}`,

ex_res: String.raw`\tau_{\max}=\frac{d}{c}=${r(S16.tau_max_us,2)}\ \mu\text{s}
 =\underbrace{${r(S16.tau_max_smp,4)}\ \text{样点}}_{0^{\circ}\text{ 到 }180^{\circ}\text{ 的全部范围}}
 \qquad\Longrightarrow\qquad
 \underbrace{\pm1\ \text{样点}\ \leftrightarrow\ 0^{\circ}\sim${r(S16.th_of_pm1smp[0],1)}^{\circ}}
 _{\text{整点分辨率完全不够用}}`,

// ── §17 导向矢量与相干矩阵 ───────────────────────────────
ex_a: String.raw`\mathbf a=\Bigl[e^{-j${r(P.dphi_deg*1.5,2)}^{\circ}},\;
 e^{-j${r(P.dphi_deg*0.5,2)}^{\circ}},\;
 e^{+j${r(P.dphi_deg*0.5,2)}^{\circ}},\;
 e^{+j${r(P.dphi_deg*1.5,2)}^{\circ}}\Bigr]^{T}
 \qquad\underbrace{\text{相邻差 }${r(P.dphi_deg,2)}^{\circ}}_{\text{就是上面那个 }\Delta\varphi_{12}}`,

ex_gam: String.raw`\Gamma_{ij}=\mathrm{sinc}\bigl(k\lvert i-j\rvert d\bigr):\quad
 \underbrace{\mathrm{sinc}(${r(P.kd,4)})=${r(S17.sinc[1],4)}}_{\text{相邻}}
 \quad
 \underbrace{\mathrm{sinc}(${r(2*P.kd,4)})=${r(S17.sinc[2],4)}}_{\text{隔一个}}
 \quad
 \underbrace{\mathrm{sinc}(${r(3*P.kd,4)})=${r(S17.sinc[3],4)}}_{\text{两端}}`,

ex_das: String.raw`\mathbf w_{\text{DAS}}=\frac{\mathbf a}{4}
 \;\Longrightarrow\;
 \underbrace{\mathrm{WNG}=10\log_{10}4=${r(S17.DAS.wng,2)}\ \text{dB}}_{\text{精确，与频率无关}}
 \quad
 \underbrace{\mathrm{DI}=${r(S17.DAS.di,2)}\ \text{dB}}_{L/\lambda=${r(P.L_lam,3)}\text{，几乎没有指向性}}`,

ex_sd: String.raw`\mathbf a^{H}\boldsymbol\Gamma^{-1}\mathbf a=${r(S17.aHGinv_a,4)}
 =${r(S17.aHGinv_a_dB,2)}\ \text{dB}
 \qquad\underbrace{\ll 20\log_{10}4=${r(S17.M2_dB,2)}\ \text{dB}}
 _{kd=${r(P.kd,3)}\text{ 还不够小}}`,

ex_load: String.raw`\underbrace{\varepsilon=0}_{\mathrm{WNG}=${r(S17.SD0.wng,1)}}
 \;\to\;
 \underbrace{10^{-3}}_{${r(S17['SD0.001'].wng,1)}}
 \;\to\;
 \underbrace{10^{-2}}_{${r(S17['SD0.01'].wng,1)}}
 \;\to\;
 \underbrace{10^{-1}}_{${r(S17['SD0.1'].wng,1)}}
 \qquad
 \mathrm{DI}:\;${r(S17.SD0.di,2)}\to${r(S17['SD0.001'].di,2)}\to${r(S17['SD0.01'].di,2)}\to${r(S17['SD0.1'].di,2)}`,

// ── §18 后置滤波 ─────────────────────────────────────────
ex_phi: String.raw`\Phi_{ij}=\varphi_s+\varphi_n\Gamma_{ij}=1+\Gamma_{ij}:\quad
 ${r(S18.Phi_ij[0],4)},\;${r(S18.Phi_ij[1],4)},\;${r(S18.Phi_ij[2],4)}
 \qquad\qquad
 \Phi_{ii}=1+1=2`,

ex_zel: String.raw`\hat G_{\text{Zel}}
 =\frac{\bigl\langle\Phi_{ij}\bigr\rangle}{\Phi_{ii}}
 =\frac{${r(S18.Phi_ij.reduce((a,b)=>a+b,0)/6,4)}}{2}
 =${r(S18.G_zel,4)}
 \qquad\Longrightarrow\qquad
 \underbrace{\text{只压 }${r(S18.sup_zel,2)}\ \text{dB}}_{\text{该压 }${r(S18.sup_true,2)}\text{ dB}}`,

ex_mcc: String.raw`\hat\varphi_s^{(12)}
 =\frac{\Phi_{12}-\Gamma_{12}\Phi_{ii}}{1-\Gamma_{12}}
 =\frac{${r(S18.Phi_ij[0],4)}-${r(S18.Gamma_ij[0],4)}\times2}{1-${r(S18.Gamma_ij[0],4)}}
 =\frac{${r(S18.Phi_ij[0]-S18.Gamma_ij[0]*2,4)}}{${r(1-S18.Gamma_ij[0],4)}}
 =\underbrace{1.0000}_{\text{六对全部如此}}
 \;\Longrightarrow\;
 \hat G=\tfrac12`,
};

const I = {
  f: String.raw`f=1\ \text{kHz}`,
  kd: String.raw`kd=${r(P.kd,4)}`,
  tau: String.raw`\tau_{12}=${r(P.tau12_us,2)}\ \mu\text{s}`,
  dphi: String.raw`\Delta\varphi_{12}=${r(P.dphi_deg,2)}^{\circ}`,
  Ll: String.raw`L/\lambda=${r(P.L_lam,3)}`,
  rc: String.raw`r_c=${r(P.rc,3)}\ \text{m}`,
  aGa: String.raw`\mathbf a^{H}\boldsymbol\Gamma^{-1}\mathbf a=${r(S17.aHGinv_a,4)}`,
  gb: String.raw`\bar\Gamma=${r(S18.gbar,4)}`,
};
const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('ex.json', JSON.stringify(out));
fs.writeFileSync('ex_inline.json', JSON.stringify(oi));
console.log('算例公式:', Object.keys(out).length, '行内:', Object.keys(oi).length);
