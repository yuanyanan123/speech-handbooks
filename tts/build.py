#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把《TTS 合成手册》拼起来。外壳（字体、KaTeX、CSS）沿用阵列手册，
   正文由 book1.py / book2.py 生成。"""
import json, io, re

HEAD = io.open('_head.html', encoding='utf-8').read()
HEAD = HEAD.replace('<title>麦克风阵列手册</title>', '<title>TTS 合成手册</title>')

# 补两个阵列手册没有、但这本要用的类
EXTRA = '''
<style>
.dp{min-width:0;font-family:var(--f-mono);font-variant-numeric:tabular-nums;font-size:12.5px}
.dp td,.dp th{padding:6px 11px;text-align:center}
.dp td:first-child,.dp th:first-child{text-align:left;color:var(--text-3)}
.dp .best{background:var(--accent-soft);color:var(--accent);font-weight:600}
.matrix table{min-width:640px;font-size:12.5px}
.matrix td,.matrix th{padding:7px 10px}
.matrix thead th{font-size:10px;text-align:center;line-height:1.3;white-space:normal;min-width:54px}
.matrix thead th:first-child{text-align:left;min-width:150px}
.matrix td.m{text-align:center;font-size:13px}
.matrix .yes{color:var(--hot)}
.matrix .no{color:var(--text-3);opacity:.5}
.matrix .part-y{color:var(--accent)}
.matrix tbody td:first-child{white-space:nowrap}
.matrix .era{font-family:var(--f-mono);font-size:10.5px;color:var(--text-3);display:block;font-weight:400}
.paths{display:grid;grid-template-columns:repeat(auto-fill,minmax(92px,1fr));gap:5px;margin:12px 0 14px;
       font-family:var(--f-mono);font-size:12.5px}
.paths span{background:var(--surface-2);border:1px solid var(--border);border-radius:3px;
            padding:3px 6px;text-align:center;letter-spacing:.06em}
.paths span.k{background:var(--accent-soft);color:var(--accent)}
</style>
'''

TOC = [
    ('导读', [('s0', '—', '怎么读这一页')]),
    ('Ⅰ 根本问题', [('s1', '01', 'TTS 与 ASR 的不对称'), ('s2', '02', '一句话有多少种读法'),
                 ('s3', '03', '怎么衡量好坏')]),
    ('Ⅱ 前端', [('s4', '04', '文本归一化 TN'), ('s5', '05', '中文 G2P 与多音字'),
              ('s6', '06', '变调、儿化、轻声'), ('s7', '07', '韵律与停顿'),
              ('s8', '08', '建模单元怎么选')]),
    ('Ⅲ 技术脉络', [('s9', '09', '七代地层图'), ('s10', '10', '拼接与参数合成'),
                 ('s11', '11', 'Tacotron 与注意力'), ('s12', '12', 'FastSpeech 与显式时长'),
                 ('s13', '13', 'VITS 与端到端'), ('s14', '14', '扩散与流匹配'),
                 ('s15', '15', 'LLM-TTS')]),
    ('Ⅳ 机制拆解', [('s16', '16', '梅尔谱丢了什么'), ('s17', '17', '时长与对齐'),
                 ('s18', '18', '声码器'), ('s19', '19', '音频 tokenizer'),
                 ('s20', '20', '零样本克隆'), ('s21', '21', '采样与多样性')]),
    ('Ⅴ 工程落地', [('s22', '22', '流式与首包延迟'), ('s23', '23', '端侧与算力'),
                 ('s24', '24', '选型速查'), ('s25', '25', '七个翻车点'),
                 ('s26', '26', '评测方法'), ('s27', '27', '数据与标注'),
                 ('s28', '28', '安全、伪造与水印')]),
    ('Ⅵ 难点与趋势', [('s29', '29', '当前的真正难点'), ('s30', '30', '技术趋势')]),
    ('附录', [('s31', '31', '公式、算例与自测'), ('s32', '32', '术语表')]),
]


def toc_html():
    o = ['<nav class="toc" aria-label="目录"><ol>']
    for part, items in TOC:
        o.append('<li class="part">%s</li>' % part)
        for sid, num, name in items:
            o.append('<li><a href="#%s"><span class="num">%s</span>%s</a></li>' % (sid, num, name))
    o.append('</ol></nav>')
    return ''.join(o)


MAST = '''<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">从文字到声音 · 七代技术脉络 · 每个数都可复算</p>
    <h1>TTS 合成手册</h1>
    <p class="dek">语音合成难在哪：同一句话有无数种合法读法，而损失函数只能给出一个答案。
    这本手册沿着这条主线走完七代技术——每一代把"一对多"往后推了一步，代价是什么。
    全书三十三节、十二张自绘图，每个数字都由随书脚本算出，可以自己复算：
    真训了两个自回归模型去量温度、真搭了一个 HiFi-GAN 形状的声码器去实测感受野、
    真造了一批"说话人 × 房间 × 内容"去量相似度协议差多少。</p>
    <dl class="specstrip">
      <div class="spec"><dt>采样率</dt><dd>22.05<small>kHz</small></dd></div>
      <div class="spec"><dt>帧长 / 帧移</dt><dd>46<small>/</small>11.6<small>ms</small></dd></div>
      <div class="spec"><dt>梅尔维数</dt><dd>80<small>维</small></dd></div>
      <div class="spec"><dt>时长解释的不确定性</dt><dd>91.5<small>%</small></dd></div>
      <div class="spec"><dt>贪心解码的复读率</dt><dd>100<small>%</small></dd></div>
      <div class="spec"><dt>声码器右感受野</dt><dd>55<small>ms</small></dd></div>
      <div class="spec"><dt>换个评测协议</dt><dd>29<small>倍 EER</small></dd></div>
    </dl>
  </header>
</div>
<div class="ruler"></div>
'''

FOOT = '''<footer>
    <p>本页所有数字——多音字统计、方差分解、梅尔谱的谐波分辨率、Griffin-Lim 收敛、
    MAS 边界误差、扩散与流匹配的步数-误差曲线、RVQ 码率阶梯、混叠与棋盘伪影、
    听测功效、HiFi-GAN 的乘加数、采样温度的两种失效模式、
    流式声码器的感受野与块边界、克隆相似度的协议差异——都由随书脚本计算生成，可复算。</p>
    <p>语音信号由源-滤波模型合成，基频、共振峰轨迹与音素边界是已知真值；
    这样"对齐准不准"、"梅尔谱丢了多少"才有客观答案，代价是它不是真录音，
    绝对数值不能直接和真实语料上的结果比——可比的是形状和量级。
    听测那一节的方差参数是<em>假设</em>，来自公开听测里常见的量级；
    给定那组假设之后，功效计算本身是精确的。</p>
    <p>书里有<b>四处我把自己猜错的假说连同否掉它的对照实验一起留着</b>：
    以为过自信的模型需要更低的采样温度（实测最优温度反而挪高了）、
    以为 top-p 是比降温更便宜的旋钮（截尾和降温是同一件事）、
    以为一阶统计量的说话人嵌入会被房间盖过（实测房间只有说话人的四分之一）、
    以为倒谱均值归一化是靠消掉房间起作用（实测是靠放大说话人差异）。
    留着是因为错误的归因比错误的结论更常见。</p>
    <p>姊妹篇：<a href="https://claude.ai/artifact/NL7s2XicLUVjGk8uq4jXvw">ASR 链路手册</a>
    ——语音识别从 GMM-HMM 到 LLM-ASR 的七代脉络；
    <a href="https://claude.ai/artifact/JkNwTFLFyfWYejCCzykVLQ">麦克风阵列手册</a>
    ——从物理上限到工程落地。三本共用同一套记号与算例风格。</p>
  </footer>
'''


def fix_text(html):
    """只在文本节点里做排版修正：ASCII 负号 → 真负号；不碰标签、svg、script、style。"""
    parts = re.split(r'(<svg.*?</svg>|<script.*?</script>|<style.*?</style>|<pre>.*?</pre>)',
                     html, flags=re.S)
    for i in range(0, len(parts), 2):
        seg = re.split(r'(<[^>]*>)', parts[i])
        for j in range(0, len(seg), 2):
            seg[j] = re.sub(r'(^|[\s（(>])-(?=\d)', lambda m: m.group(1) + '−', seg[j])
            seg[j] = re.sub(r'(^|[\s（(>])-(?=\d)', lambda m: m.group(1) + '−', seg[j])
        parts[i] = ''.join(seg)
    return ''.join(parts)


def main():
    import book1, book2
    body = fix_text(book1.build() + book2.build())
    html = (HEAD + EXTRA + MAST + '<div class="wrap">\n<div class="cols">\n'
            + toc_html() + '\n<main>\n' + body + FOOT + '\n</main>\n</div>\n</div>\n')
    io.open('tts-handbook.html', 'w', encoding='utf-8').write(html)
    print('tts-handbook.html  %.1f KB' % (len(html.encode()) / 1024))
    # 粗查
    for t in ('section', 'h2', 'figure', 'table'):
        print('  <%s> %d / </%s> %d' % (t, len(re.findall('<%s[ >]' % t, html)),
                                        t, html.count('</%s>' % t)))


if __name__ == '__main__':
    main()
