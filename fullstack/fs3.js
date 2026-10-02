// 《全栈音频链路手册》补遗篇（硬件、时钟、传输、推导、指标）的公式。第三批。
const katex = require('katex'), fs = require('fs');

const D = {

// ══ 16 采集与播放 ══════════════════════════════════════════════
alias: String.raw`X_s(f)=\frac{1}{T_s}\sum_{k=-\infty}^{\infty}X\big(f-k\,f_s\big)\qquad\Longrightarrow\qquad \text{不混叠的条件：}\ \ f_{\max}<\frac{f_s}{2}`,
sqnr_adc: String.raw`\mathrm{SQNR}=6.02\,N+1.76\ \ [\mathrm{dB}]\ \ (\text{N 位，满量程正弦}),\qquad
 \mathrm{SQNR}_{\Delta\Sigma}\approx6.02N+1.76-10\log_{10}\frac{\pi^{2L}}{2L+1}+(20L+10)\log_{10}\mathrm{OSR}`,
zoh: String.raw`\lvert H_{\text{ZOH}}(f)\rvert=\Big\lvert\frac{\sin(\pi f/f_s)}{\pi f/f_s}\Big\rvert,\qquad
 \lvert H_{\text{ZOH}}(f_s/2)\rvert=\frac{2}{\pi}\ \Rightarrow\ -3.92\ \mathrm{dB}`,
thd: String.raw`\mathrm{THD}=\frac{\sqrt{\sum_{n\ge2}V_n^{2}}}{V_1},\qquad
 L_p=20\log_{10}\frac{p}{p_0}\ \ (p_0=20\,\mu\mathrm{Pa}),\qquad L_p(r)=L_p(r_0)-20\log_{10}\frac{r}{r_0}\ \ (\text{自由场})`,

// ══ 17 重采样与时钟 ════════════════════════════════════════════
resamp_rat: String.raw`\frac{f_{s,\text{出}}}{f_{s,\text{入}}}=\frac{L}{M}:\quad \uparrow L\ \to\ \text{低通}\ \Big(\omega_c=\frac{\pi}{\max(L,M)}\Big)\ \to\ \downarrow M,\qquad
 \tau_{\text{FIR}}=\frac{N_{\text{tap}}-1}{2\,f_s}\ \ (\text{线性相位})`,
sincint: String.raw`x(t)=\sum_{n}x[n]\,\mathrm{sinc}\big(f_s t-n\big),\qquad h[n]=2f_c\,\mathrm{sinc}(2f_c\,n)\,w[n]\ \ (\text{窗化 sinc：实际用的有限长近似})`,
drift2: String.raw`\Delta n(t)=f_s\,\varepsilon\,t,\quad\varepsilon=\mathrm{ppm}\times10^{-6},\qquad
 t_{\text{错开一块}}=\frac{B}{f_s\,\varepsilon},\qquad \hat\varepsilon=\frac{\Delta\hat\tau}{\Delta t}\ \ (\text{延迟估计随时间的斜率})`,

// ══ 18 编解码与传输 ════════════════════════════════════════════
jitter: String.raw`\hat d_i=\alpha\,\hat d_{i-1}+(1-\alpha)\,n_i,\qquad \hat v_i=\alpha\,\hat v_{i-1}+(1-\alpha)\,\lvert\hat d_i-n_i\rvert,\qquad t_{\text{播出}}=\hat d_i+4\,\hat v_i`,
bw: String.raw`\text{带宽}=\frac{(\text{载荷字节}+\text{头字节})\times8}{T_{\text{帧}}},\qquad \text{头}=\underbrace{20}_{\text{IP}}+\underbrace{8}_{\text{UDP}}+\underbrace{12}_{\text{RTP}}=40\ \text{字节}`,
plc2: String.raw`\hat x[n]=g^{\,j}\,x\big[n-j\,T_0\big],\quad j=\Big\lceil\frac{n-n_0}{T_0}\Big\rceil,\ \ g<1\qquad(\text{按基音周期重复，每重复一周期衰减})`,

// ══ 19 关键推导补遗 ════════════════════════════════════════════
nlms_rec: String.raw`\begin{aligned}
 &\boldsymbol\Delta=\mathbf h-\mathbf w,\quad e=\mathbf x^{\top}\boldsymbol\Delta+v,\quad \boldsymbol\Delta'=\boldsymbol\Delta-\mu\,\frac{e\,\mathbf x}{\lVert\mathbf x\rVert^{2}}\\[4pt]
 &\mathbb E\lVert\boldsymbol\Delta'\rVert^{2}=\Big(1-\frac{\mu(2-\mu)}{L}\Big)\,\mathbb E\lVert\boldsymbol\Delta\rVert^{2}+\frac{\mu^{2}\sigma_v^{2}}{L\,\sigma_x^{2}}\qquad(\text{白输入、}v\perp\mathbf x)\\[4pt]
 &\text{稳态：}\ \mathbb E\lVert\boldsymbol\Delta\rVert^{2}_{\infty}=\frac{\mu}{2-\mu}\frac{\sigma_v^{2}}{\sigma_x^{2}}\ \Rightarrow\ \text{额外均方误差}=\sigma_x^{2}\,\mathbb E\lVert\boldsymbol\Delta\rVert^{2}_{\infty}=\frac{\mu}{2-\mu}\sigma_v^{2}
 \end{aligned}`,
kalman_der: String.raw`\begin{aligned}
 &h_{t+1}=A\,h_t+w_t\ (\mathrm{Var}\,w=q),\qquad y_t=x_t\,h_t+v_t\ (\mathrm{Var}\,v=\Phi_v)\\[4pt]
 &\hat h=\hat h^{-}+K\,(y-x\hat h^{-})\ \Rightarrow\ P(K)=\lvert1-Kx\rvert^{2}P^{-}+\lvert K\rvert^{2}\Phi_v\\[4pt]
 &\frac{\partial P}{\partial K^{*}}=0\ \Rightarrow\ K=\frac{P^{-}x^{*}}{\lvert x\rvert^{2}P^{-}+\Phi_v},\qquad P=(1-Kx)\,P^{-}
 \end{aligned}`,
gausscond: String.raw`\begin{pmatrix}S\\Y\end{pmatrix}\sim\mathcal{CN}\Big(\mathbf 0,\begin{pmatrix}\Phi_s&\Phi_s\\\Phi_s&\Phi_s+\Phi_n\end{pmatrix}\Big)
 \ \Rightarrow\ S\mid Y\sim\mathcal{CN}\Big(\frac{\Phi_s}{\Phi_s+\Phi_n}Y,\ \frac{\Phi_s\Phi_n}{\Phi_s+\Phi_n}\Big)`,
bw_hmm: String.raw`\begin{aligned}
 \beta_t(i)&=\sum_{j}a_{ij}\,b_j(\mathbf o_{t+1})\,\beta_{t+1}(j)\\[4pt]
 \gamma_t(i)&=\frac{\alpha_t(i)\,\beta_t(i)}{P(\mathbf O)},\qquad
 \xi_t(i,j)=\frac{\alpha_t(i)\,a_{ij}\,b_j(\mathbf o_{t+1})\,\beta_{t+1}(j)}{P(\mathbf O)}\\[4pt]
 \bar a_{ij}&=\frac{\sum_{t}\xi_t(i,j)}{\sum_{t}\gamma_t(i)}\\[4pt]
 Q(\lambda,\bar\lambda)&=\sum_{\mathbf q}P(\mathbf q\mid\mathbf O,\bar\lambda)\,\log P(\mathbf O,\mathbf q\mid\lambda)
 \end{aligned}`,
ctc_grad: String.raw`\begin{aligned}
 P(\mathbf y\mid\mathbf x)&=\sum_{s}\frac{\alpha_t(s)\,\beta_t(s)}{y_t^{\,l'_s}}\ \ (\text{任意固定的 }t)\ \Rightarrow\ \frac{\partial P}{\partial y_t^{\,k}}=\frac{1}{(y_t^{\,k})^{2}}\sum_{s:\,l'_s=k}\alpha_t(s)\,\beta_t(s)\\[4pt]
 \frac{\partial\mathcal L}{\partial u_t^{\,k}}&=y_t^{\,k}-\frac{1}{y_t^{\,k}\,P(\mathbf y\mid\mathbf x)}\sum_{s:\,l'_s=k}\alpha_t(s)\,\beta_t(s),\qquad\mathcal L=-\ln P,\ \ y=\mathrm{softmax}(u)
 \end{aligned}`,
softmaxj: String.raw`\frac{\partial s_i}{\partial z_j}=s_i\big(\delta_{ij}-s_j\big),\qquad
 \mathrm{Var}(\mathbf q^{\top}\mathbf k)=d_k\ \ (\text{各分量零均值、单位方差、相互独立})\ \Rightarrow\ \text{除以 }\sqrt{d_k}\text{ 使方差回到 1}`,
gan_opt: String.raw`\min_G\max_D\ \mathbb E_{x}\big[\log D(x)\big]+\mathbb E_{z}\big[\log\big(1-D(G(z))\big)\big],\qquad
 D^{\ast}(x)=\frac{p_{\text{data}}(x)}{p_{\text{data}}(x)+p_g(x)},\qquad C(G)=-\log4+2\,\mathrm{JS}\big(p_{\text{data}}\Vert p_g\big)`,
vq_ste: String.raw`\mathcal L=\lVert x-\hat x\rVert^{2}+\big\lVert\mathrm{sg}[\mathbf z_e]-\mathbf e\big\rVert^{2}+\beta\,\big\lVert\mathbf z_e-\mathrm{sg}[\mathbf e]\big\rVert^{2},\qquad
 \frac{\partial\mathcal L}{\partial\mathbf z_e}\approx\frac{\partial\mathcal L}{\partial\mathbf z_q}\ \ (\text{直通估计：argmin 不可导，把量化当作恒等映射})`,
ddpm_post: String.raw`\begin{aligned}
 q(x_{t-1}\mid x_t,x_0)&=\mathcal N\big(\tilde{\boldsymbol\mu}_t,\ \tilde\beta_t\mathbf I\big)\\[4pt]
 \tilde{\boldsymbol\mu}_t&=\frac{1}{\sqrt{\alpha_t}}\Big(x_t-\frac{\beta_t}{\sqrt{1-\bar\alpha_t}}\,\boldsymbol\epsilon\Big)\\[4pt]
 \mathrm{KL}\big(q\Vert p_\theta\big)&\propto\lVert\tilde{\boldsymbol\mu}_t-\boldsymbol\mu_\theta\rVert^{2}\ \Rightarrow\ \mathcal L_{\text{simple}}=\mathbb E\big\lVert\boldsymbol\epsilon-\boldsymbol\epsilon_\theta(x_t,t)\big\rVert^{2}
 \end{aligned}`,
fm_marg: String.raw`\begin{aligned}
 &\partial_tp_t+\nabla\!\cdot\!\big(p_t\,v_t\big)=0\ \ (\text{连续性方程})\\[4pt]
 &p_t(x)\,v_t(x)=\int p_t(x\mid x_1)\,u_t(x\mid x_1)\,q(x_1)\,dx_1\ \Longrightarrow\ v_t(x)=\mathbb E\big[u_t\mid x_t=x\big]
 \end{aligned}`,

// ══ 20 评价指标 ════════════════════════════════════════════════
segsnr: String.raw`\mathrm{SegSNR}=\frac{1}{N_f}\sum_{m=1}^{N_f}\mathrm{clip}\Big(10\log_{10}\frac{\sum_{n}s^{2}[n]}{\sum_{n}\big(s[n]-\hat s[n]\big)^{2}},\ -10,\ 35\Big),\qquad
 \mathrm{LSD}=\frac1T\sum_{t}\sqrt{\frac1F\sum_{k}\Big(10\log_{10}\frac{\lvert S\rvert^{2}}{\lvert\hat S\rvert^{2}}\Big)^{2}}`,
pesq: String.raw`\mathrm{PESQ}_{\text{raw}}=4.5-0.1\,d_{\text{sym}}-0.0309\,d_{\text{asym}},\qquad
 \text{MOS-LQO}=0.999+\frac{4}{1+e^{-1.4945\,\mathrm{PESQ}_{\text{raw}}+4.6607}}`,
stoi: String.raw`\begin{aligned}
 &\bar{\mathbf y}=\min\!\Big(\frac{\lVert\mathbf x\rVert}{\lVert\mathbf y\rVert}\mathbf y,\ \big(1+10^{-\beta/20}\big)\mathbf x\Big),\quad\beta=-15\ \mathrm{dB}\\[4pt]
 &d_{j,m}=\frac{(\mathbf x-\mu_x)^{\top}(\bar{\mathbf y}-\mu_{\bar y})}{\lVert\mathbf x-\mu_x\rVert\,\lVert\bar{\mathbf y}-\mu_{\bar y}\rVert},\qquad \mathrm{STOI}=\frac{1}{JM}\sum_{j,m}d_{j,m}
 \end{aligned}`,
f0rmse: String.raw`\mathrm{F0\text{-}RMSE}=\sqrt{\mathbb E\Big[\Big(1200\log_2\frac{\hat f_0}{f_0}\Big)^{2}\Big]}\ \ (\text{音分}),\qquad
 \mathrm{ECE}=\sum_{b=1}^{B}\frac{\lvert\mathcal B_b\rvert}{N}\,\big\lvert\mathrm{acc}(\mathcal B_b)-\mathrm{conf}(\mathcal B_b)\big\rvert`,
nsample: String.raw`n=\Big(\frac{(z_{1-\alpha/2}+z_{1-\beta})\,\sigma_d}{\Delta}\Big)^{2}\ \ (\text{配对评分：区分差距 }\Delta),\qquad
 p=\Pr\big(X\ge k\mid X\sim\mathrm{Bin}(n,\tfrac12)\big)\ \ (\text{AB 偏好：}k\text{ 次偏好 A})`,

// ══ 9、13 的演进链 ═════════════════════════════════════════════
slu: String.raw`P(c\mid\mathbf x)=\mathrm{softmax}\big(\mathbf W\mathbf h_{\text{[CLS]}}\big),\qquad
 P(\mathbf y\mid\mathbf x)=\frac1Z\exp\Big(\sum_{t}\psi(y_t,\mathbf x)+\sum_{t}\phi(y_{t-1},y_t)\Big),\qquad
 P(c\mid X)\approx\sum_{W\in\mathcal N}P(c\mid W)\,\tilde P(W\mid X)`,
cmos: String.raw`\mathrm{CMOS}=\frac1N\sum_{i=1}^{N}\big(r_i^{A}-r_i^{B}\big),\qquad \text{标准误}=\frac{s_d}{\sqrt N}\ \ (s_d:\ \text{逐对评分差的标准差})`,
};

const out = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('fs_k3.json', JSON.stringify(out));
console.log('公式(三)', Object.keys(out).length);
