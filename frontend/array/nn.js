// §20 神经前端：掩码进到哪一步，决定了它错了会怎样
const katex = require('katex'), fs = require('fs');
const N = JSON.parse(fs.readFileSync('demo_nn.json', 'utf8'));
const r = (x, n) => Number(x).toFixed(n);

const D = {
// ① 两条路：掩码出现在什么位置
nn_two: String.raw`\begin{aligned}
 \text{直接乘：}\quad \hat y_{tf}&=\hat m_{tf}\cdot x_{tf}
 &&\underbrace{\text{每个格子各用各的增益}}_{\textstyle \text{时变 → 非线性}}\\[8pt]
 \text{mask-based 波束：}\quad \hat y_{tf}&=\mathbf w_f^{H}(\hat m)\,\mathbf x_{tf}
 &&\underbrace{\text{整段只有一个 }\mathbf w_f}_{\textstyle \text{线性时不变}}
 \end{aligned}`,

// ② 掩码在波束里只是一个求和的权重
nn_cov: String.raw`\hat{\mathbf R}_s(f)=\frac{\sum_{t}\hat m_{tf}\,\mathbf x_{tf}\mathbf x_{tf}^{H}}
 {\sum_{t}\hat m_{tf}}
 \qquad
 \underbrace{T=${N.T}\ \text{帧}}_{\textstyle \hat m\ \text{只以"权重"的身份出现，不直接乘到输出上}}`,

// ③ 掩码只通过两条路影响波束
nn_path: String.raw`\hat m\;\longrightarrow\;
 \begin{cases}
 \ \mathbf a=\text{主特征向量}\bigl(\hat{\mathbf R}_s\bigr)
 &\underbrace{\text{决定"保谁"}}_{\textstyle \text{几乎不动}}\\[10pt]
 \ \hat{\mathbf R}_n
 &\underbrace{\text{决定"零点放哪"}}_{\textstyle \text{动了也不太亏}}
 \end{cases}`,

// ④ 主特征向量为什么这么稳
nn_steer: String.raw`\cos\angle\bigl(\mathbf a(\hat m),\ \mathbf a(m^{\mathrm{IRM}})\bigr)
 =\begin{cases}
 ${r(N.steer.cos['0.5'], 4)} & \hat m\ \text{一半是随机数}\\[3pt]
 ${r(N.steer.cos['1.0'], 4)} & \hat m\ \text{完全是随机数}\\[3pt]
 ${r(N.steer.adv, 4)} & \hat m\leftarrow 1-m\ \text{（整个反过来）}
 \end{cases}
 \qquad
 \underbrace{\text{能量最强的方向不随加权改变}}
 _{\textstyle \text{只要加权不是对抗性的}}`,

// ⑤ 无失真约束：掩码怎么错都动不了它
nn_why: String.raw`\mathbf w^{H}\mathbf a=1\quad\forall\,\hat m
 \qquad
 \underbrace{\text{约束本身与掩码无关}}_{\textstyle \text{目标被钉住了}}
 \qquad\text{vs.}\qquad
 \underbrace{\mathbf w_{\mathrm{GEV}}=\arg\max
 \frac{\mathbf w^{H}\hat{\mathbf R}_s\mathbf w}{\mathbf w^{H}\hat{\mathbf R}_n\mathbf w}}
 _{\textstyle \substack{\text{方向完全由 }\hat m\ \text{决定，}\\ \text{没有任何东西钉住目标}}}`,

// ⑥ 边界在哪：对抗性的错法
nn_adv: String.raw`\hat m=1-m^{\mathrm{IRM}}
 \;\Longrightarrow\;
 \hat{\mathbf R}_n\approx\mathbf R_s
 \;\Longrightarrow\;
 \underbrace{\text{波束开始往目标上放零点}}_{\textstyle \text{SNR }${r(N.adv_mvdr[0], 2)}\ \text{dB}}
 \qquad
 \underbrace{\text{但失真仍有 }${r(N.adv_mvdr[1], 2)}\ \text{dB}}
 _{\textstyle \mathbf w^{H}\mathbf a=1\ \text{不让它消干净}}`,
};

const I = {
  m: String.raw`\hat m_{tf}`,
  cos1: String.raw`\cos=${r(N.steer.cos['1.0'], 4)}`,
  w: String.raw`\mathbf w_f`,
  T: String.raw`T=${N.T}`,
  Rs: String.raw`\hat{\mathbf R}_s`,
  c1: String.raw`\mathbf w^{H}\mathbf a=1`,
};

const out = {}, oi = {};
for (const [k, v] of Object.entries(D)) out[k] = katex.renderToString(v, { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I)) oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('nn.json', JSON.stringify(out));
fs.writeFileSync('nn_inline.json', JSON.stringify(oi));
console.log('NN:', Object.keys(out).length, '行内:', Object.keys(oi).length);
