// §03：主瓣宽度与孔径下限的推导
const katex = require('katex'), fs = require('fs');
const D = {
ap_af: String.raw`B(\theta)=\frac{1}{M}\sum_{m=0}^{M-1}e^{\,jkdm\sin\theta}
 =\frac{1}{M}\cdot\frac{1-e^{\,jM\psi}}{1-e^{\,j\psi}}
 \;\Longrightarrow\;
 \lvert B\rvert=\Biggl\lvert\frac{\sin(M\psi/2)}{M\sin(\psi/2)}\Biggr\rvert,
 \quad \psi=kd\sin\theta`,

ap_null: String.raw`\frac{M\psi}{2}=\pi
 \;\Longrightarrow\;
 kd\,M\sin\theta_{\text{零}}=2\pi
 \;\Longrightarrow\;
 \boxed{\;\sin\theta_{\text{零}}=\frac{\lambda}{Md}=\frac{\lambda}{L}\;}`,

ap_bw: String.raw`\Biggl\lvert\frac{\sin(M\psi/2)}{M\sin(\psi/2)}\Biggr\rvert
 \;\xrightarrow[\;M\gg1\;]{}\;
 \Bigl\lvert\mathrm{sinc}\Bigl(\frac{M\psi}{2}\Bigr)\Bigr\rvert
 \quad\Longrightarrow\quad
 \boxed{\;\Delta\theta_{-3\,\mathrm{dB}}
 =2\arcsin\Bigl(0.443\,\frac{\lambda}{L}\Bigr)
 \;\underset{L\gg\lambda}{\approx}\;\frac{51^{\circ}}{L/\lambda}\;}`,

ap_di: String.raw`\mathrm{DI}_{\text{DAS}}
 =\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\boldsymbol\Gamma\mathbf w}
 \;\overset{\mathbf w=\mathbf a/M}{=}\;
 \frac{M^{2}}{\displaystyle\sum_{i,j}\mathrm{sinc}\bigl(k\lvert i-j\rvert d\bigr)}`,

ap_exp: String.raw`\mathrm{sinc}(x)=1-\frac{x^{2}}{6}+\cdots
 \quad\Longrightarrow\quad
 \sum_{i,j}\Gamma_{ij}\approx M^{2}-\frac{k^{2}d^{2}}{6}
 \underbrace{\sum_{i,j}(i-j)^{2}}_{\textstyle =\,M^{2}(M^{2}-1)/6}
 =M^{2}\Bigl[1-\frac{(kd)^{2}(M^{2}-1)}{36}\Bigr]`,

ap_res: String.raw`\boxed{\;\mathrm{DI}_{\text{DAS}}\;\approx\;1+\frac{(kd)^{2}(M^{2}-1)}{36}
 \;\underset{M\gg1}{=}\;1+\frac{(kL)^{2}}{36}\;,\qquad L\equiv Md\;}`,

ap_half: String.raw`\mathrm{DI}=1\ \text{dB}
 \;\Longrightarrow\;
 (kL)^{2}=36\bigl(10^{0.1}-1\bigr)
 \;\Longrightarrow\;
 kL=3.053
 \;\Longrightarrow\;
 \boxed{\;L=0.486\,\lambda\approx\frac{\lambda}{2}\;}`,
};
const I = {
  psi: String.raw`\psi=kd\sin\theta`,
  L: String.raw`L\equiv Md`,
  Lm: String.raw`L=(M-1)d`,
  kL: String.raw`kL=2\pi L/\lambda`,
};
const out={},oi={};
for(const[k,v]of Object.entries(D))out[k]=katex.renderToString(v,{displayMode:true,throwOnError:true,strict:'ignore',output:'html'});
for(const[k,v]of Object.entries(I))oi[k]=katex.renderToString(v,{displayMode:false,throwOnError:true,strict:'ignore',output:'html'});
fs.writeFileSync('ap.json',JSON.stringify(out));fs.writeFileSync('ap_inline.json',JSON.stringify(oi));
console.log('孔径:',Object.keys(out).length,'行内:',Object.keys(oi).length);
