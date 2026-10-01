#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把《ASR 链路手册》拼起来。"""
import io, re

HEAD = io.open('_head.html', encoding='utf-8').read()
HEAD = HEAD.replace('<title>麦克风阵列手册</title>', '<title>ASR 链路手册</title>')

EXTRA = io.open('_extra_css.txt', encoding='utf-8').read()

# (section id, 显示编号, 目录标题)
TOC = [
    ('导读', [('s0', '—', '怎么读这一页')]),
    ('Ⅰ 基础', [('s1', '01', '声音怎么变成数字'),
               ('s2', '02', '为什么难：五个问题'),
               ('s3', '03', '怎么衡量好坏')]),
    ('Ⅱ 技术脉络', [('s4', '04', '六代地层图'),
                 ('s5', '05', '第一代：GMM-HMM'),
                 ('s6', '06', '第二代：DNN-HMM 混合'),
                 ('s7', '07', '第三代：chain / LF-MMI'),
                 ('s8', '08', '第四代：CTC 与 blank'),
                 ('s9', '09', '第五代：RNN-T 与 Attention'),
                 ('s10', '10', '第六代：预训练与弱监督'),
                 ('s11', '11', '第七代：LLM-ASR')]),
    ('Ⅲ 机制拆解', [('s12', '12', '特征提取：同态解卷积'),
                 ('s13', '13', '决策树与 senone'),
                 ('s14', '14', '帧几何：166 × 3000'),
                 ('s16', '15', '自注意力与 Conformer'),
                 ('s40', '16', '对齐格：路径、格子与剪枝'),
                 ('s41', '17', '序列判别训练的梯度'),
                 ('s18', '18', '强制对齐与发音评测')]),
    ('Ⅳ 解码', [('s15', '19', 'WFST：五件必须知道的事'),
               ('s42', '20', '构图的代价：确定化与消歧符'),
               ('s17', '21', 'beam search 与 lattice'),
               ('s43', '22', '语言模型融合与内部 LM')]),
    ('Ⅴ 工程落地', [('s19', '23', '选型速查'),
                 ('s20', '24', '前端信号处理'),
                 ('s21', '25', 'VAD 与切分'),
                 ('s22', '26', '标点恢复与 ITN'),
                 ('s23', '27', '热词偏置'),
                 ('s24', '28', '幻觉与循环重复'),
                 ('s25', '29', '中文特有的坑'),
                 ('s44', '30', '流式：前瞻、分块与状态'),
                 ('s27', '31', '端侧部署与延迟预算'),
                 ('s45', '32', '说话人日志与重叠下限'),
                 ('s28', '33', '数据与评测'),
                 ('s46', '34', '数据增强：每种做法覆盖哪一块'),
                 ('s47', '35', '说话人与领域自适应'),
                 ('s48', '36', '置信度、校准与拒识'),
                 ('s49', '37', '蒸馏与压缩'),
                 ('s50', '38', '长音频：切在哪里'),
                 ('s29', '39', '生产流水线'),
                 ('s30', '40', '出了问题怎么排查')]),
    ('Ⅵ 前沿', [('s31', '41', '当前的真正难点'),
               ('s32', '42', '研究方向')]),
    ('附录', [('s33', '43', '参数速查'),
             ('s35', '44', '符号约定'),
             ('s36', '45', '特征与统计模型：公式与算例'),
             ('s37', '46', '判别训练与端到端：公式与算例'),
             ('s38', '47', '解码、评测与量化：公式与算例'),
             ('s34', '48', '术语表')]),
]

PARTS = {
    'Ⅰ 基础': ('Part Ⅰ', '基础', '声音是什么、难点在哪、怎么打分'),
    'Ⅱ 技术脉络': ('Part Ⅱ', '技术脉络', '七代方法，每一代解决了上一代的哪个具体问题'),
    'Ⅲ 机制拆解': ('Part Ⅲ', '机制拆解', '把最难的几段拆开：特征、状态绑定、对齐格、判别训练'),
    'Ⅳ 解码': ('Part Ⅳ', '解码', '从一张静态图到一条文字，以及路上所有会犯的错'),
    'Ⅴ 工程落地': ('Part Ⅴ', '工程落地', '决定线上体验的，基本都不是模型本身'),
    'Ⅵ 前沿': ('Part Ⅵ', '前沿', '还没解决的，和正在被解决的'),
    '附录': ('附录', '公式、算例与速查', '每个方法的完整推导，配可复算的数值例子'),
}

MAST = '''<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">从波形到文字 · 七代方法 · 每个数都可复算</p>
    <h1>ASR 链路手册</h1>
    <p class="dek">语音识别是一条六段的链路，每一段坏掉时，错误在最终指标上长得不一样。
    这本书按这条链路排：先讲每一段的模型是怎么来的，再把最难的三段——对齐、构图、解码——拆开，
    最后讲工程。四十八节、十五张自绘图，书里出现的每个数字都由随书脚本算出：
    真造了四级 WFST 并真做了合成与确定化，真写了 CTC 与 RNN-T 的前向后向并与暴力枚举对齐，
    真训了会出现尖峰的 CTC 模型，真扫了 beam、融合权重、前瞻帧数与重叠比例；
    工程篇的 34–38 节在一个能真训的玩具声学世界里量了数据增强、说话人自适应、置信度校准、蒸馏与量化、长音频切分。</p>
    <dl class="specstrip">
      <div class="spec"><dt>CTC 比 RNN-T 多的对齐路径</dt><dd>10<small>^81 倍</small></dd></div>
      <div class="spec"><dt>RNN-T 联合网络一条 30 s</dt><dd>11.6<small>GB</small></dd></div>
      <div class="spec"><dt>99% 后验占据的格子</dt><dd>7.0<small>%</small></dd></div>
      <div class="spec"><dt>beam 1→32 的错误率</dt><dd>变差<small>17.8→19.3%</small></dd></div>
      <div class="spec"><dt>减内部 LM 比加外部 LM</dt><dd>少一半<small>12.5→7.0%</small></dd></div>
      <div class="spec"><dt>最优前瞻</dt><dd>240<small>ms</small></dd></div>
    </dl>
  </header>
</div>
<div class="ruler"></div>
'''

FOOT = '''<footer>
    <p>本页的数字来自九个随书脚本，可复算（前四个是原有的，后五个在 34–38 节）：<b>demo_wfst</b> 真造 G/L/C/H 四级 FST，
    做 ε-滤波合成、输入侧加权确定化（带输出串残留）与划分细化最小化；
    <b>demo_align</b> 手写 CTC 与 RNN-T 的前向后向，与暴力枚举对齐到 1e−15，
    并真训了一个会出现尖峰的 CTC 模型；<b>demo_decode</b> 在一个内部语言模型强度已知（τ=0.55）
    的解析模型上扫 beam 与三种融合；<b>demo_stream</b> 扫前瞻帧数、状态缓存与重叠比例下的 DER；
    <b>demo_aug / demo_adapt / demo_conf / demo_kd / demo_vad</b> 在 <code>toylib.py</code> 的玩具声学世界里真训 9 类帧级音素分类器，
    量数据增强、说话人自适应、置信度校准、蒸馏与权重量化、长音频切分。</p>
    <p>代价要说清楚：这些都是<b>解析构造或小规模合成的模型</b>，不是真实语料上的系统。
    绝对数值不能和 LibriSpeech、AISHELL 上的结果比。
    可比的是形状、量级、拐点的位置和方向——而这本书要讲的恰好是这些。
    WFST 那几节的词表只有几十个词，所以"爆炸"是按比例看的；
    解码那几节的 TER 是字错误率的代理，不是 WER。</p>
    <p>书里有<b>七处</b>我把<b>自己猜错的假说连同否掉它的对照实验一起留着</b>：
    以为 RNN-T 的对齐路径比 CTC 多（反了，CTC 多 10^81 倍），
    按斜率外推得出"按需合成能省几十倍"（也反了，展开倍数根本不随词表涨），
    以及 34–38 节里的五处：全部叠加增强就是最强的、SpecAugment 是通用的鲁棒性手段、没有标注也能靠伪标签自己教自己、
    增强过的模型也会更"知道自己不知道"、蒸馏要仔细调温度和 α。
    34–38 节的玩具声学世界不是语音识别：没有词、没有语言模型、没有解码，只量声学模型这一层。
    留着是因为错误的归因比错误的结论更常见。</p>
    <p>姊妹篇：前端信号处理手册——多通道阵列、单通道增强、回声消除与全双工、唤醒与声纹（原先分开的四本，现在合在一本里）；
    <a href="https://claude.ai/artifact/JoVn5ZfQeMhCGQbfScKuwC">TTS 合成手册</a>
    ——从文字到声音。三本共用同一套记号与算例风格。</p>
  </footer>
'''


SPY = '''
<script>
(function(){
  var links = Array.prototype.slice.call(document.querySelectorAll('nav.toc a'));
  if(!links.length) return;
  var map = {}, targets = [];
  links.forEach(function(a){
    var id = a.getAttribute('href').slice(1);
    var el = document.getElementById(id);
    if(el){ map[id] = a; targets.push(el); }
  });
  function setActive(id){
    links.forEach(function(a){ a.classList.remove('on'); });
    var a = map[id];
    if(a){ a.classList.add('on'); }
  }
  if('IntersectionObserver' in window){
    var visible = {};
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){ visible[e.target.id] = e.isIntersecting; });
      for(var i=0;i<targets.length;i++){
        if(visible[targets[i].id]){ setActive(targets[i].id); return; }
      }
    }, {rootMargin:'-6% 0px -72% 0px', threshold:0});
    targets.forEach(function(t){ io.observe(t); });
  }
  setActive(targets[0].id);
})();
</script>
'''


# 旧章节正文里写死的节号（34–43 整体后移 5 位；两处早就指向附录的旧编号，一并改正）
STALE = [('（37 节 J）', '（47 节 J）'), ('36 节 B2', '46 节 B2')]


# ── 书名交叉引用：阵列、单通道、声纹与唤醒三本已并入《前端信号处理手册》 ──────────
_PART = {'麦克风阵列手册': ('A', 'A 部分（阵列）'), '单通道增强手册': ('B', 'B 部分（单通道）'),
         '声纹与唤醒手册': ('D', 'D 部分（唤醒与声纹）')}


def fix_xref(html, inside=False):
    """inside=True：在前端手册内部，写成 B17 节 / 本书内锚点；False：别的书里指过去，写成"前端手册 B17 节"。"""
    pre = '' if inside else '前端手册 '
    pfx = {'A': 'a', 'B': 'e', 'D': 'k'}
    names = '|'.join(_PART)

    def link(m):
        L, _ = _PART[m.group(1)]
        num = m.group(2)
        if inside and num:
            return '<a href="#%s%s">%s%s 节</a>' % (pfx[L], int(num), L, num)
        return ('%s%s%s 节' % (pre, L, num)) if num else (pre + _PART[m.group(1)][1])
    # 带链接的书名（可后接（NN 节））
    html = re.sub(r'<a href="https://claude\.ai/artifact/[^"]+">(%s)</a>(?:[（(]\s*(\d\d) 节\s*[）)])?' % names, link, html)
    # 书名（NN 节）/《书名》NN 节
    html = re.sub(r'《?(%s)》?\s*[（(]\s*(\d\d) 节\s*[）)]' % names, link, html)
    html = re.sub(r'《(%s)》\s*(\d\d) 节' % names, link, html)
    # 单独的书名
    html = re.sub(r'《?(%s)》?' % names, lambda m: pre + _PART[m.group(1)][1], html)
    return html


def toc_html():
    o = ['<nav class="toc" aria-label="目录"><ol>']
    for part, items in TOC:
        o.append('<li class="part">%s</li>' % part)
        for sid, num, name in items:
            o.append('<li><a href="#%s"><span class="num">%s</span>%s</a></li>'
                     % (sid, num, name))
    o.append('</ol></nav>')
    return ''.join(o)


def fix_text(html):
    parts = re.split(r'(<svg.*?</svg>|<script.*?</script>|<style.*?</style>|<pre>.*?</pre>'
                     r'|<pre><code>.*?</code></pre>)', html, flags=re.S)
    for i in range(0, len(parts), 2):
        seg = re.split(r'(<[^>]*>)', parts[i])
        for j in range(0, len(seg), 2):
            for _ in range(2):
                seg[j] = re.sub(r'(^|[\s（(>])-(?=\d)',
                                lambda m: m.group(1) + '−', seg[j])
        parts[i] = ''.join(seg)
    return ''.join(parts)


def main():
    import secs
    num = {s: n for _, its in TOC for s, n, _ in its}
    reg = secs.build(num)                    # {sid: html}
    miss = [s for _, its in TOC for s, _, _ in its if s not in reg]
    if miss:
        raise SystemExit('缺少：%s' % miss)
    o = []
    for part, items in TOC:
        if part in PARTS:
            pn, t, d = PARTS[part]
            o.append('<div class="partmark"><span class="pn">%s</span><h2>%s</h2>'
                     '<p class="pd">%s</p></div>' % (pn, t, d))
        for sid, num, _ in items:
            o.append(reg[sid])
    body = ''.join(o)
    for a_, b_ in STALE:
        body = body.replace(a_, b_)
    body = fix_xref(fix_text(body))
    html = (HEAD + EXTRA + MAST + '<div class="wrap">\n<div class="cols">\n'
            + toc_html() + '\n<main>\n' + body + FOOT + '\n</main>\n</div>\n</div>\n'
            + SPY)
    io.open('asr-handbook.html', 'w', encoding='utf-8').write(html)
    print('asr-handbook.html  %.1f KB' % (len(html.encode()) / 1024))
    for t in ('section', 'h2', 'figure', 'table', 'details'):
        print('  <%s> %d / </%s> %d' % (t, len(re.findall('<%s[ >]' % t, html)),
                                        t, html.count('</%s>' % t)))


if __name__ == '__main__':
    main()
