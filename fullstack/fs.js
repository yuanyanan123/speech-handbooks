// 《全栈音频链路手册》的全部公式。没有实验，没有读 json；每个公式都在正文里推导或解释。
const katex = require('katex'), fs = require('fs');

const D = {

// ══ 1 观测模型 ═════════════════════════════════════════════════
obs_td: String.raw`y_m[n]=\sum_{i}\big(h_{m,i}*s_i\big)[n]\;+\;\big(g_m*x\big)[n]\;+\;v_m[n],\qquad m=1,\dots,M`,
obs_fd: String.raw`\begin{aligned}
 \mathbf y(t,k)&=\mathbf a(k)\,S(t,k)+\mathbf g(k)\,X(t,k)+\mathbf v(t,k)\\[4pt]
 a_m(k)&=e^{-j2\pi f_k\tau_m},\qquad \tau_m=\frac{\mathbf p_m^{\top}\mathbf u}{c},\qquad f_k=\frac{k\,f_s}{N_{\text{fft}}}
 \end{aligned}`,
nframes: String.raw`T=1+\Big\lfloor\frac{N-N_w}{H}\Big\rfloor,\qquad F=\frac{N_{\text{fft}}}{2}+1`,
loop: String.raw`x[n]=\mathcal T\Big(\mathcal R\big(\mathcal A\big(\mathcal F(\,y[\le n],\,x[\le n]\,)\big)\big)\Big),\qquad
 y[n]\ \ni\ (g*x)[n]\ \ \text{（输出又回到输入）}`,

// ══ 2 阵列 ═════════════════════════════════════════════════════
das: String.raw`\mathbf w_{\text{DAS}}=\frac{\mathbf a}{M},\qquad
 \mathrm{WNG}(\mathbf w)=\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\mathbf w}
 \ \Longrightarrow\ \mathrm{WNG}_{\text{DAS}}=\frac{1}{1/M}=M\ \ (10\log_{10}M\ \mathrm{dB})`,
mvdr_deriv: String.raw`\begin{aligned}
 &\min_{\mathbf w}\ \mathbf w^{H}\boldsymbol\Phi_n\mathbf w\quad\text{s.t.}\quad\mathbf w^{H}\mathbf a=1\\[4pt]
 &\mathcal L=\mathbf w^{H}\boldsymbol\Phi_n\mathbf w+\lambda\,(\mathbf w^{H}\mathbf a-1)
 \ \Rightarrow\ \frac{\partial\mathcal L}{\partial\mathbf w^{H}}=\boldsymbol\Phi_n\mathbf w+\lambda\mathbf a=\mathbf 0
 \ \Rightarrow\ \mathbf w=-\lambda\,\boldsymbol\Phi_n^{-1}\mathbf a\\[4pt]
 &\mathbf a^{H}\mathbf w=1\ \Rightarrow\ \lambda=-\frac{1}{\mathbf a^{H}\boldsymbol\Phi_n^{-1}\mathbf a}
 \end{aligned}`,
mvdr_res: String.raw`\mathbf w_{\text{MVDR}}=\frac{\boldsymbol\Phi_n^{-1}\mathbf a}{\mathbf a^{H}\boldsymbol\Phi_n^{-1}\mathbf a},\qquad
 P_{\text{out}}=\mathbf w^{H}\boldsymbol\Phi_n\mathbf w=\frac{1}{\mathbf a^{H}\boldsymbol\Phi_n^{-1}\mathbf a}`,
diffuse: String.raw`\Gamma_{mn}(k)=\frac{\sin(2\pi f_k d_{mn}/c)}{2\pi f_k d_{mn}/c},\qquad
 \mathrm{DI}=\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\boldsymbol\Gamma\,\mathbf w},\qquad
 f_{\text{alias}}=\frac{c}{2d}`,
gcc: String.raw`R_{12}(\tau)=\sum_{k}\frac{Y_1(k)\,Y_2^{*}(k)}{\lvert Y_1(k)\,Y_2^{*}(k)\rvert}\,e^{\,j2\pi f_k\tau},\qquad
 \hat\tau=\arg\max_\tau R_{12}(\tau),\qquad \hat\theta=\arccos\frac{c\,\hat\tau}{d}`,
mask_mvdr: String.raw`\mathbf w(k)=\frac{\boldsymbol\Phi_{nn}^{-1}(k)\,\boldsymbol\Phi_{ss}(k)}{\mathrm{tr}\big(\boldsymbol\Phi_{nn}^{-1}(k)\,\boldsymbol\Phi_{ss}(k)\big)}\,\mathbf u,\qquad
 \boldsymbol\Phi_{vv}(k)=\frac{\sum_t m_v(t,k)\,\mathbf y\,\mathbf y^{H}}{\sum_t m_v(t,k)},\ \ v\in\{s,n\}`,
loading: String.raw`\mathbf w=\frac{(\boldsymbol\Phi_n+\epsilon\mathbf I)^{-1}\mathbf a}{\mathbf a^{H}(\boldsymbol\Phi_n+\epsilon\mathbf I)^{-1}\mathbf a}\quad
 \epsilon\to\infty:\ \text{DAS（WNG 最高）};\ \ \epsilon\to0:\ \text{MVDR（抑制最强）}`,

// ══ 3 回声消除 ═════════════════════════════════════════════════
nlms_deriv: String.raw`\begin{aligned}
 &\min_{\mathbf w'}\ \lVert\mathbf w'-\mathbf w\rVert^{2}\quad\text{s.t.}\quad\mathbf x^{\top}\mathbf w'=y
 \ \ (\text{一次更新后，当前样本的误差归零})\\[4pt]
 &\Longrightarrow\ \mathbf w'=\mathbf w+\mu\,\frac{e\;\mathbf x}{\mathbf x^{\top}\mathbf x+\delta},\qquad e=y-\mathbf x^{\top}\mathbf w
 \end{aligned}`,
nlms_perf: String.raw`\tau_{\text{收敛}}\approx\frac{L}{\mu\,(2-\mu)}\ \text{（样点）},\qquad
 M_{\text{稳态}}\approx\frac{\mu}{2-\mu}\,\sigma_v^{2}
 \ \Longrightarrow\ \tau\cdot M\approx\frac{L\,\sigma_v^{2}}{(2-\mu)^{2}}\ \ (\mu\ll1\ \text{时几乎不随 }\mu\text{ 变})`,
erle: String.raw`\mathrm{ERLE}=10\log_{10}\frac{\mathbb E\,[d^{2}]}{\mathbb E\,[(d-\hat d)^{2}]},\qquad
 \mathrm{ERLE}_{\max}=-10\log_{10}\!\big(1-\gamma_{xd}^{2}\big)`,
kalman: String.raw`\begin{aligned}
 &\text{预测：}\ \ \hat H^{-}=A\hat H,\quad P^{-}=A^{2}P+q\\[4pt]
 &\text{增益：}\ \ K=\frac{P^{-}X^{*}}{\lvert X\rvert^{2}P^{-}+\Phi_{vv}},\qquad E=Y-X\hat H^{-}\\[4pt]
 &\text{更新：}\ \ \hat H=\hat H^{-}+K\,E,\qquad P=(1-K X)\,P^{-}
 \end{aligned}`,
res_gain: String.raw`G(t,k)=\max\Big(1-\gamma\,\frac{\Phi_{\hat y}(t,k)}{\Phi_{e}(t,k)},\ G_{\min}\Big),\qquad
 \hat s(t,k)=G(t,k)\,E(t,k)`,

// ══ 4 单通道增强 ═══════════════════════════════════════════════
wiener_deriv: String.raw`\begin{aligned}
 &Y=S+N,\quad S\perp N:\qquad \mathbb E\lvert S-GY\rvert^{2}=(1-G)^{2}\Phi_s+G^{2}\Phi_n\\[4pt]
 &\frac{\partial}{\partial G}=0\ \Rightarrow\ -2(1-G)\Phi_s+2G\Phi_n=0
 \ \Rightarrow\ G_{\text{W}}=\frac{\Phi_s}{\Phi_s+\Phi_n}=\frac{\xi}{1+\xi},\qquad \xi=\frac{\Phi_s}{\Phi_n}
 \end{aligned}`,
ss: String.raw`\gamma=\frac{\lvert Y\rvert^{2}}{\Phi_n},\qquad
 G_{\text{SS}}=\sqrt{\max\Big(1-\frac1\gamma,\ \beta\Big)},\qquad
 G_{\text{W}}=\frac{\xi}{1+\xi}`,
dd: String.raw`\hat\xi(t,k)=\alpha\,\frac{\lvert\hat S(t-1,k)\rvert^{2}}{\Phi_n(t-1,k)}+(1-\alpha)\,\max\big(\gamma(t,k)-1,\ 0\big),\qquad \alpha\approx0.98`,
logmmse: String.raw`G_{\text{LSA}}=\frac{\xi}{1+\xi}\,\exp\!\Big(\frac12\int_{v}^{\infty}\frac{e^{-u}}{u}\,du\Big),\qquad
 v=\frac{\xi}{1+\xi}\,\gamma`,
noise_est: String.raw`\Phi_n(t,k)=\alpha_n\,\Phi_n(t-1,k)+(1-\alpha_n)\,\lvert Y(t,k)\rvert^{2},\qquad
 \alpha_n=\alpha+(1-\alpha)\,p(t,k)`,
sisdr: String.raw`\alpha=\frac{\hat s^{\top}s}{\lVert s\rVert^{2}},\qquad
 \mathrm{SI\text{-}SDR}=10\log_{10}\frac{\lVert\alpha s\rVert^{2}}{\lVert\hat s-\alpha s\rVert^{2}}`,

// ══ 5 其他前端模块 ═════════════════════════════════════════════
wpe: String.raw`\begin{aligned}
 &Y(t)=D(t)+\sum_{\tau=\Delta}^{\Delta+K-1}\mathbf g_\tau^{H}\,\mathbf y(t-\tau)\;\equiv\;D(t)+\mathbf g^{H}\tilde{\mathbf y}(t)\\[4pt]
 &\mathbf g=\Big(\sum_t\frac{\tilde{\mathbf y}\tilde{\mathbf y}^{H}}{\lambda_t}\Big)^{-1}\sum_t\frac{\tilde{\mathbf y}\,Y^{*}}{\lambda_t},\qquad
 \lambda_t=\mathbb E\lvert D(t)\rvert^{2}\ \ (\text{迭代估计})
 \end{aligned}`,
llr: String.raw`\Lambda(X)=\log\frac{p(X\mid H_1)}{p(X\mid H_0)}\ \overset{H_1}{\underset{H_0}{\gtrless}}\ \eta,\qquad
 P_{\text{FA}}=\Pr(\Lambda>\eta\mid H_0),\ \ P_{\text{miss}}=\Pr(\Lambda\le\eta\mid H_1)`,
cos: String.raw`\mathrm{score}(\mathbf e_1,\mathbf e_2)=\frac{\mathbf e_1^{\top}\mathbf e_2}{\lVert\mathbf e_1\rVert\,\lVert\mathbf e_2\rVert},\qquad
 \mathrm{EER}:\ P_{\text{FA}}(\eta^{\ast})=P_{\text{miss}}(\eta^{\ast})`,
comp: String.raw`y_{\mathrm{dB}}=\begin{cases}x_{\mathrm{dB}}, & x_{\mathrm{dB}}<T\\[2pt] T+\dfrac{x_{\mathrm{dB}}-T}{R}, & x_{\mathrm{dB}}\ge T\end{cases}
 \qquad g[n]=\alpha\,g[n-1]+(1-\alpha)\,g_{\text{目标}}[n]`,

// ══ 6 特征 ═════════════════════════════════════════════════════
feat: String.raw`\begin{aligned}
 &\tilde x[n]=x[n]-0.97\,x[n-1]\ \ (\text{预加重}),\qquad
 \mathrm{mel}(f)=2595\log_{10}\!\Big(1+\frac{f}{700}\Big)\\[4pt]
 &E_j(t)=\sum_{k}H_j(k)\,\lvert Y(t,k)\rvert^{2},\qquad
 \mathbf o(t)=\big[\log E_1(t),\dots,\log E_{80}(t)\big]^{\top}
 \end{aligned}`,
cmvn: String.raw`\log\lvert Y\rvert^{2}=\log\lvert S\rvert^{2}+\log\lvert H\rvert^{2}
 \ \Longrightarrow\ \hat o(t)=\frac{o(t)-\mu_o}{\sigma_o}\ \ (\text{均值里的 }\log\lvert H\rvert^{2}\text{ 被减掉})`,

// ══ 7 ASR 建模 ═════════════════════════════════════════════════
bayes: String.raw`\hat W=\arg\max_{W}P(W\mid X)=\arg\max_{W}\ \underbrace{P(X\mid W)}_{\text{声学模型}}\ \underbrace{P(W)}_{\text{语言模型}}`,
hmm: String.raw`\begin{aligned}
 \alpha_t(j)&=\Big[\sum_{i}\alpha_{t-1}(i)\,a_{ij}\Big]\,b_j(\mathbf o_t)\qquad(\text{前向：总概率})\\[4pt]
 \delta_t(j)&=\Big[\max_{i}\delta_{t-1}(i)\,a_{ij}\Big]\,b_j(\mathbf o_t)\qquad(\text{Viterbi：最优路径})\\[4pt]
 b_j(\mathbf o)&\propto\frac{P(j\mid\mathbf o)}{P(j)}\qquad(\text{混合系统：后验除先验})
 \end{aligned}`,
ctc: String.raw`\begin{aligned}
 P(\mathbf y\mid\mathbf x)&=\sum_{\boldsymbol\pi\in\mathcal B^{-1}(\mathbf y)}\ \prod_{t=1}^{T}P(\pi_t\mid\mathbf x)\\[4pt]
 \alpha_t(s)&=\big[\alpha_{t-1}(s)+\alpha_{t-1}(s-1)+\mathbb 1_{[\,l'_s\neq\varnothing,\ l'_s\neq l'_{s-2}\,]}\,\alpha_{t-1}(s-2)\big]\;P(l'_s\mid\mathbf x_t)
 \end{aligned}`,
rnnt: String.raw`\alpha(t,u)=\alpha(t-1,u)\,P_{\varnothing}(t-1,u)+\alpha(t,u-1)\,P_{y_u}(t,u-1),\qquad
 P(\mathbf y\mid\mathbf x)=\alpha(T,U)\,P_{\varnothing}(T,U)`,
aed: String.raw`\begin{aligned}
 P(\mathbf y\mid\mathbf x)&=\prod_{u}P(y_u\mid y_{<u},\mathbf x),\qquad
 c_u=\sum_t\alpha_{u,t}\,\mathbf h_t,\quad \alpha_{u,\cdot}=\mathrm{softmax}_t\big(\mathrm{score}(\mathbf q_u,\mathbf h_t)\big)\\[4pt]
 \mathcal L&=\lambda\,\mathcal L_{\text{CTC}}+(1-\lambda)\,\mathcal L_{\text{注意力}}
 \end{aligned}`,
wer: String.raw`\begin{aligned}
 D[i][j]&=\min\Big(D[i-1][j-1]+\mathbb 1_{[r_i\neq h_j]},\ \ D[i-1][j]+1,\ \ D[i][j-1]+1\Big)\\[4pt]
 \mathrm{WER}&=\frac{S+D+I}{N_{\text{ref}}}=\frac{D[N_{\text{ref}}][N_{\text{hyp}}]}{N_{\text{ref}}}
 \end{aligned}`,
nce: String.raw`\mathcal L_{\text{对比}}=-\log\frac{\exp\big(\mathrm{sim}(\mathbf c_t,\mathbf q_t)/\kappa\big)}{\sum_{\tilde{\mathbf q}\in\{\mathbf q_t\}\cup\mathcal Q_{\text{负}}}\exp\big(\mathrm{sim}(\mathbf c_t,\tilde{\mathbf q})/\kappa\big)}`,

// ══ 8 解码与语言模型 ═══════════════════════════════════════════
fusion: String.raw`\hat{\mathbf y}=\arg\max_{\mathbf y}\ \Big[\log P_{\text{AM}}(\mathbf y\mid\mathbf x)+\lambda\log P_{\text{LM}}(\mathbf y)-\mu\log P_{\text{ILM}}(\mathbf y)+\beta\,\lvert\mathbf y\rvert\Big]`,
kn: String.raw`\begin{aligned}
 P_{\text{KN}}(w\mid v)&=\frac{\max\big(c(vw)-d,\,0\big)}{c(v)}+\frac{d\;N_{1+}(v\,\bullet)}{c(v)}\;P_{\text{cont}}(w),\qquad
 P_{\text{cont}}(w)=\frac{N_{1+}(\bullet\,w)}{N_{1+}(\bullet\,\bullet)}\\[4pt]
 \mathrm{PPL}&=\exp\Big(-\frac1N\sum_{i=1}^{N}\log P(w_i\mid w_{<i})\Big)
 \end{aligned}`,

// ══ 10–13 TTS ══════════════════════════════════════════════════
mse: String.raw`\mathbb E\lVert x-f(c)\rVert^{2}=\underbrace{\mathbb E\lVert x-\mathbb E[x\mid c]\rVert^{2}}_{\text{与 }f\text{ 无关：一对多的方差}}+\mathbb E\lVert\mathbb E[x\mid c]-f(c)\rVert^{2}
 \ \Longrightarrow\ f^{\ast}(c)=\mathbb E[x\mid c]`,
cfm: String.raw`\begin{aligned}
 &x_t=(1-t)\,x_0+t\,x_1,\qquad x_0\sim\mathcal N(0,\mathbf I),\ \ x_1\sim p_{\text{数据}},\qquad \frac{dx_t}{dt}=x_1-x_0\\[4pt]
 &\mathcal L_{\text{CFM}}=\mathbb E_{t,x_0,x_1}\big\lVert\,v_\theta(x_t,t,c)-(x_1-x_0)\,\big\rVert^{2}
 \ \Longrightarrow\ v^{\ast}(x,t)=\mathbb E\big[\,x_1-x_0\ \big|\ x_t=x\,\big]\\[4pt]
 &\text{采样：}\ \frac{dx}{dt}=v_\theta(x,t,c),\qquad x_{t+\Delta}=x_t+\Delta\,v_\theta(x_t,t,c)\ \ (\text{Euler，NFE}=1/\Delta)
 \end{aligned}`,
cfg: String.raw`\tilde v=v_\theta(x,t,c)+s\,\big(v_\theta(x,t,c)-v_\theta(x,t,\varnothing)\big)\qquad(s=0\ \text{即无引导，每步多一次前向})`,
rvq: String.raw`\begin{aligned}
 &r_0=\mathbf z,\qquad q_k=\arg\min_{\mathbf e\in\mathcal C_k}\lVert r_{k-1}-\mathbf e\rVert,\qquad r_k=r_{k-1}-q_k,\qquad \hat{\mathbf z}=\sum_{k=1}^{K}q_k\\[4pt]
 &\text{码率}=K\cdot\log_2 N_{\text{码本}}\cdot f_{\text{帧}}\ \ \text{[bit/s]}
 \end{aligned}`,
gan: String.raw`\begin{aligned}
 \mathcal L_D&=\mathbb E\big[(D(x)-1)^{2}\big]+\mathbb E\big[D(\hat x)^{2}\big]\\[4pt]
 \mathcal L_G&=\mathbb E\big[(D(\hat x)-1)^{2}\big]+\lambda_{\text{fm}}\mathcal L_{\text{FM}}+\lambda_{\text{mel}}\,\lVert\mathrm{mel}(x)-\mathrm{mel}(\hat x)\rVert_1
 \end{aligned}`,
mos: String.raw`\bar m\ \pm\ t_{N-1,\,0.975}\,\frac{s}{\sqrt N},\qquad
 \mathrm{MCD}=\frac{10}{\ln10}\sqrt{2\sum_{d=1}^{13}\big(c_d-\hat c_d\big)^{2}}`,

// ══ 15 闭环与预算 ══════════════════════════════════════════════
budget: String.raw`\begin{aligned}
 T_{\text{帧}}&=\frac{N_w+N_{\text{lookahead}}}{f_s},\qquad
 T_{\text{首音}}=T_{\text{判停}}+T_{\text{ASR 尾}}+T_{\text{理解首字}}+T_{\text{TTS 首包}}+T_{\text{播放缓冲}}\\[4pt]
 T_{\text{打断}}&=T_{\text{hold}}+T_{\text{VAD}}+T_{\text{决策}}+T_{\text{播放缓冲}}+T_{\text{淡出}}
 \end{aligned}`,

// ══ TTS 补充 ═══════════════════════════════════════════════════
g2p: String.raw`\hat{\boldsymbol\phi}=\arg\max_{\boldsymbol\phi}P(\boldsymbol\phi\mid\mathbf g),\qquad
 \text{多音字：}\ P(\phi_i\mid g_i,\ \text{上下文})\ \ \text{而不是}\ \ P(\phi_i\mid g_i)`,
lenreg: String.raw`\mathbf H_{\text{帧}}=\mathrm{LR}\big(\mathbf H_{\text{音素}},\,\mathbf d\big),\qquad
 T_{\text{mel}}=\sum_{i=1}^{m}d_i,\qquad d_i\in\mathbb N\ \ (\text{第 }i\text{ 个音素占的帧数})`,
mas: String.raw`\hat{\mathbf d}=\arg\max_{\text{单调对齐 }\mathcal A}\ \sum_{t=1}^{T}\log\mathcal N\big(\mathbf x_t;\ \boldsymbol\mu_{\mathcal A(t)},\ \boldsymbol\sigma_{\mathcal A(t)}\big),\qquad
 \mathcal A(t)\le\mathcal A(t+1)\le\mathcal A(t)+1`,
refdelay: String.raw`\tau_{\text{ref}}=T_{\text{播放缓冲}}+T_{\text{DAC}}+\frac{d_{\text{喇叭→麦}}}{c}+T_{\text{ADC}}+T_{\text{采集缓冲}}`,
bits: String.raw`\text{码率}=K\cdot\log_2 N_{\text{码本}}\cdot f_{\text{帧}},\qquad
 \text{例：}\ K=8,\ N_{\text{码本}}=1024,\ f_{\text{帧}}=75\ \Rightarrow\ 8\times10\times75=6000\ \text{bit/s}`,
};

const out = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('fs_k.json', JSON.stringify(out));
console.log('公式', Object.keys(out).length);
