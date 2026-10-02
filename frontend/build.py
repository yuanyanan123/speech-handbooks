#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把《前端信号处理手册》拼起来：
总纲 + A 空间（阵列）+ B 统计（单通道）+ C 参考（回声消除与全双工）+ D 入口（唤醒与声纹）。

A、B、D 三部分各自是一本能独立 build 的手册（array/、enh/、sv/），这里从它们的成品原样搬来，
只改 id 前缀、节号前缀和 Part 标记，不动正文与图；总纲与 C 部分是新写的（aec/）。
所以要先把 enh/、sv/ 各自 build 好（array/ 的 HTML 本身就是源）。
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, os.path.join(HERE, 'aec'))

HEAD = io.open('_head.html', encoding='utf-8').read()
HEAD = HEAD.replace('<title>麦克风阵列手册</title>', '<title>前端信号处理手册</title>')
EXTRA = io.open('_extra.html', encoding='utf-8').read()

# 字母、id 前缀、成品、Part 标题（目录里的）
PARTS = [
    ('A', 'a', 'array/array-handbook.html', 'A 空间 · 阵列'),
    ('B', 'e', 'enh/enh-handbook.html', 'B 统计 · 单通道'),
    ('D', 'k', 'sv/sv-handbook.html', 'D 入口 · 唤醒与声纹'),
]
SRC = {L: io.open(f, encoding='utf-8').read() for L, _, f, _ in PARTS}
PREFIX = {L: p for L, p, _, _ in PARTS}


def between(h, a, b, start=0):
    i = h.index(a, start)
    j = h.index(b, i)
    return h[i + len(a):j]


def body_of(h):
    """<main> 到它自己的 <footer> 之间的正文。"""
    return between(h, '<main>', '<footer>')


def toc_items(h):
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
    body = re.sub(r'href="#s(\d+)"', lambda m: 'href="#%s%s"' % (p, m.group(1)), body)   # 部分内的交叉引用
    body = re.sub(r'(<section id="%s\d+">\s*<h2>)<span class="num">(\d+)</span>' % p,
                  lambda m: '%s<span class="num">%s%s</span>' % (m.group(1), L, m.group(2)), body)
    body = re.sub(r'<span class="pn">Part ([^<]+)</span>',
                  lambda m: '<span class="pn">Part %s·%s</span>' % (L, m.group(1)), body)
    body = body.replace('<span class="pn">附录</span>', '<span class="pn">%s 附录</span>' % L)
    return body


def toc_html():
    import book_fe
    o = ['<nav class="toc" aria-label="目录"><ol>',
         '<li class="part">导读</li>',
         '<li><a href="#g0"><span class="num">—</span>这本手册怎么读</a></li>']

    def part_a_b_d(L):
        p, title = PREFIX[L], [t for l, _, _, t in PARTS if l == L][0]
        o.append('<li class="part">%s</li>' % title)
        for it in toc_items(SRC[L]):
            if it[0] == 'part':
                if it[1] != '导读':
                    o.append('<li class="part sub">%s·%s</li>' % (L, it[1]))
            else:
                _, sid, num, name = it
                nm = ('%s%s' % (L, num)) if num != '—' else '—'
                o.append('<li><a href="#%s%s"><span class="num">%s</span>%s</a></li>' % (p, sid[1:], nm, name))

    part_a_b_d('A')
    part_a_b_d('B')
    o.append('<li class="part">C 参考 · 回声消除与全双工</li>')
    for sid, num, name in book_fe.TOC_C:
        o.append('<li><a href="#%s"><span class="num">%s</span>%s</a></li>' % (sid, num, name))
    part_a_b_d('D')
    import extra_e
    o.append('<li class="part">E 补遗 · 链路两端与相邻问题</li>')
    for sid, num, name in extra_e.TOC_E:
        o.append('<li><a href="#%s"><span class="num">%s</span>%s</a></li>' % (sid, num, name))
    o.append('</ol></nav>')
    return ''.join(o)


def mast(body):
    import book_fe as B
    nsec = len(re.findall(r'<section id=', body))
    nfig = len(re.findall(r'<figure>', body))
    return '''<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">空间 · 统计 · 参考 · 入口 · 一个前端手里的信息与它的出口</p>
    <h1>前端信号处理手册</h1>
    <p class="dek">多个麦克风给空间，一路信号里残存统计，自己播的声音是参考。三种信息各有各的上限、各有各的失效方式，互相不能替代。处理完之后，信号要过两道门：唤醒决定要不要开口，声纹决定是谁在说。这本手册把阵列、单通道增强、回声消除与全双工、唤醒与声纹放在一起，因为它们在工程里是同一条链路。全书 %d 节、%d 张自绘图，每个数字都由随书脚本算出，可以自己复算。</p>
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
    <p>本页所有数字都由随书脚本计算生成，可复算。A、B、D 三部分（阵列、单通道增强、唤醒与声纹）是三本独立手册的原文并入，
    其实验与脚本在 <code>array/</code>、<code>enh/</code>、<code>sv/</code>；C 部分（回声消除与全双工）的实验在 <code>aec/demo_aec_*.py</code>。</p>
    <p>C 部分的信号全是合成的：回声路径是指数衰减的随机冲激响应（不是某个真实房间的实测），
    远端语音沿用单通道那本的源-滤波合成语音，近端同理。
    所以<b>绝对数值不能直接和公开数据集或真机上的结果比</b>，可比的是形状、量级和趋势——
    而这一部分要讲的恰好是形状：快与准的积、阈值型与渐进型的代价、悬崖与斜坡。
    喇叭非线性用的是一个 tanh 软限幅，真实喇叭有记忆效应，上界会更低。</p>
    <p>C 部分里<b>九处</b>我把自己猜错的假说连同否掉它的对照实验一起留着：
    双讲检测的阈值按"两种错误相等"去定、"最优"的在线 DTD 其实只是几乎不再学习、相干性检测比能量比好、
    滤波器加长总能覆盖时钟漂移、ERLE 越高越好、取最早的显著峰去估延迟、半波整流足以给立体声参考去相关、
    ERLE 每高 10 dB 能听见的近端就轻 10 dB、自适应波束一定比固定波束好。
    阵列、AEC、RES、NS 四段在 C10 里按六种顺序真的串起来跑过（一种房间、一个近端方向、弥散噪声，没有方向性干扰）。</p>
    <p>C11 是理论补篇：神经方法、打断与唤醒/声纹的联动、回声尖峰的来源、带记忆的喇叭非线性——这四块<b>没有做实验</b>，只给定义、推导与评测规范，不含任何实测数字。</p>
    <p>E 部分（补遗）同样<b>没有实验</b>：麦克风硬件指标、增益控制、啸叫与风噪、丢包补偿与带宽扩展、多通道端到端、神经 AEC，只写机理、定义与评测规范。</p>
        <p>姊妹篇：<a href="https://claude.ai/artifact/NL7s2XicLUVjGk8uq4jXvw">ASR 链路手册</a>
    ——语音识别的七代脉络；
    <a href="https://claude.ai/artifact/JoVn5ZfQeMhCGQbfScKuwC">TTS 合成手册</a>
    ——从文字到声音。</p>
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


def array_scripts():
    """阵列那一半的交互（图表数据 + 脚本），原样搬来。"""
    h = SRC['A']
    i = h.index('<script id="chart-data"')
    j = h.rindex('</script>') + len('</script>')
    return h[i:j]


def main():
    import book_fe, extra_e
    a = retag(body_of(SRC['A']), 'A')
    b = retag(body_of(SRC['B']), 'B')
    d = retag(body_of(SRC['D']), 'D')
    body = fix_text(book_fe.build_intro()) + fix_xref(a + b, True) + fix_text(book_fe.build_echo()) + '<!--part-D-->' + fix_xref(d, True) + '<!--part-E-->' + fix_text(extra_e.build_extra())
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
