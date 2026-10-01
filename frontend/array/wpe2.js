// §15 算例：WPE 在 12 节那间真实房间里的实测
const katex = require('katex'), fs = require('fs');
const W = JSON.parse(fs.readFileSync('demo_wpe.json', 'utf8'));
const r = (x, n) => Number(x).toFixed(n);

const D = {
// 用来打分的那个量：尺度无关的"早期/晚期"比
wpe_srr: String.raw`\mathrm{SRR}=10\log_{10}
 \frac{\lVert \alpha\,\mathbf r\rVert^{2}}{\lVert \mathbf y-\alpha\,\mathbf r\rVert^{2}},
 \qquad
 \alpha=\frac{\langle \mathbf r,\mathbf y\rangle}{\langle \mathbf r,\mathbf r\rangle}
 \qquad
 \underbrace{\mathbf r=\text{只卷早期 RIR 的参考}}
 _{\textstyle \text{先投影再算残差，所以与整体增益无关}}`,

// Δ 为什么不能取 0
wpe_why0: String.raw`\Delta=0\ \Longrightarrow\ \bar{\mathbf x}_t\ \text{里含 }\mathbf x_t\ \text{本身}
 \;\Longrightarrow\;
 \underbrace{\mathbf d_t\to\mathbf 0}_{\textstyle \text{把目标一起预测掉}}
 \qquad
 \underbrace{${r(W.delay['0'], 1)}\ \text{dB}}_{\textstyle \text{实测}}
 \;\ll\;
 \underbrace{${r(W['in'], 2)}\ \text{dB}}_{\textstyle \text{完全不处理}}`,

// 最优 Δ 与早期窗的对应
wpe_dmatch: String.raw`\Delta^{\star}\cdot\frac{H}{f_s}
 =${W.best_delay}\times\frac{256}{16000}
 =${r(W.best_delay * 256 / 16000 * 1000, 0)}\ \text{ms}
 \qquad\approx\qquad
 \underbrace{50\ \text{ms}}_{\textstyle \text{定义"早期"的那条线}}
 \qquad
 \underbrace{\text{不是巧合}}_{\textstyle \Delta\ \text{就是"从哪儿开始算晚期"}}`,

// 加权买到的是什么
wpe_gain: String.raw`\begin{aligned}
 \Delta=1:&\quad ${r(W.delay['1'], 2)}\;-\;(${r(W.unw_delay['1'], 2)})
 \;=\;\mathbf{${r(W.delay['1'] - W.unw_delay['1'], 2)}}\ \text{dB}\\[4pt]
 \Delta=3:&\quad ${r(W.delay['3'], 2)}\;-\;${r(W.unw_delay['3'], 2)}
 \;=\;\mathbf{${r(W.delay['3'] - W.unw_delay['3'], 2)}}\ \text{dB}\\[4pt]
 \Delta=4:&\quad ${r(W.delay['4'], 2)}\;-\;${r(W.unw_delay['4'], 2)}
 \;=\;\mathbf{${r(W.delay['4'] - W.unw_delay['4'], 2)}}\ \text{dB}
 \end{aligned}
 \qquad
 \underbrace{\text{加权的价值随 }\Delta\ \text{增大而消失}}
 _{\textstyle \text{它买的是"敢用短延迟"}}`,
};

const I = {
  Ds: String.raw`\Delta^{\star}=${W.best_delay}`,
  Ks: String.raw`K=${W.best_taps}`,
  srr: String.raw`\mathrm{SRR}`,
  gain: String.raw`+${r(W.best - W['in'], 2)}\ \text{dB}`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D)) out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I)) oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('wpe2.json', JSON.stringify(out));
fs.writeFileSync('wpe2_inline.json', JSON.stringify(oi));
console.log('WPE2:', Object.keys(out).length, '行内:', Object.keys(oi).length);
