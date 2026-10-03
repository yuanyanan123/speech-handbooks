// 《全栈音频链路手册》方法演进链的公式（第二批）。没有实验，不读 json。
const katex = require('katex'), fs = require('fs');

const D = {

// ══ 2 阵列 ═════════════════════════════════════════════════════
lcmv: String.raw`\begin{aligned}
 &\min_{\mathbf w}\ \mathbf w^{H}\boldsymbol\Phi\,\mathbf w\quad\text{s.t.}\quad\mathbf C^{H}\mathbf w=\mathbf f,\qquad \mathbf C=[\mathbf a,\ \mathbf a_{\text{干扰}1},\dots],\ \ \mathbf f=[1,0,\dots]^{\top}\\[4pt]
 &\Longrightarrow\ \mathbf w_{\text{LCMV}}=\boldsymbol\Phi^{-1}\mathbf C\big(\mathbf C^{H}\boldsymbol\Phi^{-1}\mathbf C\big)^{-1}\mathbf f
 \end{aligned}`,
gsc: String.raw`\begin{aligned}
 z&=\underbrace{\mathbf w_q^{H}\mathbf y}_{\text{固定波束}}-\mathbf w_a^{H}\underbrace{\mathbf B^{H}\mathbf y}_{\text{噪声参考}},\qquad \mathbf B^{H}\mathbf a=\mathbf 0\ \ (\text{阻塞矩阵：挡住目标})\\[4pt]
 \mathbf w_a&\leftarrow\mathbf w_a+\mu\,\frac{(\mathbf B^{H}\mathbf y)\,z^{*}}{\lVert\mathbf B^{H}\mathbf y\rVert^{2}+\delta}\ \ (\text{NLMS 更新})
 \end{aligned}`,
srp: String.raw`P_{\text{SRP}}(\theta)=\sum_{i<j}R_{ij}\big(\tau_{ij}(\theta)\big),\qquad
 \tau_{ij}(\theta)=\frac{(\mathbf p_i-\mathbf p_j)^{\top}\mathbf u(\theta)}{c},\qquad \hat\theta=\arg\max_\theta P_{\text{SRP}}(\theta)`,
music: String.raw`\mathbf R=\mathbf E_s\boldsymbol\Lambda_s\mathbf E_s^{H}+\mathbf E_n\boldsymbol\Lambda_n\mathbf E_n^{H},\qquad
 P_{\text{MUSIC}}(\theta)=\frac{1}{\mathbf a^{H}(\theta)\,\mathbf E_n\mathbf E_n^{H}\,\mathbf a(\theta)}`,
gev: String.raw`\mathbf w_{\text{GEV}}=\arg\max_{\mathbf w}\frac{\mathbf w^{H}\boldsymbol\Phi_{ss}\mathbf w}{\mathbf w^{H}\boldsymbol\Phi_{nn}\mathbf w}
 \ \Longrightarrow\ \boldsymbol\Phi_{ss}\,\mathbf w=\lambda_{\max}\,\boldsymbol\Phi_{nn}\,\mathbf w`,
ipd: String.raw`\mathrm{IPD}_{ij}(t,k)=\angle\frac{Y_i(t,k)}{Y_j(t,k)},\qquad
 \mathrm{IPD}^{\text{理论}}_{ij}(k)=-2\pi f_k\,\tau_{ij}(\theta)\ \ (\text{平面波、方向 }\theta)`,

// ══ 3 回声消除 ═════════════════════════════════════════════════
ap: String.raw`\mathbf w\leftarrow\mathbf w+\mu\,\mathbf X\big(\mathbf X^{\top}\mathbf X+\delta\mathbf I\big)^{-1}\mathbf e,\qquad
 \mathbf X=[\mathbf x_n,\dots,\mathbf x_{n-P+1}]\in\mathbb R^{L\times P},\quad \mathbf e=\mathbf y_P-\mathbf X^{\top}\mathbf w`,
rls: String.raw`\begin{aligned}
 \mathbf k&=\frac{\mathbf P\mathbf x}{\lambda+\mathbf x^{\top}\mathbf P\mathbf x},\qquad e=y-\mathbf x^{\top}\mathbf w\\[4pt]
 \mathbf w&\leftarrow\mathbf w+\mathbf k\,e,\qquad \mathbf P\leftarrow\frac{1}{\lambda}\big(\mathbf P-\mathbf k\,\mathbf x^{\top}\mathbf P\big)
 \end{aligned}`,
fdaf: String.raw`\hat Y(t,k)=\sum_{p=0}^{P-1}W_p(t,k)\,X(t-p,k),\qquad
 W_p(t{+}1,k)=W_p(t,k)+\mu\,\frac{X^{*}(t-p,k)\,E(t,k)}{P_x(t,k)+\delta}`,
ncc: String.raw`\rho=\sqrt{\frac{\mathbf r_{xy}^{\top}\,\mathbf R_{xx}^{-1}\,\mathbf r_{xy}}{\sigma_y^{2}}},\qquad
 \rho\ \text{接近 1：只有回声；}\ \rho\ \text{明显偏低：近端在说话}`,
volterra: String.raw`d[n]=\sum_{p\in\{1,3,5\}}\sum_{k=0}^{K-1}c_{p,k}\,x^{p}[n-k],\qquad
 \hat d=\sum_{p}\mathbf h_p^{\top}\mathbf x_p[n],\quad \mathbf x_p[n]=\big[x^{p}[n],\dots,x^{p}[n-K+1]\big]^{\top}`,
rescoh: String.raw`\hat\Phi_r(t,k)=\lvert\rho_{e\hat y}(t,k)\rvert^{2}\,\Phi_e(t,k),\qquad
 \rho_{e\hat y}=\frac{S_{e\hat y}}{\sqrt{S_{ee}\,S_{\hat y\hat y}}}\ \ (\text{残差里与回声估计线性相关的那一部分})`,
nlaec: String.raw`\mathcal L=\sum_{t,f}\Big(\lvert\hat S\rvert^{c}-\lvert S\rvert^{c}\Big)^{2}+\mu\sum_{t,f\in\text{单讲回声段}}\lvert\hat S\rvert^{2},\qquad c\approx0.3`,

// ══ 4 单通道增强 ═══════════════════════════════════════════════
ss_gen: String.raw`\lvert\hat S\rvert^{2}=\max\big(\lvert Y\rvert^{2}-\alpha\,\Phi_n,\ \beta\,\Phi_n\big),\qquad \alpha\ge1\ (\text{过减}),\ \ 0\le\beta\ll1\ (\text{谱下限})`,
mmse_post: String.raw`\begin{aligned}
 &S\sim\mathcal{CN}(0,\Phi_s),\ \ N\sim\mathcal{CN}(0,\Phi_n),\ \ Y=S+N\\[4pt]
 &S\mid Y\ \sim\ \mathcal{CN}\big(G_{\text{W}}\,Y,\ \ G_{\text{W}}\,\Phi_n\big),\qquad G_{\text{W}}=\frac{\xi}{1+\xi}\ \ (\text{后验：高斯，均值就是维纳输出})
 \end{aligned}`,
mmse_stsa: String.raw`\begin{aligned}
 \hat A&=\mathbb E\big[\lvert S\rvert\ \big|\ Y\big]=G_{\text{STSA}}\,\lvert Y\rvert\qquad(\lvert S\rvert\mid Y\ \text{服从莱斯分布})\\[4pt]
 G_{\text{STSA}}&=\frac{\sqrt\pi}{2}\,\frac{\sqrt v}{\gamma}\,e^{-v/2}\Big[(1+v)\,I_0\!\big(\tfrac v2\big)+v\,I_1\!\big(\tfrac v2\big)\Big],\qquad v=\frac{\xi}{1+\xi}\gamma
 \end{aligned}`,
lsa_deriv: String.raw`\hat A_{\text{LSA}}=\exp\!\big(\mathbb E[\ln\lvert S\rvert\mid Y]\big),\qquad
 \mathbb E[\ln\lvert S\rvert\mid Y]=\ln\big(G_{\text{W}}\lvert Y\rvert\big)+\frac12E_1(v),\qquad E_1(v)=\int_{v}^{\infty}\frac{e^{-u}}{u}\,du`,
spp: String.raw`\begin{aligned}
 \Lambda&=\frac{p(Y\mid H_1)}{p(Y\mid H_0)}=\frac{1}{1+\xi_{H_1}}\exp\!\Big(\frac{\xi_{H_1}}{1+\xi_{H_1}}\,\gamma\Big)\\[4pt]
 p(H_1\mid Y)&=\frac{q\,\Lambda}{q\,\Lambda+(1-q)},\qquad q=\Pr(H_1)\ \ (\text{先验：这个时频点有语音})
 \end{aligned}`,
omlsa: String.raw`G_{\text{OM-LSA}}(t,k)=G_{\text{LSA}}(t,k)^{\,p(t,k)}\cdot G_{\min}^{\,1-p(t,k)}`,
minstat: String.raw`\bar P(t,k)=\alpha_s\,\bar P(t-1,k)+(1-\alpha_s)\,\lvert Y(t,k)\rvert^{2},\qquad
 \hat\Phi_n(t,k)=B_{\min}\cdot\min_{t-D<\tau\le t}\bar P(\tau,k)`,
subspace: String.raw`\begin{aligned}
 &\mathbf R_y=\mathbf R_s+\sigma_n^{2}\mathbf I=\mathbf U\boldsymbol\Lambda_y\mathbf U^{H},\qquad \boldsymbol\Lambda_y=\boldsymbol\Lambda_s+\sigma_n^{2}\mathbf I\\[4pt]
 &\hat{\mathbf s}=\mathbf U\,\boldsymbol\Lambda_s\big(\boldsymbol\Lambda_s+\mu\,\sigma_n^{2}\mathbf I\big)^{-1}\mathbf U^{H}\,\mathbf y\qquad(\mu=1:\ \text{维纳；}\ \mu>1:\ \text{更狠，失真更大})
 \end{aligned}`,
masks: String.raw`\begin{aligned}
 \mathrm{IBM}&=\mathbb 1\big[\lvert S\rvert^{2}>\theta\lvert N\rvert^{2}\big],\qquad
 \mathrm{IRM}=\Big(\frac{\lvert S\rvert^{2}}{\lvert S\rvert^{2}+\lvert N\rvert^{2}}\Big)^{\beta}\\[4pt]
 \mathrm{PSM}&=\frac{\lvert S\rvert}{\lvert Y\rvert}\cos(\angle S-\angle Y),\qquad
 \mathrm{cIRM}=\frac{S}{Y}=\frac{Y_rS_r+Y_iS_i}{Y_r^{2}+Y_i^{2}}+j\,\frac{Y_rS_i-Y_iS_r}{Y_r^{2}+Y_i^{2}}
 \end{aligned}`,
tasnet: String.raw`\mathbf w=\mathrm{ReLU}\big(\mathrm{Conv1d}(\mathbf y)\big),\qquad \mathbf m=\sigma\big(\mathrm{TCN}(\mathbf w)\big),\qquad
 \hat s=\mathrm{ConvTranspose1d}\big(\mathbf w\odot\mathbf m\big)\ \ (\text{编码器、掩蔽、解码器都是可学习的})`,
deepfilter: String.raw`\hat S(t,k)=\sum_{i=0}^{N-1}c_i(t,k)\,Y(t-i+l,\,k),\qquad
 N=1:\ \text{退化为掩蔽 }\hat S=c_0Y;\quad N>1:\ \text{跨多帧的复数 FIR 滤波}`,
sgmse: String.raw`\begin{aligned}
 &\text{正向：}\ d\mathbf x_t=\gamma(\mathbf y-\mathbf x_t)\,dt+g(t)\,d\mathbf w,\qquad \mathbf x_0=\mathbf s\ (\text{干净}),\ \ \mathbf x_T\approx\mathbf y+\text{噪声}\\[4pt]
 &\text{训练：}\ \mathcal L=\mathbb E\Big\lVert\mathbf s_\theta(\mathbf x_t,\mathbf y,t)+\frac{\mathbf x_t-\boldsymbol\mu_t}{\sigma_t^{2}}\Big\rVert^{2}\\[4pt]
 &\text{逆向：}\ d\mathbf x=\Big[\gamma(\mathbf y-\mathbf x)-g(t)^{2}\,\mathbf s_\theta(\mathbf x,\mathbf y,t)\Big]dt+g(t)\,d\bar{\mathbf w}
 \end{aligned}`,

// ══ 5 去混响 / VAD / 唤醒 / 声纹 ═══════════════════════════════
mint: String.raw`\mathbf H\,\mathbf g=\mathbf e_{\text{直达}}\qquad(\mathbf H:\ \text{冲激响应的卷积矩阵；多通道时可精确求解，但对冲激响应估计误差极敏感})`,
late: String.raw`\Phi_{\text{late}}(t,k)=e^{-2\delta\,T_l}\,\Phi_y(t-N_l,k),\qquad \delta=\frac{3\ln10}{T_{60}},\qquad
 \lvert\hat S\rvert^{2}=\max\big(\lvert Y\rvert^{2}-\Phi_{\text{late}},\ \beta\lvert Y\rvert^{2}\big)`,
sohn: String.raw`\Lambda_k=\frac{1}{1+\xi_k}\exp\!\Big(\frac{\xi_k}{1+\xi_k}\gamma_k\Big),\qquad
 \frac1K\sum_{k=1}^{K}\log\Lambda_k\ \overset{\text{语音}}{\underset{\text{非语音}}{\gtrless}}\ \eta`,
kws: String.raw`p'_{ij}=\frac{1}{j-h_s+1}\sum_{k=h_s}^{j}p_{ik},\qquad
 c_j=\Big(\prod_{i=1}^{n-1}\ \max_{h_{\max}\le k\le j}p'_{ik}\Big)^{\frac{1}{\,n-1\,}}\ \ (\text{平滑后取各关键词标签的最大后验，几何平均})`,
gmmubm: String.raw`s(X)=\frac1T\sum_{t=1}^{T}\Big[\log p(\mathbf o_t\mid\lambda_{\text{说话人}})-\log p(\mathbf o_t\mid\lambda_{\text{UBM}})\Big],\qquad
 \mathbf M=\mathbf m+\mathbf T\mathbf w\ \ (\text{i-vector：总变化空间})`,
aam: String.raw`\mathcal L_{\text{AAM}}=-\log\frac{e^{\,s\cos(\theta_y+m)}}{e^{\,s\cos(\theta_y+m)}+\sum_{j\ne y}e^{\,s\cos\theta_j}},\qquad
 \cos\theta_j=\frac{\mathbf w_j^{\top}\mathbf e}{\lVert\mathbf w_j\rVert\,\lVert\mathbf e\rVert}`,

// ══ 6 特征 ═════════════════════════════════════════════════════
lpc: String.raw`\hat x[n]=\sum_{k=1}^{p}a_k\,x[n-k],\qquad \mathbf R\,\mathbf a=\mathbf r\ \ (\text{Yule–Walker}),\qquad H(z)=\frac{G}{1-\sum_{k=1}^{p}a_kz^{-k}}`,
cep: String.raw`c[n]=\mathrm{IDFT}\big(\log\lvert X(k)\rvert\big),\qquad
 c_i=\sum_{j=1}^{J}\log E_j\,\cos\!\Big(\frac{\pi i}{J}\big(j-\tfrac12\big)\Big)\ \ (\text{MFCC：对数梅尔的 DCT})`,
delta: String.raw`\Delta c_t=\frac{\sum_{n=1}^{N}n\,\big(c_{t+n}-c_{t-n}\big)}{2\sum_{n=1}^{N}n^{2}}`,
pcen: String.raw`\mathrm{PCEN}(t,f)=\Big(\frac{E(t,f)}{\big(\epsilon+M(t,f)\big)^{\alpha}}+\delta\Big)^{r}-\delta^{r},\qquad M(t,f)=(1-s)\,M(t-1,f)+s\,E(t,f)`,
sinc: String.raw`g[n;f_1,f_2]=\Big(2f_2\,\mathrm{sinc}(2\pi f_2n)-2f_1\,\mathrm{sinc}(2\pi f_1n)\Big)\,w[n]\qquad(\text{只学两个截止频率})`,

// ══ 7 ASR 建模 ═════════════════════════════════════════════════
gmm: String.raw`b_j(\mathbf o)=\sum_{m=1}^{M}c_{jm}\,\mathcal N(\mathbf o;\boldsymbol\mu_{jm},\boldsymbol\Sigma_{jm}),\qquad
 \boldsymbol\mu_{jm}=\frac{\sum_t\gamma_t(j,m)\,\mathbf o_t}{\sum_t\gamma_t(j,m)}\ \ (\text{EM 的 M 步})`,
mmi: String.raw`\mathcal F_{\text{MMI}}=\sum_{r}\log\frac{p(\mathbf O_r\mid W_r)^{\kappa}\,P(W_r)}{\sum_{W}p(\mathbf O_r\mid W)^{\kappa}\,P(W)},\qquad
 \mathcal F_{\text{sMBR}}=\sum_r\sum_{W}P(W\mid\mathbf O_r)\,A(W,W_r)`,
attn: String.raw`\mathrm{Attn}(\mathbf Q,\mathbf K,\mathbf V)=\mathrm{softmax}\!\Big(\frac{\mathbf Q\mathbf K^{\top}}{\sqrt{d_k}}\Big)\mathbf V,\qquad
 \text{复杂度}\ O(T^{2}d)\ \ (T:\ \text{帧数})`,
hubert: String.raw`\mathcal L_{\text{HuBERT}}=-\sum_{t\in\mathcal M}\log p\big(z_t\mid\tilde{\mathbf X},\,t\big),\qquad z_t:\ \text{离线聚类（K-means）给出的帧级伪标签}`,
llmasr: String.raw`\mathbf h=\mathrm{Adapter}\big(\mathrm{Enc}(\mathbf X)\big)\in\mathbb R^{T''\times d_{\text{LLM}}},\qquad
 \mathcal L=-\sum_u\log P_{\text{LLM}}\big(y_u\mid[\mathbf h;\ \text{提示}],\ y_{<u}\big)`,

// ══ 8 解码与语言模型 ═══════════════════════════════════════════
rnnlm: String.raw`P(w_t\mid w_{<t})=\mathrm{softmax}\big(\mathbf W\,\mathbf h_t\big),\qquad \mathbf h_t=f(\mathbf h_{t-1},\,\mathbf e_{w_{t-1}})\ \ (\text{或自注意力})`,
ilme: String.raw`\log P_{\text{ILM}}(\mathbf y)\approx\sum_u\log P\big(y_u\mid y_{<u},\ \mathbf h=\mathbf 0\big)\qquad(\text{把声学上下文抹掉，只留解码器自己的语言偏好})`,
mbr: String.raw`\hat W=\arg\min_{W'}\ \sum_{W\in\mathcal N}P(W\mid\mathbf X)\,L(W,W'),\qquad L=\text{编辑距离}\ \ (\text{MAP 是 }L=0/1\text{ 的特例})`,
prefix: String.raw`\begin{aligned}
 p_b(\ell,t)&=\big(p_b(\ell,t-1)+p_{nb}(\ell,t-1)\big)\,y_t(\varnothing)\\[4pt]
 p_{nb}(\ell{+}c,t)&=\big(p_b(\ell,t-1)+[\,c\ne\ell_{\text{末}}\,]\,p_{nb}(\ell,t-1)\big)\,y_t(c)
 \end{aligned}`,
wfstc: String.raw`(A\circ B)(x,z)=\bigoplus_{y}A(x,y)\otimes B(y,z),\qquad
 \mathrm{HCLG}=\min\big(\det(H\circ C\circ L\circ G)\big),\qquad
 \gamma(a)=\frac{\alpha(\mathrm{src}\,a)\,w(a)\,\beta(\mathrm{dst}\,a)}{\beta(\text{起点})}\ \ (\text{格上弧的后验})`,

// ══ 10–12 合成 ═════════════════════════════════════════════════
jointg2p: String.raw`P(\mathbf g,\boldsymbol\phi)=\prod_i P\big(q_i\mid q_{i-n+1},\dots,q_{i-1}\big),\qquad q_i=(g_i{:}\phi_i)\ \ (\text{字形–音素联合单元})`,
unitsel: String.raw`\hat{\mathbf u}=\arg\min_{u_1,\dots,u_N}\ \sum_{i=1}^{N}C_{t}(u_i,t_i)+\sum_{i=2}^{N}C_{c}(u_{i-1},u_i)\qquad(\text{目标代价 + 拼接代价；Viterbi 求解})`,
mlpg: String.raw`\mathbf o=\mathbf W\mathbf c,\qquad \hat{\mathbf c}=\arg\max_{\mathbf c}\mathcal N(\mathbf W\mathbf c;\boldsymbol\mu,\boldsymbol\Sigma)=\big(\mathbf W^{\top}\boldsymbol\Sigma^{-1}\mathbf W\big)^{-1}\mathbf W^{\top}\boldsymbol\Sigma^{-1}\boldsymbol\mu`,
elbo: String.raw`\log p(x\mid c)\ \ge\ \mathbb E_{q(z\mid x,c)}\big[\log p(x\mid z,c)\big]-\mathrm{KL}\big(q(z\mid x,c)\,\Vert\,p(z\mid c)\big)`,
ddpm: String.raw`x_t=\sqrt{\bar\alpha_t}\,x_0+\sqrt{1-\bar\alpha_t}\,\boldsymbol\epsilon,\qquad
 \mathcal L=\mathbb E\,\big\lVert\boldsymbol\epsilon-\boldsymbol\epsilon_\theta(x_t,t,c)\big\rVert^{2},\qquad \boldsymbol\epsilon_\theta=-\sigma_t\,\mathbf s_\theta`,
artts: String.raw`\mathcal L=-\sum_{t=1}^{T}\log p\big(z_t\mid z_{<t},\ c\big),\qquad z_t:\ \text{离散语音 token（来自 RVQ 的第 1 级或多级）}`,
gl: String.raw`\mathbf X^{(i+1)}=\mathcal P_{\text{一致}}\Big(\lvert\mathbf X\rvert\,e^{\,j\angle\mathbf X^{(i)}}\Big),\qquad \mathcal P_{\text{一致}}(\mathbf Z)=\mathrm{STFT}\big(\mathrm{ISTFT}(\mathbf Z)\big)`,
wavenet: String.raw`p(\mathbf x)=\prod_{t}p(x_t\mid x_{<t}),\qquad f_\mu(x)=\mathrm{sign}(x)\frac{\ln(1+\mu\lvert x\rvert)}{\ln(1+\mu)},\ \ \mu=255,\qquad R=1+\sum_{l}(k-1)\,d_l`,
lpcnet: String.raw`x_t=\underbrace{\sum_{k=1}^{p}a_k\,x_{t-k}}_{\text{LPC 预测（便宜）}}+e_t,\qquad \text{网络只预测激励 }e_t\text{ 的分布（贵的那部分变小）}`,
nflow: String.raw`\log p_X(x)=\log p_Z\big(f(x)\big)+\log\Big\lvert\det\frac{\partial f}{\partial x}\Big\rvert,\qquad z\sim\mathcal N(0,\mathbf I)\ \ (\text{可逆变换：采样即把 }z\text{ 反推回 }x)`,
};

const out = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('fs_k2.json', JSON.stringify(out));
console.log('公式(二)', Object.keys(out).length);
