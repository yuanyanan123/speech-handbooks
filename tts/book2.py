#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正文 Part Ⅳ–附录：机制拆解、工程落地、难点趋势、公式表与术语表。"""
from bookutil import (K, KI, F, G, S, ME, AL, FL, RQ, VO, EV, TP, CK, CL,
                      fml, fig, sec, part, table, ex, note, trap, step, why,
                      code, q)

ASR = '<a href="https://claude.ai/artifact/NL7s2XicLUVjGk8uq4jXvw">ASR 链路手册</a>'
SV = '<a href="https://claude.ai/artifact/WMzwGqiwAy6vi8MrLwJpgg">声纹与唤醒手册</a>'
ARR = '<a href="https://claude.ai/artifact/JkNwTFLFyfWYejCCzykVLQ">麦克风阵列手册</a>'
ENH = '<a href="https://claude.ai/artifact/5hcKYi2GKnDSKneRv7A87L">单通道增强手册</a>'


def xref(items):
    """本节不展开、已经在姊妹篇里讲透的东西"""
    return ('<div class="note"><span class="tag">这块在别处讲透了</span><p>'
            + '<br>'.join(items) + '</p></div>')


r0 = lambda x: '%.0f' % x
r1 = lambda x: '%.1f' % x
r2 = lambda x: '%.2f' % x
r3 = lambda x: '%.3f' % x
r4 = lambda x: '%.4f' % x


def build():
    o = [part('Part Ⅳ', '机制拆解', '六个零件，单独拿出来看清楚')]

    # ── 16 梅尔谱 ─────────────────────────────────────────────
    o.append(sec('s16', '16', '梅尔谱丢了什么', '深入',
                 tldr='它丢了相位，丢了高频的谐波结构，而且几乎<strong>没有压缩</strong>。'
                      '它的价值不在"小"，在"平滑、可预测、适合回归"。'))
    o.append('<p>先把配置固定下来，后面所有的数都在这组参数上：</p>')
    o.append(table(['量', '#值', '含义'], [
        ['采样率', '#%d Hz' % ME['cfg']['sr'], '上限 %.2f kHz' % (ME['cfg']['sr'] / 2000)],
        ['帧长 nfft', '#%d（%s ms）' % (ME['cfg']['nfft'], r2(ME['cfg']['frame_ms'])),
         'DFT 分辨率 %s Hz' % r1(ME['harm']['dft_res'])],
        ['帧移 hop', '#%d（%s ms）' % (ME['cfg']['hop'], r3(ME['cfg']['hop_ms'])),
         '帧率 %s Hz' % r2(ME['cfg']['fps'])],
        ['线性谱维数', '#%d' % ME['cfg']['nbin'], ''],
        ['梅尔维数', '#%d' % ME['cfg']['nmel'], '压缩比 %s:1' % r2(ME['fb']['compress'])],
    ]))
    o.append(fml('⑧ 梅尔弯曲与滤波器组', 'melwarp'))
    o.append(why('滤波器组是<strong>满行秩</strong>的，条件数只有 %s——'
                 '也就是说它不是病态的。'
                 '丢信息不是因为数值问题，'
                 '是因为 %d→%d 这个降维<em>本来就不可逆</em>。'
                 % (r1(ME['fb']['cond']), ME['cfg']['nbin'], ME['cfg']['nmel'])))
    o.append(step('第一样：高频的谐波结构'))
    o.append('<p>梅尔滤波器越往高频越宽。当一个滤波器的带宽超过基频时，'
             '它里面就装进了不止一根谐波，'
             '<strong>谐波的精细结构在输出里被求和抹掉了</strong>。'
             '这个交叉频率可以直接算：</p>')
    o.append(fml('⑨ 谐波什么时候看不见了', 'melharm'))
    o.append(table(['基频 F0', '#谐波开始混在一起的频率'],
                   [['%d Hz（%s）' % (f, tag), '#%d Hz' % ME['harm']['f0_%d' % f]]
                    for f, tag in ((90, '低沉男声'), (120, '典型男声'),
                                   (200, '典型女声'), (300, '儿童 / 高音女声'))]))
    o.append(why('男声 120 Hz 的情形：<strong>%s Hz 以上，梅尔谱里就只剩包络了</strong>。'
                 '到 7 kHz 附近，一个梅尔带宽 %s Hz，里面塞着 %s 根谐波。'
                 '而语音能量虽然主要在低频，'
                 '<em>“清晰”“通透”这类听感恰恰来自高频的精细结构</em>。'
                 % (int(ME['harm']['f0_120']), r0(ME['harm']['width_at_7k']),
                    r1(ME['harm']['bins_at_7k']))))
    o.append(step('第二样：相位'))
    o.append('<p>梅尔谱只有幅度。Griffin-Lim 试图用迭代把相位猜回来：'
             '反复在"时域信号"和"幅度约束"之间投影。</p>')
    o.append(fml('⑩ Griffin-Lim 的不动点', 'gl'))
    o.append(table(['迭代次数', '#谱一致性（从真实幅度谱出发）'],
                   [['%s' % k, '#%s dB' % r2(ME['gl'][k])] for k in ('0', '1', '3', '10', '32', '100')]))
    o.append(why('注意这是<strong>幅度谱完全正确</strong>的理想情形，'
                 '迭代一百次仍然停在 %s dB。'
                 '原因写在公式右边：重叠相加之后再做 STFT，不等于原来那一组帧——'
                 '“每帧幅度对”和“帧之间拼得上”这两组约束一般<em>不相容</em>，'
                 '所以它只能收敛到一个折中点。'
                 % r2(ME['gl']['100'])))
    o.append('<p>从梅尔谱出发更糟：先用伪逆回到线性谱，对数谱距离已经有 %s dB；'
             '再做 100 次 Griffin-Lim，对真实幅度谱的一致性只有 %s dB。'
             '<strong>这就是 Griffin-Lim 声码器那股金属音的全部来源。</strong></p>'
             % (r2(ME['melinv']['lsd_db']), r2(ME['melinv']['gl_100'])))
    o.append(step('第三样：它其实没怎么压缩'))
    B = ME['budget']
    o.append(table(['表示', '#每秒数值个数', '#码率'], [
        ['16 bit PCM', '#%d' % ME['cfg']['sr'], '#%s kbps' % r1(B['pcm_kbps'])],
        ['%d 维梅尔 float32' % ME['cfg']['nmel'], '#%d' % B['vals_per_s'],
         '#%s kbps' % r1(B['mel_f32_kbps'])],
        ['%d 维梅尔 int8' % ME['cfg']['nmel'], '#%d' % B['vals_per_s'],
         '#%s kbps' % r1(B['mel_i8_kbps'])],
    ]))
    o.append(why('数值个数少 %s 倍，但比特只少 %s 倍。'
                 '<strong>梅尔谱不是一种压缩</strong>——'
                 '它的价值是平滑、相邻帧强相关、动态范围可控，'
                 '也就是"好让一个网络去回归"。'
                 '真正的压缩要等到 19 节的 RVQ。'
                 % (r2(B['ratio_val']), r2(B['ratio_bit']))))
    o.append(fig('mel',
                 '<strong>三件事合起来说明了神经声码器在干什么。</strong>'
                 '它要干的一大半不是"还原"，是<em>编造</em>：'
                 '把梅尔谱里根本不存在的高频谐波和相位造出来，而且要造得像。'
                 '这也解释了为什么声码器必须是生成模型（GAN / 流 / 扩散），'
                 '而不能是一个回归器。'))
    o.append('</section>')

    # ── 17 对齐 ───────────────────────────────────────────────
    o.append(sec('s17', '17', '时长与对齐：MAS 到底有多准', '深入',
                 tldr='把单调对齐搜索跑在一段边界已知的语音上：平均误差 %s ms。'
                      '但这个平均数会骗人——'
                      '<strong>误差几乎全在"本来就没有边界"的地方</strong>。'
                      % r1(AL['mas']['mae_ms'])))
    o.append('<p>12 节说过，FastSpeech 那一系把对齐外包了出去，'
             '于是对齐质量成了整条链的上限。这一节把这个上限量出来。</p>')
    o.append('<p>实验对象是一段 %d 帧、%d 个音素的合成语音，'
             '每个音素的起止样点是<strong>已知真值</strong>。'
             '先看问题有多大：</p>' % (AL['cfg']['T'], AL['cfg']['I']))
    o.append(fml('⑪ 单调对齐的条数', 'maspaths'))
    o.append('<p>和 CTC 的前向算法是同一笔交易：指数级的枚举，'
             '换成一个 O(TI) 的动态规划。递推式只有一行：</p>')
    o.append(fml('⑫ MAS 的动态规划', 'masdp',
                 [('Q', '前 t+1 帧分配给前 i+1 个音素的最大总对数似然'),
                  ('μᵢ, σᵢ', '第 i 个音素的高斯参数，由文本编码器给出')]))
    o.append(step('它有多准'))
    o.append(table(['方法', '#平均边界误差', '#最大', '#±20 ms 内'], [
        ['MAS（标准高斯打分）', '#<strong>%s ms</strong>' % r2(AL['mas']['mae_ms']),
         '#%s ms' % r1(AL['mas']['max_ms']), '#%d%%' % AL['mas']['within20']],
        ['均分（GMM-HMM 的冷启动）', '#%s ms' % r1(AL['uniform']['mae_ms']),
         '#%s ms' % r1(AL['uniform']['max_ms']), '#—'],
    ]))
    o.append('<p>%s ms 看起来一般。但按边界类型拆开之后，图景完全不同：</p>'
             % r2(AL['mas']['mae_ms']))
    o.append(table(['边界类型', '#个数', '#平均误差'],
                   [[k, '#%d' % v[0], '#%s ms' % r1(v[1])] for k, v in AL['bykind'].items()]))
    o.append(why('<strong>在有谱突变的地方，MAS 准到一帧以内（%s ms）；'
                 '在浊音滑到浊音的地方，差 %s ms。</strong>'
                 '后者不是算法的问题——那里物理上就没有一条线可以标，'
                 '共振峰是连续滑过去的，<em>人工标注同样标不准</em>。'
                 % (r1(AL['bykind'].get('有明显谱突变', [0, 0])[1]),
                    r1(list(AL['bykind'].values())[-1][1]))))
    o.append(fig('align',
                 '<strong>左边是似然矩阵上的那条路，右边是误差的去向。</strong>'
                 '共有 10^%s 条合法的单调路径，DP 在 O(TI) 内找到最优的那条。'
                 '<em>去掉单调约束，%s%% 的帧会"时间倒流"，%d 个音素一帧也分不到——'
                 '这就是漏词和复读的结构性来源。</em>'
                 % (r1(AL['npaths_log10']), r1(AL['soft']['nonmono_pct']),
                    AL['soft']['n_skipped'])))
    o.append(ex('算例 · 打分写法的三个细节各值多少',
                table(['打分', '#MAE', '#最大', '#±20 ms', '#最短音素'],
                      [[v['tag'], '#%s ms' % r2(v['mae']), '#%s ms' % r1(v['max']),
                        '#%d%%' % v['within20'], '#%d 帧' % v['minlen']]
                       for v in AL['variants']], cls='dp')
                + fml('⑬ logdet 那一项在干什么', 'maslogdet')
                + '<p class="why">高斯对数似然里有一项 −Σlog σ，'
                  '它和当前帧长什么样<strong>无关</strong>——'
                  '只要这一帧分给了方差小的音素，就白拿一份奖励。'
                  '于是 DP 倾向于把帧多分给"稳定"的音素（静音、长元音），'
                  '把短音素挤到只剩一帧。</p>'
                  '<p>去掉这一项（只留马氏距离）反而更准（%s → %s ms），'
                  '但那就不是最大似然了。'
                  '<em>真实系统里的对策是给每个音素设一个最短时长，'
                  '或者干脆用共享的 σ。</em></p>'
                  % (r2(AL['variants'][0]['mae']), r2(AL['variants'][2]['mae']))))
    o.append(note('时长预测本身的上限',
                  '<p>就算对齐完全正确，时长预测也有一个天花板。'
                  '在只知道"是哪个音素"的条件下，'
                  '时长的 R² 是 %s，看起来很高；'
                  '但绝对误差仍有 <strong>%s ms</strong>。</p>'
                  '<p>R² 高是因为<em>音素之间</em>差别大（静音 200 ms，塞音 50 ms），'
                  '不是因为<em>同一个音素</em>好预测。'
                  '<strong>韵律就住在那 ±%s ms 的残差里</strong>——'
                  '它要靠上下文、句法、说话风格来解释，而这正是 07 节那件难事。</p>'
                  % (r3(AL['durpred']['r2']), r1(AL['durpred']['mae_ms']),
                     r0(AL['durpred']['mae_ms']))))
    o.append('</section>')

    # ── 18 声码器 ─────────────────────────────────────────────
    o.append(sec('s18', '18', '声码器：那股"电音"从哪来', '深入',
                 tldr='两个来源都能精确算出来：逐点非线性造出的谐波会折回语音频段；'
                      '转置卷积的核长不能被步长整除时，输出带上 3.01 dB 的周期性调制。'))
    o.append(step('来源一：非线性混叠'))
    o.append('<p>神经声码器要在网络内部把 86 Hz 的梅尔帧率升到 22050 Hz——'
             '中间每一层都有激活函数。'
             '<strong>任何逐点非线性都会造出高次谐波</strong>，'
             '超过当前采样率一半的那些不会消失，它们会折回来：</p>')
    o.append(fml('⑭ 折回的位置是算得出来的', 'aliasfold'))
    o.append(fig('alias',
                 '<strong>左边是折回的去向，右边是反混叠能买回多少。</strong>'
                 '3 kHz 纯音的 7 次谐波落回 1.05 kHz——语音最要命的频段。'
                 '<em>激活函数光滑不光滑差了七十个 dB</em>：同样上采 2× 再做，'
                 'snake 降到 −%s dB，leaky ReLU 只到 −%s dB。'
                 % (r1(abs(VO['alias']['cases'][1]['up2'])),
                    r1(abs(VO['alias']['cases'][0]['up2'])))))
    o.append(table(['激活', '#直接做', '#上采 2× 再做', '#上采 4×'],
                   [[c['act'], '#%s dB' % r2(c['naive']), '#%s dB' % r2(c['up2']),
                     '#%s dB' % r2(c['up4'])] for c in VO['alias']['cases']]))
    o.append(why('leaky ReLU 有一个折点，它的谐波只按 1/k² 衰减；'
                 'snake 是光滑函数，谐波指数衰减。'
                 '<strong>所以同样的反混叠手段，用在光滑激活上效果好几十个 dB。</strong>'
                 '这就是 BigVGAN 那套 anti-aliased 激活在买的东西，'
                 '代价是内部采样率翻倍、算力翻倍（23 节会算）。'))
    o.append(step('来源二：棋盘伪影'))
    o.append('<p>这一条可以完全在纸上算死。步长 s、核长 k 的转置卷积，'
             '输出第 p 个相位上叠加的权重个数是 ⌈(k−p)/s⌉：</p>')
    o.append(fml('⑮ 各相位的权重个数', 'checker'))
    o.append(table(['步长 s', '#核长 k', '各相位权重数', '#功率调制'],
                   [['#%d' % c['stride'], '#%d' % c['k'],
                     str(c['counts']) + ('　整除 ✓' if c['divisible'] else '　不整除 ✗'),
                     '#%s dB' % r2(c['mod_db'])] for c in VO['checker']], cls='dp'))
    o.append(why('整除时各相位一样多，调制为 0；不整除时输出带上一个周期为 s 的功率调制，'
                 '在谱上就是 <strong>SR/s 处的一根固定亮线</strong>——'
                 '听感是固定音高的电流声。'
                 '推导给的 3.01 dB，实测是 3.19 dB，对得上。'))
    o.append(trap('所以核长要取步长的整数倍',
                  '<p>HiFi-GAN 的上采样核长取 2×stride，就是为了这个。'
                  '这是个<strong>一行代码的事，但查起来要命</strong>——'
                  '症状是"某个频率上总有一点嗡嗡声"，而所有的损失曲线都很正常。</p>'
                  '<p>顺带：这也是为什么有些实现改用"最近邻上采样 + 普通卷积"'
                  '替代转置卷积——那样根本不会有相位不等的问题。</p>'))
    o.append(step('第三件事：损失函数为什么不能用波形 L2'))
    o.append(fml('⑯ 相位挪一点，波形 L2 就爆炸', 'phasel2'))
    o.append(table(['相位差', '#波形 L2', '#幅度谱距离', '听感'],
                   [['%d°' % p['deg'], '#%s dB' % r2(p['wave_db']),
                     '#%s dB' % r3(p['spec_db']), '完全一样'] for p in VO['phase']]))
    o.append(why('相位挪 90°，波形 L2 是 <strong>+3.01 dB</strong>——'
                 '误差的能量比信号还大；而幅度谱距离是 0，人耳听不出任何区别。'
                 '<strong>波形 L2 惩罚的几乎全是相位，而人耳几乎不听相位。</strong>'
                 '所以 HiFi-GAN 一类的损失里没有波形 L2，'
                 '只有多尺度谱损失（管幅度）加判别器（管细节的真实性）。'))
    o.append('</section>')

    # ── 19 tokenizer ──────────────────────────────────────────
    L8 = RQ['ladder'][7]
    o.append(sec('s19', '19', '音频 tokenizer：把波形变成离散符号', '深入',
                 tldr='残差矢量量化把"指数"变成"线性"：%d 级 × 10 bit 的效果，'
                      '不需要一个 2^%d 条目的码本。'
                      '代价是 token 数量直接变成 LLM 的上下文长度。'
                      % (L8['nq'], RQ['why_rvq']['equiv_bits'])))
    o.append(fml('⑰ 残差矢量量化', 'rvq'))
    o.append('<p>做法直白：第一级用一个 1024 条目的码本量化，'
             '第二级去量化<strong>第一级的残差</strong>，如此往下。'
             '在一批合成语音的梅尔表示上跑一遍：</p>')
    o.append(table(['级数', '#码率', '#token/秒', '#重建 SNR', '#码本利用率', '#困惑度'],
                   [['#%d' % r['nq'], '#%s kbps' % r2(r['kbps']), '#%s' % r1(r['tok_s']),
                     '#%s dB' % r2(r['snr']), '#%d（%s%%）' % (r['used'], r1(r['used_pct'])),
                     '#%s' % r1(r['perp'])] for r in RQ['ladder']], cls='dp'))
    o.append(why('两件事值得注意。<strong>一</strong>：每加一级大约换 1.5 dB，'
                 '而且越往后越少——'
                 '<strong>二</strong>：困惑度从 %s 掉到 %s，'
                 '说明后面的码本用得越来越不均匀。'
                 '<em>越靠后的级，信息越少、越难学</em>，'
                 '这正是 LLM-TTS 里"后几级交给非自回归的头"这种设计的依据。'
                 % (r0(RQ['ladder'][0]['perp']), r0(L8['perp']))))
    o.append(fig('rvq',
                 '<strong>左边是质量的阶梯，右边是上下文的代价。</strong>'
                 '86 Hz × 8 级的十秒话是 %d 个 token，25 Hz × 8 级只要 %d 个。'
                 '<em>但帧率压下去，时长分辨率也跟着掉：25 Hz 一帧 40 ms，'
                 '而 17 节说过音素边界的精度要求是 10–20 ms。</em>'
                 % (int(86.1 * 8 * 10), int(25 * 8 * 10))))
    o.append(ex('算例 · 码本坍塌是几行代码的事',
                table(['初始化 / 处理', '#前四级各用了多少码', '#四级后 SNR'],
                      [['随机小初始化，不救死码',
                        '#%s' % RQ['collapse']['no_revive']['used'],
                        '#%s dB' % r2(RQ['collapse']['no_revive']['snr'])],
                       ['同样初始化，但把没人用的码搬到误差最大处',
                        '#%s' % RQ['collapse']['revive']['used'],
                        '#%s dB' % r2(RQ['collapse']['revive']['snr'])]], cls='dp')
                + '<p class="why">第一级只有 <strong>%d 个码</strong>被用上（共 1024），'
                  '也就是说 90%% 的码本是死的。'
                  '而修复它不需要任何新算法——'
                  '只要在每轮之后检查哪些码没人用，把它们搬到当前误差最大的样本上。</p>'
                  '<p>真实系统里等价的手段有几种：EMA 更新 + 死码重启、'
                  'k-means 初始化（用数据点而不是随机数）、'
                  '以及给量化损失加一个码本利用率的正则。'
                  '<em>它们解决的是同一个问题。</em></p>'
                  % RQ['collapse']['no_revive']['used'][0]))
    o.append(fml('⑱ token 率就是上下文长度', 'tokrate'))
    o.append(note('声学 token 和语义 token',
                  '<p>上面量化的是声学表示，得到的是<strong>声学 token</strong>：'
                  '信息全（能还原波形），但和文本的对应关系很松，'
                  '一个 LLM 要学会"这段文字对应哪串声学 token"很难。</p>'
                  '<p>另一条路是先用一个自监督语音模型（HuBERT 一类）提特征再量化，'
                  '得到<strong>语义 token</strong>：'
                  '和音素的对应关系紧、数量少，但丢掉了音色和大部分声学细节。</p>'
                  '<p>目前的主流做法是<strong>两级</strong>：'
                  'LLM 先生成语义 token（好学、好控），'
                  '再用另一个模型把语义 token + 音色条件变成声学 token 或直接变成波形。'
                  '<em>这是"把一对多分两步走"在 token 域的版本。</em></p>'))
    o.append('</section>')

    # ── 20 克隆 ───────────────────────────────────────────────
    o.append(sec('s20', '20', '零样本克隆：音色从哪来，泄漏到哪去', '进阶',
                 tldr='给一段几秒的参考音频就能模仿音色。'
                      '但参考音频里<strong>同时带着</strong>音色、口音、情绪、房间和设备——'
                      '模型分不开，就会一起学走。'))
    o.append(fml('⑲ 克隆就是多一个条件', 'clone'))
    o.append(table(['怎么给条件', '做法', '优点', '代价'], [
        ['<strong>说话人嵌入</strong>', '用声纹模型提一个定长向量，加到模型里',
         '简单、可插值、可以做"新音色"', '信息瓶颈太窄，相似度上不去'],
        ['<strong>参考音频当 prompt</strong>', '把参考的声学 token 放在序列最前面，让模型续写',
         '<span class="hi">相似度最高</span>', '连房间和情绪一起学走'],
        ['<strong>交叉注意力</strong>', '让解码器在生成时对参考音频做注意力',
         '比定长向量信息多，比 prompt 可控', '实现复杂，训练要成对数据'],
    ]))
    o.append(step('“音色泄漏”的确切含义'))
    o.append('<p>这个词常被用来指两件不同的事，分清楚很重要：</p>')
    o.append('<ul>'
             '<li><strong>内容泄漏进音色</strong>——'
             '参考音频说了什么内容，合成结果里会带上它的痕迹'
             '（比如参考里有个"啊"，合成的句子里莫名其妙也带上）。'
             '这是条件编码器没有把内容剥干净。</li>'
             '<li><strong>环境泄漏进音色</strong>——'
             '参考是在一个有回声的房间录的，合成结果也带回声；'
             '参考是手机录的，合成结果也带手机的频响。'
             '<em>这是最常见、也最难解决的一种。</em></li>'
             '<li><strong>情绪 / 语速泄漏</strong>——'
             '参考里说话人很激动，合成的中性文本也被读得很激动。'
             '有时这是想要的（风格迁移），有时不是。</li>'
             '</ul>')
    o.append(why('三者的根源是同一个：<strong>参考音频是一个纠缠在一起的信号，'
                 '而训练数据里没有"同一个人在不同房间说不同内容"的成对样本</strong>，'
                 '模型没有信号去学会把它们分开。'))
    o.append(note('工程上能做的几件事',
                  '<ul>'
                  '<li><strong>数据侧</strong>：同一说话人的多条参考随机换着用，'
                  '强迫模型只保留它们的共同点（= 音色）</li>'
                  '<li><strong>增广</strong>：给参考音频加随机混响和噪声，'
                  '让"环境"这一维变得不可靠，模型就不会依赖它</li>'
                  '<li><strong>前端</strong>：参考音频先过一遍去混响和降噪'
                  '（这正好是阵列手册 15 节和 18 节的活）</li>'
                  '<li><strong>解耦损失</strong>：加一个对抗头，'
                  '要求从内容表示里预测不出说话人</li>'
                  '</ul>'))
    o.append(trap('相似度指标本身也会被环境骗',
                  '<p>常用的说话人相似度是用声纹模型算余弦相似度。'
                  '但声纹模型对房间和设备也是敏感的——'
                  '<strong>如果合成结果和参考带着同一个房间的混响，'
                  '相似度会偏高</strong>，而听起来并不更像那个人。</p>'
                  '<p>更可靠的做法：用<em>同一说话人的另一段、另一场景录的音频</em>当参照，'
                  '而不是用那段参考本身。这样环境的共同成分就被排除了。</p>'))

    # ── 20 的定量部分：把"纠缠"量出来 ───────────────────────
    o.append(step('把这三件事量出来'))
    o.append('<p>上面三条都是通行说法。这一节把它们换成数。'
             '做法是造一批"说话人 × 房间 × 内容"的梅尔谱——'
             '说话人是声道长度、基频区间和谱倾斜，'
             '房间是混响拖尾加一条信道曲线，内容是一串音素目标——'
             '再用一个说话人嵌入（长时平均谱，和 x-vector 的一阶统计量同类）去打分。</p>')
    clr = CL['pairs']['raw']
    clc = CL['pairs']['cmn']
    o.append(fig('clone2', '四种配对的相似度、两种评测协议的差距，以及参考时长的断崖。'))
    o.append(table(['配对', '#余弦均值', '#标准差', '说明'], [
        ['同人同室', '#%.4f' % clr['同人同室']['mean'], '#%.4f' % clr['同人同室']['sd'],
         '同一个人、同一个房间，换了内容'],
        ['同人异室', '#%.4f' % clr['同人异室']['mean'], '#%.4f' % clr['同人异室']['sd'],
         '<strong>这一行才是"像不像这个人"</strong>'],
        ['异人同室', '#%.4f' % clr['异人同室']['mean'], '#%.4f' % clr['异人同室']['sd'],
         '不同的人，同一个房间'],
        ['异人异室', '#%.4f' % clr['异人异室']['mean'], '#%.4f' % clr['异人异室']['sd'],
         '冒充者的基准'],
    ], cls='dp'))
    o.append(note('一个我猜错了的假设',
                  '<p>我原本以为：在这种只用一阶统计量的嵌入上，'
                  '房间会盖过说话人——也就是"同一个房间里的两个陌生人，'
                  '会比换了房间的同一个人更像"。</p>'
                  '<p><strong>实测不成立。</strong>换房间掉 %.4f，换人掉 %.4f，'
                  '房间只有说话人的 %.2f 倍；异人同室 %.4f 也确实低于同人异室 %.4f。'
                  '这个嵌入比我以为的稳健。</p>'
                  '<p>但下面那件事仍然成立，而且更值得记住——'
                  '<strong>它成立的原因和"房间有多大影响"没关系</strong>。</p>'
                  % (clr['room_gap'], clr['spk_gap'],
                     clr['room_gap'] / clr['spk_gap'],
                     clr['异人同室']['mean'], clr['同人异室']['mean'])))

    o.append(step('评测协议：同一批嵌入，差 %.0f 倍'
                  % (clr['eer_strict'] / max(clr['eer_naive'], 1e-9))))
    o.append(fml('㉕ 拿什么去比，决定了你测到什么', 'simproto'))
    o.append(table(['协议', '目标对', '冒充对', '#EER'], [
        ['<strong>偷懒</strong>：拿那段参考本身比',
         '合成结果 vs 那段参考（同室）', '异人异室',
         '#<span style="color:var(--hot)">%.2f%%</span>' % clr['eer_naive']],
        ['<strong>严谨</strong>：换一场录音再比',
         '同人异室', '异人异室', '#%.2f%%' % clr['eer_strict']],
    ]))
    o.append(why('差的不是一点，是 <strong>%.0f 倍</strong>。'
                 '而关键在于 EER 比的不是绝对差距，是<strong>两个分布重叠多少</strong>：'
                 '同人异室的标准差只有 %.4f，冒充者那一堆却有 %.4f——'
                 '散得多。所以一点点共有的房间偏置，'
                 '就足以把目标那一堆整体顶上去、和冒充者拉开，'
                 '让数字好看得不像话。'
                 % (clr['eer_strict'] / clr['eer_naive'],
                    clr['同人异室']['sd'], clr['异人异室']['sd'])))
    o.append(ex('顶上去多少',
                '<p>直接量：让合成结果带着参考的房间，和让它是干净的，'
                '分别去和那段参考比。</p>'
                '<p class="step q">带房间 − 不带房间 = <strong>%+.4f ± %.4f</strong>，'
                '%.0f%% 的说话人上都是正的</p>'
                '<p>绝对值不大，和"换房间"本身同一个量级（%.4f）。'
                '但它<strong>方向一致、无一例外</strong>——这是系统性偏置，不是噪声。'
                '系统性偏置正好是 EER 最怕的东西：它不增加方差，只平移均值。</p>'
                % (CL['inflation']['mean'], CL['inflation']['sd'],
                   CL['inflation']['pos_frac'], clr['room_gap'])))

    o.append(step('倒谱均值归一化有用，但不是那个机制'))
    o.append(table(['', '#换房间掉', '#换人掉', '#比值', '#严谨协议 EER'], [
        ['原始', '#%.4f' % clr['room_gap'], '#%.4f' % clr['spk_gap'],
         '#%.2f' % (clr['room_gap'] / clr['spk_gap']), '#%.2f%%' % clr['eer_strict']],
        ['倒谱均值归一化后', '#%.4f' % clc['room_gap'], '#%.4f' % clc['spk_gap'],
         '#%.2f' % (clc['room_gap'] / clc['spk_gap']), '#%.2f%%' % clc['eer_strict']],
    ], cls='dp'))
    o.append(note('第二个我猜错了的地方',
                  '<p>我以为 CMN 的作用是"把信道那一项减掉"，'
                  '所以第二列（换房间掉多少）应该变小。</p>'
                  '<p><strong>它反而变大了</strong>：%.4f → %.4f。'
                  '真正发生的是第三列——<strong>换人的差距被放大了 %.1f 倍</strong>'
                  '（%.4f → %.4f），于是比值从 %.2f 降到 %.2f，'
                  'EER 从 %.2f%% 降到 %.2f%%。</p>'
                  '<p>道理是：长时平均谱里，<em>全局电平</em>占掉了大部分模长，'
                  '而说话人信息在谱的<em>形状</em>上。减掉均值等于把电平那一维扔了，'
                  '剩下的形状差异被归一化放大——说话人和房间都被放大，'
                  '但说话人放大得多。</p>'
                  '<p>结论不变（CMN 该做），但理由不是我原先以为的那个。'
                  '这也解释了为什么它消不掉混响：'
                  '<strong>混响是时间上的拖尾，不是 log 域上的一个常数</strong>，'
                  '减均值碰不到它——那部分还得靠去混响（%s 15 节）。</p>'
                  % (clr['room_gap'], clc['room_gap'],
                     clc['spk_gap'] / clr['spk_gap'], clr['spk_gap'], clc['spk_gap'],
                     clr['room_gap'] / clr['spk_gap'],
                     clc['room_gap'] / clc['spk_gap'],
                     clr['eer_strict'], clc['eer_strict'], ARR)))

    o.append(step('参考音频要几秒'))
    du_ = CL['dur']
    o.append(table(['参考时长', '#同人余弦', '#标准差', '#EER'], [
        ['#%d 秒' % r['sec'], '#%.4f' % r['mean'], '#%.4f' % r['sd'],
         '#%.1f%%' % r['eer']] for r in du_], cls='dp'))
    o.append(why('这是个<strong>断崖，不是斜坡</strong>：1 秒 %.1f%%，3 秒 %.1f%%，'
                 '5 秒 %.1f%%，再长基本不涨。'
                 '而且短参考掉的是<em>均值和方差两头</em>'
                 '（%.4f ± %.4f → %.4f ± %.4f）——'
                 '方差大意味着同样 2 秒的参考，'
                 '有的能用有的不能用，取决于那 2 秒里说了什么音。'
                 % (du_[0]['eer'], du_[2]['eer'], du_[3]['eer'],
                    du_[0]['mean'], du_[0]['sd'], du_[3]['mean'], du_[3]['sd'])))
    o.append(trap('产品上该怎么用这条曲线',
                  '<p><strong>别只写"支持 3 秒克隆"。</strong>'
                  '3 秒那一档的方差是 5 秒的好几倍，意味着用户体验是<em>抽签式</em>的：'
                  '同样录 3 秒，有人觉得很像，有人觉得完全不像，而他们都没做错什么。</p>'
                  '<p>能做的两件事：'
                  '① 引导用户念一段<strong>音素覆盖全</strong>的定稿文本，'
                  '而不是随便说；'
                  '② 录完之后用同一套嵌入自检一下（和第二段比），'
                  '相似度太低就提示重录——这比事后解释便宜得多。</p>'))
    o.append(note('这个实验能说什么、不能说什么',
                  '<p>嵌入是长时平均谱，比真的 ECAPA 粗得多；'
                  '房间是一阶模型；说话人是解析构造的。'
                  '<strong>绝对 EER 不能和公开结果比。</strong></p>'
                  '<p>可比的是<strong>协议之间的倍数关系</strong>，'
                  '和三个机制的方向：房间是系统性偏置、'
                  'CMN 靠放大说话人差异起作用、参考时长有断崖。'
                  '说话人嵌入本身的训练、打分与校准，见 %s。</p>' % SV))
    o.append(q([
        ('报告里写"克隆相似度 0.92"，该追问什么？',
         '<p>追问<strong>拿什么当参照</strong>。同一批嵌入上，'
          '拿那段参考本身去比 EER 是 %.2f%%，换一场录音再比是 %.2f%%，'
          '差 %.0f 倍。前者把参考和合成结果共有的房间也算成了相似度。</p>'
          % (clr['eer_naive'], clr['eer_strict'],
             clr['eer_strict'] / clr['eer_naive']),
         '20 节 · 协议比数字重要'),
        ('参考音频从 3 秒加到 5 秒，值不值？',
         '<p>值，而且是这条曲线上最陡的一段：EER %.1f%% → %.1f%%。'
          '再从 5 秒加到 10 秒就基本不涨了。'
          '更重要的是方差：3 秒那一档的抽签感来自方差，不是均值。</p>'
          % (du_[2]['eer'], du_[3]['eer'])),
        ('参考音频先做倒谱均值归一化，消掉的是什么？',
         '<p>不是房间。实测换房间的代价反而变大（%.4f → %.4f），'
          '是<strong>换人的差距被放大了 %.1f 倍</strong>才让 EER 降下来的。'
          '混响是时间上的拖尾，减均值碰不到它。</p>'
          % (clr['room_gap'], clc['room_gap'],
             clc['spk_gap'] / clr['spk_gap'])),
    ]))
    o.append('</section>')

    # ── 21 采样 ───────────────────────────────────────────────
    o.append(sec('s21', '21', '采样、温度与多样性', '进阶',
                 tldr='TTS 的随机性不是缺陷，是必需品。'
                      '但它和"稳定可复现"直接冲突，'
                      '<strong>这个取舍没有通解，只能按场景定</strong>。'))
    o.append('<p>02 节说过，答案是一个分布。那么生成时"从分布里采一个"就是正确的做法。'
             '但不同架构里，随机性进入的位置不一样：</p>')
    o.append(table(['架构', '随机性在哪', '怎么调'], [
        ['FastSpeech（回归）', '<span style="color:var(--hot)">几乎没有</span>',
         '同一文本每次输出完全一样——稳定，但"念稿感"'],
        ['VITS', '隐变量 z 的采样 + 随机时长预测器', '给 z 的方差乘一个系数'],
        ['扩散 / 流匹配', '初始噪声 + （SDE 时）过程噪声', '换种子；SDE 比 ODE 更多样'],
        ['LLM-TTS', '每一步 token 采样', '温度、top-k、top-p——和文本 LLM 一样'],
    ]))
    o.append(ex('算例 · 温度这个旋钮的两端',
                '<p>用 LLM-TTS 的温度做例子，两端都很具体：</p>'
                + table(['温度', '表现', '适合'],
                        [['#→ 0（贪心）', '每次完全一样；韵律平、像念稿；'
                                      '<strong>容易卡在重复上</strong>（同一个 token 反复出）',
                          '需要严格一致的播报'],
                         ['#0.6–0.8', '自然，有变化，偶尔小瑕疵', '<strong>大多数场景</strong>'],
                         ['#→ 1.2', '表现力强；<span style="color:var(--hot)">开始出错</span>——'
                                 '读错字、加词、破音', '几乎没有合适的场景']], cls='dp')
                + '<p class="why">注意左端的坑：<strong>温度调到 0 不会让它更稳，'
                  '反而会触发重复</strong>。'
                  '因为贪心解码在音频 token 上和在文本 token 上一样，'
                  '会掉进"最高概率的下一个 token 是上一个 token"的循环里。</p>'
                  '<p>实践里的做法是温度保持在 0.7 上下，'
                  '而用<em>重复惩罚</em>和<em>最大长度</em>去防那些病，'
                  '而不是靠降温。</p>'))
    o.append(note('什么时候应该要可复现',
                  '<p><strong>要</strong>：有声书（同一本书前后章节音色语速要一致）、'
                  '导航播报（同一句提示每次都该一样）、'
                  '任何要做 A/B 对比的场景（否则你分不清差异来自改动还是来自采样）。</p>'
                  '<p><strong>不要</strong>：对话式助手（每次完全一样会很诡异）、'
                  '角色配音、任何强调表现力的场景。</p>'
                  '<p>工程上的答案是<strong>把种子暴露成接口</strong>：'
                  '默认随机，需要时可固定。'
                  '这比在模型里选边站要好。</p>'))

    # ── 21 的定量部分：温度到底在调什么 ─────────────────────
    o.append(step('把这个旋钮量出来'))
    o.append('<p>上面那张表是通行说法。这一节把它换成实测。'
             '做法是造一个<strong>真实分布完全已知</strong>的自回归过程'
             '（音素序列 + 时长分布 + 每个音素的发声分布，'
             '所以任何前缀下的真实下一 token 分布都能用前向算法精确算出来），'
             '再在它采出来的语料上训两个小模型：一个数据充足（%s 句），'
             '一个数据饥饿（%s 句）。然后只改采样参数。</p>'
             % ('{:,}'.format(TP['setup']['nbig']), TP['setup']['nsmall']))
    o.append(fml('⑳ 温度只是把 logits 除一下', 'temp'))
    o.append(fig('temp', '左：低温和高温的坏法不是同一种。右：最优温度是校准问题——'
                         '而"过自信会把最优温度压到 1 以下"这个猜想被数据否掉了。'))
    tm = {r['temp']: r for r in TP['temp']}
    o.append(table(['温度', '#复读率', '#越界率', '#长度', '#二元分布对称 KL', '症状'], [
        ['#%.2f' % r['temp'], '#%.1f%%' % r['rep'], '#%.1f%%' % r['off'],
         '#%.1f' % r['len_mean'], '#%.4f' % r['skl'],
         ('<span style="color:var(--hot)">贪心，全部复读到长度上限</span>'
          if r['temp'] == 0 else
          ('复读还很重' if r['rep'] > 20 else
           ('<strong>最好</strong>' if r['temp'] == TP['temp_best']['temp'] else
            ('开始读错' if r['off'] > 18 else '可用'))))]
        for r in TP['temp']], cls='dp'))
    o.append(why('真实序列长 %.1f ± %.1f 帧。温度 1.0 生成的是 %.1f 帧，贪心是 %d 帧'
                 '——<strong>贪心根本停不下来，每一条都撞到长度上限</strong>。'
                 % (TP['true_len']['mean'], TP['true_len']['sd'],
                    tm[1.0]['len_mean'], int(tm[0.0]['len_mean']))))
    o.append(trap('温度调到 0 不是"最稳"，是最不稳',
                  '<p>实测复读率：贪心 <strong>%.1f%%</strong>，温度 0.3 %.1f%%，'
                  '温度 0.7 %.1f%%，温度 1.0 %.1f%%。</p>'
                  '<p>机制很直接：音频 token 里有大量<strong>稳态 token</strong>'
                  '（元音持续的那几帧，发的是同一个 token）。'
                  '贪心每一步都挑概率最高的那个，而在稳态段里概率最高的下一个 token '
                  '就是<em>上一个 token 自己</em>。'
                  '于是它进去就出不来——这不是训练不充分，是贪心解码在这种分布上的必然结果。</p>'
                  '<p>所以"想稳一点就把温度调低"这个直觉，在 TTS 上是反的。</p>'
                  % (tm[0.0]['rep'], tm[0.3]['rep'], tm[0.7]['rep'], tm[1.0]['rep'])))

    o.append(step('那最优温度到底由什么决定'))
    o.append(fml('㉑ 校准：模型说的把握，和它真有的把握', 'calib'))
    cb = TP['calib']
    o.append(table(['模型', '#平均最高概率', '#那个 token 的真实概率', '#差', '#最优温度'], [
        ['数据充足（%s 句）' % '{:,}'.format(TP['setup']['nbig']),
         '#%.3f' % cb['big']['conf'], '#%.3f' % cb['big']['true_p_of_argmax'],
         '#%+.3f' % (cb['big']['conf'] - cb['big']['true_p_of_argmax']),
         '#<strong>%.1f</strong>' % TP['temp_best']['temp']],
        ['数据饥饿（%d 句）' % TP['setup']['nsmall'],
         '#%.3f' % cb['small']['conf'], '#%.3f' % cb['small']['true_p_of_argmax'],
         '#<span style="color:var(--hot)">%+.3f</span>'
         % (cb['small']['conf'] - cb['small']['true_p_of_argmax']),
         '#<strong>%.1f</strong>' % TP['temp_small']['temp']
         if False else '#<strong>%.1f</strong>' % TP['temp_small_best']['temp']],
    ], cls='dp'))
    o.append(note('一个我猜错了的假设',
                  '<p>我原本的推理是这样的：既然温度 &lt; 1 等于把分布削尖，'
                  '那它应该是在补偿模型的<strong>不够尖</strong>；'
                  '反过来，一个过自信的模型应该需要温度 &gt; 1 才对——'
                  '而实践里大家用 0.7，说明模型多半是<em>不够自信</em>的。</p>'
                  '<p>于是我把一个模型故意训成数据饥饿的。它<strong>确实过自信</strong>：'
                  '平均最高概率 %.3f，而它指的那个 token 的真实概率只有 %.3f，差了快一倍。</p>'
                  '<p><strong>但它的最优温度不是 &gt; 1 也不是 &lt; 1 的某个补偿值，'
                  '而是 %.1f——和校准良好的那个几乎一样。</strong></p>'
                  '<p>为什么：过自信不是"整条分布均匀地削尖了"，'
                  '而是<strong>把质量压在了错的模态上</strong>。'
                  '温度是个全局标量，它能改变分布的尖锐程度，'
                  '改不了"尖在哪儿"。用它去修一个模态错了的模型，修不动。</p>'
                  % (cb['small']['conf'], cb['small']['true_p_of_argmax'],
                     TP['temp_small_best']['temp'])))
    o.append(why('那实践里的 0.7 是从哪来的？这组数据给不出答案，只能划掉几个解释：'
                 '<strong>不是</strong>因为模型过自信（上面否掉了），'
                 '<strong>不是</strong>因为低温更稳（复读率否掉了）。'
                 '剩下比较可能的是：真实系统的序列比这里长一个量级，'
                 '误差会沿着自回归累积，而<em>一次破音毁掉整句</em>的代价'
                 '远大于韵律平一点——也就是说，'
                 '0.7 修的不是分布，是<strong>尾部风险</strong>。'))

    o.append(step('top-p 和重复惩罚，各自修什么'))
    tp0 = {r['topp']: r for r in TP['topp']}
    o.append(table(['top-p', '#复读率', '#越界率', '#二元对称 KL（数据充足）',
                    '#二元对称 KL（数据饥饿）'], [
        ['#%.2f' % r['topp'], '#%.1f%%' % r['rep'], '#%.1f%%' % r['off'],
         '#%.4f' % r['skl'],
         '#%.4f' % [x for x in TP['topp_small'] if x['topp'] == r['topp']][0]['skl']]
        for r in TP['topp']], cls='dp'))
    o.append(note('第二个我猜错了的假设',
                  '<p>我以为 top-p 是比降温更便宜的旋钮——它只砍尾巴，不动主体。</p>'
                  '<p>两个模型上都不成立：p 越小，二元分布离真实越远，'
                  '而且是单调的（充足：%.4f → %.4f；饥饿：%.4f → %.4f）。</p>'
                  '<p><strong>截尾和降温是同一件事</strong>：都是把概率质量往众数上挤。'
                  '砍掉的那条尾巴里，有一部分本来就是合法的读法——'
                  '而 TTS 的"合法读法"本来就比文本生成多得多（02 节那 %s%% 的时长不确定性）。</p>'
                  % (tp0[1.0]['skl'], tp0[0.7]['skl'],
                     [x for x in TP['topp_small'] if x['topp'] == 1.0][0]['skl'],
                     [x for x in TP['topp_small'] if x['topp'] == 0.7][0]['skl'],
                     r1(S['explain']['dur']))))
    o.append(fml('㉒ 重复惩罚：按已经出现的次数打折', 'reppen'))
    o.append(table(['重复惩罚', '#贪心下的复读率', '#长度（真实 %.1f）'
                    % TP['true_len']['mean']], [
        ['#%.2f' % r['reppen'], '#%.1f%%' % r['rep'], '#%.1f' % r['len_mean']]
        for r in TP['reppen']], cls='dp'))
    o.append(why('重复惩罚确实能止住复读，但代价写在第三列上：'
                 '压住复读的那一档，时长已经被压到 %.1f 帧（真实 %.1f）。'
                 '因为它扣的是"这个 token 已经出现过几次"——'
                 '而在 TTS 里，<strong>重复的 token 本来就是合法的</strong>：'
                 '一个元音要持续好几帧，发的就是同一串 token。'
                 '文本生成里重复基本等于病，音频 token 里不是。'
                 % (TP['reppen'][-1]['len_mean'], TP['true_len']['mean'])))
    o.append(trap('所以这三个旋钮的分工是',
                  '<p><strong>温度</strong>——调的是"生成的分布像不像真实分布"。'
                  '校准得好的模型，1.0 就是最优，不用动。</p>'
                  '<p><strong>top-p</strong>——不是免费的降温。'
                  '要用就用 0.95 以上，0.8 以下的收益在这组数据上看不到。</p>'
                  '<p><strong>重复惩罚 / 最大长度</strong>——'
                  '这才是复读的对症药，但在音频 token 上要比文本生成保守得多，'
                  '而且要盯住时长有没有被压短。</p>'
                  '<p>最该避免的组合是<em>低温 + 无重复惩罚</em>：'
                  '两个方向都朝着复读走。</p>'))
    o.append(note('这个实验能说什么、不能说什么',
                  '<p>真实过程是解析构造的，序列只有 %.0f 帧、词表只有 %d——'
                  '比真的音频 token 小两个量级。所以<strong>绝对数值不能外推</strong>。</p>'
                  '<p>可外推的是三件事的方向：贪心会复读（机制是稳态 token 的自吸引）、'
                  '最优温度由校准决定（不由口味决定）、'
                  '截尾和降温是同一类操作。这三条都不依赖规模。</p>'
                  % (TP['true_len']['mean'], TP['setup']['V'])))
    o.append(q([
        ('把温度调到 0 想让输出更稳定，会发生什么？',
         '<p>反而最不稳：实测复读率 %.1f%%，每一条都撞到长度上限。'
          '因为音频 token 里有大量稳态 token（元音持续的那几帧），'
          '贪心在那里的最优下一步就是重复自己。</p>' % tm[0.0]['rep'],
         '21 节 · 和文本生成的直觉相反'),
        ('一个过自信的模型，该把采样温度调高还是调低？',
         '<p>实测两个都不对。数据饥饿的模型确实过自信（%.3f vs 真实 %.3f），'
          '但它的最优温度仍然是 %.1f。'
          '<strong>过自信是模态错了，不是整体削尖了</strong>，'
          '而温度是个全局标量，改不了尖在哪儿。</p>'
          % (cb['small']['conf'], cb['small']['true_p_of_argmax'],
             TP['temp_small_best']['temp'])),
        ('复读了，该调温度还是加重复惩罚？',
         '<p>加重复惩罚。但要盯住时长：实测压住复读的那一档，'
          '长度从真实的 %.1f 帧被压到 %.1f 帧——'
          '因为元音本来就要连发好几个相同的 token。</p>'
          % (TP['true_len']['mean'], TP['reppen'][-1]['len_mean'])),
    ]))
    o.append('</section>')

    # ══════════════════════════════════════════════════════════
    o.append(part('Part Ⅴ', '工程落地', '延迟、算力、选型、评测、数据、安全'))

    # ── 22 延迟 ───────────────────────────────────────────────
    o.append(sec('s22', '22', '流式与首包延迟', '进阶',
                 lede='"感觉不到延迟"的门槛大约是 300 ms。这一节把这 300 ms 拆开，'
                      '看每一块花在哪儿。'))
    for b in EV['latency']:
        rows = [[k, '#%s ms' % r1(v)] for k, v in b['items']]
        rows.append(['<strong>合计</strong>', '#<strong>%s ms</strong>　%s'
                     % (r1(b['total']), '✓ 够快' if b['total'] < 300 else '✗ 能感觉到')])
        o.append('<h3>%s</h3>' % b['name'])
        o.append(table(['环节', '#耗时'], rows))
    o.append(why('三份预算里，只有 LLM-TTS 那份超标，而且超得很有代表性：'
                 '<strong>240 ms 全花在"凑够第一个音频块"上</strong>——'
                 '25 帧 × 8 级 = 200 次自回归前向，每次 1.2 ms。'
                 '这不是模型慢，是 token 太多（19 节）。'))
    o.append(table(['优化手段', '省下什么', '代价'], [
        ['<strong>降帧率</strong>（86 → 25 Hz）', '<span class="hi">token 数降到 1/3.4</span>',
         '时长分辨率变成 40 ms，韵律变粗'],
        ['<strong>delay pattern</strong>（多级错位并行出）',
         '<span class="hi">8 级变成 1 次前向</span>', '实现复杂，前几帧要填充'],
        ['<strong>后几级交给非自回归头</strong>', '自回归只做 1–2 级', '音质略降'],
        ['<strong>更小的首块</strong>（25 → 10 帧）', '首包提前 60%',
         '块边界处的韵律衔接变差'],
        ['<strong>蒸馏成少步 / 一步</strong>（流匹配那一支）',
         '<span class="hi">NFE 从 32 降到 1–4</span>', '要额外一轮训练，质量略降'],
    ]))
    o.append(trap('别把"块"切得太小',
                  '<p>流式声码器按块生成，块越小首包越快。但有两个隐藏成本：</p>'
                  '<p><strong>一、边界伪影。</strong>'
                  '卷积的感受野跨块，块边界处上下文不全，会出现轻微的不连续。'
                  '对策是块之间重叠几帧再做交叉淡入，但那又增加了算力。</p>'
                  '<p><strong>二、算力利用率。</strong>'
                  '同样的总帧数，切成十个小块比切成一个大块慢——'
                  '因为每块都有固定开销。<em>端侧尤其明显。</em></p>'))

    # ── 22 的定量部分：感受野是结构给的 ─────────────────────
    o.append(step('"块边界的伪影"到底有多大'))
    o.append('<p>上面那段是通行说法。这一节把它量出来。'
             '做法是搭一个 HiFi-GAN 形状的声码器（四级转置卷积 + 多感受野残差块，'
             '权重随机但固定——<strong>要量的是上下文依赖，那是结构决定的，'
             '不是训练决定的</strong>），'
             '然后用扰动法实测：改一帧梅尔，看输出的哪些样点跟着变。</p>')
    rf_ = CK['rf']
    o.append(table(['量', '#值', '含义'], [
        ['左感受野', '#%.1f 帧（%.0f ms）' % (rf_['left_frames'], rf_['left_ms']),
         '流式时要留多长的缓存'],
        ['<strong>右感受野</strong>',
         '#<strong>%.1f 帧（%.0f ms）</strong>' % (rf_['right_frames'], rf_['right_ms']),
         '流式时<strong>只能等，不能省</strong>'],
        ['一帧梅尔影响的总跨度', '#%.0f ms' % rf_['total_ms'], '这是"一帧的责任范围"'],
    ], cls='dp'))
    o.append(fml('㉓ 首包延迟：结构那一项拿不掉', 'rf'))
    o.append(fig('stream', '右感受野实测 %.1f 帧；块大小把首包延迟和摊销算力往两个方向拉。'
                 % rf_['right_frames']))
    o.append(table(['给的右上下文', '#附加延迟', '#相对整句的误差', '判断'], [
        ['#%d 帧' % r['right'], '#%.0f ms' % r['lat_ms'],
         '#%s' % ('误差为 0' if r['db'] < -99 else '%.1f dB' % r['db']),
         ('听得出' if r['db'] > -25 else ('边缘' if r['db'] > -40 else
          ('<strong>逐比特相同</strong>' if r['db'] < -99 else '听不出')))]
        for r in CK['right']], cls='dp'))
    o.append(why('给到 %d 帧（%.0f ms）误差就掉到 %.0f dB；'
                 '给到 6 帧——刚好盖住 %.1f 帧的右感受野——'
                 '流式输出和整句输出<strong>逐比特相同</strong>。'
                 '这反过来验证了扰动法测出的那个数：'
                 '<em>感受野是个硬边界，不是渐变</em>。'
                 % (CK['right_ok']['right'], CK['right_ok']['lat_ms'],
                    CK['right_ok']['db'], rf_['right_frames'])))
    o.append(note('和 ASR 那本的前瞻是镜像关系',
                  '<p>' + ASR + '的 30 节量过流式 ASR 的前瞻：'
                  '最优 6 帧 = 240 ms，两端各有一个失效机制，是个 U 形。</p>'
                  '<p>这里不是 U 形，是<strong>单调的阶梯</strong>——给够就停，'
                  '多给一帧也不会更好。</p>'
                  '<p>差别在于两边等的东西不是一回事：'
                  '<strong>ASR 等的是"证据还没到齐"</strong>，'
                  '所以等太久会让已定下的假设被推翻，两端都坏；'
                  '<strong>TTS 等的是"这段波形还没算完"</strong>，'
                  '这是个确定性的卷积依赖，够了就是够了。</p>'))

    o.append(step('块切小一点，代价在哪'))
    o.append(fml('㉔ 块越小，摊销开销越大', 'chunkcost'))
    o.append(table(['块帧数', '#首包延迟', '#每块多算的比例', '#相对整句误差'], [
        ['#%d' % r['chunk'], '#%.0f ms' % r['lat_ms'], '#%.0f%%' % r['overhead'],
         '#%.1f dB' % r['db']] for r in CK['chunk']], cls='dp'))
    ck_ = {r['chunk']: r for r in CK['chunk']}
    o.append(why('块从 16 帧切到 4 帧，首包从 %.0f ms 降到 %.0f ms（省了 %.0f%%），'
                 '但每块多算的比例从 %.0f%% 涨到 %.0f%%。'
                 '<strong>省下的延迟是拿算力买的，而且是加速涨价的</strong>——'
                 '因为左右文是固定的几帧，块越小它们占的比重越大。'
                 % (ck_[16]['lat_ms'], ck_[4]['lat_ms'],
                    (1 - ck_[4]['lat_ms'] / ck_[16]['lat_ms']) * 100,
                    ck_[16]['overhead'], ck_[4]['overhead'])))

    o.append(step('右上下文给不起的时候'))
    xf_ = CK['xfade']
    o.append(table(['交叉淡入', '#毫秒', '#相对整句误差', '#边界的包络跳变'], [
        ['#%d 样点' % r['xfade'], '#%.1f' % r['ms'], '#%.1f dB' % r['db'],
         '#%.2f×' % r['seam']] for r in xf_], cls='dp'))
    o.append(why('整句输出在同样位置的包络跳变是 %.2f×，那是"没有咔哒"的基准。'
                 '不做淡入时是 %.2f×，淡入 %d 个样点（%.1f ms）压回 %.2f×，'
                 '但总误差只从 %.1f dB 变到 %.1f dB。'
                 % (CK['seam_full'], xf_[0]['seam'], xf_[-1]['xfade'], xf_[-1]['ms'],
                    xf_[-1]['seam'], xf_[0]['db'], xf_[-1]['db'])))
    o.append(trap('淡入消的是"咔哒"，不是误差',
                  '<p>这两件事经常被混在一起。实测：不给右上下文时，'
                  '<strong>%.0f%% 的误差能量落在每块的最后 5 帧里</strong>，'
                  '而那一段只占全长的 %.0f%%——'
                  '远离边界的地方，流式输出和整句是逐比特相同的。</p>'
                  '<p>交叉淡入做的是把这段误差<em>抹匀</em>：'
                  '包络不再有台阶，所以听不到咔哒；'
                  '但那几帧的波形依然是错的，只是错得不刺耳。</p>'
                  '<p>所以它是"右上下文给不起时的止痛药"，不是替代品。'
                  '真要省，该省的是块大小，不是右上下文。</p>'
                  % (xf_[0]['conc'], CK['seam_span'])))
    o.append(q([
        ('流式声码器的右上下文能不能干脆不给？',
         '<p>不能。实测不给时相对整句的误差是 %.1f dB，听得出来；'
          '而且 %.0f%% 的误差能量集中在每块的最后几帧，表现为块边界的包络台阶'
          '（跳变 %.2f×，基准 %.2f×）。'
          '给够 %d 帧（%.0f ms）就掉到 %.0f dB。</p>'
          % (CK['right'][0]['db'], xf_[0]['conc'], xf_[0]['seam'], CK['seam_full'],
             CK['right_ok']['right'], CK['right_ok']['lat_ms'], CK['right_ok']['db']),
         '22 节 · 这是结构给的，不是实现不好'),
        ('把块从 16 帧切到 4 帧，代价是什么？',
         '<p>首包从 %.0f ms 降到 %.0f ms，但每块多算的比例从 %.0f%% 涨到 %.0f%%。'
          '左右文是固定的几帧，块越小它们占比越大——延迟是拿算力买的。</p>'
          % (ck_[16]['lat_ms'], ck_[4]['lat_ms'],
             ck_[16]['overhead'], ck_[4]['overhead'])),
        ('TTS 的流式右上下文和 ASR 的流式前瞻，是同一回事吗？',
         '<p>不是。ASR 的前瞻是 U 形（前瞻太长，已定下的假设被后来的观测推翻的机会变多）；'
          'TTS 的右上下文是单调阶梯——它等的是一个确定性的卷积依赖，够了就够了，'
          '多给一帧也不会更好。详见 ' + ASR + ' 30 节。</p>'),
    ]))
    o.append('</section>')

    # ── 23 算力 ───────────────────────────────────────────────
    o.append(sec('s23', '23', '端侧与算力：把乘加数点出来', '深入',
                 tldr='不引用任何"别人测的 RTF"，直接按 HiFi-GAN 的结构数乘加。'
                      '结论：<strong>V1 在手机大核上 RTF %s，根本跑不动</strong>；'
                      '算力的 %s%% 花在 MRF 上。'
                      % (r2(EV['variants'][0]['rtf8']), r1(EV['flops']['frac']['MRF']))))
    o.append(code('数法（HiFi-GAN V1 的结构）',
                  'conv_pre   : 80 → 512，核 7，在帧率上跑\\n'
                  '四级上采样  : 步长 8, 8, 2, 2（乘起来 = hop 256），核长 = 2×步长\\n'
                  '             通道 512 → 256 → 128 → 64 → 32\\n'
                  '每级后接 MRF: 3 个核宽 (3,7,11) × 3 个空洞 (1,3,5) × 每个 2 层卷积\\n'
                  'conv_post  : 32 → 1，核 7\\n'
                  '\\n'
                  '每个输出样点的 MAC = Σ (输入通道 × 输出通道 × 核长 × 该层的相对采样率)'))
    NAME = {'MRF': 'MRF（多尺度空洞卷积）', 'upsample': '转置卷积上采样',
            'conv_pre': '输入卷积', 'conv_post': '输出卷积'}
    o.append(table(['段落', '#占总乘加数'],
                   [[NAME.get(k, k), '#%s%%' % r1(v)]
                    for k, v in sorted(EV['flops']['frac'].items(), key=lambda x: -x[1])]))
    o.append(table(['变体', '#MAC / 样点', '#GFLOP/s @22.05 kHz', '#手机大核（8 GFLOPS）RTF'],
                   [[v['name'], '#%s' % format(int(v['mac']), ','),
                     '#%s' % r2(v['gflops']),
                     '#%s %s' % (r2(v['rtf8']), '✓' if v['rtf8'] < 0.5 else '✗')]
                    for v in EV['variants']]))
    o.append(why('这张表解释了几件在实践中反复出现的事：'
                 '<strong>①</strong> HiFi-GAN V1 是服务端模型，端侧必须用 V2/V3；'
                 '<strong>②</strong> 算力几乎全在 MRF 上，'
                 '所以"砍 MRF"（少一个核宽、少一个空洞）是最划算的裁剪方向；'
                 '<strong>③</strong> 反混叠（内部 2× 采样）让算力直接翻倍——'
                 '<em>端侧必须在音质和"能跑"之间选一个</em>。'))
    o.append(trap('MAC 数不等于实际速度',
                  '<p>上面是纯算术。实际速度还要看访存、算子融合、'
                  '有没有用上 NEON/SIMD、以及框架的开销。'
                  '通道数很少的层（最后几级）往往是<strong>访存受限</strong>而不是算力受限，'
                  '砍它们的 MAC 数不会按比例提速。</p>'
                  '<p>所以这张表的正确用法是<strong>排序和定量级</strong>，'
                  '不是预测毫秒数。要毫秒数只能实测。</p>'))
    o.append(xref([
        '<b>乘加数怎么换算成毫瓦、常驻模型的功耗预算怎么定</b>——%s（18 节）'
        '按常驻唤醒的场景算过一遍，这里只给 TTS 侧的算力分解。' % SV,
        '<b>分块大小与状态缓存的定量扫描</b>——本书 <a href="#s22">22 节</a>，'
        '那里有实测的感受野和摊销开销曲线。']))
    o.append('</section>')

    # ── 24 选型 ───────────────────────────────────────────────
    o.append(sec('s24', '24', '选型速查', '入门'))
    o.append(table(['场景', '推荐形态', '为什么'], [
        ['<strong>固定音色、长文本播报</strong>（有声书、新闻）',
         'FastSpeech 系 + HiFi-GAN，或流匹配少步',
         '稳定可复现最重要；一致性 &gt; 表现力'],
        ['<strong>对话助手</strong>（实时、要自然）', '流匹配 + 流式声码器',
         '首包 &lt; 200 ms 做得到；表现力够用'],
        ['<strong>零样本克隆</strong>', 'LLM-TTS 或带 prompt 的流匹配',
         '相似度这一项其它路线追不上'],
        ['<strong>多语种 / 跨语种克隆</strong>', 'LLM-TTS',
         '语言模型的多语种能力可以继承'],
        ['<strong>端侧离线</strong>', '小 FastSpeech + HiFi-GAN V3 / 轻量声码器',
         '23 节那张表：只有这一档 RTF 够'],
        ['<strong>高表现力配音</strong>', 'VITS 系或扩散，配人工韵律标注',
         '要能注入 SSML；纯端到端控不住'],
    ]))
    o.append(note('一条不太讨喜但实用的建议',
                  '<p>如果你的产品对"读对"比对"好听"更敏感'
                  '（金融播报、医疗提示、导航），'
                  '<strong>优先把预算花在前端上</strong>：TN、G2P、多音字词典、韵律标注。</p>'
                  '<p>04–07 节那些错误是内容错误，用户会当成产品 bug 投诉；'
                  '而声学模型换一代带来的自然度提升，'
                  '在 26 节那个功效分析下多半<em>测不出来</em>。</p>'))
    o.append('</section>')

    # ── 25 翻车点 ─────────────────────────────────────────────
    o.append(sec('s25', '25', '七个翻车点', '入门'))
    for i, (t, d) in enumerate([
        ('前端只测了词表，没测真实文本',
         '在 pypinyin 的词表上 G2P 准确率 %s%%，换成新闻稿会掉好几个点——'
         '因为真实文本里“的、了、着”这类高频多音字占比高得多（05 节）。'
         '<strong>评测集必须是真实文本。</strong>' % ('%.2f' % G['prior']['char_acc'])),
        ('用 L2 验证损失判断质量好坏',
         'L2 降到底就是条件均值，而条件均值正是最糊的答案（01 节）。'
         '<strong>在一对多问题上，验证损失和主观质量在某个点之后是反相关的。</strong>'),
        ('对齐器换了，时长模型没重训',
         'MFA、MAS、教师注意力给出的边界系统性地不同（17 节）。'
         '换对齐器等于换了训练目标，时长模型必须跟着重训，否则语速会整体偏移。'),
        ('转置卷积核长不是步长的整数倍',
         '输出带上 3.01 dB 的周期性功率调制，谱上一根固定亮线，'
         '听感是固定音高的电流声（18 节）。<strong>所有损失曲线都正常，只能靠听或看谱。</strong>'),
        ('端侧直接搬服务端的声码器',
         'HiFi-GAN V1 在 8 GFLOPS 的手机大核上 RTF %s（23 节）。'
         '<strong>不是"慢一点"，是根本跑不动。</strong>' % r2(EV['variants'][0]['rtf8'])),
        ('用 MOS 判断一个 0.1 分的改动',
         '在"两批人分别听"的设计下，ΔMOS = 0.1 <strong>320 人也测不出来</strong>（26 节）。'
         '改成组内设计（同一批人听两套），40 人 × 50 句就够。'),
        ('克隆的相似度指标被房间骗了',
         '用那段参考音频本身当参照算相似度，环境的共同成分会把分数抬高（20 节）。'
         '<strong>要用同一个人另一场景录的音频当参照。</strong>'),
    ], 1):
        o.append('<h4>%d. %s</h4><p>%s</p>' % (i, t, d))
    o.append('</section>')

    # ── 26 评测 ───────────────────────────────────────────────
    o.append(sec('s26', '26', '评测方法：要多少样本才测得准', '深入',
                 tldr='ΔMOS = 0.1 在"两批人分别听"的设计下 <strong>320 人也测不出来</strong>；'
                      '改成同一批人听两套，40 人 × 50 句就够。'
                      '<strong>听测设计比听测人数值钱。</strong>'))
    o.append(note('这一节的数是怎么来的',
                  '<p>方差参数是<strong>假设</strong>，取自公开听测里常见的量级：'
                  '评分噪声 σ=%s，评分人偏置 σ=%s，句子难度 σ=%s（五分制）。'
                  '给定这组假设之后，下面的功效计算是精确的蒙特卡洛。</p>'
                  '<p>换一组参数结论会变，但<em>数量级和三种设计之间的相对关系不会变</em>——'
                  '那才是这一节要说的东西。</p>'
                  % (EV['assume']['sd_noise'], EV['assume']['sd_rater'],
                     EV['assume']['sd_sent'])))
    o.append(fml('⑳ 为什么组内设计省这么多', 'mospower'))
    o.append(table(['ΔMOS', '#组内（同一批人听两套）', '#独立（两批人分别听）', '#CMOS'],
                   [['#%s' % ('%.2f' % r['delta']),
                     '#%s' % (r['paired'].get('20句') or '&gt;160'),
                     '#%s' % (r['indep'].get('20句') or '<strong>测不出</strong>'),
                     '#%s' % (next((c['raters_20sent'] for c in EV['cmos']
                                    if c['delta'] == r['delta']), None) or '&gt;160')]
                    for r in EV['mos']], cls='dp'))
    o.append(why('“20 句”那一列，三种设计差了一个量级。'
                 '道理写在公式里：独立设计要摊三份方差（噪声 + 评分人 + 句子），'
                 '组内设计把后两份差掉了，只剩噪声那一份。'
                 '<strong>这是听测里唯一一个"不花钱就能拿到"的改进。</strong>'))
    o.append(fig('mos',
                 '<strong>左边是主观，右边是客观。</strong>'
                 '论文里那些"MOS 提升 0.08"的结论，多数经不起这个检验。'
                 '而 ASR 回环测可懂度，CER 3%% vs 4%% 只要 %d 句就有八成把握，'
                 '<em>而且不用请人</em>。'
                 % EV['wer'][1]['sents']))
    o.append(table(['要测的差距', '#需要多少句（ASR 回环）'],
                   [['CER %s%% vs %s%%' % (r1(w['w1'] * 100), r1(w['w2'] * 100)),
                     '#%s' % (w['sents'] or '&gt;5000')] for w in EV['wer']]))
    o.append(note('一套能用的评测流程',
                  '<ol>'
                  '<li><strong>CI 里跑客观指标</strong>：ASR 回环 CER、'
                  '说话人相似度、时长/基频 RMSE、以及一个"有没有异常长的静音"的检查。'
                  '几百句，几分钟跑完，守住"没有明显翻车"这条线。</li>'
                  '<li><strong>迭代用 CMOS</strong>：20 位评分人 × 20 句，'
                  '能稳定检出 0.2 分的差距。'
                  '一定要同一批人、同一批句子、随机化 A/B 顺序。</li>'
                  '<li><strong>发版前做一次绝对 MOS</strong>：'
                  '只用来对外报数和跨版本存档，不用来做决策。</li>'
                  '<li><strong>始终保留一组"难句"</strong>：'
                  '长句、专业术语、中英混排、数字密集、多音字密集。'
                  '<em>均值会掩盖这些句子上的崩溃，而用户只记得崩溃。</em></li>'
                  '</ol>'))
    o.append(xref([
        '<b>样本量、置信区间与"两个系统差 0.3 分算不算赢"的一般算法</b>——%s（04 节）'
        '把这套统计推导写全了，那里的结论对 MOS 和 CMOS 同样适用。' % SV]))
    o.append('</section>')

    # ── 27 数据 ───────────────────────────────────────────────
    o.append(sec('s27', '27', '数据、清洗与标注', '进阶'))
    o.append(table(['环节', '要点', '踩过的坑'], [
        ['<strong>录音</strong>', '同一话筒、同一房间、同一距离；'
                           '声压级一致；避免换季换设备',
         '中途换了话筒 → 模型学到两个"音色"，合成时会飘'],
        ['<strong>切句</strong>', '按语义切，不要按静音切；句首句尾留 100–200 ms 静音',
         '静音切法会把连读处切断，时长模型学到错误边界'],
        ['<strong>文本核对</strong>', '<strong>必须逐句核对念的和写的一致</strong>',
         '录音员漏字、加字、读错——这是训练数据里最毒的噪声'],
        ['<strong>音量归一</strong>', '按响度（LUFS）而不是峰值归一',
         '峰值归一会让安静的句子被放大，底噪跟着放大'],
        ['<strong>静音处理</strong>', '句首句尾裁到固定长度；句中的长静音要么保留要么标注',
         '裁得太干净 → 模型不会停顿；不裁 → 模型学会随机拖长'],
        ['<strong>对齐</strong>', 'MFA 或 MAS；<strong>要抽查浊音→浊音的边界</strong>',
         '17 节：那里的误差可以到 %s ms' % r0(list(AL['bykind'].values())[-1][1])],
        ['<strong>韵律标注</strong>', '至少标到韵律短语层（#2/#3）',
         '标注员一致性通常只有八成，要做交叉校验'],
    ]))
    o.append(ex('算例 · 一条脏数据能有多贵',
                '<p>假设 10 小时训练数据里有 1% 的句子"念的和写的不一致"——'
                '大约 6 分钟、几十句。</p>'
                '<p>这几十句会教给模型一件事：'
                '<strong>“文本里有这个字，音频里可以没有”</strong>。'
                '在自回归模型上，这会直接表现为<em>推理时随机漏字</em>；'
                '在 FastSpeech 上，会表现为那几个音素的时长预测异常。</p>'
                '<p class="why">对策不是"数据洗干净"（做不到），而是<strong>用 ASR 做回环筛选</strong>：'
                '把训练音频过一遍 ASR，和文本比对，CER 超过阈值的句子直接丢掉。'
                '几十行代码，能去掉绝大部分这类噪声。</p>'))
    o.append(note('多说话人数据的一个常见误区',
                  '<p>"多凑几个说话人，数据量上去了，模型就更好"——'
                  '这句话只在<strong>录音条件一致</strong>时成立。</p>'
                  '<p>如果每个说话人的录音环境不同，'
                  '说话人嵌入就会把"房间"也编码进去（20 节）。'
                  '结果是：单说话人的合成质量没提升，'
                  '零样本克隆反而学会了"换个人就换个房间"。</p>'))
    o.append(xref([
        '<b>合成数据与真实数据的配比、训练覆盖不到的场景会怎么掉</b>——%s（17 节）'
        '有一组扫描：训练时没见过的噪声类型，模型的表现不是缓慢变差，'
        '而是掉到接近不处理。TTS 的说话人覆盖是同一件事。' % ENH]))
    o.append('</section>')

    # ── 28 安全 ───────────────────────────────────────────────
    o.append(sec('s28', '28', '安全：伪造、水印与同意', '入门',
                 lede='零样本克隆只要几秒参考音频。这件事在技术上是成就，'
                      '在产品上是一个必须处理的风险。'))
    o.append(table(['风险', '具体是什么', '现实中的对策'], [
        ['<strong>身份冒用</strong>', '用几秒公开音频克隆某人的声音，'
                              '用于诈骗、伪造证据、绕过声纹认证',
         '声纹认证不能单独作为身份凭证；高风险操作要多因素'],
        ['<strong>未经同意的克隆</strong>', '用配音演员、公众人物的录音训练或克隆',
         '产品侧做声音所有权校验；训练数据要有授权链'],
        ['<strong>内容伪造</strong>', '让某人"说出"他没说过的话',
         '水印 + 检测；平台侧的溯源'],
    ]))
    o.append(step('水印：能做到什么，做不到什么'))
    o.append('<ul>'
             '<li><strong>能做到</strong>：在合成音频里嵌入一段人耳听不见的标记，'
             '经过常见的压缩、重采样、轻度加噪之后仍能检出。'
             '这对"证明这段音频是我家系统生成的"是有效的</li>'
             '<li><strong>做不到</strong>：防住一个有动机的攻击者。'
             '重新录制（拿喇叭放出来再录）、'
             '过一遍另一个声码器、'
             '或者直接用开源模型自己生成——水印都不在了</li>'
             '</ul>')
    o.append(why('所以水印的正确定位是<strong>合规与溯源工具</strong>，'
                 '不是安全防线。'
                 '它解决的是"平台能不能证明这是 AI 生成的"，'
                 '而不是"坏人能不能伪造声音"。'))
    o.append(note('几条实际可执行的产品规则',
                  '<ul>'
                  '<li>克隆功能要求<strong>本人实时朗读一段随机文本</strong>做校验，'
                  '而不是上传一段音频就行</li>'
                  '<li>所有合成音频默认加水印，并在元数据里标注</li>'
                  '<li>保留合成日志（谁、什么时候、合成了什么文本），'
                  '便于事后追溯</li>'
                  '<li>公众人物音色列入拒绝名单，并定期更新</li>'
                  '<li><strong>不要把声纹当密码</strong>——'
                  '这一条要写进所有涉及语音认证的设计文档</li>'
                  '</ul>'))
    o.append('</section>')

    # ══════════════════════════════════════════════════════════
    o.append(part('Part Ⅶ', '难点与趋势', '哪些还没解决，正在往哪儿走'))

    o.append(sec('s29', '34', '当前的真正难点', '入门'))
    o.append(table(['难点', '现状'], [
        ['<strong>长文本的韵律一致性</strong>',
         '一段三分钟的有声书，模型没有"前面读到哪了"的记忆；'
         '语速、音高、情绪会在段落之间漂。'
         '<em>这是目前用户最容易感知、技术上最没解法的一条。</em>'],
        ['<strong>可控性</strong>',
         '端到端模型学到了韵律，但没有旋钮。'
         '想让某个词重读、某处停 300 ms，只能靠 SSML 打补丁，'
         '而模型对 SSML 的响应本身就不稳定'],
        ['<strong>数字和专有名词</strong>',
         'TN 永远有边界情况（04 节）。'
         'LLM-TTS 看起来能靠语言知识解决，'
         '但它同时带来了"编内容"的风险'],
        ['<strong>评测</strong>',
         '26 节：0.1 分的改动测不出来。'
         '这意味着<strong>整个领域的迭代反馈信号是噪声很大的</strong>，'
         '很多"提升"可能不存在'],
        ['<strong>端侧质量</strong>',
         '23 节：能在手机上实时跑的声码器，音质明显低一档。'
         '这个差距这几年没怎么缩小'],
        ['<strong>低资源语种与方言</strong>',
         '缺数据、缺 G2P、缺标注规范。'
         '自监督预训练有帮助，但前端那一段（04–07 节）没有捷径'],
    ]))
    o.append('</section>')

    o.append(sec('s30', '35', '技术趋势', '入门'))
    o.append('<ul>'
             '<li><strong>少步生成</strong>——流匹配 + 蒸馏，把 NFE 压到 1–4。'
             '14 节说过：这是蒸馏的功劳，不是流匹配自带的</li>'
             '<li><strong>更低的 token 率</strong>——'
             '25 Hz 甚至更低，配上更强的解码器补细节。'
             '19 节那个"帧率 vs 时长分辨率"的取舍是这条路的核心矛盾</li>'
             '<li><strong>统一的语音语言模型</strong>——'
             '一个模型同时做 ASR、TTS、对话、翻译。'
             '好处是共享表示，代价是每一项都不是最优</li>'
             '<li><strong>可控性回归</strong>——'
             '用自然语言描述风格（"用轻松一点的语气"）'
             '替代 SSML。这在 LLM-TTS 上是顺手的</li>'
             '<li><strong>全双工对话</strong>——'
             '边听边说、可被打断。'
             '这对延迟的要求比 22 节那张表还紧，'
             '而且需要 TTS 和 ASR 共享同一个流式框架</li>'
             '</ul>')
    o.append(note('一个不太会变的判断',
                  '<p>前端（TN、G2P、韵律）这一段，'
                  '<strong>短期内不会被端到端完全吃掉</strong>。'
                  '原因不是技术，是可控性和可测试性：'
                  '金额读错、日期读错这类问题，'
                  '产品上需要的是一条<em>能单元测试、能定位、能热修</em>的路径，'
                  '而不是"再训一版模型试试"。</p>'
                  '<p>这和 ASR 那边 WFST 一直没消失是同一个道理。</p>'))
    o.append('</section>')

    # ══════════════════════════════════════════════════════════
    o.append(part('附录', '速查', '公式、算例与术语'))
    o.append(appendix())
    o.append(glossary())
    return ''.join(o)


def appendix():
    o = [sec('s31', '36', '公式、算例与自测', '深入')]
    o.append('<h3>全书统一的配置</h3>')
    o.append(table(['量', '#值', '出现在'], [
        ['采样率', '#%d Hz' % ME['cfg']['sr'], '16、18、19、23 节'],
        ['帧长 / 帧移', '#%d / %d（%s / %s ms）'
         % (ME['cfg']['nfft'], ME['cfg']['hop'], r2(ME['cfg']['frame_ms']),
            r3(ME['cfg']['hop_ms'])), '16、17 节'],
        ['帧率', '#%s Hz' % r2(ME['cfg']['fps']), '17、19、22 节'],
        ['梅尔维数', '#%d（%d → %d）' % (ME['cfg']['nmel'], ME['cfg']['nbin'], ME['cfg']['nmel']),
         '16 节'],
        ['语料', '#%d 条中文词条 + %.0f 秒合成语音'
         % (G['dict']['phrases'], RQ['data']['secs']), '05、06、19 节'],
    ]))
    o.append('<h3>算例总表</h3>')
    o.append(table(['节', '这一节算出什么', '#关键数'], [
        ['<strong>02</strong> 一对多', '把不确定性按时长 / 基频 / 其余分解',
         '#时长 %s%%，基频 %s%%，其余 %s%%'
         % (r1(S['explain']['dur']), r1(S['explain']['f0']), r1(S['explain']['rest']))],
        ['<strong>02</strong> 过平滑', 'L2 / L1 / GV 补偿各自的谱对比度',
         '#真实 %s，L2 %s，L1 %s，GV %s'
         % (r3(S['loss']['real_ct']), r3(S['loss']['l2_ct']),
            r3(S['loss']['l1_ct']), r3(S['gvc']['ct']))],
        ['<strong>05</strong> 多音字', '字表 vs 语料加权，三种基线',
         '#%s%% vs %s%%；朴素 %s%%，先验 %s%%'
         % (r1(G['char_level']['poly_pct']), r1(G['token_level']['poly_pct']),
            '%.2f' % G['naive']['char_acc'], '%.2f' % G['prior']['char_acc'])],
        ['<strong>06</strong> 变调', '“一”“不”与三声连读的触发率',
         '#一 %s%%，不 %s%%，三三相连 %s%%'
         % (r1(G['sandhi']['yi_alt_pct']), r1(G['sandhi']['bu_alt_pct']),
            '%.2f' % G['sandhi']['t3t3_pct'])],
        ['<strong>14</strong> 流匹配', '四种采样器达标所需 NFE',
         '#DDPM %s，DDIM %s，FM+Heun %s'
         % (FL['nfe_at_thr']['ddpm'], FL['nfe_at_thr']['ddim'],
            FL['nfe_at_thr']['fm_heun'])],
        ['<strong>16</strong> 梅尔谱', '谐波分辨率、Griffin-Lim 上限、码率',
         '#%d Hz；%s dB；%s kbps'
         % (int(ME['harm']['f0_120']), r2(ME['gl']['100']), r1(ME['budget']['mel_f32_kbps']))],
        ['<strong>17</strong> 对齐', 'MAS 的边界误差，按类型拆开',
         '#总 %s ms；浊→浊 %s ms'
         % (r2(AL['mas']['mae_ms']), r1(list(AL['bykind'].values())[-1][1]))],
        ['<strong>18</strong> 声码器', '混叠比、棋盘调制、相位的 L2',
         '#−%s dB；3.01 dB；+3.01 dB'
         % r1(abs(VO['alias']['cases'][1]['up2']))],
        ['<strong>19</strong> tokenizer', '码率阶梯与码本坍塌',
         '#8 级 %s kbps / %s dB；坍塌到 %d 个码'
         % (r2(RQ['ladder'][7]['kbps']), r2(RQ['ladder'][7]['snr']),
            RQ['collapse']['no_revive']['used'][0])],
        ['<strong>23</strong> 算力', 'HiFi-GAN 的乘加数',
         '#V1 %s MAC/样点，RTF %s'
         % (format(int(EV['variants'][0]['mac']), ','), r2(EV['variants'][0]['rtf8']))],
        ['<strong>26</strong> 听测', '三种设计的功效',
         '#ΔMOS 0.2：组内 %s 人，独立 %s 人'
         % (next(r['paired'].get('20句') for r in EV['mos'] if r['delta'] == 0.2),
            next(r['indep'].get('20句') for r in EV['mos'] if r['delta'] == 0.2))],
    ]))
    o.append('<h3>一个可以随身带的心算</h3>')
    o.append(note('三个数',
                  '<p><strong>一帧 ≈ 12 ms</strong>（22.05 kHz，hop 256）。'
                  '一个音素 80–150 ms，也就是 7–13 帧。'
                  '所以时长预测差 2 帧，就是差 24 ms，人能听出来。</p>'
                  '<p><strong>梅尔谱在 F0×10 以上看不见谐波</strong>。'
                  '男声 120 Hz → 1.2 kHz 以上只剩包络。'
                  '这决定了声码器必须是生成模型。</p>'
                  '<p><strong>NFE × 单步耗时 = 声学模型的延迟</strong>。'
                  '这是首包预算里最大的一块，也是唯一一个可以靠换算法大幅压缩的。</p>'))
    o.append('<h3>回头自测：十二道</h3>')
    o.append('<div class="tldr"><span class="tag">怎么用</span>'
             '<p>20、21、22 三节末尾各有自己的自测题。这里这十二道是<strong>跨节的</strong>，'
             '每一道都对应本书专门纠正过的一个常见误解。'
             '能直接说出答案的，那一节可以跳过；卡住的，题后标着去哪一节。</p></div>')
    QS = [
        ('同一句话读 %d 遍，把时长对齐之后，跨读法的方差还剩多少？' % S['read']['n'], '02 节',
         '<strong>只剩 %s%%。</strong>时长一项就解释了 %s%% 的不确定性，'
         '基频再解释 %s%%。<br>这就是 FastSpeech2 那个 variance adaptor 的全部理由：'
         '把时长和基频从"要靠 L2 猜的东西"变成"先预测、再当条件喂进去的东西"。<br>'
         '容易误读的一点：<strong>基频只占 %s%% 不是因为基频不重要</strong>，'
         '是因为 80 维梅尔谱本来就看不清谐波（16 节）——'
         '基频的信息大部分在声码器那一层。'
         % (r1(S['peel'][1]['var_pct']), r1(S['explain']['dur']),
            r1(S['explain']['f0']), r1(S['explain']['f0']))),
        ('L2 损失训出来的声学模型，谱包络的峰谷对比度会掉多少？换 L1 呢？', '02 节',
         '<strong>L2 掉 %s%%（%s → %s），L1 掉 %s%%。</strong>'
         'L1 好一些是因为条件中位数比条件均值更贴近某个模态，'
         '但<strong>病根没动——中位数同样是一个点，而答案是一个分布</strong>。<br>'
         'GV 补偿把方差乘 %s 拉回去，数字好看了，'
         '放大的却是被平均糊掉的那个形状。'
         % (r1((1 - S['loss']['l2_ct'] / S['loss']['real_ct']) * 100),
            r3(S['loss']['real_ct']), r3(S['loss']['l2_ct']),
            r1((1 - S['loss']['l1_ct'] / S['loss']['real_ct']) * 100),
            r3(S['gvc']['scale']))),
        ('中文字表里两成的字是多音字。真实文本里呢？', '05 节',
         '<strong>%s%% 的字位。</strong>因为常用字更容易有多个读音——'
         '“的、了、行、长、重、还、为、和、着、差”全是。<br>'
         '频率先验（每个字永远读最常见的音）能到 %s%% 的字级正确率，'
         '但<strong>整条词组全对只有 %s%%</strong>。'
         '错误高度集中：%d 个多音字里前 %d 个占一半的错。'
         % (r1(G['token_level']['poly_pct']), '%.2f' % G['prior']['char_acc'],
            r1(G['prior']['phrase_acc']), G['tail']['poly_chars'], G['tail']['k50'])),
        ('“一”和“不”的变调，是边角料还是主线？', '06 节',
         '<strong>“一”有 %s%% 的出现不是本调</strong>，“不”有 %s%%，'
         '相邻两字都是三声的情形占全部相邻字对的 %s%%。<br>'
         '关键是：<strong>这些规则不在任何拼音词典里</strong>。'
         '词典给的是底层调，变调是表层规则，必须在 G2P 之后单独跑一遍。'
         % (r1(G['sandhi']['yi_alt_pct']), r1(G['sandhi']['bu_alt_pct']),
            '%.2f' % G['sandhi']['t3t3_pct'])),
        ('80 维梅尔谱在什么频率以上就看不见谐波了？', '16 节',
         '<strong>男声 120 Hz 时，约 %s Hz 以上。</strong>'
         '判据是梅尔带宽超过基频。到 7 kHz 附近，一个带宽 %s Hz，里面有 %s 根谐波。<br>'
         '所以<strong>神经声码器要干的一大半不是"还原"，是"编造"</strong>——'
         '把梅尔谱里根本不存在的高频谐波和相位造出来。'
         '这也是它必须是生成模型、不能是回归器的原因。'
         % (int(ME['harm']['f0_120']), r0(ME['harm']['width_at_7k']),
            r1(ME['harm']['bins_at_7k']))),
        ('幅度谱完全正确的情况下，Griffin-Lim 迭代一百次能到多少？', '16 节',
         '<strong>%s dB，然后就不动了。</strong>'
         '因为重叠相加之后再做 STFT 不等于原来那一组帧——'
         '“每帧幅度对”和“帧之间拼得上”这两组约束一般不相容。<br>'
         '从梅尔伪逆出发更糟：只有 %s dB。这就是那股金属音的全部来源。'
         % (r2(ME['gl']['100']), r2(ME['melinv']['gl_100']))),
        ('MAS 的边界误差是 %s ms。这个数该怎么读？' % r2(AL['mas']['mae_ms']), '17 节',
         '<strong>不能按平均数读。</strong>按边界类型拆开：'
         '有明显谱突变的地方 %s ms（准到一帧以内），'
         '浊音滑到浊音的地方 %s ms。<br>'
         '后者不是算法的问题——<strong>那里物理上就没有一条线可以标</strong>，'
         '共振峰是连续滑过去的，人工标注同样标不准。'
         % (r1(AL['bykind'].get('有明显谱突变', [0, 0])[1]),
            r1(list(AL['bykind'].values())[-1][1]))),
        ('去掉单调约束的软注意力，具体会出什么事？', '11、17 节',
         '实测：<strong>%s%% 的帧出现"时间倒流"，%d 个音素一帧也没分到</strong>。'
         '前者就是复读，后者就是漏词。<br>'
         '它们不是训练不充分，是<strong>结构上被允许的</strong>——'
         'Tacotron 的注意力没有任何机制禁止它们，'
         'MAS / CTC / RNN-T 在结构上禁止，代价是放弃了"让模型自己决定看哪儿"的自由度。'
         % (r1(AL['soft']['nonmono_pct']), AL['soft']['n_skipped'])),
        ('流匹配比扩散省步数，省在哪儿？', '14 节',
         '<strong>不在一阶。</strong>实测流匹配配欧拉法并没有比 DDIM 省'
         '（FM 需要 &gt;128 NFE，DDIM 需要 %s）。'
         '它省在<strong>路径够直，所以高阶求解器好用</strong>：'
         '换成二阶 Heun，%s 次前向就够。<br>'
         '而且“够直”不等于“直”：OT 路径的弯曲度是 %s，不是 0。'
         '<strong>真正的一步生成靠 reflow 或蒸馏，不是流匹配自带的。</strong>'
         % (FL['nfe_at_thr']['ddim'], FL['nfe_at_thr']['fm_heun'],
            r2(FL['straight']['fm_mean']))),
        ('为什么声码器的损失里不能有波形 L2？', '18 节',
         '把一个正弦的相位挪 90°，<strong>波形 L2 是 +3.01 dB</strong>——'
         '误差的能量比信号还大；而幅度谱距离是 <strong>0</strong>，人耳听不出区别。<br>'
         '波形 L2 惩罚的几乎全是相位，而人耳几乎不听相位。'
         '所以 HiFi-GAN 一类只用多尺度谱损失（管幅度）加判别器（管真实性）。'),
        ('HiFi-GAN V1 在 8 GFLOPS 的手机大核上 RTF 是多少？', '23 节',
         '<strong>%s——根本跑不动。</strong>'
         '按结构数乘加：每个输出样点 %s MAC，其中 <strong>%s%% 在 MRF 上</strong>。<br>'
         '所以端侧必须用 V2/V3（RTF %s / %s），'
         '而 BigVGAN 那套反混叠让算力再翻倍。'
         '<em>砍 MRF 是最划算的裁剪方向。</em>'
         % (r2(EV['variants'][0]['rtf8']),
            format(int(EV['variants'][0]['mac']), ','),
            r1(EV['flops']['frac']['MRF']),
            r2(EV['variants'][1]['rtf8']), r2(EV['variants'][2]['rtf8']))),
        ('要测出 ΔMOS = 0.1，需要多少评分人？', '26 节',
         '<strong>取决于设计，差一个量级。</strong>'
         '“两批人分别听”的设计下，%s；'
         '“同一批人听两套”的设计下，20 句要 %s 人、50 句要 %s 人。<br>'
         '道理是独立设计要摊三份方差（噪声 + 评分人 + 句子），'
         '组内设计把后两份差掉了。'
         '<strong>听测设计比听测人数值钱。</strong><br>'
         '而 ASR 回环测 CER 3%% vs 4%%，只要 %d 句，不用请人。'
         % ('320 人也测不出来',
            next(r['paired'].get('20句') for r in EV['mos'] if r['delta'] == 0.1),
            next(r['paired'].get('50句') for r in EV['mos'] if r['delta'] == 0.1),
            EV['wer'][1]['sents'])),
    ]
    for i, (q, tag, a) in enumerate(QS, 1):
        o.append('<div class="qz"><p class="qq"><span class="qn">%02d</span>%s'
                 '<span class="qs">%s</span></p><details><summary>看答案</summary>'
                 '<div class="qa">%s</div></details></div>' % (i, q, tag, a))
    o.append('</section>')
    return ''.join(o)


def glossary():
    G_ = [
        ('过平滑', 'over-smoothing。用 L2 训一对多映射时，最优解是条件均值，'
               '谱包络被抹平。<strong>TTS 里"发闷"的根源</strong>'),
        ('一对多', 'one-to-many。同一段文本有无数种合法读法。'
               'TTS 和 ASR 最根本的差别'),
        ('梅尔谱', 'mel-spectrogram。把线性频率轴按人耳的临界带宽弯曲后的幅度谱。'
               '<strong>没有相位，高频看不见谐波</strong>'),
        ('声码器', 'vocoder。把声学特征（梅尔谱 / 隐表示）还原成波形。'
               '现代声码器必须是生成模型，因为它要"编造"而不是"还原"'),
        ('MAS', 'Monotonic Alignment Search。在似然矩阵上用动态规划找单调对齐。'
                'Glow-TTS / VITS 用它在训练中自己学对齐'),
        ('时长模型', 'duration model。预测每个建模单元占多少帧。'
                 'FastSpeech 一系的核心，把 %s%% 的不确定性变成可预测的量'
                 % r1(S['explain']['dur'])),
        ('variance adaptor', 'FastSpeech2 里显式预测时长、基频、能量的模块。'
                             '本质是把一对多搬到几个低维可解释的量上'),
        ('GV 补偿', 'global variance compensation。把生成谱的方差强行拉回真实水平。'
                 'HMM-TTS 时代的补丁，<strong>数字好看但放大的是错误的形状</strong>'),
        ('流匹配', 'flow matching。规定一条从噪声到数据的路径（常用直线），'
                '回归路径上的速度场。比扩散少一堆噪声调度的换算'),
        ('NFE', 'number of function evaluations，网络前向次数。'
                '<strong>在 TTS 里它直接就是延迟</strong>'),
        ('reflow', '用已训好的 ODE 把噪声和数据配成对，再在这个配对上重训，'
                   '把路径掰直。一维里能做到一步精确，高维里只能近似'),
        ('RVQ', 'residual vector quantization。逐级量化残差。'
                '把"需要 2^80 条目的单码本"变成"8 个 1024 条目的码本"'),
        ('码本坍塌', 'codebook collapse。大部分码从不被使用。'
                 '<strong>修它只需要几行"把死码搬到误差最大处"</strong>'),
        ('声学 token / 语义 token', '前者能还原波形但和文本对应松，'
                              '后者反之。主流做法是两级：LLM 出语义，另一个模型补声学'),
        ('delay pattern', '让多级码本错开一帧生成，从而一次前向出多级。'
                          'LLM-TTS 压首包延迟的主要手段'),
        ('snake 激活', 'x + sin²(ax)/a。光滑函数，谐波指数衰减，'
                     '<strong>比 leaky ReLU 少几十个 dB 的混叠</strong>'),
        ('棋盘伪影', 'checkerboard artifact。转置卷积核长不能被步长整除时，'
                 '各输出相位叠加的权重个数不等，带来 3.01 dB 的周期性调制'),
        ('MRF', 'multi-receptive field fusion。HiFi-GAN 里并行的多尺度空洞卷积。'
                '<strong>算力的 %s%% 在这里</strong>' % r1(EV['flops']['frac']['MRF'])),
        ('CMOS', 'comparison MOS。直接 A/B 打分（−3…+3）。'
                 '共同难度被差分掉，所以<strong>迭代时该用它而不是绝对 MOS</strong>'),
        ('ASR 回环', '把合成音频过一遍 ASR，用 CER 测可懂度。'
                  '几乎免费，几百句就能测出 1 个百分点'),
        ('音色泄漏', '参考音频里的房间、设备、情绪被一起学进"音色"。'
                 '零样本克隆里最难解决的一件事'),
        ('轻声', '失去原调、变短变轻的音节（“子、头、们、的”）。'
               '05 节那张表里排第一第二的“子”和“儿”，错的就是这个'),
        ('变调', 'tone sandhi。三声连读、“一”“不”的调变。'
               '<strong>表层规则，不在拼音词典里</strong>'),
        ('韵律短语', 'PPH，#2。中文韵律四层里最常标的一层。'
                 '停顿位置能改变句子意思'),
        ('TN', 'text normalization。“2025 年”→“二零二五年”。'
               '和多音字并列，是仅有的两类<strong>内容错误</strong>'),
    ]
    o = [sec('s32', '37', '术语表', '')]
    o.append('<dl class="gloss">')
    for t, d in G_:
        o.append('<div class="gitem"><dt>%s</dt><dd>%s</dd></div>' % (t, d))
    o.append('</dl></section>')
    return ''.join(o)
