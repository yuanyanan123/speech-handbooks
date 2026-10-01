// §04 两条边界：DAS 的 WNG=M 与端射超指向 DI→M² 的完整推导
const katex = require('katex'), fs = require('fs');

const D = {
// ── 下界：DAS ────────────────────────────────────────────────
das_w: String.raw`\mathbf w_{\text{DAS}}=\frac{1}{M}\mathbf a
 \qquad\Longleftarrow\qquad
 \underbrace{\text{"对齐后取平均"}}_{\text{把每路的相位转正，再除以 }M}`,

das_num: String.raw`\underbrace{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}_{\text{信号}}
 =\Bigl\lvert\frac{1}{M}\mathbf a^{H}\mathbf a\Bigr\rvert^{2}
 =\Bigl\lvert\frac{1}{M}\sum_{m=1}^{M}\underbrace{\lvert a_m\rvert^{2}}_{=\,1}\Bigr\rvert^{2}
 =\Bigl\lvert\frac{M}{M}\Bigr\rvert^{2}=1`,

das_den: String.raw`\underbrace{\mathbf w^{H}\mathbf I\,\mathbf w}_{\text{噪声}}
 =\frac{1}{M^{2}}\mathbf a^{H}\mathbf a=\frac{M}{M^{2}}=\frac{1}{M}`,

das_res: String.raw`\boxed{\;\mathrm{WNG}_{\text{DAS}}
 =\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\mathbf I\mathbf w}
 =\frac{1}{1/M}=M
 \qquad\Longrightarrow\qquad 10\log_{10}M\;}`,

// ── 上界：Uzkov ──────────────────────────────────────────────
uz_taylor: String.raw`B(u)=\sum_{m=0}^{M-1}w_m^{*}\,e^{\,jkdm\,u}
 \;\xrightarrow[\;kd\to0\;]{}\;
 \sum_{m=0}^{M-1}w_m^{*}\sum_{p\ge0}\frac{(jkdm)^{p}}{p!}u^{p}
 \;=\;\underbrace{\sum_{p=0}^{M-1}\beta_p\,u^{p}}_{\textstyle\text{任意 }M-1\text{ 次多项式}}`,

uz_leg: String.raw`P(u)=\sum_{n=0}^{M-1}c_n\,P_n(u)
 \qquad\text{其中}\qquad
 \frac{1}{2}\int_{-1}^{1}P_n(u)P_{n'}(u)\,du=\frac{\delta_{nn'}}{2n+1}`,

uz_two: String.raw`\underbrace{P(1)=\sum_{n=0}^{M-1}c_n}_{\textstyle P_n(1)=1\ \text{恒成立}}
 \qquad\qquad
 \underbrace{\bigl\langle\lvert P\rvert^{2}\bigr\rangle_{\text{球面}}
 =\frac12\int_{-1}^{1}\lvert P\rvert^{2}du
 =\sum_{n=0}^{M-1}\frac{\lvert c_n\rvert^{2}}{2n+1}}_{\textstyle\text{正交性把交叉项全杀掉}}`,

uz_cs: String.raw`\Bigl\lvert\sum_{n}c_n\Bigr\rvert^{2}
 =\Bigl\lvert\sum_{n}\frac{c_n}{\sqrt{2n+1}}\cdot\sqrt{2n+1}\,\Bigr\rvert^{2}
 \;\overset{\text{Cauchy–Schwarz}}{\le}\;
 \underbrace{\sum_{n}\frac{\lvert c_n\rvert^{2}}{2n+1}}_{\textstyle =\ \langle\lvert P\rvert^{2}\rangle}
 \cdot\underbrace{\sum_{n=0}^{M-1}(2n+1)}_{\textstyle =\ M^{2}}`,

uz_sum: String.raw`\sum_{n=0}^{M-1}(2n+1)=\underbrace{1+3+5+\cdots+(2M-1)}_{M\ \text{项}}=M^{2}`,

uz_res: String.raw`\boxed{\;Q=\frac{\lvert P(1)\rvert^{2}}{\langle\lvert P\rvert^{2}\rangle}\;\le\;M^{2}
 \qquad\Longrightarrow\qquad
 \mathrm{DI}_{\max}^{\text{端射}}=20\log_{10}M\;}`,

uz_eq: String.raw`\text{取等条件：}\quad
 \frac{c_n}{\sqrt{2n+1}}\propto\sqrt{2n+1}
 \quad\Longleftrightarrow\quad
 c_n\propto(2n+1)
 \quad\Longrightarrow\quad
 P^{\star}(u)=\frac{1}{M^{2}}\sum_{n=0}^{M-1}(2n+1)P_n(u)`,

// ── 代价 ────────────────────────────────────────────────────
uz_cost: String.raw`\mathrm{WNG}^{\star}\;\propto\;(kd)^{\,2(M-1)}
 \qquad\Longrightarrow\qquad
 \underbrace{20(M-1)\ \text{dB/十倍频}}_{\textstyle \equiv\ 6(M-1)\ \text{dB/倍频程}}`,

// ── 边射的对照 ───────────────────────────────────────────────
bs: String.raw`\mathrm{DI}_{\max}^{\text{边射}}
 =\sum_{\substack{n=0\\ n\ \text{为偶}}}^{M-1}(2n+1)\,\bigl[P_n(0)\bigr]^{2}
 \;\ll\;M^{2}`,
};

const I = {
  M2: String.raw`M^{2}`,
  logM: String.raw`10\log_{10}M`,
  log2M: String.raw`20\log_{10}M`,
  u: String.raw`u=\cos\theta`,
  Pn: String.raw`P_n(u)`,
  cn: String.raw`c_n\propto(2n+1)`,
  sum: String.raw`\textstyle\sum_{n=0}^{M-1}(2n+1)`,
  sumN: String.raw`\textstyle\sum_{n=0}^{N}(2n+1)=(N+1)^{2}`,
  NM: String.raw`N=M-1`,
  aGa: String.raw`\mathbf a^{H}\boldsymbol\Gamma^{-1}\mathbf a`,
  kd: String.raw`kd`,
  wdas: String.raw`\mathbf w_{\text{DAS}}=\mathbf a/M`,
  am: String.raw`\lvert a_m\rvert=1`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('bound.json', JSON.stringify(out));
fs.writeFileSync('bound_inline.json', JSON.stringify(oi));
console.log('两条边界:', Object.keys(out).length, '行内:', Object.keys(oi).length);
