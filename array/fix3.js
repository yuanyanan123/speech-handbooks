// 三处补正推导：§02 Sabine、§04 二次型、§17 GEV
const katex=require('katex'), fs=require('fs');

const D={

// ── §04：输出功率为什么是二次型 ─────────────────────────────
q_out: String.raw`y(\omega)=\mathbf w^{H}\mathbf x
 =\underbrace{\mathbf w^{H}\mathbf a\,s(\omega)}_{\text{目标分量}}
 \;+\;\underbrace{\mathbf w^{H}\mathbf n(\omega)}_{\text{噪声分量}}`,

q_sig: String.raw`\underbrace{E\bigl[\lvert\mathbf w^{H}\mathbf a\,s\rvert^{2}\bigr]}_{\text{输出信号功率}}
 =\lvert\mathbf w^{H}\mathbf a\rvert^{2}\;\underbrace{E\bigl[\lvert s\rvert^{2}\bigr]}_{=\,S}`,

q_noise: String.raw`\begin{aligned}
 \underbrace{E\bigl[\lvert\mathbf w^{H}\mathbf n\rvert^{2}\bigr]}_{\text{输出噪声功率}}
 &\overset{(1)}{=}E\bigl[(\mathbf w^{H}\mathbf n)(\mathbf w^{H}\mathbf n)^{*}\bigr]
  \overset{(2)}{=}E\bigl[\mathbf w^{H}\mathbf n\,\mathbf n^{H}\mathbf w\bigr]\\[5pt]
 &\overset{(3)}{=}\mathbf w^{H}\,\underbrace{E\bigl[\mathbf n\mathbf n^{H}\bigr]}_{\textstyle =\,N\boldsymbol\Gamma}\,\mathbf w
  \;=\;\mathbf w^{H}\boldsymbol\Gamma\mathbf w\;\cdot N
 \end{aligned}`,

q_gam: String.raw`\boldsymbol\Gamma=\frac{1}{N}E\bigl[\mathbf n\mathbf n^{H}\bigr],
 \qquad
 \Gamma_{ij}=\frac{E\bigl[n_i n_j^{*}\bigr]}{N},
 \qquad
 \underbrace{\Gamma_{ii}=1}_{\text{对角线归一}}`,

// ── §02：Sabine 与 0.057 的来历 ────────────────────────────
sab_decay: String.raw`\begin{aligned}
 \text{扩散场能量衰减：}\quad E(t)&=E_0\,e^{-\frac{cA}{4V}t},
 \qquad A=S\bar\alpha\ (\text{总吸声量, m}^2)\\[5pt]
 \text{衰减 60 dB：}\quad \frac{cA}{4V}\,\mathrm{RT}_{60}&=\ln 10^{6}=6\ln 10\\[5pt]
 \Longrightarrow\quad \mathrm{RT}_{60}&=\frac{24\ln 10}{c}\cdot\frac{V}{A}
 =\frac{55.26}{343}\cdot\frac{V}{A}=\frac{0.161\,V}{A}
 \end{aligned}`,

sab_R: String.raw`\begin{aligned}
 \text{房间常数}\quad R&=\frac{S\bar\alpha}{1-\bar\alpha}=\frac{A}{1-\bar\alpha}
 \;\overset{\bar\alpha\,\ll\,1}{\approx}\;A
 \;=\;\frac{0.161\,V}{\mathrm{RT}_{60}}\\[6pt]
 \Longrightarrow\quad r_c&=\sqrt{\frac{Q\,R}{16\pi}}
 =\underbrace{\sqrt{\frac{0.161}{16\pi}}}_{=\,0.0566}\;\sqrt{\frac{Q\,V}{\mathrm{RT}_{60}}}
 \end{aligned}`,

// ── §17：GEV 是另一个问题 ─────────────────────────────────
gev_prob: String.raw`\max_{\mathbf w}\;\;
 \mathrm{SNR}_{\text{out}}(\mathbf w)
 =\frac{\mathbf w^{H}\mathbf R_{s}\mathbf w}{\mathbf w^{H}\mathbf R_{n}\mathbf w}
 \qquad\underbrace{\text{（没有约束）}}_{\text{和上面那个式子的分水岭}}`,

gev_scale: String.raw`\mathrm{SNR}_{\text{out}}(c\,\mathbf w)
 =\frac{\lvert c\rvert^{2}\,\mathbf w^{H}\mathbf R_{s}\mathbf w}
        {\lvert c\rvert^{2}\,\mathbf w^{H}\mathbf R_{n}\mathbf w}
 =\mathrm{SNR}_{\text{out}}(\mathbf w)
 \qquad\forall\,c\neq0`,

gev_solve: String.raw`\begin{aligned}
 \frac{\partial}{\partial\mathbf w^{*}}
 \frac{\mathbf w^{H}\mathbf R_{s}\mathbf w}{\mathbf w^{H}\mathbf R_{n}\mathbf w}
 &=\frac{(\mathbf w^{H}\mathbf R_{n}\mathbf w)\,\mathbf R_{s}\mathbf w
        -(\mathbf w^{H}\mathbf R_{s}\mathbf w)\,\mathbf R_{n}\mathbf w}
        {(\mathbf w^{H}\mathbf R_{n}\mathbf w)^{2}}=\mathbf 0\\[6pt]
 \Longrightarrow\quad
 \mathbf R_{s}\mathbf w&=\lambda\,\mathbf R_{n}\mathbf w,
 \qquad
 \lambda=\frac{\mathbf w^{H}\mathbf R_{s}\mathbf w}{\mathbf w^{H}\mathbf R_{n}\mathbf w}
 =\mathrm{SNR}_{\text{out}}
 \end{aligned}`,

gev_result: String.raw`\boxed{\;\mathbf w_{\text{GEV}}
 =\mathcal P\bigl\{\mathbf R_{n}^{-1}\mathbf R_{s}\bigr\}\;}
 \qquad
 \underbrace{\mathcal P\{\cdot\}=\text{最大特征值对应的特征向量}}_{\text{尺度、相位均不确定}}`,

gev_rank1: String.raw`\begin{aligned}
 \text{单点源}\;\Longrightarrow\;\mathbf R_{s}&=\phi_{s}\,\mathbf a\mathbf a^{H}
 \qquad(\text{秩 }1)\\[6pt]
 \mathbf R_{n}^{-1}\mathbf R_{s}\mathbf w
 &=\phi_{s}\,\mathbf R_{n}^{-1}\mathbf a\,
   \underbrace{\bigl(\mathbf a^{H}\mathbf w\bigr)}_{\text{标量}}
 \;=\;\lambda\,\mathbf w\\[6pt]
 \Longrightarrow\quad
 \mathbf w_{\text{GEV}}
 &=\underbrace{\frac{\phi_{s}\,\mathbf a^{H}\mathbf w}{\lambda}}_{\alpha\;\text{：任意复标量}}
   \;\mathbf R_{n}^{-1}\mathbf a
 \;=\;\alpha\,\mathbf R_{n}^{-1}\mathbf a
 \end{aligned}`,

gev_vs: String.raw`\underbrace{\mathbf w_{\text{GEV}}=\alpha\,\mathbf R_{n}^{-1}\mathbf a}_{\alpha\ \text{任意}}
 \qquad\Big\|\qquad
 \underbrace{\mathbf w_{\text{MVDR}}
 =\frac{\mathbf R_{n}^{-1}\mathbf a}{\mathbf a^{H}\mathbf R_{n}^{-1}\mathbf a}}
 _{\alpha\ \text{被无失真约束钉死}}`,

gev_lam: String.raw`\lambda_{\max}
 =\frac{\mathbf w^{H}\mathbf R_{s}\mathbf w}{\mathbf w^{H}\mathbf R_{n}\mathbf w}
 \bigg|_{\mathbf w=\alpha\mathbf R_{n}^{-1}\mathbf a}
 =\frac{\phi_{s}\lvert\alpha\rvert^{2}\bigl(\mathbf a^{H}\mathbf R_{n}^{-1}\mathbf a\bigr)^{2}}
        {\lvert\alpha\rvert^{2}\,\mathbf a^{H}\mathbf R_{n}^{-1}\mathbf a}
 =\phi_{s}\,\mathbf a^{H}\mathbf R_{n}^{-1}\mathbf a`,

ban: String.raw`\alpha_{\text{BAN}}
 =\frac{\sqrt{\mathbf w^{H}\mathbf R_{n}\mathbf R_{n}\mathbf w\,/\,M}}
        {\mathbf w^{H}\mathbf R_{n}\mathbf w}
 \qquad\text{(blind analytic normalization)}`,
};

const I={
  Rn1a: String.raw`\mathbf R_{n}^{-1}\mathbf a`,
  alpha: String.raw`\alpha`,
  lmax: String.raw`\lambda_{\max}`,
  phis: String.raw`\phi_{s}`,
  Abar: String.raw`A=S\bar\alpha`,
  abar: String.raw`\bar\alpha`,
  wgev: String.raw`\mathbf w_{\text{GEV}}`,
  wmvdr: String.raw`\mathbf w_{\text{MVDR}}`,
  nnH: String.raw`E[\mathbf n\mathbf n^{H}]`,
  wGw: String.raw`\mathbf w^{H}\boldsymbol\Gamma\mathbf w`,
};

const out={};
for(const[k,v]of Object.entries(D))
  out[k]=katex.renderToString(v,{displayMode:true,throwOnError:true,strict:'ignore',output:'html'});
const oi={};
for(const[k,v]of Object.entries(I))
  oi[k]=katex.renderToString(v,{displayMode:false,throwOnError:true,strict:'ignore',output:'html'});
fs.writeFileSync('fix3.json',JSON.stringify(out));
fs.writeFileSync('fix3_inline.json',JSON.stringify(oi));
console.log('补正推导:',Object.keys(out).length,' 行内:',Object.keys(oi).length);
