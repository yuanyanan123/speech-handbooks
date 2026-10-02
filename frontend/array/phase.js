// §04：2° 相位预算的推导
const katex = require('katex'), fs = require('fs');

const D = {
mm_model: String.raw`\tilde a_m=a_m\,\underbrace{(1+\delta_m)}_{\text{幅度误差}}\,
 \underbrace{e^{\,j\varphi_m}}_{\text{相位误差}}
 \;\approx\;a_m\bigl(1+\delta_m+j\varphi_m\bigr)
 \qquad
 \delta_m\sim(0,\sigma_g^{2}),\;\varphi_m\sim(0,\sigma_\varphi^{2})\ \text{互相独立}`,

mm_w: String.raw`\tilde w_m=w_m(1+\delta_m)e^{-j\varphi_m}\approx w_m+\underbrace{w_m(\delta_m-j\varphi_m)}_{\textstyle \Delta_m}
 \qquad\Longrightarrow\qquad
 E\bigl[\Delta\Delta^{H}\bigr]=\sigma^{2}\,\mathrm{diag}\bigl(\lvert w_m\rvert^{2}\bigr),
 \quad \sigma^{2}\overset{\text{定义}}{=}\sigma_g^{2}+\sigma_\varphi^{2}`,

mm_num: String.raw`E\bigl[\lvert\tilde{\mathbf w}^{H}\mathbf a\rvert^{2}\bigr]
 =\underbrace{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}_{=\,1}
 +\sigma^{2}\sum_m\lvert w_m\rvert^{2}\lvert a_m\rvert^{2}
 =1+\sigma^{2}\,\mathbf w^{H}\mathbf w
 =1+\underbrace{\frac{\sigma^{2}}{\mathrm{WNG}}}_{\textstyle \equiv\;x}`,

mm_den: String.raw`E\bigl[\tilde{\mathbf w}^{H}\boldsymbol\Gamma\tilde{\mathbf w}\bigr]
 =\mathbf w^{H}\boldsymbol\Gamma\mathbf w
 +\sigma^{2}\sum_m\lvert w_m\rvert^{2}\underbrace{\Gamma_{mm}}_{=\,1}
 =\frac{1}{\mathrm{DI}_0}+\frac{\sigma^{2}}{\mathrm{WNG}}
 =\frac{1}{\mathrm{DI}_0}+x`,

mm_res: String.raw`\boxed{\;\mathrm{DI}_{\text{实测}}=\frac{1+x}{\dfrac{1}{\mathrm{DI}_0}+x}\;,
 \qquad x=\frac{\sigma^{2}}{\mathrm{WNG}}\;}`,

mm_3db: String.raw`x=\frac{1}{\mathrm{DI}_0}
 \;\Longrightarrow\;
 \mathrm{DI}_{\text{实测}}=\frac{1+1/\mathrm{DI}_0}{2/\mathrm{DI}_0}=\frac{\mathrm{DI}_0+1}{2}
 \;\approx\;\frac{\mathrm{DI}_0}{2}
 \qquad\underbrace{\text{掉 3 dB}}_{\text{一半的指向性没了}}`,

mm_1db: String.raw`\mathrm{DI}_{\text{实测}}=\frac{\mathrm{DI}_0}{r},\;r=10^{0.1}
 \quad\Longrightarrow\quad
 x=\frac{r-1}{\mathrm{DI}_0-r}
 \quad\Longrightarrow\quad
 \sigma_{\max}=\sqrt{\frac{(r-1)\,\mathrm{WNG}}{\mathrm{DI}_0-r}}
 \;\approx\;0.51\sqrt{\frac{\mathrm{WNG}}{\mathrm{DI}_0}}`,

mm_rule: String.raw`\boxed{\;\sigma_{\max}\,[\,^{\circ}\,]\;\approx\;22\times
 10^{\frac{\mathrm{WNG}_{\mathrm{dB}}-\mathrm{DI}_{\mathrm{dB}}}{20}}\;}
 \qquad\qquad
 \underbrace{\sigma_g\ \text{与}\ \sigma_\varphi\ \text{各占一半}}
 _{\textstyle 1^{\circ}\ \text{相位}\;\leftrightarrow\;0.15\ \text{dB 幅度}}`,

mm_2deg: String.raw`\underbrace{\mathrm{DI}_0=12\ \text{dB}}_{\text{典型超指向}},\;
 \underbrace{\mathrm{WNG}=-10\ \text{dB}}_{\text{还能用的加载量}}
 \quad\Longrightarrow\quad
 \sigma_{\max}=22\times10^{\frac{-10-12}{20}}=1.71^{\circ}
 \;\approx\;\boxed{2^{\circ}}`,
};

const I = {
  x: String.raw`x=\sigma^{2}/\mathrm{WNG}`,
  sig: String.raw`\sigma^{2}=\sigma_g^{2}+\sigma_\varphi^{2}`,
  GI: String.raw`\boldsymbol\Gamma=\mathbf I`,
  wHw: String.raw`\mathbf w^{H}\mathbf w=1/\mathrm{WNG}`,
  DI0: String.raw`\mathrm{DI}_0`,
  sg: String.raw`\sigma_g`,
  sp: String.raw`\sigma_\varphi`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('phase.json', JSON.stringify(out));
fs.writeFileSync('phase_inline.json', JSON.stringify(oi));
console.log('相位预算:', Object.keys(out).length, '行内:', Object.keys(oi).length);
