# -*- coding: utf-8 -*-
"""《全栈音频链路手册》正文公共件：公式块、图、表、小工具。"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
K = json.load(open(os.path.join(HERE, 'fs_k.json')))
K.update(json.load(open(os.path.join(HERE, 'fs_k2.json'))))
F = json.load(open(os.path.join(HERE, 'figs.json')))


def fml(name, key, where=None):
    w = ''
    if where:
        w = '<div class="where">' + ''.join('<span><b>%s</b>%s</span>' % (a, b) for a, b in where) + '</div>'
    return '<div class="fml"><p class="fml-name">%s</p><div class="fml-body">%s</div>%s</div>' % (name, K[key], w)


def fig(key, cap):
    return '<figure><div class="figbox scrollx">%s</div><figcaption>%s</figcaption></figure>' % (F[key], cap)


def sec(sid, num, title, level='', lede='', tldr=''):
    lv = ('<span class="level %s">%s</span>' % ({'入门': 'a', '进阶': '', '深入': 'b'}[level], level)) if level else ''
    o = ['<section id="%s">' % sid, '<h2><span class="num">%s</span>%s%s</h2>' % (num, title, lv)]
    if lede:
        o.append('<p class="lede">%s</p>' % lede)
    if tldr:
        o.append('<div class="tldr"><span class="tag">一句话版</span><p>%s</p></div>' % tldr)
    return ''.join(o)


def part(pn, title, desc):
    return '<div class="partmark"><span class="pn">%s</span><h2>%s</h2><p class="pd">%s</p></div>' % (pn, title, desc)


def table(head, rows, minw=None):
    st = ' style="min-width:%dpx"' % minw if minw else ''
    o = ['<div class="tw"><table%s><thead><tr>' % st] + ['<th>%s</th>' % h for h in head] + ['</tr></thead><tbody>']
    for r in rows:
        o.append('<tr>' + ''.join('<td>%s</td>' % c for c in r) + '</tr>')
    o.append('</tbody></table></div>')
    return ''.join(o)


def note(tag, body):
    return '<div class="note"><span class="tag">%s</span>%s</div>' % (tag, body)


def trap(tag, body):
    return '<div class="trap"><span class="tag">%s</span>%s</div>' % (tag, body)


def ex(tag, body):
    return '<div class="ex"><span class="tag">%s</span>%s</div>' % (tag, body)


def why(t):
    return '<p class="why">%s</p>' % t


def step(t):
    return '<p class="step q">%s</p>' % t


def q(items):
    o = ['<div class="qz">']
    for i, it in enumerate(items):
        hint = ('<span class="qs">%s</span>' % it[2]) if len(it) > 2 else ''
        o.append('<p class="qq"><span class="qn">%02d</span>%s%s</p>' % (i + 1, it[0], hint))
        o.append('<details><summary>看答案</summary><div class="qa">%s</div></details>' % it[1])
    o.append('</div>')
    return ''.join(o)


def iface(inp, out, assume, fail):
    """每一步末尾的"交接卡"：输入、输出、依赖的假设、失效时下游看到什么。"""
    return table(['交接', '内容'], [['输入', inp], ['输出', out], ['依赖的假设', assume], ['失效时下游看到什么', fail]], minw=520)


def h4(t):
    return '<h4>%s</h4>' % t


def chain(rows):
    """方法演进总览表：方法 | 解决了上一个的什么问题 | 核心假设 | 留下的问题"""
    return table(['方法', '解决了上一步的什么', '核心假设', '留下的问题'], rows, minw=640)
