// 深化篇第三批公式（第六批）。
const katex = require('katex'), fs = require('fs');
const D = {
ola_delay: String.raw`\begin{aligned}&\text{单级：}\ \tau=W-H\ \text{（样点）}\\[4pt]
 &\text{级联：}\ \tau_{\text{总}}=\sum_i\,(W_i-H_i)\\[4pt]
 &\text{重建（COLA）：}\ \sum_k w[n-kH]=\text{常数}\\[4pt]
 &\text{Hann，跳步 }H:\ \sum_k w[n-kH]=\frac{W}{2H}\end{aligned}`,
cusum: String.raw`\begin{aligned}&S_t=\max\big(0,\ S_{t-1}+\ell_t\big),\ \ \ell_t=\frac{\mu}{\sigma^{2}}\Big(x_t-\frac{\mu}{2}\Big),\ \ \text{报警：}\ S_t>h\\[4pt]
 &I=\frac{\mu^{2}}{2\sigma^{2}}\ \text{（每样本的信息量）},\qquad \bar t_{\text{检测}}\approx\frac{h}{I}\ (+\text{过冲}),\qquad \mathrm{ARL}_0\ \ge\ e^{h}\end{aligned}`,
jit_late: String.raw`\text{目标延迟 }d=\mu+k\sigma\ \Rightarrow\ P(\text{迟到})=Q(k)\ \text{（高斯）};\qquad k=4:\ Q(4)\approx3.2\times10^{-5}`,
interleave: String.raw`\begin{aligned}&\text{码字取相隔 }D\text{ 个包的 }n\text{ 个包；}\ D\gg\frac1r\ \Rightarrow\ \text{近似独立丢包，}p_0\approx\pi_B\\[4pt]
 &P_{\text{fail}}\approx\sum_{i>n-k}\binom{n}{i}\pi_B^{\,i}(1-\pi_B)^{n-i},\qquad \text{代价：额外延迟}\ \approx\ nD\cdot T_{\text{pkt}}\end{aligned}`,
temp_cal: String.raw`p_i=\frac{e^{s_i/T}}{\sum_je^{s_j/T}},\qquad \hat T=\arg\min_T\ -\sum_u\ln p_{y_u}(T)\ \ \text{（对数似然的一维最大化）}`,
belief: String.raw`b_t(s)=\frac{P(o_t\mid s)\ \sum_{s'}P(s\mid s',a_{t})\,b_{t-1}(s')}{\sum_{s}P(o_t\mid s)\ \sum_{s'}P(s\mid s',a_{t})\,b_{t-1}(s')}`,
dur_alloc: String.raw`\min_{\mathbf d}\sum_i\frac{(d_i-\mu_i)^{2}}{\sigma_i^{2}}\ \ \text{s.t.}\ \sum_id_i=T\ \Longrightarrow\ d_i=\mu_i+\sigma_i^{2}\,\frac{T-\sum_j\mu_j}{\sum_j\sigma_j^{2}}`,
bayes_acc: String.raw`\text{两类等先验、等方差高斯：}\ \mathrm{Acc}^{*}=\Phi\Big(\frac{d'}{2}\Big),\qquad d'=\frac{\lvert\mu_1-\mu_0\rvert}{\sigma};\qquad \text{独立特征：}\ d'^{\,2}=\sum_kd_k'^{\,2}`,
fisher_z: String.raw`z=\operatorname{artanh}(r),\quad \mathrm{SE}_z=\frac{1}{\sqrt{n-3}},\quad \rho\in\Big[\tanh\big(z-\tfrac{1.96}{\sqrt{n-3}}\big),\ \tanh\big(z+\tfrac{1.96}{\sqrt{n-3}}\big)\Big]`,
sisdr: String.raw`\begin{aligned}&\alpha=\frac{\hat{\mathbf s}^{\top}\mathbf s}{\lVert\mathbf s\rVert^{2}},\quad \mathrm{SI\text{-}SDR}=10\log_{10}\frac{\lVert\alpha\mathbf s\rVert^{2}}{\lVert\alpha\mathbf s-\hat{\mathbf s}\rVert^{2}}=10\log_{10}\frac{\cos^{2}\theta}{1-\cos^{2}\theta}\\[4pt]
 &\cos\theta=\frac{\hat{\mathbf s}^{\top}\mathbf s}{\lVert\hat{\mathbf s}\rVert\,\lVert\mathbf s\rVert}\ \Rightarrow\ \hat{\mathbf s}\to c\,\hat{\mathbf s}\ \text{时不变}\end{aligned}`,
};
const out = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('fs_k6.json', JSON.stringify(out));
console.log('公式(六)', Object.keys(out).length);
