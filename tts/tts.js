// 《TTS 合成手册》全部公式。数字从各 demo_*.json 里取，改不了手。
const katex = require('katex'), fs = require('fs');
const G = JSON.parse(fs.readFileSync('demo_g2p.json', 'utf8'));
const S = JSON.parse(fs.readFileSync('demo_smooth.json', 'utf8'));
const ME = JSON.parse(fs.readFileSync('demo_mel.json', 'utf8'));
const AL = JSON.parse(fs.readFileSync('demo_align.json', 'utf8'));
const FL = JSON.parse(fs.readFileSync('demo_flow.json', 'utf8'));
const RQ = JSON.parse(fs.readFileSync('demo_rvq.json', 'utf8'));
const VO = JSON.parse(fs.readFileSync('demo_voc.json', 'utf8'));
const TP = JSON.parse(fs.readFileSync('demo_temp.json', 'utf8'));
const CK = JSON.parse(fs.readFileSync('demo_chunk.json', 'utf8'));
const CL = JSON.parse(fs.readFileSync('demo_clone.json', 'utf8'));
const r = (x, n) => Number(x).toFixed(n);
const tb = TP.temp_best, tsb = TP.temp_small_best;
const cb = TP.calib, clr = CL.pairs.raw, clc = CL.pairs.cmn;

const D = {
// ── 01 根本问题：两个方向不对称 ────────────────────────────
mirror: String.raw`\underbrace{\text{ASR：}\ \hat W=\arg\max_W p(W\mid X)}
 _{\textstyle \substack{\text{答案唯一，可以用}\\ \text{编辑距离直接打分}}}
 \qquad\qquad
 \underbrace{\text{TTS：}\ \hat X\sim p(X\mid W)}
 _{\textstyle \substack{\text{答案是一个分布，}\\ \text{"正确"有无穷多个}}}`,

// L2 的最优解是条件均值
l2mean: String.raw`\hat X^{\star}=\arg\min_{\hat X}\ \mathbb E_{X\sim p(\cdot\mid W)}
 \bigl\lVert X-\hat X\bigr\rVert^{2}
 \;=\;\underbrace{\mathbb E\bigl[X\mid W\bigr]}_{\textstyle \text{条件均值}}
 \qquad
 \underbrace{\text{它未必是任何一句真话}}
 _{\textstyle \text{两个合法读法的平均，两边都不像}}`,

// 方差分解
vardecomp: String.raw`\underbrace{\mathrm{Var}\bigl[X\mid W\bigr]}_{100\%}
 =\underbrace{\mathrm{Var}\bigl[\mathbb E[X\mid W,d]\bigr]}_{\textstyle 时长\ ${r(S.explain.dur, 1)}\%}
 +\underbrace{\mathrm{Var}\bigl[\mathbb E[X\mid W,d,f_0]\bigr]-\cdots}
 _{\textstyle 基频\ ${r(S.explain.f0, 1)}\%}
 +\underbrace{\cdots}_{\textstyle 其余\ ${r(S.explain.rest, 1)}\%}`,

// ── 05 多音字 ─────────────────────────────────────────────
polyent: String.raw`H\bigl(\text{读音}\mid\text{字}\bigr)
 =-\sum_{c}P(c)\sum_{y}P(y\mid c)\log_2 P(y\mid c)
 \;=\;${r(G.entropy_bits, 3)}\ \text{bit}
 \qquad
 \underbrace{\text{上下文必须补上这么多信息}}
 _{\textstyle \text{否则只能靠先验猜}}`,

// ── 15 梅尔 ───────────────────────────────────────────────
melwarp: String.raw`\begin{aligned}
 m&=2595\log_{10}\Bigl(1+\frac{f}{700}\Bigr)
 &&\text{频率轴按人耳弯曲}\\[6pt]
 M_{k}&=\sum_{n}H_{k}[n]\,\bigl\lvert X[n]\bigr\rvert
 &&\underbrace{${ME.cfg.nbin}\to${ME.cfg.nmel}\text{，满行秩，条件数 }${r(ME.fb.cond, 1)}}
 _{\textstyle \text{但不可逆}}
 \end{aligned}`,

melharm: String.raw`\begin{aligned}
 \Delta f_{\text{mel}}(f)&>f_0\ \Longrightarrow\ \text{谐波混在一起}
 &&f_0=120\,\text{Hz}\ \Rightarrow\ f^{\star}\approx${Math.round(ME.harm.f0_120)}\,\text{Hz}\\[8pt]
 \Delta f_{\text{mel}}(7\,\text{kHz})&=${Math.round(ME.harm.width_at_7k)}\ \text{Hz}
 &&\underbrace{\text{一个带里有 }${r(ME.harm.bins_at_7k, 1)}\ \text{根谐波}}
 _{\textstyle \text{这里的谐波结构根本不存在}}
 \end{aligned}`,

// Griffin-Lim 的不动点
gl: String.raw`\mathbf y^{(k+1)}=\mathcal G\Bigl(\lvert\mathbf A\rvert\odot
 \frac{\mathcal S\mathbf y^{(k)}}{\bigl\lvert\mathcal S\mathbf y^{(k)}\bigr\rvert}\Bigr)
 \qquad
 \underbrace{\mathcal S\mathcal G\ne\mathcal I}
 _{\textstyle \substack{\text{重叠相加之后再做 STFT 不等于原来那一组帧，}\\
 \text{所以"每帧幅度对"和"帧之间拼得上"一般不相容}}}`,

// ── 16 对齐 ───────────────────────────────────────────────
maspaths: String.raw`\#\{\text{单调对齐}\}=\binom{T-1}{I-1}
 \;\Big|_{\,T=${AL.cfg.T},\ I=${AL.cfg.I}}
 \approx10^{${r(AL.npaths_log10, 1)}}
 \qquad
 \underbrace{\text{DP 之后 }O(TI)}
 _{\textstyle \text{和 CTC 的前向算法是同一笔交易}}`,

masdp: String.raw`Q_{i,t}=\log\mathcal N\bigl(\mathbf x_t;\boldsymbol\mu_i,\boldsymbol\sigma_i\bigr)
 +\max\bigl\{\,\underbrace{Q_{i,t-1}}_{\text{留在这个音素}},\
 \underbrace{Q_{i-1,t-1}}_{\text{换到下一个}}\bigr\}`,

maslogdet: String.raw`\log\mathcal N=\underbrace{-\tfrac12\bigl\lVert(\mathbf x_t-\boldsymbol\mu_i)
 /\boldsymbol\sigma_i\bigr\rVert^{2}}_{\textstyle \text{距离项}}
 \underbrace{-\textstyle\sum_d\log\sigma_{i,d}}_{\textstyle \substack{\text{每帧一份的常数奖励，}\\
 \sigma\ \text{小的音素会多吃帧}}}
 -\tfrac{D}{2}\log 2\pi`,

// ── 13 扩散 / 流匹配 ──────────────────────────────────────
vpsde: String.raw`\mathrm d\mathbf x=-\tfrac12\beta(t)\mathbf x\,\mathrm dt
 +\sqrt{\beta(t)}\,\mathrm d\mathbf w
 \qquad\Longrightarrow\qquad
 \underbrace{\frac{\mathrm d\mathbf x}{\mathrm dt}
 =-\tfrac12\beta(t)\bigl[\mathbf x+\nabla_{\mathbf x}\log p_t(\mathbf x)\bigr]}
 _{\textstyle \text{概率流 ODE，去掉随机项后同分布}}`,

cfm: String.raw`\mathbf x_t=(1-t)\,\mathbf x_0+t\,\mathbf x_1
 \qquad
 \mathbf v^{\star}(\mathbf x,t)=\mathbb E\bigl[\mathbf x_1-\mathbf x_0
 \,\big|\,\mathbf x_t=\mathbf x\bigr]
 \qquad
 \underbrace{\mathcal L=\bigl\lVert \mathbf v_\theta-(\mathbf x_1-\mathbf x_0)\bigr\rVert^{2}}
 _{\textstyle \text{回归一个差，没有 score，没有噪声调度}}`,

curvature: String.raw`\mathbb E\bigl\lVert(\mathbf x_1-\mathbf x_0)-\mathbf v^{\star}
 (\mathbf x_t,t)\bigr\rVert^{2}
 =\begin{cases}
 ${r(FL.straight.fm_mean, 2)} & \text{OT 路径}\\[2pt]
 ${r(FL.straight.vp_mean, 2)} & \text{VP 扩散路径}
 \end{cases}
 \qquad
 \underbrace{\varepsilon_{\text{Euler}}\propto\kappa\,h^{2}}
 _{\textstyle \text{路径越弯，步子越要小}}`,

// ── 18 声码器 ─────────────────────────────────────────────
aliasfold: String.raw`\sigma(\cdot)\ \text{产生}\ kf_0
 \quad\Longrightarrow\quad
 f_{\text{折回}}=\bigl\lvert kf_0-n f_s\bigr\rvert
 \;\Big|_{\,f_0=3\,\text{kHz},\ k=7,\ f_s=22.05\,\text{kHz}}
 =\underbrace{1050\ \text{Hz}}
 _{\textstyle \text{落在语音最要命的频段}}`,

checker: String.raw`n_p=\Bigl\lceil\frac{k-p}{s}\Bigr\rceil,\quad p=0,\dots,s-1
 \qquad
 \underbrace{\frac{\max_p n_p}{\min_p n_p}=2\ \Rightarrow\ 3.01\ \text{dB}}
 _{\textstyle k\ \text{不能被}\ s\ \text{整除时的功率调制}}`,

phasel2: String.raw`\bigl\lVert\sin(\omega t)-\sin(\omega t+\varphi)\bigr\rVert^{2}
 =2\bigl(1-\cos\varphi\bigr)\lVert\cdot\rVert^{2}
 \qquad
 \underbrace{\varphi=\tfrac{\pi}{2}\Rightarrow+3.01\ \text{dB}}
 _{\textstyle \text{误差比信号还大}}
 \qquad
 \underbrace{\text{幅度谱距离}=0}
 _{\textstyle \text{而人耳听不出区别}}`,

// ── 19 tokenizer ─────────────────────────────────────────
rvq: String.raw`\mathbf r_0=\mathbf z,\qquad
 \mathbf r_{q}=\mathbf r_{q-1}-\mathbf c_{q}\bigl[k_q\bigr],\qquad
 k_q=\arg\min_{k}\bigl\lVert\mathbf r_{q-1}-\mathbf c_q[k]\bigr\rVert
 \qquad
 \underbrace{Q\cdot\log_2 K\ \text{bit}}
 _{\textstyle \text{而单码本要 }2^{Q\log_2K}\ \text{条目}}`,

tokrate: String.raw`\text{tok/s}=Q\cdot f_{\text{frame}}
 \qquad
 \underbrace{8\times86.1=${r(RQ.ctx.find(c => c.nq === 8 && c.rate > 80).tok_s, 0)}}
 _{\textstyle \text{10 秒话 }${RQ.ctx.find(c => c.nq === 8 && c.rate > 80).tok_10s}\ \text{个 token}}
 \qquad
 \underbrace{8\times25=200}
 _{\textstyle \text{同样 10 秒，只要 2000 个}}`,

// ── 25 评测 ───────────────────────────────────────────────
mospower: String.raw`n\ \gtrsim\ \frac{2\bigl(z_{1-\alpha/2}+z_{1-\beta}\bigr)^{2}\sigma^{2}}{\Delta^{2}}
 \qquad
 \underbrace{\sigma^{2}_{\text{独立}}=\sigma_{\text{噪}}^{2}+\sigma_{\text{人}}^{2}+\sigma_{\text{句}}^{2}}
 _{\textstyle \text{三份方差都要摊}}
 \;\gg\;
 \underbrace{\sigma^{2}_{\text{组内}}\approx\sigma_{\text{噪}}^{2}}
 _{\textstyle \text{同一个人同一句，另两份差掉了}}`,

// ── 20 克隆 ───────────────────────────────────────────────
clone: String.raw`p\bigl(\mathbf x\mid W,\ \mathbf s\bigr)
 \qquad
 \mathbf s=\underbrace{\text{一段参考音频}}_{\textstyle \substack{\text{它同时带着音色、}\\
 \text{口音、情绪、房间和设备}}}
 \qquad\Longrightarrow\qquad
 \underbrace{\text{解不开就一起学走}}
 _{\textstyle \text{"音色泄漏"的确切含义}}`,
// ── 03 评测：三种指标问的是三件事 ──────────────────────────
ttsmetric: String.raw`\underbrace{\text{MOS}=\tfrac1N\sum_i s_i}
 _{\textstyle \substack{\text{绝对分，跨实验不可比}}}
 \quad
 \underbrace{\text{CMOS}=\tfrac1N\sum_i (s_i^{A}-s_i^{B})}
 _{\textstyle \substack{\text{同一个听众直接比 A 和 B，}\\ \text{方差小得多}}}
 \quad
 \underbrace{\text{WER}_{\text{TTS}}}
 _{\textstyle \substack{\text{让 ASR 去听，测的是可懂度}\\ \text{不是自然度}}}`,

// ── 07 韵律：停顿时长不是常数 ──────────────────────────────
prosody: String.raw`d_{\text{pause}}=f(\underbrace{b}_{\textstyle \text{边界强度}},\
 \underbrace{\ell}_{\textstyle \text{前后短语长度}},\
 \underbrace{r}_{\textstyle \text{语速}})
 \qquad
 \underbrace{b\in\{0,1,2,3,4\}}
 _{\textstyle \substack{\text{词内 / 词间 / 短语 / 语调短语 / 句}\\
 \text{标错一级，听感上就是"断错句"}}}`,

// ── 08 建模单元：两头都要付代价 ────────────────────────────
unit: String.raw`\underbrace{|\mathcal V|}_{\textstyle \text{词表}}\ \times\
 \underbrace{L}_{\textstyle \text{序列长度}}\ \approx\ \text{常数}
 \qquad
 \underbrace{\text{字}\to\text{音素}\to\text{状态}}
 _{\textstyle \substack{\text{词表越小，序列越长，}\\ \text{自回归步数越多}}}
 \qquad
 \underbrace{\text{OOV}}
 _{\textstyle \text{只有最细的那一端没有}}`,

// ── 10 单元选择：两项代价的加权和 ──────────────────────────
unitsel: String.raw`\hat u_{1:n}=\arg\min_{u_{1:n}}\sum_{i}
 \underbrace{C_{t}(u_i,\ \text{目标}_i)}_{\textstyle \text{像不像要的那个音}}
 +\ \lambda\sum_{i}
 \underbrace{C_{c}(u_{i-1},u_i)}_{\textstyle \text{接缝顺不顺}}
 \qquad
 \underbrace{\text{Viterbi 求解}}
 _{\textstyle \text{和 ASR 解码是同一个动态规划}}`,

// ── 13 VITS：把三件事塞进一个目标 ──────────────────────────
vits: String.raw`\log p(x\mid c)\ \ge\
 \underbrace{\operatorname{E}_{q(z\mid x)}\!\left[\log p(x\mid z)\right]}
 _{\textstyle \text{重建：声码器那一半}}
 -\underbrace{\mathrm{KL}\!\left(q(z\mid x)\,\|\,p(z\mid c,\hat A)\right)}
 _{\textstyle \substack{\text{先验这一侧是流，}\\ \hat A\ \text{是 MAS 搜出来的对齐}}}
 \ +\ \underbrace{\mathcal L_{\text{adv}}}_{\textstyle \text{补 L2 丢掉的细节}}`,

// ── 15 LLM-TTS：步数是怎么算出来的 ─────────────────────────
delay: String.raw`N_{\text{step}}=\underbrace{T_{\text{tok}}}_{\textstyle \text{帧数}}
 \times\underbrace{Q}_{\textstyle \text{量化级数}}
 \ \xrightarrow{\ \text{delay pattern}\ }\
 N_{\text{step}}=T_{\text{tok}}+Q-1
 \qquad
 \underbrace{\text{错位摆放，一次前向出一整帧}}
 _{\textstyle \text{步数从乘法变成加法}}`,

// ── 20 相似度：比的是分布重叠，不是绝对差 ──────────────────
simproto: String.raw`\underbrace{\text{同一段参考去比}}_{\textstyle \text{EER}=
 ${r(clr.eer_naive, 2)}\%}
 \qquad\text{vs}\qquad
 \underbrace{\text{换一场录音再比}}_{\textstyle \text{EER}=${r(clr.eer_strict, 2)}\%}
 \qquad
 \underbrace{\text{差 }${r(clr.eer_strict / clr.eer_naive, 0)}\text{ 倍}}
 _{\textstyle \substack{\text{房间是两边共有的，}\\ \text{它顶上去的那部分全算进了相似度}}}`,

// ── 21 温度：只是把 logits 除一下 ──────────────────────────
temp: String.raw`p_T(k)=\frac{\exp(z_k/T)}{\sum_j \exp(z_j/T)}
 \qquad
 \underbrace{T\to 0}_{\textstyle \substack{\text{贪心，复读率 }
 ${r(TP.temp[0].rep, 0)}\%}}
 \qquad
 \underbrace{T=1}_{\textstyle \substack{\text{照模型自己的分布采}}}
 \qquad
 \underbrace{T\to\infty}_{\textstyle \text{均匀，全是错音}}`,

// ── 21 校准：最优温度是校准问题，不是口味问题 ──────────────
calib: String.raw`\begin{aligned}
 &\underbrace{\operatorname{E}\!\left[\max_k p_k\right]}
 _{\textstyle \text{模型说自己有多确定}}
 \qquad\text{vs}\qquad
 \underbrace{\operatorname{E}\!\left[p^{\star}(\arg\max_k p_k)\right]}
 _{\textstyle \text{它指的那个 token 真实概率}}\\[10pt]
 &\underbrace{${r(cb.big.conf, 3)}\ \text{vs}\ ${r(cb.big.true_p_of_argmax, 3)}}
 _{\textstyle \text{数据充足：几乎不差}}
 \qquad\qquad
 \underbrace{${r(cb.small.conf, 3)}\ \text{vs}\ ${r(cb.small.true_p_of_argmax, 3)}}
 _{\textstyle \text{数据饥饿：过自信近一倍}}
 \end{aligned}`,

// ── 21 重复惩罚 ────────────────────────────────────────────
reppen: String.raw`\tilde p(k)\propto p(k)\big/ \rho^{\,n_k}
 \qquad
 \underbrace{n_k}_{\textstyle \text{这个 token 已经出现几次}}
 \qquad
 \underbrace{\text{TTS 的麻烦}}
 _{\textstyle \substack{\text{元音本来就要持续好几帧，}\\
 \text{扣重复等于扣时长}}}`,

// ── 22 感受野：流式要等的那一段是结构给的 ──────────────────
rf: String.raw`T_{\text{首包}}=
 \underbrace{C}_{\textstyle \text{块帧数}}\cdot h
 +\underbrace{R}_{\textstyle \text{右感受野}}\cdot h
 +T_{\text{compute}}
 \qquad
 \underbrace{R=${r(CK.rf.right_frames, 1)}\ \text{帧}=
 ${r(CK.rf.right_ms, 0)}\ \text{ms}}
 _{\textstyle \substack{\text{扰动一帧梅尔实测出来的，}\\ \text{不是推的}}}`,

// ── 22 块越小，摊销开销越大 ────────────────────────────────
chunkcost: String.raw`\eta=\frac{L+R}{C}
 \qquad
 \underbrace{C=16\Rightarrow \eta=${r(CK.chunk[2].overhead, 0)}\%}
 _{\textstyle \text{首包 }${r(CK.chunk[2].lat_ms, 0)}\text{ ms}}
 \qquad
 \underbrace{C=4\Rightarrow \eta=${r(CK.chunk[0].overhead, 0)}\%}
 _{\textstyle \text{首包 }${r(CK.chunk[0].lat_ms, 0)}\text{ ms}}
 \qquad
 \underbrace{\text{延迟是拿算力买的}}_{\textstyle \text{而且越买越贵}}`,
};

const I = {
  poly_tok: String.raw`${r(G.token_level.poly_pct, 1)}\%`,
  Hbits: String.raw`${r(G.entropy_bits, 3)}\ \text{bit}`,
  dur_pct: String.raw`${r(S.explain.dur, 1)}\%`,
  fcross: String.raw`${ME.harm.f0_120}\ \text{Hz}`,
  nfe: String.raw`\mathrm{NFE}`,
  xt: String.raw`\mathbf x_t`,
  v: String.raw`\mathbf v_\theta`,
  Q: String.raw`Q`,
  mu_i: String.raw`\boldsymbol\mu_i`,
  sig_i: String.raw`\boldsymbol\sigma_i`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('tts.json', JSON.stringify(out));
fs.writeFileSync('tts_inline.json', JSON.stringify(oi));
console.log('公式', Object.keys(out).length, '行内', Object.keys(oi).length);
