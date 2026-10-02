#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内联 SVG 图的公共件：配色与几个画线、画网格的小函数。"""
import numpy as np

C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
HOT = 'var(--hot)'
T3, T2 = 'var(--text-3)', 'var(--text-2)'


def svg(w, h, o, label, cls='chart'):
    return (f'<svg viewBox="0 0 {w} {h}" class="{cls}" role="img" aria-label="{label}">'
            + ''.join(o) + '</svg>')


def foot(o, H, lines, y0=None, dy=18):
    y0 = y0 or (H - 18 - (len(lines) - 1) * dy)
    o.append(f'<line x1="14" y1="{y0-20}" x2="686" y2="{y0-20}" class="grid"/>')
    for i, (t, c) in enumerate(lines):
        t = t.replace('<b>', '<tspan font-weight="600">').replace('</b>', '</tspan>')
        cc = f' fill="{c}"' if c else ''
        o.append(f'<text x="14" y="{y0+i*dy}" class="arlab"{cc}>{t}</text>')


def ygrid(o, X, W, vals, f2y, fmt='%g', suf=''):
    for v in vals:
        y = f2y(v)
        o.append(f'<line x1="{X}" y1="{y:.1f}" x2="{X+W}" y2="{y:.1f}" class="grid"/>')
        s = (fmt % v)
        if s.startswith('-'):
            s = '−' + s[1:]
        o.append(f'<text x="{X-5}" y="{y+3.5:.1f}" class="ctick" text-anchor="end">'
                 f'{s}{suf}</text>')


def poly(o, pts, col, w=2.2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    o.append('<polyline points="' + ' '.join('%.1f,%.1f' % p for p in pts)
             + f'" fill="none" stroke="{col}" stroke-width="{w}"{d}/>')


def neg(s):
    return ('−' + s[1:]) if s.startswith('-') else s




def spread(ys, gap=12.0):
    """把一列标签的 y 坐标拉开，互相至少隔 gap，尽量不离原位。返回与输入同序的新 y。"""
    idx = sorted(range(len(ys)), key=lambda i: ys[i])
    out = [ys[i] for i in idx]
    for _ in range(50):
        moved = False
        for k in range(1, len(out)):
            d = out[k] - out[k - 1]
            if d < gap - 1e-6:
                s = (gap - d) / 2
                out[k - 1] -= s
                out[k] += s
                moved = True
        if not moved:
            break
    res = [0.0] * len(ys)
    for k, i in enumerate(idx):
        res[i] = out[k]
    return res
