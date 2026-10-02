# -*- coding: utf-8 -*-
"""19–21 节：关键推导补遗、评价指标的计算、全链路数值算例。"""
from util import fml, sec, part, table, note, trap, ex, why, q, h4, chain, iface, CALC as C


def build_e():
    o = []
    o.append(part('Part Ⅷ', '推导、指标与算例', '前面几处只给了结果的推导，补全；评价指标怎么算，写清；最后用一组具体的数，把整条链路走一遍'))

    # ── 19 推导补遗 ──
    o.append(sec('u20', '19', '关键推导补遗', '深入',
                 lede='前面为了保持主线，有些推导只给了结果。这一节把它们补齐。每一小节都是自足的：设定、推导、结论、它说明了什么。',
                 tldr='这一节是整本手册的"推导附录"：NLMS 的收敛与稳态、卡尔曼增益、维纳后验、Baum–Welch、CTC 梯度、注意力的缩放、GAN 的最优判别器、VQ 的直通估计、扩散的后验与流匹配的边缘向量场。'))

    o.append(h4('19.1 NLMS 的收敛与稳态：快与准的积是怎么来的'))
    o.append('<p><strong>设定。</strong>真实路径 <b>h</b>，估计 <b>w</b>，失调向量 <b>Δ</b> = <b>h</b> − <b>w</b>。观测 y = <b>x</b><sup>⊤</sup><b>h</b> + v，误差 e = y − <b>x</b><sup>⊤</sup><b>w</b> = <b>x</b><sup>⊤</sup><b>Δ</b> + v。NLMS 更新 <b>w</b>′ = <b>w</b> + μ e <b>x</b>/‖<b>x</b>‖²，所以 <b>Δ</b>′ = <b>Δ</b> − μ e <b>x</b>/‖<b>x</b>‖²。</p>')
    o.append('<p><strong>推导。</strong>对 ‖<b>Δ</b>′‖² 展开，取期望。假设输入是白的（E[<b>x</b><b>x</b><sup>⊤</sup>] = σ<sub>x</sub>²<b>I</b>）、v 与 <b>x</b> 独立，并用 E[1/‖<b>x</b>‖²] ≈ 1/(Lσ<sub>x</sub>²)（L 较大时成立）。'
             '展开后有三项：<b>Δ</b> 自身的缩减 −2μ(<b>x</b><sup>⊤</sup><b>Δ</b>)²/‖<b>x</b>‖²，二次项 μ²(<b>x</b><sup>⊤</sup><b>Δ</b>)²/‖<b>x</b>‖²，以及噪声注入 μ²v²/‖<b>x</b>‖²。前两项各得 E‖<b>Δ</b>‖²/L 的倍数，合并成压缩因子 1 − μ(2−μ)/L；第三项是常数注入：</p>')
    o.append(fml('NLMS 的失调递推与稳态', 'nlms_rec', [('Δ', '失调向量'), ('σ<sub>x</sub><sup>2</sup>, σ<sub>v</sub><sup>2</sup>', '输入与噪声功率'), ('L', '滤波器长度')]))
    o.append('<p><strong>读结果。</strong>递推是一个一阶线性差分方程：每步以因子 (1 − μ(2−μ)/L) 衰减旧失调，同时注入一个常数。所以收敛的时间常数是 L/(μ(2−μ)) 个样点，稳态的失调正比于 μ/(2−μ)。'
             '两者的乘积 ≈ L σ<sub>v</sub>²/(2−μ)²：μ ≪ 1 时几乎不随 μ 变——<strong>快与准的积守恒</strong>。μ = 1 时压缩因子最大（收敛最快），但稳态失调也最大；μ 在 (0, 2) 内才收敛。</p>')

    o.append(h4('19.2 卡尔曼增益：为什么是那个形状'))
    o.append('<p><strong>设定。</strong>状态（单频点、单分区的回声路径系数）按随机游走演化，观测是被噪声污染的线性测量。目标是在每一步求<strong>后验方差最小</strong>的线性更新。</p>')
    o.append(fml('卡尔曼增益的推导（标量复数形式）', 'kalman_der', [('q', '过程噪声方差：路径变化的快慢'), ('Φ<sub>v</sub>', '观测噪声方差（近端语音 + 噪声）'), ('P', '状态估计的方差')]))
    o.append('<p><strong>推导的要点。</strong>写更新为 ĥ = ĥ⁻ + K(y − xĥ⁻)，把观测方程代入，估计误差 h − ĥ = (1 − Kx)(h − ĥ⁻) − Kv。取模平方的期望，得到关于 K 的二次函数 P(K) = |1 − Kx|²P⁻ + |K|²Φ<sub>v</sub>。'
             '对 K* 求导令其为零，得 K = P⁻x*/(|x|²P⁻ + Φ<sub>v</sub>)，代回得 P = (1 − Kx)P⁻。</p>')
    o.append('<p><strong>读结果。</strong>分母里有 Φ<sub>v</sub>：观测噪声越大，增益越小。双讲时近端语音抬高 Φ<sub>v</sub>，更新自动放缓——这就是"不需要显式双讲检测"的数学来源。分子里有 P⁻：状态越不确定（路径刚变过），增益越大，收敛越快。</p>')

    o.append(h4('19.3 维纳后验：高斯条件分布'))
    o.append('<p>MMSE-STSA 的第一步是写出给定 Y 时 S 的后验。S 与 Y 联合是零均值复高斯，协方差如下，而高斯的条件分布有闭式（条件均值 = 协方差之比乘观测，条件方差 = 边缘方差减去被解释的部分）：</p>')
    o.append(fml('联合高斯的条件分布', 'gausscond', [('Φ<sub>s</sub>, Φ<sub>n</sub>', '语音与噪声功率'), ('CN', '复高斯分布')]))
    o.append('<p>条件均值 Φ<sub>s</sub>/(Φ<sub>s</sub>+Φ<sub>n</sub>)·Y 正是维纳输出；条件方差 Φ<sub>s</sub>Φ<sub>n</sub>/(Φ<sub>s</sub>+Φ<sub>n</sub>) = G<sub>W</sub>Φ<sub>n</sub> 是估计的残余不确定度。<strong>这说明维纳滤波是"后验均值"</strong>，而 MMSE-STSA、LSA 是对后验的幅度、对数幅度求期望。</p>')

    o.append(h4('19.4 Baum–Welch：HMM 的 EM 训练'))
    o.append('<p><strong>前向–后向。</strong>前向变量 α 已在 7 节给出；后向变量 β<sub>t</sub>(i) 是"从 t 时刻在状态 i 出发，产生其余观测的概率"，递推方向相反。二者之积给出<strong>占有概率</strong> γ（t 时刻在状态 i 的后验）与<strong>转移占有</strong> ξ（t 时刻在 i、t+1 时刻在 j 的后验）。</p>')
    o.append(fml('后向变量、占有概率与 EM', 'bw_hmm', [('β<sub>t</sub>(i)', '后向变量'), ('γ<sub>t</sub>(i)', '状态占有概率'), ('ξ<sub>t</sub>(i,j)', '转移占有概率'), ('Q', 'EM 的辅助函数')]))
    o.append('<p><strong>为什么有效。</strong>隐状态序列未知，直接最大化 log P(<b>O</b>|λ) 要对所有路径求和，不好优化。EM 的做法：E 步用当前参数算隐变量的后验（γ、ξ），M 步最大化期望完整对数似然 Q。'
             '用 Jensen 不等式可以证明：<strong>最大化 Q 不会使似然下降</strong>（Q 是似然的一个下界，在当前点处相切）。M 步的结果就是"按占有概率加权的计数"：转移概率 ā<sub>ij</sub> = 期望转移次数 / 期望在 i 的次数，高斯的均值是按 γ 加权的样本均值（7 节）。'
             '局限：只收敛到局部极大，对初值敏感。</p>')

    o.append(h4('19.5 CTC 的梯度'))
    o.append('<p><strong>思路。</strong>训练 CTC 要对 L = −ln P(<b>y</b>|<b>x</b>) 关于网络输出（softmax 之前的 logit u）求梯度。直接对所有路径求导不可行，利用前向 α 与后向 β 把梯度局部化到每个时间步、每个标签。</p>')
    o.append(fml('CTC 梯度的推导', 'ctc_grad', [('α<sub>t</sub>(s), β<sub>t</sub>(s)', '前向、后向变量（二者都包含 t 帧的发射概率）'), ('l′', '加空白的扩展标签序列'), ('u, y', 'logit 与 softmax 输出')]))
    o.append('<p><strong>推导的要点。</strong>（1）任取固定的 t，所有经过 t 帧的路径可按"在扩展序列第 s 个位置"分类：P = Σ<sub>s</sub> α<sub>t</sub>(s)β<sub>t</sub>(s)/y<sub>t</sub><sup>l′<sub>s</sub></sup>（α、β 都含 t 帧的发射概率，所以除一次）。'
             '（2）对 y<sub>t</sub><sup>k</sup> 求导：只有 l′<sub>s</sub> = k 的项含它，而 α<sub>t</sub>β<sub>t</sub> 正比于 (y<sub>t</sub><sup>k</sup>)²，所以导数是 (1/y²)Σα<sub>t</sub>β<sub>t</sub>。'
             '（3）经 softmax 的链式法则（∂y<sup>k′</sup>/∂u<sup>k</sup> = y<sup>k′</sup>(δ − y<sup>k</sup>)）并对 L = −ln P 求导，得到简洁结果：梯度 = 网络当前的输出概率 y − 每个标签在<strong>该帧被软对齐到的比例</strong>（分子是经过该标签的路径的概率质量，除以总概率）。</p>')
    o.append('<p><strong>读结果。</strong>训练的效果：把输出概率拉向"后验对齐比例"。这也解释了尖峰：一旦网络在某帧给非空白标签较高概率，该帧在对齐后验中占比就高，被进一步强化。</p>')

    o.append(h4('19.6 注意力：softmax 的雅可比与 1/√d 缩放'))
    o.append('<p><strong>缩放。</strong>点积注意力的 logit 是 <b>q</b><sup>⊤</sup><b>k</b>。设 <b>q</b>、<b>k</b> 各分量零均值、单位方差、相互独立，则 Var(<b>q</b><sup>⊤</sup><b>k</b>) = d<sub>k</sub>：维度越大，logit 的尺度越大。大尺度的 logit 使 softmax 趋于 one-hot，而 softmax 的梯度是 s<sub>i</sub>(δ<sub>ij</sub> − s<sub>j</sub>)：当 s 接近 one-hot，所有项都趋于零，<strong>梯度消失</strong>。'
             '所以除以 √d<sub>k</sub> 把方差拉回 1。</p>')
    o.append(fml('softmax 的雅可比与点积方差', 'softmaxj', [('s', 'softmax 输出'), ('δ<sub>ij</sub>', '克罗内克记号'), ('d<sub>k</sub>', '键的维度')]))
    o.append('<p><strong>多头与位置。</strong>多头把 d 维分成 h 组，每组独立做注意力再拼接——让不同的头关注不同类型的关系（局部、全局、周期）。注意力本身对输入顺序不敏感（置换等变），所以要加位置信息；语音里相对位置比绝对位置重要，常用相对位置编码。</p>')

    o.append(h4('19.7 GAN：最优判别器与散度'))
    o.append('<p><strong>原始 GAN。</strong>固定生成器 G，对判别器 D 逐点最大化 p<sub>data</sub>(x)log D + p<sub>g</sub>(x)log(1−D)，逐点求导得最优判别器 D* = p<sub>data</sub>/(p<sub>data</sub> + p<sub>g</sub>)。代回，生成器的目标变成 −log4 加上两倍的 Jensen–Shannon 散度，所以最优的 G 使 p<sub>g</sub> = p<sub>data</sub>：</p>')
    o.append(fml('GAN 的极小极大与最优判别器', 'gan_opt', [('D*', '最优判别器'), ('JS', 'Jensen–Shannon 散度')]))
    o.append('<p>声码器用的是<strong>最小二乘 GAN</strong>（12 节）：把对数损失换成平方损失，在适当选取目标值时等价于最小化 Pearson χ² 散度；梯度在 D 判得很"自信"时不消失，训练更稳。<strong>实践中的局限</strong>：以上只是在"判别器总是最优"的理想下成立；真实训练里 D 与 G 交替更新，可能震荡、模式坍缩，所以要特征匹配、谱归一化等稳定手段。</p>')

    o.append(h4('19.8 VQ：不可导的量化怎么训练'))
    o.append('<p>量化是 argmin，不可导。VQ-VAE 用<strong>直通估计</strong>：前向用量化后的向量 <b>z</b><sub>q</sub>，反向把梯度原样复制给量化前的 <b>z</b><sub>e</sub>（把量化当作恒等映射）。码本本身用两个辅助项训练：一项把码字拉向编码器输出，另一项（承诺损失）把编码器输出拉向码字，防止编码器输出在码字之间乱漂：</p>')
    o.append(fml('VQ 的损失与直通估计', 'vq_ste', [('sg[·]', '停止梯度'), ('e', '码字'), ('β', '承诺损失权重')]))
    o.append('<p>常见的问题是<strong>码本塌缩</strong>：只有少数码字被用到。对策：用滑动平均更新码本（代替梯度）、对未使用的码字重新初始化、降低码本维度。残差矢量量化（RVQ）逐级对残差再量化，每一级都用同样的机制。</p>')

    o.append(h4('19.9 扩散的后验与流匹配的边缘向量场'))
    o.append('<p><strong>DDPM 的损失为什么是噪声预测。</strong>正向过程每步加高斯噪声，所以给定 x₀ 时 q(x<sub>t−1</sub>|x<sub>t</sub>, x₀) 是一个高斯（贝叶斯公式，两个高斯相乘），其均值有闭式，并可用噪声 ε 表示。逆向模型也取高斯并取同样的方差，二者的 KL 散度就化为<strong>均值之差的平方</strong>，把均值参数化成噪声预测后，损失简化为 ‖ε − ε<sub>θ</sub>‖²：</p>')
    o.append(fml('扩散后验与简化损失', 'ddpm_post', [('α<sub>t</sub>, ᾱ<sub>t</sub>', '噪声调度及其累积'), ('β<sub>t</sub>', '1 − α<sub>t</sub>'), ('ε', '加进去的噪声')]))
    o.append('<p><strong>流匹配的关键定理。</strong>我们回归的是"条件速度"u<sub>t</sub>(x|x₁)（给定数据终点的速度），但要学的是<strong>边缘向量场</strong> v<sub>t</sub>(x)（所有终点平均后的速度）。二者的关系：边缘向量场等于在点 x 处条件速度的条件期望（用边缘密度加权）。'
             '最小二乘回归的最优解恰好是条件期望，所以回归条件速度，等价于学到了边缘向量场；而边缘向量场满足连续性方程，意味着沿它积分，能把噪声分布搬运成数据分布：</p>')
    o.append(fml('连续性方程与边缘向量场', 'fm_marg', [('p<sub>t</sub>', 't 时刻的边缘密度'), ('u<sub>t</sub>(x|x₁)', '给定终点 x₁ 的条件速度'), ('q(x₁)', '数据分布')]))
    o.append('<p>这就是 11 节问题"回归的目标是一对多，为什么不会糊"的数学回答：平均发生在<strong>速度</strong>上，且这个平均场恰好是一个<strong>合法的输运</strong>，而不是对样本的平均。</p>')

    o.append(h4('19.10 其余几处，简要'))
    o.append(table(['推导', '要点'], [
        ['WPE 的正规方程', '加权最小二乘 min Σ_t |Y(t) − g<sup>H</sup>ỹ(t)|²/λ<sub>t</sub> 对 g 求导令其为零，得 5 节给出的 g = (Σ ỹỹ<sup>H</sup>/λ)<sup>−1</sup> Σ ỹY<sup>*</sup>/λ'],
        ['MLPG', 'log N(Wc; μ, Σ) = −½(Wc − μ)<sup>⊤</sup>Σ<sup>−1</sup>(Wc − μ) + 常数，对 c 求导令其为零，得 W<sup>⊤</sup>Σ<sup>−1</sup>W c = W<sup>⊤</sup>Σ<sup>−1</sup>μ'],
        ['Kneser–Ney', '从"绝对折扣"出发，要求低阶分布的边缘约束与训练语料一致，得到续接概率'],
        ['MUSIC', '无噪声时协方差秩 = 源数；白噪声使特征值整体抬高同一常数，噪声子空间与信号子空间正交（2 节）']], minw=560))
    o.append(note('这一节没覆盖的', '更完整的证明（如 EM 的单调性、莱斯分布矩的闭式、GAN 的收敛性）需要对应的教材。这里给出的是"为什么结论是这样"的推导主线。'))
    o.append(q([
        ('NLMS 的稳态额外误差为什么正比于 μ/(2−μ)，而时间常数反比于 μ(2−μ)？', '失调递推是一阶线性差分方程：衰减因子 1 − μ(2−μ)/L 决定收敛，常数注入 μ²σ_v²/(Lσ_x²) 与衰减之比决定稳态。'),
        ('为什么注意力要除以 √d_k？', 'q、k 各分量单位方差时点积方差为 d_k；大尺度 logit 使 softmax 饱和、梯度消失。除以 √d_k 把方差拉回 1。'),
        ('直通估计在做什么近似？', '量化的 argmin 不可导，反向时把量化当作恒等映射，把梯度原样传给量化前的向量；只是近似，所以要承诺损失约束编码器输出。'),
    ]))
    o.append('</section>')

    # ── 20 评价指标 ──
    o.append(sec('u21', '20', '评价指标的计算', '进阶',
                 lede='前面每一步都提到了指标。这一节把它们怎么算、算的是什么、容易在哪里误用，一次写清。',
                 tldr='每个指标都在回答一个特定的问题，且都有"不能回答"的问题。选指标的第一步是问：我要判断的是信号失真、感知质量、可懂度，还是任务效果？'))
    o.append('<h3>1. 信号级：有参考，逐样点或逐帧</h3>')
    o.append('<p>最基本的是信噪比与它的分段版本。分段信噪比对每帧单独算再平均，并把每帧的值<strong>截在 −10 到 35 dB 之间</strong>，避免静音帧（分母极小、分子极小）或完美帧（分母趋零）主宰平均。对数谱失真（LSD）衡量对数谱的均方根差：</p>')
    o.append(fml('分段信噪比与对数谱失真', 'segsnr', [('s, ŝ', '参考与待评信号'), ('N<sub>f</sub>', '帧数'), ('S, Ŝ', '二者的 STFT')]))
    o.append('<p>SI-SDR（4 节）对幅度缩放不敏感，常用于增强与分离。它们的共同局限：<strong>对相位、对时间对齐敏感，与听感不单调</strong>。比如一个整体延迟了几毫秒的完美输出，SNR 会很差。</p>')
    o.append('<h3>2. 感知级：模拟人的感知</h3>')
    o.append('<p><strong>PESQ</strong>（ITU-T P.862）把参考与待评信号都经过一个<strong>听觉模型</strong>：时间对齐 → 电平归一 → 感知频率变换（Bark 刻度）→ 响度变换（压缩）。然后逐时频点计算两者响度之差，得到<strong>失真密度</strong>，分别算对称与不对称两种（不对称：增加成分比丢失成分更令人不悦）并在时间与频率上聚合。最后线性组合，并映射到平均意见分的尺度：</p>')
    o.append(fml('PESQ 的最终组合与映射', 'pesq', [('d<sub>sym</sub>, d<sub>asym</sub>', '聚合后的对称与不对称失真'), ('MOS-LQO', '映射到主观平均意见分的客观估计')]))
    o.append('<p>PESQ 为电话语音设计，对宽带语音、增强后的非线性失真、生成式输出的相关性有限；它是"和某类传统失真的主观评价相关"的预测器，<strong>不是通用的质量尺</strong>。</p>')
    o.append('<p><strong>STOI</strong>（短时客观可懂度）专为可懂度设计：把信号分到 15 个 1/3 倍频程带，提取每带的<strong>时间包络</strong>，在约 384 ms 的片段内（30 帧）计算参考与待评包络的相关系数。算相关前，对待评包络做归一化与截断，使其不会比参考高出一个下限（β = −15 dB）。最后对所有带和片段求平均：</p>')
    o.append(fml('STOI', 'stoi', [('x, y', '参考与待评的某带、某片段的包络向量'), ('J, M', '频带数与片段数'), ('β', '截断下限')]))
    o.append('<p>STOI 的值域大致在 0–1，与可懂度（词识别率）高度相关，但它<strong>不衡量自然度</strong>，且对增强后可懂度基本不变的情况不灵敏。</p>')
    o.append('<p><strong>无参考的神经预测器</strong>（DNSMOS、UTMOS 一类）：在带主观评分的数据上训练一个回归网络，直接从待评语音预测 MOS。优点是不需要参考；局限是预测器在训练分布之外（新语言、新风格、生成式输出）不可信，且可能被"针对性优化"刷分。</p>')
    o.append('<h3>3. 识别、说话人与置信度</h3>')
    o.append(table(['指标', '怎么算', '要点'], [
        ['WER / CER / MER', '编辑距离 / 参考词（字）数（7 节）', '规范化必须一致；S/D/I 分开；要有置信区间'],
        ['cpWER（多说话人）', '把每个说话人的转写拼接，对说话人排列取最小 WER', '同时反映识别错误与归属错误'],
        ['EER、DET', '误报率 = 漏检率 的点；扫阈值的曲线', '只是一个工作点；产品常看极低误报下的漏检'],
        ['检测代价 minDCF', 'C<sub>miss</sub>·P<sub>miss</sub>·P<sub>target</sub> + C<sub>fa</sub>·P<sub>fa</sub>·(1−P<sub>target</sub>)，取阈值上的最小值', '把先验和代价写进指标，比 EER 更贴近应用'],
        ['ECE（置信度校准）', '按置信度分桶，|桶内准确率 − 桶内平均置信度| 的加权平均', '分桶数与样本量影响估计；要配风险–覆盖率曲线']], minw=620))
    o.append('<h3>4. 合成：客观与主观</h3>')
    o.append(fml('基频误差与置信度校准', 'f0rmse', [('f<sub>0</sub>, f̂<sub>0</sub>', '参考与合成的基频'), ('ECE', '期望校准误差')]))
    o.append(table(['指标', '计算', '它衡量 / 不衡量'], [
        ['MCD（梅尔倒谱失真）', '倒谱前 13 维距离，乘 10/ln10 与 √2（13 节）；通常用 DTW 对齐', '衡量谱包络；不衡量基频、时长、细节；一个合法的另一种读法也会被判为"远"'],
        ['F0 RMSE（音分）', '对数基频差的均方根；另报清浊判决错误率', '只衡量韵律的音高侧；对声码器质量不敏感'],
        ['说话人相似度', '参考与合成的说话人嵌入余弦（5 节）', '依赖嵌入模型与协议；与口音泄漏纠缠'],
        ['ASR 可懂度', '用 ASR 转写合成语音，算 CER / WER', '内容是否被正确说出；强语言模型会"猜对"'],
        ['神经 MOS 预测器', '回归网络（UTMOS 一类）', '同类系统粗排序；分布外不可信'],
        ['RTF、首包延迟', '耗时 / 时长；文本到第一块音频', '要说明硬件与是否流式']], minw=620))
    o.append('<h3>5. 主观评价的设计</h3>')
    o.append(table(['方法', '做法', '适用', '注意'], [
        ['ACR / MOS', '听者对每段打 1–5 分，取平均与置信区间', '绝对质量；多系统', '听者标准漂移；需锚点（参考系统）'],
        ['DCR / CMOS', '听者比较一对，给出 −3 到 +3 的分差', '两个系统相差不大', '顺序随机化；报告标准误'],
        ['AB 偏好', '二选一，统计偏好 A 的次数，用二项检验', '最简单、最稳', '要有"无差别"选项或剔除'],
        ['MUSHRA', '同一段多个系统 + 隐藏参考 + 锚点，0–100 打分', '中高质量、多系统细比较', '要筛掉听不出隐藏参考的听者']], minw=620))
    o.append('<p><strong>要多少听者 / 样本。</strong>配对评分的样本量由要分辨的差距 Δ、评分差的标准差 σ<sub>d</sub> 和统计功效决定；Δ 减半，所需样本数是原来的 4 倍。AB 偏好用二项检验：在"两者无差别"的原假设下，偏好 A 的次数服从 n、0.5 的二项分布，p 值是观察到的次数及更极端次数的概率：</p>')
    o.append(fml('样本量与二项检验', 'nsample', [('Δ', '要分辨的评分差'), ('σ<sub>d</sub>', '配对评分差的标准差'), ('z', '标准正态分位数')]))
    o.append(trap('我原以为：客观指标分数高就够了', '每个客观指标都只覆盖质量的一个侧面，且彼此排序不一致（TTS 手册 33 节实测过）。客观指标适合在迭代中便宜地筛掉明显更差的版本；<strong>最终判据仍是听测与任务效果</strong>。'))
    o.append(note('去哪看细节', 'ASR 链路手册 56 节（WER 的方差与配对检验）、TTS 合成手册 26 节（听测要多少样本）、33 节（客观指标）、38 节（无参考指标）；前端信号处理手册 B 部分（增强指标）。'))
    o.append('</section>')

    # ── 21 数值算例 ──
    o.append(sec('u22', '21', '全链路数值算例：一段数据的旅程', '入门',
                 lede='前面都是符号。这一节用一组具体的数，把一段语音从麦克风走到喇叭，每一步的中间量算一遍。',
                 tldr='场景：一个人在 2 米外、与阵列轴成 60° 的方向说"今天天气怎么样"，电视在 1 米外同时播放。<strong>每个数都是把前面的公式代入参数算出来的</strong>，由 calc.py 生成，不是实验。'))
    o.append(why('读法：每一小节先写参数，再写公式，再写结果。你可以改参数自己重算——calc.py 里一行一个量。'))
    o.append('<h3>0. 场景与参数</h3>')
    o.append(table(['量', '取值', '说明'], [
        ['阵列', '%d 个麦克风，线阵，间距 %s cm' % (C['scene']['M'], C['scene']['d_cm']), '间距小：低频孔径小'],
        ['目标方向', '%d°（与阵列轴的夹角）' % C['scene']['theta'], '用户说话'],
        ['采样率 / 时长', '%d Hz / %d 秒' % (C['scene']['fs'], C['scene']['dur']), '共 %d 个样点 / 通道' % C['shape']['N']],
        ['电视', '距离 1 m，声压级 60 dB', '与用户同声压级，但更近'],
        ['用户', '距离 2 m，声压级 60 dB', '"今天天气怎么样"，7 个字'],
        ['回声路径', '滤波器长度 %d 点（%s ms）' % (C['nlms']['L'], int(C['nlms']['L_ms'])), '覆盖房间混响的主要部分'],
        ['晶振偏差', '%d ppm' % C['drift']['ppm'], '采集与播放不同源']], minw=520))
    o.append('<h3>1. 采集：到达时延与相对电平</h3>')
    o.append('<p>平面波到第 m 个麦克风的时延 τ<sub>m</sub> = m·d·cosθ/c（1 节公式）。取 d = 3.5 cm、θ = 60°、c = 343 m/s：</p>')
    o.append(table(['麦克风 m', '#0', '#1', '#2', '#3'], [
        ['时延 τ<sub>m</sub>（μs）'] + ['%s' % v for v in C['delay']['tau_us']],
        ['时延（样点，16 kHz）'] + ['%s' % v for v in C['delay']['tau_samples']],
        ['1 kHz 处的相位（rad）'] + ['%s' % v for v in C['delay']['phase_1k']]], minw=520))
    o.append('<p>注意相邻麦克风之间的时延只有 %s 个样点——远小于一个样点，所以延迟求和必须用<strong>分数延迟</strong>（在频域是逐频点的相位补偿，不涉及取整）。'
             '空间混叠频率 c/(2d) = <strong>%d Hz</strong>：高于它，波束出现栅瓣。</p>' % (C['delay']['tau_samples'][1], int(C['delay']['alias_hz'])))
    o.append('<p>电平：用户在 2 m、电视在 1 m，二者在各自声源处声压级相同，到达麦克风时电视强 20log₁₀(2/1) = <strong>%s dB</strong>（16 节）。回声比近端语音更响。</p>' % C['spl']['ser_db'])
    o.append('<h3>2. STFT：形状</h3>')
    o.append('<p>窗长 512、帧移 256：T = 1 + ⌊(%d − 512)/256⌋ = <strong>%d</strong> 帧，F = 257 个频点。整个张量 %d × 257 × %d，共 <strong>%s</strong> 个复数。</p>' % (C['shape']['N'], C['shape']['T_stft'], C['scene']['M'], C['shape']['T_stft'], format(C['shape']['stft_complex'], ',')))
    o.append('<h3>3. 阵列：能得到多少增益</h3>')
    o.append('<p>延迟求和的白噪声增益 = M = %d，即 <strong>%s dB</strong>，与频率无关。但对<strong>弥散噪声</strong>（混响房间里的背景），增益 DI 取决于孔径与频率（2 节公式，用 sinc 相干函数代入，目标在阵列侧向）：</p>' % (C['scene']['M'], C['das']['wng_db']))
    o.append(table(['频率（Hz）'] + list(C['das']['di'].keys()), [['DAS 的弥散场 DI（dB）'] + ['%s' % v for v in C['das']['di'].values()]], minw=520))
    o.append('<p><strong>读结果：</strong>3.5 cm 间距的 4 麦阵列，在 500 Hz 以下对弥散噪声几乎没有增益（< 0.2 dB），要到 4 kHz 才有约 %s dB。<strong>小孔径阵列的低频指向性很差</strong>——这就是为什么要用差分阵列、超指向（代价是 WNG 下降），或者靠掩蔽驱动的方法与单通道增强来补低频。</p>' % C['das']['di']['4000'])
    o.append('<h3>4. 回声消除：能消多干净、多快</h3>')
    o.append('<p>滤波器 L = %d 点。NLMS 的时间常数 L/(μ(2−μ))、稳态额外误差 μ/(2−μ)·σ<sub>v</sub>²（19.1 节）。设回声比近端噪声高 40 dB（功率比 10⁴），稳态额外误差限制的 ERLE 上界是 10log₁₀(10⁴/M<sub>稳态</sub>)：</p>' % C['nlms']['L'])
    rows = []
    for mu, r in C['nlms']['rows'].items():
        rows.append([mu, '%d 样点（%s ms）' % (r['tau_samples'], r['tau_ms']), '%s' % r['M'], '%s' % r['erle_db']])
    o.append(table(['步长 μ', '时间常数', '稳态失调 μ/(2−μ)', 'ERLE 上界（dB）'], rows, minw=520))
    o.append('<p><strong>读结果：</strong>μ 从 0.1 增大到 0.5，收敛从 %s ms 缩短到 %s ms（约 4 倍），ERLE 上界从 %s dB 降到 %s dB。快与准确实在互换。</p>' % (C['nlms']['rows']['0.1']['tau_ms'], C['nlms']['rows']['0.5']['tau_ms'], C['nlms']['rows']['0.1']['erle_db'], C['nlms']['rows']['0.5']['erle_db']))
    o.append('<p>时钟：%d ppm 时每秒错开 %s 个样点，10 分钟累计 <strong>%d 个样点（%s ms）</strong>（17 节）。滤波器长度 128 ms，这样的漂移已不可忽略，需要在线估计偏差。</p>' % (C['drift']['ppm'], C['drift']['slip_per_s'], C['drift']['slip_10min'], C['drift']['ms_10min']))
    o.append('<h3>5. 单通道降噪：增益的三种估计</h3>')
    o.append('<p>先验信噪比 ξ 给定、取 γ = 1 + ξ（观测功率恰为期望）时，三种增益（4 节）：</p>')
    rows = []
    for g in C['gain']:
        rows.append(['%d dB' % g['xi_db'], '%s（%s dB）' % (g['gw'], g['gw_db']), '%s（%s dB）' % (g['glsa'], g['glsa_db']), '%s（%s dB）' % (g['gstsa'], g['gstsa_db'])])
    o.append(table(['ξ', '维纳', 'LSA', 'MMSE-STSA'], rows, minw=560))
    o.append('<p><strong>读结果：</strong>三者的顺序始终是 <b>维纳 ≤ LSA ≤ STSA</b>，与 4 节的推导一致（LSA = 维纳 × exp(E₁/2) ≥ 维纳；Jensen 不等式给出 LSA ≤ STSA）；差异在低信噪比最大——ξ = −10 dB 时，维纳衰减 %s dB，而 STSA 只衰减 %s dB。信噪比高时（≥ 10 dB）三者几乎相同。</p>' % (C['gain'][0]['gw_db'], C['gain'][0]['gstsa_db']))
    o.append('<h3>6. 特征：梅尔与帧</h3>')
    o.append('<p>梅尔刻度：8 kHz 对应 %s mel。取 80 个滤波器、范围 60–7600 Hz，相邻中心在梅尔轴上等间隔，间隔 %s mel；第 1 个滤波器中心 %s Hz、带宽 %s Hz，第 80 个中心 %s Hz、带宽 %s Hz——<strong>高频滤波器的带宽是低频的 10 倍以上</strong>，这就是梅尔滤波"低频精细、高频粗糙"的含义。</p>'
             % (C['mel']['mel8k'], C['mel']['step_mel'], C['mel']['first_center'], C['mel']['width_first'], C['mel']['last_center'], C['mel']['width_last']))
    o.append('<p>帧数：窗 25 ms（400 点）、帧移 10 ms（160 点）：T′ = 1 + ⌊(%d − 400)/160⌋ = <strong>%d</strong> 帧，形状 %d × 80。' % (C['shape']['N'], C['shape']['T_mel'], C['shape']['T_mel']) +
             '编码器下采样 4 倍：⌈%d/4⌉ = <strong>%d</strong> 帧，每帧 40 ms。</p>' % (C['shape']['T_mel'], C['shape']['T_enc']))
    o.append('<h3>7. 识别：对齐的数目与错误率</h3>')
    o.append('<p>标签 "今天天气怎么样" 有 U = %d 个字；CTC 编码器输出 T = %d 帧。把"所有帧概率都为 1"代入 CTC 的前向递推（7 节），得到映射到该标签的帧级路径个数约 <strong>10<sup>%s</sup></strong> 条——'
             '训练要对这么多条路径求和，前向–后向递推用 O(T·U) 次运算就完成了。</p>' % (C['ctc']['U'], C['ctc']['T'], C['ctc']['log10_paths']))
    o.append('<p>错误率算例：参考 %d 个词，假设识别出现 %d 次替换、%d 次删除、%d 次插入，则 WER = (%d + %d + %d)/%d = <strong>%d%%</strong>。注意 WER 可以超过 100%%（插入太多时）。</p>'
             % (C['wer']['N'], C['wer']['S'], C['wer']['D'], C['wer']['I'], C['wer']['S'], C['wer']['D'], C['wer']['I'], C['wer']['N'], int(C['wer']['wer'] * 100)))
    o.append('<h3>8. 合成：从文字到波形</h3>')
    o.append('<p>回复 3 秒语音。取 22.05 kHz、帧移 256：帧率 = 22050/256 = %s 帧/秒，梅尔帧数 ≈ 3 × %s = <strong>%d</strong>。设文本展开成 %d 个音素，则平均每个音素占 %d/%d ≈ <strong>%s 帧</strong>（长度调节器要给每个音素分配一个整数帧数，总和为 %d）。'
             % (C['tts']['fps'], C['tts']['fps'], C['tts']['frames'], C['tts']['phones'], C['tts']['frames'], C['tts']['phones'], C['tts']['avg_dur_frames'], C['tts']['frames']) + '</p>')
    o.append('<p>流匹配用 NFE = %d 步，带引导每步要两次前向，共 <strong>%d 次</strong>网络前向（11 节）。声码器：上采样倍数 %s，乘积 = <strong>%d</strong>，恰好等于帧移，所以 %d 帧输出 %d 个样点。'
             % (C['tts']['nfe'], C['tts']['forwards_cfg'], ' × '.join(str(x) for x in C['tts']['upsample']), C['tts']['upsample_prod'], C['tts']['frames'], C['tts']['samples']) + '</p>')
    o.append('<p>若改走编解码器路线：75 Hz 帧率 × 3 秒 = %d 帧 × 8 个码本 = <strong>%d 个 token</strong>，码率 6000 bit/s × 3 秒 = %d bit = %d 字节（12 节）。</p>' % (C['tts']['codec_frames'], C['tts']['codec_tokens'], C['tts']['codec_bits'], C['tts']['codec_bytes']))
    o.append('<h3>9. 回到起点：播放参考与时间轴</h3>')
    o.append('<p>合成输出 %d 个样点（22.05 kHz）要作为参考送回 AEC，须重采样到 16 kHz：比值 %d/%d，3 秒变成 <strong>%d</strong> 个样点（17 节）。参考与回声之间的整块延迟由驱动缓冲、DAC、声程、ADC 之和决定（14 节）；'
             '声程部分仅为距离 ÷ 声速，如 1 m 对应 1/343 ≈ 2.9 ms。</p>' % (C['tts']['samples'], C['resample']['ratio_num'], C['resample']['ratio_den'], C['resample']['ref_samples']))
    o.append('<h3>10. 各级的帧延迟（纯算术）</h3>')
    o.append(table(['环节', '窗 / 帧', '帧移 / 步', '算术'], [
        ['前端 STFT', '%d ms' % int(C['lat']['stft_win_ms']), '%d ms' % int(C['lat']['stft_hop_ms']), '512/16000 = 32 ms；256/16000 = 16 ms'],
        ['ASR 特征', '%d ms' % int(C['lat']['mel_win_ms']), '%d ms' % int(C['lat']['mel_hop_ms']), '400/16000 = 25 ms；160/16000 = 10 ms'],
        ['ASR 编码器', '—', '%d ms' % int(C['lat']['enc_frame_ms']), '4 × 10 ms'],
        ['TTS 梅尔', '—', '%s ms' % round(256 / 22050 * 1000, 1), '256/22050']], minw=520))
    o.append('<p>其余环节（端点静音、模型推理、网络、播放缓冲）取决于具体实现，必须在目标设备上测量——没有可以代入的通用值，所以这里不给数。</p>')
    o.append(note('这一节没覆盖的', '这是一个<strong>算术</strong>算例，不是仿真：它没有真的处理任何音频。它的作用是让每个公式有一个具体的数字落点，并检验前面的论断（如三种增益的大小顺序）。真实系统的性能必须在真实数据上测量。'))
    o.append(q([
        ('为什么 3.5 cm 间距的 4 麦阵列在 500 Hz 以下几乎没有指向性增益？', '孔径（0.105 m）远小于 500 Hz 的波长（约 0.69 m），各麦克风信号高度相干，延迟求和对弥散噪声几乎不起作用；DI 随频率升高才增大。'),
        ('μ 从 0.1 增大到 0.5，NLMS 的收敛时间缩短约几倍，ERLE 上界降多少？', '时间常数 ∝ 1/(μ(2−μ))，约缩短 4 倍；ERLE 上界由 52.8 dB 降到 44.8 dB（回声比噪声高 40 dB 的设定下）。'),
        ('为什么重采样 22050→16000 要用 320/441？', '最大公约数 50，约分后 16000/22050 = 320/441；先上采样 320 倍、低通、再下采样 441 倍。'),
    ]))
    o.append('</section>')
    return ''.join(o)
