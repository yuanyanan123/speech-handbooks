#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正文生成的公共件：公式块、图、表、小工具。"""
import json

K = json.load(open('tts.json'))
KI = json.load(open('tts_inline.json'))
F = json.load(open('figs.json'))
F.update(json.load(open('figs_b.json')))
G = json.load(open('demo_g2p.json'))
S = json.load(open('demo_smooth.json'))
ME = json.load(open('demo_mel.json'))
AL = json.load(open('demo_align.json'))
FL = json.load(open('demo_flow.json'))
RQ = json.load(open('demo_rvq.json'))
VO = json.load(open('demo_voc.json'))
EV = json.load(open('demo_eval.json'))
TP = json.load(open('demo_temp.json'))
CK = json.load(open('demo_chunk.json'))
CL = json.load(open('demo_clone.json'))


def fml(name, key, where=None):
    w = ''
    if where:
        w = '<div class="where">' + ''.join(
            '<span><b>%s</b>%s</span>' % (a, b) for a, b in where) + '</div>'
    return ('<div class="fml"><p class="fml-name">%s</p><div class="fml-body">%s</div>%s</div>'
            % (name, K[key], w))


def fig(key, cap):
    return ('<figure><div class="figbox scrollx">%s</div><figcaption>%s</figcaption></figure>'
            % (F[key], cap))


def sec(sid, num, title, level='', lede='', tldr=''):
    lv = ('<span class="level %s">%s</span>'
          % ({'入门': 'a', '进阶': '', '深入': 'b'}[level], level)) if level else ''
    o = ['<section id="%s">' % sid,
         '<h2><span class="num">%s</span>%s%s</h2>' % (num, title, lv)]
    if lede:
        o.append('<p class="lede">%s</p>' % lede)
    if tldr:
        o.append('<div class="tldr"><span class="tag">一句话版</span><p>%s</p></div>' % tldr)
    return ''.join(o)


def part(pn, title, desc):
    return ('<div class="partmark"><span class="pn">%s</span><h2>%s</h2>'
            '<p class="pd">%s</p></div>' % (pn, title, desc))


def table(head, rows, cls='', minw=None):
    st = ' style="min-width:%dpx"' % minw if minw else ''
    o = ['<div class="tw %s"><table%s><thead><tr>' % (cls, st)]
    for h in head:
        c = ' class="num"' if h.startswith('#') else ''
        o.append('<th%s>%s</th>' % (c, h.lstrip('#')))
    o.append('</tr></thead><tbody>')
    for r in rows:
        o.append('<tr>' + ''.join(
            '<td%s>%s</td>' % (' class="num"' if str(c).startswith('#') else '',
                               str(c).lstrip('#')) for c in r) + '</tr>')
    o.append('</tbody></table></div>')
    return ''.join(o)


def ex(tag, body):
    return '<div class="ex"><span class="tag">%s</span>%s</div>' % (tag, body)


def note(tag, body):
    return '<div class="note"><span class="tag">%s</span>%s</div>' % (tag, body)


def trap(tag, body):
    return '<div class="trap"><span class="tag">%s</span>%s</div>' % (tag, body)


def step(t):
    return '<p class="step q">%s</p>' % t


def why(t):
    return '<p class="why">%s</p>' % t


def code(cap, body):
    return '<div class="code"><p class="cap">%s</p><pre>%s</pre></div>' % (cap, body)


def q(items):
    """自测题：题干 + 折叠答案。items = [(题干, 答案, 提示?)]"""
    o = ['<div class="qz">']
    for i, it in enumerate(items):
        qq, qa = it[0], it[1]
        hint = ('<span class="qs">%s</span>' % it[2]) if len(it) > 2 else ''
        o.append('<p class="qq"><span class="qn">%02d</span>%s%s</p>' % (i + 1, qq, hint))
        o.append('<details><summary>看答案</summary><div class="qa">%s</div></details>' % qa)
    o.append('</div>')
    return ''.join(o)
