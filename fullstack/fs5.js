// 深化篇第二批的公式（第五批）。
const katex = require('katex'), fs = require('fs');
const D = {
mos_var: String.raw`r_{ij}=\mu+a_i+b_j+\varepsilon_{ij},\quad \bar r=\frac{1}{IJ}\sum_{i,j}r_{ij}\ \Rightarrow\ \mathrm{Var}(\bar r)=\frac{\sigma_{\text{item}}^{2}}{I}+\frac{\sigma_{\text{rater}}^{2}}{J}+\frac{\sigma_{\varepsilon}^{2}}{IJ}`,
prebuf: String.raw`\begin{aligned}&A_k=\sum_{i\le k}p_i\ \ (\text{第 }k\text{ 块就绪的时刻}),\qquad \text{第 }k\text{ 块必须在 }T_0+(k-1)c\text{ 前就绪}\\[4pt]
 &T_0^{*}=\max_{k}\big(A_k-(k-1)c\big)\ \ (\text{首包延迟的下界}),\qquad \mathrm{RTF}=\frac{\mathrm E[p]}{c}<1\ \text{是必要条件}\end{aligned}`,
wm_det: String.raw`\begin{aligned}&z=\frac{1}{\sigma_x\sqrt N}\sum_{i=1}^{N}y_iw_i,\quad y=x+\alpha w\\[4pt]
 &H_0:\ z\sim\mathcal N(0,1),\qquad H_1:\ z\sim\mathcal N\!\Big(\frac{\alpha\sqrt N}{\sigma_x},1\Big)\\[4pt]
 &\mathrm{FPR}=Q(\tau),\qquad \mathrm{TPR}=Q\Big(\tau-\frac{\alpha\sqrt N}{\sigma_x}\Big)\end{aligned}`,
chain_attr: String.raw`\begin{aligned}&E=1-\prod_i(1-e_i)\ \Longleftrightarrow\ -\ln(1-E)=\sum_i\big[-\ln(1-e_i)\big]\\[4pt]
 &\text{把环节 }i\text{ 换成完美：}\ E_{-i}=1-\frac{1-E}{1-e_i},\qquad \text{贡献份额}\ s_i=\frac{-\ln(1-e_i)}{-\ln(1-E)}\end{aligned}`,
paired: String.raw`\mathrm{Var}(\bar d)=\frac{\mathrm{Var}(x_A-x_B)}{n}=\frac{2\sigma^{2}(1-\rho)}{n}\qquad(\rho:\ \text{同一条目上两系统得分的相关})`,
adc_load: String.raw`\begin{aligned}&D(A)=\underbrace{\frac{\Delta^{2}}{12}}_{\text{粒度噪声}},\ \Delta=\frac{2A}{2^{N}}\ \ +\ \ \underbrace{2\!\int_A^\infty(x-A)^{2}f(x)\,dx}_{\text{削波噪声}}\\[6pt]
 &\text{高斯：}\ D_{\text{clip}}=2\big[(1+A^{2})Q(A)-A\,\phi(A)\big]\sigma^{2},\qquad \text{拉普拉斯：}\ D_{\text{clip}}=\sigma^{2}e^{-\sqrt2A/\sigma}\end{aligned}`,
kaiser: String.raw`N\approx\frac{A-7.95}{2.285\,\Delta\omega}+1,\qquad \beta=0.1102\,(A-8.7)\ \ (A>50\ \mathrm{dB})\qquad(A:\ \text{阻带衰减},\ \Delta\omega:\ \text{过渡带宽，rad/样本})`,
drift_est: String.raw`\hat\delta=\text{时间戳对本地计数的最小二乘斜率}-1,\qquad \mathrm{Var}(\hat\delta)=\frac{\sigma_t^{2}}{\sum_k(t_k-\bar t)^{2}}\approx\frac{12\,\sigma_t^{2}}{T^{2}N^{3}}`,
};
const out = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('fs_k5.json', JSON.stringify(out));
console.log('公式(五)', Object.keys(out).length);
