// 深化篇第四批公式（第七批）。
const katex = require('katex'), fs = require('fs');
const D = {
power_n: String.raw`\begin{aligned}&H_0:\ \Delta=0\ \ \text{对}\ \ H_1:\ \Delta>0,\qquad z=\frac{\bar d}{\sigma_d/\sqrt n}\\[4pt]
 &n=\Big(\frac{(z_{1-\alpha/2}+z_{1-\beta})\,\sigma_d}{\Delta}\Big)^{2},\qquad \mathrm{功效}=1-\beta\end{aligned}`,
gain_stage: String.raw`\begin{aligned}&\text{模拟增益 }G\text{ 后接 ADC：}\ \ \sigma_{\text{in}}^{2}(G)=\sigma_m^{2}+\frac{\sigma_q^{2}}{G^{2}},\quad \sigma_q^{2}=\frac{\Delta^{2}}{12},\ \Delta=\frac{2A}{2^{N}}\\[4pt]
 &\text{数字增益（在 ADC 之后）：}\ \ \sigma_{\text{in}}^{2}=\sigma_m^{2}+\sigma_q^{2}\quad(\text{量化噪声与信号同被放大，不改善})\end{aligned}`,
lin_interp: String.raw`\begin{aligned}&\text{线性插值误差：}\ e(\alpha)=x(n+\alpha)-\big[(1-\alpha)x(n)+\alpha\,x(n+1)\big]\\[4pt]
 &\qquad\approx-\frac{\alpha(1-\alpha)}{2}\,x''\\[4pt]
 &\alpha\sim U(0,1),\ x=\sin(\omega n):\ \ \mathrm{SNR}\approx10\log_{10}\frac{120}{\omega^{4}},\ \ \omega=\frac{2\pi f}{f_s}\\[4pt]
 &\text{（每升高一个倍频程降 12 dB）}\end{aligned}`,
mm1: String.raw`\begin{aligned}&\text{M/M/1，到达率 }\lambda,\ \text{服务率 }\mu,\ \rho=\lambda/\mu:\quad T\sim\mathrm{Exp}(\mu-\lambda)\\[4pt]
 &\mathrm E[T]=\frac{1}{\mu(1-\rho)},\qquad t_q=\frac{-\ln(1-q)}{\mu-\lambda}\ \ \text{（第 }q\text{ 分位）}\end{aligned}`,
rnnt_lat: String.raw`\begin{aligned}&\alpha(t,u)=\alpha(t-1,u)\,b(t-1,u)+\alpha(t,u-1)\,y(t,u-1)\\[4pt]
 &P(\mathbf y\mid\mathbf x)=\alpha(T-1,U)\,b(T-1,U)\\[4pt]
 &b(t,u)=P(\text{blank}\mid t,u),\quad y(t,u)=P(y_{u+1}\mid t,u)\\[4pt]
 &\#\text{对齐路径}=\binom{T+U-1}{U}\end{aligned}`,
stft_par: String.raw`\begin{aligned}&\sum_{m}\sum_{k}\lvert X_m[k]\rvert^{2}=N_{\text{fft}}\sum_nx^{2}[n]\sum_mw^{2}[n-mH]\\[4pt]
 &\qquad\approx N_{\text{fft}}\,\frac{\sum_jw_j^{2}}{H}\,\lVert x\rVert^{2},\qquad \text{Hann：}\sum_jw_j^{2}=\tfrac38W\\[4pt]
 &x\to c\,x:\ \ \ln\lvert X\rvert\ \text{整体平移}\ \ln c\\[4pt]
 &\Rightarrow\ \text{对数谱损失对整体增益不是尺度不变的}\end{aligned}`,
};
const out = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('fs_k7.json', JSON.stringify(out));
console.log('公式(七)', Object.keys(out).length);
