// 《全栈音频链路手册》深化篇的公式（第四批）。
const katex = require('katex'), fs = require('fs');
const D = {
dl_wng: String.raw`\begin{aligned}&\min_{\mathbf w}\ \mathbf w^{H}\boldsymbol\Phi\mathbf w+\delta\,\mathbf w^{H}\mathbf w\ \ \text{s.t.}\ \mathbf w^{H}\mathbf a=1\\[4pt]
 &\Longrightarrow\ \mathbf w_\delta=\frac{(\boldsymbol\Phi+\delta\mathbf I)^{-1}\mathbf a}{\mathbf a^{H}(\boldsymbol\Phi+\delta\mathbf I)^{-1}\mathbf a}\\[4pt]
 &\mathrm{WNG}(\mathbf w)=\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\mathbf w}\ \xrightarrow{\ \delta\to\infty\ }\ M\end{aligned}`,
nlms_track: String.raw`\begin{aligned}&\mathrm E\lVert\boldsymbol\Delta'\rVert^{2}=\Big(1-\frac{\mu(2-\mu)}{L}\Big)\mathrm E\lVert\boldsymbol\Delta\rVert^{2}+\frac{\mu^{2}\sigma_v^{2}}{L\sigma_x^{2}}+Lq\\[6pt]
 &\Longrightarrow\ \mathrm{MSD}_\infty=\underbrace{\frac{\mu\,\sigma_v^{2}}{(2-\mu)\sigma_x^{2}}}_{\text{噪声项（随 }\mu\text{ 增大）}}+\underbrace{\frac{L^{2}q}{\mu(2-\mu)}}_{\text{滞后项（随 }\mu\text{ 增大而减小）}}\end{aligned}`,
nlms_opt: String.raw`\mu\ll1:\quad \mathrm{MSD}_\infty\approx\frac{\mu\sigma_v^{2}}{2\sigma_x^{2}}+\frac{L^{2}q}{2\mu}\ \Rightarrow\ \mu^{*}=\frac{L\sqrt q\,\sigma_x}{\sigma_v},\qquad \mathrm{MSD}^{*}=\frac{L\sqrt q\,\sigma_v}{\sigma_x}`,
pwf: String.raw`\begin{aligned}&\min_G\ \underbrace{(1-G)^{2}\sigma_s^{2}}_{\text{语音失真}}\ \ \text{s.t.}\ \ \underbrace{G^{2}\sigma_n^{2}}_{\text{残余噪声}}\le R\\[6pt]
 &\Longrightarrow\ G=\frac{\xi}{\xi+\mu},\quad \mu=\xi\Big(\frac{1}{G}-1\Big),\quad G=\sqrt{R/\sigma_n^{2}}\end{aligned}`,
rt60: String.raw`h[n]=\epsilon[n]\,e^{-\rho n},\ \ \rho=\frac{3\ln10}{T_{60}\,f_s}\qquad
 \mathrm{EDC}(n)=\sum_{m\ge n}h^{2}[m],\qquad E_{\text{late}}=\sigma^{2}\,\frac{e^{-2\rho N_0}}{1-e^{-2\rho}}`,
dct_klt: String.raw`G_{\text{cod}}=\frac{\frac1N\sum_{k}\sigma_k^{2}}{\big(\prod_{k}\sigma_k^{2}\big)^{1/N}},\qquad
 \mathbf C_{ij}=\rho^{\lvert i-j\rvert}\ \text{(AR(1))},\quad \sigma_k^{2}=\text{变换后第 }k\text{ 个系数的方差}`,
logLin: String.raw`\hat w=\arg\max_w\ \kappa\ln p(\mathbf x\mid w)+\lambda\ln P(w),\qquad \text{贝叶斯最优：}\ \lambda/\kappa=1`,
rej_thr: String.raw`\text{接受}\iff(1-p)\,c_{\text{err}}\le c_{\text{rej}}\ \Longleftrightarrow\ p\ge t^{*}=1-\frac{c_{\text{rej}}}{c_{\text{err}}}`,
crf: String.raw`\begin{aligned}&p(\mathbf y\mid\mathbf x)=\frac{e^{s(\mathbf y)}}{Z},\qquad s(\mathbf y)=\sum_t E_{t,y_t}+\sum_t A_{y_{t-1},y_t}\\[4pt]
 &\alpha_t(j)=E_{t,j}+\ln\sum_i e^{\alpha_{t-1}(i)+A_{ij}},\qquad \ln Z=\ln\sum_j e^{\alpha_T(j)}\\[4pt]
 &\frac{\partial\ln p(\mathbf y^{*})}{\partial E_{t,k}}=\mathbb 1[y^{*}_t=k]-p(y_t=k\mid\mathbf x)\end{aligned}`,
rd_bound: String.raw`\begin{aligned}&D(R)=\sigma^{2}\,2^{-2R}\ \ (\text{高斯源，}R\text{：比特/维})\\[4pt]
 &R_{\text{RVQ}}=\frac{Q\log_2K}{d}\ \Rightarrow\ \mathrm{MSE}_Q\ \ge\ \sigma^{2}\,2^{-2Q\log_2K/d}\end{aligned}`,
ge: String.raw`\begin{aligned}&\pi_B=\frac{p}{p+r},\qquad \mathrm E[\text{突发长度}]=\frac1r\\[4pt]
 &P_{\text{fail}}^{(n,k)}=\sum_{i=n-k+1}^{n}\binom{n}{i}p_0^{\,i}(1-p_0)^{n-i}\end{aligned}`,
wer_var: String.raw`R=\frac{\sum_iE_i}{\sum_iN_i},\qquad \widehat{\mathrm{SE}}(R)=\frac{\sqrt{\sum_i\big(E_i-R\,N_i\big)^{2}}}{\sum_iN_i}`,
loop_gain: String.raw`\begin{aligned}&y[n]=G\sum_{k\ge1}h_k\,y[n-k]+x[n]\ \Rightarrow\ 1-G\sum_{k}h_kz^{-k}=0:\ \ \text{稳定}\iff\text{所有根 }\lvert z\rvert<1\\[4pt]
 &G\sum_k\lvert h_k\rvert<1\ \Rightarrow\ \text{稳定（充分条件，保守）}\\[4pt]
 &h\to h\,10^{-E/20}\ \Rightarrow\ G_{\text{crit}}\ \text{抬高}\ E\ \mathrm{dB}\end{aligned}`,
};
const out = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('fs_k4.json', JSON.stringify(out));
console.log('公式(四)', Object.keys(out).length);
