// 《ASR 链路手册》全部公式。数字从 demo_*.json 取，不手抄。
// _head.html 只内嵌 Main / Math / Size / Caligraphic 四族字体，
// 所以不用 \mathbb、\triangleq、\mathsf 等需要 AMS / SansSerif 的记号。
const katex = require('katex'), fs = require('fs');
const WF = JSON.parse(fs.readFileSync('demo_wfst.json', 'utf8'));
const AL = JSON.parse(fs.readFileSync('demo_align.json', 'utf8'));
const DE = JSON.parse(fs.readFileSync('demo_decode.json', 'utf8'));
const ST = JSON.parse(fs.readFileSync('demo_stream.json', 'utf8'));
const AG = JSON.parse(fs.readFileSync('demo_aug.json', 'utf8'));
const AP = JSON.parse(fs.readFileSync('demo_adapt.json', 'utf8'));
const CF = JSON.parse(fs.readFileSync('demo_conf.json', 'utf8'));
const KDJ = JSON.parse(fs.readFileSync('demo_kd.json', 'utf8'));
const VD = JSON.parse(fs.readFileSync('demo_vad.json', 'utf8'));
const r = (x, n) => Number(x).toFixed(n);
const cm = (x) => Number(x).toLocaleString('en');
const cnt = AL.count[AL.count.length - 1];
const mem = AL.mem[AL.mem.length - 1];

const D = {

// ══ Ⅰ 基础 ══════════════════════════════════════════════════
// 贝叶斯分解：声学模型 + 语言模型
bayes: String.raw`\hat W=\arg\max_{W}\ P(W\mid X)
 =\arg\max_{W}\ \underbrace{p(X\mid W)}_{\textstyle \text{声学模型}}\,
 \underbrace{P(W)}_{\textstyle \text{语言模型}}
 \qquad
 \underbrace{\text{端到端把这两项合成一个}}
 _{\textstyle \substack{\text{于是"模型自带一个语言模型"}\\ \text{成了后面一整节的麻烦}}}`,

// 词错误率
wer: String.raw`\text{WER}=\frac{S+D+I}{N}
 \qquad
 \underbrace{S\ \text{替换}\quad D\ \text{删除}\quad I\ \text{插入}}
 _{\textstyle \text{由编辑距离的回溯路径决定}}
 \qquad
 \underbrace{\text{可以大于 }100\%}
 _{\textstyle \text{插入没有上界}}`,

// ══ Ⅱ 技术脉络 ═══════════════════════════════════════════════
// HMM 的似然
hmm: String.raw`p(X\mid W)=\sum_{S}\ \prod_{t=1}^{T}
 \underbrace{a_{s_{t-1}s_{t}}}_{\textstyle \text{转移}}\,
 \underbrace{b_{s_{t}}(x_{t})}_{\textstyle \text{这一帧像不像这个状态}}
 \qquad
 \underbrace{\text{求和变求最大 = Viterbi}}
 _{\textstyle \text{解码用最大，训练用求和}}`,

// GMM 的发射概率
gmm: String.raw`b_{s}(x)=\sum_{m=1}^{M}c_{sm}\,
 \mathcal N\bigl(x;\ \boldsymbol\mu_{sm},\ \boldsymbol\Sigma_{sm}\bigr)
 \qquad
 \underbrace{\boldsymbol\Sigma\ \text{取对角}}
 _{\textstyle \substack{\text{所以特征必须先去相关}\\ \text{——这是 MFCC 里那个 DCT 的唯一理由}}}`,

// DNN-HMM 的伪似然
hybrid: String.raw`b_{s}(x_{t})\ \propto\ \frac{P(s\mid x_{t})}{P(s)}
 \qquad
 \underbrace{\text{网络输出的是后验，HMM 要的是似然}}
 _{\textstyle \text{除以先验这一步叫"伪似然"，漏了它模型会偏向高频状态}}`,

// MMI / LF-MMI
mmi: String.raw`\mathcal F_{\text{MMI}}=\sum_{u}\log
 \frac{p(X_{u}\mid W_{u})^{\kappa}P(W_{u})}
 {\sum_{W}p(X_{u}\mid W)^{\kappa}P(W)}
 \qquad
 \underbrace{\text{分子：正确的那条}}_{\textstyle \text{numerator lattice}}
 \quad
 \underbrace{\text{分母：所有可能}}_{\textstyle \text{denominator lattice}}`,

// MMI 的梯度就是两个占据度之差
mmigrad: String.raw`\frac{\partial\mathcal F_{\text{MMI}}}{\partial\,\log b_{s}(x_{t})}
 =\underbrace{\gamma^{\text{num}}_{s}(t)}_{\textstyle \text{分子占据度}}
 -\underbrace{\gamma^{\text{den}}_{s}(t)}_{\textstyle \text{分母占据度}}
 \qquad
 \underbrace{\text{两次前向-后向之差}}
 _{\textstyle \substack{\text{所有序列判别训练都是这个形状：}\\ \text{"该走的路"减去"实际在走的路"}}}`,

// MWER
mwer: String.raw`\mathcal L_{\text{MWER}}=\sum_{W\in\mathcal N}
 \hat P(W\mid X)\,\bigl[\mathcal E(W,W^{*})-\bar{\mathcal E}\bigr],
 \qquad
 \hat P(W\mid X)=\frac{P(W\mid X)}{\sum_{W'\in\mathcal N}P(W'\mid X)}
 \qquad
 \underbrace{\mathcal N=\text{n-best}}
 _{\textstyle \text{直接优化词错误的期望}}`,

// ══ Ⅲ 机制拆解 ═══════════════════════════════════════════════
// 帧几何
frame: String.raw`T=\Bigl\lfloor\frac{L-N_{\text{win}}}{R}\Bigr\rfloor+1
 \qquad
 \underbrace{\text{下采样 }k\text{ 倍后}\ T'=\lceil T/k\rceil}
 _{\textstyle \substack{\text{每个输出帧代表 }kR/f_s\ \text{秒}\\
 \text{——这是所有时间戳的分母}}}`,

// 同态解卷积
cepstrum: String.raw`x=h * e
 \ \xrightarrow{\ \text{DFT}\ }\ X=H\cdot E
 \ \xrightarrow{\ \log\ }\ \log X=\log H+\log E
 \ \xrightarrow{\ \text{DCT}\ }\ \underbrace{c_{\text{低}}}_{\textstyle \text{声道}}
 +\underbrace{c_{\text{高}}}_{\textstyle \text{激励}}`,

// CTC 的损失
ctc: String.raw`P(y\mid X)=\sum_{\pi\in\mathcal B^{-1}(y)}\prod_{t=1}^{T}P(\pi_{t}\mid X)
 \qquad
 \underbrace{\mathcal B:\ \text{去重复、去 blank}}
 _{\textstyle \substack{T=${cnt.T},\ U=${cnt.U}\ \text{时对齐有}\ 10^{${r(cnt.ctc_log10, 0)}}\ \text{条}\\
 \text{——但动态规划只要 }O(TU)}}`,

// CTC 的前向递推
ctcfwd: String.raw`\alpha_{t}(s)=P(\pi_{t}=\ell'_{s}\mid X)\cdot
 \Bigl[\alpha_{t-1}(s)+\alpha_{t-1}(s-1)
 +\underbrace{\alpha_{t-1}(s-2)}_{\textstyle \substack{\text{只有 }\ell'_{s}\neq\text{blank}\\
 \text{且}\ \ell'_{s}\neq\ell'_{s-2}\ \text{时}}}\Bigr]`,

// RNN-T 的格
rnnt: String.raw`\begin{aligned}
 P(y\mid X)&=\sum_{\text{格上的单调路径}}\prod P(\cdot)\\[4pt]
 \underbrace{\text{路径数}=\binom{T+U}{U}}
 _{\textstyle T=${cnt.T},\ U=${cnt.U}\ \Rightarrow\ 10^{${r(cnt.rnnt_log10, 0)}}}
 &\qquad
 \underbrace{\text{格子数}=T\times(U{+}1)}
 _{\textstyle \text{内存卡在这一项，不是上一项}}
 \end{aligned}`,

// RNN-T 的前向
rnntfwd: String.raw`\alpha(t,u)=\underbrace{\alpha(t-1,u)\,P_{\text{b}}(t-1,u)}
 _{\textstyle \text{走一帧，不输出}}
 +\underbrace{\alpha(t,u-1)\,P_{y_{u}}(t,u-1)}
 _{\textstyle \text{输出一个符号，不走帧}}`,

// 联合网络的内存
joint: String.raw`\text{显存}\ \approx\ B\cdot T\cdot(U{+}1)\cdot V\cdot 4\ \text{字节}
 \qquad
 \underbrace{${mem.sec}\ \text{s},\ V=${cm(mem.V)}\ \Rightarrow\ ${r(mem.rnnt_mb / 1000, 1)}\ \text{GB / 条}}
 _{\textstyle \substack{\text{CTC 是 }T\cdot V\text{，小 }${mem.ratio}\ \text{倍}\\
 \text{——RNN-T 全部的工程麻烦都在这里}}}`,

// 注意力
attn: String.raw`\text{Attn}(Q,K,V)=\text{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_{k}}}\right)V
 \qquad
 \underbrace{O(T^{2}d)}_{\textstyle \substack{30\ \text{秒音频 }T\approx750\\
 \text{所以流式必须切块}}}`,

// 强制对齐与 GOP
gop: String.raw`\text{GOP}(p)=\log\frac{p\bigl(X_{(t_1,t_2)}\mid p\bigr)}
 {\max_{q\in\mathcal Q}p\bigl(X_{(t_1,t_2)}\mid q\bigr)}
 \qquad
 \underbrace{\text{先强制对齐拿到}\ (t_1,t_2)}
 _{\textstyle \text{所以发音评测的上限就是对齐的精度}}`,

// ══ Ⅳ 解码 ═══════════════════════════════════════════════════
// WFST 合成
compose: String.raw`(A\circ B)\bigl[(q_{a},q_{b})\xrightarrow{\ i:o\ }(q'_{a},q'_{b})\bigr]
 \ \Longleftarrow\
 A\bigl[q_{a}\xrightarrow{\ i:c\ }q'_{a}\bigr]\ \wedge\
 B\bigl[q_{b}\xrightarrow{\ c:o\ }q'_{b}\bigr]
 \qquad
 \underbrace{\text{HCLG}=H\circ C\circ L\circ G}
 _{\textstyle \text{senone} \to \text{三音子} \to \text{音素} \to \text{词} \to \text{词串}}`,

// 确定化的残留
detmz: String.raw`Q'=\bigl\{(q,\ \underbrace{w}_{\textstyle \text{残留权重}},\
 \underbrace{\sigma}_{\textstyle \text{残留输出串}})\bigr\}
 \qquad
 \underbrace{\text{同音词} \Rightarrow \sigma\ \text{永远吐不出去}}
 _{\textstyle \substack{\text{实测：不加消歧符时确定化在 }6\!\times\!10^{4}\ \text{态上被迫中止；}\\
 \text{加了是}\ ${cm(WF.disambig.states)}\ \text{态}}}`,

// beam search 的打分
beamscore: String.raw`\begin{aligned}
 s(y)&=\sum_{u}\Bigl[\log P_{\text{AM}}(y_{u}\mid X,y_{<u})
 +\lambda\log P_{\text{LM}}(y_{u}\mid y_{<u})
 -\gamma\log P_{\text{ILM}}(y_{u}\mid y_{<u})+\beta\Bigr]\\[4pt]
 &\qquad\qquad
 \underbrace{\text{beam 只负责找}\ \arg\max s}
 _{\textstyle s\ \text{本身对不对，是另一回事}}
 \end{aligned}`,

// 三种融合
fusion: String.raw`\begin{aligned}
 \text{shallow}\quad & s=\log P_{\text{AM}}+\lambda\log P_{\text{LM}}
 &&${r(DE.fusion.shallow, 2)}\%\\[4pt]
 \text{density ratio}\quad & s=\log P_{\text{AM}}+\lambda\log P_{\text{LM}}
 -\gamma\log P_{\text{源域}}
 &&${r(DE.fusion.dr, 2)}\%\\[4pt]
 \text{ILME}\quad & s=\log P_{\text{AM}}+\lambda\log P_{\text{LM}}
 -\gamma\log P_{\text{内部}}
 &&${r(DE.fusion.ilme, 2)}\%
 \end{aligned}`,

// 内部语言模型
ilm: String.raw`P_{\text{ILM}}(y_{u}\mid y_{<u})\ \approx\
 P_{\text{AM}}\bigl(y_{u}\mid \underbrace{X=0}_{\textstyle \text{声学输入置零}},\,y_{<u}\bigr)
 \qquad
 \underbrace{\text{它比训练文本的文法}\ \textbf{弱}}
 _{\textstyle \substack{\text{所以按训练文法去减会减多；}\\
 \text{实测 }${r(DE.fusion.dr, 2)}\%\ \text{vs}\ ${r(DE.fusion.ilme, 2)}\%}}`,

// lattice 的 oracle
oracle: String.raw`\text{oracle WER}=\min_{W\in\mathcal L}\ \text{WER}(W,W^{*})
 \qquad
 \underbrace{\text{top-1}\ ${r(DE.oracle[DE.oracle.length - 1].top1, 2)}\%
 \ \to\ \text{oracle}\ ${r(DE.oracle[DE.oracle.length - 1].oracle, 2)}\%}
 _{\textstyle \text{这个差就是重打分的全部空间}}`,

// ══ Ⅴ 工程 ══════════════════════════════════════════════════
// 流式延迟
latency: String.raw`T_{\text{总}}=\underbrace{T_{\text{chunk}}}_{\textstyle \text{攒够一块}}
 +\underbrace{T_{\text{look}}}_{\textstyle \text{前瞻}}
 +\underbrace{T_{\text{计算}}}_{\textstyle \text{RTF}\times T_{\text{chunk}}}
 +\underbrace{T_{\text{端点}}}_{\textstyle \text{等静音}}
 \qquad
 \underbrace{\text{最优前瞻}\ ${r(ST.look_best.lat_ms, 0)}\ \text{ms}}
 _{\textstyle \text{再长反而更差}}`,

// 状态缓存
cache: String.raw`M_{\text{cache}}=B\cdot N_{\text{layer}}\cdot T_{\text{hist}}\cdot d\cdot 4
 \qquad
 \underbrace{${ST.cache[2].chunk}\ \text{帧 chunk}\ \Rightarrow\ ${r(ST.cache[2].total_mb, 2)}\ \text{MB / 路}}
 _{\textstyle \substack{100\ \text{路并发}\ =\ ${r(ST.cache_100, 0)}\ \text{MB}\\
 \text{模型权重是共享的，这个不是}}}`,

// DER
der: String.raw`\text{DER}=\frac{\overbrace{T_{\text{miss}}}^{\textstyle \text{漏检}}
 +\overbrace{T_{\text{fa}}}^{\textstyle \text{虚警}}
 +\overbrace{T_{\text{conf}}}^{\textstyle \text{说话人混淆}}}
 {T_{\text{总说话时间}}}
 \qquad
 \underbrace{\text{聚类式的漏检下限}=\text{重叠比例}}
 _{\textstyle \substack{\text{每个窗只能给一个标签}\\
 \text{实测重叠 }30\%\ \text{时下限}\ ${r(ST.dia[ST.dia.length - 1].floor, 1)}\%}}`,

// 热词偏置
bias: String.raw`s'(y)=s(y)+\underbrace{\mu\sum_{u}\bigl[y_{<u}\ \text{是某个热词的前缀}\bigr]}
 _{\textstyle \text{沿前缀逐步给，不是命中了才给}}
 \qquad
 \underbrace{\text{必须配"走错了要扣回去"}}
 _{\textstyle \text{否则解码器会被诱导着往热词走}}`,

// ══ 新增：数据增强 / 自适应 / 校准 / 蒸馏 / 切分 ═══════════════════════
// 逐条 CMVN：对数梅尔域里，信道是加性偏置、增益是加性常数
cmvn: String.raw`\underbrace{\log\lvert Y_{t,k}\rvert^{2}=\log\lvert S_{t,k}\rvert^{2}+\underbrace{\log\lvert H_k\rvert^{2}}_{\textstyle \text{信道：每个频带一个常数}}}
 _{\textstyle \text{卷积信道在对数谱里变成加性偏置}}
 \qquad
 \hat x_{t,k}=\frac{x_{t,k}-\mu_k}{\sigma_k}
 \ \Rightarrow\ \underbrace{\text{偏置被减掉}}_{\textstyle \substack{\text{电话带宽}\ ${r(AG.note.clean_tel, 0)}\%\to ${r(AG.note.cmvn_tel, 0)}\%}}`,

// 声道长度失配：共振峰整体缩放 = 对数频率轴上的平移
vtl: String.raw`F_i\ \to\ e^{v}F_i
 \quad\Longleftrightarrow\quad
 \underbrace{\log F_i\ \to\ \log F_i+v}_{\textstyle \text{对数频率轴上整体平移}}
 \qquad
 \underbrace{\text{源模型 }\lvert v\rvert<0.1:\ ${r(AP.note.src_acc, 0)}\%\ \to\ ${r(AP.note.far_acc, 0)}\%}
  _{\textstyle \text{平移到 }v\approx\pm0.35\text{ 时}}`,

// 校准：ECE 与温度
ece: String.raw`\mathrm{ECE}=\sum_{b=1}^{B}\frac{\lvert\mathcal{B}_b\rvert}{N}\,
 \Big\lvert\ \underbrace{\mathrm{acc}(\mathcal{B}_b)}_{\textstyle \text{桶内准确率}}
 -\underbrace{\mathrm{conf}(\mathcal{B}_b)}_{\textstyle \text{桶内平均置信度}}\Big\rvert
 \qquad
 p_i=\frac{e^{z_i/T}}{\sum_j e^{z_j/T}},\ \ T^{*}=\arg\min_{T}\ \mathrm{NLL}_{\text{验证集}}`,

// 蒸馏
kd: String.raw`\mathcal{L}=\alpha\,T^{2}\,\mathrm{KL}\!\Big(
 \underbrace{\mathrm{softmax}(z_t/T)}_{\textstyle \text{教师（温度 }T\text{）}}\ \Big\Vert\
 \underbrace{\mathrm{softmax}(z_s/T)}_{\textstyle \text{学生}}\Big)
 +(1-\alpha)\,\mathrm{CE}(y,\ \mathrm{softmax}(z_s))
 \qquad
 \underbrace{T\in[1,8],\ \alpha\in[0,1]}_{\textstyle \text{整个扫描里差别}\ \le 1\ \text{个点}}`,

// 量化
quant: String.raw`w_q=s\cdot\mathrm{clip}\!\Big(\mathrm{round}\big(\tfrac{w}{s}\big),\,-(2^{b-1}-1),\,2^{b-1}-1\Big)
 \qquad
 \underbrace{s=\frac{\max\lvert w\rvert}{2^{b-1}-1}}
  _{\textstyle \substack{\text{按张量：整个矩阵一个 }s\\ \text{按通道：每个输出通道一个 }s}}`,
};

const I = {
  wer: String.raw`\text{WER}`,
  T: String.raw`T`,
  U: String.raw`U`,
  V: String.raw`V`,
  alpha: String.raw`\alpha(t,u)`,
  blank: String.raw`\text{blank}`,
  lam: String.raw`\lambda`,
  gam: String.raw`\gamma`,
  hclg: String.raw`H\circ C\circ L\circ G`,
  eps: String.raw`\varepsilon`,
  ctcN: String.raw`10^{${r(cnt.ctc_log10, 0)}}`,
  rnntN: String.raw`10^{${r(cnt.rnnt_log10, 0)}}`,
  occ: String.raw`${r(AL.occupancy['q0.99'] * 100, 0)}\%`,
  kappa: String.raw`\kappa`,
  gnum: String.raw`\gamma^{\text{num}}`,
  gden: String.raw`\gamma^{\text{den}}`,
  pilm: String.raw`P_{\text{ILM}}`,
  RTF: String.raw`\text{RTF}`,
  DER: String.raw`\text{DER}`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('asr_k.json', JSON.stringify(out));
fs.writeFileSync('asr_ki.json', JSON.stringify(oi));
console.log('公式', Object.keys(out).length, '行内', Object.keys(oi).length);
