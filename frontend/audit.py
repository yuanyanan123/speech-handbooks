#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《前端信号处理手册》的自检：总纲与 C 部分是新写的，A、B 两部分是并入的，所以还要核对"原样"。"""
import re, json, io, sys

h = io.open('frontend-handbook.html', encoding='utf-8').read()
body = h[h.index('<main>'):h.index('</main>')]
newpart = re.search(r'<section id="g0">.*?</section>', body, re.S).group(0) + body[body.index('<section id="f1">'):]
txt = re.sub(r'<[^>]+>', '', re.sub(r'<svg.*?</svg>', '', newpart, flags=re.S))
bad = []


def chk(ok, what):
    print(('  ✓ ' if ok else '  ✗ ') + what)
    if not ok:
        bad.append(what)


print('── 1. 结构 ' + '─' * 50)
for t in ('section', 'h2', 'h3', 'h4', 'figure', 'figcaption', 'table', 'details', 'summary', 'dl', 'pre'):
    a = len(re.findall(r'<%s[ >]' % t, body))
    b = body.count('</%s>' % t)
    chk(a == b, '<%s> 开闭配对 %d/%d' % (t, a, b))
ids = re.findall(r'<section id="([a-z]\d+)"', body)
chk(len(ids) == len(set(ids)), 'section id 无重复（%d 个）' % len(ids))
allids = re.findall(r'\bid="([^"]+)"', body)
chk(len(allids) == len(set(allids)), '全部 id 无重复（%d 个）' % len(allids))
links = set(re.findall(r'href="#([a-z]\d+)"', h))
chk(links <= set(ids), '目录链接都有对应 section' + ('' if links <= set(ids) else ' 缺：%s' % (links - set(ids))))
chk(set(ids) <= links, '每个 section 都在目录里' + ('' if set(ids) <= links else ' 漏：%s' % (set(ids) - links)))

print('── 2. A、B 两部分与源文件一致 ' + '─' * 36)
for L, p, f in (('A', 'a', '../array/array-handbook.html'), ('B', 'e', '../enh/enh-handbook.html')):
    src = io.open(f, encoding='utf-8').read()
    ss = re.findall(r'<section id="s(\d+)"', src[src.index('<main>'):])
    mine = re.findall(r'<section id="%s(\d+)"' % p, body)
    chk(ss == mine, '%s 部分 %d 个 section 与 %s 一一对应' % (L, len(ss), f))
    nf = src[src.index('<main>'):].count('<figure>')
    mf = sum(len(re.findall(r'<figure>', m)) for m in re.findall(r'<section id="%s\d+">.*?</section>' % p, body, re.S))
    chk(nf == mf, '%s 部分图数一致（%d）' % (L, nf))
    nk = len(re.findall(r'class="katex-display"', src[src.index('<main>'):]))
    mk = len(re.findall(r'class="katex-display"', ''.join(re.findall(r'<section id="%s\d+">.*?</section>' % p, body, re.S))))
    chk(nk == mk, '%s 部分公式块数一致（%d）' % (L, nk))
chk('<script id="chart-data"' in h, '阵列那一半的交互数据与脚本都在')

print('── 3. SVG ' + '─' * 51)
svgs = re.findall(r'<svg[^>]*>', newpart)
chk(len(svgs) == newpart.count('</svg>'), '新写部分 svg 开闭配对（%d 个）' % len(svgs))
inner = re.findall(r'<svg.*?</svg>', newpart, re.S)
chk(not any('<em>' in s or '<strong>' in s or '<br' in s or '<sup>' in s for s in inner),
    'SVG 内无 HTML 标签（em/strong/br/sup）')
chk(all(len(re.findall(r'<text[ >]', s)) == s.count('</text>') for s in inner), '每张图的 <text> 都闭合')
rg = []
for s_ in inner:
    if 'var(--hot)' in s_ and 'var(--s3)' in re.sub(r'<defs>.*?</defs>', '', s_, flags=re.S):
        lab = re.search(r'aria-label="([^"]{0,24})', s_)
        rg.append(lab.group(1) if lab else '?')
# 这一组图沿用 s1/s2/s3 + hot 的配色（三种信息各一色），仅记录不判错
print('    （同时用 --hot 与 --s3 的图：%d 张，三种信息各占一色，属有意）' % len(rg))
caps = re.findall(r'<figcaption>(.*?)</figcaption>', newpart, re.S)
chk(not [c for c in caps if any(t in c for t in ('<h3', '<table', '<figure', '<section'))], 'figcaption 内无块级内容')
chk(len(caps) == 5, '新写的五张图都有图注（%d）' % len(caps))

print('── 4. 公式与格式符 ' + '─' * 43)
chk('undefined' not in newpart and 'NaN' not in newpart and 'None' not in txt, '无 undefined / NaN / None')
stray = re.findall(r'%[sdfrg]\b|%%', txt)
chk(not stray, '正文无残留格式符' + ('' if not stray else ' 出现：%s' % set(stray)))
raw = re.findall(r'\\(?:frac|sum|underbrace|mathbf|begin|cdot|log|boldsymbol)\b', txt)
chk(not raw, '正文无裸 LaTeX' + ('' if not raw else ' 出现：%s' % set(raw)))
K = json.load(open('fe_k.json'))
unused = [k for k, v in K.items() if v not in newpart]
chk(not unused, '所有公式都用上了（%d 个）' % len(K) + ('' if not unused else ' 未用：%s' % unused))
KI = json.load(open('fe_ki.json'))
print('    （行内公式 %d 个已渲染，正文暂未引用；留作术语用）' % len(KI))
F = json.load(open('figs_fe.json'))
for k, v in F.items():
    chk(v in newpart, '图 %s 已嵌入' % k)

print('── 5. 数字和脚本对得上 ' + '─' * 39)
AD = json.load(open('demo_aec_adapt.json')); DT = json.load(open('demo_aec_dtd.json'))
DR = json.load(open('demo_aec_drift.json')); RS = json.load(open('demo_aec_res.json'))
RES0 = RS['res'][0]['near_segsnr']
NUMS = {
    '%.2f' % AD['length_note']['d64_128']: '滤波器 64→128 ms 的 ERLE 收益',
    '%.1f' % AD['mu_tradeoff']['prod_spread']: 'μ 扫描里快与准之积的浮动',
    '%.2f' % AD['mu_tradeoff']['mis_gain']: 'μ 0.1→1 的失调差',
    '%.0f' % AD['part_note']['delay_ratio']: '块长缩小带来的延迟倍数',
    '%.1f' % AD['part_note']['mac_ratio']: '块长缩小带来的算力倍数',
    '%.2f' % DT['no_dtd_cost']: '不冻结 vs 全知',
    '%.2f' % DT['eer_cost']: '按 EER 定阈值的代价',
    '%.1f' % DT['miss_knee']['free_up_to']: '漏检免费的上限（s）',
    '%.2f' % DT['asym']['miss_jump']: '漏检 0.4 s 的失调跳升',
    '%.2f' % DT['asym']['fa_cost']: '误检一半的 ERLE 代价',
    '%d' % DR['ppm_note']['ppm_6db']: '掉 6 dB 的时钟差',
    '%.2f' % DR['len_drift_note']['long']: '长滤波器在 50 ppm 下的损失',
    '%.2f' % abs(DR['delay_note']['last']): '延迟悬崖尽头的 ERLE',
    '%.2f' % RS['nl_note']['bind_drop']: '非线性 4.65% 处的掉量',
    '%.2f' % (RES0 - RS['res_note']['q_at_erle']): 'ERLE 最大点的近端代价',
    '%.1f' % RS['split_note']['gap']: '线性/RES 分工的最大差距',
    '%.2f' % RS['res_note']['knee_erle_gain']: 'RES 拐点的 ERLE 收益',
}
for s_, w in NUMS.items():
    chk(s_ in txt or s_ in h, '出现「%s」（%s）' % (s_, w))
# 正文里 "相差 N 倍" 必须与 json 一致
fa, ms = DT['best']['fa'], DT['best']['miss']
chk('%.0f 倍' % (fa / ms) in txt, '"误检 / 漏检 = %.0f 倍"与最优工作点一致' % (fa / ms))
chk(abs(DT['asym']['miss_recover'] / DT['asym']['miss_dur'] - DT['asym']['ratio']) < 0.6,
    '漏检"还清时长 / 漏检时长"与 asym.ratio 一致')

print('── 6. 排版细节 ' + '─' * 47)
bad_minus = re.findall(r'[（(\s]-\d', txt)
chk(not bad_minus, '负号用 − 而不是 -' + ('' if not bad_minus else ' %d 处' % len(bad_minus)))
chk(h.count('<title>') == 1 and '<title>前端信号处理手册</title>' in h, '标题正确')
chk('麦克风阵列手册</title>' not in h, '外壳标题没留下阵列那本的痕迹')
chk(h.count('claude.ai/artifact') >= 3, '姊妹篇链接都在')
nq = len(re.findall(r'class="qz"', newpart))
chk(nq >= 1, '自测块 %d 处' % nq)
chk(len(re.findall(r'class="trap"', newpart)) >= 4, '"我原以为"与翻车块不少于 4 处')

print('\n' + '=' * 62)
print('未通过 %d 项' % len(bad))
sys.exit(1 if bad else 0)
