// 把所有公式用 KaTeX 服务端渲染成自包含 HTML（不依赖 CDN / 运行时 JS）
const katex = require('katex');
const fs = require('fs');

const F = {
  steer: String.raw`\tau_m(\theta)=-\frac{\mathbf r_m\cdot\mathbf u(\theta)}{c}
  \qquad
  a_m(\omega,\theta)=e^{-j\omega\tau_m(\theta)}
  \qquad
  y(\omega)=\mathbf w^{H}(\omega)\,\mathbf x(\omega)`,

  coh: String.raw`\Gamma_{ij}(\omega)=\operatorname{sinc}\!\left(\frac{\omega d_{ij}}{c}\right)
  =\frac{\sin(k\,d_{ij})}{k\,d_{ij}},\qquad k=\frac{\omega}{c}=\frac{2\pi f}{c}`,

  farfield: String.raw`r_{\text{far}}=\frac{2L^{2}}{\lambda}`,

  nearsteer: String.raw`a_m=\frac{1}{r_m}\,e^{-jk r_m}`,

  rc: String.raw`r_c=0.057\sqrt{\frac{Q\,V}{\mathrm{RT}_{60}}}`,

  rcq: String.raw`r_c\propto\sqrt{Q},\qquad \mathrm{DI}=10\log_{10}Q
  \qquad\Longrightarrow\qquad \mathrm{DI}\;{+}6\,\text{dB}\;\Rightarrow\;r_c\times 2`,

  alias: String.raw`f_{\text{alias}}=\frac{c}{2d}`,

  flow: String.raw`f_{\text{low}}\approx\frac{c}{2L},\qquad L=(M-1)\,d`,

  diwng: String.raw`\begin{aligned}
  \mathrm{DI}&=10\log_{10}\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\boldsymbol\Gamma\mathbf w}\\[4pt]
  \mathrm{WNG}&=10\log_{10}\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\mathbf w}
  \end{aligned}`,

  limits: String.raw`\mathrm{WNG}_{\text{DAS}}=10\log_{10}M\qquad
  \mathrm{DI}_{\max}^{\text{端射}}=20\log_{10}M`,

  sdload: String.raw`\mathbf w=\frac{(\boldsymbol\Gamma+\varepsilon\mathbf I)^{-1}\mathbf a}
  {\mathbf a^{H}(\boldsymbol\Gamma+\varepsilon\mathbf I)^{-1}\mathbf a}`,

  dma: String.raw`D(\theta)=A+(1-A)\cos\theta
  \qquad
  Q=\frac{1}{A^{2}+\dfrac{(1-A)^{2}}{3}}`,

  dmaloss: String.raw`20\log_{10}\!\bigl(2\sin(kd/2)\bigr)\;\approx\;20\log_{10}(kd)
  \qquad (kd\ll 1)`,

  gcc: String.raw`R_{12}(\tau)=\int\frac{X_1(\omega)X_2^{*}(\omega)}
  {\lvert X_1(\omega)X_2^{*}(\omega)\rvert}\,e^{j\omega\tau}\,d\omega
  \qquad
  \hat\theta=\arccos\frac{c\,\hat\tau}{d}`,

  wpe: String.raw`\mathbf d_t=\mathbf x_t-\sum_{\tau=\Delta}^{\Delta+L}\mathbf G_\tau^{H}\,\mathbf x_{t-\tau}`,

  post: String.raw`H(\omega,t)=\frac{\hat S(\omega,t)}{\hat S(\omega,t)+\hat N(\omega,t)}`,

  // —— 附录速查表用的小公式 ——
  lam:     String.raw`\lambda=c/f`,
  aliasS:  String.raw`f_{\text{alias}}=\dfrac{c}{2d}`,
  flowS:   String.raw`f_{\text{low}}\approx\dfrac{c}{2L}`,
  beamw:   String.raw`\Delta\theta\approx\lambda/L`,
  pherr:   String.raw`\Delta\varphi=360^{\circ}\,f\,\dfrac{\Delta x}{c}`,
  steerS:  String.raw`a_m=e^{-j\omega\tau_m}`,
  cohS:    String.raw`\Gamma_{ij}=\operatorname{sinc}(\omega d_{ij}/c)`,
  dasS:    String.raw`\mathbf w=\mathbf a/M`,
  sdS:     String.raw`\mathbf w=\dfrac{(\boldsymbol\Gamma+\varepsilon\mathbf I)^{-1}\mathbf a}{\mathbf a^{H}(\boldsymbol\Gamma+\varepsilon\mathbf I)^{-1}\mathbf a}`,
  mvdrS:   String.raw`\mathbf w=\dfrac{\mathbf R_n^{-1}\mathbf a}{\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}`,
  gevS:    String.raw`\mathbf R_s\mathbf w=\lambda\,\mathbf R_n\mathbf w`,
  diS:     String.raw`10\log_{10}\dfrac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\boldsymbol\Gamma\mathbf w}`,
  wngS:    String.raw`10\log_{10}\dfrac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\mathbf w}`,
  dmaS:    String.raw`D(\theta)=A+(1-A)\cos\theta`,
  dmalossS:String.raw`20\log_{10}\bigl(2\sin(kd/2)\bigr)`,
  gccS:    String.raw`R_{12}(\tau)=\displaystyle\int\frac{X_1X_2^{*}}{\lvert X_1X_2^{*}\rvert}e^{j\omega\tau}d\omega`,
  wpeS:    String.raw`\mathbf d_t=\mathbf x_t-\!\!\sum_{\tau=\Delta}^{\Delta+L}\!\!\mathbf G_\tau^{H}\mathbf x_{t-\tau}`,
  rcS:     String.raw`r_c=0.057\sqrt{QV/\mathrm{RT}_{60}}`,
  farS:    String.raw`r_{\text{far}}=2L^{2}/\lambda`,

  // —— 行内变量 ——
  i_rc: String.raw`r_c`,  i_G: String.raw`\boldsymbol\Gamma`, i_eps: String.raw`\varepsilon`,
  i_lam2: String.raw`\lambda/2`, i_M: String.raw`M`, i_L: String.raw`L`,
  i_kd: String.raw`kd`, i_Q: String.raw`Q`, i_w: String.raw`\mathbf w`,
  i_invr2: String.raw`1/r^{2}`, i_Ginv: String.raw`\boldsymbol\Gamma^{-1}`,
  i_cd2: String.raw`c/(2d)`, i_cd: String.raw`c/d`, i_d: String.raw`d`,
};

const out = {};
for (const [k, v] of Object.entries(F)) {
  out[k] = katex.renderToString(v, {
    displayMode: !k.startsWith('i_'),
    throwOnError: true, strict: 'ignore', output: 'html',
  });
}
fs.writeFileSync('formulas.json', JSON.stringify(out));

// 找出实际用到的字体族
const all = Object.values(out).join(' ');
const css = fs.readFileSync('node_modules/katex/dist/katex.min.css', 'utf8');
const used = new Set(['KaTeX_Main']);
for (const m of css.matchAll(/\.katex\s+\.([a-zA-Z0-9_-]+)\{[^}]*font-family:\s*([A-Za-z_0-9]+)/g)) {
  if (new RegExp('class="[^"]*\\b' + m[1] + '\\b').test(all)) used.add(m[2]);
}
for (const fam of ['KaTeX_Size1','KaTeX_Size2','KaTeX_Size3','KaTeX_Size4']) {
  if (all.includes(fam.toLowerCase().replace('katex_','')) || all.includes('delimsizing') || all.includes('sqrt')) used.add(fam);
}
console.log('公式数:', Object.keys(out).length);
console.log('需要的字体族:', [...used].sort().join(', '));
fs.writeFileSync('fonts_used.json', JSON.stringify([...used]));

// —— 行内符号：让正文里的变量和公式里的排版完全一致 ——
const INLINE = {
 rm:String.raw`\mathbf r_m`, utheta:String.raw`\mathbf u(\theta)`, c:'c',
 w:String.raw`\mathbf w`, a:String.raw`\mathbf a`, Gam:String.raw`\boldsymbol\Gamma`,
 eps:String.raw`\varepsilon`, I:String.raw`\mathbf I`, M:'M', L:'L', d:'d',
 lam:String.raw`\lambda`, Q:'Q', V:'V', RT:String.raw`\mathrm{RT}_{60}`, k:'k',
 tau:String.raw`\tau`, Del:String.raw`\Delta`, A:'A', th:String.raw`\theta`,
 Rn:String.raw`\mathbf R_n`, Rs:String.raw`\mathbf R_s`, Shat:String.raw`\hat S`,
 Nhat:String.raw`\hat N`, X1:'X_1', X2:'X_2', dij:'d_{ij}', rc:'r_c',
 rfar:String.raw`r_{\text{far}}`, falias:String.raw`f_{\text{alias}}`,
 flow2:String.raw`f_{\text{low}}`, Gtau:String.raw`\mathbf G_\tau`,
 om:String.raw`\omega`, kd:'kd', lam2:String.raw`\lambda/2`, cd2:'c/(2d)', cd:'c/d',
 invr2:'1/r^2', DI:String.raw`\mathrm{DI}`, WNG:String.raw`\mathrm{WNG}`,
 taum:String.raw`\tau_m`, Mm1d:'(M-1)d', y:String.raw`y(\omega)`, H:String.raw`H(\omega,t)`,
};
const inl = {};
for (const [k,v] of Object.entries(INLINE))
  inl[k] = katex.renderToString(v,{displayMode:false,throwOnError:true,strict:'ignore',output:'html'});
fs.writeFileSync('inline.json', JSON.stringify(inl));
console.log('行内符号:', Object.keys(inl).length);
