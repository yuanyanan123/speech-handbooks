#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《声纹与唤醒手册》的自检。"""
import re, json, io, sys

h = io.open('enh-handbook.html', encoding='utf-8').read()
body = h[h.index('<main>'):]
txt = re.sub(r'<[^>]+>', '', re.sub(r'<svg.*?</svg>', '', body, flags=re.S))
bad = []


def chk(ok, what):
    print(('  ✓ ' if ok else '  ✗ ') + what)
    if not ok:
        bad.append(what)


print('── 1. 结构 ' + '─' * 50)
for t in ('section', 'h2', 'h3', 'h4', 'figure', 'figcaption', 'table', 'details',
          'summary', 'dl', 'pre'):
    a = len(re.findall(r'<%s[ >]' % t, body))
    b = body.count('</%s>' % t)
    chk(a == b, '<%s> 开闭配对 %d/%d' % (t, a, b))
ids = re.findall(r'<section id="(s\d+)"', body)
chk(len(ids) == len(set(ids)), 'section id 无重复（%d 个）' % len(ids))
links = set(re.findall(r'href="#(s\d+)"', h))
chk(links <= set(ids), '目录链接都有对应 section'
    + ('' if links <= set(ids) else ' 缺：%s' % (links - set(ids))))
chk(set(ids) <= links, '每个 section 都在目录里'
    + ('' if set(ids) <= links else ' 漏：%s' % (set(ids) - links)))

print('── 2. SVG ' + '─' * 51)
svgs = re.findall(r'<svg[^>]*>', body)
chk(len(svgs) == body.count('</svg>'), 'svg 开闭配对（%d 个）' % len(svgs))
inner = re.findall(r'<svg.*?</svg>', body, re.S)
chk(not any('<em>' in s or '<strong>' in s or '<br' in s or '<sup>' in s for s in inner),
    'SVG 内无 HTML 标签（em/strong/br/sup）')
for s_ in inner:
    n = len(re.findall(r'<text[ >]', s_)), s_.count('</text>')
    if n[0] != n[1]:
        lab = re.search(r'aria-label="([^"]{0,20})', s_)
        chk(False, 'SVG <text> 未闭合：%s %s' % (lab.group(1) if lab else '?', n))
        break
else:
    chk(True, '每张图的 <text> 都闭合')
mk = re.findall(r'<marker id="([^"]+)"', body)
chk(len(mk) == len(set(mk)), 'marker id 无重复（%d 个）' % len(mk))
refs = set(re.findall(r'url\(#([^)]+)\)', body))
allid = set(mk) | set(re.findall(r'id="([^"]+)"', body))
chk(refs <= allid, '所有 url(#id) 都有定义'
    + ('' if refs <= allid else ' 缺：%s' % (refs - allid)))
rg = []
for s_ in inner:
    b_ = re.sub(r'<defs>.*?</defs>', '', s_, flags=re.S)
    if ('var(--hot)' in b_ or 'ar-h' in b_ or 'bx-h' in b_) and 'var(--s3)' in b_:
        lab = re.search(r'aria-label="([^"]{0,24})', s_)
        rg.append(lab.group(1) if lab else '?')
chk(not rg, '无图同时用 --hot 与 --s3 作数据标记'
    + ('' if not rg else ' 违规：%s' % rg))
caps = re.findall(r'<figcaption>(.*?)</figcaption>', body, re.S)
badcap = [c[:20] for c in caps if any(t in c for t in ('<h3', '<table', '<figure', '<section'))]
chk(not badcap, 'figcaption 内无块级内容' + ('' if not badcap else ' 违规：%s' % badcap))
chk(len(caps) == 14, '十四张图都有图注（%d）' % len(caps))

print('── 3. 公式与格式符 ' + '─' * 43)
chk('undefined' not in body and 'NaN' not in body, '无 undefined / NaN')
stray = re.findall(r'%[sdfrg]\b|%%', txt)
chk(not stray, '正文无残留格式符' + ('' if not stray else ' 出现：%s' % set(stray)))
nd = len(re.findall(r'class="katex-display"', body))
chk(nd >= 18, 'KaTeX 公式块 %d 个' % nd)
raw = re.findall(r'\\(?:frac|sum|underbrace|mathbf|begin|cdot|log|boldsymbol)\b', txt)
chk(not raw, '正文无裸 LaTeX' + ('' if not raw else ' 出现：%s' % set(raw)))
K = json.load(open('enh_k.json'))
unused = [k for k, v in K.items() if v not in body]
chk(not unused, '所有公式都用上了' + ('' if not unused else ' 未用：%s' % unused))
# 字体：_head.html 只内嵌 Main/Math/Size/Caligraphic
chk('amsrm' not in body and 'mathsf' not in body and 'mathtt' not in body,
    '未使用缺失字体的字形（AMS / SansSerif / Typewriter）')

print('── 4. 图都嵌进去了 ' + '─' * 43)
F = json.load(open('figs_a.json'))
F.update(json.load(open('figs_b.json')))
for k, v in F.items():
    chk(v in body, '图 %s 已嵌入' % k)

print('── 5. 数字和脚本对得上 ' + '─' * 39)
GA = json.load(open('demo_gain.json')); DD = json.load(open('demo_dd.json'))
PH = json.load(open('demo_phase.json')); NN = json.load(open('demo_nn.json'))
EV = json.load(open('demo_eval.json'))
M5 = {r['tag']: r for r in GA['main']['5']}
MK = {r['snr']: r for r in PH['mask']}
NUMS = {
    '%.2f' % GA['mus_floor']: '音乐噪声的理论零点',
    '%.2f' % M5['带噪（不处理）']['mus']: '实测带噪的残差起伏',
    '%.2f' % M5['谱减（α=1，无谱底）']['mus']: '谱减的残差起伏',
    '%.2f' % M5['log-MMSE']['mus']: 'log-MMSE 的残差起伏',
    '%g' % GA['oversub_best']: '过减的总误差最小点',
    '%.0f' % GA['sig']['pr_db']: '完美重构误差',
    '%.2f' % DD['capture']['0.98']['thr_db']: 'α=0.98 的捕获阈值',
    '%.2f' % DD['capture']['0.9']['thr_db']: 'α=0.9 的捕获阈值',
    '%.0f' % DD['step']['ms_delay_ms']: 'MS 的追踪延迟',
    '%.0f' % DD['step']['mcra_delay_ms']: 'MCRA 的追踪延迟',
    '%.2f' % DD['est_cost']: '噪声估计在平稳噪声上的代价',
    '%.2f' % MK[0.0]['phase_worth']: '相位在 0 dB 时的价值',
    '%.2f' % PH['overlap_gain']: '重叠率带来的相位收益',
    '%.1f' % PH['resolve']['need_ms']: '分辨基频谐波需要的窗长',
    '%g' % PH['best_win']['babble']: '非平稳噪声的最优窗长',
    '%g' % PH['tiers'][0]['best_win_ms']: '耳机档可用窗长',
    '%+.2f' % NN['gap_seen']: '神经网络在见过噪声上的领先',
    '%+.2f' % NN['gap_unseen']: '神经网络在没见过噪声上的领先',
    '%.2f' % NN['cost']['mmac_s']: '网络算力',
    '%.2f' % NN['cost']['mw50']: '网络功耗',
    '{:,}'.format(NN['data']['frames']): '训练帧数',
    '%.2f' % NN['diversity'][0]['unseen']['segsnr']: '1 种训练噪声的泛化',
    '%.2f' % NN['diversity'][-1]['unseen']['segsnr']: '3 种训练噪声的泛化',
    '%d' % EV['max_spread']['n']: '名次跨度',
    '%.2f' % EV['asv_clean']: '干净语音的 EER 下限',
    '%+.3f' % EV['corr']['SI-SDR']: 'SI-SDR 与下游的相关系数',
}
for s_, w in NUMS.items():
    s_ = s_.replace('-', '−')
    chk(s_ in txt, '出现「%s」（%s）' % (s_, w))

print('── 6. 排版细节 ' + '─' * 47)
bad_minus = re.findall(r'[（(\s]-\d', txt)
chk(not bad_minus, '负号用 − 而不是 -' + ('' if not bad_minus else ' %d 处' % len(bad_minus)))
chk('姊妹篇' in h, '有姊妹篇链接')
chk(h.count('claude.ai/artifact') >= 4, '四本姊妹篇都链上了')
chk(h.count('<title>') == 1 and '声纹与唤醒手册' in h, '标题正确')
chk('声纹与唤醒手册' not in h[:h.index('<main>')], '外壳标题没留下上一本的痕迹')
nq = len(re.findall(r'class="qz"', body))
chk(nq >= 8, '自测块 %d 处' % nq)

print('\n' + '=' * 62)
print('未通过 %d 项' % len(bad))
sys.exit(1 if bad else 0)
