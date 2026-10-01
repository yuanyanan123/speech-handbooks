#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《TTS 合成手册》的自检。"""
import re, json, io, sys

h = io.open('tts-handbook.html', encoding='utf-8').read()
body = h[h.index('<main>'):]
_b = re.sub(r'<svg.*?</svg>', '', body, flags=re.S)
_b = re.sub(r'<pre>.*?</pre>', '', _b, flags=re.S)   # 等宽代码块里用 ASCII 连字符是对的
txt = re.sub(r'<[^>]+>', '', _b)
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
chk(len(caps) >= 12, '图都有图注（%d）' % len(caps))

print('── 3. 公式与格式符 ' + '─' * 43)
chk('undefined' not in body and 'NaN' not in body, '无 undefined / NaN')
stray = re.findall(r'%[sdfrg]\b|%%', txt)
chk(not stray, '正文无残留格式符' + ('' if not stray else ' 出现：%s' % set(stray)))
nd = len(re.findall(r'class="katex-display"', body))
chk(nd >= 32, 'KaTeX 公式块 %d 个' % nd)
raw = re.findall(r'\\(?:frac|sum|underbrace|mathbf|begin|cdot|log|boldsymbol)\b', txt)
chk(not raw, '正文无裸 LaTeX' + ('' if not raw else ' 出现：%s' % set(raw)))
K = json.load(open('tts.json'))
unused = [k for k, v in K.items() if v not in body]
chk(not unused, '所有公式都用上了' + ('' if not unused else ' 未用：%s' % unused))
# 字体：_head.html 只内嵌 Main/Math/Size/Caligraphic
CLS2FONT = {'amsrm': 'KaTeX_AMS', 'mathsf': 'KaTeX_SansSerif',
            'mathtt': 'KaTeX_Typewriter', 'mathcal': 'KaTeX_Caligraphic',
            'mathscr': 'KaTeX_Script', 'mathfrak': 'KaTeX_Fraktur'}
_head = h[:h.index('<main>')]
_need = {f for c, f in CLS2FONT.items() if ('class="mord ' + c) in body
         or ('class="mrel ' + c) in body or ('class="mbin ' + c) in body}
_miss = sorted(f for f in _need if f not in _head)
chk(not _miss, '用到的 KaTeX 字体都内嵌了'
    + ('' if not _miss else ' 缺：%s' % _miss))

print('── 4. 图都嵌进去了 ' + '─' * 43)
F = json.load(open('figs.json'))
F.update(json.load(open('figs_b.json')))
for k, v in F.items():
    chk(v in body, '图 %s 已嵌入' % k)

print('── 5. 数字和脚本对得上 ' + '─' * 39)
TP = json.load(open('demo_temp.json')); CK = json.load(open('demo_chunk.json'))
CL = json.load(open('demo_clone.json')); S = json.load(open('demo_smooth.json'))
ME = json.load(open('demo_mel.json')); EV = json.load(open('demo_eval.json'))
tm = {r['temp']: r for r in TP['temp']}
clr = CL['pairs']['raw']; clc = CL['pairs']['cmn']
ck = {r['chunk']: r for r in CK['chunk']}
NUMS = {
    '%.1f' % S['explain']['dur']: '时长解释的不确定性比例',
    '%.3f' % S['loss']['l2_ct']: 'L2 的谱对比度',
    '%.1f' % tm[0.0]['rep']: '贪心的复读率',
    '%.1f' % TP['temp_best']['temp']: '数据充足模型的最优温度',
    '%.1f' % TP['temp_small_best']['temp']: '数据饥饿模型的最优温度',
    '%.3f' % TP['calib']['small']['conf']: '过自信模型的平均最高概率',
    '%.3f' % TP['calib']['small']['true_p_of_argmax']: '它指的 token 的真实概率',
    '%.1f' % CK['rf']['right_frames']: '声码器右感受野帧数',
    '%.0f' % CK['rf']['right_ms']: '右感受野毫秒数',
    '%.0f' % ck[16]['lat_ms']: 'chunk=16 的首包延迟',
    '%.0f' % ck[4]['overhead']: 'chunk=4 的摊销开销',
    '%.2f' % CK['xfade'][0]['seam']: '不淡入时的包络跳变',
    '%.2f' % clr['eer_naive']: '偷懒协议的 EER',
    '%.2f' % clr['eer_strict']: '严谨协议的 EER',
    '%.2f' % clc['eer_strict']: 'CMN 之后的严谨 EER',
    '%.4f' % clr['room_gap']: '换房间掉多少',
    '%.4f' % clr['spk_gap']: '换人掉多少',
    '%.4f' % CL['inflation']['mean']: '同房间造成的虚高',
    '%.1f' % CL['dur'][0]['eer']: '1 秒参考的 EER',
    '%.1f' % CL['dur'][3]['eer']: '5 秒参考的 EER',
}
for s_, w in NUMS.items():
    s_ = s_.replace('-', '−')
    chk(s_ in txt, '出现「%s」（%s）' % (s_, w))

print('── 6. 排版细节 ' + '─' * 47)
bad_minus = re.findall(r'[（(\s]-\d', txt)
chk(not bad_minus, '负号用 − 而不是 -' + ('' if not bad_minus else ' %d 处' % len(bad_minus)))
chk('姊妹篇' in h, '有姊妹篇链接')
chk(h.count('claude.ai/artifact') >= 4, '四本姊妹篇都链上了')
chk(h.count('<title>') == 1 and 'TTS 合成手册' in h, '标题正确')
chk('麦克风阵列手册</title>' not in h, '外壳标题没留下上一本的痕迹')
nq = len(re.findall(r'class="qz"', body))
chk(nq >= 14, '自测块 %d 处' % nq)

print('\n' + '=' * 62)
print('未通过 %d 项' % len(bad))
sys.exit(1 if bad else 0)
