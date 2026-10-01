// §02：Q 是怎么来的，以及它和 DI、和 04/07 节的 Q 是同一个
const katex = require('katex'), fs = require('fs');

const D = {
qdef: String.raw`\underbrace{I_{\text{全向}}=\frac{W}{4\pi r^{2}}}_{\text{功率 }W\text{ 均匀摊在整个球面上}}
 \qquad\qquad
 \underbrace{I_{\text{有指向性}}=Q\cdot\frac{W}{4\pi r^{2}}}
 _{\text{同样的 }W\text{，被集中到主瓣里}}`,

qpat: String.raw`\boxed{\;Q\;\overset{\text{定义}}{=}\;
 \frac{\lvert B(\theta_0)\rvert^{2}}{\bigl\langle\lvert B(\theta)\rvert^{2}\bigr\rangle_{\text{球面}}}\;}
 \qquad\qquad
 \underbrace{\mathrm{DI}\;\overset{\text{定义}}{=}\;10\log_{10}Q}
 _{\text{只是同一个数的 dB 写法}}`,

qunify: String.raw`\begin{aligned}
 B(\theta)=\mathbf w^{H}\mathbf a(\theta)
 \quad\Longrightarrow\quad
 \bigl\langle\lvert B(\theta)\rvert^{2}\bigr\rangle_{\text{球面}}
 &=\mathbf w^{H}\underbrace{\bigl\langle\mathbf a(\theta)\,\mathbf a^{H}(\theta)\bigr\rangle_{\text{球面}}}
   _{\textstyle =\;\boldsymbol\Gamma_{\text{diff}}\ (\text{01 节那个 sinc 矩阵})}\mathbf w\\[10pt]
 \Longrightarrow\qquad
 Q&=\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\boldsymbol\Gamma_{\text{diff}}\mathbf w}
 \end{aligned}`,

qrc: String.raw`r_c=\sqrt{\frac{Q\,R}{16\pi}}
 \qquad\Longrightarrow\qquad
 \underbrace{Q\times4}_{\mathrm{DI}\,+6\,\text{dB}}
 \;\Longrightarrow\;
 \underbrace{r_c\times\sqrt{4}=r_c\times2}_{\text{拾音距离翻倍}}`,
};

const I = {
  Q: String.raw`Q`,
  Gd: String.raw`\boldsymbol\Gamma_{\text{diff}}`,
  aaH: String.raw`\bigl\langle\mathbf a\mathbf a^{H}\bigr\rangle_{\text{球面}}`,
  B: String.raw`B(\theta)=\mathbf w^{H}\mathbf a(\theta)`,
  W: String.raw`W`,
  DI: String.raw`\mathrm{DI}=10\log_{10}Q`,
  sq: String.raw`r_c\propto\sqrt{Q}`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('qfix.json', JSON.stringify(out));
fs.writeFileSync('qfix_inline.json', JSON.stringify(oi));
console.log('Q 的来历:', Object.keys(out).length, '行内:', Object.keys(oi).length);
