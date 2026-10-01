// §19 多说话人：W-disjoint、CACGMM、GSS 的先验、rank-1 与 GEV
const katex = require('katex'), fs = require('fs');
const D = JSON.parse(fs.readFileSync('demo_sep.json', 'utf8'));
const r = (x, n) => Number(x).toFixed(n);

const Dm = {
// ① W-disjoint：分离这件事凭什么在时频域成立
sep_wdo: String.raw`\underbrace{S_A(t,f)\,S_B(t,f)\approx0\ \ \forall (t,f)}
 _{\textstyle \text{W-disjoint orthogonality}}
 \;\Longrightarrow\;
 \underbrace{m^{\mathrm{IBM}}(t,f)=\mathbb 1\bigl[\lvert S_A\rvert>\lvert S_B\rvert\bigr]}
 _{\textstyle \text{一刀切就够了}}
 \qquad
 \underbrace{${r(D.wdo['6'], 1)}\%}_{\textstyle \text{实测领先 }6\,\text{dB 的格子}}`,

// ② 复角中心高斯：为什么只看方向、不看幅度
sep_cacg: String.raw`\mathbf z_{tf}=\frac{\mathbf x_{tf}}{\lVert\mathbf x_{tf}\rVert}
 \qquad
 p(\mathbf z\mid \mathbf B_k)=\frac{(M-1)!}{\pi^{M}\det\mathbf B_k}
 \cdot\frac{1}{\bigl(\mathbf z^{H}\mathbf B_k^{-1}\mathbf z\bigr)^{M}}
 \qquad
 \underbrace{\text{对 }\mathbf z\to e^{j\phi}\mathbf z\ \text{不变}}
 _{\textstyle \text{所以它只描述"方向"}}`,

// ③ EM 的两步
sep_em: String.raw`\begin{aligned}
 \text{E：}\quad \gamma_{tfk}&\propto\pi_k\,p(\mathbf z_{tf}\mid\mathbf B_{kf})\\[4pt]
 \text{M：}\quad \mathbf B_{kf}&=\frac{M}{\sum_t\gamma_{tfk}}
 \sum_t\gamma_{tfk}\frac{\mathbf z_{tf}\mathbf z_{tf}^{H}}
 {\mathbf z_{tf}^{H}\mathbf B_{kf}^{-1}\mathbf z_{tf}}
 \end{aligned}
 \qquad
 \underbrace{\text{每个 }f\ \text{各跑各的}}_{\textstyle k\ \text{的编号对不上}}`,

// ④ GSS：先验乘进去，排列就被钉死了
sep_gss: String.raw`\gamma_{tfk}\;\propto\;
 \underbrace{\pi_k\,p(\mathbf z_{tf}\mid\mathbf B_{kf})}_{\textstyle \text{空间证据，每个 }f\ \text{独立}}
 \;\times\;
 \underbrace{q_k(t)}_{\textstyle \substack{\text{diarization 给的时间先验}\\ \text{对所有 }f\ \text{是同一份}}}
 \qquad\Longrightarrow\qquad
 \underbrace{k\ \text{在所有频率上指同一个人}}_{\textstyle \text{这就是 GSS 的全部}}`,

// ⑤ rank-1 在混响里站不住
sep_rank1: String.raw`\mathbf R_s=\mathbb E\bigl[\mathbf x_s\mathbf x_s^{H}\bigr]
 \;\overset{?}{=}\;\sigma^{2}\mathbf a\mathbf a^{H}
 \qquad
 \underbrace{\frac{\lambda_1}{\lambda_1+\lambda_2+\lambda_3+\lambda_4}=${r(D.rank1_frac, 0)}\%}
 _{\textstyle \text{实测：第一特征值只占这么点}}
 \qquad
 \underbrace{\text{剩下 }${r(100 - D.rank1_frac, 0)}\%\ \text{是混响}}
 _{\textstyle \mathbf a\ \text{表示不了它}}`,

sep_gev: String.raw`\underbrace{\mathbf w_{\mathrm{MVDR}}
 =\frac{\mathbf R_n^{-1}\mathbf a}{\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}}
 _{\textstyle \text{只用 }\mathbf R_s\ \text{的主特征向量}}
 \qquad\text{vs.}\qquad
 \underbrace{\mathbf w_{\mathrm{GEV}}=\arg\max_{\mathbf w}
 \frac{\mathbf w^{H}\mathbf R_s\mathbf w}{\mathbf w^{H}\mathbf R_n\mathbf w}}
 _{\textstyle \mathbf R_s\ \text{整个都用上}}
 \qquad
 \underbrace{${r(D.oracle_r1, 2)}\to${r(D.oracle_gev, 2)}\ \text{dB}}
 _{\textstyle \text{同一份神仙协方差}}`,
};

const I = {
  z: String.raw`\mathbf z_{tf}`,
  B: String.raw`\mathbf B_{kf}`,
  q: String.raw`q_k(t)`,
  gam: String.raw`\gamma_{tfk}`,
  Rs: String.raw`\mathbf R_s`,
  a: String.raw`\mathbf a`,
  wdo6: String.raw`${r(D.wdo['6'], 1)}\%`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(Dm)) out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I)) oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('sep.json', JSON.stringify(out));
fs.writeFileSync('sep_inline.json', JSON.stringify(oi));
console.log('SEP:', Object.keys(out).length, '行内:', Object.keys(oi).length);
