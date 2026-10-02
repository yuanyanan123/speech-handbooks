#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part Ⅵ 补篇（29–33 节）：引导、跨语种克隆、语音转换、长文本、客观指标。"""
from bookutil import (fml, fig, sec, part, table, ex, note, trap, step, why, q, CF, LG, VC, LO, OB)

r0 = lambda x: '%.0f' % x
r1 = lambda x: '%.1f' % x
r2 = lambda x: '%.2f' % x
r3 = lambda x: '%.3f' % x
r4 = lambda x: '%.4f' % x
neg = lambda s: ('−' + s[1:]) if s.startswith('-') else s


def s33(n):
    N = CF['note']
    G = {r['lam']: {c['s']: c for c in r['cells']} for r in CF['grid']}
    o = [sec('s33', n, '可控性与引导：CFG 补的是什么', '深入',
             lede='说话风格、情感、说话人相似度、文本遵循——这些"可控性"在扩散与流匹配 TTS 里大多靠一个技巧：'
                  'classifier-free guidance。它到底在修什么，调大了又会发生什么？',
             tldr='条件项完美时，引导 s=2 把风格遵循从 %s%% 推到 <strong>%s%%</strong>，代价是与对方重叠的那个读法被删掉'
                  '（较大子峰占比 %s%% → %s%%，标准差 %s → %s）。条件项被学小了（λ=0.5）时，s=1 把遵循从 %s%% 补回 %s%%。'
                  '<strong>引导只看有效强度 λ(1+s)</strong>——它补的是模型没学够的条件项，补过头就是在删多样性。'
                  % (r1(N['perfect_adh']), r0(N['s2_adh']), r1(N['perfect_lo']), r1(N['s2_lo']), r2(N['perfect_sd']), r2(N['s2_sd']),
                     r1(N['weak_adh']), r1(N['weak_fix_adh'])))]
    o.append('<p>14 节讲过流匹配的向量场：给定当前位置 x 与时刻 t，网络输出"往哪个方向走"。条件生成时再多一个条件 c（风格、文本、参考说话人）：'
             '条件向量场 v<sub>c</sub>(x,t) 与无条件向量场 v<sub>u</sub>(x,t)。训练时随机丢掉条件（一部分样本把 c 置空），同一个网络就同时学会两者。'
             '<strong>引导</strong>就是采样时把两者的差放大。</p>')
    o.append(fml('引导与"有效强度"', 'cfg'))
    o.append(note('这一节的做法',
                  '<p>和 14 节一样，选一个<strong>最优向量场有闭式解</strong>的目标分布，不训练任何网络：一维"声学量"（比如归一化的基频），两种风格 A / B，每种自己是双峰，彼此在中间有重叠——'
                  'p(x|A) = 0.6 N(−1.6, 0.5²) + 0.4 N(0.2, 0.35²)，p(x|B) = 0.5 N(0.9, 0.4²) + 0.5 N(2.4, 0.5²)。'
                  '这样误差<em>只</em>来自引导强度，和"模型学得好不好"分开。要模拟"条件项学得不够"，就用 v̂<sub>c</sub> = v<sub>u</sub> + λ(v<sub>c</sub> − v<sub>u</sub>)，λ=1 完美，λ&lt;1 偏弱。'
                  '%s 个样本、%s 步 Euler。</p>' % ('{:,}'.format(CF['const']['n']), CF['const']['steps'])))
    o.append(fig('cfg', '<strong>两个小图。</strong>① 遵循率与较大子峰占比随有效强度的变化，λ = 1、0.5、0.25 三组落在同一条曲线上；'
                 '② λ=1 时不同 s 生成的分布：s 越大越窄，与风格 B 重叠的那个峰最先消失。'))
    rows = []
    for lam in CF['const']['lams']:
        for s in CF['const']['ss']:
            c = G[lam][s]
            rows.append(['λ=%g' % lam, '#%g' % s, '#%s' % r2(c['eff']), '#%s%%' % r1(c['adh']), '#%s' % r2(c['sd']),
                         '#%s%%' % r1(c['share_lo']), '#%s' % r3(c['w2'])])
    o.append(ex('实测：风格 A 的生成（遵循 = 贝叶斯判决认为样本属于 A 的比例；真分布自己是 %s%%）' % r1(N['true_adh']),
                table(['条件项', '#引导 s', '#有效强度', '#遵循', '#标准差', '#较大子峰占比', '#与真分布的 W2'], rows, cls='dp')
                + '<p>真条件分布的标准差 %s、较大子峰占比 %s%%，采样噪声地板 W2 = %s。λ(1+s) = 1 的那几行（λ=1,s=0；λ=0.5,s=1；λ=0.25,s=3）<strong>数字完全一样</strong>——'
                  '三种条件项强度、三个不同的 s，只要乘起来是 1 就等于真条件分布。</p>' % (r2(N['true_sd']), r1(N['perfect_lo']), r4(N['floor']))))
    o.append(step('引导补的是什么'))
    o.append('<p>λ=0.5 时模型只有一半的条件项：遵循只有 %s%%，与真分布的 W2 是 %s。s=1 把有效强度补到 1：遵循 %s%%，W2 回到 %s。'
             'λ=0.25 要 s=3 才补回来。<strong>现实里的网络大多是 λ&lt;1</strong>（条件 dropout 训练、条件信息在深层被稀释、数据里风格标签很噪），'
             '所以引导在实践中几乎总是要开；而且最优的 s 取决于这一个模型的 λ，不是一个通用常数。</p>'
             % (r1(N['weak_adh']), r3(N['weak_w2']), r1(N['weak_fix_adh']), r3(N['weak_fix_w2'])))
    o.append(step('补过头'))
    o.append('<p>有效强度超过 1 之后，样本不再是真条件分布：遵循升到 100%%，但<strong>多样性塌了</strong>。s=2（有效强度 3）时较大子峰占了 %s%%，'
             '另一个子峰——恰好是和风格 B 重叠的那个——几乎消失。这不是巧合：引导的方向是"离无条件分布更远"，最先被推走的就是<strong>最像对方的那一部分读法</strong>。'
             's=5（有效强度 6）时平均对数似然从 %s 掉到 %s，样本被推出了真分布的两个峰之外。</p>'
             % (r1(N['s2_lo']), r2(N['perfect_ll']), r2(N['s5_ll'])))
    o.append(trap('我原以为：引导能让生成更接近真分布',
                  '不能。条件项完美时，s 从 0 开始每加一点，与真条件分布的距离（W2）就变大：s=0.5 时 %s，s=1 时 %s，s=2 时 %s（采样噪声地板 %s）。'
                  '引导<strong>不是在改进分布估计</strong>，是在用多样性换遵循。它在实践里有用，是因为 λ&lt;1 时它在补条件项；也因为评测常常奖励"遵循"（说话人相似度、WER）——'
                  '而不奖励多样性。'
                  % (r3(G[1.0][0.5]['w2']), r3(G[1.0][1.0]['w2']), r3(G[1.0][2.0]['w2']), r4(N['floor']))))
    o.append(note('这一节没覆盖的',
                  '真实 TTS 里的条件有好几路（文本、参考说话人、风格标签），各自可以有不同的引导强度；还有对时间步分段设置强度、引导区间等变体。'
                  '这里只有一个一维、两种风格的玩具分布；可以带走的是<strong>有效强度的关系和"先删掉重叠的读法"这个方向</strong>，不是具体的 s 取值。'))
    o.append(q([
        ('条件项完美的模型上开引导，会变得更接近真分布吗？',
         '不会。s=1 时 W2 从 %s 涨到 %s。引导是在拿多样性换遵循。' % (r3(G[1.0][0.0]['w2']), r3(G[1.0][1.0]['w2']))),
        ('同一个引导强度 s=2，在不同的模型上效果一样吗？',
         '不一样：看有效强度 λ(1+s)。λ=1 时是 3（已经把较大子峰推到 %s%%），λ=0.5 时是 1.5，λ=0.25 时是 0.75（还没补够，遵循 %s%%）。'
         % (r1(G[1.0][2.0]['share_lo']), r1(G[0.25][2.0]['adh']))),
    ]))
    o.append('</section>')
    return ''.join(o)


def s34(n):
    N = LG['note']
    K = {r['key']: r for r in LG['kinds']}
    o = [sec('s34', n, '多语种与跨语种克隆', '进阶',
             lede='克隆一个中文说话人的声音去说英文——参考音频是一种语言，合成的是另一种。20 节量过房间和说话人在嵌入里的纠缠；这里再加语言这一层。',
             tldr='同一个说话人换一种语言，嵌入的余弦掉 %s，是"换人"所掉的 %s 的 <strong>%s%%</strong>；说话人确认 EER 从同语种 %s%% 涨到跨语种 <strong>%s%%</strong>。'
                  '一个完美的跨语种克隆，在 %s%% 的说话人上得分比"说同一语言的另一个人"还低。按音素均衡后这些差距基本消失。'
                  % (r3(N['raw_lang_gap']), r3(N['raw_spk_gap']), r0(100 * N['raw_ratio']), r1(N['raw_eer_same']), r1(N['raw_eer_cross']),
                     r0(N['xl_below_wrong'])))]
    o.append(note('这一节的做法',
                  '<p>在 20 节同一套"说话人 × 内容"梅尔谱上再加一个<strong>语言</strong>因子：两种语言（Z、E）使用的音素频率不同（Z 多用前四个音素，E 多用后四个）。'
                  '%d 个说话人都是双语者，每种语言 %d 条 × %s s。说话人嵌入仍是长时平均谱（和 x-vector 的一阶统计量同类）。'
                  '<strong>口音</strong>（系统性的实现偏移）没有建模，只有音素使用频率这一个语言差异——所以这里量到的是一个下限。</p>'
                  % (LG['const']['nspk'], LG['const']['nutt'], r0(LG['const']['sec']))))
    o.append(fml('长时平均谱里藏着语言', 'lang'))
    o.append(fig('lang', '<strong>两个小图。</strong>① 四类配对的余弦均值，原始嵌入与音素均衡嵌入；② 说话人确认 EER。'))
    o.append(ex('实测：同语种与跨语种',
                table(['嵌入', '#同人同语种', '#同人跨语种', '#异人同语种', '#异人跨语种', '#EER 同语种', '#EER 跨语种'],
                      [[r['name'], '#%s' % r4(r['mean']['同人同语种']), '#%s' % r4(r['mean']['同人跨语种']), '#%s' % r4(r['mean']['异人同语种']),
                        '#%s' % r4(r['mean']['异人跨语种']), '#%s%%' % r1(r['eer_same']), '#%s%%' % r1(r['eer_cross'])] for r in LG['kinds']], cls='dp')
                + '<p>原始嵌入里，"同人跨语种"（%s）比"同人同语种"（%s）低 %s——是"异人同语种"掉的幅度（%s）的 %s%%。'
                  '<strong>语言在嵌入里的分量和半个说话人差不多。</strong></p>'
                % (r3(K['raw']['mean']['同人跨语种']), r3(K['raw']['mean']['同人同语种']), r3(N['raw_lang_gap']), r3(N['raw_spk_gap']), r0(100 * N['raw_ratio']))))
    o.append(step('评测会怎么判一个完美的克隆'))
    o.append('<p>假设克隆系统完美：合成的就是同一个人说另一种语言。参考是语言 Z 的一条，合成是语言 E 的另一条：相似度 <strong>%s</strong>；'
             '如果合成的是说同一语言 Z 的<em>另一个人</em>：%s。<strong>%s%% 的说话人上，完美的跨语种克隆比说同语言的另一个人得分还低</strong>。'
             '换成音素均衡的嵌入（每个音素等权求均值，需要音素对齐），这个比例降到 %s%%。</p>'
             % (r3(N['perfect_xl']), r3(N['wrong_sl']), r0(N['xl_below_wrong']), r0(N['bal_xl_below_wrong'])))
    o.append(trap('我原以为：同语种评测的 EER 就能代表跨语种',
                  '不能。原始嵌入同语种 EER %s%%、跨语种 %s%%，差 <strong>%.1f 倍</strong>。更要警惕的是"偷懒协议"：目标取同语种、冒充者取跨语种，EER 只有 %s%%——'
                  '语言差异白送了一道分界线。克隆系统报告"说话人相似度"时，要问清楚<strong>参考和合成是不是同一种语言、冒充者用的是哪一种</strong>。'
                  % (r1(N['raw_eer_cross']), r1(N['raw_eer_same']), N['raw_eer_cross'] / N['raw_eer_same'], r1(N['raw_eer_lazy']))))
    o.append(note('这一节没覆盖的',
                  '口音泄漏（克隆出的英文带着中文口音，或反过来）、混合语种文本里的切换、多语种 G2P 与文本归一化的共用问题。这里只量了语言因子进到说话人嵌入里的那一部分，'
                  '而且是用一个手工构造的嵌入；真实的说话人编码器（ECAPA 之类）可能把一部分语言信息学掉，也可能学进更多——要在目标语言对上重新量。'))
    o.append(q([
        ('参考音频是中文、要合成英文，说话人相似度分数低，是克隆失败了吗？',
         '不一定。嵌入里混着语言：完美的跨语种克隆在 %s%% 的说话人上得分比"同语言的另一个人"还低。先用音素均衡的嵌入或语言对内的校准重新评分。' % r0(N['xl_below_wrong'])),
        ('怎么降低评测里语言的影响？',
         '让嵌入对内容均衡：每个音素等权求均值（本节 %s → %s 的语言差距），或者在每个语言对内单独设阈值与校准。'
         % (r4(N['raw_lang_gap']), r4(N['bal_lang_gap']))),
    ]))
    o.append('</section>')
    return ''.join(o)


def s35(n):
    N = VC['note']
    R = {r['k']: r for r in VC['rows']}
    o = [sec('s35', n, '语音转换：把内容和说话人拆开', '深入',
             lede='语音转换（VC）：保持说的内容，换成另一个人的声音。几乎所有方案的第一步都是"把内容和说话人拆开"。最朴素的拆法是把编码器的输出压窄——压到多窄？',
             tldr='压到 k=1–2：说话人几乎被抹掉（编码里 %s%%，随机 %s%%），输出 %s%% 被认作目标——但<strong>音素也只剩 %s%%</strong>（探针上限 %s%%）。'
                  'k≥6：内容保持 %s%%，但解码器不听说话人嵌入，输出像目标只有 %s%%。<strong>没有哪个 k 同时拆开</strong>，最好的折中 k=%s 是 %s%% / %s%%。'
                  % (r0(N['k1_spk']), r0(N['chance_spk']), r0(100 * R[2]['tgt_hit']), r0(N['k2_ph']), r0(N['probe_ph']),
                     r0(N['k8_ph']), r0(N['k8_hit']), N['best_k'], r0(N['best_hit']), r0(N['best_ph'])))]
    o.append(note('这一节的做法',
                  '<p>同一套"说话人 × 内容"梅尔谱（20 节那套，不带房间）：%d 个说话人，训练 %d 条、留出 %d 条，每条 %s s。<strong>真值是现成的</strong>：同一段内容、换成目标说话人，就是转换的标准答案（生成器是确定的）。</p>'
                  '<p>模型是帧级自编码器：编码器 80→128→k（线性瓶颈），解码器 [k 维编码 ‖ 说话人嵌入]→128→80，纯 numpy、手写反传，只用重建误差训练。'
                  '没有对抗训练、没有说话人归一化，只有"瓶颈"这一个旋钮。评判用两个在<em>真实</em>梅尔帧上训的探针：谁在说（真实留出帧上 %s%%）、说的是什么音素（%s%%）。</p>'
                  % (VC['const']['nspk'], VC['const']['ntr'], VC['const']['nte'], r0(VC['const']['sec']), r0(N['probe_spk']), r0(N['probe_ph']))))
    o.append(fml('转换与瓶颈', 'vc'))
    o.append(fig('vc', '<strong>两个小图。</strong>① 转换后的输出被认作目标说话人 / 音素是否保持 / 仍像源；② 编码里剩下的说话人与音素信息（线性探针）。'))
    o.append(ex('实测：瓶颈维数 k（%d 个种子的均值）' % len(VC['const']['seeds']),
                table(['#k', '#重建误差', '#编码里说话人', '#编码里音素', '#像目标', '#仍像源', '#音素保持', '#离标准答案'],
                      [['#%d' % r['k'], '#%s' % r3(r['recon']), '#%s%%' % r0(100 * r['code_spk']), '#%s%%' % r0(100 * r['code_ph']),
                        '#%s%%' % r0(100 * r['tgt_hit']), '#%s%%' % r0(100 * r['src_keep']), '#%s%%' % r0(100 * r['ph_keep']),
                        '#%s' % r3(r['conv_mse'])] for r in VC['rows']], cls='dp')
                + '<p>说话人随机 %s%%、音素随机 %s%%。"离标准答案"是转换结果与目标说话人说同一内容的真值梅尔的均方误差；直接拷贝源的是 %s。</p>'
                % (r0(N['chance_spk']), r0(N['chance_ph']), r3(N['copy_mse']))))
    o.append(step('两头都有各自的失效'))
    o.append('<p><strong>瓶颈太窄</strong>（k=1–2）：编码里的说话人信息被挤掉，解码器只能靠说话人嵌入来决定声音，所以输出很像目标（%s%%）；'
             '可是内容也被一起挤掉——音素保持只有 %s%%（距离探针上限 %s%% 还差很多）。<strong>瓶颈太宽</strong>（k≥6）：内容完整（%s%%），'
             '但编码里还剩说话人（%s%%），解码器发现"直接从编码里拿"比"听嵌入"容易，于是<strong>不听嵌入</strong>——输出像目标只有 %s%%；k=32 时 %s%% 的输出仍像源说话人。</p>'
             % (r0(100 * R[2]['tgt_hit']), r0(N['k2_ph']), r0(N['probe_ph']), r0(N['k8_ph']), r0(N['k8_spk']), r0(N['k8_hit']), r0(N['k32_keep'])))
    o.append(trap('我原以为：重建误差越低，转换越好',
                  '重建误差一路变好（k=1 的 %s → k=32 的 %s），转换质量却是倒 U：k=4 是折中。更要警惕的是<strong>离标准答案的均方误差</strong>：k=1 是 %s，'
                  '比直接把源拷过去（%s）还低——它是靠把内容丢掉、输出一个"目标说话人的平均谱"换来的。所以 MSE 不能单独当转换质量的指标：'
                  '它奖励"安全地平均"，而不是"内容对、声音对"。'
                  % (r3(R[1]['recon']), r3(R[32]['recon']), r3(N['k1_mse']), r3(N['copy_mse']))))
    o.append(note('这一节没覆盖的',
                  '真实 VC 的拆法还有对抗训练去掉编码里的说话人信息、离散化（量化到 token 之后说话人信息自然少）、预训练自监督单元（HuBERT 单元）当内容、说话人归一化，以及用 TTS 当解码器。'
                  '本节只量了最朴素的一个旋钮，并且是帧级、没有上下文——这也让内容更难保持。可以带走的是<strong>怎么量</strong>：两个探针 + 一个现成的标准答案，'
                  '而不是 k=4 这个数。'))
    o.append(q([
        ('把编码器瓶颈压到最窄，能把说话人拆干净吗？',
         '能拆掉说话人（编码里 %s%%），但内容一起丢了（音素保持 %s%%）。单纯收窄瓶颈没有同时拆开的档位。' % (r0(N['k1_spk']), r0(N['k2_ph']))),
        ('转换结果离标准答案的 MSE 很低，说明转换得好吗？',
         '不一定。k=1 的 MSE（%s）比直接拷贝源（%s）还低，因为它输出了一个内容被丢掉的"平均谱"。要同时看"像不像目标"和"内容在不在"。' % (r3(N['k1_mse']), r3(N['copy_mse']))),
    ]))
    o.append('</section>')
    return ''.join(o)


def s36(n):
    N = LO['note']
    S = {(r['nq'], r['sec']): r for r in LO['single']}
    C = {(r['c'], r['p']): r for r in LO['chunk']}
    o = [sec('s36', n, '长文本：上下文、算力与分段', '进阶',
             lede='有声书、新闻播报、长篇对话——文本往往比模型一次吃得下的长得多。一次生成多长，上下文、显存与算力各自在哪里撞墙？分段又要付什么？',
             tldr='每个 token 的线性层 %s MMAC，注意力的平方项在 n = 12d = <strong>%s token</strong>（约 %s s，nq=4）处追上线性层。'
                  '十分钟一次生成：%s token、KV <strong>%s GB</strong>、注意力是线性层的 %s 倍。分成 30 s 一段、各带前一段 5 s 做提示：每段 KV %s GB，总乘加只有一次生成的 <strong>%s%%</strong>。'
                  % (r0(N['lin_mmac']), '{:,}'.format(N['cross_tok']), r0(N['cross_sec_nq4']), '{:,}'.format(N['m10_tok']), r1(N['m10_kv']),
                     r1(N['m10_ratio']), r2(N['c30p5_kv']), r1(100 * N['c30p5_rel'])))]
    o.append(note('这一节的做法',
                  '<p>不训练任何东西，把乘加和字节数点出来（和 23 节同一个做法）。输入里<strong>只有 token 速率是本书实测的</strong>（19 节 RVQ：每秒 %.1f 帧 × 码本级数；nq=4 即 %.1f token/s，nq=8 即 %.1f）。'
                  '解码器的形状是<strong>假设</strong>的一个典型值（%d 层、d=%d、fp16，仿 LLM-TTS 常见规模）；换一组参数把 <code>demo_long.py</code> 开头的常量改一行重跑即可——'
                  '重点是平方项什么时候压过线性项，不是小数点后一位。</p>'
                  % (LO['const']['fps'], N['tok_s4'], N['tok_s8'], LO['const']['layers'], LO['const']['d'])))
    o.append(fml('注意力与线性层的账', 'longctx'))
    o.append(fig('long', '<strong>两个小图。</strong>① 一次生成 D 秒的 KV 显存；② 注意力乘加与线性层乘加之比。'))
    rows = []
    for nq in (1, 4, 8):
        for sec_ in (10, 30, 120, 600, 3600):
            r = S[(nq, sec_)]
            rows.append(['nq=%d · %s' % (nq, ('%d s' % sec_) if sec_ < 3600 else '1 h'), '#%s' % '{:,}'.format(r['tokens']),
                         '#%s GB' % r2(r['kv_gb']), '#%s T' % r2(r['att_tmac']), '#%s T' % r2(r['lin_tmac']), '#%s×' % r2(r['att_over_lin'])])
    o.append(ex('实测（计算）：一次生成',
                table(['码本级数 · 时长', '#token 数', '#KV 显存', '#注意力乘加', '#线性层乘加', '#注意力 / 线性'], rows, cls='dp')
                + '<p>10 秒（nq=4）是 %s token，注意力只有线性层的 %s；到两分钟已经是 %s 倍。<strong>一小时有声书一次生成要 %s 万个 token、KV %s GB</strong>——没有哪个设备放得下，而且早就在训练长度之外。</p>'
                % ('{:,}'.format(N['tok_10s_nq4']), r2(S[(4, 10)]['att_over_lin']), r1(S[(4, 120)]['att_over_lin']),
                   r0(N['h1_nq4_tok'] / 10000), r0(N['h1_nq4_kv']))))
    o.append(step('分段'))
    crow = []
    for c in (10, 30, 60, 120):
        for p in (0, 5):
            r = C[(c, p)]
            crow.append(['%d s + 提示 %d s' % (c, p), '#%d' % r['chunks'], '#%s' % '{:,}'.format(r['ctx_tok']), '#%s GB' % r2(r['kv_gb']),
                         '#%s T' % r1(r['total_tmac']), '#%s%%' % r1(100 * r['rel'])])
    o.append(ex('实测（计算）：十分钟、nq=4 分段生成（每段带前一段末尾的 p 秒当提示）',
                table(['分段', '#段数', '#每段上下文 token', '#KV 显存', '#总乘加', '#相对一次生成'], crow, cls='dp')
                + '<p>一次生成十分钟是 %s T 乘加、KV %s GB。分成 30 s 一段，每段 %s token、KV %s GB，总乘加 <strong>%s%%</strong>；再带 5 s 提示只多花 %s%% 的乘加'
                  '（提示 token 只前向一次）、上下文长 %s token。<strong>段越短越省，但每个边界都是一次韵律的衔接</strong>——提示越长，衔接越连贯，代价越大。</p>'
                % (r1(LO['single10min']['att_tmac'] + LO['single10min']['lin_tmac']), r1(N['m10_kv']), '{:,}'.format(N['c30p5_ctx']), r2(N['c30p5_kv']),
                   r1(100 * N['c30p5_rel']), r1(100 * (N['c30p5_rel'] - N['c30p0_rel']) / N['c30p0_rel']), '{:,}'.format(N['c30p5_ctx'] - 30 * int(N['tok_s4'])))))
    o.append(trap('我原以为：长文本只是"更慢"',
                  '不是更慢，是<strong>换了一种复杂度</strong>。短上下文里线性层占主导，成本和长度成正比；超过 n = 12d 之后注意力的平方项占主导，十分钟是线性层的 %s 倍。'
                  '这也是流式（22 节）和长文本不是同一个问题：流式关心首包延迟，长文本关心上下文随时长的平方增长。'
                  % r1(N['m10_ratio'])))
    o.append(note('这一节没覆盖的',
                  '分段边界的<strong>韵律衔接</strong>（句间停顿、基频的重置与延续）、一次生成越长<strong>漏词与复读</strong>的概率怎么随长度涨（21 节那组温度实验只给了单句长度）、'
                  '稀疏 / 滑窗注意力与状态空间模型这类绕开平方项的结构，都没有量。边界处声码器的连续性见 22 节。'
                  '这一节只回答了"一次放不放得下、分段省多少"，没有回答"分段听起来怎么样"——后者要听测。'))
    o.append(q([
        ('为什么长文本不能一次生成，哪怕显存够用？',
         '注意力的平方项在 n=12d=%s token 之后占主导：十分钟是线性层的 %s 倍。而且训练长度之外的位置，质量没有保证。' % ('{:,}'.format(N['cross_tok']), r1(N['m10_ratio']))),
        ('分段带 5 秒提示，算力多花多少？',
         '30 s 一段时只多花 %s%% 的乘加（提示只前向一次），换来边界处的韵律上下文。' % r1(100 * (N['c30p5_rel'] - N['c30p0_rel']) / N['c30p0_rel'])),
    ]))
    o.append('</section>')
    return ''.join(o)


def s37(n):
    N = OB['note']
    t = OB['tau']
    R = {r['key']: r for r in OB['rows']}
    o = [sec('s37', n, '客观指标：和参考比，比的是什么', '进阶',
             lede='26 节算过听测要多少人；听测贵，所以大家用 MCD、基频误差、LSD 这些"和参考比"的客观指标。它们同意彼此吗？它们在罚什么？',
             tldr='三个指标的排序几乎互不相关（Kendall τ：MCD 与 F0 %s，MCD 与 LSD %s，F0 与 LSD %s）。'
                  '一条<strong>合法的另一种读法</strong>：MCD（带 DTW 对齐）%s dB 排第 %s，不对齐 %s dB，F0 误差 %s cents 排第 %s——同一条合法输出，三个指标给出三种判决。'
                  % (neg('%+.2f' % t['mcd-f0']), neg('%+.2f' % t['mcd-lsd']), neg('%+.2f' % t['f0-lsd']), r1(N['legal_mcd']), N['legal_rank_mcd'],
                     r0(N['legal_mcd_raw']), r0(N['legal_f0']), N['legal_rank_f0']))]
    o.append(note('这一节的做法',
                  '<p>参考：一句话（ttssim 合成，音素与时长已知，加 −60 dB 底噪）。六种候选：<strong>合法的另一种读法</strong>（同一串音素，语速 0.82–1.22 倍、各音素时长各自抖动、基频中枢 98–148 Hz，%d 种的均值）、'
                  '声码器金属音（非线性失真 + 周期性调幅）、过平滑（对数谱沿时间平滑 3 帧）、加噪 20 dB、变速变调 ×1.03、4 kHz 低通。'
                  '三个参考式指标：MCD（13 阶梅尔倒谱，带 DTW 对齐 / 不对齐）、基频 RMSE（cents，取生成器真值，所以它<strong>只反映韵律、对波形质量完全不敏感</strong>）、LSD（STFT 对数谱距离，DTW 对齐）。</p>'
                  '<p><strong>这一节没有听测</strong>：只能回答"指标之间是否一致"，不能回答"哪个排序对"。</p>' % OB['const']['ncand']))
    o.append(fml('三个指标', 'mcd'))
    o.append(fig('obj', '<strong>六种候选 × 四列。</strong>格内是数值和名次（1 = 最像参考），橙色行是"合法的另一种读法"，颜色越深越差。'))
    o.append(ex('实测：六种候选的指标与名次',
                table(['候选', '#MCD(DTW) dB', '#名次', '#MCD(不对齐)', '#F0 RMSE cents', '#名次', '#LSD(DTW)', '#名次'],
                      [[r['name'], '#%s' % r1(r['mcd']), '#%d' % r['rank_mcd'], '#%s' % r1(r['mcd_raw']), '#%s' % r0(r['f0']), '#%d' % r['rank_f0'],
                        '#%s' % r3(r['lsd']), '#%d' % r['rank_lsd']] for r in OB['rows']], cls='dp')
                + '<p>名次相同表示数值并列（按显示精度）。Kendall τ：MCD–F0 %s，MCD–LSD %s，F0–LSD %s；对齐前后的 MCD 名次也只有 %s。</p>'
                % tuple(neg('%+.2f' % t[k]) for k in ('mcd-f0', 'mcd-lsd', 'f0-lsd', 'mcd-mcd_raw'))))
    o.append(step('各自在罚什么、对什么视而不见'))
    o.append('<p><strong>MCD（对齐）</strong>把合法的另一种读法判成很近（%s dB，第 %d 名），因为 DTW 把时长差抹掉了；<strong>不对齐的 MCD</strong>同一条输出是 %s dB，'
             '说明它罚的主要是时间错位。<strong>F0 误差</strong>把它判成最差（%s cents）——合法读法的基频中枢本来就可以相差 ±20%%——而对声码器金属音、加噪、低通都接近 0。'
             '<strong>LSD</strong>对低通最敏感（%s，排最后）而对过平滑最宽容。每个指标只覆盖"自然度"的一个方向。</p>'
             % (r1(N['legal_mcd']), N['legal_rank_mcd'], r1(N['legal_mcd_raw']), r0(N['legal_f0']), r3(N['lp_lsd'])))
    o.append(trap('我原以为：多看几个客观指标就能代替听测',
                  '这一节的结果反过来：三个指标排序几乎互不相关，加起来也不构成一个"自然度"。更要紧的是 1 节讲过的那件事——<strong>TTS 的答案是一个分布</strong>。'
                  '所有"和一条参考比"的指标都在把"合法的另一种读法"当成误差：F0 误差把它判为最差，不对齐的 MCD 给出 %s dB。'
                  '参考式指标在 TTS 上只适合<strong>同一个系统、同一条参考、改一个旋钮</strong>的回归测试（比如声码器换一版），不适合比较两个系统，更不适合替代听测。'
                  % r0(N['legal_mcd_raw'])))
    o.append(note('这一节没覆盖的',
                  '不依赖参考的指标（基于 MOS 预测器、基于 ASR 的 WER / CER 的可懂度）、说话人相似度（20、30 节）、基于嵌入的分布距离（FAD 之类）。'
                  '这里的候选是手工构造的几种退化，不是真实系统的输出；"过平滑"等是对谱的变换而不是真的回归模型的结果。'
                  '要判断一个指标到底有没有用，必须有听测作对照——本书没有。'))
    o.append(q([
        ('MCD 低，这个合成就一定自然吗？',
         '不一定。MCD（带 DTW）把一条合法的另一种读法判得很近（%s dB），也把声码器金属音判得不算最差（第 %d 名）；它主要反映谱包络，对基频、时长与细节失真不敏感。' % (r1(N['legal_mcd']), N['metal_rank_mcd'])),
        ('能用 F0 误差评价声码器吗？',
         '不能。F0 取自生成器时，声码器金属音、加噪、低通的 F0 误差都接近 0——它只看韵律，对波形质量完全不敏感。'),
    ]))
    o.append('</section>')
    return ''.join(o)


def build(num):
    o = [part('Part Ⅵ', '补篇', '可控性、跨语种、语音转换、长文本与客观指标——前五个部分没有展开的五件事')]
    o.append(s33(num['s33']))
    o.append(s34(num['s34']))
    o.append(s35(num['s35']))
    o.append(s36(num['s36']))
    o.append(s37(num['s37']))
    return ''.join(o)
