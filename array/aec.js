// §14 AEC 在阵列里放哪：把"波束一动 AEC 就废"推成一个式子
const katex = require('katex'), fs = require('fs');
const A = JSON.parse(fs.readFileSync('demo_aec.json', 'utf8'));
const r = (x, n) => Number(x).toFixed(n);

const D = {
// ① 波束后面的 AEC 看到的是什么
aec_geff: String.raw`y_t=\sum_{m}w_m^{*}x_{m,t}
 \quad\Longrightarrow\quad
 \underbrace{g^{\mathrm{eff}}[n]=\sum_{m=1}^{M}w_m^{*}\,g_m[n]}
 _{\textstyle \text{AEC 要辨识的"那一条"回声路径}}
 \qquad
 \underbrace{w\ \text{一变，}g^{\mathrm{eff}}\ \text{就是另一条路径}}
 _{\textstyle \text{这就是 B 方案的全部问题}}`,

// ② 换路径之后，旧滤波器还剩多少本事
aec_res: String.raw`\begin{aligned}
 \hat h&=g_1\quad(\text{AEC 已在旧波束上收敛})\\[4pt]
 e_t&=\underbrace{(g_2*u)_t}_{\text{新回声}}-\underbrace{(\hat h*u)_t}_{\text{按旧路径消}}
 =\bigl((g_2-g_1)*u\bigr)_t
 \end{aligned}`,

aec_erle: String.raw`\mathbb E\lvert e_t\rvert^{2}=\sigma_u^{2}\lVert g_2-g_1\rVert^{2}
 \;\Longrightarrow\;
 \boxed{\;\mathrm{ERLE}_{\max}=-20\log_{10}\frac{\lVert g_2-g_1\rVert}{\lVert g_2\rVert}\;}
 \qquad
 \underbrace{\text{与 AEC 用什么算法无关}}_{\textstyle \text{它是路径本身给的上限}}`,

// ③ 代入 5° 那一档
aec_num: String.raw`\begin{aligned}
 60^{\circ}\to65^{\circ}:\quad
 \frac{\lVert g_2-g_1\rVert}{\lVert g_2\rVert}&=10^{-${r(A.dth['5'], 2)}/20}
 =${r(Math.pow(10, -A.dth['5'] / 20), 4)}\\[6pt]
 \mathrm{ERLE}_{\max}&=${r(A.dth['5'], 2)}\ \text{dB}
 \qquad
 \underbrace{\text{实测 }${r(A.nlms.var_inst, 2)}\ \text{dB}}
 _{\textstyle \text{跳变后头 50 ms}}
 \end{aligned}`,

// ④ 权重只动了一点点
aec_phase: String.raw`\underbrace{\frac{\lVert w_2-w_1\rVert}{\lVert w_1\rVert}
 =${r(A.wrel['1.0'] * 100, 1)}\%}_{\textstyle \theta:60^{\circ}\to61^{\circ}\ \text{时权重的变化}}
 \qquad\Longrightarrow\qquad
 \underbrace{\mathrm{ERLE}_{\max}=${r(A.dth['1'], 1)}\ \text{dB}}
 _{\textstyle \approx-20\log_{10}${r(A.wrel['1.0'], 3)}=${r(-20 * Math.log10(A.wrel['1.0']), 1)}\ \text{dB}}`,
};

const I = {
  geff: String.raw`g^{\mathrm{eff}}`,
  gd: String.raw`\lVert g_2-g_1\rVert`,
  erm: String.raw`\mathrm{ERLE}_{\max}`,
  w: String.raw`w`,
  th5: String.raw`60^{\circ}\!\to\!65^{\circ}`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D)) out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I)) oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('aec.json', JSON.stringify(out));
fs.writeFileSync('aec_inline.json', JSON.stringify(oi));
console.log('AEC:', Object.keys(out).length, '行内:', Object.keys(oi).length);
