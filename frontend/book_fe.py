#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新写的两块正文：总纲（放在最前面）与 Part C「参考」——回声消除与全双工。

所有数字都从 demo_aec_*.json 里取，不手抄。节号用 C1…C8，与阵列(A)、单通道(B)两部分各自独立。
"""
from bookfe_util import (K, KI, F, AD, DT, DR, RS, fml, fig, sec, part, table,
                         ex, note, trap, step, why, q, ki)

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


# ══════════════════════════════════════════════════════════════
def build_intro():
    """放在全书最前面：这三部分为什么在一本里。"""
    o = ['<section id="g0"><h2>这本手册怎么读</h2>']
    o.append('<p>一个语音前端手里只有<strong>三种信息</strong>可用：多个麦克风给的<strong>空间</strong>，'
             '一路信号里残存的<strong>统计</strong>规律，以及自己正在播放的那一路<strong>参考</strong>。'
             '这三种信息各有各的上限、各有各的失效方式，<strong>而且互相不能替代</strong>。'
             '这本手册把三部分合在一起，是因为它们在工程里是同一条链路上的三段。</p>')
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
        ['阵列设备上 AEC 该放哪', '<strong>A 部分</strong>的 A14，再读 C7', '波束权重一动，AEC 的上限就掉'],
        ['回声消除"看起来不错"但一说话就坏', 'C 部分的 C4、C6', '双讲检测与残余抑制都在伤近端'],
        ['换了设备或接了蓝牙就消不掉', 'C 部分的 C5', '延迟是悬崖，不是斜坡'],
    ], minw=560))
    o.append(note('编号约定',
                  '三个部分的节号各自从头数：<b>A01</b> 是阵列手册的第 1 节，<b>B01</b> 是单通道手册的第 1 节，'
                  '<b>C1</b> 是回声消除的第 1 节。正文里"第 N 节"指的都是它所在部分的第 N 节。'
                  '阵列和单通道两部分是原样并入的；回声消除与全双工是这一本新写的，实验与图都在 <code>frontend/</code> 目录。'))
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
                  '因为漏检的代价是悬崖，误检的代价是斜坡，宁可多冻。'
                  '按 EER 去定（κ = %g），单讲段 ERLE 要低 <strong>%s dB</strong>。'
                  % (best['kappa'], r1(best['miss']), r1(best['fa']), r0(best['fa'] / best['miss']),
                     eer['kappa'], r2(DT['eer_cost']))))
    hn = DT['hang_note']
    o.append(note('拖尾（hangover）值多少',
                  '检测到近端后再多冻几块。阈值定得紧时它有用：κ = %g、拖尾 %d 块，漏检从 %s%% 降到 %s%%，'
                  'ERLE 好 %s dB。<strong>但阈值本来就合适时拖尾是净损失</strong>——它是补救"阈值没调好"的，不是通用加分项。'
                  % (hn['loose_kappa'], hn['best_hang'], r1(hn['miss0']), r1(hn['missb']), r2(hn['gain']))))
    o.append('</section>')

    # ── C5 ────────────────────────────────────────────────────
    pn = DR['ppm_note']
    ln = DR['len_drift_note']
    dn = DR['delay_note']
    o.append(sec('f5', 'C5', '追不上的那一部分：漂移、延迟与路径变化', '进阶',
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
                  '都是在悄悄推这个数。' % neg(r2(dn['last']))))
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
    o.append(sec('f6', 'C6', '非线性与残余抑制：把 ERLE 当目标，会毁掉近端', '进阶',
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

    # ── C7 ────────────────────────────────────────────────────
    o.append(sec('f7', 'C7', '三段合起来：全双工的预算与翻车点', '深入',
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
         '不冻结比全知差 %s dB' % r2(DT['no_dtd_cost']), '按 EER 定阈值会亏 %s dB' % r2(DT['eer_cost'])],
        ['时钟', '尾部抽头先解相关', '%d ppm 掉 6 dB' % pn['ppm_6db'], '加长滤波器反而更亏'],
        ['整块延迟', '滤波器装不下就是悬崖', '落到 %s dB' % r1(dn['last']), '换设备、接蓝牙时悄悄发生'],
        ['喇叭非线性', '−20·log₁₀(占比)', '%s%% → %s dB' % (r1(nn['worst_thd']), r1(nn['worst_erle'])),
         '线性方法结构上拿不到'],
        ['残余抑制', '近端被一起压', 'ERLE +%s dB ⇔ 近端 −%s dB' % (r1(rn['erle_best'] - RES[0]['erle']),
                                                              r1(RES[0]['near_segsnr'] - rn['q_at_erle'])),
         '把 ERLE 当目标会毁掉近端'],
    ], minw=640))
    o.append(note('三段怎么串',
                  '链路顺序是：<strong>回声消除（C）→ 自适应波束与分离（A）→ 单通道增强（B）</strong>，'
                  'C 在最前。原因在 A14 里算过：波束权重每帧都在变，波束后面的 AEC 要辨识的路径就跟着变，'
                  '指向只动 1°，AEC 的上限就掉到 14.6 dB，动 5° 掉到 5.03 dB。'
                  '所以 AEC 要么在自适应波束<strong>之前</strong>（每路一个，算力 ×M），'
                  '要么让波束固定 / 在远端有声时冻结权重。B 部分的单通道增强放在最后，接手的是线性消除之后留下的残余——'
                  '它与 C6 的 RES 是同一个位置上的两种做法，不要叠着用两遍。'
                  '这段顺序的数字来自 A14，本书没有另外跑 A→C→B 的联合实验。'))
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
        ('DTD 的两种错误率相等是最优点吗？',
         '不是。漏检是阈值型（短于 %s s 几乎免费，长了发散），误检是渐进型，所以应该宁可多冻。'
         '实测最优点漏检 %s%%、误检 %s%%，按 EER 去定要亏 %s dB。'
         % (r1(DT['miss_knee']['free_up_to']), r1(best['miss']), r1(best['fa']), r2(DT['eer_cost']))),
        ('50 ppm 的时钟差下，32 ms 和 256 ms 的滤波器哪个更亏？',
         '256 ms 的：赔 %s dB，而 32 ms 的几乎不受影响（%s dB）。尾部抽头最先解相关。'
         % (r2(ln['long']), r2(ln['short']))),
        ('RES 的 γ 取多大合适？',
         '看拐点，不看 ERLE 最大点。本实验的拐点在 γ = %s：近端代价 %s dB，换 ERLE +%s dB。'
         % (rn['knee_gamma'], r2(RES[0]['near_segsnr'] - rn['knee_q']), r2(rn['knee_erle_gain']))),
    ]))
    o.append('</section>')

    # ── C8 ────────────────────────────────────────────────────
    o.append(sec('f8', 'C8', '复现与术语', ''))
    o.append('<div class="gl"><dl>'
             '<div class="gitem"><dt>AEC</dt><dd>回声消除。用已知的参考信号辨识回声路径并从麦克风信号里减掉。</dd></div>'
             '<div class="gitem"><dt>ERLE</dt><dd>回声损耗增强。消除前后回声能量比（dB）。只衡量"消了多少"，不衡量"伤了多少"。</dd></div>'
             '<div class="gitem"><dt>失调</dt><dd>滤波器抽头与真实路径的归一化距离（dB）。比 ERLE 更接近"滤波器到底学对了没有"。</dd></div>'
             '<div class="gitem"><dt>NLMS</dt><dd>归一化最小均方。步长 μ 决定收敛与稳态的取舍。</dd></div>'
             '<div class="gitem"><dt>PBFDAF</dt><dd>分区块频域自适应滤波。块长定延迟，分区数定覆盖。</dd></div>'
             '<div class="gitem"><dt>DTD</dt><dd>双讲检测。近端开口时冻结更新，避免滤波器把近端语音当回声去追。</dd></div>'
             '<div class="gitem"><dt>RES</dt><dd>残余抑制。线性消除之后在时频域再压一次，代价是同时压到近端。</dd></div>'
             '<div class="gitem"><dt>ppm</dt><dd>百万分之一。晶振的频率偏差单位，10 ppm 在 16 kHz 下每秒错开 0.16 个采样点。</dd></div>'
             '</dl></div>')
    o.append('<div class="note"><span class="tag">复现</span>'
             '<span><b>aeclib.py</b> 滤波器与场景</span> '
             '<span><b>demo_aec_adapt.py</b> C1–C3</span> '
             '<span><b>demo_aec_dtd.py</b> C4</span> '
             '<span><b>demo_aec_drift.py</b> C5</span> '
             '<span><b>demo_aec_res.py</b> C6</span> '
             '<span><b>figs_fe.py</b> 五张图</span> '
             '<span><b>fe.js</b> 全部公式</span>'
             '<p>每个 demo 独立运行，各写一个同名 JSON；正文、图与公式里的数都从 JSON 里取。</p></div>')
    o.append('</section>')
    return ''.join(o)
