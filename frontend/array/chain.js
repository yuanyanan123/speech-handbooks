const katex=require('katex'), fs=require('fs');
const C={
 // ① 几何 → 相位
 geo2phase: String.raw`\tau_m(\theta)=-\frac{\mathbf r_m\cdot\mathbf u(\theta)}{c}
 \qquad\Longrightarrow\qquad
 a_m(\omega,\theta)=e^{-j\omega\tau_m(\theta)}`,
 stackvec: String.raw`\mathbf a(\omega,\theta)=
 \bigl[\,a_1,\;a_2,\;\dots,\;a_M\,\bigr]^{T}`,
 // ② 观测模型 —— 原来缺失的一环
 obs: String.raw`\underbrace{\mathbf x(\omega)}_{M\ \text{个麦的频谱}}
 =\underbrace{\mathbf a(\omega,\theta_s)\,s(\omega)}_{\text{目标：同一个声源，按导向矢量分布到各阵元}}
 +\underbrace{\mathbf n(\omega)}_{\text{噪声}}`,
 // ③ 波束输出 = 把观测模型代进去
 beamout: String.raw`y(\omega)=\mathbf w^{H}\mathbf x(\omega)
 =\underbrace{\mathbf w^{H}\mathbf a\;s(\omega)}_{\text{留下的目标}}
 \;+\;\underbrace{\mathbf w^{H}\mathbf n(\omega)}_{\text{残余噪声}}`,
 // ④ 两个设计目标自己长出来
 goals: String.raw`\underbrace{\mathbf w^{H}\mathbf a=1}_{\text{目标原样保留}}
 \qquad\qquad
 \underbrace{\min_{\mathbf w}\;\mathbf w^{H}\boldsymbol\Gamma\mathbf w}_{\text{残余噪声最小}}`,
 // 顺带给另外两处加上推出符号
 gcc2: String.raw`R_{12}(\tau)=\int\frac{X_1(\omega)X_2^{*}(\omega)}
 {\lvert X_1(\omega)X_2^{*}(\omega)\rvert}\,e^{j\omega\tau}\,d\omega
 \quad\Longrightarrow\quad
 \hat\tau=\arg\max_\tau R_{12}(\tau)
 \quad\Longrightarrow\quad
 \hat\theta=\arccos\frac{c\,\hat\tau}{d}`,
 dma2: String.raw`D(\theta)=A+(1-A)\cos\theta
 \qquad\Longrightarrow\qquad
 Q=\frac{D^{2}(0)}{\bigl\langle D^{2}(\theta)\bigr\rangle}
 =\frac{1}{A^{2}+\dfrac{(1-A)^{2}}{3}}`,
};
const out={};
for(const[k,v]of Object.entries(C))
  out[k]=katex.renderToString(v,{displayMode:true,throwOnError:true,strict:'ignore',output:'html'});
fs.writeFileSync('chain.json',JSON.stringify(out));
console.log('链条公式:',Object.keys(out).length);
