# -*- coding: utf-8 -*-
"""22–24 节：公式的仿真验证、神经网络结构与数据形状演进、参考文献与核对状态。"""
import json, os, re
from util import sec, part, table, note, trap, h4
import refs

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = json.load(open(os.path.join(HERE, 'sim.json')))
NN = json.load(open(os.path.join(HERE, 'nn.json')))
FN = json.load(open(os.path.join(HERE, 'figs_nn.json')))


def fmt(v):
    if isinstance(v, bool):
        return '是' if v else '否'
    if isinstance(v, (int, float)):
        return ('%.4g' % v).replace('-', '−')
    return str(v)


def cite_note(sid):
    ks = refs.CITES.get(sid)
    if not ks:
        return ''
    links = '、'.join('<a href="#ref-%s">[%d]</a>' % (k, refs.IDX[k]) for k in ks)
    return note('依据的文献', '本节的方法与公式依据：%s。核对状态见 24 节。' % links)


def build_f():
    o = []
    o.append(part('Part Ⅸ', '验证、结构与文献', '用仿真检验公式、用结构图与形状表讲清神经网络、给出参考文献及其核对状态'))

    # ── 22 仿真验证 ──
    rows = SIM['rows']
    n, nok = SIM['n'], SIM['n_ok']
    o.append(sec('u23', '22', '公式的仿真验证', '深入',
                 lede='前面的公式都是推导出来的。这一节回答：它们对不对？做法是用独立的数值仿真，把"公式预测的数"与"仿真量出来的数"放在一起比，判据在比之前写定。',
                 tldr='%d 项检验全部通过。这证明的是"在写明的假设下，公式成立"，不是"在真实设备和真实语音上成立"。' % n))
    o.append(h4('22.1 检验的方法'))
    o.append('<p>每项检验有四个要素：<strong>被检验的公式</strong>、<strong>公式的预测值</strong>、<strong>独立仿真得到的值</strong>、<strong>事先写定的判据</strong>（例如"偏差不超过 0.05 dB"）。'
             '仿真用合成信号：白噪声、已知房间冲激响应的卷积、人工构造的小语料等；仿真代码不调用被检验的公式，而是用蒙特卡洛、暴力枚举或直接数值积分得到结果。'
             '对于"定义恒等式"类的公式（如 σ² 的算术），不检验它本身，而检验由它导出的、可被独立量出的后果。</p>')
    o.append('<p>举两个例子说明"独立"的含义。DAS 对不相关噪声的增益，公式说是 10·lg M；仿真则生成 M 路独立噪声，实际做延迟求和，量输出噪声功率，再换算成 dB（表中 A1：预测 6.0206 dB，仿真 6.0253 dB，偏差 0.0047 dB）。'
             'GMM-EM 的对数似然单调不降，公式（Jensen 不等式）给出的是一个不等式；仿真则对每次迭代记下似然，检查最小增量不小于 0（表中 D7）。</p>')
    # 分组计数
    grp = {}
    for r in rows:
        k = r['sec'].split(',')[0]
        grp.setdefault(k, []).append(r)
    names = {'1': '1 节 观测模型', '2': '2 节 阵列', '3': '3 节 回声消除', '4': '4 节 单通道增强', '6': '6 节 特征', '7': '7 节 HMM/GMM',
             '8': '8 节 解码与语言模型', '11': '11 节 声学模型', '12': '12 节 声码器与编解码', '16': '16 节 采集与播放', '17': '17 节 重采样与时钟',
             '18': '18 节 编解码与传输', '19': '19 节 推导补遗', '20': '20 节 评价指标', '21': '21 节 数值算例'}
    srt = sorted(grp, key=lambda x: int(x))
    o.append(h4('22.2 覆盖范围'))
    o.append(table(['书中章节', '检验项数', '通过'], [[names.get(k, k + ' 节'), str(len(grp[k])), str(sum(1 for r in grp[k] if r['ok']))] for k in srt]
                   + [['合计', str(n), str(nok)]], minw=420))
    o.append('<p>表按"主要对应节"归类；有的检验同时支撑两节（例如 19 节的推导在 3、4 节被使用），完整对应关系见下面的明细。</p>')
    o.append(h4('22.3 明细（%d 项）' % n))
    body = []
    for r in rows:
        body.append([r['id'], r['sec'], r['what'], fmt(r['pred']), fmt(r['sim']), fmt(r['dev']), r['crit'].replace('-', '−'), '通过' if r['ok'] else '<b>未通过</b>'])
    o.append('<details><summary>展开 %d 项检验的预测、仿真值、判据</summary>' % n
             + table(['编号', '节', '检验内容', '公式预测', '仿真', '偏差', '判据', '结果'], body, minw=700) + '</details>')
    o.append(h4('22.4 如实记录：仿真本身出过的错'))
    o.append('<p>检验不是一次就全过的。开发过程中有几项最初失败，查下来都是<strong>检验设计的问题，不是公式错了</strong>，修正后才通过：</p>')
    o.append(table(['检验', '最初的问题', '处理'], [
        ['NLMS 稳态失调', '迭代次数不够，滤波器没有到稳态就量了', '提高噪声强度，迭代到 12–14 个时间常数之后再量'],
        ['"快与准的积"', '第一版是公式对公式的比较（循环论证）', '改成用仿真量出的时间常数与失调去相乘'],
        ['Kneser–Ney', '玩具语料里"francisco"的频次比"dog"还低，不满足例子的前提', '把语料重复构造到满足前提'],
        ['流匹配的边缘向量场', '某些取值的格子里没有样本', '选样本充足的取值，并要求每格至少 2000 个样本'],
        ['WaveNet 感受野', '用来数感受野的缓冲区太短', '把序列长度加到 12000'],
        ['重采样阻带', '探测频率落在过渡带里', '换到 10 kHz 的探测点，衰减 ≥ 40 dB，实测 56.9 dB']], minw=640))
    o.append(trap('这些检验证明不了什么', '（1）<strong>不证明真实性能</strong>：仿真用的是白噪声、合成房间、小语料；真实麦克风、真实房间、真实语音上的数字要靠前端、ASR、TTS 三本手册里标明了适用范围的实验，或自己的测量。'
                  '（2）<strong>不检验神经网络的效果</strong>：深度模型"能达到多少 PESQ/WER"不是一个公式，不在本节范围。'
                  '（3）<strong>不替代文献核对</strong>：仿真说明"公式在假设下自洽"，文献核对说明"这个公式确是该方法的原始表述"，两者互补。后者的做到程度见 24 节。'))
    o.append(note('怎么复现', '检验脚本在仓库的 fullstack/sim 目录，汇总结果在 fullstack/sim.json；每一项的预测、仿真值与判据与上面的明细一致。'))
    o.append(cite_note('u23'))
    o.append('</section>')

    # ── 23 网络结构 ──
    o.append(sec('u24', '23', '神经网络结构与数据形状演进', '深入',
                 lede='前面各节提到了很多网络：增强的 DeepFilterNet2、DCCRN、Conv-TasNet，识别的 Conformer、RNN-T、wav2vec 2.0，说话人的 ECAPA-TDNN，合成的 FastSpeech 2、HiFi-GAN、EnCodec。'
                      '这一节把它们逐个画成结构图，并列出一段数据穿过网络时每一步的形状。',
                 tldr='读图和表的方法：先看形状主线（左到右，哪里变长、哪里变短、哪里变宽），再看每一步的运算。形状是检验自己有没有读懂结构的最快办法。'))
    o.append('<p><strong>这些图和表是怎么来的。</strong>结构与超参数<strong>取自各模型的公开参考实现的源码</strong>（每个小节的"来源"一栏给出文件与关键参数），形状由这些超参数<strong>算出</strong>；'
             '没有训练模型、没有复现论文里的指标。图 FastSpeech 2 取自 speechbrain 的结构说明，不给超参数；图"条件流匹配声学模型"是<strong>概念图</strong>，只表达数据流，没有对照具体论文或实现。'
             '示例输入统一取 3 s 的语音（16 kHz 或各模型自己的采样率），与 21 节的数值算例一致。</p>')
    items = [
        ('dfn2', '23.1 DeepFilterNet2：增强（对应 4 节）', '先在 ERB 带上估计增益，再在低频用深度滤波补回相位与谐波细节。'),
        ('dccrn', '23.2 DCCRN：复数卷积循环网络（对应 4 节）', '输入复数谱，编码器逐层压缩频率维，中间 LSTM 建模时间，解码器还原并输出复数掩码。'),
        ('tasnet', '23.3 Conv-TasNet：时域增强与分离（对应 4 节）', '不经过 STFT，直接在波形上学一个一维卷积"滤波器组"；中间是空洞卷积的堆叠。'),
        ('conformer', '23.4 Conformer 块：识别编码器（对应 7 节）', '前馈 ½ → 自注意力 → 卷积模块 → 前馈 ½，各自带残差；形状始终不变，所以可以堆叠。'),
        ('rnnt', '23.5 RNN-T 联合网络：识别（对应 7 节）', '编码器输出 [T, D]、预测网络输出 [U, D]，在联合网络里两两相加成 T×U 的网格，再投影到词表。'),
        ('w2v2', '23.6 wav2vec 2.0：自监督预训练（对应 7 节）', '七层卷积把波形压成每 20 ms 一帧，再接 Transformer；预训练时对部分帧遮蔽并做对比学习。'),
        ('ecapa', '23.7 ECAPA-TDNN：说话人嵌入（对应 5 节）', '一维卷积 + SE 残差块，多层输出拼接后用带注意力的统计池化把变长序列压成定长向量。'),
        ('fs2', '23.8 FastSpeech 2：声学模型（对应 11 节）', '编码器 → 方差适配器（时长、音高、能量）→ 长度调节器按时长把序列展开 → 解码器 → 梅尔谱。'),
        ('hifigan', '23.9 HiFi-GAN 生成器：声码器（对应 12 节）', '输入梅尔谱，用转置卷积逐级上采样，每级后接多感受野的残差块，直到每帧对应的采样点数。'),
        ('encodec', '23.10 EnCodec：神经编解码（对应 12 节）', '编码器逐级下采样 → 残差向量量化，每个码本贡献一组整数 → 解码器对称上采样。'),
        ('cfm', '23.11 条件流匹配声学模型：概念图（对应 11 节）', '从噪声出发，用向量场网络沿时间积分到梅尔谱；每一步是一次网络前向。'),
    ]
    for key, title, blurb in items:
        o.append(h4(title))
        o.append('<p>%s</p>' % blurb)
        svg = FN[key].replace('id="ah"', 'id="ah_%s"' % key).replace('url(#ah)', 'url(#ah_%s)' % key)
        o.append('<figure><div class="figbox scrollx">%s</div><figcaption>%s</figcaption></figure>' % (svg, title.split('（')[0]))
        d = NN.get(key)
        if d:
            shapes = [s[2] for s in d['stages'] if s[2] not in ('—', '')]
            o.append('<p><strong>形状主线：</strong>' + ' → '.join(shapes[:1] + [s for s in shapes[1:]]) + '</p>')
            o.append(table(['阶段', '运算', '输出形状', '数据在这一步发生了什么'], [list(s) for s in d['stages']], minw=720))
            o.append('<p class="why">来源：%s。</p>' % d['src'])
        elif key == 'fs2':
            o.append(table(['阶段', '形状', '说明'], [
                ['音素序列', '[14]', '示例：m = 14 个音素'], ['嵌入 + 位置编码', '[14, D]', ''], ['编码器（FFT 块堆叠）', '[14, D]', '形状不变'],
                ['方差适配器', '[14, D]', '时长预测器给出每个音素的帧数；音高、能量预测后嵌入并加回'],
                ['长度调节器', '[258, D]', '按时长把每个音素复制展开成 258 帧（3 s @ 22.05 kHz，帧移 256）'],
                ['解码器（FFT 块堆叠）', '[258, D]', '形状不变'], ['线性 → 梅尔', '[258, 80]', '']], minw=560))
            o.append('<p class="why">来源：speechbrain 的 FastSpeech 2 结构说明；本图不给超参数。训练时用真值时长展开（teacher forcing），推理时用预测时长。</p>')
        else:
            o.append(table(['阶段', '形状', '说明'], [
                ['文本 / 音素', '[m] → [m, D]', '嵌入'], ['噪声样本 x₀', '[T, 80]', '从 N(0, I) 采样'],
                ['条件拼接', '[T, D + 80]', '文本展开到帧级，与当前 x_t 拼接（含说话人或提示）'],
                ['向量场网络 v_θ', '[T, 80]', '输入 (x_t, t, c)，输出同形状的速度'],
                ['ODE 积分', '[T, 80]', '欧拉法 x_{t+Δ} = x_t + Δ·v，共 NFE 步']], minw=560))
            o.append('<p class="why">概念图：没有对照具体论文或实现，不给超参数。训练目标与边缘向量场的推导见 11 节、19 节，其数值检验见 22 节。</p>')
        if key == 'conformer':
            o.append(note('实现与论文的差别', '这里的结构取自 torchaudio 的 ConformerLayer：自注意力用的是标准的多头注意力，<strong>不带</strong>相对位置编码；原论文用的是 Transformer-XL 式的相对正弦位置编码。'
                          '两者在数据形状上一致，但论文里的结论（例如位置编码对长句泛化的作用）不能直接套到这个实现上。'))
        if key == 'dccrn':
            o.append(note('形状的两种算法', '表里卷积按"保持边长对齐"的方式记帧数。若第一级下采样用无填充卷积，3 s 输入的帧数会是 73 而不是 75（两次"核 3、步长 2"：(298−3)//2+1 = 148，再 (148−3)//2+1 = 73）。'
                          '不同实现的填充方式不同，帧数差一两帧是常态；做流式或对齐时要以所用实现为准。'))
    o.append(trap('读这些图的时候', '（1）同一个名字在不同实现里超参数可能不同（隐层大小、层数、核大小），表里的数是"某一个公开配置"的数。'
                  '（2）图和表说明<strong>结构与形状</strong>，不说明<strong>效果</strong>；效果取决于数据、训练目标与调参。'
                  '（3）概念图不能当作某篇论文的结构。'))
    o.append(cite_note('u24'))
    o.append('</section>')

    # ── 24 参考文献 ──
    nA = sum(1 for r in refs.R if 'A' in r[3])
    nB = sum(1 for r in refs.R if 'B' in r[3])
    nC = sum(1 for r in refs.R if r[3].strip() == 'C')
    o.append(sec('u25', '24', '参考文献与核对状态', '进阶',
                 lede='这一节列出全书依据的文献，并如实写出每条核对到了什么程度。核对分三级，不混为一谈。',
                 tldr='共 %d 条：%d 条的题名、作者、出处、年份已在线检索核对；%d 条的公式或超参数另外对照了参考实现；%d 条是通行引用，未逐条核对。<strong>没有一条做到"拿原论文逐式对照"</strong>。' % (len(refs.R), nA, nB, nC)))
    o.append(table(['级别', '含义'], [
        ['A', '题名、作者、出处、年份：通过检索（出版社、会议、数据库的页面）核对过'],
        ['B', '本书用到的具体数值（常数、超参数、流水线步骤）：对照了公开的参考实现（ITU 的 PESQ C 代码、pystoi、各网络的官方或主流源码）。'
              '它说明"实现是这样写的"，在没有拿到原论文全文的前提下，作为原论文的替代证据'],
        ['C', '通行引用：按领域里通用的引用格式写出，没有逐条在线核对；使用前请自行查证']], minw=520))
    o.append(trap('这一节做不到什么', '核对时可访问的站点有限：arXiv、ITU 的标准文本和 Crossref 的接口在本环境里被网络策略拦截，所以<strong>无法打开原论文或标准全文逐式对照</strong>。'
                  'A 级只保证引用信息对；B 级用参考实现代替了原文，但实现可能与论文有出入（如 23 节 Conformer 的位置编码）。'
                  '若在环境的网络设置里放行这几个站点，可以补做"原文逐式对照"。'))
    body = []
    for i, (k, c, s, st) in enumerate(refs.R):
        body.append(['<span id="ref-%s"></span>[%d]' % (k, i + 1), c, s, st.replace(' ', '·')])
    o.append(table(['编号', '文献', '用于', '核对'], body, minw=700))
    o.append(h4('已知的口径说明'))
    o.append('<ul><li>PESQ：原始 P.862 的 MOS-LQO 映射常数（4.5、0.1、0.0309）与宽带 P.862.2 的映射（1.3669、3.8224）、窄带的 1.4945 / 4.6607，已对照 ITU 参考 C 代码核对（20 节）。</li>'
             '<li>STOI：预处理（重采样到 10 kHz、去除 40 dB 以下的静音帧、256/512 点 STFT、50% 重叠、自 150 Hz 起 15 个三分之一倍频程带、N = 30 帧、β = −15 dB）已对照 pystoi 核对（20 节）。</li>'
             '<li>各神经网络的结构参数：对照源码，见 23 节每小节的"来源"。</li></ul>')
    o.append(cite_note('u25').replace('', '') if False else '')
    o.append('</section>')
    return ''.join(o)
