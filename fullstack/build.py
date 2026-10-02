#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拼《全栈音频链路手册》。先 node fs.js 渲染公式、python figs.py 生成图。"""
import io, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)

HEAD = io.open('_head.html', encoding='utf-8').read().replace('<title>麦克风阵列手册</title>', '<title>全栈音频链路手册</title>')
EXTRA = io.open('_extra.html', encoding='utf-8').read()
SPY = io.open('spy.html', encoding='utf-8').read()

TOC = [
    ('导读', [('g0', '—', '这本手册怎么读')]),
    ('Ⅰ 观测模型', [('u1', '01', '观测模型与数据形状：一段数据的一生')]),
    ('Ⅱ 前端', [('u2', '02', '阵列：用空间信息拆开目标与干扰'), ('u3', '03', '回声消除：用已知的参考把自己的声音减掉'),
              ('u4', '04', '单通道增强：只剩一路信号时，还能拆什么'), ('u5', '05', '前端的其余模块：去混响、增益、VAD、唤醒与声纹')]),
    ('Ⅲ 识别', [('u6', '06', '特征提取：从波形到梅尔对数谱'), ('u7', '07', '识别建模：从 HMM 到端到端'),
               ('u8', '08', '解码与语言模型：声学分数之外的东西')]),
    ('Ⅳ 理解与回复', [('u9', '09', '文本中枢：理解、回复与交给合成的方式')]),
    ('Ⅴ 合成', [('u10', '10', '文本前端：规范化、发音与韵律'), ('u11', '11', '声学模型：从音素到梅尔谱，以及"一对多"'),
               ('u12', '12', '声码器与神经编解码：从梅尔谱回到波形'), ('u13', '13', '合成的评价、流式与安全')]),
    ('Ⅵ 合起来', [('u14', '14', '闭环与全链路架构：参考、延迟、状态机'), ('u15', '15', '评测体系与排障：从症状找到环节'),
                ('u16', '16', '索引：每一节去哪看细节')]),
]


def toc_html():
    o = ['<nav class="toc" aria-label="目录"><ol>']
    for part, items in TOC:
        o.append('<li class="part">%s</li>' % part)
        for sid, num, name in items:
            o.append('<li><a href="#%s"><span class="num">%s</span>%s</a></li>' % (sid, num, name))
    o.append('</ol></nav>')
    return ''.join(o)


def fix_text(html):
    parts = re.split(r'(<svg.*?</svg>|<script.*?</script>|<style.*?</style>|<pre>.*?</pre>)', html, flags=re.S)
    for i in range(0, len(parts), 2):
        seg = re.split(r'(<[^>]*>)', parts[i])
        for j in range(0, len(seg), 2):
            for _ in range(2):
                seg[j] = re.sub(r'(^|[\s（(>])-(?=\d)', lambda m: m.group(1) + '−', seg[j])
        parts[i] = ''.join(seg)
    return ''.join(parts)


def mast(body):
    nsec = len(re.findall(r'<section id=', body)) - 1
    return '''<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">阵列 · 单通道 · ASR · TTS · 一条闭环的链路</p>
    <h1>全栈音频链路手册</h1>
    <p class="dek">从一组多通道语音出发，走过阵列、回声消除、单通道增强、特征、识别、解码、理解、合成、声码器，再回到麦克风。
    每一步按同一个顺序写：原理与推导、方法演进（从最早的方法一路讲到最先进的做法）、先进方法、评价、工程问题、与上下游的交接卡。
    全书 %d 节、一张总架构图、一百多个公式；没有实验，不含实测数字，出现的数字都是算术或定义。
    要看实验与数字，每节末尾指向前端、ASR、TTS 三本详细手册。</p>
    <dl class="specstrip">
      <div class="spec"><dt>3 秒 × 4 麦 × 16 kHz 的 STFT</dt><dd>4×257×186<small>复数</small></dd></div>
      <div class="spec"><dt>ASR 特征</dt><dd>298×80<small>对数梅尔</small></dd></div>
      <div class="spec"><dt>编码器下采样 4 倍后</dt><dd>75<small>帧 × 40 ms</small></dd></div>
      <div class="spec"><dt>NLMS 快与准的积</dt><dd>≈ L/(2−μ)²<small>与 μ 无关</small></dd></div>
      <div class="spec"><dt>8 码本 × 1024 × 75 Hz</dt><dd>6000<small>bit/s</small></dd></div>
      <div class="spec"><dt>链路是</dt><dd>闭环<small>输出回到输入</small></dd></div>
    </dl>
  </header>
</div>
<div class="ruler"></div>
''' % nsec


FOOT = '''<footer>
    <p>这一本是总览：把前端、识别、合成三个方向串成一条闭环的链路，并给出每一步的核心推导。<b>没有任何实验，不含实测数字。</b>
    出现的数字只有两类：算术（帧数、形状、码率）与定义。每一节"去哪看细节"指向前端信号处理手册、ASR 链路手册、TTS 合成手册，
    那里的实验数字来自随书脚本，并明确了"合成信号与小模型"的适用范围。</p>
    <p>关于正确性：推导与结论按领域通行的表述写成，没有逐条对照文献核对；关键论断请在使用前自行查证，
    尤其是各节"先进方法"里对具体方法优缺点的概括。</p>
  </footer>
'''


def splice(body):
    """把"方法演进"插到各节的"先进方法"之前（没有就插在"评价"之前）。"""
    import evo_a, evo_b, evo_c
    EVO = {'u2': evo_a.evo_u2, 'u3': evo_a.evo_u3, 'u4': evo_a.evo_u4, 'u5': evo_a.evo_u5,
           'u6': evo_b.evo_u6, 'u7': evo_b.evo_u7, 'u8': evo_b.evo_u8,
           'u10': evo_c.evo_u10, 'u11': evo_c.evo_u11, 'u12': evo_c.evo_u12}
    for sid, fn in EVO.items():
        a = body.index('<section id="%s">' % sid)
        b = body.index('</section>', a)
        sec = body[a:b]
        for mk in ('<h3>先进方法</h3>', '<h3>评价与工程问题</h3>', '<h3>评价</h3>'):
            if mk in sec:
                i = sec.index(mk)
                break
        else:
            raise SystemExit('找不到插入点：%s' % sid)
        sec = sec[:i] + fn() + sec[i:]
        body = body[:a] + sec + body[b:]
    return body.replace('<h3>先进方法</h3>', '<h3>先进方法（演进链的终点与相邻方向）</h3>')


def main():
    import book_a, book_b, book_c
    body = fix_text(splice(book_a.build_a() + book_b.build_b() + book_c.build_c()))
    ids = re.findall(r'\bid="([^"]+)"', body)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise SystemExit('重复的 id：%s' % dup)
    html = ('<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
            + HEAD + EXTRA + mast(body) + '<div class="wrap">\n<div class="cols">\n' + toc_html() + '\n<main>\n' + body + FOOT
            + '\n</main>\n</div>\n</div>\n' + SPY)
    io.open('fullstack-handbook.html', 'w', encoding='utf-8').write(html)
    print('fullstack-handbook.html  %.1f KB' % (len(html.encode()) / 1024))
    for t in ('section', 'h2', 'h3', 'figure', 'table'):
        print('  <%s> %d / </%s> %d' % (t, len(re.findall('<%s[ >]' % t, html)), t, html.count('</%s>' % t)))


if __name__ == '__main__':
    main()
