const katex=require('katex'), fs=require('fs');
const MAP={
 'r_c':'r_c','Γ':'\\boldsymbol\\Gamma','c/(2d)':'c/(2d)','kd':'kd',
 '[300 Hz, f_alias]':'[300\\ \\mathrm{Hz},\\ f_{\\text{alias}}]',
 'Γ→1':'\\boldsymbol\\Gamma\\to 1','Γ → 1':'\\boldsymbol\\Gamma\\to 1','m':'m',
 'w = a(θ₀)/M':'\\mathbf w=\\mathbf a(\\theta_0)/M','1/r²':'1/r^{2}','Q':'Q',
 'd ≤ λ_min/2':'d\\le\\lambda_{\\min}/2','L = (M−1)·d':'L=(M-1)d',
 '|wᴴa(θ)|':'\\lvert\\mathbf w^{H}\\mathbf a(\\theta)\\rvert','c/d':'c/d','λ/2':'\\lambda/2',
 'Δθ ≈ λ/L':'\\Delta\\theta\\approx\\lambda/L','−WNG':'-\\mathrm{WNG}',
 '|γ₁₂|²':'\\lvert\\gamma_{12}\\rvert^{2}','exp(−jωτ)':'e^{-j\\omega\\tau}',
 'w(ω)':'\\mathbf w(\\omega)','Γ(ω)':'\\boldsymbol\\Gamma(\\omega)','R(ω)':'\\mathbf R(\\omega)',
 'ω_k = 2πk·fs/N':'\\omega_k=2\\pi k\\,f_s/N','2πk/N':'2\\pi k/N','fs':'f_s',
 'RT60 &gt; 0.5 s':'\\mathrm{RT}_{60}>0.5\\,\\mathrm{s}','w = a/M':'\\mathbf w=\\mathbf a/M',
 'w = (Γ+εI)⁻¹a / aᴴ(Γ+εI)⁻¹a':'\\mathbf w=(\\boldsymbol\\Gamma+\\varepsilon\\mathbf I)^{-1}\\mathbf a\\,/\\,\\mathbf a^{H}(\\boldsymbol\\Gamma+\\varepsilon\\mathbf I)^{-1}\\mathbf a',
 'w = R_n⁻¹a / aᴴR_n⁻¹a':'\\mathbf w=\\mathbf R_n^{-1}\\mathbf a\\,/\\,\\mathbf a^{H}\\mathbf R_n^{-1}\\mathbf a',
 'R_x':'\\mathbf R_x','R_s w = λ R_n w':'\\mathbf R_s\\mathbf w=\\lambda\\,\\mathbf R_n\\mathbf w',
 'R_s, R_n':'\\mathbf R_s,\\ \\mathbf R_n','R_n':'\\mathbf R_n','εI':'\\varepsilon\\mathbf I',
 'H(ω,t)':'H(\\omega,t)','O(N log N)':'O(N\\log N)','O(M³)':'O(M^{3})','O((ML)³)':'O((ML)^{3})',
 'N(0, 0.5 dB)':'N(0,\\ 0.5\\,\\mathrm{dB})','N(0, 2°)':'N(0,\\ 2^{\\circ})',
 '20log₁₀(M)':'20\\log_{10}(M)','1e−16':'10^{-16}','cond(Γ)':'\\operatorname{cond}(\\boldsymbol\\Gamma)',
 'Γ⁻¹':'\\boldsymbol\\Gamma^{-1}','w':'\\mathbf w','L=(M−1)d':'L=(M-1)d'
};
const out={};
for(const[k,v]of Object.entries(MAP))
  out[k]=katex.renderToString(v,{displayMode:false,throwOnError:true,strict:'ignore',output:'html'});
fs.writeFileSync('inlinemath.json',JSON.stringify(out));
console.log('行内数学:',Object.keys(out).length);
