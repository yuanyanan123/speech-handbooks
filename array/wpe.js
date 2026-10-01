// §15 WPE：为什么多通道线性预测能去晚期混响
const katex = require('katex'), fs = require('fs');
const D = {
wpe_split: String.raw`\mathbf x_t=\underbrace{\sum_{\tau=0}^{\Delta-1}\mathbf h_\tau s_{t-\tau}}
 _{\textstyle \mathbf d_t\ \text{：直达 + 早期，要留}}
 \;+\;\underbrace{\sum_{\tau=\Delta}^{L_h}\mathbf h_\tau s_{t-\tau}}
 _{\textstyle \text{晚期混响，要去}}`,

wpe_key: String.raw`\underbrace{\sum_{\tau\ge\Delta}\mathbf h_\tau s_{t-\tau}}_{\text{未知的 }s}
 \;=\;\underbrace{\sum_{k=0}^{K-1}\mathbf G_k^{H}\,\mathbf x_{t-\Delta-k}}_{\text{只用观测到的 }\mathbf x}
 \qquad\underbrace{\Longleftarrow\ \ \{H_m(z)\}\ \text{无公共零点}}_{\textstyle M\ge2\ \text{时一般成立（Bezout）}}`,

wpe_pred: String.raw`\boxed{\;\mathbf d_t=\mathbf x_t-\sum_{k=0}^{K-1}\mathbf G_k^{H}\mathbf x_{t-\Delta-k}\;}
 \qquad\underbrace{\text{没有出现 }\mathbf h\ \text{，也没有出现 }s}_{\textstyle \text{"不需要知道房间冲激响应"的确切含义}}`,

wpe_ml: String.raw`s_t\sim\mathcal{CN}\bigl(0,\lambda_t\bigr)
 \;\Longrightarrow\;
 -\log p=\sum_t\Bigl[\,M\log\lambda_t
 +\frac{\lVert\mathbf d_t\rVert^{2}}{\lambda_t}\Bigr]`,

wpe_lam: String.raw`\frac{\partial}{\partial\lambda_t}=0
 \;\Longrightarrow\;
 \hat\lambda_t=\frac{1}{M}\bigl\lVert\mathbf d_t\bigr\rVert^{2}
 \qquad\qquad
 \underbrace{\text{给定 }\lambda\text{，对 }\mathbf G\text{ 是加权最小二乘}}
 _{\textstyle \text{权重 }1/\lambda_t}`,

wpe_G: String.raw`\mathbf G=\Bigl(\sum_t\frac{\bar{\mathbf x}_t\bar{\mathbf x}_t^{H}}{\lambda_t}\Bigr)^{-1}
 \Bigl(\sum_t\frac{\bar{\mathbf x}_t\mathbf x_t^{H}}{\lambda_t}\Bigr)
 \qquad
 \bar{\mathbf x}_t=\bigl[\mathbf x_{t-\Delta}^{T},\dots,\mathbf x_{t-\Delta-K+1}^{T}\bigr]^{T}`,
};
const I = {
  Dl: String.raw`\Delta`,
  lam: String.raw`\lambda_t`,
  w1: String.raw`1/\lambda_t`,
  G: String.raw`\mathbf G_k`,
  d: String.raw`\mathbf d_t`,
  M2: String.raw`M\ge2`,
};
const out={},oi={};
for(const[k,v]of Object.entries(D))out[k]=katex.renderToString(v,{displayMode:true,throwOnError:true,strict:'ignore',output:'html'});
for(const[k,v]of Object.entries(I))oi[k]=katex.renderToString(v,{displayMode:false,throwOnError:true,strict:'ignore',output:'html'});
fs.writeFileSync('wpe.json',JSON.stringify(out));fs.writeFileSync('wpe_inline.json',JSON.stringify(oi));
console.log('WPE:',Object.keys(out).length,'行内:',Object.keys(oi).length);
