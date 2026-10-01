// §01 两处断链要补的公式
const katex = require('katex'), fs = require('fs');

const D = {
// ── 断链一：从 w^H n 到 w^H Γ w ─────────────────────────────
npow: String.raw`\underbrace{E\bigl[\lvert\mathbf w^{H}\mathbf n\rvert^{2}\bigr]}_{\text{残余噪声的平均功率}}
 \;\overset{(*)}{=}\;E\bigl[\mathbf w^{H}\mathbf n\,\mathbf n^{H}\mathbf w\bigr]
 \;=\;\mathbf w^{H}\underbrace{E\bigl[\mathbf n\mathbf n^{H}\bigr]}_{\textstyle =\,N\boldsymbol\Gamma}\mathbf w
 \;=\;N\cdot\mathbf w^{H}\boldsymbol\Gamma\mathbf w`,

gamdef: String.raw`\boldsymbol\Gamma\;\overset{\text{定义}}{=}\;\frac{1}{N}E\bigl[\mathbf n\mathbf n^{H}\bigr]
 \qquad\Longrightarrow\qquad
 \Gamma_{ij}=\frac{E\bigl[n_i n_j^{*}\bigr]}{N}
 \qquad
 \underbrace{\Gamma_{ii}=1}_{\text{对角线恒为 }1}`,

// ── 断链二：从"扩散场"这个模型到 ⟨e^{jkd cosθ}⟩ ──────────────
dmodel: String.raw`\begin{aligned}
 \text{扩散场的定义：}\quad
 \mathbf n&=\sum_{\ell}A_\ell\,\mathbf a(\theta_\ell),
 \qquad
 \underbrace{E\bigl[A_\ell A_{\ell'}^{*}\bigr]=\sigma^{2}\,\delta_{\ell\ell'}}
 _{\text{各方向互不相关、功率相同}}\\[8pt]
 \Longrightarrow\quad
 E\bigl[n_1 n_2^{*}\bigr]
 &=\sum_{\ell}\underbrace{E\bigl[\lvert A_\ell\rvert^{2}\bigr]}_{\sigma^{2}}\,
   e^{\,jkd\cos\theta_\ell}
 \qquad\underbrace{(\text{交叉项全为 }0)}_{\ell\neq\ell'\ \text{不相关}}\\[8pt]
 \Longrightarrow\quad
 \Gamma_{12}&=\frac{E[n_1n_2^{*}]}{N}
 =\bigl\langle e^{\,jkd\cos\theta}\bigr\rangle_{\text{所有方向}}
 \end{aligned}`,

solid: String.raw`\bigl\langle f\bigr\rangle_{\text{球面}}
 =\frac{1}{4\pi}\oint f\,d\Omega,
 \qquad
 \underbrace{d\Omega=\sin\theta\,d\theta\,d\varphi}_{\text{立体角元}},
 \qquad
 \underbrace{\oint d\Omega=4\pi}_{\text{所以除以 }4\pi}`,
};

const I = {
  wn: String.raw`\mathbf w^{H}\mathbf n`,
  wGw: String.raw`\mathbf w^{H}\boldsymbol\Gamma\mathbf w`,
  Gam: String.raw`\boldsymbol\Gamma`,
  G12: String.raw`\Gamma_{12}`,
  sinth: String.raw`\sin\theta`,
  dOm: String.raw`d\Omega`,
  Al: String.raw`A_\ell`,
  costh: String.raw`\cos\theta`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('s01fix.json', JSON.stringify(out));
fs.writeFileSync('s01fix_inline.json', JSON.stringify(oi));
console.log('§01 补链公式:', Object.keys(out).length, '行内:', Object.keys(oi).length);
