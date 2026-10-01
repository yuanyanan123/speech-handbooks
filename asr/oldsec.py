#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从旧版 asr-handbook 里取出正文段落，重新编号后复用。"""
import io, re

_RAW = io.open('old.html', encoding='utf-8').read()
_IDX = {}
_m = list(re.finditer(r'<section id="(s\d+)"[^>]*>', _RAW))
for _k, _mm in enumerate(_m):
    _end = _RAW.find('</section>', _mm.end())
    _IDX[_mm.group(1)] = _RAW[_mm.end():_end]

LEVEL = {'入门': 'a', '进阶': '', '深入': 'b'}


def raw(sid):
    return _IDX[sid]


def head(sid):
    """返回 (标题, 难度)"""
    h = re.search(r'<h2>(.*?)</h2>', _IDX[sid], re.S).group(1)
    lv = re.search(r'<span class="level[^"]*">(.*?)</span>', h)
    t = re.sub(r'<span class="num">.*?</span>', '', h)
    t = re.sub(r'<span class="level[^"]*">.*?</span>', '', t).strip()
    return t, (lv.group(1) if lv else '')


def body(sid):
    """去掉 h2 之后的正文"""
    b = _IDX[sid]
    return b[re.search(r'</h2>', b).end():]


def old(sid, num, title=None, level=None, lede=None, patch=None, append=''):
    """按新编号重新发一节。patch = [(旧串, 新串), ...]"""
    t0, l0 = head(sid)
    t = title or t0
    lv = l0 if level is None else level
    bd = body(sid)
    for a, b in (patch or []):
        if a not in bd:
            raise KeyError('%s: 补丁没匹配上 %r' % (sid, a[:60]))
        bd = bd.replace(a, b, 1)
    lvh = ('<span class="level %s">%s</span>' % (LEVEL[lv], lv)) if lv else ''
    o = ['<section id="%s">' % sid,
         '<h2><span class="num">%s</span>%s%s</h2>' % (num, t, lvh)]
    if lede:
        o.append('<p class="lede">%s</p>' % lede)
    o.append(bd)
    o.append(append)
    o.append('</section>')
    return ''.join(o)
