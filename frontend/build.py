#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把《前端信号处理手册》拼起来：总纲 + A 空间（阵列）+ B 统计（单通道）+ C 参考（回声与全双工）。

A、B 两部分从 ../array/array-handbook.html 与 ../enh/enh-handbook.html 原样搬来
（只改 id 前缀、节号前缀和 Part 标记，不动正文与图），C 部分与总纲是新写的。
所以要先把 array/、enh/ 各自 build 好。
"""
import io, re, json

HEAD = io.open('_head.html', encoding='utf-8').read()
HEAD = HEAD.replace('<title>麦克风阵列手册</title>', '<title>前端信号处理手册</title>')
EXTRA = io.open('_extra.html', encoding='utf-8').read()

SRC = {
    'A': io.open('../array/array-handbook.html', encoding='utf-8').read(),
    'B': io.open('../enh/enh-handbook.html', encoding='utf-8').read(),
}
PREFIX = {'A': 'a', 'B': 'e'}


def between(h, a, b, start=0):
    i = h.index(a, start)
    j = h.index(b, i)
    return h[i + len(a):j]


def body_of(h):
    """<main> 到它自己的 <footer> 之间的正文。"""
    return between(h, '<main>', '<footer>')


def toc_items(h):
    """[(part_label | None, sid, num, name)]，按出现顺序。"""
    nav = between(h, '<nav class="toc"', '</nav>')
    out = []
    for m in re.finditer(r'<li class="part">(.*?)</li>|<li><a href="#(s\d+)"><span class="num">(.*?)</span>(.*?)</a></li>',
                         nav, flags=re.S):
        if m.group(1) is not None:
            out.append(('part', m.group(1)))
        else:
            out.append(('item', m.group(2), m.group(3), m.group(4)))
    return out


def retag(body, L):
    """id、节号与 Part 标记加前缀。"""
    p = PREFIX[L]
    body = re.sub(r'<section id="s(\d+)"', lambda m: '<section id="%s%s"' % (p, m.group(1)), body)
    # 节标题里的编号：<h2><span class="num">05</span>…
    body = re.sub(r'(<section id="%s\d+">\s*<h2>)<span class="num">(\d+)</span>' % p,
                  lambda m: '%s<span class="num">%s%s</span>' % (m.group(1), L, m.group(2)), body)
    body = re.sub(r'<span class="pn">Part ([^<]+)</span>',
                  lambda m: '<span class="pn">Part %s·%s</span>' % (L, m.group(1)), body)
    body = body.replace('<span class="pn">附录</span>', '<span class="pn">%s 附录</span>' % L)
    return body


def toc_html():
    import book_fe  # noqa: F401  (保证先能 import)
    o = ['<nav class="toc" aria-label="目录"><ol>']
    o.append('<li class="part">导读</li>')
    o.append('<li><a href="#g0"><span class="num">—</span>这本手册怎么读</a></li>')
    for L, title in (('A', 'A 空间 · 阵列'), ('B', 'B 统计 · 单通道')):
        p = PREFIX[L]
        o.append('<li class="part">%s</li>' % title)
        for it in toc_items(SRC[L]):
            if it[0] == 'part':
                o.append('<li class="part sub">%s·%s</li>' % (L, it[1]) if it[1] != '导读' else '')
            else:
                _, sid, num, name = it
                nm = ('%s%s' % (L, num)) if num != '—' else '—'
                o.append('<li><a href="#%s%s"><span class="num">%s</span>%s</a></li>'
                         % (p, sid[1:], nm, name))
    o.append('<li class="part">C 参考 · 回声消除与全双工</li>')
    for sid, num, name in [('f1', 'C1', '回声是辨识问题'), ('f2', 'C2', 'NLMS：快与准的积'),
                           ('f3', 'C3', '分区块：延迟与长度解耦'), ('f4', 'C4', '双讲检测'),
                           ('f5', 'C5', '追不上的那一部分'), ('f6', 'C6', '非线性与残余抑制'),
                           ('f7', 'C7', '三段合起来：预算与翻车点'), ('f8', 'C8', '复现与术语')]:
        o.append('<li><a href="#%s"><span class="num">%s</span>%s</a></li>' % (sid, num, name))
    o.append('</ol></nav>')
    return ''.join(o)


def mast(body):
    import book_fe as B
    nsec = len(re.findall(r'<section id=', body))
    nfig = len(re.findall(r'<figure>', body))
    return '''<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">空间 · 统计 · 参考 · 一个前端手里的三种信息</p>
    <h1>前端信号处理手册</h1>
    <p class="dek">多个麦克风给空间，一路信号里残存统计，自己播的声音是参考。三种信息各有各的上限、各有各的失效方式，互相不能替代。这本手册把阵列、单通道增强、回声消除与全双工放在一起，因为它们在工程里是同一条链路上的三段。全书 %d 节、%d 张自绘图，每个数字都由随书脚本算出，可以自己复算。</p>
    <dl class="specstrip">
      <div class="spec"><dt>阵列 DAS 增益上限</dt><dd>10log<small>M</small></dd></div>
      <div class="spec"><dt>音乐噪声的理论零点</dt><dd>5.57<small>dB</small></dd></div>
      <div class="spec"><dt>回声消除对时钟差的容忍</dt><dd>%d<small>ppm 掉 6 dB</small></dd></div>
      <div class="spec"><dt>滤波器装不下路径时</dt><dd>%s<small>dB</small></dd></div>
      <div class="spec"><dt>把 ERLE 推到最高，近端掉</dt><dd>%s<small>dB</small></dd></div>
      <div class="spec"><dt>漏检的代价是误检的</dt><dd>%d<small>倍</small></dd></div>
    </dl>
  </header>
</div>
<div class="ruler"></div>
''' % (nsec, nfig, B.DR['ppm_note']['ppm_6db'], ('%.1f' % B.DR['delay_note']['last']).replace('-', '−'),
       '%.2f' % (B.RES[0]['near_segsnr'] - B.RS['res_note']['q_at_erle']), B.DT['asym']['ratio'])


FOOT = '''<footer>
    <p>本页所有数字都由随书脚本计算生成，可复算。A、B 两部分（阵列、单通道增强）是两本独立手册的原文并入，
    其实验与脚本在 <code>array/</code>、<code>enh/</code>；C 部分（回声消除与全双工）的实验在 <code>frontend/demo_aec_*.py</code>。</p>
    <p>C 部分的信号全是合成的：回声路径是指数衰减的随机冲激响应（不是某个真实房间的实测），
    远端语音沿用单通道那本的源-滤波合成语音，近端同理。
    所以<b>绝对数值不能直接和公开数据集或真机上的结果比</b>，可比的是形状、量级和趋势——
    而这一部分要讲的恰好是形状：快与准的积、阈值型与渐进型的代价、悬崖与斜坡。
    喇叭非线性用的是一个 tanh 软限幅，真实喇叭有记忆效应，上界会更低。</p>
    <p>C 部分里<b>三处</b>我把自己猜错的假说连同否掉它的对照实验一起留着：
    双讲检测的阈值按"两种错误相等"去定、滤波器加长总能覆盖时钟漂移、ERLE 越高越好。
    回声消除放在自适应波束之前的数字来自 A14，本书没有另外跑 A→C→B 的联合实验。</p>
        <p>姊妹篇：<a href="https://claude.ai/artifact/NL7s2XicLUVjGk8uq4jXvw">ASR 链路手册</a>
    ——语音识别的七代脉络；
    <a href="https://claude.ai/artifact/JoVn5ZfQeMhCGQbfScKuwC">TTS 合成手册</a>
    ——从文字到声音；
    <a href="https://claude.ai/artifact/WMzwGqiwAy6vi8MrLwJpgg">声纹与唤醒手册</a>
    ——说话人确认与关键词唤醒。</p>
  </footer>
'''


def fix_text(html):
    parts = re.split(r'(<svg.*?</svg>|<script.*?</script>|<style.*?</style>|<pre>.*?</pre>)',
                     html, flags=re.S)
    for i in range(0, len(parts), 2):
        seg = re.split(r'(<[^>]*>)', parts[i])
        for j in range(0, len(seg), 2):
            seg[j] = re.sub(r'(^|[\s（(>])-(?=\d)', lambda m: m.group(1) + '−', seg[j])
            seg[j] = re.sub(r'(^|[\s（(>])-(?=\d)', lambda m: m.group(1) + '−', seg[j])
        parts[i] = ''.join(seg)
    return ''.join(parts)


def array_scripts():
    """阵列那一半的交互（图表数据 + 脚本），原样搬来。"""
    h = SRC['A']
    i = h.index('<script id="chart-data"')
    j = h.rindex('</script>') + len('</script>')
    return h[i:j]


def main():
    import book_fe
    a = retag(body_of(SRC['A']), 'A')
    b = retag(body_of(SRC['B']), 'B')
    body = (fix_text(book_fe.build_intro()) + a + b + fix_text(book_fe.build_echo()))
    ids = re.findall(r'\bid="([^"]+)"', body)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise SystemExit('重复的 id：%s' % dup)
    html = (HEAD + EXTRA + mast(body) + '<div class="wrap">\n<div class="cols">\n'
            + toc_html() + '\n<main>\n' + body + FOOT + '\n</main>\n</div>\n</div>\n'
            + array_scripts() + '\n')
    io.open('frontend-handbook.html', 'w', encoding='utf-8').write(html)
    print('frontend-handbook.html  %.1f KB' % (len(html.encode()) / 1024))
    for t in ('section', 'h2', 'figure', 'table'):
        print('  <%s> %d / </%s> %d' % (t, len(re.findall('<%s[ >]' % t, html)), t, html.count('</%s>' % t)))


if __name__ == '__main__':
    main()
