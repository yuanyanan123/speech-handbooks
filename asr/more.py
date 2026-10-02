#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""34–38 节：补篇——数据增强、说话人自适应、置信度与校准、蒸馏与压缩、长音频切分。

   这五节共用 toylib.py 里的"玩具声学世界"：9 类帧级音素分类器，真训、真测，
   不是语音识别（没有词、没有语言模型、没有解码），量的是声学模型这一层的行为。
"""
from bookutil import (fml, fig, sec, table, ex, note, trap, step, why, q, AG, AP, CF, KD, VD)

r0 = lambda x: '%.0f' % x
r1 = lambda x: '%.1f' % x
r2 = lambda x: '%.2f' % x
r3 = lambda x: '%.3f' % x
neg = lambda s: ('−' + s[1:]) if s.startswith('-') else s

TOY = ('34–38 节共用同一个"玩具声学世界"（<code>toylib.py</code>）：源-滤波合成的语音（5 个元音、3 个擦音、静音），'
       '40 维对数梅尔、前后各拼 2 帧，纯 numpy 的 MLP 做 9 类帧分类，真训、真测。'
       '<strong>它不是语音识别</strong>——没有词、没有语言模型、没有解码。量的是声学模型这一层在这些问题上的行为；'
       '绝对数值别和真实系统比，可比的是形状、量级和趋势。')


def s46(n):
    A = AG['note']
    R = {r['key']: r for r in AG['rows']}
    o = [sec('s46', n, '数据增强：每种做法覆盖哪一块', '进阶',
             lede='标注永远不够，所以大家都加增强。但"加了增强"不是一个答案——噪声、混响、变速、SpecAugment、'
                  '归一化各管各的，覆盖不到的地方一点都帮不上。',
             tldr='只用干净数据，白噪 10 dB 下帧准确率 %s%%；加噪之后 %s%%，但<strong>没见过的 babble 噪声只有 %s%%</strong>。'
                  '混响增强对加噪没用，反过来也是。<strong>零成本的逐条 CMVN</strong> 在没见过的条件上比任何单一增强都强，'
                  '和增强叠加后最好。'
                  % (r0(A['clean_white10']), r0(A['noise_white10']), r0(A['noise_babble10'])))]
    o.append(note('这一节的底盘', '<p>' + TOY + '</p>'))
    o.append('<p>先把"增强"拆开。训练里能做的事有五种：往波形里加噪声、卷一条房间冲激响应、变速（同时改音高和共振峰）、'
             '在特征上盖掉一些频带和时间段（SpecAugment），以及对每条语音的特征做均值方差归一化（CMVN）。'
             '下面每一种训练集都是<strong>同样的 %d 条底料（%s 分钟）× %d 份</strong>，只在每一份怎么处理上不同。'
             % (AG['const']['ntr'], r1(AG['const']['train_min'] / AG['const']['copies']), AG['const']['copies']) + '</p>')
    o.append(fml('逐条 CMVN：为什么它能顶一部分增强', 'cmvn'))
    o.append(fig('aug', '<strong>十种测试条件 × 八种训练做法。</strong>绿色标题是训练里出现过的类型，红色是没见过或超出范围的。'))
    o.append(ex('实测：帧准确率（%%，%d 个种子的均值）' % len(AG['const']['seeds']),
                table(['训练做法', '#干净', '#见过的四项平均', '#没见过的五项平均', '#电话带宽'],
                      [[r['name'], '#%s' % r1(r['acc']['clean']), '#%s' % r1(r['seen']), '#%s' % r1(r['unseen']),
                        '#%s' % r1(r['acc']['tel'])] for r in AG['rows']], cls='dp')
                + '<p>"见过的四项"取白噪 10/0 dB、混响 0.5 s、×0.9 语速；"没见过的五项"取 babble 10/0 dB、混响 1.2 s、×1.25 语速、电话带宽。'
                  '十种条件逐项的数字在上面的图里，完整表在 <code>demo_aug.json</code>。</p>'))
    o.append(step('各管各的'))
    o.append('<p>噪声增强把白噪 10 dB 从 %s%% 拉到 %s%%，但对混响 0.5 s 只有 %s%%（混响增强是 %s%%），对电话带宽 %s%%（只用干净 %s%%）。'
             '<strong>增强只在它模拟的那一类失配上有效</strong>；"噪声增强会让模型更鲁棒"这句话在没见过的噪声上不成立——'
             'babble 10 dB 只从 %s%% 到 %s%%。这和单通道增强那本书里"训练噪声覆盖不到的场景，表现不是缓慢变差而是掉到接近不处理"是同一件事。</p>'
             % (r0(A['clean_white10']), r0(A['noise_white10']), r0(A['noise_rev05']), r0(A['rev_rev05']),
                r0(A['noise_tel']), r0(R['clean']['acc']['tel']), r0(A['clean_babble10']), r0(A['noise_babble10'])))
    o.append(trap('我原以为：全部叠加就是最强的',
                  '全部叠加（噪声 + 混响 + 变速 + SpecAugment）在见过的类型上最好，干净数据却从 %s%% 掉到 %s%%，'
                  '而<strong>电话带宽反而更差</strong>（%s%%，只用干净是 %s%%）——叠加的增强里没有带宽限制这一项，多出来的变化只让模型更依赖它见过的那些失真。'
                  '把逐条 CMVN 加上之后电话带宽到 %s%%、没见过的平均 %s%%（全部叠加是 %s%%）。'
                  % (r0(A['clean_clean']), r0(A['all_clean']), r1(A['all_tel']), r0(R['clean']['acc']['tel']),
                     r1(A['allcmvn_tel']), r1(A['allcmvn_unseen']), r1(A['all_unseen']))))
    o.append(trap('我原以为：SpecAugment 是通用的鲁棒性手段',
                  '在这里它几乎没有任何效果：干净 %s%%、babble 10 dB %s%%（不加是 %s%%）。'
                  'SpecAugment 的作用是正则化大模型、防止过拟合；这里的模型只有 %s 个参数，没有可过拟合的余地。'
                  '真实大模型上它的价值是另一回事，本节没有量。'
                  % (r0(A['specaug_clean']), r0(A['specaug_babble10']), r0(A['clean_babble10']), '{:,}'.format(AG['const']['nparams']))))
    o.append(note('局限',
                  '白噪 10 dB 下"只用干净数据"只剩 %s%% 是这个玩具世界里特别脆弱的一种：干净训练集里静音是（近乎）零，噪声一加，所有静音帧都被当成擦音。'
                  '真实系统不会这么极端，但方向一样：训练时没有的条件，推理时就是未知。'
                  '这里的增强强度（SNR 0–20 dB、T60 0.2–0.9 s、变速 0.9–1.1）是我设的；范围怎么取是一个要按目标场景去定的参数。' % r0(A['clean_white10'])))
    o.append(q([
        ('训练里加了噪声增强，上线后遇到没见过的噪声类型会怎样？',
         '只能期待一点点：本实验里 babble 10 dB 从 %s%% 到 %s%%。要覆盖就得把那类噪声放进训练或测试集里，不能指望"加噪"这个动作本身泛化。'
         % (r0(A['clean_babble10']), r0(A['noise_babble10']))),
        ('零成本的逐条 CMVN 为什么能顶一部分增强？',
         '信道（和一部分整体增益）在对数谱里是加性常数，减掉每条语音的均值就把它去掉了。它对电话带宽这类"没见过的信道"有效（%s%%），'
         '对共振峰整体移位（说话人声道）没用，那是平移不是偏置。' % r0(A['cmvn_tel'])),
    ]))
    o.append('</section>')
    return ''.join(o)


def s47(n):
    A = AP['note']
    R = {r['key']: r['acc'] for r in AP['rows']}
    o = [sec('s47', n, '说话人与领域自适应', '进阶',
             lede='换一个说话人（小孩、老人、口音很重的人），模型会掉多少？给它多少数据、调哪一层才划算？'
                  '没有标注的时候能不能自己教自己？',
             tldr='声道长度因子 |v| 到 0.35，源模型从 %s%% 掉到 %s%%。给 3 秒标注：全部微调回到 <strong>%s%%</strong>，'
                  '只调第一层 %s%%，只调最后一层 %s%%——<strong>失配在输入端，改输出端补不上</strong>。'
                  '代价是原说话人从 %s%% 掉到 %s%%。无标注的伪标签自训练几乎没用（%s%% → %s%%）。'
                  % (r0(A['src_acc']), r0(A['far_acc']), r0(A['all_3']), r0(A['first_3']), r0(A['last_3']),
                     r0(A['forget_none']), r0(A['forget_all_3']), r0(A['none_tgt']), r0(A['pseudo_9'])))]
    o.append(note('这一节的底盘', '<p>' + TOY + '</p>'
                  '<p>"换说话人"在这里是真的共振峰整体缩放：声道长度因子 e<sup>v</sup>，v&gt;0 声道短、共振峰整体往高频走（像小孩），v&lt;0 反过来。'
                  '源模型只见过 |v|&lt;0.1 的 10 个说话人；目标是 v = %s 的四个。</p>'
                  % '、'.join(neg('%+.2f' % v) for v in AP['const']['tgt_v'])))
    o.append(fml('说话人失配的数学形状', 'vtl'))
    o.append(step('失配曲线'))
    o.append(fig('adapt', '<strong>三个小图。</strong>① 源模型的准确率随声道因子；② 给目标说话人不同秒数的标注，各种自适应方式的准确率；'
                 '③ 调完之后原说话人还剩多少。'))
    o.append(step('给多少数据、调哪里'))
    secs = ['3', '9', '18', '45', '90']
    o.append(ex('实测：目标说话人的帧准确率（%%，4 个目标说话人 × %d 个种子；每条 3 秒）' % len(AP['const']['seeds']),
                table(['自适应方式'] + ['#%s s' % s for s in secs],
                      [[r['name']] + ['#%s' % r1(r['acc'][s]) for s in secs] for r in AP['rows']], cls='dp')
                + '<p>全部微调 3 秒就到 %s%%，之后几乎是平的；<strong>只调第一层几乎一样好</strong>（%s%% → %s%%）——失配是输入端的一个整体平移，'
                  '一个输入层的线性变换就能吸收。只调最后一层要 %s 秒才追上，因为它拿到的还是错位的特征。</p>'
                % (r0(A['all_3']), r0(A['first_3']), r0(A['first_90']), '90')))
    o.append(step('代价：忘掉原来的'))
    forg = ['none', 'all', 'mix', 'last', 'first']
    nm = {r['key']: r['name'] for r in AP['rows']}
    o.append(ex('实测：调完之后原说话人（源域）的准确率（%）',
                table(['方式'] + ['#%s s' % s for s in secs],
                      [[nm[k] if k in nm else '不自适应'] + ['#%s' % r1(AP['forget'][k][s]) for s in secs] for k in forg], cls='dp')
                + '<p>全部微调把源域从 %s%% 砸到 <strong>%s%%</strong>，而且和用了多少目标数据无关（3 秒和 90 秒一样）——忘掉原来的不是数据量的问题，'
                  '是整个网络都往目标那边挪了。混入等量源数据（复习）能压住：源域 %s%%，目标侧只少 %s 个点。'
                  '只调最后一层的遗忘是随数据量慢慢涨的（%s%% → %s%%）。</p>'
                % (r0(A['forget_none']), r0(A['forget_all_3']), r0(A['forget_mix_3']), r1(A['all_3'] - A['mix_3']),
                   r0(AP['forget']['last']['3']), r0(A['forget_last_90']))))
    o.append(trap('我原以为：没有标注也能自己教自己',
                  '用源模型自己的高置信（&gt;%.1f）预测当伪标签、微调一轮：3 秒 %s%%、9 秒 %s%%、90 秒 %s%%，和不自适应的 %s%% 几乎一样。'
                  '我的解释（没有单独量）：失配越大，高置信的帧里错的比例越高，模型把自己的错误当成对的再学一遍（确认偏差）。'
                  '逐条 CMVN 对声道失配也没用（%s%%）：那是平移，不是偏置。无标注自适应得靠别的信号（比如另一个更强的模型、或文本约束），不能只靠自己的置信度。'
                  % (AP['const']['pseudo_thr'], r0(R['pseudo']['3']), r0(R['pseudo']['9']), r0(R['pseudo']['90']),
                     r0(A['none_tgt']), r0(A['cmvn_tgt']))))
    o.append(note('这一节没覆盖的',
                  '真实系统里的自适应还有 i-vector / x-vector 作为额外输入、LoRA 与 adapter、领域自适应（专业词汇、场景噪声）、测试时自适应。'
                  '这里的"说话人"只有声道长度与基频两个维度，口音与语言风格都没有；所以数字夸大了"3 秒就够"——'
                  '真实说话人的差异是高维的。可以带走的是形状：<strong>改哪一层要对着失配发生的位置选</strong>，以及<strong>自适应一定要想好怎么不忘</strong>。'))
    o.append(q([
        ('只有 5 秒目标说话人的标注，应该调哪里？',
         '失配出现在输入端（共振峰整体移位）时，调第一层（%s%%）和全部微调（%s%%）都够；只调最后一层不够（%s%%）。'
         % (r0(R['first']['9']), r0(R['all']['9']), r0(R['last']['9']))),
        ('微调之后原来的用户体验变差了，怎么办？',
         '混入等量原数据一起调（源域 %s%%，目标 %s%%），或者只调输入层、保留后面的层。全部微调会把源域砸到 %s%%。'
         % (r0(A['forget_mix_3']), r0(A['mix_3']), r0(A['forget_all_3']))),
    ]))
    o.append('</section>')
    return ''.join(o)


def s48(n):
    A = CF['note']
    P = CF['models']['plain']['conds']
    Rb = CF['models']['robust']['conds']
    names = {c['key']: c['name'] for c in CF['conds']}
    o = [sec('s48', n, '置信度、校准与拒识', '进阶',
             lede='模型说"我有 95% 把握"的时候，对的比例是多少？识别不出来的时候，它知道自己不知道吗？',
             tldr='干净时准确率 %s%%、置信度 %s%%，几乎对得上。<strong>白噪 10 dB 下准确率只剩 %s%%，置信度仍有 %s%%</strong>；'
                  '用干净验证集拟合的温度几乎救不了（ECE %s → %s）。此时置信度没有区分对错的能力（AUROC %s），'
                  '"只收最高的一半"准确率 %s%%。拒识救不了一个整体失配的模型。'
                  % (r0(A['clean_acc']), r0(A['clean_conf']), r0(A['w10_acc']), r0(A['w10_conf']), r0(A['w10_ece']),
                     r0(A['w10_eceT']), r2(A['w10_auc']), r0(A['w10_at50'])))]
    o.append(note('这一节的底盘', '<p>' + TOY + '</p><p>这里的"置信度"是帧级 softmax 的最大概率。词级、句级的置信度（lattice 后验、N-best 一致性）是另外的东西，本节没有量。</p>'))
    o.append(fml('校准的两个量：ECE 与温度', 'ece'))
    o.append(fig('conf', '<strong>三个小图。</strong>① 准确率与平均置信度；② 只收置信度最高的一半时的准确率；'
                 '③ 置信度判断对错的 AUROC（蓝：只见过干净的模型；橙：增强过的）。'))
    o.append(ex('实测：只见过干净语音的模型（%d 个种子）' % len(CF['const']['seeds']),
                table(['条件', '#准确率', '#置信度', '#ECE', '#干净 T', '#自拟合 T', '#收 50%', '#AUROC'],
                      [[names[c['key']], '#%s' % r1(P[c['key']]['acc']), '#%s' % r1(P[c['key']]['conf']),
                        '#%s' % r1(P[c['key']]['ece']), '#%s' % r1(P[c['key']]['ece_T']), '#%s' % r1(P[c['key']]['ece_Tm']),
                        '#%s' % r1(P[c['key']]['at50']), '#%s' % r3(P[c['key']]['auc_maxp'])]
                       for c in CF['conds']], cls='dp')
                + '<p>准确率、置信度、收 50%% 的单位是 %%；ECE 以百分点计。"干净 T"是把干净验证集上拟合的温度（T=%s）搬过来之后的 ECE；"自拟合 T"是在该条件的数据上拟合——偷看了答案的上界。'
                  'AUROC 是用最大概率区分帧对错的判别力。句子级（用句子平均置信度预测这批里错得最多的三分之一）AUROC：干净 %s、白噪 10 dB %s、babble 10 dB %s。</p>'
                % (r2(A['T_clean']), r2(P['clean']['utt_auc']), r2(P['white10']['utt_auc']), r2(P['babble10']['utt_auc']))))
    o.append(step('失配时置信度几乎不降'))
    o.append('<p>干净时置信度和准确率对得上（ECE %s）。失配后准确率掉得很多，<strong>置信度却几乎不掉</strong>：电话带宽 %s%% 对、置信度 %s%%；'
             '白噪 10 dB %s%% 对、置信度 %s%%。这不是校准没做好——温度缩放把这件事救不回来：干净验证集上拟合的温度对白噪 10 dB 只把 ECE 从 %s 降到 %s，'
             '要在失配条件自己的数据上拟合才到 %s。<strong>校准是和条件绑定的</strong>，在一个条件上校准好的置信度搬到另一个条件上就失效。</p>'
             % (r1(A['clean_ece']), r0(A['tel_acc']), r0(A['tel_conf']), r0(A['w10_acc']), r0(A['w10_conf']),
                r0(A['w10_ece']), r0(A['w10_eceT']), r0(A['w10_eceTm'])))
    o.append(step('拒识：收最高的那一部分'))
    o.append('<p>拒识就是只留置信度最高的一部分，把其余的交给别的流程。它能买到多少取决于<strong>置信度能不能区分对错</strong>：'
             'babble 10 dB 下准确率 %s%%、收最高的一半达到 %s%%（AUROC %s）；而白噪 10 dB 下 AUROC 只有 %s，收一半也只有 %s%%——整体错了，挑不出对的。'
             '最大概率、间隔（最高减次高）、熵三种量在这里的 AUROC 几乎一样（平均差 %s），不用为"用哪个量"纠结。</p>'
             % (r0(P['babble10']['acc']), r0(P['babble10']['at50']), r2(P['babble10']['auc_maxp']), r2(A['w10_auc']),
                r0(A['w10_at50']), r3(abs(A['margin_vs_maxp']))))
    o.append(trap('我原以为：增强过的模型也会更"知道自己不知道"',
                  '增强过的模型在白噪 10 dB 上 %s%% 对、ECE %s，看着很好——但那是因为它见过这类噪声。换到电话带宽：%s%% 对、置信度 %s%%、ECE %s（只见过干净的是 %s）。'
                  '增强提高了准确率，<strong>没有让模型知道哪些条件是自己没见过的</strong>。要在线上发现失配，得靠另外的东西：输入的统计量漂移、'
                  '多个模型的分歧、或者定期用线上抽样标注回算 ECE。'
                  % (r0(Rb['white10']['acc']), r1(Rb['white10']['ece']), r0(Rb['tel']['acc']), r0(Rb['tel']['conf']),
                     r0(Rb['tel']['ece']), r0(P['tel']['ece']))))
    o.append(note('这一节没覆盖的',
                  '词级与句级的置信度（lattice 后验、N-best 一致性）、OOV 与拒识的联动、置信度估计模型（单独训一个二分类器预测"这个词对不对"），本节都没有做。'
                  '这里量的是最基础的一层：声学模型自己的 softmax 值得信几分。'))
    o.append(q([
        ('在干净验证集上拟合了温度，上线后带噪的用户的置信度能信吗？',
         '不能。白噪 10 dB 下 ECE 只从 %s 降到 %s，要在该条件自己的数据上拟合才到 %s。校准是条件相关的。' % (r0(A['w10_ece']), r0(A['w10_eceT']), r0(A['w10_eceTm']))),
        ('拒识阈值设得很高，错误会少很多吗？',
         '取决于置信度的 AUROC。babble 10 dB 下 AUROC %s，收最高一半能到 %s%%；白噪 10 dB 下 AUROC %s，收一半也只有 %s%%。'
         % (r2(P['babble10']['auc_maxp']), r0(P['babble10']['at50']), r2(A['w10_auc']), r0(A['w10_at50']))),
    ]))
    o.append('</section>')
    return ''.join(o)


def s49(n):
    A = KD['note']
    S = {(r['H'], r['key']): r for r in KD['students']}
    o = [sec('s49', n, '蒸馏与压缩', '进阶',
             lede='端侧塞不下教师模型。小模型从大模型那里到底能学到什么？权重量化到几位还不坏？',
             tldr='蒸馏值钱的不是"软标签"，而是<strong>教师给没有标注的增强数据打的标</strong>：同样 12 条标注，加教师软标签 babble 从 %s%% 到 %s%%（没动），'
                  '加教师打标的无标注增强数据到 <strong>%s%%</strong>。温度和 α 在整个扫描里差别 ≤ 1 个点。权重量化到 4 位几乎免费（按通道），3 位要看模型和方式。'
                  % (r0(A['hard32_babble']), r0(A['kd32_babble']), r0(A['kdu32_babble'])))]
    o.append(note('这一节的底盘', '<p>' + TOY + '</p>'
                  '<p>教师是 2×512 的 MLP（%s 参数），用带噪、混响、变速的全部数据训练并做逐条 CMVN；学生是 2×16 / 32 / 64，只允许看到 %d 条（%d 秒）干净标注。</p>'
                  % ('{:,}'.format(KD['teacher']['params']), KD['const']['nlab'], KD['const']['lab_s'])))
    o.append(fml('蒸馏损失', 'kd'))
    o.append(fig('kd', '<strong>两个小图。</strong>① 学生（2×32）的三种训练做法；② 教师与学生的权重量化。'))
    cks = [('clean', '干净'), ('white10', '白噪 10 dB'), ('babble10', 'babble 10 dB'), ('tel', '电话带宽')]
    short_recipe = {'hard': '硬标签', 'kd': '软标签', 'kd_u': '教师打标无标注增强数据'}
    rows = [['教师 2×512', '#%s' % '{:,}'.format(KD['teacher']['params'])] + ['#%s' % r1(KD['teacher']['acc'][k]) for k, _ in cks]]
    for H in (16, 32, 64):
        for key in ('hard', 'kd', 'kd_u'):
            r = S[(H, key)]
            rows.append(['学生 2×%d · %s' % (H, short_recipe[key]), '#%s' % '{:,}'.format(r['params'])] +
                        ['#%s' % r1(r['acc'][k]) for k, _ in cks])
    o.append(ex('实测：帧准确率（%%，%d 个种子）' % len(KD['const']['seeds']),
                table(['模型 · 训练做法', '#参数'] + ['#' + nm for _, nm in cks], rows, cls='dp')
                + '<p>"硬标签"= 只用 12 条干净标注；"软标签"= 同样 12 条加教师软标签；"教师打标无标注增强数据"= 再加一大批没有标注、经过增强的数据，由教师打标。'
                  '学生（2×32）比教师小 %s 倍。只有 12 条标注时，硬标签和同样数据上的软标签没有区别——软标签在这么少的数据上没有可学的地方；'
                  '<strong>真正起作用的是让教师给一大批没有标注、但经过增强的数据打标</strong>：白噪 10 dB 从 %s%% 到 %s%%，babble 10 dB 从 %s%% 到 %s%%，'
                  '干净数据上则略有下降（%s%% → %s%%）。</p>'
                % (r0(A['ratio_params']), r1(A['hard32_white']), r1(A['kdu32_white']), r1(A['hard32_babble']), r1(A['kdu32_babble']),
                   r1(A['hard32_clean']), r1(A['kdu32_clean']))))
    o.append(trap('我原以为：蒸馏要仔细调温度和 α',
                  '在 T = 1/2/4/8 与 α = 0/0.5/1 的整个网格上（学生 2×32、教师打标的无标注池），干净、白噪、babble 的准确率都在 ±1 个点以内'
                  '（表在 <code>demo_kd.json</code> 里）。这两个旋钮几乎不重要；<strong>教师看过什么数据、给学生看哪些数据</strong>才重要。'))
    o.append(step('量化'))
    o.append(fml('权重量化：按张量与按通道', 'quant'))
    qrows = []
    for mdl in ('教师 2×512', '学生 2×64'):
        for bits in (32, 8, 6, 4, 3):
            for pc in ([None] if bits == 32 else [False, True]):
                qq = [q_ for q_ in KD['quant'] if q_['model'] == mdl and q_['bits'] == bits and q_['per_channel'] == pc][0]
                label = '%s · %s' % (mdl, 'fp32' if bits == 32 else 'int%d %s' % (bits, '按通道' if pc else '按张量'))
                qrows.append([label, '#%s' % r1(qq['kb'])] + ['#%s' % r1(qq['acc'][k]) for k, _ in cks])
    o.append(ex('实测：权重量化后的帧准确率（只量化权重，激活保持浮点）',
                table(['模型 · 位宽 · 粒度', '#大小 KB'] + ['#' + nm for _, nm in cks], qrows, cls='dp')
                + '<p>教师 int8 按张量 %s%%，int4 %s%%（按通道 %s%%），3 位按张量掉到 %s%%、按通道还有 %s%%。'
                  '学生更小，更不耐量化：int4 按张量 %s%%、按通道 %s%%，int3 按张量 %s%%、按通道 %s%%。'
                  '教师 fp32 %s KB，int4 按通道 %s KB——体积降到 1/8，准确率几乎没变。</p>'
                % (r1(A['q8_pt']), r1(A['q4_pt']), r1(A['q4_pc']), r1(A['q3_pt']), r1(A['q3_pc']), r1(A['sq4_pt']), r1(A['sq4_pc']),
                   r1(A['sq3_pt']), r1(A['sq3_pc']), r0(A['tq_kb']), r0(A['tq4_kb']))))
    o.append(note('局限',
                  '这是一个没有 BatchNorm、没有注意力、没有激活异常值的小 MLP，<strong>只量化了权重</strong>。真实的 Conformer 上，激活的异常值会让 8 位激活量化也变难，'
                  '量化感知训练和校准集的选择是另一个层面的问题——本节没有量。同样，教师与学生相差 %s 倍是这个玩具世界里的数；真实 ASR 的教师和学生差距、'
                  '蒸馏用的数据量与教师的标注质量，都要在目标场景里重新量。' % r0(A['ratio_params'])))
    o.append(q([
        ('标注很少，想用大模型教小模型，最该花力气的地方是什么？',
         '给教师准备一大批没有标注但经过增强的数据让它打标。本实验里这一步把 babble 10 dB 从 %s%% 提到 %s%%；而只在同样的少量标注上加软标签没有收益。'
         % (r0(A['hard32_babble']), r0(A['kdu32_babble']))),
        ('权重量化到 4 位，要按张量还是按通道？',
         '学生模型上差别明显：int4 按张量 %s%%、按通道 %s%%。通道间权重范围差得越多，按张量越吃亏。' % (r1(A['sq4_pt']), r1(A['sq4_pc']))),
    ]))
    o.append('</section>')
    return ''.join(o)


def s50(n):
    A = VD['note']
    V = {r['key']: {(c['margin'], c['pad_ms']): c for c in r['cells']} for r in VD['vad']}
    o = [sec('s50', n, '长音频：切在哪里', '进阶',
             lede='会议、访谈、播客都是几十分钟的连续录音，模型一次吃不下。切在哪儿、切多长，决定了有多少词被切断、多少算力花在静音上。',
             tldr='固定切 10 s、不重叠，会切断 <strong>%s%%</strong> 的语音岛；重叠 1 s 降到 %s%%，算力 ×%s。'
                  '能量 VAD 的余量要随噪声调：同一个 9 dB 余量，白噪 10 dB 召回 %s%%，<strong>白噪 0 dB 召回 %s%%</strong>。'
                  '首尾各补 100 ms 把被削头尾的语音岛从 %s%% 降到 %s%%。'
                  % (r1(A['fix10_pct']), r1(A['fix10ov_pct']), r2(A['fix10ov_cost']), r0(A['w10_recall']), r0(A['w0_recall9']),
                     r1(A['w10_clip0']), r1(A['w10_clip100'])))]
    o.append(note('这一节的底盘',
                  '<p>%s s 的连续合成语音：语音片段之间插入 0.25–3 s、长短不一的停顿，片段内部保留短静音；真值边界已知。'
                  '"语音岛"指两段静音之间连续发声的一串（本实验里每 120 s 约 %s 个，中位长 %s s、最长 %s s）。VAD 是最朴素的那种：帧能量高出过去 3 s 内的 10%% 分位噪声底多少 dB 就算语音，'
                  '拖尾 %s ms。这不是任何生产系统的 VAD——神经 VAD 要好得多，这一节量的是<strong>三个参数（余量、拖尾、补偿）各自在买什么</strong>。</p>'
                  % (r0(VD['const']['dur']), r0(A['islands']), r2(A['isl_med_s']), r2(A['isl_max_s']), r0(VD['const']['hang_ms']))))
    o.append(fig('vad', '<strong>三个小图。</strong>① 固定切块切断的语音岛；② 能量 VAD 的余量与召回 / 误报；③ 首尾补偿后被削头尾的语音岛。'))
    o.append(step('固定切块'))
    o.append(ex('实测：固定切块（%d 个种子）' % len(VD['const']['seeds']),
                table(['块长', '重叠', '#被切断的语音岛', '#占比', '#算力'],
                      [['%s s' % r0(r['L']), '无' if r['overlap'] == 0 else '%s s' % r0(r['overlap']),
                        '#%s / %s' % (r1(r['cut']), r0(r['islands'])), '#%s%%' % r1(r['pct']), '#×%s' % r2(r['cost'])]
                       for r in VD['fixed']], cls='dp')
                + '<p>固定切块切断的比例不高（10 s 块 %s%%），因为语音岛大多比块短得多；<strong>重叠 1 s 就够把它降到零</strong>，因为最长的语音岛也只有 %s s、'
                  '总有一块完整包含它——<strong>这个玩具世界里的语音岛偏短</strong>，真实对话里连续发声更长，重叠要取得比你关心的最长连续发声还长。代价是重叠部分算两遍（×%s）。但这只保证"词没被切坏"，不保证模型在两块的交界处输出一致——去重与拼接是另一个问题。</p>'
                % (r1(A['fix10_pct']), r2(A['isl_max_s']), r2(A['fix10ov_cost']))))
    o.append(step('能量 VAD：余量要随噪声调'))
    rows = []
    for ck, nm in (('clean', '干净'), ('w20', '白噪 20 dB'), ('w10', '白噪 10 dB'), ('w0', '白噪 0 dB'), ('b10', 'babble 10 dB')):
        r = [x for x in VD['vad'] if x['key'] == ck][0]
        c0 = {(c['margin'], c['pad_ms']): c for c in r['cells']}
        rows.append([nm] + ['#%s / %s' % (r0(c0[(m, 0)]['recall']), r0(c0[(m, 0)]['fa'])) for m in VD['const']['margins_db']])
    o.append(ex('实测：能量 VAD，召回 / 误报（%，不补偿）',
                table(['条件'] + ['#余量 %g dB' % m for m in VD['const']['margins_db']], rows, cls='dp')
                + '<p>"误报"是被送进模型的非语音帧占全部非语音帧的比例（含拖尾 %s ms）。干净和白噪 20 dB 下余量不敏感；到 10 dB 余量 9 dB 开始丢（召回 %s%%）；'
                  '<strong>0 dB 下余量 9 dB 一个语音帧都找不到</strong>，降到 3 dB 召回 %s%%、误报 %s%%。babble 10 dB 则是另一种难：余量 3 dB 召回 %s%% 但误报 %s%%——'
                  '多人叠加的噪声本身就像语音，能量检测分不开。</p>'
                % (r0(VD['const']['hang_ms']), r0(A['w10_recall']), r0(A['w0_recall3']), r0(A['w0_fa3']), r0(A['b10_recall3']), r0(A['b10_fa3']))))
    o.append(step('首尾补偿'))
    prow = []
    for ck, nm in (('clean', '干净'), ('w10', '白噪 10 dB'), ('b10', 'babble 10 dB')):
        r = [x for x in VD['vad'] if x['key'] == ck][0]
        c0 = {(c['margin'], c['pad_ms']): c for c in r['cells']}
        for p in (0, 100, 300):
            c = c0[(9.0, p)]
            prow.append([nm, '#补 %d ms' % p, '#%s%%' % r1(c['recall']), '#%s%%' % r1(c['keep']), '#%s%%' % r1(c['clip_pct'])])
    o.append(ex('实测：余量 9 dB 下，首尾补偿的收益与代价',
                table(['条件', '#补偿', '#召回', '#送进模型的时长占比', '#被削头尾的语音岛'], prow, cls='dp')
                + '<p>补 100 ms：白噪 10 dB 召回从 %s%% 到 %s%%，被削头尾的语音岛从 %s%% 到 %s%%，送进模型的时长从 %s%% 到 %s%%。'
                  '补偿是便宜的保险：模型更怕丢掉一个词的头（起音），而不是多听 100 ms 静音。</p>'
                % (r0(V['w10'][(9.0, 0)]['recall']), r0(V['w10'][(9.0, 100)]['recall']), r1(A['w10_clip0']), r1(A['w10_clip100']),
                   r0(V['w10'][(9.0, 0)]['keep']), r0(V['w10'][(9.0, 100)]['keep']))))
    o.append(trap('一个常见的误判：先把 VAD 调好，切分就不是问题了',
                  '余量是一个<strong>要随噪声调的数</strong>：同一个 9 dB，在 20 dB 以上的环境里是最优，在 0 dB 的环境里一无所获。'
                  '用固定余量上线，等于假设现场噪声和调参时一样——在会议室、地铁、车里，这个假设一定会破。'
                  '用自适应噪声底（本节已经用了）能解决"整体变响"，解决不了"噪声像语音"（babble）。'))
    o.append(note('这一节没覆盖的',
                  '神经 VAD 与端点检测、说话人切换点、按停顿切分后相邻段的上下文传递（把前一段的结尾当提示）、'
                  '长音频上 AED 的长度外推与幻觉（28 节）、时间戳的拼接与漂移。这一节只量了"切在哪里"这一个问题。'))
    o.append(q([
        ('把长录音按固定 30 秒切块，会不会切到词？',
         '会，但比想象的少：本实验里 30 s 块无重叠切断 %s%%，10 s 块 %s%%。重叠 1 s（语音岛都短于它）就能避免，算力只多 %s%%。'
         % (r1(A['fix30_pct']), r1(A['fix10_pct']), r0((A['fix10ov_cost'] - 1) * 100))),
        ('VAD 阈值在会议室调好了，搬到地铁里为什么不行？',
         '固定余量假设信噪比不变。本实验里同一个 9 dB 余量，白噪 10 dB 召回 %s%%，0 dB 召回 %s%%。要么按噪声自适应余量，要么换神经 VAD。'
         % (r0(A['w10_recall']), r0(A['w0_recall9']))),
    ]))
    o.append('</section>')
    return ''.join(o)


def build(num):
    return {'s46': s46(num['s46']), 's47': s47(num['s47']), 's48': s48(num['s48']),
            's49': s49(num['s49']), 's50': s50(num['s50'])}
