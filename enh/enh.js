// 《单通道增强手册》全部公式。数字从 demo_*.json 取，不手抄。
// _head.html 只内嵌 Main / Math / Size / Caligraphic 四族字体，
// 所以不能用 \mathbb、\triangleq、\mathsf 等需要 AMS / SansSerif 的记号。
const katex = require('katex'), fs = require('fs');
const GA = JSON.parse(fs.readFileSync('demo_gain.json', 'utf8'));
const DD = JSON.parse(fs.readFileSync('demo_dd.json', 'utf8'));
const PH = JSON.parse(fs.readFileSync('demo_phase.json', 'utf8'));
const NN = JSON.parse(fs.readFileSync('demo_nn.json', 'utf8'));
const OU = JSON.parse(fs.readFileSync('demo_out.json', 'utf8'));
const GE = JSON.parse(fs.readFileSync('demo_gen.json', 'utf8'));
const TI = JSON.parse(fs.readFileSync('demo_tier.json', 'utf8'));
const PD = JSON.parse(fs.readFileSync('demo_pd.json', 'utf8'));
const EV = JSON.parse(fs.readFileSync('demo_eval.json', 'utf8'));
const r = (x, n) => Number(x).toFixed(n);
const main5 = (t) => GA.main['5'].find(x => x.tag.startsWith(t));
const cap98 = DD.capture['0.98'];
const CMP = 2.10;                       // tanh 压缩后 |M| 的 99.9 分位，见 demo_out.py 的打印
const ABL0 = GE.ablate[0];              // 消融里最贵的那一维

const D = {

// ══ Ⅰ 根本问题 ═══════════════════════════════════════════════
model: String.raw`y(t)=s(t)+v(t)
 \quad\xrightarrow{\ \text{STFT}\ }\quad
 Y_{k,l}=S_{k,l}+V_{k,l}
 \qquad
 \underbrace{\hat S_{k,l}=G_{k,l}\,Y_{k,l}}
 _{\textstyle \substack{\text{整本书只有这一个输出：}\\ \text{每个时频点上的一个实数增益}}}`,

// 误差的正交分解
decomp: String.raw`\hat S-S=\underbrace{(G-1)\,S}_{\textstyle \text{语音失真}}
 +\underbrace{G\,V}_{\textstyle \text{残留噪声}}
 \qquad
 \underbrace{\ \operatorname{E}\lVert\hat S-S\rVert^{2}
 =\operatorname{E}\lVert(G-1)S\rVert^{2}+\operatorname{E}\lVert GV\rVert^{2}}
 _{\textstyle \substack{S\perp V\ \text{，所以功率直接相加}\\ \text{——这是全书的记分板}}}`,

// 两个信噪比
snrdef: String.raw`\underbrace{\gamma_{k,l}=\frac{\lvert Y_{k,l}\rvert^{2}}{\lambda_{v}(k,l)}}
 _{\textstyle \substack{\text{后验信噪比}\\ \text{看得见，但含噪声的随机起伏}}}
 \qquad\qquad
 \underbrace{\xi_{k,l}=\frac{\lambda_{s}(k,l)}{\lambda_{v}(k,l)}}
 _{\textstyle \substack{\text{先验信噪比}\\ \text{看不见，必须估——这是全部难点}}}`,

// ══ Ⅱ 增益函数族 ═══════════════════════════════════════════════
subtract: String.raw`\lvert\hat S\rvert^{2}
 =\max\bigl(\lvert Y\rvert^{2}-\alpha\,\lambda_{v},\ \beta\,\lambda_{v}\bigr)
 \quad\Longrightarrow\quad
 G_{\text{sub}}=\sqrt{\max\Bigl(1-\frac{\alpha}{\gamma},\ \beta_{0}^{2}\Bigr)}
 \qquad
 \underbrace{\alpha=\text{过减}\quad\beta_{0}=\text{谱底}}
 _{\textstyle \text{两个纯听感补丁}}`,

wiener: String.raw`G_{\text{W}}=\frac{\xi}{1+\xi}
 \qquad
 \underbrace{\text{在}\ \lVert\hat S-S\rVert^{2}\ \text{下最优}}
 _{\textstyle \text{前提是 }S,V\text{ 都是高斯}}
 \qquad
 \underbrace{\xi\to 0\Rightarrow G\approx\xi}
 _{\textstyle \substack{\text{低信噪比处按 }\xi\text{ 线性下降，}\\ \xi\text{ 抖多少，增益就抖多少 dB}}}`,

stsa: String.raw`G_{\text{STSA}}=\frac{\sqrt{\pi}}{2}\,\frac{\sqrt{\nu}}{\gamma}\,
 e^{-\nu/2}\Bigl[(1+\nu)\,I_{0}\bigl(\tfrac{\nu}{2}\bigr)
 +\nu\,I_{1}\bigl(\tfrac{\nu}{2}\bigr)\Bigr],
 \qquad
 \nu=\frac{\xi}{1+\xi}\,\gamma
 \qquad
 \underbrace{\text{估的是}\ \lvert S\rvert\ \text{，不是}\ S}
 _{\textstyle \text{相位照抄带噪的}}`,

logmmse: String.raw`G_{\text{log}}=\frac{\xi}{1+\xi}\,
 \exp\Bigl(\frac{1}{2}\int_{\nu}^{\infty}\frac{e^{-t}}{t}\,dt\Bigr)
 =\frac{\xi}{1+\xi}\,e^{\frac{1}{2}E_{1}(\nu)}
 \qquad
 \underbrace{\text{估的是}\ \log\lvert S\rvert}
 _{\textstyle \substack{\text{对数域的均方误差最小，}\\ \text{更贴近人耳的响度感知}}}`,

// 共同形式：差别全在低 ξ 那一段
family: String.raw`G=G(\xi,\gamma),\qquad
 \underbrace{\lim_{\xi\to\infty}G=1}_{\textstyle \text{信号强就别动它}}
 \qquad
 \underbrace{\xi=-5\,\text{dB}\ \text{处：谱减}\ ${r(GA.curve_xi.sub[GA.curve_xi.xi_db.indexOf(-5)], 1)}\,\text{dB}
 \ \text{vs}\ \text{维纳}\ ${r(GA.curve_xi.wiener[GA.curve_xi.xi_db.indexOf(-5)], 1)}\,\text{dB}}
 _{\textstyle \text{全部差别都在低 }\xi\text{ 那一段}}`,

// ══ Ⅲ 先验信噪比 ═════════════════════════════════════════════
dd: String.raw`\hat\xi_{l}=\alpha\,\frac{\lvert\hat S_{l-1}\rvert^{2}}{\lambda_{v}}
 +(1-\alpha)\,\max\bigl(\gamma_{l}-1,\ 0\bigr)
 \qquad
 \underbrace{\alpha\approx0.98}
 _{\textstyle \substack{\text{残差起伏 }${r(DD.alpha[0].mus, 1)}\to${r(DD.alpha.find(a => a.alpha === 0.98).mus, 1)}\ \text{dB}\\
 \text{音乐噪声基本消失}}}`,

// 不动点：捕获阈值的来源
ddfix: String.raw`\xi^{\star}=\alpha\,\frac{(\xi^{\star})^{2}}{(1+\xi^{\star})^{2}}\,\gamma
 +(1-\alpha)(\gamma-1)
 \qquad
 \underbrace{\text{两个稳定解}}
 _{\textstyle \substack{\gamma<${r(cap98.thr_db, 2)}\,\text{dB}:\ \hat\xi\ \text{塌到下限}\\
 \gamma>${r(cap98.thr_db, 2)}\,\text{dB}:\ \hat\xi\approx\gamma-1}}`,

// 最小统计量
ms: String.raw`\hat\lambda_{v}(k,l)=B_{\min}\cdot
 \min_{\,l-D<i\le l}\ \underbrace{P(k,i)}_{\textstyle \text{平滑后的周期图}}
 \qquad
 \underbrace{B_{\min}>1}_{\textstyle \text{最小值天然偏小，要补偿}}
 \qquad
 \underbrace{D\ \text{要跨过最长的语音段}}
 _{\textstyle \text{所以追踪延迟至少 }D\text{ 帧}}`,

// MCRA / 语音存在概率
mcra: String.raw`\begin{aligned}
 I(k,l)&=\Bigl[\tfrac{P(k,l)}{P_{\min}(k,l)}<\delta\Bigr]
 &&\text{判"这里没语音"}\\[4pt]
 p(k,l)&=\alpha_{p}\,p(k,l-1)+(1-\alpha_{p})\bigl(1-I(k,l)\bigr)
 &&\text{语音存在概率}\\[4pt]
 \hat\lambda_{v}(k,l)&=\tilde\alpha\,\hat\lambda_{v}(k,l-1)+(1-\tilde\alpha)\,P(k,l),
 &&\tilde\alpha=\alpha_{d}+(1-\alpha_{d})\,p
 \end{aligned}`,

// 语音存在概率加权的增益（OM-LSA）
omlsa: String.raw`G_{\text{OM-LSA}}=\bigl[G_{\text{log}}\bigr]^{\,p}\cdot
 \bigl[G_{\min}\bigr]^{\,1-p}
 \qquad
 \underbrace{p=\Pr\bigl[H_{1}\mid Y\bigr]}
 _{\textstyle \text{这一点有语音的后验概率}}
 \qquad
 \underbrace{G_{\min}\ \text{就是谱底}}
 _{\textstyle \text{只是换了个推导来路}}`,

// ══ Ⅳ 变换与相位 ═════════════════════════════════════════════
ola: String.raw`\sum_{l}w^{2}\bigl(n-lR\bigr)=1
 \qquad
 \underbrace{\text{平方根汉宁窗} + 50\%\ \text{重叠}}
 _{\textstyle \text{满足 COLA，可完美重构}}
 \qquad
 \underbrace{\text{实测重构误差}\ ${r(GA.sig.pr_db, 0)}\ \text{dB}}
 _{\textstyle \text{浮点精度极限}}`,

latency: String.raw`T_{\text{alg}}=\underbrace{N_{\text{win}}}_{\textstyle \text{要等窗填满}}
 +\underbrace{R}_{\textstyle \text{块处理}}
 \qquad
 \underbrace{\Delta f=\frac{4f_{s}}{N_{\text{win}}}}
 _{\textstyle \text{汉宁窗主瓣宽度}}
 \qquad
 \underbrace{\Delta f<f_{0}\Rightarrow N_{\text{win}}\ge ${PH.resolve.need_pts}\ \text{点}=${r(PH.resolve.need_ms, 1)}\ \text{ms}}
 _{\textstyle \text{才分得开 }${r(PH.resolve.f0, 0)}\ \text{Hz 的相邻谐波}}`,

// 掩码的三种形式
masks: String.raw`\underbrace{M_{\text{IRM}}=\sqrt{\frac{\lvert S\rvert^{2}}
 {\lvert S\rvert^{2}+\lvert V\rvert^{2}}}}_{\textstyle \text{理想比值掩码}}
 \qquad
 \underbrace{M_{\text{IAM}}=\frac{\lvert S\rvert}{\lvert Y\rvert}}
 _{\textstyle \substack{\text{理想幅度掩码}\\ \text{只改幅度的天花板}}}
 \qquad
 \underbrace{M_{\text{cIRM}}=\frac{S}{Y}\ \text{（复数）}}
 _{\textstyle \text{复数，连相位一起改}}`,

// ══ Ⅴ 神经 ══════════════════════════════════════════════════
sisdr: String.raw`\text{SI-SDR}=10\log_{10}
 \frac{\lVert\alpha s\rVert^{2}}{\lVert\hat s-\alpha s\rVert^{2}},
 \qquad
 \alpha=\frac{\langle\hat s,\,s\rangle}{\lVert s\rVert^{2}}
 \qquad
 \underbrace{\text{由帕塞瓦尔定理，可以在谱域算}}
 _{\textstyle \text{所以能对掩码直接反传}}`,

macs: String.raw`\text{MMAC/s}=\frac{\text{MAC/帧}}{R/f_{s}}
 \qquad
 P\approx E_{\text{MAC}}\cdot\text{MMAC/s}
 \qquad
 \underbrace{${NN.cost.mac_per_frame.toLocaleString('en')}\ \text{MAC}
 \Rightarrow ${r(NN.cost.mmac_s, 2)}\ \text{MMAC/s}
 \Rightarrow ${r(NN.cost.mw50, 2)}\ \text{mW}}
 _{\textstyle \text{只比一对 FFT 贵 }${r(NN.cost.mac_per_frame / NN.cost.fft_mac, 0)}\ \text{倍}}`,

// ══ Ⅵ 评测 ══════════════════════════════════════════════════
segsnr: String.raw`\text{SegSNR}=\frac{1}{\lvert\mathcal L\rvert}\sum_{l\in\mathcal L}
 \Bigl[10\log_{10}\frac{\sum_{n}s^{2}}{\sum_{n}(s-\hat s)^{2}}\Bigr]_{-10}^{35}
 \qquad
 \underbrace{\mathcal L=\text{有语音的帧}}
 _{\textstyle \substack{\text{不截断、不去静音，}\\ \text{这个数就没有意义}}}`,

lsdf: String.raw`\begin{aligned}
 A_{k,l}&=20\log_{10}\lvert S_{k,l}\rvert,
 \qquad f_{l}=\max_{k}A_{k,l}-45\,\text{dB}\\[6pt]
 \text{LSD}&=\frac{1}{L}\sum_{l}\sqrt{\frac{1}{K}\sum_{k}
 \Bigl(\bigl[A_{k,l}\bigr]_{f_{l}}-\bigl[\hat A_{k,l}\bigr]_{f_{l}}\Bigr)^{2}}\\[4pt]
 &\qquad\underbrace{\text{下限 }f_{l}\text{ 必须逐帧设}}
 _{\textstyle \text{否则谐波谷里的对数差会发散}}
 \end{aligned}`,

// 音乐噪声的理论零点
musical: String.raw`\underbrace{\lvert V_{k,l}\rvert^{2}\sim\frac{\lambda_{v}}{2}\chi^{2}_{2}}
 _{\textstyle \text{平稳高斯噪声的周期图}}
 \quad\Longrightarrow\quad
 \sigma\Bigl[10\log_{10}\lvert V\rvert^{2}\Bigr]
 =\frac{10}{\ln 10}\cdot\frac{\pi}{\sqrt{6}}
 =\underbrace{${r(GA.mus_floor, 2)}\ \text{dB}}
 _{\textstyle \substack{\text{与处理无关的理论零点}\\ \text{实测 }${r(main5('带噪').mus, 2)}\ \text{dB}}}`,

// 下游：增强是一个信道
channel: String.raw`\underbrace{\hat s=\mathcal G(y)}_{\textstyle \text{增强}}
 \quad\longrightarrow\quad
 \underbrace{\mathbf e=f(\hat s)}_{\textstyle \text{下游的表示}}
 \qquad
 \underbrace{\mathcal G\ \text{非线性}\Rightarrow f(\mathcal G(\cdot))\ \text{的分布变了}}
 _{\textstyle \substack{\text{注册端和测试端必须用同一个 }\mathcal G\\
 \text{实测失配时 EER }${r(EV.asv[3].eer_matched, 1)}\%\to${r(EV.asv[3].eer_mismatch, 1)}\%}}`,
// ══ 新增：输出参数化 / 泛化 / 预算 / 保真与像真 ═══════════════════
// ㉓ 四种输出参数化
outparam: String.raw`\underbrace{M_{\text{IRM}}=\sqrt{\frac{\lvert S\rvert^{2}}
   {\lvert S\rvert^{2}+\lvert V\rvert^{2}}}\in[0,1]}
 _{\textstyle \substack{\text{维纳式，天然有界}}}
 \quad
 \underbrace{M_{\text{IAM}}=\frac{\lvert S\rvert}{\lvert Y\rvert}\in[0,\infty)}
 _{\textstyle \substack{\text{理想幅度掩码}\\ \text{——并}\textbf{不}\text{落在 }[0,1]}}
 \quad
 \underbrace{M_{\text{cIRM}}=\frac{S}{Y}\ \text{（复数）}}
 _{\textstyle \substack{\text{复数：上界是完美重建}}}`,

// ㉔ 上界与实得
ceilgap: String.raw`\underbrace{\text{上界}}_{\textstyle \substack{\text{知道 }S\text{ 时}\\ \text{这个参数化能做到}}}
 \;-\;\underbrace{\text{实得}}_{\textstyle \substack{\text{固定容量的网络}\\ \text{真正回归出来的}}}
 \;=\;\text{回归误差}
 \qquad
 \underbrace{\eta=\frac{\text{实得}}{\text{上界}}}
 _{\textstyle \substack{\text{兑现率：}${r(OU.achieved[0].realized,1)}\%\ \to\ ${r(OU.achieved[4].realized,1)}\%\\ \text{上界越高，它越低}}}`,

// ㉕ 复数掩码的压缩
cirmcomp: String.raw`\tilde M=K\,\frac{1-e^{-C M}}{1+e^{-C M}}
 \qquad K=${OU.const.ck},\ C=${OU.const.cc}
 \qquad
 \underbrace{\text{99.9 分位 } ${r(OU.range[1].cirm[3],2)}\ \to\ ${r(CMP,2)}}
 _{\textstyle \text{把重尾压回可回归的范围}}`,

// ㉖ 泛化：失配本身 vs 覆盖不足
cover: String.raw`\underbrace{\Delta_{\text{总}}}_{\textstyle \substack{\text{线上比基准档少的增益}}}
 =\underbrace{\Delta_{\text{失配}}}_{\textstyle \substack{\text{这个条件本身就更难}\\ \text{（训练盖住了也躲不掉）}}}
 +\underbrace{\Delta_{\text{覆盖}}}_{\textstyle \substack{\text{训练分布里没有它}\\ \text{（加数据能买回来的只有这一项）}}}
 \qquad
 \underbrace{\frac{\Delta_{\text{失配}}}{\Delta_{\text{覆盖}}}=${r(ABL0.stress_cost/ABL0.drop,1)}\times}
 _{\textstyle \substack{\text{实测：噪声类型这一维}}}`,

// ㉗ 延迟预算一路算到分辨率
budget: String.raw`\underbrace{\tau=\frac{N_{\text{win}}+R}{f_s}}
  _{\textstyle \substack{\text{算法延迟}}}
 +\underbrace{\frac{L\,R}{f_s}}_{\textstyle \substack{\text{前瞻}}}
 \;\le\;\tau_{\text{预算}}
 \qquad\Longrightarrow\qquad
 \underbrace{\Delta f=\frac{f_s}{N_{\text{win}}}}
 _{\textstyle \substack{\text{频率分辨率}}}
 \;\le\;\frac{F_0^{\min}}{2}
 \;\Longleftrightarrow\;
 \underbrace{N_{\text{win}}\ge\frac{2f_s}{F_0^{\min}}}
 _{\textstyle \text{要分开谐波，窗至少 }${r(TI.tiers[0].need_win_ms,1)}\ \text{ms}}`,

// ㉘ 两种失效方式
pdtrade: String.raw`\underbrace{\text{删掉了}=
   \frac{\#\{\lvert S\rvert\ \text{显著}\ \wedge\ \lvert\hat S\rvert\ \text{掉了}\}}
        {\#\{\lvert S\rvert\ \text{显著}\}}}
 _{\textstyle \substack{\text{预测式唯一会犯的错}\\ \beta{:}\,0\to1\ \ ${r(PD.summary.miss_b0,1)}\%\to${r(PD.summary.miss_b1,1)}\%}}
 \qquad
 \underbrace{\text{编出来了}=
   \frac{\#\{\lvert S\rvert\approx 0\ \wedge\ \lvert\hat S\rvert\ \text{显著}\}}
        {\#\{\lvert S\rvert\approx 0\}}}
 _{\textstyle \substack{\text{只有生成式才会犯}\\ ${r(PD.summary.hall_b0,2)}\%\to${r(PD.summary.hall_b1,2)}\%}}`,
};

const I = {
  gam: String.raw`\gamma`,
  xi: String.raw`\xi`,
  lamv: String.raw`\lambda_v`,
  G: String.raw`G`,
  alpha: String.raw`\alpha`,
  beta0: String.raw`\beta_0`,
  Y: String.raw`Y_{k,l}`,
  S: String.raw`S_{k,l}`,
  V: String.raw`V_{k,l}`,
  nu: String.raw`\nu=\frac{\xi}{1+\xi}\gamma`,
  E1: String.raw`E_1(\nu)`,
  musfloor: String.raw`${r(GA.mus_floor, 2)}\ \text{dB}`,
  capthr: String.raw`${r(cap98.thr_db, 2)}\ \text{dB}`,
  Nwin: String.raw`N_{\text{win}}`,
  R: String.raw`R`,
  p1: String.raw`p=\Pr[H_1\mid Y]`,
  Gmin: String.raw`G_{\min}`,
  cirm: String.raw`M_{\text{cIRM}}=S/Y`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('enh_k.json', JSON.stringify(out));
fs.writeFileSync('enh_ki.json', JSON.stringify(oi));
console.log('公式', Object.keys(out).length, '行内', Object.keys(oi).length);
