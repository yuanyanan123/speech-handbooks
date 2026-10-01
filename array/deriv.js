const katex=require('katex'), fs=require('fs');
const D={
 // 阵列增益的统一定义
 gaindef: String.raw`G(\omega)=\frac{\mathrm{SNR}_{\text{out}}}{\mathrm{SNR}_{\text{in}}}
 =\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}\,S\;/\;\mathbf w^{H}\boldsymbol\Gamma\mathbf w\,N}{S/N}
 =\frac{\lvert\mathbf w^{H}\mathbf a\rvert^{2}}{\mathbf w^{H}\boldsymbol\Gamma\mathbf w}`,
 gainswap: String.raw`\boldsymbol\Gamma=\boldsymbol\Gamma_{\text{diff}}\;\Rightarrow\;\mathrm{DI}
 \qquad\qquad
 \boldsymbol\Gamma=\mathbf I\;\Rightarrow\;\mathrm{WNG}`,
 // 扩散场相干的推导
 cohderiv: String.raw`\begin{aligned}
 \Gamma_{12}&=\bigl\langle e^{\,jkd\cos\theta}\bigr\rangle_{\text{球面}}
 =\frac{1}{4\pi}\int_{0}^{2\pi}\!\!\int_{0}^{\pi} e^{\,jkd\cos\theta}\sin\theta\,d\theta\,d\varphi\\[4pt]
 &\overset{u=\cos\theta}{=}\frac{1}{2}\int_{-1}^{1} e^{\,jkdu}\,du
 =\frac{1}{2}\cdot\frac{e^{\,jkd}-e^{-jkd}}{jkd}
 =\frac{\sin(kd)}{kd}
 \end{aligned}`,
 // 拉格朗日主推导
 lagprob: String.raw`\min_{\mathbf w}\;\mathbf w^{H}\boldsymbol\Gamma\mathbf w
 \qquad\text{s.t.}\qquad \mathbf w^{H}\mathbf a=1`,
 lagsolve: String.raw`\begin{aligned}
 \mathcal L&=\mathbf w^{H}\boldsymbol\Gamma\mathbf w-\lambda\bigl(\mathbf w^{H}\mathbf a-1\bigr)\\[3pt]
 \frac{\partial\mathcal L}{\partial\mathbf w^{*}}&=\boldsymbol\Gamma\mathbf w-\lambda\mathbf a=0
 \;\Longrightarrow\;\mathbf w=\lambda\,\boldsymbol\Gamma^{-1}\mathbf a\\[3pt]
 \text{代回约束：}\;&\lambda\,\mathbf a^{H}\boldsymbol\Gamma^{-1}\mathbf a=1
 \;\Longrightarrow\;\lambda=\frac{1}{\mathbf a^{H}\boldsymbol\Gamma^{-1}\mathbf a}
 \end{aligned}`,
 lagresult: String.raw`\boxed{\;\mathbf w=\frac{\boldsymbol\Gamma^{-1}\mathbf a}
 {\mathbf a^{H}\boldsymbol\Gamma^{-1}\mathbf a}\;}`,
 dasspecial: String.raw`\boldsymbol\Gamma=\mathbf I\;\Rightarrow\;
 \mathbf w=\frac{\mathbf a}{\mathbf a^{H}\mathbf a}=\frac{\mathbf a}{M}`,
 // 对角加载的来源
 loadprob: String.raw`\min_{\mathbf w}\;\mathbf w^{H}\boldsymbol\Gamma\mathbf w
 \quad\text{s.t.}\quad \mathbf w^{H}\mathbf a=1,\;\;
 \underbrace{\mathbf w^{H}\mathbf w\le 1/G_{\min}}_{\text{WNG 下限}}`,
 loadresult: String.raw`\mathbf w=\frac{(\boldsymbol\Gamma+\varepsilon\mathbf I)^{-1}\mathbf a}
 {\mathbf a^{H}(\boldsymbol\Gamma+\varepsilon\mathbf I)^{-1}\mathbf a}
 \qquad \varepsilon=\text{WNG 约束的拉格朗日乘子}`,
 // 差分阵
 dmaqderiv: String.raw`\begin{aligned}
 \bigl\langle D^{2}(\theta)\bigr\rangle&=\bigl\langle\bigl(A+(1-A)\cos\theta\bigr)^{2}\bigr\rangle
 =A^{2}+2A(1-A)\underbrace{\langle\cos\theta\rangle}_{=0}
 +(1-A)^{2}\underbrace{\langle\cos^{2}\theta\rangle}_{=1/3}\\[3pt]
 Q&=\frac{D^{2}(0)}{\langle D^{2}(\theta)\rangle}=\frac{1}{A^{2}+\tfrac{(1-A)^{2}}{3}}
 \end{aligned}`,
 dmalossderiv: String.raw`\begin{aligned}
 x_1-x_2&=x_1\bigl(1-e^{-jkd}\bigr)
 =x_1\,e^{-jkd/2}\bigl(e^{\,jkd/2}-e^{-jkd/2}\bigr)
 =x_1\,e^{-jkd/2}\cdot 2j\sin(kd/2)\\[3pt]
 \lvert H\rvert&=2\bigl\lvert\sin(kd/2)\bigr\rvert\;\xrightarrow{\;kd\ll1\;}\;kd
 \quad\Rightarrow\quad 6\ \text{dB/oct}
 \end{aligned}`,
 // 临界距离
 rcderiv: String.raw`\begin{aligned}
 \text{直达声能量密度}\;&D_d=\frac{Q\,W}{4\pi r^{2}c}
 \qquad
 \text{混响声}\;D_r=\frac{4W}{Rc}\\[4pt]
 D_d=D_r\;\Rightarrow\;&\frac{Q}{4\pi r^{2}}=\frac{4}{R}
 \;\Rightarrow\; r_c=\sqrt{\frac{Q\,R}{16\pi}}
 \overset{R\approx\frac{0.161V}{\mathrm{RT}_{60}}}{=}0.057\sqrt{\frac{Q\,V}{\mathrm{RT}_{60}}}
 \end{aligned}`,
 // 远场边界
 farderiv: String.raw`\begin{aligned}
 \Delta&=\sqrt{r^{2}+(L/2)^{2}}-r\;\approx\;\frac{L^{2}}{8r}
 \qquad(\text{阵列边缘的程差})\\[3pt]
 k\Delta&<\frac{\pi}{8}\;\Longrightarrow\;\frac{2\pi}{\lambda}\cdot\frac{L^{2}}{8r}<\frac{\pi}{8}
 \;\Longrightarrow\; r>\frac{2L^{2}}{\lambda}
 \end{aligned}`,
 // GCC-PHAT 白化
 phatderiv: String.raw`\begin{aligned}
 G_{12}(\omega)&=X_1X_2^{*}=\lvert S(\omega)\rvert^{2}e^{-j\omega\tau}+\text{混响与噪声}\\[3pt]
 \frac{G_{12}}{\lvert G_{12}\rvert}&\approx e^{-j\omega\tau}
 \;\xrightarrow{\ \text{IFT}\ }\;\delta(t-\tau)
 \end{aligned}`,
 // 混叠的来源
 aliasderiv: String.raw`\begin{aligned}
 \text{相邻阵元相位差}\;\psi&=kd\cos\theta\in[-kd,\;kd]\\[3pt]
 \text{无歧义要求}\;&kd\le\pi\;\Longrightarrow\;\frac{2\pi f}{c}d\le\pi
 \;\Longrightarrow\; f\le\frac{c}{2d}
 \end{aligned}`,
};
const out={};
for(const[k,v]of Object.entries(D))
  out[k]=katex.renderToString(v,{displayMode:true,throwOnError:true,strict:'ignore',output:'html'});
fs.writeFileSync('deriv.json',JSON.stringify(out));
console.log('推导公式:',Object.keys(out).length);
