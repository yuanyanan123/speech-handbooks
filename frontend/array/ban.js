// §17：BAN 的推导 + 目标抵消的真正机理
const katex = require('katex'), fs = require('fs');
const D = {
ban_want: String.raw`\text{想要的是 MVDR 的那个归一化：}\quad
 \alpha_{\star}=\frac{1}{\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}
 \qquad\underbrace{\text{可是 }\mathbf a\text{ 不知道}}_{\text{GEV 的前提就是没有 }\mathbf a}`,

ban_id: String.raw`\mathbf w=\mathbf R_n^{-1}\mathbf a
 \quad\Longrightarrow\quad
 \underbrace{\mathbf w^{H}\mathbf R_n\mathbf w=\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}_{\textstyle \text{分母，正是要的那个数}}
 \qquad
 \underbrace{\mathbf w^{H}\mathbf R_n\mathbf R_n\mathbf w=\mathbf a^{H}\mathbf a=M}
 _{\textstyle \text{分子，}\ \lvert a_m\rvert=1\ \text{时恒为 }M}`,

ban_res: String.raw`\boxed{\;\alpha_{\text{BAN}}
 =\frac{\sqrt{\mathbf w^{H}\mathbf R_n\mathbf R_n\mathbf w\,/\,M}}{\mathbf w^{H}\mathbf R_n\mathbf w}
 \;=\;\frac{\sqrt{M/M}}{\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}
 \;=\;\frac{1}{\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}=\alpha_{\star}\;}`,

ban_scale: String.raw`\mathbf w=c\,\mathbf R_n^{-1}\mathbf a
 \;\Longrightarrow\;
 \alpha_{\text{BAN}}\mathbf w
 =\frac{\lvert c\rvert}{\lvert c\rvert^{2}\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}\,c\,\mathbf R_n^{-1}\mathbf a
 =\underbrace{e^{\,j\angle c}}_{\textstyle \text{剩下的相位}}\cdot\,\mathbf w_{\text{MVDR}}`,

canc_lemma: String.raw`\bigl(\mathbf R_n+\phi_s\mathbf a\mathbf a^{H}\bigr)^{-1}\mathbf a
 =\mathbf R_n^{-1}\mathbf a-\frac{\phi_s\,\mathbf R_n^{-1}\mathbf a\,\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}
 {1+\phi_s\,\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}
 =\underbrace{\frac{\mathbf R_n^{-1}\mathbf a}{1+\phi_s\,\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}}
 _{\textstyle \text{只差一个实数因子}}`,

canc_res: String.raw`\mathbf w=\frac{\bigl(\mathbf R_n+\phi_s\mathbf a\mathbf a^{H}\bigr)^{-1}\mathbf a}
 {\mathbf a^{H}\bigl(\mathbf R_n+\phi_s\mathbf a\mathbf a^{H}\bigr)^{-1}\mathbf a}
 \;=\;\frac{\mathbf R_n^{-1}\mathbf a}{\mathbf a^{H}\mathbf R_n^{-1}\mathbf a}
 \qquad\underbrace{\text{与 }\phi_s\text{ 完全无关}}_{\textstyle \mathbf a\ \text{精确时，目标进 }\mathbf R_n\ \text{无害}}`,

canc_bad: String.raw`\tilde{\mathbf a}\neq\mathbf a
 \;\Longrightarrow\;
 \tilde{\mathbf a}^{H}\mathbf a\neq\lVert\mathbf a\rVert^{2}
 \;\Longrightarrow\;
 \underbrace{\mathbf a\mathbf a^{H}\ \text{对 }\tilde{\mathbf a}\ \text{不再"透明"}}
 _{\textstyle \phi_s\ \text{越大，这条零点越深}}`,
};
const I = {
  al: String.raw`\alpha`,
  aR: String.raw`\mathbf a^{H}\mathbf R_n^{-1}\mathbf a`,
  w: String.raw`\mathbf w=\mathbf R_n^{-1}\mathbf a`,
  c: String.raw`c`,
  at: String.raw`\tilde{\mathbf a}`,
  phis: String.raw`\phi_s`,
  Rs1: String.raw`\mathbf R_s=\phi_s\mathbf a\mathbf a^{H}`,
};
const out={},oi={};
for(const[k,v]of Object.entries(D))out[k]=katex.renderToString(v,{displayMode:true,throwOnError:true,strict:'ignore',output:'html'});
for(const[k,v]of Object.entries(I))oi[k]=katex.renderToString(v,{displayMode:false,throwOnError:true,strict:'ignore',output:'html'});
fs.writeFileSync('ban.json',JSON.stringify(out));fs.writeFileSync('ban_inline.json',JSON.stringify(oi));
console.log('BAN:',Object.keys(out).length,'行内:',Object.keys(oi).length);
