#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《ASR 链路手册》的自检。"""
import re, json, io, sys

h = io.open('asr-handbook.html', encoding='utf-8').read()
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
chk(len(caps) >= 15, '图都有图注（%d）' % len(caps))

print('── 3. 公式与格式符 ' + '─' * 43)
chk('undefined' not in body and 'NaN' not in body, '无 undefined / NaN')
stray = re.findall(r'%[sdfrg]\b|%%', txt)
chk(not stray, '正文无残留格式符' + ('' if not stray else ' 出现：%s' % set(stray)))
nd = len(re.findall(r'class="katex-display"', body))
chk(nd >= 24, 'KaTeX 公式块 %d 个' % nd)
raw = re.findall(r'\\(?:frac|sum|underbrace|mathbf|begin|cdot|log|boldsymbol)\b', txt)
chk(not raw, '正文无裸 LaTeX' + ('' if not raw else ' 出现：%s' % set(raw)))
K = json.load(open('asr_k.json'))
unused = [k for k, v in K.items() if v not in body]
chk(not unused, '所有公式都用上了' + ('' if not unused else ' 未用：%s' % unused))
# 字体：_head.html 只内嵌 Main/Math/Size/Caligraphic
chk('amsrm' not in body and 'mathsf' not in body and 'mathtt' not in body,
    '未使用缺失字体的字形（AMS / SansSerif / Typewriter）')

print('── 4. 图都嵌进去了 ' + '─' * 43)
F = json.load(open('figs_a.json'))
F.update(json.load(open('figs_b.json')))
F.update(json.load(open('figs_c.json')))
for k, v in F.items():
    chk(v in body, '图 %s 已嵌入' % k)

print('── 5. 数字和脚本对得上 ' + '─' * 39)
WF = json.load(open('demo_wfst.json')); AL = json.load(open('demo_align.json'))
DE = json.load(open('demo_decode.json')); ST = json.load(open('demo_stream.json'))
cnt, mem, oc = AL['count'][-1], AL['mem'][-1], AL['occupancy']
opt = {r['tag']: r for r in WF['opt']}
b = ST['look_best']; ca = ST['cache']
dia3 = [r for r in ST['dia'] if r['overlap'] == 0.3][0]
AG = json.load(open('demo_aug.json')); AP = json.load(open('demo_adapt.json')); CF = json.load(open('demo_conf.json'))
KD = json.load(open('demo_kd.json')); VD = json.load(open('demo_vad.json'))
NUMS = {
    '%.0f' % AG['note']['clean_white10']: '只用干净数据在白噪 10 dB 下的准确率',
    '%.0f' % AG['note']['noise_white10']: '加噪之后',
    '%.0f' % AG['note']['noise_babble10']: '没见过的 babble',
    '%.1f' % AG['note']['allcmvn_unseen']: '增强加 CMVN 在没见过条件上的平均',
    '%.0f' % AP['note']['all_3']: '3 秒全部微调',
    '%.0f' % AP['note']['first_3']: '3 秒只调第一层',
    '%.0f' % AP['note']['forget_all_3']: '全部微调后源域',
    '%.0f' % CF['note']['w10_acc']: '白噪 10 dB 准确率',
    '%.0f' % CF['note']['w10_conf']: '白噪 10 dB 置信度',
    '%.2f' % CF['note']['w10_auc']: '白噪 10 dB 的 AUROC',
    '%.0f' % KD['note']['kdu32_babble']: '教师打标的无标注增强数据后的学生',
    '%.1f' % KD['note']['q4_pc']: '教师 int4 按通道',
    '%.1f' % VD['note']['fix10_pct']: '10 s 固定切块的切断率',
    '%.2f' % VD['note']['isl_max_s']: '最长语音岛',

    '%.0f' % AL['count_gap']: 'CTC 与 RNN-T 的路径数量级差',
    '%.1f' % cnt['ctc_log10']: 'CTC 的路径数指数',
    '%.1f' % cnt['rnnt_log10']: 'RNN-T 的路径数指数',
    '%.1f' % (mem['rnnt_mb'] / 1000): 'RNN-T 一条 30 s 的显存',
    '%.0f' % AL['mem_note']['batch16_gb']: 'batch=16 的显存',
    '%.1f' % (oc['q0.99'] * 100): '99%% 占据度需要的格子比例',
    '%.1f' % (oc['q0.5'] * 100): '一半占据度需要的格子比例',
    '%.1f' % (AL['prune_ok']['frac'] * 100): '固定带宽要的格子比例',
    '%.2f' % AL['ctc_train']['peak_width']: 'CTC 尖峰宽度',
    '%.0f' % (AL['ctc_train']['blank_frac'] * 100): 'CTC 输出 blank 的帧占比',
    '%s' % '{:,}'.format(WF['disambig']['arcs']): '带消歧符的 L∘G 边数',
    '%s' % '{:,}'.format(WF['nodisambig']['cap']): '不加消歧符的中止规模',
    '%.0f' % opt['L∘G']['det_pct']: 'L∘G 确定化后的相对规模',
    '%.0f' % opt['C∘L∘G']['min_pct']: 'C∘L∘G 最小化后的相对规模',
    '%.1f' % WF['peak']['ratio']: '构图峰值与最终图之比',
    '%.2f' % DE['ref_score']: '参考答案自己的得分',
    '%.2f' % DE['fusion']['none']: '不融合的 TER',
    '%.2f' % DE['fusion']['shallow']: '浅融合最好的 TER',
    '%.2f' % DE['fusion']['ilme']: 'ILME 的 TER',
    '%.1f' % DE['oracle_gap']: 'oracle 与 top-1 的差距',
    '%.0f' % b['lat_ms']: '最优前瞻的毫秒数',
    '%.2f' % b['ter']: '最优前瞻的 TER',
    '%.2f' % ca[2]['total_mb']: 'chunk=16 的单路缓存',
    '%.0f' % ST['cache_100']: '100 路并发的缓存',
    '%.2f' % dia3['der']: '30%% 重叠的 DER',
    '%.2f' % dia3['floor']: '30%% 重叠的漏检下限',
    '%.2f' % ST['dia2'][-1]['gain']: '多标签拿回的点数',
}
for s_, w in NUMS.items():
    s_ = s_.replace('-', '−')
    chk(s_ in txt, '出现「%s」（%s）' % (s_, w))

print('── 6. 排版细节 ' + '─' * 47)
bad_minus = re.findall(r'[（(\s]-\d', txt)
chk(not bad_minus, '负号用 − 而不是 -' + ('' if not bad_minus else ' %d 处' % len(bad_minus)))
chk('姊妹篇' in h, '有姊妹篇链接')
chk(h.count('claude.ai/artifact') >= 4, '四本姊妹篇都链上了')
chk(h.count('<title>') == 1 and 'ASR 链路手册' in h, '标题正确')
chk('麦克风阵列手册</title>' not in h, '外壳标题没留下上一本的痕迹')
nq = len(re.findall(r'class="qz"', body))
chk(nq >= 7, '自测块 %d 处' % nq)

print('\n' + '=' * 62)
print('未通过 %d 项' % len(bad))
sys.exit(1 if bad else 0)
