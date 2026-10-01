// 《前端信号处理手册》新增部分的公式：总纲 + 回声消除与全双工。
// 阵列与单通道两部分的公式已经渲染在各自的 HTML 里，合并时原样搬过来，
// 这里只渲染新写的。编号沿用阵列那一半的习惯：<strong>每节自己从 ① 起</strong>。
const katex = require('katex'), fs = require('fs');
const AD = JSON.parse(fs.readFileSync('demo_aec_adapt.json', 'utf8'));
const DT = JSON.parse(fs.readFileSync('demo_aec_dtd.json', 'utf8'));
const DR = JSON.parse(fs.readFileSync('demo_aec_drift.json', 'utf8'));
const RS = JSON.parse(fs.readFileSync('demo_aec_res.json', 'utf8'));
const r = (x, n) => Number(x).toFixed(n);
const mu0 = AD.mu[0], mu4 = AD.mu[AD.mu.length - 1];
const best = DT.sweep.reduce((a, b) => (b.erle > a.erle ? b : a));
const ppm6 = DR.ppm_note.ppm_6db;
const knee = RS.res_note;
const mdt = DT.miss_knee;

const D = {

// ══ 总纲 ══════════════════════════════════════════════════════
// ① 一个前端只有三种信息可用
three: String.raw`y_m(t)=\underbrace{\sum_i a_{m,i}\!*\!s_i(t)}
  _{\textstyle \substack{\text{目标与干扰}\\ \text{方向不同}\ \Rightarrow\ \textbf{空间}}}
 \;+\;\underbrace{v_m(t)}
  _{\textstyle \substack{\text{弥散噪声}\\ \text{只剩分布假设}\ \Rightarrow\ \textbf{统计}}}
 \;+\;\underbrace{g_m\!*\!x(t)}
  _{\textstyle \substack{x\ \text{是自己播的}\\ \text{已知}\ \Rightarrow\ \textbf{参考}}}`,

// ② 三种信息各自的上限由什么定
limits: String.raw`\begin{aligned}
 \text{空间：}&\ \mathrm{DI}\le 10\log_{10}M
   &&\textstyle\text{上限由麦克风数与孔径定}\\[4pt]
 \text{统计：}&\ \text{假设成立的程度}
   &&\textstyle\text{噪声比语音平稳、语音在时频上稀疏}\\[4pt]
 \text{参考：}&\ \mathrm{ERLE}\le-10\log_{10}\!\big(\epsilon_{\text{尾}}+\epsilon_{\text{nl}}+\epsilon_{\text{底噪}}\big)
   &&\textstyle\text{三条天花板取最低的那条}
 \end{aligned}`,

// ══ 回声：模型与上界 ═══════════════════════════════════════════
// ① 回声的观测模型
echomodel: String.raw`y(t)=\underbrace{(g*x)(t)}_{\textstyle \text{回声}}
 +\underbrace{s(t)}_{\textstyle \text{近端语音}}+\underbrace{v(t)}_{\textstyle \text{底噪}}
 \qquad
 \underbrace{e(t)=y(t)-(\hat g*x)(t)}
  _{\textstyle \substack{x\ \text{完全已知，所以这是个}\textbf{辨识}\text{问题}\\
   \text{——不是}\textbf{估计}\text{问题}}}`,

// ② ERLE 与它的三条天花板
erle: String.raw`\mathrm{ERLE}=10\log_{10}\frac{\operatorname{E}\{d^{2}\}}{\operatorname{E}\{e^{2}\}}
 \qquad
 \mathrm{ERLE}_{\max}=-10\log_{10}\Big(
 \underbrace{\epsilon_{\text{尾}}}_{\textstyle \substack{\text{截断掉的}\\ \text{路径能量}}}
 +\underbrace{\epsilon_{\text{nl}}}_{\textstyle \substack{\text{喇叭的}\\ \text{非线性}}}
 +\underbrace{\epsilon_{v}}_{\textstyle \substack{\text{近端}\\ \text{底噪}}}\Big)`,

// ══ 自适应滤波 ════════════════════════════════════════════════
// ① NLMS
nlms: String.raw`\mathbf{w}_{n+1}=\mathbf{w}_n+\mu\,
 \frac{e(n)\,\mathbf{x}_n}{\lVert\mathbf{x}_n\rVert^{2}+\delta}
 \qquad
 \underbrace{\mathcal{M}=\frac{\lVert\mathbf{w}-\mathbf{g}\rVert}{\lVert\mathbf{g}\rVert}}
  _{\textstyle \substack{\text{失调：真正该看的那个量}\\ \text{——ERLE 看不见它}}}`,

// ② 快与准的积是守恒的
tradeoff: String.raw`\underbrace{T_{\text{收敛}}\propto\frac{1}{\mu}}
  _{\textstyle \text{快}}
 \qquad
 \underbrace{\mathcal{M}_{\infty}^{2}\propto\frac{\mu}{2-\mu}\cdot
   \frac{\sigma_v^{2}}{\sigma_d^{2}}}
  _{\textstyle \text{准}}
 \qquad\Longrightarrow\qquad
 \underbrace{T_{\text{收敛}}\cdot\mathcal{M}_{\infty}^{2}\approx\text{常数}}
  _{\textstyle \substack{\mu\ \text{变}\ ${r(mu4.mu / mu0.mu, 0)}\ \text{倍，积只动}\
   ${r(AD.mu_tradeoff.prod_spread, 1)}\ \text{倍}}}`,

// ③ 特征值扩散
spread: String.raw`\chi=\frac{\lambda_{\max}(\mathbf{R}_{xx})}{\lambda_{\min}(\mathbf{R}_{xx})}
 \qquad
 \underbrace{\mu_{\text{稳}}\propto\frac{1}{\lambda_{\max}}}
  _{\textstyle \substack{\text{步长由最强的频点定}}}
 \qquad
 \underbrace{T_{\text{收敛}}\propto\chi}
  _{\textstyle \substack{\text{于是最弱的频点慢}\ \chi\ \text{倍}\\
   \text{白噪}\ ${r(AD.spec[0].spread, 1)}\ \to\ \text{语音}\ ${r(AD.spec[2].spread, 0)}}}`,

// ④ 分区块：延迟和滤波器长度解耦
partition: String.raw`\underbrace{\tau_{\text{块}}=\frac{B}{f_s}}
  _{\textstyle \substack{\text{延迟只看}\ B}}
 \qquad
 \underbrace{L=P\cdot B}
  _{\textstyle \substack{\text{覆盖多长的路径}\\ \text{看分区数}\ P}}
 \qquad
 \underbrace{\text{算力}\propto\frac{f_s}{B}\big(c_1\log_2 2B+c_2P\big)}
  _{\textstyle \substack{B\ \text{减半，延迟减半}\\ \text{算力约翻倍}}}`,

// ══ 双讲检测 ══════════════════════════════════════════════════
// ① 判据
dtd: String.raw`\xi_b=\frac{\operatorname{E}_b\{y^{2}\}}{\operatorname{E}_b\{\hat y^{2}\}}
 \;\;\gtrless\;\;\kappa
 \qquad
 \underbrace{\xi\approx1+\frac{\sigma_s^{2}}{\sigma_d^{2}}}
  _{\textstyle \substack{\text{近端一开口它就抬头}\\ \text{但要滤波器先收敛才准}}}`,

// ② 两种错误的代价不是一回事
dtdcost: String.raw`\underbrace{C_{\text{漏检}}(\Delta t)\approx\begin{cases}
 0,&\Delta t<\Delta t^{*}\\[2pt]
 \text{发散，再花 }T_{\text{重收敛}}\text{ 还清},&\Delta t\ge\Delta t^{*}\end{cases}}
  _{\textstyle \substack{\textbf{阈值型}\ \ \Delta t^{*}\approx
   ${r(DT.miss_knee.free_up_to, 1)}\!-\!${r(DT.inject.miss[3].dur, 1)}\ \text{s}}}
 \qquad
 \underbrace{C_{\text{误检}}(f)\propto f}
  _{\textstyle \substack{\textbf{渐进型}\ \ \text{少的只是更新机会}}}`,

// ══ 追不上的那一部分 ═══════════════════════════════════════════
// ① 时钟漂移
drift: String.raw`\Delta n(t)=\varepsilon\,f_s\,t
 \qquad
 \underbrace{\text{第 }\ell\text{ 个抽头在 }T\text{ 秒后错开 }\varepsilon f_sT}
  _{\textstyle \substack{\text{和}\ \ell\ \text{无关，但尾部抽头的}\\
   \text{相关时间最短，先解相关}}}
 \qquad
 \underbrace{\varepsilon\gtrsim ${ppm6}\ \text{ppm}}
  _{\textstyle \substack{\text{实测掉}\ 6\ \text{dB 的拐点}}}`,

// ② 延迟预算：滤波器要装下什么
budget: String.raw`\underbrace{L/f_s}_{\textstyle \text{滤波器长度}}
 \;\ge\;\underbrace{\tau_{\text{纯时延}}}
  _{\textstyle \substack{\text{缓冲、编解码、}\\ \text{蓝牙、声程}}}
 \;+\;\underbrace{\tau_{\text{尾巴}}}
  _{\textstyle \substack{\text{房间混响}}}
 \qquad
 \underbrace{\text{差一点}\;\Rightarrow\;\mathrm{ERLE}\to 0}
  _{\textstyle \substack{\text{这是悬崖，不是斜坡}}}`,

// ══ 非线性与残余抑制 ═══════════════════════════════════════════
// ① 线性能拿到的上界
nonlin: String.raw`x_{\text{播}}=\underbrace{\alpha x}_{\textstyle \substack{\text{线性滤波器}\\ \text{能对消的}}}
 +\underbrace{n(x)}_{\textstyle \substack{\text{它结构上}\\ \text{拿不到的}}}
 \qquad
 \underbrace{\mathrm{ERLE}_{\max}=-20\log_{10}\frac{\lVert n\rVert}{\lVert\alpha x\rVert}}
  _{\textstyle \substack{\text{实测}\ ${r(RS.nl_note.worst_thd, 1)}\%\ \to\
   ${r(RS.nl_note.worst_erle, 1)}\ \text{dB}\\ \text{理论}\
   ${r(RS.nl_note.worst_theory, 1)}\ \text{dB}}}`,

// ② RES 的两头
res: String.raw`G_{k,l}=\max\!\Big(\frac{\lvert E_{k,l}\rvert^{2}
   -\gamma\lvert \hat Y_{k,l}\rvert^{2}}{\lvert E_{k,l}\rvert^{2}},\,G_{\min}\Big)
 \qquad
 \underbrace{\gamma\uparrow\;\Rightarrow\;\mathrm{ERLE}\uparrow\ \text{而近端}\downarrow}
  _{\textstyle \substack{\text{实测 ERLE}\ +${r(RS.res_note.erle_best - RS.res[0].erle, 1)}\
   \text{dB，近端}\ -${r(RS.res[0].near_segsnr - RS.res_note.q_at_erle, 1)}\ \text{dB}}}`,
};

const I = {
  erle: String.raw`\mathrm{ERLE}`,
  mis: String.raw`\mathcal{M}`,
  mu: String.raw`\mu`,
  chi: String.raw`\chi`,
  kappa: String.raw`\kappa`,
  gam: String.raw`\gamma`,
  eps: String.raw`\varepsilon`,
  Bblk: String.raw`B`,
  Ppart: String.raw`P`,
  xi: String.raw`\xi_b`,
  ghat: String.raw`\hat g`,
  dtstar: String.raw`\Delta t^{*}`,
  ppm6: String.raw`${ppm6}\ \text{ppm}`,
  kbest: String.raw`\kappa=${best.kappa}`,
  gknee: String.raw`\gamma=${knee.knee_gamma}`,
};

// \substack 的两行在 underbrace 下面挤在一起（字距太紧，会叠字），给每个行间加 4pt。
function loosen(t) {
  const key = String.raw`\substack{`;
  let o = '', i = 0;
  for (;;) {
    const j = t.indexOf(key, i);
    if (j < 0) { o += t.slice(i); break; }
    let d = 1, k = j + key.length;
    while (d > 0) { const c = t[k++]; if (c === '{') d++; else if (c === '}') d--; }
    o += t.slice(i, j) + t.slice(j, k).replace(/\\\\(?!\[)/g, String.raw`\\[4pt]`);
    i = k;
  }
  return o;
}
const out = {}, oi = {};
for (const [k, v] of Object.entries(D))
  out[k] = katex.renderToString(loosen(v), { displayMode: true, throwOnError: true, strict: 'ignore', output: 'html' });
for (const [k, v] of Object.entries(I))
  oi[k] = katex.renderToString(v, { displayMode: false, throwOnError: true, strict: 'ignore', output: 'html' });
fs.writeFileSync('fe_k.json', JSON.stringify(out));
fs.writeFileSync('fe_ki.json', JSON.stringify(oi));
console.log('公式', Object.keys(out).length, '行内', Object.keys(oi).length);
