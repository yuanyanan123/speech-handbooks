// 附录公式表新增行
const katex = require('katex'), fs = require('fs');
const D = {
  bnS:    String.raw`b_n(kr)=4\pi j^{\,n}j_n(kr)`,
  bnrS:   String.raw`b_n^{\text{rigid}}=\dfrac{4\pi j^{\,n+1}}{(kr)^{2}h_n'(kr)}`,
  sftS:   String.raw`p_{nm}=\dfrac{4\pi}{Q}\sum_q p(\mathbf u_q)Y_n^{m*}(\mathbf u_q)`,
  shbS:   String.raw`y=\sum_{n\le N}\dfrac{c_n}{b_n}\sum_m p_{nm}Y_n^{m}(\hat{\mathbf u}_0)`,
  shdiS:  String.raw`\mathrm{DI}_{\max}=(N+1)^{2}`,
  shwngS: String.raw`\mathrm{WNG}=\dfrac{Q(N+1)^{4}}{(4\pi)^{2}\sum_n\frac{2n+1}{|b_n|^{2}}}`,
  shlimS: String.raw`Q\ge(N+1)^{2},\qquad kr\lesssim N`,
  itdS:   String.raw`\tau=\dfrac{a}{c}(\theta+\sin\theta)`,
  itdlS:  String.raw`\tau_{ka\ll1}=\dfrac{3a}{c}\sin\theta,\quad \tau_{ka\gg1}=\dfrac{2a}{c}\sin\theta`,
  bmvdrS: String.raw`\mathbf w_L=a_L^{*}\dfrac{\mathbf R_n^{-1}\mathbf a}{\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}`,
  mwfnS:  String.raw`y_L=(1-\eta)\mathbf w_L^{H}\mathbf x+\eta\,x_L`,
  banS:   String.raw`\alpha_{\text{BAN}}=\dfrac{\sqrt{\mathbf w^{H}\mathbf R_n\mathbf R_n\mathbf w/M}}{\mathbf w^{H}\mathbf R_n\mathbf w}`,
  gevS2:  String.raw`\mathbf R_s\mathbf w=\lambda\mathbf R_n\mathbf w,\;\;\lambda=\mathrm{SNR}_{\text{out}}`,
  quadS:  String.raw`E[|\mathbf w^{H}\mathbf n|^{2}]=\mathbf w^{H}\boldsymbol\Gamma\mathbf w\,N`,
  sabS:   String.raw`\mathrm{RT}_{60}=\dfrac{24\ln10}{c}\cdot\dfrac{V}{A}=\dfrac{0.161V}{A}`,
};
const out = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('append.json', JSON.stringify(out));
console.log('附录公式:', Object.keys(out).length);
