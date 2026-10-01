// §18 后置滤波：维纳增益的推导、Zelinski / McCowan 的来历、音乐噪声
const katex = require('katex'), fs = require('fs');

const D = {
pf_prob: String.raw`\min_{G(\omega,t)}\;
 E\Bigl[\bigl\lvert\,\underbrace{G(\omega,t)\,Y(\omega,t)}_{\text{处理后}}
 -\underbrace{S(\omega,t)}_{\text{想要的}}\bigr\rvert^{2}\Bigr]
 \qquad\text{其中}\quad Y=S+N`,

pf_expand: String.raw`\begin{aligned}
 J(G)&=E\bigl[\lvert G(S+N)-S\rvert^{2}\bigr]\\[4pt]
 &=\lvert G-1\rvert^{2}\,\varphi_s+\lvert G\rvert^{2}\,\varphi_n
 \qquad\underbrace{\bigl(E[SN^{*}]=0\bigr)}_{\text{目标与噪声不相关}}
 \end{aligned}`,

pf_solve: String.raw`\frac{\partial J}{\partial G^{*}}=(G-1)\varphi_s+G\varphi_n=0
 \qquad\Longrightarrow\qquad
 \boxed{\;G=\frac{\varphi_s}{\varphi_s+\varphi_n}
 =\frac{\xi}{1+\xi}\;,\quad \xi\overset{\text{定义}}{=}\frac{\varphi_s}{\varphi_n}\;}`,

pf_model: String.raw`\underbrace{\Phi_{ij}(\omega)=\varphi_s+\varphi_n\,\Gamma_{ij}(\omega)}_{i\neq j\ \text{：互谱}}
 \qquad\qquad
 \underbrace{\Phi_{ii}(\omega)=\varphi_s+\varphi_n}_{\text{自谱}}`,

pf_zel: String.raw`\underbrace{\Gamma_{ij}\overset{\text{假设}}{=}0}_{\text{Zelinski 的全部内容}}
 \;\Longrightarrow\;
 \hat\varphi_s=\Phi_{ij}
 \;\Longrightarrow\;
 \hat G_{\text{Zel}}=\frac{\dfrac{2}{M(M-1)}\displaystyle\sum_{i<j}\mathrm{Re}\{\Phi_{ij}\}}
 {\dfrac{1}{M}\displaystyle\sum_{i}\Phi_{ii}}`,

pf_mcc: String.raw`\begin{aligned}
 \Phi_{ij}&=\varphi_s+\Gamma_{ij}\bigl(\Phi_{ii}-\varphi_s\bigr)
 =\varphi_s(1-\Gamma_{ij})+\Gamma_{ij}\Phi_{ii}\\[6pt]
 \Longrightarrow\quad
 \hat\varphi_s^{\,(ij)}&=\frac{\mathrm{Re}\{\Phi_{ij}\}-\Gamma_{ij}\,\bar\Phi_{ii}}{1-\Gamma_{ij}}
 \qquad\underbrace{\bar\Phi_{ii}=\tfrac12(\Phi_{ii}+\Phi_{jj})}_{\text{两个自谱取平均}}
 \end{aligned}`,

pf_bias: String.raw`\frac{\hat G_{\text{Zel}}}{G_{\text{真}}}
 =\frac{\varphi_s+\varphi_n\bar\Gamma}{\varphi_s}
 =1+\frac{\bar\Gamma}{\xi}
 \qquad\xrightarrow[\;\omega\to0\;]{\bar\Gamma\to1}\qquad
 \underbrace{1+\frac{1}{\xi}=\frac{1}{G_{\text{真}}}}
 _{\textstyle \hat G_{\text{Zel}}\to1\ \text{：一点都不压}}`,

pf_var: String.raw`\hat\varphi\;\sim\;\frac{\varphi}{K}\,\chi^{2}_{2K}
 \qquad\Longrightarrow\qquad
 \mathrm{Var}\bigl[\hat\varphi\bigr]=\frac{\varphi^{2}}{K}
 \qquad\underbrace{K=1\;\Longrightarrow\;\text{标准差}=\text{均值}}
 _{\textstyle \text{每一帧的功率估计误差和它本身一样大}}`,

pf_fix: String.raw`G_{\text{用}}(\omega,t)=\max\Bigl\{\,
 \underbrace{\alpha\,G_{\text{用}}(\omega,t-1)+(1-\alpha)\hat G(\omega,t)}_{\text{时间平滑}}
 ,\;\underbrace{G_{\min}}_{\text{地板，约 }-12\text{ dB}}\Bigr\}`,
};

const I = {
  xi: String.raw`\xi=\varphi_s/\varphi_n`,
  G: String.raw`G(\omega,t)`,
  Gb: String.raw`\bar\Gamma`,
  Gij: String.raw`\Gamma_{ij}`,
  Phi: String.raw`\Phi_{ij}`,
  chi: String.raw`\chi^{2}_{2}`,
  K: String.raw`K`,
  Gmin: String.raw`G_{\min}`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('post.json', JSON.stringify(out));
fs.writeFileSync('post_inline.json', JSON.stringify(oi));
console.log('后置滤波:', Object.keys(out).length, '行内:', Object.keys(oi).length);
