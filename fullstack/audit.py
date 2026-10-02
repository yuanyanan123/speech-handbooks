#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, json, io, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
h = io.open('fullstack-handbook.html', encoding='utf-8').read()
body = h[h.index('<main>'):h.index('</main>')]
txt = re.sub(r'<[^>]+>', '', re.sub(r'<svg.*?</svg>', '', body, flags=re.S))
bad = []


def chk(ok, what):
    print(('  ✓ ' if ok else '  ✗ ') + what)
    if not ok:
        bad.append(what)


print('── 结构')
for t in ('section', 'h2', 'h3', 'h4', 'figure', 'figcaption', 'table', 'details', 'summary', 'dl', 'div'):
    a, b = len(re.findall(r'<%s[ >]' % t, body)), body.count('</%s>' % t)
    chk(a == b, '<%s> 开闭配对 %d/%d' % (t, a, b))
ids = re.findall(r'<section id="([a-z]\d+)"', body)
links = set(re.findall(r'href="#([a-z]\d+)"', h))
chk(set(ids) == links, '目录与章节一一对应（%d）' % len(ids))
chk(len(re.findall(r'\bid="([^"]+)"', body)) == len(set(re.findall(r'\bid="([^"]+)"', body))), 'id 无重复')
print('── 公式与格式')
K = json.load(open('fs_k.json'))
K.update(json.load(open('fs_k2.json')))
unused = [k for k, v in K.items() if v not in body]
chk(not unused, '所有公式都用上了（%d）' % len(K) + ('' if not unused else ' 未用：%s' % unused))
chk('undefined' not in body and 'NaN' not in body and 'None' not in txt, '无 undefined / NaN / None')
chk(not re.findall(r'%[sdfrg]\b|%%', txt), '无残留格式符')
chk(not re.findall(r'\\(?:frac|sum|begin|mathbf|boldsymbol)\b', txt), '正文无裸 LaTeX')
print('── 图')
svgs = [x for x in re.findall(r'<svg.*?</svg>', body, re.S) if 'class="chart"' in x[:200]]
chk(len(svgs) == 1, '图数 %d' % len(svgs))
chk(not any('<em>' in s or '<strong>' in s or '<br' in s for s in svgs), 'SVG 内无 HTML 标签')
chk(all(len(re.findall(r'<text[ >]', s)) == s.count('</text>') for s in svgs), '<text> 闭合')
chk(not any('var(--hot)' in s and 'var(--s3)' in s for s in svgs), '图未同时用 hot 与 s3')
print('── 排版与声明')
chk(h.startswith('<!doctype html>') and '<meta charset="utf-8">' in h[:300], '有 doctype 与 charset')
chk(h.count('<title>') == 1 and '<title>全栈音频链路手册</title>' in h, '标题正确')
chk(len(re.findall(r'class="qz"', body)) >= 6, '自测块 %d 处' % len(re.findall(r'class="qz"', body)))
cards = body.count('失效时下游看到什么')
chk(cards >= 14, '交接卡 %d 张' % cards)
chk(not re.findall(r'[（(\s]-\d', txt), '负号用 −')
# 每节都有"评价"与"工程"
miss = []
for sid in ids:
    m = re.search(r'<section id="%s">.*?</section>' % sid, body, re.S)
    t = m.group(0)
    if sid in ('u1', 'u14', 'u15', 'u16') or sid == 'g0':
        continue
    if '评价' not in t or '工程问题' not in t and '工程' not in t:
        miss.append(sid)
chk(not miss, '每节都含"评价"与"工程问题"' + ('' if not miss else ' 缺：%s' % miss))
print('── 演进链')
chk(body.count('解决了上一步的什么') >= 10, '方法演进总览表 %d 张' % body.count('解决了上一步的什么'))
print('\n未通过 %d 项' % len(bad))
sys.exit(1 if bad else 0)
