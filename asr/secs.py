#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""章节登记处：旧章节按新编号重发（带补丁），新章节由 new1 / new2 生成。"""
import oldsec as O
import bookutil as B

# 复用但不改动的章节
KEEP = ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9', 's10', 's11',
        's12', 's13', 's14', 's16', 's18', 's19', 's21', 's22', 's23', 's24',
        's25', 's29', 's30', 's31', 's32', 's33', 's34', 's35', 's36', 's37', 's38']

XB = {   # 姊妹篇链接
    'arr': '<a href="https://claude.ai/artifact/JkNwTFLFyfWYejCCzykVLQ">麦克风阵列手册</a>',
    'enh': '<a href="https://claude.ai/artifact/5hcKYi2GKnDSKneRv7A87L">单通道增强手册</a>',
    'sv': '<a href="https://claude.ai/artifact/WMzwGqiwAy6vi8MrLwJpgg">声纹与唤醒手册</a>',
    'tts': '<a href="https://claude.ai/artifact/JoVn5ZfQeMhCGQbfScKuwC">TTS 合成手册</a>',
}


def xref(items):
    """本节不展开、已经在别处讲透的东西"""
    o = ['<div class="note"><span class="tag">这块在别处讲透了</span><p>']
    o.append('<br>'.join(items))
    o.append('</p></div>')
    return ''.join(o)


def _beam_tail():
    """给 beam search 一节补上定量部分：搜索质量 ≠ 识别质量。"""
    DE = B.DE
    bm, orc = DE['beam'], DE['oracle']
    o = ['<h3>beam 开大，为什么反而更差</h3>']
    o.append('<p>先看一组实测。同一个模型、同一批句子，只改 beam 宽度：</p>')
    o.append(B.table(['beam', '#每步平均模型得分', '#TER', '#每步展开次数'],
                     [('#%d' % r['beam'], '#%.4f' % r['score'], '#%.2f%%' % r['ter'],
                       '#%s' % '{:,}'.format(int(r['expand']))) for r in bm], cls='dp'))
    o.append('<p><strong>模型得分一路变高，错误率一路变差。</strong>'
             '搜索本身没问题——它确实找到了模型眼里分更高的句子。'
             '问题在于模型眼里分高的那句，不是对的那句。</p>')
    o.append(B.fml('beam 在比较什么', 'beamscore',
                   [('第一项', '声学得分'), ('第二项', '外部语言模型得分'),
                    ('第三项', '减掉内部语言模型，见 22 节'),
                    ('β', '词插入奖励，抵消长度偏置')]))
    o.append(B.fig('beam', 'beam 的悖论：模型得分与识别质量反向；'
                           '而 oracle 与 top-1 的差距一直在拉大。'))
    o.append(B.ex('决定性的证据：参考答案自己的得分',
                  '<p>把参考答案送进同一个打分函数：<strong>%.4f</strong>。'
                  '而 beam=32 找到的那条（错的）是 %.4f。</p>'
                  '<p class="step q">模型认为错的那句比对的那句更像话。</p>'
                  '<p>这说明<strong>搜索没坏，是模型的排序坏了</strong>。'
                  'beam 小的时候，搜索不充分反而掩盖了这个问题——'
                  '它没能力找到那些"分高但错"的句子。'
                  'beam 开大，只是让模型把自己的偏好执行得更彻底。</p>'
                  % (DE['ref_score'], bm[-1]['score'])))
    o.append(B.fml('oracle：答案在不在候选里', 'oracle',
                   [('候选集', 'lattice 或 n-best 里的全部候选'),
                    ('取最小', '候选里最接近参考的那条能做到多好')]))
    o.append('<p>但开大 beam 不是白开的。oracle 一直在往下走：</p>')
    o.append(B.table(['beam', '#top-1', '#oracle', '#差距'],
                     [('#%d' % r['beam'], '#%.2f%%' % r['top1'],
                       '#%.2f%%' % r['oracle'], '#%.2f' % (r['top1'] - r['oracle']))
                      for r in orc], cls='dp'))
    o.append(B.why('beam=32 时，正确答案有 %.1f%% 的概率落在 n-best 里，'
                   '而 top-1 只有 %.1f%%——<strong>中间这 %.1f 个点，'
                   '是重打分能拿而 beam 自己拿不到的</strong>。'
                   '这正是 lattice 存在的理由：把候选留下来，交给一个排序更好的模型。'
                   % (orc[-1]['oracle'], orc[-1]['top1'], DE['oracle_gap'])))
    o.append(B.trap('从这条曲线能推出的三件事',
                    '<p><strong>① 调 beam 时不要只看 top-1 的 WER。</strong>'
                    '同时看 oracle。oracle 还在降说明候选池还在变好，'
                    'oracle 不动了才是真的该收手。</p>'
                    '<p><strong>② "beam 开大没变好"不等于"模型够好了"。</strong>'
                    '更可能是模型的排序能力到顶了，该去修排序（重打分、融合、MWER），'
                    '不是去修搜索。</p>'
                    '<p><strong>③ 排序坏掉最常见的原因是内部语言模型。</strong>'
                    '端到端模型自带一个 LM，它会偏好训练文本里常见的说法。'
                    '这一件事单独成节：<a href="#s43">22 节</a>。</p>'))
    o.append(B.q([
        ('beam 从 1 开到 32，模型得分变高了，WER 却变差了。搜索出 bug 了吗？',
         '<p>没有。把参考答案送进同一个打分函数得 %.4f，'
          '比 beam=32 找到的错句（%.4f）还低——<strong>模型本来就认为错的那句更像话</strong>。'
          '搜索忠实地执行了一个坏排序。该修的是排序，不是搜索。</p>'
          % (DE['ref_score'], bm[-1]['score'])),
        ('那开大 beam 还有意义吗？',
         '<p>有，但意义在 oracle 不在 top-1。beam=32 时 oracle %.2f%% 而 top-1 %.2f%%，'
          '差 %.1f 个点。这些点要靠重打分（LM 重打分、MBR、MWER）去兑现。</p>'
          % (orc[-1]['oracle'], orc[-1]['top1'], DE['oracle_gap'])),
        ('CTC 的 prefix beam search 和普通 beam search 差在哪？',
         '<p>多条帧级路径会折叠成同一个文本前缀，剪枝时必须把它们的概率<strong>合并</strong>'
          '而不是当成不同候选。这是 CTC 解码实现里最容易写错的地方——'
          '写错了表现为候选多样性异常低。</p>'),
    ]))
    return ''.join(o)


# 把公式补进原有章节：{sid: [(插在哪个小节标题之前, 公式 html), ...]}
def _inject():
    f = B.fml
    return {
        's3': [('<h3>RTF / RTFx：速度</h3>',
                f('词错误率：三类错误的和', 'wer',
                  [('S', '替换'), ('D', '删除'), ('I', '插入'), ('N', '参考词数')]))],
        's5': [('<h3>GMM 负责打分</h3>',
                f('HMM 的似然：在所有状态序列上求和', 'hmm',
                  [('a', '转移概率'), ('b', '发射概率'), ('S', '状态序列')])),
               ('<h3>鸡生蛋问题怎么破</h3>',
                f('GMM 的发射概率', 'gmm',
                  [('c', '混合权重'), ('μ, Σ', '每个高斯分量的均值与协方差')]))],
        's6': [('<h3>伪似然：hybrid 系统的核心 trick</h3>',
                f('伪似然：把后验换算回似然', 'hybrid',
                  [('P(s|x)', '网络输出的状态后验'),
                   ('P(s)', '状态先验，从对齐里数出来')]))],
        's12': [('<h3>DCT 的真实动机，以及它为什么过时了</h3>',
                 f('倒谱：把卷积变成加法', 'cepstrum',
                   [('取对数', '卷积 → 加法'), ('DCT', '去相关 + 降维')]))],
        's14': [('<h3>另一个维度：3000</h3>',
                 f('帧数怎么算出来的', 'frame',
                   [('窗长/帧移', '典型 25 ms / 10 ms'),
                    ('下采样', '编码器通常再降 4×')]))],
        's16': [('<h3>为什么还需要卷积</h3>',
                 f('自注意力', 'attn',
                   [('Q, K, V', '查询、键、值'),
                    ('√d', '缩放，避免 softmax 饱和')]))],
        's18': [('<h3>三个必踩的坑</h3>',
                 f('GOP：这个音发得像不像', 'gop',
                   [('分子', '按强制对齐算出的目标音素似然'),
                    ('分母', '同一段音频上所有音素里最像的那个')]))],
        's23': [('<h3>中文特有：拼音层纠错（务必做）</h3>',
                 f('热词偏置：沿前缀逐步给分', 'bias',
                   [('μ', '偏置强度'), ('扣回去', '走错了要撤销已给的奖励')]))],
    }


def build(num):
    r = {}
    inj = _inject()
    for s in KEEP:
        r[s] = O.old(s, num[s],
                     patch=[(a, v + a) for a, v in inj.get(s, [])])

    # ── 20 前端信号处理：归口到《单通道增强手册》与《麦克风阵列手册》
    r['s20'] = O.old('s20', num['s20'], append=xref([
        '<b>单通道降噪的增益函数、噪声估计、音乐噪声、神经降噪的输出形式</b>'
        '——' + XB['enh'] + '（04–17 节）。那本书里有一条结论直接影响本节：'
        '把增强当预处理挂在 ASR 前面，<b>四个感知指标全部变好的那一档参数，'
        '下游识别反而变差</b>；该按下游损失训，而不是按 PESQ 调。',
        '<b>波束形成、自适应滤波、混响与麦克风阵列的物理上限</b>'
        '——' + XB['arr'] + '。本节只说这些模块对 ASR 意味着什么，不重复推导。']))

    # ── 31 端侧部署：算力/功耗归口到《声纹与唤醒手册》
    r['s27'] = O.old('s27', num['s27'], append=xref([
        '<b>MAC 数怎么换算成毫瓦、常驻模型的功耗预算、两级唤醒的分工</b>'
        '——' + XB['sv'] + '（18 节）。那本书按常驻场景算过一遍，'
        '这里只给 ASR 侧的延迟分解。',
        '<b>分块大小、前瞻帧数与状态缓存的定量扫描</b>——本书 '
        '<a href="#s44">30 节</a>，那里有可复算的曲线。']))

    # ── 33 数据与评测：合成数据 vs 真实回流归口到《单通道增强手册》
    r['s28'] = O.old('s28', num['s28'], append=xref([
        '<b>合成数据与真实回流的配比、加噪训练的收益边界、失配时泛化怎么掉</b>'
        '——' + XB['enh'] + '（17 节）有一组扫描：训练噪声类型覆盖不到的场景，'
        '模型的表现<b>不是缓慢变差，而是掉到接近不处理</b>。ASR 的数据配比是同一件事。',
        '<b>统计显著性：两个系统差 0.3 个点算不算赢</b>——' + XB['sv'] +
        '（04 节）给了样本量与置信区间的算法，WER 的比较适用同一套。']))

    # ── 19 WFST：概念层保留，定量部分指向下一节
    r['s15'] = O.old('s15', num['s15'], append=xref([
        '<b>这四级机器到底涨多少、哪一步收得回来、不加消歧符会怎样</b>'
        '——下一节（<a href="#s42">20 节</a>）真把它们造出来做了合成与确定化，'
        '包括三个可复算的对照实验。本节先把概念铺好。']))

    # ── 21 beam search：补上定量部分
    r['s17'] = O.old('s17', num['s17'], append=_beam_tail())

    import new1, new2, more
    r.update(new1.build(num))
    r.update(new2.build(num))
    r.update(more.build(num))
    return r
