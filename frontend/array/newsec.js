// §27 球谐 / §28 双耳 的全部公式
const katex = require('katex'), fs = require('fs');

const D = {
// ══════════════ 球谐 ══════════════
sh_expand: String.raw`\underbrace{e^{\,j k r\,\mathbf u_q\cdot\hat{\mathbf u}}}_{\text{阵元 }q\text{ 上的平面波}}
 =\sum_{n=0}^{\infty}\underbrace{4\pi j^{\,n} j_n(kr)}_{\textstyle b_n(kr)}
   \sum_{m=-n}^{n} Y_n^{m*}(\hat{\mathbf u})\,Y_n^{m}(\mathbf u_q)`,

sh_sft: String.raw`\underbrace{p_{nm}=\frac{4\pi}{Q}\sum_{q=1}^{Q}p(\mathbf u_q)\,Y_n^{m*}(\mathbf u_q)}_{\text{球谐变换：从"哪个麦"换到"哪个空间模式"}}
 \qquad\Longrightarrow\qquad
 p_{nm}=b_n(kr)\,Y_n^{m*}(\hat{\mathbf u})\,s`,

sh_beam: String.raw`y(\hat{\mathbf u}_0)=\sum_{n=0}^{N}\underbrace{\frac{c_n}{b_n(kr)}}_{\text{模态均衡}}
 \sum_{m=-n}^{n}p_{nm}\,Y_n^{m}(\hat{\mathbf u}_0)
 \;\overset{\text{加法定理}}{=}\;
 s\sum_{n=0}^{N}c_n\frac{2n+1}{4\pi}P_n(\cos\Theta)`,

sh_di: String.raw`\begin{aligned}
 c_n\equiv 1:\quad B(0)&=\sum_{n=0}^{N}\frac{2n+1}{4\pi}=\frac{(N+1)^{2}}{4\pi}\\[5pt]
 \frac{1}{4\pi}\!\int\!\lvert B\rvert^{2}d\Omega
 &=\frac{1}{4\pi}\sum_{n=0}^{N}\Bigl(\frac{2n+1}{4\pi}\Bigr)^{2}
   \underbrace{\int P_n^{2}\,d\Omega}_{=\;4\pi/(2n+1)}
 =\frac{1}{4\pi}\sum_{n=0}^{N}\frac{2n+1}{4\pi}
 =\frac{(N+1)^{2}}{(4\pi)^{2}}\\[5pt]
 \mathrm{DI}&=\frac{\lvert B(0)\rvert^{2}}{\frac{1}{4\pi}\int\lvert B\rvert^{2}d\Omega}
 =\boxed{\;(N+1)^{2}\;}\quad\Rightarrow\quad 20\log_{10}(N+1)\ \text{dB}
 \end{aligned}`,

sh_lowf: String.raw`j_n(x)\;\xrightarrow{\;x\ll1\;}\;\frac{x^{n}}{(2n+1)!!}
 \qquad\Longrightarrow\qquad
 \Bigl\lvert\frac{1}{b_n(kr)}\Bigr\rvert\propto (kr)^{-n}
 \qquad\Longrightarrow\qquad
 \underbrace{6n\ \text{dB/oct}}_{\text{第 }n\text{ 阶的噪声放大}}`,

sh_wng: String.raw`\mathrm{WNG}(N,kr)=\frac{Q\,(N+1)^{4}}
 {(4\pi)^{2}\displaystyle\sum_{n=0}^{N}\frac{2n+1}{\lvert b_n(kr)\rvert^{2}}}`,

sh_rigid: String.raw`\underbrace{b_n^{\text{open}}=4\pi j^{\,n}j_n(kr)}_{j_n\ \text{有零点}\;\Rightarrow\;\text{整阶陷零}}
 \qquad
 \underbrace{b_n^{\text{rigid}}=4\pi j^{\,n}\Bigl[j_n(kr)-\frac{j_n'(kr)}{h_n'(kr)}h_n(kr)\Bigr]
 =\frac{4\pi\,j^{\,n+1}}{(kr)^{2}\,h_n'(kr)}}_{\text{无零点，且分母恒不为 0}}`,

sh_limits: String.raw`\underbrace{Q\ \ge\ (N+1)^{2}}_{\text{阵元数下限}}
 \qquad
 \underbrace{kr\ \lesssim\ N}_{\text{空间混叠上限}}
 \qquad\Longrightarrow\qquad
 f\ \lesssim\ \frac{N\,c}{2\pi r}`,

// ══════════════ 双耳 ══════════════
bin_itd: String.raw`\underbrace{\tau(\theta)=\frac{a}{c}\bigl(\theta+\sin\theta\bigr)}_{\text{Woodworth：工程近似}}
 \qquad
 \underbrace{\tau\to\frac{3a}{c}\sin\theta}_{ka\ll1}
 \qquad
 \underbrace{\tau\to\frac{2a}{c}\sin\theta}_{ka\gg1}`,

bin_amb: String.raw`\underbrace{2\pi f\,\tau_{\max}<\pi}_{\text{相位不卷绕}}
 \;\Longrightarrow\;
 f<\frac{1}{2\tau_{\max}}=\frac{1}{2\times 656\,\mu\text{s}}\approx 762\ \text{Hz}`,

bin_prob: String.raw`\begin{aligned}
 \text{左耳：}\quad &\min_{\mathbf w_L}\;\mathbf w_L^{H}\mathbf R_n\mathbf w_L
 \quad\text{s.t.}\quad
 \underbrace{\mathbf w_L^{H}\mathbf a=a_L}_{\text{不是 }1\text{，是"左耳本来会收到的样子"}}\\[10pt]
 \text{右耳：}\quad &\min_{\mathbf w_R}\;\mathbf w_R^{H}\mathbf R_n\mathbf w_R
 \quad\text{s.t.}\quad \mathbf w_R^{H}\mathbf a=a_R
 \end{aligned}`,

bin_sol: String.raw`\mathbf w_L=a_L^{*}\,\underbrace{\frac{\mathbf R_n^{-1}\mathbf a}
 {\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}}_{\mathbf w_{\text{MVDR}}}
 \qquad\qquad
 \mathbf w_R=a_R^{*}\,\mathbf w_{\text{MVDR}}`,

bin_tgt: String.raw`\underbrace{\frac{\mathbf w_L^{H}\mathbf a}{\mathbf w_R^{H}\mathbf a}
 =\frac{a_L\,\mathbf w_{\text{MVDR}}^{H}\mathbf a}{a_R\,\mathbf w_{\text{MVDR}}^{H}\mathbf a}
 =\frac{a_L}{a_R}}_{\text{目标的 ITD / ILD 一丝不差地保住了}}`,

bin_noise: String.raw`\begin{aligned}
 \text{左耳残余噪声}\;&=\mathbf w_L^{H}\mathbf n=a_L\underbrace{\mathbf w_{\text{MVDR}}^{H}\mathbf n}_{\textstyle \nu\ \text{：同一个标量}}\\[4pt]
 \text{右耳残余噪声}\;&=\mathbf w_R^{H}\mathbf n=a_R\,\nu\\[6pt]
 \Longrightarrow\quad
 \frac{\text{左耳噪声}}{\text{右耳噪声}}&=\frac{a_L\nu}{a_R\nu}
 =\boxed{\;\frac{a_L}{a_R}\;}\;=\;\text{目标的双耳传函}
 \end{aligned}`,

bin_mwfn: String.raw`y_L=\underbrace{(1-\eta)\,\mathbf w_L^{H}\mathbf x}_{\text{处理过的}}
 \;+\;\underbrace{\eta\,x_L}_{\text{原封不动的左耳信号}}
 \qquad \eta\in[0,1]`,

bin_blcmv: String.raw`\mathbf w_L^{H}\mathbf a=a_L
 \qquad\text{且}\qquad
 \underbrace{\mathbf w_L^{H}\mathbf a_{\text{int}}=\gamma\,a_{L,\text{int}}}
 _{\text{干扰压低 }\gamma\text{ 倍，但保留它自己的方位}}`,
};

const I = {
  aL: String.raw`a_L`, aR: String.raw`a_R`, eta: String.raw`\eta`,
  bn: String.raw`b_n(kr)`, Np1: String.raw`(N+1)^2`, kr: String.raw`kr`,
  cn: String.raw`c_n`, pnm: String.raw`p_{nm}`, Ynm: String.raw`Y_n^{m}`,
  jn: String.raw`j_n(kr)`, tau: String.raw`\tau`, aa: String.raw`a`,
  ratio: String.raw`a_L/a_R`, gam: String.raw`\gamma`, NN: String.raw`N`,
  PN: String.raw`P_n(\cos\Theta)`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('newsec.json', JSON.stringify(out));
fs.writeFileSync('newsec_inline.json', JSON.stringify(oi));
console.log('新章公式:', Object.keys(out).length, '行内:', Object.keys(oi).length);
