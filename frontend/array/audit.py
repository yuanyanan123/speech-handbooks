#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""严格审查：结构、编号、交叉引用、术语、数字一致性。"""
import io, re, json, sys

h = io.open('array-handbook.html', encoding='utf-8').read()
b = h.rfind('</style>')
body = h[b:]
txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body))
bad = []

def chk(cond, msg):
    print(('  ✓ ' if cond else '  ✗ ') + msg)
    if not cond: bad.append(msg)

print('── 1. 章节编号与目录一致性 ' + '─' * 34)
secs = re.findall(r'<section id="s(\d+)">', body)
nums = re.findall(r'<h2><span class="num">(\d+)</span>([^<]*)', body)
toc = re.findall(r'<li><a href="#s(\d+)"><span class="num">(\d+)</span>([^<]*)', body)
chk([int(x) for x in secs] == list(range(0, 33)), 'section id 连续 s0–s32（实际 %s…%s，共 %d）'
    % (secs[0], secs[-1], len(secs)))
chk(all(int(a) == int(b_) for a, b_ in zip([s for s in secs[1:]], [n[0] for n in nums])),
    'h2 编号与 section id 对齐')
chk(len(toc) == 32, '目录条目 32 条（实际 %d）' % len(toc))
mis = [(a, b_) for a, b_, _ in toc if int(a) != int(b_)]
chk(not mis, '目录 href 与显示编号一致' + ('' if not mis else ' 不一致：%s' % mis))
tocmap = {int(a): c.strip() for a, b_, c in toc}
h2map = {int(a): c.strip() for a, c in nums}
print('     目录 vs 标题：')
for k in sorted(tocmap):
    if k in h2map:
        t, t2 = tocmap[k], h2map[k]
        mark = '  ' if (t in t2 or t2 in t or t[:4] == t2[:4]) else ' ⚠'
        if mark == ' ⚠':
            print('    %s %2d  目录「%s」  标题「%s」' % (mark, k, t, t2))
print('     （只列出不一致项，无输出 = 全部一致）')

print('── 2. 正文交叉引用是否指向存在的章节 ' + '─' * 24)
refs = sorted(set(int(x) for x in re.findall(r'(?<![\d.])(\d{1,2})\s*节', txt)))
oob = [r for r in refs if r < 1 or r > 32]
chk(not oob, '所有「NN 节」引用落在 1–32 内' + ('' if not oob else ' 越界：%s' % oob))
print('     被引用的章节：%s' % refs)

print('── 3. 数字与验算脚本一致 ' + '─' * 36)
NUMS = {
    '141 Hz': 'HOA N=1 WNG 起点', '694 Hz': 'N=2', '1428 Hz': 'N=3', '2256 Hz': 'N=4',
    '1300 Hz': 'N=1 混叠上限', '2600 Hz': 'N=2', '3899 Hz': 'N=3', '5199 Hz': 'N=4',
    '6.02 dB': '一阶 DI', '9.54 dB': '二阶 DI', '12.04 dB': '三阶 DI', '13.98 dB': '四阶 DI',
    '765': 'ITD 低频极限', '510': 'ITD 高频极限', '762': 'ITD 歧义起点',
    '1960': 'ILD 分界', '655.8': 'ITD 最大值', '0.3 dB': '250Hz ILD',
    '17.76': '刚性球 N=2 4kHz', '10.31': '干扰输入 ILD',
    '1.4 秒': '1ppm 相位预算', '0.527': '球面测度算例', '3.3196': 'Q 两种定义一致', '1.46 m': '高心形 r_c', '0.322': '漏 sinθ 的错值', '25 kHz 掉到 8 kHz': '亥姆霍兹算例',
    '63.9999999473': 'Uzkov M=8 极限', '4.78515625': '边射上界 M=8', '−85.4 dB': '超指向 100Hz WNG', '20.00 / 40.00 / 60.01': 'WNG 斜率拟合', '2.4×10⁻⁴': '最优方向图比对', '1.71': '2° 预算工作点', '0.001800': '失配协方差核对', '0.29°': '无加载 1dB 失配', '−8.03 dB': '最差 5% 机器', '2012 Hz': 'Zelinski 失效边界', '118.4 dB': '音乐噪声峰谷差', '0.288': 'K=1 增益标准差', '1.9933': '互谱模型核对', '0.8859': '主瓣常数', '0.486': '半波长判据', '3.254': 'kL=6 各 M 一致', '11.715327': 'BAN 恒等式', '34.97': '目标抵消 3°+20dB', '34.1 dB': '加载救回',
    '19.98': 'AEC 0.5° ERLE 上限', '14.60': 'AEC 1° 上限',
    '5.70': 'AEC 跳变后实测', '33.67': 'AEC 波束固定稳态',
    '7.66': 'WPE 最优工作点', '4.14': 'WPE 输入起跑线',
    '−23.7': 'WPE Δ=0 毁信号', '3.52': 'WPE 净收益',
}
for s, why in NUMS.items():
    chk(s in txt, '出现「%s」（%s）' % (s, why))

print('── 4. 新增 SVG 的完整性 ' + '─' * 37)
F2 = json.load(open('figs2.json')); F3 = json.load(open('figs3.json'))
F4 = json.load(open('figs4.json')); F5 = json.load(open('figs5.json'))
F6 = json.load(open('figs6.json')); F7 = json.load(open('figs7.json')); F8 = json.load(open('figs8.json')); F9 = json.load(open('figs9.json')); FA = json.load(open('figs10.json')); FB = json.load(open('figs11.json'))
FF = json.load(open('figs15.json')); FG = json.load(open('figs16.json'))
FH = json.load(open('figs17.json')); FI = json.load(open('figs18.json'))
for k, v in list(F2.items()) + list(F3.items()) + list(F4.items()) + list(F5.items()) + list(F6.items()) + list(F7.items()) + list(F8.items()) + list(F9.items()) + list(FA.items()) + list(FB.items()) + list(FF.items()) + list(FG.items()) + list(FH.items()) + list(FI.items()):
    chk(v in body, '图 %s 已嵌入' % k)
svgs = re.findall(r'<svg[^>]*>', body)
chk(len(svgs) == body.count('</svg>'), 'svg 开闭标签配对（%d 个）' % len(svgs))
ids = re.findall(r'<marker id="([^"]+)"', body)
chk(len(ids) == len(set(ids)), 'marker id 无重复（%d 个）' % len(ids))
refs_m = set(re.findall(r'url\(#([^)]+)\)', body))
miss = refs_m - set(ids) - set(re.findall(r'id="([^"]+)"', body))
chk(not miss, '所有 url(#id) 都有定义' + ('' if not miss else ' 缺：%s' % miss))

print('── 4b. 配色：图表里不得出现红绿同现（CVD）' + '─' * 17)
inner_svgs = re.findall(r'<svg.*?</svg>', body, re.S)
rg = []
for s_ in inner_svgs:
    b_ = re.sub(r'<defs>.*?</defs>', '', s_, flags=re.S)
    has_hot = ('var(--hot)' in b_) or ('ar-h' in b_) or ('bx-h' in b_)
    if has_hot and 'var(--s3)' in b_:
        lab = re.search(r'aria-label="([^"]{0,28})', s_)
        rg.append(lab.group(1) if lab else '?')
chk(not rg, '无图同时用 --hot 与 --s3 作数据标记' + ('' if not rg else ' 违规：%s' % rg))
cat4 = []
for s_ in inner_svgs:
    b_ = re.sub(r'<defs>.*?</defs>', '', s_, flags=re.S)
    n = sum(1 for t in ('s1','s2','s3','hot') if 'var(--%s)' % t in b_)
    if n > 3:
        lab = re.search(r'aria-label="([^"]{0,28})', s_)
        cat4.append((lab.group(1) if lab else '?', n))
caps = re.findall(r'<figcaption>(.*?)</figcaption>', body, re.S)
badcap = []
for cp in caps:
    for t in ('<h3', '<table', '<figure', '<div class="fml"', '<div class="tw"', '<section'):
        if t in cp: badcap.append((t, re.sub(r'<[^>]+>', '', cp)[:24]))
chk(not badcap, 'figcaption 内无块级内容' + ('' if not badcap else ' 发现：%s' % badcap[:3]))
chk(not cat4, '分类色不超过三种' + ('' if not cat4 else ' 超限：%s' % cat4))

print('── 5. HTML 结构 ' + '─' * 45)
for tag in ['section', 'figure', 'figcaption', 'table', 'div', 'p', 'h2', 'h3', 'pre', 'details', 'summary']:
    o = len(re.findall(r'<%s\b' % tag, body)); c = body.count('</%s>' % tag)
    chk(o == c, '<%s> 开闭配对 %d/%d' % (tag, o, c))
chk('<em>' not in ''.join(svgs), 'SVG 内无 <em>')
inner = re.findall(r'<svg.*?</svg>', body, re.S)
badtag = set()
for s_ in inner:
    badtag |= set(re.findall(r'<(?!/?(?:svg|defs|marker|path|rect|text|tspan|line|circle|ellipse|polygon|polyline|g|use|clipPath|title|desc)\b)([a-zA-Z]+)', s_))
chk(not badtag, 'SVG 内无非法标签' + ('' if not badtag else ' 发现：%s' % badtag))

print('── 6. 公式渲染（KaTeX 是否有漏网的裸 LaTeX）' + '─' * 18)
leaks = re.findall(r'\\[a-zA-Z]{2,}(?![^<]*</annotation>)', txt)
leaks = [x for x in leaks if x not in (r'\times',)]
chk(not leaks, '正文无裸 LaTeX 命令' + ('' if not leaks else ' 发现：%s' % set(leaks[:10])))
chk('katex-display' in body, 'KaTeX display 块存在（%d 个）' % body.count('katex-display'))
chk('undefined' not in txt and 'NaN' not in txt, '无 undefined / NaN')

print('── 7. 术语表与附录是否覆盖新章 ' + '─' * 30)
gl = body[body.find('<section id="s32">'):]
for t in ['球谐', 'Ambisonics', 'ITD', 'ILD', 'RTF', 'BAN', '模态强度', 'MWF-N', 'BLCMV', '刚性球']:
    chk(t in gl, '术语表含「%s」' % t)

print('\n' + '=' * 62)
print('未通过 %d 项' % len(bad))
for x in bad: print('  ·', x)
sys.exit(1 if bad else 0)
