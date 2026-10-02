// 《声纹与唤醒手册》全部公式。数字从各 demo_*.json 里取，不手抄。
// 注意：_head.html 只内嵌了 Main / Math / Size / Caligraphic 四族字体，
// 所以这里不能用 \mathbb、\triangleq、\mathsf、\mathfrak 等要 AMS/SansSerif 的记号。
const katex = require('katex'), fs = require('fs');
const SC = JSON.parse(fs.readFileSync('demo_score.json', 'utf8'));
const MT = JSON.parse(fs.readFileSync('demo_metric.json', 'utf8'));
const CD = JSON.parse(fs.readFileSync('demo_cond.json', 'utf8'));
const MG = JSON.parse(fs.readFileSync('demo_margin.json', 'utf8'));
const KW = JSON.parse(fs.readFileSync('demo_kws.json', 'utf8'));
const FA = JSON.parse(fs.readFileSync('demo_fa.json', 'utf8'));
const FE = JSON.parse(fs.readFileSync('demo_fe.json', 'utf8'));
const OP = JSON.parse(fs.readFileSync('demo_open.json', 'utf8'));
const r = (x, n) => Number(x).toFixed(n);
const z24 = FA.zero.find(x => x.hours === 24);
const sp01 = FA.spec.find(x => x.per_day === 0.1);
const me01 = FA.measure.find(x => x.spec === '0.1 次/天');
const cmp2 = FA.compare.find(x => x.ratio === 2.0);
const fe5 = FE.grid.filter(x => x.snr === 5);
const en5 = OP.enroll.find(x => x.n === 5);
const op = (p) => MT.ops.find(o => o.p === p);
const fa = (d) => KW.op.find(o => o.fa_day === d);

const D = {

// ══ Ⅰ 共同骨架 ═══════════════════════════════════════════════
// 01 两件事都是同一个假设检验
bintest: String.raw`\underbrace{\ell(\mathbf x)=\log\frac{p(\mathbf x\mid H_1)}
 {p(\mathbf x\mid H_0)}}_{\textstyle \text{唯一要算的东西}}
 \;\mathrel{\substack{\textstyle>\\[-3pt]\textstyle<}}\;\theta
 \qquad
 \begin{aligned}
 &H_1:\ \text{是本人 / 是唤醒词}\\
 &H_0:\ \text{是别人 / 是别的声音}
 \end{aligned}`,

// 阈值由代价和先验决定，与模型无关
bayes: String.raw`\theta^{\star}=\log\frac{C_{\text{fa}}\,(1-P_{\text{tar}})}
 {C_{\text{miss}}\,P_{\text{tar}}}
 \qquad
 \underbrace{P_{\text{tar}}=0.5\Rightarrow\theta^{\star}=0}
 _{\textstyle \text{EER 那个点}}
 \qquad
 \underbrace{P_{\text{tar}}=0.001\Rightarrow\theta^{\star}=${r(op(0.001).bayes_thr, 2)}}
 _{\textstyle \text{实测最优阈值 }${r(op(0.001).thr, 2)}}`,

// 02 DCF
dcf: String.raw`\begin{aligned}
 C_{\text{det}}(\theta)&=C_{\text{miss}}\,P_{\text{tar}}\,P_{\text{miss}}(\theta)
 +C_{\text{fa}}\,(1-P_{\text{tar}})\,P_{\text{fa}}(\theta)\\[6pt]
 \text{DCF}(\theta)&=\frac{C_{\text{det}}(\theta)}
 {\min\bigl(C_{\text{miss}}P_{\text{tar}},\ C_{\text{fa}}(1-P_{\text{tar}})\bigr)}
 &&\underbrace{1.0=\text{和什么都不做一样差}}
 _{\textstyle \text{归一化的全部意义}}
 \end{aligned}`,

// minDCF vs actDCF
mindcf: String.raw`\underbrace{\text{minDCF}=\min_{\theta}\text{DCF}(\theta)}
 _{\textstyle \substack{\text{事后挑阈值，}\\ \text{只看排序 → }${r(MT.calib[0].mindcf, 4)}\ \text{恒定}}}
 \qquad\qquad
 \underbrace{\text{actDCF}=\text{DCF}(\theta^{\star})}
 _{\textstyle \substack{\text{只能用贝叶斯阈值，}\\ ${r(MT.calib[0].actdcf, 4)}\to${r(Math.max(...MT.calib.map(c => c.actdcf)), 4)}}}`,

// Cllr
cllr: String.raw`\begin{aligned}
 C_{\text{llr}}&=\frac{1}{2\log 2}\left[
 \frac{1}{N_{\text{tar}}}\sum_{i}\log\bigl(1+e^{-\ell_i}\bigr)
 +\frac{1}{N_{\text{non}}}\sum_{j}\log\bigl(1+e^{+\ell_j}\bigr)\right]\\[6pt]
 &\underbrace{${r(MT.calib[0].cllr, 3)}\ \longrightarrow\ ${r(Math.max(...MT.calib.map(c => c.cllr)), 3)}}
 _{\textstyle \text{同一批分数，只做单调变换}}
 \end{aligned}`,

// 03 置信区间
binomse: String.raw`\widehat{p}\pm 1.96\sqrt{\frac{p(1-p)}{N}}
 \qquad\Longrightarrow\qquad
 \frac{\text{半宽}}{p}\approx\frac{1.96}{\sqrt{Np}}=\frac{1.96}{\sqrt{\text{错误个数}}}
 \qquad
 \underbrace{\text{30 个错误}\Rightarrow\pm 36\%}
 _{\textstyle \text{"三十法则"的来处}}`,

// 两系统比较的样本量
power: String.raw`N\;\ge\;\frac{\bigl(z_{1-\alpha/2}+z_{1-\beta}\bigr)^{2}
 \bigl[p_1(1-p_1)+p_2(1-p_2)\bigr]}{(p_1-p_2)^{2}}
 \qquad
 \underbrace{2.0\%\ \text{vs}\ 2.2\%\ \Rightarrow\ N\approx${MT.power[0].n_tar.toLocaleString('en')}}
 _{\textstyle \text{目标对，不是句子}}`,

// ══ Ⅱ 声纹 ═══════════════════════════════════════════════════
// 05 两协方差 PLDA 的生成模型
plda: String.raw`\mathbf x_{ij}=\underbrace{\mathbf y_i}
 _{\textstyle \substack{\text{说话人因子}\\ \mathbf y_i\sim N(\mathbf 0,\mathbf B)}}
 +\underbrace{\boldsymbol\varepsilon_{ij}}
 _{\textstyle \substack{\text{这一条的会话扰动}\\ \boldsymbol\varepsilon_{ij}\sim N(\mathbf 0,\mathbf W)}}
 \qquad
 \underbrace{\mathbf B=\text{类间}\quad \mathbf W=\text{类内}}
 _{\textstyle \text{整本手册只有这两个矩阵}}`,

// PLDA 的对数似然比：分块高斯，没有近似
pldallr: String.raw`\ell(\mathbf a,\mathbf b)
 =\log\frac{N\!\left(\begin{bmatrix}\mathbf a\\ \mathbf b\end{bmatrix};
 \mathbf 0,\ \boldsymbol\Sigma_{\text{同}}\right)}
 {N\!\left(\begin{bmatrix}\mathbf a\\ \mathbf b\end{bmatrix};
 \mathbf 0,\ \boldsymbol\Sigma_{\text{异}}\right)},
 \quad
 \boldsymbol\Sigma_{\text{同}}=\begin{bmatrix}\mathbf T&\mathbf B\\ \mathbf B&\mathbf T\end{bmatrix},
 \quad
 \boldsymbol\Sigma_{\text{异}}=\begin{bmatrix}\mathbf T&\mathbf 0\\ \mathbf 0&\mathbf T\end{bmatrix},
 \quad \mathbf T=\mathbf B+\mathbf W`,

// 展开成二次型
pldaquad: String.raw`\ell(\mathbf a,\mathbf b)
 =\underbrace{\mathbf a^{\top}\boldsymbol\Lambda\,\mathbf b}
 _{\textstyle \text{交叉项，唯一"比较"的地方}}
 +\underbrace{\tfrac12\mathbf a^{\top}\boldsymbol\Gamma\mathbf a
 +\tfrac12\mathbf b^{\top}\boldsymbol\Gamma\mathbf b}
 _{\textstyle \substack{\text{各自的"这条有多典型"}\\ \text{余弦完全没有这两项}}}
 +\underbrace{c}_{\textstyle \text{常数}}`,

// 余弦其实是"白化后的内积"
cos: String.raw`\cos(\mathbf a,\mathbf b)
 =\frac{\mathbf a^{\top}\mathbf b}{\lVert\mathbf a\rVert\,\lVert\mathbf b\rVert}
 \qquad
 \underbrace{\boldsymbol\Lambda\propto\mathbf I\ \Longrightarrow\ \ell\ \text{与}\ \cos\ \text{同序}}
 _{\textstyle \substack{\text{类内各向同性时二者等价；}\\ \text{实测 }8{:}1\text{ 时 PLDA 好 }${r(SC.aniso[SC.aniso.length - 1].ratio, 1)}\text{ 倍}}}`,

// LDA = 广义对称特征问题
lda: String.raw`\mathbf S_b\,\mathbf v=\lambda\,\mathbf S_w\,\mathbf v
 \qquad
 \underbrace{\mathbf V^{\top}\mathbf S_w\mathbf V=\mathbf I}
 _{\textstyle \text{顺带把类内白化了}}
 \qquad
 \underbrace{${r(SC.methods[0].eer, 2)}\%\ \to\ ${r(SC.methods[3].eer, 2)}\%}
 _{\textstyle \substack{\text{原始余弦 → LDA 后余弦；}\\ \text{白化买走了大头}}}`,

// 长度归一化
lnorm: String.raw`\mathbf x\ \mapsto\ \sqrt{d}\,\frac{\mathbf x}{\lVert\mathbf x\rVert}
 \qquad
 \underbrace{\text{对余弦是恒等变换}}
 _{\textstyle ${r(SC.methods[0].eer, 2)}\%\ \to\ ${r(SC.methods[1].eer, 2)}\%\ \text{，一模一样}}
 \qquad
 \underbrace{\text{对 PLDA 不是}}
 _{\textstyle \text{它是高斯化，要放在 PLDA 之前}}`,

// 06 统计池化
pool: String.raw`\boldsymbol\mu=\frac1T\sum_{t}\mathbf h_t,\qquad
 \boldsymbol\sigma=\sqrt{\frac1T\sum_{t}\mathbf h_t\odot\mathbf h_t-\boldsymbol\mu\odot\boldsymbol\mu}
 \qquad\longrightarrow\qquad
 \underbrace{[\boldsymbol\mu;\boldsymbol\sigma]}
 _{\textstyle \substack{\text{变长 }T\text{ 帧 → 定长一个向量}\\ \text{整条链路唯一的"降维打击"}}}`,

// 注意力池化
attpool: String.raw`\alpha_t=\frac{\exp\bigl(\mathbf w^{\top}f(\mathbf h_t)\bigr)}
 {\sum_{\tau}\exp\bigl(\mathbf w^{\top}f(\mathbf h_{\tau})\bigr)},
 \qquad
 \boldsymbol\mu=\sum_t\alpha_t\mathbf h_t,
 \qquad
 \boldsymbol\sigma=\sqrt{\sum_t\alpha_t\,\mathbf h_t\odot\mathbf h_t-\boldsymbol\mu\odot\boldsymbol\mu}`,

// 07 AAM-softmax
aam: String.raw`L=-\log\frac{e^{\,s\cos(\theta_{y}+m)}}
 {e^{\,s\cos(\theta_{y}+m)}+\sum_{k\neq y}e^{\,s\cos\theta_{k}}}
 \qquad
 \cos\theta_k=\frac{\mathbf W_k^{\top}}{\lVert\mathbf W_k\rVert}\cdot
 \frac{\mathbf z}{\lVert\mathbf z\rVert}
 \qquad
 \underbrace{s=${r(MG.setup.s, 0)},\ m=${r(MG.setup.m, 2)}}
 _{\textstyle \text{实测最优 }m=${r(MG.msweep.reduce((a, b) => a.eer <= b.eer ? a : b).m, 2)}}`,

// margin 的反传因子
aamgrad: String.raw`\frac{\partial\,\cos(\theta_y+m)}{\partial\,\cos\theta_y}
 =\frac{\sin(\theta_y+m)}{\sin\theta_y}\;>\;1
 \qquad
 \underbrace{\text{离得越近，放大越狠}}
 _{\textstyle \substack{\theta_y\to 0\ \text{时发散，}\\ \text{所以 }m\ \text{不能太大}}}
 \qquad
 \underbrace{m=0.5\ \text{开始变差}}
 _{\textstyle ${r(MG.msweep[MG.msweep.length - 2].eer, 2)}\%\to${r(MG.msweep[MG.msweep.length - 1].eer, 2)}\%}`,

// 09 AS-norm
asnorm: String.raw`\ell'(\mathbf a,\mathbf b)=\frac12\left[
 \frac{\ell-\mu_{\mathcal E}(\mathbf a)}{\sigma_{\mathcal E}(\mathbf a)}
 +\frac{\ell-\mu_{\mathcal E}(\mathbf b)}{\sigma_{\mathcal E}(\mathbf b)}\right]
 \qquad
 \underbrace{\mathcal E=\text{各自最像的 top-}k\ \text{冒充队列}}
 _{\textstyle \substack{\text{修的是"有人天生容易被冒充"：}\\
 \text{各人冒充分均值散布 }\sigma=${r(CD.asnorm.bias_sd, 4)}}}`,

// 10 时长：类内协方差随时长放大
durscale: String.raw`\mathbf W(T)\;\approx\;\mathbf W_{\!\infty}\left[\,
 \underbrace{f}_{\textstyle \substack{\text{说话人自己的}\\ \text{会话变化，不随 }T\text{ 降}}}
 +\ (1-f)\,\frac{T_0}{T}\,\right]
 \qquad
 \underbrace{T=1\,\text{s}:\ ${r(CD.dur[0].plda, 2)}\%
 \quad T=10\,\text{s}:\ ${r(CD.dur.find(d => d.T === 10).plda, 2)}\%}
 _{\textstyle \text{差 }${r(CD.dur_ratio, 0)}\ \text{倍}}`,

// 多条注册
enroll: String.raw`\bar{\mathbf x}=\frac1N\sum_{n=1}^{N}\mathbf x_n
 \ \sim\ N\!\left(\mathbf y,\ \frac{\mathbf W}{N}\right)
 \qquad
 \underbrace{N:1\to5\ \Rightarrow\ ${r(CD.enroll[0].cos, 2)}\%\to${r(CD.enroll[3].cos, 2)}\%}
 _{\textstyle \substack{\text{注册端是免费的那一侧：}\\ \text{只做一次，测试端每次都短}}}`,

// 域失配
domain: String.raw`\mathbf x^{(d)}=\mathbf y+\boldsymbol\varepsilon+
 \underbrace{\boldsymbol\delta_d}_{\textstyle \text{整个域的常数偏移}}
 \qquad\Longrightarrow\qquad
 \underbrace{\mathbf x^{(d)}-\frac{1}{|\mathcal D_d|}\sum_{\mathcal D_d}\mathbf x^{(d)}}
 _{\textstyle \substack{\text{各域各自去均值}\\ ${r(CD.domain[3].eer, 2)}\%\to${r(CD.domain[3].eer_cmn, 2)}\%}}`,

// ══ Ⅲ 唤醒 ═══════════════════════════════════════════════════
// 12 误唤醒率的单位
decrate: String.raw`N_{\text{dec}}=\frac{24\times3600\times1000}{\text{hop}_{\text{ms}}}
 =\frac{86{,}400{,}000}{${r(KW.unit.hop_ms, 0)}}
 =${KW.unit.dec_per_day.toLocaleString('en')}\ \text{次/天}
 \qquad
 \underbrace{\text{FA/天}=p_{\text{dec}}\times N_{\text{dec}}}
 _{\textstyle \substack{0.5\ \text{次/天}\Rightarrow
 p_{\text{dec}}=${KW.fa_map.find(f => f.fa_day === 0.5).p_dec.toExponential(1)}}}`,

// 13 唤醒词：碰巧说出的概率
chance: String.raw`p_{\text{词}}=\prod_{k=1}^{n}p(\text{音节}_k)
 \qquad
 \underbrace{\text{你好}:\ ${KW.words[0].p.toExponential(1)}}
 _{\textstyle ${r(KW.words[0].per_day, 2)}\ \text{次/天}}
 \qquad
 \underbrace{\text{小爱同学}:\ ${KW.words[2].p.toExponential(1)}}
 _{\textstyle \text{差 }${Math.round(KW.len_ratio).toLocaleString('en')}\ \text{倍}}`,

// 音节熵 → 等效词表
sylent: String.raw`H=-\sum_{s}p(s)\log_2 p(s)=${r(KW.syl.entropy_bits, 3)}\ \text{bit}
 \qquad\Longrightarrow\qquad
 \underbrace{2^{H}=${r(KW.syl.eff_types, 0)}}
 _{\textstyle \substack{${KW.syl.types}\ \text{个带调音节，}\\ \text{等效只有这么多}}}
 \qquad
 \underbrace{p_{\text{词}}\approx 2^{-nH}}
 _{\textstyle \text{每多一个音节，除以 }${r(KW.syl.eff_types, 0)}}`,

// 要多少小时的负样本
hours: String.raw`\text{Poisson}:\ \lambda_i=r_i\cdot\frac{T}{24}
 \qquad
 T\ \ \text{使得}\ \ \Pr\bigl[\hat r_1>\hat r_2\bigr]\ \text{达到 80\% 功效}
 \qquad
 \underbrace{1.0\to0.5\ \text{次/天}:\ T\approx${KW.hours[0].hours.toLocaleString('en')}\ \text{小时}}
 _{\textstyle \text{负样本音频，不是标注}}`,

// 15 级联功耗
cascade: String.raw`\bar P=\underbrace{P_1}_{\textstyle \text{一级常开}}
 +\underbrace{\frac{r_{\text{trig}}\cdot \tau}{3600}\,P_2}
 _{\textstyle \text{二级只在被叫醒时跑}}
 \qquad
 \underbrace{${r(KW.nocascade_mw, 0)}\ \text{mW}\ \to\ ${r(KW.cascade_best.mw, 2)}\ \text{mW}}
 _{\textstyle \substack{\text{省 }${r(KW.nocascade_mw / KW.cascade_best.mw, 0)}\ \text{倍，}\\
 \text{代价是漏唤醒 }${r(fa(0.5).miss, 2)}\%\to${r(KW.cascade_best.miss, 2)}\%}}`,

// 端侧算力
macs: String.raw`\text{MMAC/s}=\frac{\text{MAC/次}}{\text{hop}}
 \qquad
 P\approx E_{\text{MAC}}\cdot\text{MMAC/s}
 \qquad
 \underbrace{${KW.edge[0].mac.toLocaleString('en')}\ \text{MAC}\Rightarrow${r(KW.edge[0].mw50, 3)}\ \text{mW}}
 _{\textstyle \text{50 pJ/MAC，够用}}
 \qquad
 \underbrace{${KW.edge[2].mac.toLocaleString('en')}\Rightarrow${r(KW.edge[2].mw50, 2)}\ \text{mW}}
 _{\textstyle \text{超预算 }${r(KW.edge[2].mw50 / 0.5, 0)}\ \text{倍}}`,

// 后验平滑
smooth: String.raw`\tilde p_t=\frac{1}{w_{\text{smooth}}}\sum_{\tau=t-w+1}^{t}p_{\tau},
 \qquad
 c_t=\max_{\tau\in[t-w_{\max},\,t]}\tilde p_{\tau}
 \qquad
 \underbrace{\text{两级滑窗}}
 _{\textstyle \substack{\text{平滑抑制单帧尖峰，}\\ \text{取最大容忍语速抖动}}}`,

// 21 防伪
spoof: String.raw`\underbrace{\ell_{\text{ASV}}}_{\textstyle \text{是不是这个人}}
 \quad\text{与}\quad
 \underbrace{\ell_{\text{CM}}}_{\textstyle \text{是不是真人发声}}
 \qquad\Longrightarrow\qquad
 \text{t-DCF}=\underbrace{\beta\,P_{\text{miss}}^{\text{ASV}}
 +P_{\text{fa}}^{\text{CM}}\cdot P_{\text{fa,spoof}}^{\text{ASV}}}
 _{\textstyle \text{两个系统串起来的联合代价}}`,
// ── 11 常开：一天要做多少次判决 ────────────────────────────
alwayson: String.raw`N_{\text{判决}}=\underbrace{\tfrac{1}{T_{\text{hop}}}}
 _{\textstyle \text{每秒帧数}}\times 86400
 \qquad
 \underbrace{10\ \text{ms}\Rightarrow 8.64\times 10^{6}\ \text{次/天}}
 _{\textstyle \substack{\text{平滑到词级也还有百万量级，}\\
 \text{每一次都可能误唤醒}}}
 \qquad
 \underbrace{P_{\text{均}}\cdot 86400\ \text{是电池账本}}
 _{\textstyle \text{这两条约束推翻了从 ASR 带来的直觉}}`,

// ── 12 误唤醒是泊松率：零事件能说明什么 ────────────────────
poisson: String.raw`\begin{aligned}
 &k\sim\mathrm{Poisson}(\lambda T)
 \qquad
 \underbrace{k=0\ \Rightarrow\ \lambda\le\frac{-\ln\alpha}{T}\approx\frac{3}{T}}
 _{\textstyle \text{95\% 上界，俗称三法则}}\\[10pt]
 &\qquad\qquad
 \underbrace{T=24\,\text{h}\Rightarrow \lambda\le ${r(z24.hi_day, 2)}\ \text{次/天}}
 _{\textstyle \text{"跑了一天没误唤醒"只能说明这个}}
 \end{aligned}`,

// ── 12 要测准得跑多久 ──────────────────────────────────────
facount: String.raw`\frac{\mathrm{sd}[\hat\lambda]}{\lambda}=\frac{1}{\sqrt{k}}
 \qquad
 \underbrace{k\ge ${FA.k_ok.k}\ \Rightarrow\ \text{相对区间}\pm${r(FA.k_ok.rel * 50, 0)}\%}
 _{\textstyle \text{要"测准"而不只是给上界}}
 \qquad
 \underbrace{T=\frac{k}{\lambda}}
 _{\textstyle \substack{\lambda=0.1\ \text{次/天}\Rightarrow
 ${r(me01.days, 0)}\ \text{天的负样本}}}`,

// ── 12 比较两个系统 ────────────────────────────────────────
facomp: String.raw`T_{\text{每套}}=\frac{2\,(z_{\alpha/2}+z_{\beta})^{2}}
 {\bigl(2\sqrt{\lambda_{1}}-2\sqrt{\lambda_{2}}\bigr)^{2}}
 \qquad
 \underbrace{\lambda:0.5\to 0.25\ \text{次/天}}
 _{\textstyle \text{好 2 倍}}
 \ \Rightarrow\
 \underbrace{${r(cmp2.days, 0)}\ \text{天}}
 _{\textstyle \text{每套各跑这么久，才有 80\% 的把握说得出口}}`,

// ── 17 前端：两个最优点不是同一个 ──────────────────────────
fedual: String.raw`\alpha^{\star}_{\text{感知}}=\arg\max_{\alpha}\ \mathrm{segSNR}
 \qquad\ne\qquad
 \alpha^{\star}_{\text{下游}}=\arg\min_{\alpha}\ \mathrm{FRR}\big|_{\text{FA 固定}}
 \qquad
 \underbrace{\text{而}\ \frac{\text{FRR}_{\text{失配}}}{\text{FRR}_{\text{匹配}}}
 =${r(FE.summary.matched_gain_5db, 1)}}
 _{\textstyle \substack{\text{信号链一致带来的收益，}\\
 \text{比调}\ \alpha\ \text{大得多}}}`,

// ── 16 自定义唤醒词：注册就是在估一个模板 ──────────────────
openkws: String.raw`\hat T=\frac{1}{n}\sum_{i=1}^{n}\mathrm{warp}\bigl(L_{i}\bigr)
 \qquad
 s(X)=\frac{\langle \mathrm{warp}(X),\ \hat T\rangle}
 {\lVert \mathrm{warp}(X)\rVert\,\lVert \hat T\rVert}
 \qquad
 \underbrace{n\ \text{从 1 到 5 有用，再多没用}}
 _{\textstyle \substack{\text{补的是这个人自己的发音变异，}\\
 \text{补完就到头了}}}`,

// ── 19 负样本的构成决定了你测到的 FA ───────────────────────
corpus: String.raw`\lambda_{\text{测得}}\ \approx\
 \underbrace{\lambda_{0}}_{\textstyle \text{模型}}\times
 \underbrace{\rho_{\text{语音占比}}}_{\textstyle \text{素材}}\times
 \underbrace{\kappa_{\text{难度}}}_{\textstyle \text{素材}}
 \qquad
 \underbrace{\text{同一个模型，换素材差}\ ${r(FA.corpus_spread, 0)}\ \text{倍}}
 _{\textstyle \text{所以没说明素材的 FA/天 没有单位}}`,
};

const I = {
  eer: String.raw`${r(MT.base.eer, 2)}\%`,
  mindcf: String.raw`${r(MT.calib[0].mindcf, 4)}`,
  thr_eer: String.raw`${r(op(0.5).thr, 2)}`,
  thr_001: String.raw`${r(op(0.001).thr, 2)}`,
  B: String.raw`\mathbf B`,
  W: String.raw`\mathbf W`,
  T: String.raw`\mathbf T=\mathbf B+\mathbf W`,
  ell: String.raw`\ell`,
  theta: String.raw`\theta`,
  ptar: String.raw`P_{\text{tar}}`,
  pmiss: String.raw`P_{\text{miss}}`,
  pfa: String.raw`P_{\text{fa}}`,
  sqrtN: String.raw`1/\sqrt{N}`,
  mparam: String.raw`m`,
  sparam: String.raw`s`,
  cosab: String.raw`\cos(\mathbf a,\mathbf b)`,
  lam: String.raw`\boldsymbol\Lambda`,
  gam: String.raw`\boldsymbol\Gamma`,
  aniso: String.raw`${r(SC.aniso[SC.aniso.length - 1].ratio, 1)}\times`,
  hop: String.raw`${r(KW.unit.hop_ms, 0)}\ \text{ms}`,
  ndec: String.raw`${KW.unit.dec_per_day.toLocaleString('en')}`,
  Hbit: String.raw`${r(KW.syl.entropy_bits, 2)}\ \text{bit}`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('sv_k.json', JSON.stringify(out));
fs.writeFileSync('sv_ki.json', JSON.stringify(oi));
console.log('公式', Object.keys(out).length, '行内', Object.keys(oi).length);
