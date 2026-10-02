#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新写的两块正文：总纲（放在最前面）与 Part C「参考」——回声消除与全双工。

所有数字都从 demo_aec_*.json 里取，不手抄。节号用 C1…C8，与阵列(A)、单通道(B)两部分各自独立。
"""
from bookfe_util import (K, KI, F, AD, DT, DR, RS, D2, DL, MU2, DX, CH, JT, fml, fig, sec, part,
                         table, ex, note, trap, step, why, q, ki)

r0 = lambda x: '%.0f' % x
r1 = lambda x: '%.1f' % x
r2 = lambda x: '%.2f' % x
r3 = lambda x: '%.3f' % x
neg = lambda s: ('−' + s[1:]) if s.startswith('-') else s
db = lambda x: neg('%.2f' % x)

MU = AD['mu']
SPEC = {r['kind']: r for r in AD['spec']}
WH = {r['kind']: r for r in AD['white']}
LEN = AD['length']
PART = AD['part']
DM = {r['mode']: r for r in DT['modes']}
DSW = DT['sweep']
IM = DT['inject']['miss']
IF = DT['inject']['fa']
PPM = DR['ppm']
LD = DR['len_drift']
DLY = DR['delay']
CHG = DR['change']
NL = RS['nl']
RES = RS['res']
SPL = RS['split']
S2 = {r['key']: r for r in D2['static']}
C2R = {r['key']: r for r in D2['change']}
DXK = {r['kind']: r for r in DX['kinds']}
CHR = {r['key']: r for r in CH['rows']}


TOC_C = [('f1', 'C1', '回声是辨识问题'), ('f2', 'C2', 'NLMS：快与准的积'),
         ('f3', 'C3', '分区块：延迟与长度解耦'), ('f4', 'C4', '双讲检测'),
         ('f5', 'C5', '不靠检测器：双路径与卡尔曼'), ('f6', 'C6', '追不上的那一部分'),
         ('f7', 'C7', '非线性与残余抑制'), ('f8', 'C8', '多参考通道'),
         ('f9', 'C9', '全双工与打断'), ('f10', 'C10', '三段合起来：预算与翻车点'),
         ('f12', 'C11', '理论补篇：没做实验的四块'), ('f11', 'C12', '复现与术语')]


# ══════════════════════════════════════════════════════════════
def build_intro():
    """放在全书最前面：这三部分为什么在一本里。"""
    o = ['<section id="g0"><h2>这本手册怎么读</h2>']
    o.append('<p>一个语音前端手里只有<strong>三种信息</strong>可用：多个麦克风给的<strong>空间</strong>，'
             '一路信号里残存的<strong>统计</strong>规律，以及自己正在播放的那一路<strong>参考</strong>。'
             '这三种信息各有各的上限、各有各的失效方式，<strong>而且互相不能替代</strong>。'
             '这本手册把三部分合在一起，是因为它们在工程里是同一条链路上的三段；'
             '链路的出口还有两道门——<strong>唤醒</strong>决定要不要开口，<strong>声纹</strong>决定是谁在说——放在 D 部分。</p>')
    o.append(fig('three', '<strong>三种信息，三个上限。</strong>'
                 '空间由阵元数和孔径定，统计由假设成立的程度定，参考由截断、非线性和底噪三条天花板里最低的那条定。'))
    o.append(fml('三种信息分别对应观测里的哪一项', 'three'))
    o.append(fml('各自的上限由什么定', 'limits'))
    o.append(table(['你要解决的问题', '先读哪里', '为什么'], [
        ['几个麦够不够、能拾多远', '<strong>A 部分</strong>（阵列）的 02–04', '物理上限比任何算法都先锁死结果'],
        ['只有一个麦，怎么降噪', '<strong>B 部分</strong>（单通道）的 01、04–10',
         '空间自由度为零，只剩统计假设'],
        ['降噪之后识别或声纹反而变差', 'B 部分的 18–19', '指标排序和下游任务的排序不是一回事'],
        ['带喇叭的设备，对方听到自己的回声', '<strong>C 部分</strong>（参考）的 C1–C3', '这是辨识问题，理论上能消干净'],
        ['立体声 / 多喇叭设备，ERLE 好看却一换人就崩', 'C 部分的 C8', '参考通道相关时，解不唯一'],
        ['做语音助手：播放时怎么听见用户打断', 'C 部分的 C9，再读 D 部分', '打断的灵敏度由回声底和瞬态一起定'],
        ['阵列设备上 AEC 该放哪', '<strong>A 部分</strong>的 A14，再读 C10', '波束权重一动，AEC 的上限就掉'],
        ['做唤醒词或声纹验证', '<strong>D 部分</strong>（唤醒与声纹）的 D01–D04', 'EER、DCF 与校准是两者共用的骨架'],
        ['前端增强之后唤醒或声纹反而变差', 'D17，再读 B18–B19', '增强对不同下游的影响方向相反'],
        ['回声消除"看起来不错"但一说话就坏', 'C 部分的 C4、C5、C7', '双讲检测与残余抑制都在伤近端'],
        ['换了设备或接了蓝牙就消不掉', 'C 部分的 C6', '延迟是悬崖，不是斜坡，高估比低估致命'],
    ], minw=560))
    o.append(note('编号约定',
                  '各部分的节号各自从头数：<b>A01</b> 是阵列手册的第 1 节，<b>B01</b> 是单通道手册的第 1 节，'
                  '<b>C1</b> 是回声消除的第 1 节，<b>D01</b> 是唤醒与声纹的第 1 节。正文里"第 N 节"指的都是它所在部分的第 N 节。'
                  'A、B、D 三部分是原样并入的；回声消除与全双工是这一本新写的，实验与图在 <code>aec/</code> 目录。'))
    o.append('</section>')
    return ''.join(o)


# ══════════════════════════════════════════════════════════════
def build_echo():
    o = []
    o.append(part('Part C', '参考：回声消除与全双工',
                  '知道自己播了什么，所以理论上能消干净；真正的上限在别处'))

    # ── C1 ────────────────────────────────────────────────────
    big = [r for r in LEN if r['bind'] == '近端底噪'][0]
    o.append(sec('f1', 'C1', '回声是辨识问题，不是估计问题', '入门',
                 tldr='回声的来源 x(t) 是你自己播的、完全已知，所以这是辨识一条未知路径，不是从噪声里估计信号。'
                      '理论上能消到很深，实际被三条天花板里最低的那条卡住：'
                      '<strong>滤波器没盖住的路径尾巴、喇叭的非线性、近端底噪</strong>。'))
    o.append('<p>前两部分的敌人是"不知道的东西"：空间里不知道干扰在哪，统计上不知道噪声是多少。'
             '回声不一样。喇叭播的就是 x(t)，你手里有它的每一个采样点，只缺从喇叭到麦克风那条路径 g。'
             '所以问题是<strong>辨识</strong>，而不是估计。</p>')
    o.append(fml('观测模型与残差', 'echomodel'))
    o.append('<p>衡量消得多干净用 ERLE。它的上界由三项误差决定，三项之和取负对数：</p>')
    o.append(fml('ERLE 与它的三条天花板', 'erle'))
    o.append(step('先看第一条天花板：滤波器多长'))
    o.append(ex('实测：滤波器长度 vs ERLE 上限（房间 T60 = %s s，近端底噪 %s dB）'
                % (AD['const']['t60'], r0(AD['const']['near_snr'])),
                table(['#长度', '#尾巴上限', '#底噪上限', '谁在卡', '#实测 ERLE'],
                      [['#%s ms' % r0(r['l_ms']), '#%s dB' % r2(r['ceiling']),
                        '#%s dB' % r2(r['cap_noise']), r['bind'],
                        '#%s dB' % r2(r['erle'])] for r in LEN], cls='dp')
                + '<p>滤波器从 64 ms 加到 128 ms，ERLE 涨 <strong>%s dB</strong>；从 256 ms 加到 512 ms，只涨 '
                  '<strong>%s dB</strong>。同一个旋钮，前一段值钱，后一段一文不值——因为到了 256 ms，'
                  '卡住你的已经换成了近端底噪。<strong>先找出此刻是哪条天花板最低，再决定动哪个旋钮。</strong></p>'
                % (r2(AD['length_note']['d64_128']), neg(r2(AD['length_note']['d256_512'])))))
    o.append(why('这张表是整个 C 部分的总开关。下面每一节都是在讲另一条天花板或者另一种"追不上"。'))
    o.append('</section>')

    # ── C2 ────────────────────────────────────────────────────
    mu0, mu4 = MU[0], MU[-1]
    o.append(sec('f2', 'C2', 'NLMS：快与准的积是守恒的', '进阶',
                 tldr='步长 μ 变 %s 倍，收敛时间和稳态失调的积只在 %s 倍以内浮动：快和准是同一枚硬币。'
                      '而 <strong>ERLE 几乎看不出这件事</strong>，所以只盯 ERLE 调参会调出一个"看着没事"的坏滤波器。'
                      % (r0(mu4['mu'] / mu0['mu']), r1(AD['mu_tradeoff']['prod_spread']))))
    o.append('<p>最朴素的辨识办法是 NLMS：每来一个采样，按误差的方向把滤波器抽头挪一小步。'
             '步长 μ 是唯一的主旋钮。</p>')
    o.append(fml('NLMS 更新与失调', 'nlms'))
    o.append(fml('快与准：积是常数', 'tradeoff'))
    o.append(fig('adapt', '<strong>三个小图一个结论。</strong>① μ 越大收敛越快、稳态越差；'
                 '② 同一组里 ERLE 几乎不动；③ 输入白化值多少，取决于远端信号的谱。'))
    o.append(ex('实测：μ 扫描（白噪远端，%d 抽头）' % AD['const']['taps'],
                table(['#μ', '#收敛到 −20 dB 的时间（s）', '#稳态失调（dB）', '#ERLE（dB）', '#两者之积'],
                      [['#%s' % r['mu'], '#%s' % r2(r['t20']), '#%s' % neg(r2(r['misalign'])),
                        '#%s' % r2(r['erle']), '#%s' % r3(r['product'])] for r in MU], cls='dp')
                + '<p>μ 从 %s 到 %s（%s 倍），收敛快了 <strong>%s 倍</strong>，稳态失调差了 <strong>%s dB</strong>，'
                  '而 ERLE 只差 %s dB。<strong>ERLE 看不见失调。</strong>'
                  '失调大意味着滤波器抽头是歪的，换一个远端信号或者路径一变，它就会暴露出来。</p>'
                % (mu0['mu'], mu4['mu'], r0(mu4['mu'] / mu0['mu']), r1(mu0['t20'] / mu4['t20']),
                   r2(mu0['misalign'] - mu4['misalign']), r2(mu0['erle'] - mu4['erle']))))
    o.append(step('远端不是白噪：特征值扩散'))
    o.append('<p>语音是强有色信号。NLMS 的步长由最强的频点定，最弱的频点就慢 χ 倍。</p>')
    o.append(fml('特征值扩散与收敛时间', 'spread'))
    o.append(ex('实测：同一个滤波器喂三种远端',
                table(['远端', '#特征值扩散 χ', '#逐频点归一化（白化）后的失调', '#不白化的失调', '#白化的收益（dB）'],
                      [[k, '#%s' % r1(SPEC[k]['spread']),
                        '#%s' % neg(r2(WH[k]['on'])), '#%s' % neg(r2(WH[k]['off'])),
                        '#%s' % r2(WH[k]['gain'])]
                       for k in ('白噪', '粉噪', '语音')], cls='dp')
                + '<p>白噪下白化没有收益（甚至差 %s dB，因为多了估计噪声）；'
                  '粉噪下收益 <strong>%s dB</strong>；语音下收益 <strong>%s dB</strong>。'
                  '所以<strong>"要不要做频域归一化"不是通用答案，要看你的远端是什么谱</strong>。'
                  '通话场景里远端几乎都是语音，这一步基本是必选。</p>'
                % (r2(-WH['白噪']['gain']), r2(WH['粉噪']['gain']), r2(WH['语音']['gain']))))
    o.append('</section>')

    # ── C3 ────────────────────────────────────────────────────
    p0, p1 = PART[0], PART[-1]
    o.append(sec('f3', 'C3', '分区块：延迟与滤波器长度解耦', '进阶',
                 tldr='把长滤波器切成 P 个短块，延迟只看块长 B，覆盖范围看 P·B。'
                      '块长减半，延迟减半，算力约翻倍——这是唯一一个明码标价的取舍。'))
    o.append('<p>C1 说滤波器要装下房间的尾巴，所以得很长；而时域长滤波器要等攒够一整块才能算，'
             '延迟就是整块的长度。分区块频域（PBFDAF）把这两件事拆开。</p>')
    o.append(fml('分区块：延迟、覆盖、算力', 'partition'))
    o.append(ex('实测：覆盖固定 %s ms，只改块长' % AD['const']['l_ms'],
                table(['#块长 B', '#分区数 P', '#处理延迟（ms）', '#稳态失调（dB）', '#ERLE（dB）',
                       '#每秒 FFT 次数', '#算力（MMAC/s）'],
                      [['#%d' % r['b'], '#%d' % r['nparts'], '#%s' % r1(r['delay_ms']),
                        '#%s' % neg(r2(r['misalign'])), '#%s' % r2(r['erle']),
                        '#%s' % r0(r['ffts_per_s']), '#%s' % r2(r['mmac_s'])] for r in PART], cls='dp')
                + '<p>块长从 %d 缩到 %d，延迟降 <strong>%s 倍</strong>（%s ms → %s ms），'
                  '算力涨 <strong>%s 倍</strong>，失调还好了 %s dB——小块更新更勤。'
                  '所以在延迟预算里，块长是应该先砍的那一项。</p>'
                % (PART[-1]['b'], PART[0]['b'], r0(AD['part_note']['delay_ratio']),
                   r0(PART[-1]['delay_ms']), r0(PART[0]['delay_ms']),
                   r1(AD['part_note']['mac_ratio']), r2(AD['part_note']['mis_gain']))))
    o.append('</section>')

    # ── C4 ────────────────────────────────────────────────────
    m = DM['在线 DTD（κ=4）']
    nf = DM['从不冻结']
    om = DM['全知 DTD']
    o.append(sec('f4', 'C4', '双讲检测：漏检是阈值型的，误检是渐进型的', '进阶',
                 tldr='近端一开口，滤波器的误差就会把近端语音当成"回声没消干净"去追，然后发散。'
                      '双讲检测（DTD）负责在那时把更新冻住。两种错误的代价<strong>完全不是一个形状</strong>：'
                      '漏检短于 %s s 几乎免费，长了就发散；误检只是更新机会变少，线性地吃亏。'
                      % r1(DT['miss_knee']['free_up_to'])))
    o.append(fml('判据：能量比', 'dtd'))
    o.append(fig('dtd', '<strong>三个小图。</strong>① 阈值扫描：两种错误率此消彼长；'
                 '② 两种错误的代价形状；③ 冻结与不冻结的差距。'))
    o.append(step('先看这件事值不值得做'))
    o.append(ex('实测：近端占 25% 的时间，三种策略',
                table(['策略', '#漏检（%）', '#误检（%）', '#单讲段 ERLE（dB）', '#失调（dB）'],
                      [[k, '#%s' % r1(DM[k]['miss']), '#%s' % r1(DM[k]['fa']),
                        '#%s' % r2(DM[k]['erle']), '#%s' % neg(r2(DM[k]['misalign']))]
                       for k in ('从不冻结', '在线 DTD（κ=4）', '全知 DTD')], cls='dp')
                + '<p>不冻结比"全知"差 <strong>%s dB</strong>。在线 DTD 能追回一部分（%s → %s），'
                  '但离全知还有 <strong>%s dB</strong>：这是一个检测器能做到的和它被允许做错的之间的距离。</p>'
                % (r2(DT['no_dtd_cost']), r2(nf['erle']), r2(m['erle']), r2(om['erle'] - m['erle']))))
    o.append(step('两种错误，两种形状'))
    o.append(fml('漏检是阈值型，误检是渐进型', 'dtdcost'))
    o.append(ex('实测：人为注入错误',
                '<p><strong>漏检</strong>（近端在说，但没冻住）：</p>'
                + table(['#漏检持续（s）', '#失调跳升（dB）', '#还清要花（s）'],
                        [['#%s' % r['dur'], '#%s' % neg(r2(r['jump'])), '#%s' % r2(r['recover'])]
                         for r in IM], cls='dp')
                + '<p><strong>误检</strong>（只有远端在说，却冻住了一部分）：</p>'
                + table(['#被冻住的比例', '#失调（dB）', '#ERLE（dB）'],
                        [['#%s%%' % r0(r['frac'] * 100), '#%s' % neg(r2(r['misalign'])),
                          '#%s' % r2(r['erle'])] for r in IF], cls='dp')
                + '<p>漏检 %s s 以内完全没事（失调变化 %s dB），到 0.4 s 就跳升 %s dB、还要 %s s 才恢复，'
                  '是漏检时长的 <strong>%s 倍</strong>。误检则是一条斜线：冻住一半，ERLE 少 %s dB。</p>'
                % (r1(DT['miss_knee']['free_up_to']), r2(DT['miss_knee']['free_jump']),
                   r2(DT['asym']['miss_jump']), r2(DT['asym']['miss_recover']),
                   r0(DT['asym']['ratio']), r2(DT['asym']['fa_cost']))))
    best, eer = DT['best'], DT['eer_point']
    o.append(trap('我原以为：把两种错误率调到相等最公平',
                  '检测里的惯例是找"等错误率点"（EER）。在这里它是错的。'
                  '最优阈值在 κ = %g：漏检 %s%%、误检 %s%%，<strong>差 %s 倍</strong>——'
                  '因为漏检的代价是悬崖，误检的代价是斜坡。'
                  '按 EER 去定（κ = %g），单讲段 ERLE 要低 <strong>%s dB</strong>。'
                  '<strong>但这个"最优"要打折：</strong>它的误检高达 %s%%，单讲段里大部分块也被冻住，'
                  '滤波器几乎不再学习。C5 加了一条"收敛后不再学"的对照，在另一组种子上它反而比能量比 DTD 高 %s dB。'
                  '所以这里能下的结论只是"两种错误的代价形状不同"，<strong>不是"该冻多少"</strong>。'
                  % (best['kappa'], r1(best['miss']), r1(best['fa']), r0(best['fa'] / best['miss']),
                     eer['kappa'], r2(DT['eer_cost']), r1(best['fa']), r2(D2['note']['frozen_vs_energy']))))
    hn = DT['hang_note']
    o.append(note('拖尾（hangover）值多少',
                  '检测到近端后再多冻几块。阈值定得紧时它有用：κ = %g、拖尾 %d 块，漏检从 %s%% 降到 %s%%，'
                  'ERLE 好 %s dB。<strong>但阈值本来就合适时拖尾是净损失</strong>——它是补救"阈值没调好"的，不是通用加分项。'
                  % (hn['loose_kappa'], hn['best_hang'], r1(hn['miss0']), r1(hn['missb']), r2(hn['gain']))))
    o.append('</section>')

    # ── C5（新）──────────────────────────────────────────────
    N2 = D2['note']
    o.append(sec('f5', 'C5', '不靠检测器：双路径与频域卡尔曼', '进阶',
                 tldr='C4 的"最优阈值"其实只是"几乎不再学"。真要在双讲时保住滤波器，'
                      '有两类办法不依赖一个会出错的检测器：<strong>双路径</strong>（后台乱学、前台只在后台明显更好时才换）'
                      '和<strong>频域卡尔曼</strong>（每个频点的步长自己算）。'
                      '在这套实验里卡尔曼比不冻结高 %s dB、比能量比 DTD 高 %s dB，但离全知仍差 %s dB。'
                      % (r1(N2['fdkf_vs_none']), r1(N2['fdkf_vs_energy']), r1(N2['fdkf_gap_to_oracle']))))
    o.append('<p>C4 的结论里有一处我后来觉得不对劲：最优阈值对应的<strong>误检高达 %s%%</strong>——'
             '单讲段里大多数块也被冻住了。一个检测器被迫把大多数时间都判成"别学"才算最优，'
             '说明它本身分辨不了单讲和双讲。要验证这一点只需加一条对照：<strong>收敛期一过就再也不学</strong>。</p>'
             % r1(DT['best']['fa']))
    o.append(step('一条对照：收敛期之后不再学'))
    o.append(fig('dtd2', '<strong>四个小图。</strong>① 路径不变；② 第 12 s 路径整条换掉；③ 近端电平变化；'
                 '④ 三类做法：要检测器的、不要检测器的、上界。'))
    o.append(ex('实测① 路径不变（近端电平 = 回声，近端占 25%% 时间；%s 个种子）' % len(D2['const']['seeds']),
                table(['做法', '#单讲段 ERLE', '#双讲段近端保真', '#失调', '#漏检', '#误检'],
                      [[r['name'], '#%s dB' % r2(r['erle']), '#%s dB' % r2(r['near']), '#%s dB' % neg(r2(r['mis'])),
                        '#%s' % (('%s%%' % r1(r['miss'])) if 'miss' in r else '—'),
                        '#%s' % (('%s%%' % r1(r['fa'])) if 'fa' in r else '—')] for r in D2['static']], cls='dp')
                + '<p>"收敛后不再学"的 ERLE 是 <strong>%s dB</strong>，比能量比 DTD 的 %s dB <strong>高 %s dB</strong>。'
                  '换句话说 C4 里那个"最优点"没有带来任何超出"不学"的东西。'
                  '它还把失调拖到 %s dB——比"不冻结"的 %s dB 更差——因为冻的时候恰好不该冻。</p>'
                % (r2(N2['frozen_static']), r2(N2['energy_static']), r2(N2['frozen_vs_energy']),
                   neg(r2(S2['energy']['mis'])), neg(r2(S2['none']['mis'])))))
    o.append(step('代价：路径一换，被冻住的滤波器回不来'))
    o.append(ex('实测② 第 %s s 路径整条换掉（统计从换路径后 4 s 开始）' % r0(D2['const']['change_s']),
                table(['做法', '#单讲段 ERLE', '#双讲段近端保真', '#失调'],
                      [[r['name'], '#%s dB' % neg(r2(r['erle'])), '#%s dB' % neg(r2(r['near'])),
                        '#%s dB' % neg(r2(r['mis']))] for r in D2['change']], cls='dp')
                + '<p>"不再学"掉到 <strong>%s dB</strong>，能量比 DTD 只剩 <strong>%s dB</strong>，'
                  '失调回到 0 dB 附近——滤波器根本没动过。无检测器的两种做法仍有 %s dB 和 %s dB。'
                  '这就是 C4 里"误检只是渐进型代价"那句话的盲区：<strong>渐进型是针对路径不变而言的</strong>。</p>'
                % (neg(r2(N2['frozen_change'])), neg(r2(N2['energy_change'])),
                   r1(N2['fdkf_change']), r1(N2['twopath_change']))))
    o.append(step('两种不用检测器的办法'))
    o.append(fml('双路径：后台乱学，前台只在后台明显更好时才换', 'twopath'))
    o.append('<p>双路径装两个滤波器。后台那个<strong>一直</strong>在学，不管近端在不在说；'
             '前台那个只负责输出，只有当后台的误差明显比前台小（本实验里 ρ = %s）时，才把后台的权重拷过去。'
             '双讲时后台被近端语音带偏，但它不比前台好，所以不会被采用；路径一变，后台先收敛、先变好，就被拷过去。'
             '代价是多一份滤波器的算力，以及拷贝时机总要慢半拍。</p>' % D2['const']['twopath']['thr'])
    o.append(fml('频域卡尔曼：步长由观测噪声自己定', 'kalman'))
    o.append('<p>卡尔曼把"滤波器抽头随时间随机游走"当成状态模型，每个分区、每个频点维护一个协方差 P。'
             '增益 K 的分母里有观测噪声功率 Ψ，而 Ψ 是用<strong>后验误差的功率</strong>递推出来的：'
             '近端一开口，误差变大，Ψ 变大，K 自动变小，滤波器就慢下来——'
             '这正是 DTD 想做的事，只是它不做二值判决。这里用的是对角协方差的近似，'
             '常数 a=%s、λ=%s 在种子 0、1 上做过一次 3×3 的网格，本节的数字用的是另外三个种子（%s）。'
             % (D2['const']['fdkf']['a'], D2['const']['fdkf']['lam'],
                '、'.join(str(x) for x in D2['const']['seeds'])) + '</p>')
    o.append(step('近端有多响，谁更扛得住'))
    nrows = []
    for blk in D2['ner']:
        R_ = {r['key']: r for r in blk['rows']}
        nrows.append(['近端 %s dB' % neg('%+.0f' % blk['ner'])] +
                     ['#%s' % r2(R_[k]['erle']) for k in ('none', 'frozen', 'energy', 'twopath', 'fdkf', 'oracle')])
    o.append(ex('实测③ 近端相对回声的电平（单讲段 ERLE，dB）',
                table(['', '#不冻结', '#不再学', '#能量比', '#双路径', '#卡尔曼', '#全知'], nrows, cls='dp')
                + '<p>不冻结的做法对近端电平极其敏感：近端轻 10 dB 时 %s dB，响 10 dB 时 %s dB。'
                  '卡尔曼随近端变响而下降（%s → %s dB），双路径几乎不受影响（%s → %s dB）。'
                  '所以<strong>没有一个办法在所有近端电平下都最好</strong>：近端很响时，双路径比卡尔曼更稳。</p>'
                % (r1([r for r in D2['ner'][0]['rows'] if r['key'] == 'none'][0]['erle']),
                   neg(r1([r for r in D2['ner'][2]['rows'] if r['key'] == 'none'][0]['erle'])),
                   r1([r for r in D2['ner'][0]['rows'] if r['key'] == 'fdkf'][0]['erle']),
                   r1([r for r in D2['ner'][2]['rows'] if r['key'] == 'fdkf'][0]['erle']),
                   r1([r for r in D2['ner'][0]['rows'] if r['key'] == 'twopath'][0]['erle']),
                   r1([r for r in D2['ner'][2]['rows'] if r['key'] == 'twopath'][0]['erle']))))
    o.append(trap('我又猜错了一处：相干性 DTD 并不比能量比好',
                  '教科书上相干性检测（滤波器输出与麦克风信号的逐频点相干系数）通常比能量比更稳。'
                  '在这套实验里它的单讲段 ERLE 只有 %s dB，低于能量比的 %s dB，漏检 %s%%、误检 %s%%。'
                  '原因我的判断（没有单独验证）是：T60 = 0.25 s 的回声路径比一个 16 ms 的块长得多，'
                  '相干性依赖的"滤波器输出和麦克风信号线性相关"在滤波器还没收敛好时本身就不成立——'
                  '检测器想要一个收敛好的滤波器，而滤波器要靠检测器才能收敛好。'
                  '这是在<strong>这套参数</strong>下的结果，没有对相干性检测做过逐项调参。'
                  % (r2(S2['coh']['erle']), r2(S2['energy']['erle']), r1(S2['coh']['miss']), r1(S2['coh']['fa']))))
    o.append(note('没解决的部分',
                  '无检测器的最好做法（卡尔曼）距全知 DTD 仍差 %s dB。这 %s dB 是"知道哪几块是双讲"这条信息的价值，'
                  '目前没有一种在线办法拿得到。神经网络做的双讲判决或端到端回声消除可以逼近它，本书没有训这一类模型。'
                  % (r1(N2['fdkf_gap_to_oracle']), r1(N2['fdkf_gap_to_oracle']))))
    o.append('</section>')

    # ── C5 ────────────────────────────────────────────────────
    pn = DR['ppm_note']
    ln = DR['len_drift_note']
    dn = DR['delay_note']
    o.append(sec('f6', 'C6', '追不上的那一部分：漂移、延迟与路径变化', '进阶',
                 tldr='有三件事是自适应滤波"追不上"的：采样时钟漂移、整块延迟超出滤波器范围、路径突变。'
                      '前两件是<strong>结构性</strong>的——不是调参能解决的。'
                      '尤其是延迟：差一点就从 %s dB 掉到 %s dB，是悬崖。'
                      % (r1(dn['clean']), r1(dn['last']))))
    o.append(step('时钟漂移'))
    o.append('<p>扬声器和麦克风不在同一个时钟域时（蓝牙、USB 声卡、多设备），'
             '参考和回声之间的相对位置会慢慢错开，每个抽头错开的量和抽头位置无关，'
             '但尾部抽头的相关时间最短，先被解相关。</p>')
    o.append(fml('漂移', 'drift'))
    o.append(fig('drift', '<strong>四个小图。</strong>① 时钟差几个 ppm；② 同样的漂移，滤波器越长越亏；'
                 '③ 整块延迟吃掉滤波器的覆盖范围；④ 路径中途变了。'))
    o.append(ex('实测：时钟差 vs ERLE（%s ms 滤波器，%s s）' % (DR['const']['l_ms'], r0(DR['const']['dur'])),
                table(['#时钟差（ppm）', '#累计错开（采样点）', '#ERLE（dB）'],
                      [['#%d' % r['ppm'], '#%s' % r2(r['slip_samp']), '#%s' % r2(r['erle'])] for r in PPM],
                      cls='dp')
                + '<p>仅 <strong>%d ppm</strong>——一个普通晶振的零头——就掉了 6 dB；100 ppm 掉 %s dB。</p>'
                % (pn['ppm_6db'], r1(pn['drop_100']))))
    o.append(trap('我原以为：滤波器加长总能把漂移覆盖进去',
                  '正相反。50 ppm 下 %d ms 的滤波器几乎不受影响（%s dB），'
                  '<strong>%d ms 的要赔 %s dB</strong>。'
                  '道理是尾部抽头的相关时间最短，漂移先把它们解相关；滤波器越长，尾部这批"先死"的抽头越多。'
                  '所以长滤波器要配漂移补偿（重采样或时钟同步），而不是靠它自己扛。'
                  % (ln['short_ms'], r2(ln['short']), ln['long_ms'], r2(ln['long']))))
    o.append(step('整块延迟：悬崖'))
    o.append(fml('滤波器要装下什么', 'budget'))
    o.append(ex('实测：回声路径整体后移（滤波器 %s ms）' % r0(dn['l_ms']),
                table(['#额外延迟（ms）', '#滤波器还剩的尾巴（ms）', '#ERLE（dB）'],
                      [['#%s' % r0(r['off_ms']), '#%s' % r0(r['head_left_ms']), '#%s' % r2(r['erle'])]
                       for r in DLY], cls='dp')
                + '<p>延迟吃掉了滤波器的覆盖范围。<strong>剩余尾巴一旦不够装下房间，ERLE 一路掉到 0 附近</strong>，'
                  '最后一行 %s dB 说明滤波器已经完全对不上路径。换设备、接蓝牙、加一级缓冲，'
                  '都是在悄悄推这个数。</p>' % neg(r2(dn['last']))))
    o.append(step('延迟是怎么估出来的，估偏了往哪边偏'))
    DN = DL['note']
    o.append('<p>上面把延迟当成已知。真实系统里要自己估：用远端参考和麦克风信号做广义互相关（GCC-PHAT），'
             '峰的位置就是参考到回声的延迟。估完以后把参考多延迟这么多再喂给滤波器。</p>')
    o.append(fml('GCC-PHAT 与"往低的一侧偏"', 'gcc'))
    o.append(fig('delay', '<strong>两个小图。</strong>① 窗长与估对的比例，红线和橙线是最差的两种条件；'
                 '② 估偏之后的 ERLE，实线不留余量，虚线留 8 ms 余量。'))
    wi = {w: i for i, w in enumerate(DL['const']['wins'])}
    o.append(ex('实测：GCC-PHAT 估对（误差 ≤ 2 ms）的比例，真值 %s ms（%s 次试验）' % (r0(DL['const']['pre_ms']), DL['const']['trials']),
                table(['条件'] + ['#%s s' % ('%g' % w) for w in DL['const']['wins']] + ['#最早峰 · 1 s'],
                      [[r['cond']] + ['#%s%%' % r0(c['ok']) for c in r['wins']] + ['#%s%%' % r0(r['wins'][wi[1.0]]['ok_early'])]
                       for r in DL['acc']], cls='dp')
                + '<p>窗长是第一决定因素：0.25 s 只有 %s%% 估对，1 s 起才靠得住，2 s 起基本都对。'
                  '近端插话、混响、喇叭非线性在 1 s 窗下都没把它拖垮；最差的两种是<strong>回声比底噪还低 10 dB</strong> 和'
                  '<strong>直达声很弱</strong>（最强的峰是反射，不是直达声，估出来比真值大，也就是高估）。'
                  '我曾想用"取第一个高过最大峰 40%% 的峰"去对付后者，结果在多数条件下更差'
                  '（回声/底噪 −10 dB 时 1 s 窗只有 %s%%，而全局最大峰是 %s%%）——前面的小峰多半是噪声。</p>'
                % (r0(DN['ok_short']),
                   r0([r for r in DL['acc'] if r['cond'].startswith('回声/底噪')][0]['wins'][wi[1.0]]['ok_early']),
                   r0([r for r in DL['acc'] if r['cond'].startswith('回声/底噪')][0]['wins'][wi[1.0]]['ok']))))
    erows = []
    for ci in range(len(DL['err'][0]['cells'])):
        c0, c1 = DL['err'][0]['cells'][ci], DL['err'][1]['cells'][ci]
        erows.append(['#%s ms' % neg('%+d' % c0['err_ms']) if c0['err_ms'] else '#0', '#%s dB' % neg(r2(c0['erle'])),
                      '#%s dB' % neg(r2(c1['erle']))])
    o.append(ex('实测：估偏之后的 ERLE（滤波器 %s ms，估计 − 真值）' % r0(DL['const']['l_ms']),
                table(['#估计 − 真值', '#余量 0', '#余量 8 ms'], erows, cls='dp')
                + '<p>两边完全不对称：估低 %s ms 还有 %s dB，估高 %s ms 就只剩 %s dB。'
                  '道理在滤波器的结构里：滤波器只覆盖从参考出发的 [0, L)，<strong>估高了，直达声和早期反射落在 0 之前，滤波器结构上表示不了</strong>；'
                  '估低了，只是把滤波器的前端空出来一段、尾巴被截短一点。'
                  '所以工程上要<strong>故意往低估的一侧偏一点</strong>：留 8 ms 余量时，估高 8 ms 仍有 %s dB，'
                  '代价是估准时少 %s dB。</p>'
                % (r0(abs(-48)), r2(DN['under48']), r0(8), neg(r2(DN['over8'])),
                   r2(DN['m8_over8']), r2(DN['erle_exact'] - DN['m8_exact']))))
    o.append(why('这也解释了 C6 前面那张延迟表为什么是悬崖：那是"估低太多、滤波器装不下尾巴"的一侧；'
                 '而这里量的是反方向——估高——它在更小的偏差（4–8 ms）上就垮了。'))
    o.append(step('路径中途变了'))
    o.append(ex('实测：路径变了多少，掉多深，多久回来',
                table(['变化', '#ERLE 掉了（dB）', '#恢复要花（s）'],
                      [[r['name'], '#%s' % r2(r['dip']), '#%s' % r2(r['recover'])] for r in CHG], cls='dp')
                + '<p>即使"挪一下手"这种轻微变化也掉 %s dB；完全换一条路径（挡住喇叭）掉 %s dB，要 %s s 才回来。'
                  '这段时间里对方听到的就是回声。</p>'
                % (r1(CHG[0]['dip']), r1(CHG[-1]['dip']), r2(CHG[-1]['recover']))))
    o.append('</section>')

    # ── C6 ────────────────────────────────────────────────────
    rn = RS['res_note']
    nn = RS['nl_note']
    sn = RS['split_note']
    o.append(sec('f7', 'C7', '非线性与残余抑制：把 ERLE 当目标，会毁掉近端', '进阶',
                 tldr='线性滤波器结构上拿不到喇叭的非线性部分，所以 ERLE 上限是 −20·log₁₀(非线性占比)。'
                      '剩下的靠残余抑制（RES）压，但 <strong>RES 越狠，近端语音越被削</strong>。'
                      '把 ERLE 当唯一目标，会走到近端 SNR 掉 %s dB 的地步。'
                      % r1(RES[0]['near_segsnr'] - rn['q_at_erle'])))
    o.append(fml('线性能拿到的上界', 'nonlin'))
    o.append(ex('实测：喇叭越推越狠',
                table(['#驱动', '#非线性占比 THD（%）', '#ERLE（dB）', '#理论上界（dB）'],
                      [['#%s' % r['drive'], '#%s' % r2(r['thd']), '#%s' % r2(r['erle']),
                        '#%s' % (r2(r['theory']) if r['theory'] is not None else '—')] for r in NL], cls='dp')
                + '<p>非线性 %s%% 看不出来（只差 %s dB）；到 %s%% 就掉 <strong>%s dB</strong>，'
                  '之后实测紧贴理论上界。<strong>这条天花板不是滤波器长度、步长或 DTD 能碰的。</strong></p>'
                % (r2(nn['thd1']), r2(nn['drop1']), r2(nn['bind_thd']), r2(nn['bind_drop']))))
    o.append(fml('残余抑制：增益与代价', 'res'))
    o.append(fig('res', '<strong>三个小图。</strong>① 非线性占比 → 线性 AEC 的上界；'
                 '② RES 越激进：ERLE ↑，近端 ↓；③ 凑到同样的总 ERLE，线性与 RES 怎么分工。'))
    o.append(ex('实测：RES 的激进程度 γ',
                table(['#γ', '#ERLE（dB）', '#近端分段信噪比（dB）', '#近端 STOI'],
                      [['#%s' % r['gamma'], '#%s' % r2(r['erle']), '#%s' % r2(r['near_segsnr']),
                        '#%s' % r3(r['near_stoi'])] for r in RES], cls='dp')
                + '<p>γ 从 0 到 %s：ERLE 好了 %s dB，近端分段信噪比从 %s 掉到 %s dB。'
                  '<strong>拐点在 γ = %s</strong>：用 %s dB 的近端代价换 %s dB 的 ERLE；'
                  '再往后每多拿 1 dB ERLE 就要多付好几 dB 近端。'
                  % (r0(RES[-1]['gamma']), r2(rn['erle_best'] - RES[0]['erle']),
                     r2(RES[0]['near_segsnr']), r2(rn['q_at_erle']), rn['knee_gamma'],
                     r2(RES[0]['near_segsnr'] - rn['knee_q']), r2(rn['knee_erle_gain'])) + '</p>'))
    o.append(trap('我原以为：ERLE 越高越好',
                  '把 γ 推到 ERLE 最高的那一点（γ = %g，ERLE %s dB），近端语音<strong>掉 %s dB</strong>。'
                  '对方不再听到回声，但也听不清你说话。<strong>回声消除的目标是"近端不受损下的 ERLE"，'
                  '而不是 ERLE 本身。</strong>'
                  % (rn['erle_best_gamma'], r2(rn['erle_best']), r2(RES[0]['near_segsnr'] - rn['q_at_erle']))))
    o.append(step('同样的总预算，线性和 RES 怎么分工'))
    o.append(ex('实测：凑到总 ERLE ≈ %s dB' % r0(RS['const']['target']),
                table(['分工', '#γ', '#总 ERLE（dB）', '#近端分段信噪比（dB）', '#近端 STOI'],
                      [[r['name'], '#%s' % r['gamma'], '#%s' % r2(r['erle']),
                        '#%s' % r2(r['near_segsnr']), '#%s' % r3(r['near_stoi'])] for r in SPL], cls='dp')
                + '<p>最好的是"%s"。线性部分做短了就得让 RES 补，RES 一补近端就坏——'
                  '三种分工里最好和最差差 <strong>%s dB</strong>。'
                  '<strong>能用线性消掉的，就别留给 RES。</strong></p>'
                % (sn['best'], r1(sn['gap']))))
    o.append('</section>')

    # ── C8（新）──────────────────────────────────────────────
    MN = MU2['note']
    MR = {r['name']: r for r in MU2['rows']}
    o.append(sec('f8', 'C8', '多参考通道：ERLE 好看，路径却没辨识对', '进阶',
                 tldr='立体声或多喇叭时，如果几路参考相互高度相关（同一个说话人，只差时延和增益），'
                      '滤波器只能辨识出一个<strong>组合</strong>，而不是每条路径本身。'
                      '换人之前 ERLE 有 %s dB、失调却只有 %s dB；远端一换人 ERLE 掉 %s dB。'
                      '去相关能买回一些，但每一种都要付播放质量的代价。'
                      % (r1(MN['base_before']), neg(r1(MN['base_mis'])), r1(MN['base_drop']))))
    o.append('<p>A14 末尾提到过多参考的非唯一性，这里把它量出来。'
             '设远端是立体声，但两路来自同一个说话人，所以 x₂ = c∗x₁，c 只是个短滤波器（位置不同，时延和增益不同）。</p>')
    o.append(fml('多参考的非唯一性', 'stereo'))
    o.append(fig('multi', '<strong>两个小图。</strong>① 远端说话人换人之后 ERLE 掉多少；'
                 '② 去相关换来的失调改善与它的播放信噪比代价。'))
    o.append(ex('实测：第 %s s 远端换人（c 由"时延 2、增益 0.9"变成"时延 14、增益 0.6"）' % r0(MU2['const']['change_s']),
                table(['去相关做法', '#两路相干性', '#换人前 ERLE', '#换人后 2 s', '#掉了', '#换人前失调', '#播放信噪比'],
                      [[r['name'], '#%s' % r3(r['coh']), '#%s dB' % r1(r['erle_before']),
                        '#%s dB' % r1(r['erle_after2s']), '#%s dB' % r1(r['drop']), '#%s dB' % neg(r1(r['mis'])),
                        '#%s' % (('%s dB' % r0(r['play_snr'])) if r['play_snr'] < 59 else '—')]
                       for r in MU2['rows']], cls='dp')
                + '<p>"播放信噪比"是去相关之后的播放信号相对原信号的信噪比（先去掉最佳的整体增益，不算单纯变响）。'
                  '不去相关时两路相干性是 %s，滤波器只辨识出 h₁ + h₂∗c 这一个组合：<strong>失调 %s dB，却有 %s dB 的 ERLE</strong>。'
                  'ERLE 在这种设备上不是"辨识对了"的证据。</p>'
                % (r3(MN['base_coh']), neg(r1(MN['base_mis'])), r1(MN['base_before']))))
    o.append(trap('我原以为：半波整流去相关就够了',
                  '经典的做法是给两路参考加相反方向的半波整流（Benesty 的非线性去相关）。α = 0.5 时两路相干性降到 %s，'
                  '但换人后的 ERLE 只少掉 %s dB（从 %s 到 %s），换人前的 ERLE 还少了 %s dB——线性滤波器拿不到的那部分变成了新的天花板（C7）。'
                  '加独立噪声更有效：−10 dB 的噪声把掉量降到 %s dB、失调到 %s dB，但<strong>播放信噪比只剩 %s dB，是听得出来的</strong>。'
                  '−20 dB（信噪比 %s dB）买到的只有 %s dB 的改善。'
                  % (r3(MR['半波整流 α=0.5']['coh']), r1(MN['base_drop'] - MN['hw05_drop']), r1(MN['base_drop']), r1(MN['hw05_drop']),
                     r1(MN['base_before'] - MN['hw05_before']), r1(MN['n10_drop']), neg(r1(MN['n10_mis'])), r0(MN['n10_snr']),
                     r0(MN['n20_snr']), r1(MN['base_drop'] - MN['n20_drop']))))
    o.append(note('怎么办',
                  '本书只量了上面两种去相关。工程上更常见的是<strong>不让问题出现</strong>：单喇叭设备用单路参考（一个喇叭只有一条路径，没有非唯一性）；'
                  '立体声设备把参考下混成一路给 AEC 之前先确认喇叭是否真有两路独立声道；'
                  '多说话人的会议系统把每个远端说话人当成独立参考。这几条是工程惯例，不是本书的实测。'
                  '实验里的 c 只是时延加增益；真实立体声录音里 c 是频率相关的，相干性不会这么高，但同样会随说话人位置变化。'))
    o.append('</section>')

    # ── C9（新）──────────────────────────────────────────────
    DN2 = DX['note']
    o.append(sec('f9', 'C9', '全双工与打断：回声消除之后真正要回答的问题', '深入',
                 tldr='半双工是播放时关麦，用户插不进话；全双工靠 AEC 在播放时还能听见用户。'
                      '听见的灵敏度由<strong>回声底</strong>（平均 ERLE）和<strong>瞬态尖峰</strong>一起定：'
                      '本实验里 ERLE %s dB → 近端比回声轻 %s dB 仍可检；ERLE %s dB（卡尔曼）→ %s dB；'
                      '而全知 DTD（ERLE %s dB）并不比卡尔曼更灵。'
                      % (r0(DXK['energy']['erle']), neg(r0(abs(DN2['energy_min']))) if DN2['energy_min'] is not None else '—',
                         r0(DXK['fdkf']['erle']), neg(r0(abs(DN2['fdkf_min']))) if DN2['fdkf_min'] is not None else '—',
                         r0(DXK['oracle']['erle']))))
    o.append('<p>语音助手在播报（TTS）时用户开口——这叫<strong>打断</strong>（barge-in）。'
             '半双工设备在播放时把麦克风关掉（或者门限抬得很高），用户只能等它说完。'
             '全双工的前提是 AEC 够好，好到<strong>还能在回声里听见用户</strong>。'
             '这里把"够好"量成两个数：最轻能检出多轻的近端，以及要等多久。</p>')
    o.append(fml('打断的检测量', 'barge'))
    o.append('<p>检测量取残差功率与回声估计功率之比。只有回声时它等于 −ERLE；用户开口后它抬到大约近端相对回声的电平。'
             '阈值 θ 用<strong>只有回声</strong>的校准段定：校准段里最高的一次再加 1 dB，保证校准段里一次误触发都没有；'
             '然后在插话段里看多快触发、多轻触发不了。连续 %s ms 超过阈值才算。'
             % r0(DX['const']['hold_ms']) + '</p>')
    o.append(fig('duplex', '<strong>两个小图。</strong>① 各种前端下，近端有多轻还能检出；'
                 '② 稳态回声底与校准出的阈值——两者之间隔着一段瞬态尖峰。'))
    o.append(ex('实测：前端与可检测电平（%s 次试验，近端 %s s 插话；误触发在 %s 段只有回声的测试上数）'
                % (len(DX['const']['test_seeds']), r0(DX['const']['t_len']), len(DX['const']['test_seeds'])),
                table(['前端', '#ERLE', '#回声底', '#阈值', '#阈值 − 回声底', '#误触发', '#最轻可检（≥90%）'],
                      [[r['name'], '#%s dB' % r1(r['erle']) if r['kind'] != 'raw' else '#—',
                        '#%s dB' % neg(r1(r['floor'])), '#%s dB' % neg(r1(r['theta'])),
                        '#%s dB' % r1(r['theta'] - r['floor']), '#%d/%d' % (r['fa_runs'], len(DX['const']['test_seeds'])),
                        '#%s' % (('%s dB' % neg('%+.0f' % r['min_ner'])) if r['min_ner'] is not None else '检不出')]
                       for r in DX['kinds']], cls='dp')
                + '<p>"最轻可检"取检出率 ≥ 90% 的最低近端电平，分辨率只有 5 dB 一档。'
                  '不做 AEC 时，近端比回声轻 5 dB 以下一个也检不出；有了 AEC，ERLE 每高一截，最轻可检就低一截。</p>'))
    lat_rows = []
    for r in DX['kinds']:
        lat_rows.append([r['name']] + ['#%s' % (('%s%%<br>%s' % (r0(c['det']), ('%s ms' % r0(c['lat_ms'])) if c['lat_ms'] else '—')))
                                        for c in r['by_ner']])
    o.append(ex('实测：检出率与中位延迟（从用户开口算起）',
                table(['前端'] + ['#%s dB' % neg('%+.0f' % c['ner']) for c in DX['kinds'][0]['by_ner']], lat_rows, cls='dp')
                + '<p>延迟里有 %s ms 是"连续超过阈值"的保持时间。近端比回声响 10 dB 时 %s ms 就能触发；'
                  '近端和回声一样响（0 dB）时要 %s ms——因为要等用户的第一个响亮元音。'
                  '这是在<strong>这套检测量</strong>下的结果，一个把"远端当前说话 / 用户在说"一起考虑的判决器会好得多，本书没有做。</p>'
                % (r0(DX['const']['hold_ms']), r0(DN2['fdkf_lat10']), r0(DN2['fdkf_lat0']))))
    o.append(trap('我原以为：ERLE 每高 10 dB，能听见的声音就轻 10 dB',
                  '从 ERLE %s dB 到 %s dB（高 %s dB），最轻可检只低了 5 dB 一档；ERLE %s dB 的全知 DTD 也没有更灵。'
                  '原因是阈值不是由平均回声底定的，而是由<strong>校准段里最高的那个瞬态尖峰</strong>定的：'
                  '它比回声底高 %s–%s dB，平均 ERLE 的好处被这段"尖峰余量"抵掉大半。'
                  '我试过"远端起音后屏蔽 %s ms"，阈值没有降（%s → %s dB），所以尖峰不集中在远端起音处——'
                  '它们具体来自哪里，这一节没有查清。'
                  % (r0(DXK['energy']['erle']), r0(DXK['fdkf']['erle']), r0(DXK['fdkf']['erle'] - DXK['energy']['erle']),
                     r0(DXK['oracle']['erle']), r0(DXK['energy']['theta'] - DXK['energy']['floor']),
                     r0(DXK['fdkf']['theta'] - DXK['fdkf']['floor']),
                     r0(190), neg(r1(DXK['fdkf']['theta'])), neg(r1(DXK['fdkf_mask']['theta'])))))
    o.append(note('这一节没覆盖的',
                  '打断真正的判决还要看<strong>用户是不是在说话</strong>（VAD）、说的是不是<strong>唤醒词或指令</strong>（D 部分的唤醒），'
                  '以及是不是<strong>该设备的用户</strong>（D 部分的声纹）。这些都不是靠回声消除后的能量能回答的。'
                  '停播的响应时间（判决之后设备多久真的静下来）、重新开始识别要多久，本书也没有测。'
                  '实验里的近端和远端都是合成语音，近端插话的位置已知；真机上是未知的，误触发会更多。'))
    o.append('</section>')

    # ── C7 ────────────────────────────────────────────────────
    o.append(sec('f10', 'C10', '三段合起来：全双工的预算与翻车点', '深入',
                 tldr='全双工的效果由链路上最差的一段定，而且三段的上限互不相通。'
                      '这一节把前面所有"天花板"和"悬崖"放进一张表，再列出现场最常见的几个翻车点。'))
    o.append(table(['环节', '天花板由什么定', '典型的数', '它怎么失效'], [
        ['滤波器长度', '覆盖房间尾巴的比例',
         '64→128 ms：+%s dB；256→512 ms：%s dB' % (r2(AD['length_note']['d64_128']),
                                                   neg(r2(AD['length_note']['d256_512']))),
         '短了被尾巴卡死，长了被底噪卡死'],
        ['步长 μ', '快与准的积守恒', 'μ %g→%g：收敛快 %s 倍 ⇔ 失调差 %s dB' % (AD['mu_tradeoff']['slow_mu'], AD['mu_tradeoff']['fast_mu'], r1(AD['mu_tradeoff']['t_ratio']),
                                                                  r2(AD['mu_tradeoff']['mis_gain'])),
         '只看 ERLE 看不见失调'],
        ['块长', '延迟与算力互换', '延迟 −%s 倍 ⇔ 算力 +%s 倍' % (r0(AD['part_note']['delay_ratio']),
                                                                 r1(AD['part_note']['mac_ratio'])),
         '唯一明码标价的取舍'],
        ['双讲检测', '漏检阈值型 / 误检渐进型',
         '不冻结比全知差 %s dB' % r2(DT['no_dtd_cost']), '检测器弱时最优点只是"几乎不学"，路径一换就回不来（C5）'],
        ['不靠检测器', '观测噪声自己定步长', '卡尔曼 %s dB，距全知差 %s dB' % (r1(D2['note']['fdkf_static']), r1(D2['note']['fdkf_gap_to_oracle'])),
         '近端很响时不如双路径'],
        ['延迟估计', '高估是悬崖，低估是斜坡', '估高 8 ms：%s dB；估低 48 ms：%s dB' % (r1(DL['note']['over8']), r1(DL['note']['under48'])),
         '要故意往低的一侧偏'],
        ['多参考通道', '参考相关 → 解不唯一', '换人掉 %s dB，失调只有 %s dB' % (r1(MU2['note']['base_drop']), r1(MU2['note']['base_mis'])),
         'ERLE 不是"辨识对了"的证据'],
        ['打断灵敏度', '回声底 + 瞬态尖峰', 'ERLE %s → %s dB，最轻可检仅低 5 dB' % (r0(DXK['energy']['erle']), r0(DXK['fdkf']['erle'])),
         '平均 ERLE 的好处被尖峰余量抵掉大半'],
        ['时钟', '尾部抽头先解相关', '%d ppm 掉 6 dB' % pn['ppm_6db'], '加长滤波器反而更亏'],
        ['整块延迟', '滤波器装不下就是悬崖', '落到 %s dB' % r1(dn['last']), '换设备、接蓝牙时悄悄发生'],
        ['喇叭非线性', '−20·log₁₀(占比)', '%s%% → %s dB' % (r1(nn['worst_thd']), r1(nn['worst_erle'])),
         '线性方法结构上拿不到'],
        ['残余抑制', '近端被一起压', 'ERLE +%s dB ⇔ 近端 −%s dB' % (r1(rn['erle_best'] - RES[0]['erle']),
                                                              r1(RES[0]['near_segsnr'] - rn['q_at_erle'])),
         '把 ERLE 当目标会毁掉近端'],
    ], minw=640))
    o.append(step('AEC 之后那一级：RES 与单通道降噪各管什么'))
    CN = CH['note']
    o.append('<p>前面把"AEC 之后再压一次"都叫 RES（C7）。而 B 部分的单通道降噪也能放在这个位置。'
             '它们能互相替代吗？分三个场景量：只有回声、只有近端语音加房间噪声、三样都有。AEC 是频域卡尔曼（C5）。</p>')
    o.append(fig('chain', '<strong>三个小图。</strong>各自管各自的事：RES 压回声、NS 压噪声；两者先后顺序几乎无所谓。'))
    o.append(ex('实测：AEC（频域卡尔曼）之后的一级（喇叭 THD ≈ %s%%，近端噪声信噪比 %s dB，近端 = 回声）'
                % (r0(CH['thd']), r0(CH['const']['noise_snr'])),
                table(['这一级', '#只有回声：下降（dB）', '#只有噪声：近端 segSNR', '#三样都有：近端 segSNR', '#三样都有：STOI'],
                      [['不做处理（麦克风信号）', '#—', '#%s dB' % r1(CH['base']['noise_near']), '#%s dB' % r1(CH['base']['all_near']), '#—']] +
                      [[r['name'], '#%s dB' % r1(r['echo']), '#%s dB' % r1(r['noise_near']), '#%s dB' % r1(r['all_near']),
                        '#%s' % r3(r['all_stoi'])] for r in CH['rows']], cls='dp')
                + '<p>NS 在只有回声时只多压 %s dB——回声不平稳，它把残余回声当语音留下来；RES 多压 %s dB。'
                  '只有噪声时 NS 让近端 segSNR 好 %s dB，RES 一点没有（它只看回声估计）。'
                  '三样都有时 RES→NS 比 NS→RES 只好 %s dB，顺序几乎无所谓；<strong>两个都留</strong>比任何单独一个都好。</p>'
                % (r1(CN['ns_echo'] - CN['aec_echo']), r1(CN['res_echo'] - CN['aec_echo']),
                   r1(CN['ns_noise'] - CN['base_noise']), r2(CN['order_gap']))))
    o.append(step('四段按不同顺序串起来'))
    JN = JT['note']
    o.append('<p>前面把每一段单独量过。这里把阵列（A）、回声消除（C）、残余抑制（R）、单通道降噪（N）真的串起来跑：'
             '四麦线阵（间距 %s mm）、喇叭紧挨阵列、近端说话人在 %s° 方向、粉噪，回声与近端各有每个麦克风自己的混响冲激响应，喇叭带轻度非线性（THD %s%%）。'
             'MVDR 的噪声协方差在近端没说话的帧上递推，所以权重是真的时变（相邻帧中位变化 %s%%）。</p>'
             % (r0(JT['const']['spacing_mm']), r0(JT['const']['theta_deg']), r1(JN['thd']), r1(100 * JN['w_change'])))
    o.append(fig('joint', '<strong>六种串法。</strong>① 只有回声时输出相对回声下降多少；② 近端说话时对直达声的分段信噪比。'))
    o.append(ex('实测：端到端（%d 个种子）' % len(JT['const']['seeds']),
                table(['串法', '#回声下降', '#近端 segSNR', '#近端 STOI'],
                      [['不处理（参考麦克风）', '#0', '#%s dB' % neg(r1(JT['base']['near'])), '#%s' % r3(JT['base']['stoi'])]] +
                      [[r['name'], '#%s dB' % r1(r['echo']), '#%s dB' % neg(r1(r['near'])), '#%s' % r3(r['stoi'])] for r in JT['rows']], cls='dp')
                + '<p>目标是近端语音在参考麦克风上的<strong>直达声</strong>（波束会去混响，拿带混响的当标准答案会罚波束）。'
                  '<strong>顺序确实有区别</strong>：自适应波束放在回声消除前面，回声只下降 %s dB；放在后面是 %s dB，差 <strong>%s dB</strong>，近端也差 %s dB。'
                  '换成固定波束，前后只差 %s dB——和 A14 的结论一致：问题不在"波束"，在"权重会变"。</p>'
                % (r1(JN['mvdr_echo']), r1(JN['cmvdr_echo']), r1(JN['order_gap_echo']), r1(JN['order_gap_near']), r1(JN['fixed_gap_echo']))))
    o.append(trap('我原以为：自适应波束一定比固定波束好',
                  '在这个场景里不是：自适应 MVDR 的近端分段信噪比 %s dB，固定 DAS 是 %s dB。噪声是弥散的（粉噪各麦独立生成），MVDR 能压的方向性干扰不存在，'
                  '协方差的估计误差反而带来代价。MVDR 的价值在有方向性干扰时才出来——本实验没有放方向性干扰，所以没有量那一半。'
                  % (r1(JN['cmvdr_near']), r1(JN['cdas_near']))))
    o.append(note('三段怎么串',
                  '链路顺序是：<strong>回声消除（C）→ 波束（A）→ 残余抑制与单通道降噪（R、N）</strong>。上面的端到端实验验证了 A14 的计算：'
                  '波束权重每帧都在变，波束后面的 AEC 要辨识的路径就跟着变——自适应波束放在 AEC 前面，回声多留 %s dB。'
                  '所以 AEC 要么在自适应波束<strong>之前</strong>（每路一个，算力 ×M），要么让波束固定 / 在远端有声时冻结权重。'
                  'AEC 之后那一级是 <strong>RES 加 NS 一起留着</strong>（上一步的实测），先后顺序几乎无所谓。'
                  '这一组实验的局限：只有一种房间、一个近端方向、弥散噪声、近端说话时间已知（MVDR 的协方差更新用了这个"理想 VAD"），没有方向性干扰。'
                  % r1(JN['order_gap_echo'])))
    o.append(trap('现场常见的五个翻车点',
                  '<p>① 只在安静房间测 ERLE，上线后一说话就坏——没测双讲。<br>'
                  '② 用 ERLE 当唯一指标，把 RES 调到近端发闷。<br>'
                  '③ 换了蓝牙耳机或加了一级缓冲，没人重算延迟，滤波器已经装不下路径。<br>'
                  '④ 喇叭推到接近削波，把线性 AEC 的上限悄悄压到 %s dB 以下。<br>'
                  '⑤ 麦克风和喇叭不同源，没有时钟补偿，长滤波器反而更差。</p>' % r0(nn['bind_erle'])))
    o.append(q([
        ('滤波器从 256 ms 加到 512 ms，ERLE 几乎没变（%s dB）。下一步应该调什么？' % neg(r2(AD['length_note']['d256_512'])),
         '加长滤波器已经没用：此时卡住的是近端底噪（%s dB 的上限）。应该看 RES、阵列或者提高近端信噪比。'
         % r0(LEN[3]['cap_noise']), '提示：先找最低的天花板。'),
        ('DTD 的两种错误率相等是最优点吗？那"误检高达 80%"的最优点就是该冻的比例吗？',
         '不是最优点：漏检是阈值型（短于 %s s 几乎免费，长了发散），误检是渐进型，两种错误的代价形状不同，按 EER 去定要亏 %s dB。'
         '但 80%% 的误检不是工程建议——它意味着滤波器几乎不再学，"收敛后不再学"的对照比它还高 %s dB，而路径一换它就回不来。'
         % (r1(DT['miss_knee']['free_up_to']), r2(DT['eer_cost']), r2(D2['note']['frozen_vs_energy'])),
         '提示：看 C5 的对照与"路径整条换掉"那一行。'),
        ('延迟估计有 ±8 ms 的不确定，应该往哪边偏？',
         '往低估的一侧偏。估高 8 ms 就从 %s dB 掉到 %s dB（直达声落到滤波器之外），估低 48 ms 也还有 %s dB。留 8 ms 余量，代价是估准时少 %s dB。'
         % (r1(DL['note']['erle_exact']), r1(DL['note']['over8']), r1(DL['note']['under48']), r1(DL['note']['erle_exact'] - DL['note']['m8_exact']))),
        ('立体声设备上 ERLE 有 %s dB，可以认为两条路径都辨识对了吗？' % r0(MU2['note']['base_before']),
         '不能。两路参考相干时滤波器只辨识出 h₁ + h₂∗c 这个组合，实测失调只有 %s dB；远端一换人 ERLE 就掉 %s dB。'
         % (neg(r1(MU2['note']['base_mis'])), r1(MU2['note']['base_drop']))),
        ('AEC 的 ERLE 从 %s dB 提到 %s dB，打断检测能听见的近端会轻 %s dB 吗？'
         % (r0(DXK['energy']['erle']), r0(DXK['fdkf']['erle']), r0(DXK['fdkf']['erle'] - DXK['energy']['erle'])),
         '不会。本实验里只轻了 5 dB（一档）：阈值由回声里的瞬态尖峰定，比回声底高 %s–%s dB，平均 ERLE 的好处被抵掉大半。'
         % (r0(DXK['energy']['theta'] - DXK['energy']['floor']), r0(DXK['fdkf']['theta'] - DXK['fdkf']['floor']))),
        ('50 ppm 的时钟差下，32 ms 和 256 ms 的滤波器哪个更亏？',
         '256 ms 的：赔 %s dB，而 32 ms 的几乎不受影响（%s dB）。尾部抽头最先解相关。'
         % (r2(ln['long']), r2(ln['short']))),
        ('RES 的 γ 取多大合适？',
         '看拐点，不看 ERLE 最大点。本实验的拐点在 γ = %s：近端代价 %s dB，换 ERLE +%s dB。'
         % (rn['knee_gamma'], r2(RES[0]['near_segsnr'] - rn['knee_q']), r2(rn['knee_erle_gain']))),
    ]))
    o.append('</section>')

    # ── C11 理论补篇 ──────────────────────────────────────────
    o.append(sec('f12', 'C11', '理论补篇：没有做实验的四块', '深入',
                 tldr='前面十节的每个数都是跑出来的。这一节讲的四件事——神经方法、打断与唤醒/声纹的联动、回声尖峰的来源、带记忆的喇叭非线性——'
                      '我没有做实验，所以这里<strong>一个实测数字都没有</strong>，只给定义、推导、判据和该怎么测。'
                      '需要实测的地方，写明了要测什么、怎样才算数。'))
    o.append(why('读这一节的方式：把每一小节当作"如果要做，应该怎么做、怎么判断做对了"的规范，而不是结论。'))

    # 1 神经方法
    o.append('<h3>一、神经方法：它改变了什么，没改变什么</h3>')
    o.append('<p><strong>1.1 先分清三种用法。</strong>神经网络在回声链路里有三种位置，风险完全不同：</p>')
    o.append(table(['用法', '网络的输入 → 输出', '线性 AEC 还在吗', '主要风险'], [
        ['神经 RES（后置）', '残差 e 与回声估计 ŷ 的幅度谱 → 时频增益', '在，且先跑',
         '增益是乘性的：只能压，不能凭空造；训练分布外会"压错地方"'],
        ['神经 DTD / 步长控制', 'x、y、e 的特征 → 每块"更新还是冻结"（或步长）', '在，网络只管调度',
         '判错的代价不对称（C4）：漏检阈值型、误检渐进型，损失函数得显式反映'],
        ['端到端（含神经 AEC）', 'x 与 y → 近端语音', '可以没有',
         '要在网络里隐式学路径与非线性；路径变化的跟踪要靠网络状态，而不是自适应更新']],
        minw=560))
    o.append('<p><strong>1.2 神经 RES 的标准写法。</strong>目标是理想比值掩蔽：在每个时频点上，近端语音功率占"近端 + 残余回声"总功率的比例的平方根。'
             '网络从特征预测它，输出乘到残差谱上。</p>')
    o.append(fml('神经 RES 的训练目标', 'irm', [('P<sub>s</sub>', '近端语音功率'), ('P<sub>r</sub>', 'AEC 之后残余回声功率'),
                                               ('E', '线性 AEC 的残差谱'), ('θ', '网络参数')]))
    o.append('<p>它和 C7 的维纳式 RES 是<strong>同一类东西</strong>：都是对残差谱乘一个 0–1 的增益。区别只在增益怎么得到——'
             '维纳式用一个旋钮 γ 乘回声估计功率当"噪声功率"，假设残余回声的谱形状正比于 ŷ 的谱；'
             '神经式从数据里学这个对应关系，所以<strong>能表达"非线性失真产生的谐波落在哪些频点"</strong>这类线性假设表达不了的结构。'
             '这是它真正的增益来源，也只有这一处。</p>')
    o.append('<p><strong>1.3 它没改变的三件事。</strong></p><ul>'
             '<li><strong>近端损伤与 ERLE 的取舍仍在。</strong>掩蔽只能压，近端与残余回声在同一时频点重叠时，'
             '任何增益都是"两个一起压"。更好的网络是把<strong>同样的近端损伤下的 ERLE</strong>推高，而不是消除这条取舍曲线。'
             '所以比较两种 RES 必须在<strong>同一近端损伤</strong>上比 ERLE（C7 的做法），而不能各取各的最佳点。</li>'
             '<li><strong>天花板的第一条仍是相干性。</strong>见下面的公式：对线性时不变滤波器，ERLE 上界由参考与回声之间的相干性定。'
             '神经 RES 作用在滤波之后，不受这条限制——但它的输入 ŷ 里已经不含非线性成分，所以它只能靠"残差谱形状"去猜。</li>'
             '<li><strong>训练分布决定它在哪里可信。</strong>网络没有自适应更新；房间、喇叭、远端内容与训练时不同，性能退化是<strong>默默发生</strong>的，'
             '而线性自适应滤波器至少会因为误差变大而重新收敛。</li></ul>')
    o.append(fml('线性滤波器的 ERLE 上界（相干性）', 'cohbound',
                 [('γ²', '参考 x 与回声 d 的幅度平方相干'), ('S', '互谱 / 自谱')]))
    o.append('<p>这条式子说明：只要 d 里有 x 的线性函数<strong>解释不了</strong>的部分（非线性、时变、噪声），γ² &lt; 1，线性 AEC 的 ERLE 就有硬上界。'
             '这就是为什么非线性成为瓶颈时要换结构，而不是继续加长滤波器、调步长。</p>')
    o.append('<p><strong>1.4 因果性、时延与算力。</strong>RES 网络的每帧时延 = 帧长 + 前瞻帧数 × 帧移。'
             '全双工链路的总时延预算里它与块长（C3）共用同一条延迟线；用了前瞻就要把它记进 T<sub>buf</sub>（见第二节的时延账）。'
             '算力按"每帧乘加数 ÷ 帧移"折成每秒乘加；一个 N 层、宽度 H 的全连接网络，每帧乘加约 N·H²。'
             '要在端侧跑，先确认的是<strong>峰值算力占用</strong>而不是平均值，因为回声消除与语音识别抢同一颗核。</p>')
    o.append('<p><strong>1.5 怎样才算"做对了"（评测规范）。</strong></p>'
             + table(['维度', '做法', '常见错误'], [
                 ['同一近端损伤下的 ERLE', '扫增益指数或阈值，得到"ERLE–近端 SegSNR"曲线，在相同的近端 SegSNR 上读 ERLE',
                  '各取各的最优点比较，天然偏向更激进的那个'],
                 ['训练外条件', '换远端内容（语音/音乐/噪声）、换喇叭失真量、换近端电平，单独报告',
                  '训练与测试同房间同喇叭，数字好看但泛化未知'],
                 ['近端保真', '双讲段用 SegSNR 与可懂度代理量，同时听', '只报单讲段 ERLE'],
                 ['时延与算力', '报每帧乘加、前瞻帧数、峰值内存', '只报参数量'],
                 ['线性级的对照', '同一个线性 AEC 后面接维纳 RES 当基线', '拿"无 RES"当基线，高估增益']],
                 minw=560))
    o.append(note('这一小节没覆盖的',
                  '没有训练过任何网络，所以<strong>不给"神经比维纳好多少"的数</strong>。我起初打算用一个小 MLP 做同损伤对比，决定不做：'
                  '一个玩具规模的网络在合成数据上得出的差距，既不能代表真实的 DNS/AEC 网络，也会让读者误以为这个差距可迁移。'
                  '大规模神经 AEC 需要真实录音与大量数据，本书没有。'))

    # 2 打断联动
    o.append('<h3>二、打断与 VAD、唤醒、声纹的联动，以及停播的时延账</h3>')
    o.append('<p><strong>2.1 判决是一个多级门，不是一个阈值。</strong>C9 的统计量 s 只回答"残差里有没有比回声底更多的东西"。'
             '要把它变成"该不该停播"，还要问三件事，依次变窄：</p>')
    o.append(table(['级', '问题', '依据', '放过 / 拦住'], [
        ['1 能量门', '残差里有额外能量吗', 'C9 的统计量 s 与阈值 θ、保持块数 H', '放过：用户说话、TV、旁人；拦住：纯回声'],
        ['2 VAD', '那是语音吗', '在残差 e（不是原始麦克风信号）上做语音活动检测', '拦住：脚步声、敲击、风噪'],
        ['3 唤醒 / 指令词', '是不是设备该响应的内容', '唤醒词模型（D 部分）；在 e 上跑', '拦住：旁人闲聊、TV 里的人声'],
        ['4 声纹', '是不是这位用户', '说话人嵌入与注册声纹的相似度（D 部分）', '拦住：其他家庭成员、TV']],
        minw=560))
    o.append('<p>后一级比前一级更慢、更准、更贵。工程上常见的是<strong>先停后判</strong>：能量门一过就把 TTS 压低（duck），'
             '后级确认了再真停，没确认就恢复。这样前级可以放宽误触发，代价由"压低又恢复"那一下来付，用户体感比"误停"轻得多。'
             '把"压低"和"停"分成两个动作，是这一节最重要的结构性建议。</p>')
    o.append('<p><strong>2.2 为什么后级必须吃 AEC 之后的信号。</strong>唤醒与声纹模型是在干净或带环境噪声的近端语音上训练的。'
             '直接喂麦克风原始信号，设备自己的 TTS 就是最强的干扰；喂 AEC 之后的残差，输入里还有残余回声与 AEC 引入的失真。'
             '两种输入的分布都和训练时不同，要么重训、要么对残差做数据增强（把"残余回声 + 近端"按真实 ERLE 分布混进训练集）。'
             '声纹尤其敏感：残余回声在频谱上带着"设备自己声音"的长时统计，会污染说话人嵌入。</p>')
    o.append('<p><strong>2.3 时延账。</strong>从用户开口到设备真的静下来，是下面几项的和：</p>')
    o.append(fml('用户开口到设备静下来的时延', 'stoplat',
                 [('T<sub>hold</sub>', '连续超过阈值的块数 × 块长（C9 中 H 块）'),
                  ('T<sub>smooth</sub>', '统计量的平滑窗；一个因果平滑窗平均滞后窗长的一半'),
                  ('T<sub>vad</sub>', 'VAD 或唤醒级的判决所需上下文'),
                  ('T<sub>dec</sub>', '决策逻辑与跨线程/跨进程调度'),
                  ('T<sub>buf</sub>', '音频输出缓冲里已经排队的 TTS（播放器缓冲）'),
                  ('T<sub>ramp</sub>', '为避免爆音而做的淡出时长')]))
    o.append('<p>C9 实测的"检测延迟"只包含前两项。<strong>T<sub>buf</sub> 常常是最大的一项</strong>：为了抗抖动，播放链路里排着几十到几百毫秒的音频，'
             '判决之后这些要么被丢弃（需要播放器支持 flush），要么被播完。能否 flush、flush 后参考通道怎么处理，'
             '决定了整条链路的下界。另有一个<strong>参考一致性</strong>问题：flush 之后，送给 AEC 的参考 x 必须同步截断，'
             '否则滤波器会按"还在播"去预测回声，把残余的真实静音当作近端出现。</p>')
    o.append('<p><strong>2.4 停播之后还有两笔账。</strong>其一是<strong>重新开始识别的起点</strong>：被判为打断的那一刻之前，'
             '用户已经说了 T<sub>stop</sub> 这么久，识别需要从更早的位置开始（回溯缓冲），否则开头的词被吞掉——'
             '回溯长度不应小于 T<sub>hold</sub> + T<sub>smooth</sub>/2 + T<sub>vad</sub>。'
             '其二是<strong>AEC 状态在静音期间怎么处理</strong>：TTS 停了，参考 x 为零，自适应更新应暂停（C2 的归一化项会放大噪声），'
             '恢复播放时滤波器仍保留停前的权重，这正是它不用重新收敛的原因。</p>')
    o.append(note('这一小节没覆盖的',
                  '没有搭 VAD、唤醒、声纹与 TTS 播放器，所以<strong>没有实测的停播时延</strong>，也没有"先压低后确认"的误触发数。'
                  '上面的时延账是定义与分解，不是测量。播放缓冲、flush 行为是设备相关的，只能在目标设备上测。'))

    # 3 尖峰来源
    o.append('<h3>三、回声底上的瞬态尖峰从哪里来</h3>')
    o.append('<p>C9 里的阈值比回声底高出好几 dB，原因是校准段的最大值被尖峰抬高。我试过"远端起音后屏蔽"，阈值没降，所以那里没有查清。'
             '这里把<strong>可能的来源按机理列全</strong>，并给出分辨它们的实验设计；没有跑，所以不下结论。</p>')
    o.append(table(['候选机理', '会在什么时候出现', '怎么分辨（要测的量）'], [
        ['远端谱突变，滤波器跟不上', '远端从停顿到元音、或换说话人时；某些频点之前长时间没有能量，权重没有被激励过',
         '尖峰时刻与"远端分频带能量上升斜率"相关；把远端换成平稳噪声后尖峰应消失'],
        ['滤波器失调累积', '长时间有近端干扰（双讲）或路径缓变之后',
         '失调（C2）随时间的曲线与尖峰出现位置对齐；冻结全部更新后尖峰应不再增多'],
        ['非线性在峰值处', '远端幅度大的瞬间，tanh 一类的软限幅失真最大',
         '尖峰与远端瞬时幅度的包络相关；把远端幅度压低 6 dB，尖峰应按非线性占比减小，而不是按线性比例'],
        ['分母过小', '远端静音、ŷ 的功率趋近于零，s = 10log(Pe/Pŷ) 比值被噪声撑大',
         '看尖峰是否集中在远端能量低的块；换用"Pe 相对其长期均值"做统计量后消失'],
        ['路径的微小变化', '温度、位置、人在附近走动', '同一段数据重放两遍，尖峰位置不变则是信号机理、变了则是路径']],
        minw=560))
    o.append('<p><strong>3.1 阈值与误触发的统计学。</strong>如果把 s 在只有回声时的分布近似为均值 μ₀、标准差 σ₀ 的高斯，'
             '单块越过阈值的概率是 p = 1 − Φ(z)。要求"连续 H 块都越过"才触发，在<strong>块间独立</strong>的假设下误触发概率是 p<sup>H</sup>；'
             '但统计量是平滑过的、滤波器的失调也是缓变的，块间<strong>正相关</strong>，所以真实的连续越过概率远大于 p<sup>H</sup>。'
             '再乘上总块数就是一段时间内的期望误触发数。</p>')
    o.append(fml('阈值与误触发', 'fa', [('μ₀, σ₀', '纯回声下 s 的均值与标准差'), ('z', '高斯分位数'), ('H', '保持块数'), ('T', '总时长')]))
    o.append('<p>这有两个后果。第一，<strong>用校准段的最大值定阈值</strong>（C9 的做法）本质是取了一个随校准时长增长的极值：'
             '段越长、尖峰越重尾，阈值越高。校准时长应与部署时的连续纯回声时长同量级，不能用"几分钟"去保证"几天"。'
             '第二，重尾的尖峰意味着<strong>高斯近似会低估误触发</strong>，更稳的做法是直接用经验分布的高分位数，'
             '并报告校准集的大小和分位数的置信区间。</p>')
    o.append(note('这一小节没覆盖的',
                  '上表是假说清单，不是结论。C9 里只验证了其中一条（远端起音屏蔽）无效。'
                  '其余各条都要用"控制变量重放"来分辨：固定远端、只改一个因素，看尖峰是否随之改变。'))

    # 4 记忆非线性
    o.append('<h3>四、带记忆的喇叭非线性：为什么线性 AEC 的天花板更低</h3>')
    o.append('<p>C7 用的是无记忆的 tanh 软限幅：输出只取决于当前样点的输入。真实的喇叭与功放不是这样——'
             '音圈的位置、温度、悬挂的弹性都带有<strong>时间上的惯性</strong>，当前输出依赖于过去一小段输入。</p>')
    o.append(fml('Hammerstein 型带记忆非线性喇叭 + 房间', 'mempoly',
                 [('x', '数字参考信号'), ('u', '喇叭的声压输出（带记忆多项式）'), ('c<sub>p,k</sub>', 'p 次项、第 k 个延迟的系数'),
                  ('h<sub>q</sub>', '房间冲激响应'), ('d', '麦克风处的回声')]))
    o.append('<p><strong>4.1 它为什么更难。</strong>线性 AEC 只能捕捉 p = 1 的那一族项（x(n−k) 的线性组合），其余 p ≥ 3 的项都落在"线性滤波器的互补空间"里，'
             '构成不可消除的残余。无记忆时，这些项是 x(n) 的瞬时函数，谐波的幅度与相位关系固定；'
             '有记忆时，k 个不同延迟的 x 乘在一起，<strong>残余的谱形状会随 x 的包络和相位变化</strong>，'
             '这让 C7 里"残余的谱与回声估计的谱成比例"这一维纳式假设更不成立。</p>')
    o.append('<p><strong>4.2 上界怎么推。</strong>把 d 分成线性可预测的部分 d<sub>L</sub> 与不可预测的部分 d<sub>N</sub>（两者对 x 不相关）。'
             '最优线性滤波器之后，残余功率 ≥ P(d<sub>N</sub>)，所以 ERLE ≤ −10log₁₀(P(d<sub>N</sub>)/P(d))；'
             '它与上面的相干性公式是同一个量：γ² = P(d<sub>L</sub>)/P(d)。'
             '无记忆 tanh 的 d<sub>N</sub> 只含奇次谐波；带记忆时 d<sub>N</sub> 还含"互调项"（不同延迟样点的乘积），'
             '这些互调项在频域上落在输入带内，<strong>不能靠"只看谐波落到带外去滤掉"解决</strong>。</p>')
    o.append('<p><strong>4.3 补救办法与它们各自的代价。</strong></p>'
             + table(['方法', '做法', '代价与限制'], [
                 ['Hammerstein 级联', '前面加一个静态非线性（如多项式 / 软限幅的逆），后面接线性 AEC',
                  '只覆盖无记忆部分；非线性参数要在线辨识，辨识本身对双讲敏感'],
                 ['记忆多项式 / Volterra', '把 x^p(n−k) 作为额外的"参考通道"喂给多通道 AEC（C8）',
                  '参考彼此高度相关（x、x³ 几乎共线），C8 的非唯一性问题原样出现；参数量按 K·P 增长'],
                 ['神经网络的非线性回声估计', '网络从 x 的历史预测 d 的非线性成分，再从 y 里减掉',
                  '要在目标喇叭上训练或自适应；分布外性能不可控（一节）'],
                 ['RES 兜底', '线性之后用 RES（C7）压残余', '近端损伤；并且在非线性占比大时 RES 的"谱与 ŷ 成比例"假设最差'],
                 ['从硬件侧限制', '限幅、功放工作点、整机结构', '不是算法问题，但常常是性价比最高的一条']],
                 minw=560))
    o.append('<p><strong>4.4 辨识需要什么条件。</strong>要把 p = 3 的项辨识出来，参考信号要能激励到足够幅度的三次项：'
             '远端音量长期很小的设备，三次项占比微乎其微，辨识不出来也不需要；远端大音量、喇叭接近过载时占比急剧上升，'
             '这正是 C7 里 ERLE 随过载"悬崖式"下降的机理。因此评测一个非线性 AEC 必须<strong>扫音量</strong>，'
             '并报告 ERLE 随音量变化的曲线，而不是某个固定音量下的单点。</p>')
    o.append(note('这一小节没覆盖的',
                  '没有仿真带记忆的喇叭，也没有实现任何一种上表里的非线性补救，所以<strong>没有"带记忆之后 ERLE 天花板降到多少"的数</strong>。'
                  'C7 的结论（上界贴着 −20log₁₀(非线性占比)）只对无记忆 tanh 成立；带记忆时的占比要在真实喇叭上测 γ²。'
                  '测法：用宽带稳态噪声以多档音量播放，测麦克风与参考的幅度平方相干，在带内取平均。'))
    o.append(q([
        ('神经 RES 比维纳 RES 好，应该怎样报告这个"好"？',
         '在同一近端损伤（同一个近端 SegSNR）上比 ERLE，并分别报告训练分布内与分布外条件；不能各取各的最佳点。'),
        ('为什么"先压低、后确认"比"一过阈值就停"更合适？',
         '前级（能量门）误触发率高，后级（VAD、唤醒、声纹）慢但准。压低可以恢复，停不可以；把两个动作分开，前级可以放宽、后级再收紧，误触发的体感代价小得多。'),
        ('"最大值定阈值"在校准时间翻倍时会怎样？',
         '极值随样本数增大，阈值只升不降（对重尾分布升得更快）。所以校准时长必须与部署时的连续纯回声时长同量级，否则误触发率会在部署时偏高。'),
        ('非线性占比 1% 与 5% 的喇叭，线性 AEC 的 ERLE 上界各约多少？',
         '按无记忆近似 −20log₁₀(占比)：1% → 40 dB，5% → 约 26 dB。带记忆时占比要用相干性在真机上测，不能套这个数。',
         '提示：占比是幅度比，不是功率比。'),
    ]))
    o.append('</section>')

    # ── C12 ───────────────────────────────────────────────────
    o.append(sec('f11', 'C12', '复现与术语', ''))
    o.append('<div class="gl"><dl>'
             '<div class="gitem"><dt>AEC</dt><dd>回声消除。用已知的参考信号辨识回声路径并从麦克风信号里减掉。</dd></div>'
             '<div class="gitem"><dt>ERLE</dt><dd>回声损耗增强。消除前后回声能量比（dB）。只衡量"消了多少"，不衡量"伤了多少"。</dd></div>'
             '<div class="gitem"><dt>失调</dt><dd>滤波器抽头与真实路径的归一化距离（dB）。比 ERLE 更接近"滤波器到底学对了没有"。</dd></div>'
             '<div class="gitem"><dt>NLMS</dt><dd>归一化最小均方。步长 μ 决定收敛与稳态的取舍。</dd></div>'
             '<div class="gitem"><dt>PBFDAF</dt><dd>分区块频域自适应滤波。块长定延迟，分区数定覆盖。</dd></div>'
             '<div class="gitem"><dt>DTD</dt><dd>双讲检测。近端开口时冻结更新，避免滤波器把近端语音当回声去追。</dd></div>'
             '<div class="gitem"><dt>RES</dt><dd>残余抑制。线性消除之后在时频域再压一次，代价是同时压到近端。</dd></div>'
             '<div class="gitem"><dt>双路径</dt><dd>前台输出、后台一直学；后台明显更好时才把权重拷给前台。不需要双讲检测器。</dd></div>'
             '<div class="gitem"><dt>FDKF</dt><dd>频域卡尔曼滤波。每个分区、每个频点一个"自己的步长"，由观测噪声功率自动决定。</dd></div>'
             '<div class="gitem"><dt>GCC-PHAT</dt><dd>相位变换加权的广义互相关，用来估参考与回声之间的延迟。</dd></div>'
             '<div class="gitem"><dt>非唯一性</dt><dd>多路参考相关时，不同的 (h₁, h₂) 给出同一个麦克风信号，滤波器只能辨识出一个组合。</dd></div>'
             '<div class="gitem"><dt>barge-in</dt><dd>打断。设备在播放（TTS）时用户开口。半双工做不到，全双工靠 AEC 做到。</dd></div>'
             '<div class="gitem"><dt>NER</dt><dd>近端相对回声的电平（near-to-echo ratio）。</dd></div>'
             '<div class="gitem"><dt>ppm</dt><dd>百万分之一。晶振的频率偏差单位，10 ppm 在 16 kHz 下每秒错开 0.16 个采样点。</dd></div>'
             '</dl></div>')
    o.append('<div class="note"><span class="tag">复现</span>'
             '<span><b>aeclib.py</b> 滤波器与场景</span> '
             '<span><b>demo_aec_adapt.py</b> C1–C3</span> '
             '<span><b>demo_aec_dtd.py</b> C4</span> '
             '<span><b>demo_aec_drift.py</b> C6</span> '
             '<span><b>demo_aec_res.py</b> C7</span> '
             '<span><b>aecadv.py / demo_aec_dtd2.py</b> C5（双路径、卡尔曼）</span> '
             '<span><b>demo_aec_delay.py</b> C6（延迟估计）</span> '
             '<span><b>demo_aec_multi.py</b> C8</span> '
             '<span><b>demo_aec_duplex.py</b> C9</span> '
             '<span><b>demo_aec_chain.py / demo_aec_joint.py</b> C10</span> '
             '<span><b>figs_fe.py / figs_fe2.py</b> 十一张图</span> '
             '<span><b>fe.js</b> 全部公式</span>'
             '<p>每个 demo 独立运行，各写一个同名 JSON；正文、图与公式里的数都从 JSON 里取。</p></div>')
    o.append('</section>')
    return ''.join(o)
