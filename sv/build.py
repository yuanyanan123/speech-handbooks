#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把《声纹与唤醒手册》拼起来。外壳（字体、KaTeX、CSS）沿用阵列手册，
   正文由 book1.py / book2.py 生成。"""
import json, io, re

HEAD = io.open('_head.html', encoding='utf-8').read()
HEAD = HEAD.replace('<title>麦克风阵列手册</title>', '<title>声纹与唤醒手册</title>')

EXTRA = '''
<style>
.dp{min-width:0;font-family:var(--f-mono);font-variant-numeric:tabular-nums;font-size:12.5px}
.dp td,.dp th{padding:6px 11px;text-align:center}
.dp td:first-child,.dp th:first-child{text-align:left;color:var(--text-3)}
.dp .best{background:var(--accent-soft);color:var(--accent);font-weight:600}
.matrix table{min-width:620px;font-size:12.5px}
.matrix td,.matrix th{padding:7px 10px}
.matrix thead th{font-size:10px;text-align:center;line-height:1.3;white-space:normal;min-width:54px}
.matrix thead th:first-child{text-align:left;min-width:140px}
.matrix td.m{text-align:center;font-size:13px}
.matrix .yes{color:var(--hot)}
.matrix .no{color:var(--text-3);opacity:.5}
.matrix .part-y{color:var(--accent)}
.matrix tbody td:first-child{white-space:nowrap}
.matrix .era{font-family:var(--f-mono);font-size:10.5px;color:var(--text-3);display:block;font-weight:400}
.two{display:grid;grid-template-columns:1fr 1fr;gap:0 26px;margin:16px 0 20px}
.two>div{border-left:2px solid var(--border-2);padding-left:14px}
.two h4{margin:0 0 6px;font-size:13px}
.two p{margin:0 0 8px;font-size:14px;line-height:1.7}
@media(max-width:620px){.two{grid-template-columns:1fr;gap:16px}}
.unit{display:grid;grid-template-columns:repeat(auto-fill,minmax(172px,1fr));gap:6px;
      margin:12px 0 18px;font-family:var(--f-mono);font-size:12px}
.unit span{background:var(--surface-2);border:1px solid var(--border);border-radius:3px;
           padding:5px 8px;letter-spacing:.03em}
.unit span b{color:var(--accent);font-weight:600}
</style>
'''

TOC = [
    ('导读', [('s0', '—', '这本手册怎么读')]),
    ('Ⅰ 同一根骨架', [('s1', '01', '判别、辨认与检测'), ('s2', '02', 'EER、DCF 与 DET'),
                  ('s3', '03', '校准：好看不等于能用'),
                  ('s4', '04', '要多少试验才测得准')]),
    ('Ⅱ 声纹', [('s5', '05', '嵌入：从 i-vector 到 ECAPA'), ('s6', '06', '池化那一步'),
              ('s7', '07', '损失函数与 margin'), ('s8', '08', '打分：余弦与 PLDA'),
              ('s9', '09', '分数归一化'), ('s10', '10', '时长、注册与失配')]),
    ('Ⅲ 唤醒', [('s11', '11', '唤醒不是小一号的 ASR'), ('s12', '12', '误唤醒率的单位'),
              ('s13', '13', '唤醒词怎么选'), ('s14', '14', '模型结构与流式'),
              ('s15', '15', '级联与功耗'), ('s16', '16', '自定义唤醒词')]),
    ('Ⅳ 共同的工程问题', [('s17', '17', '前端：增强帮不帮得上'),
                    ('s18', '18', '端侧部署与量化'), ('s19', '19', '数据与增广'),
                    ('s20', '20', '评测的坑'), ('s21', '21', '防伪与安全')]),
    ('Ⅴ 难点与趋势', [('s22', '22', '当前的真正难点'), ('s23', '23', '技术趋势')]),
    ('附录', [('s24', '24', '公式、算例与自测'), ('s25', '25', '术语表')]),
]


def toc_html():
    o = ['<nav class="toc" aria-label="目录"><ol>']
    for part, items in TOC:
        o.append('<li class="part">%s</li>' % part)
        for sid, num, name in items:
            o.append('<li><a href="#%s"><span class="num">%s</span>%s</a></li>' % (sid, num, name))
    o.append('</ol></nav>')
    return ''.join(o)


MAST = '''<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">说话人确认 · 关键词唤醒 · 同一套假设检验的两个极端</p>
    <h1>声纹与唤醒手册</h1>
    <p class="dek">这两件事在教科书里分属两章，在系统里却是同一个东西：一个分数配一个阈值。
    区别只在工作点——声纹一天判决几次，唤醒一天判决两百多万次。
    六个数量级的差距，推出了两套完全不同的工程结论。
    全书二十六节、十二张自绘图，每个数字都由随书脚本算出，可以自己复算：
    唤醒那半边还真做了三组实验——误唤醒率的泊松统计量、
    前端降噪对唤醒是帮是害、自定义唤醒词的注册曲线与覆盖面。</p>
    <dl class="specstrip">
      <div class="spec"><dt>唤醒每天判决</dt><dd>288<small>万次</small></dd></div>
      <div class="spec"><dt>EER 与真实工作点</dt><dd>6.6<small>nat</small></dd></div>
      <div class="spec"><dt>同 minDCF 下 actDCF</dt><dd>4.6<small>倍</small></dd></div>
      <div class="spec"><dt>1 秒 : 10 秒</dt><dd>32<small>倍 EER</small></dd></div>
      <div class="spec"><dt>中文带调音节熵</dt><dd>9.25<small>bit</small></dd></div>
      <div class="spec"><dt>跑一天零误唤醒只能说</dt><dd>≤3.7<small>次/天</small></dd></div>
      <div class="spec"><dt>换一套负样本素材</dt><dd>40<small>倍</small></dd></div>
      <div class="spec"><dt>自定义唤醒词换个人喊</dt><dd>2.1<small>倍</small></dd></div>
    </dl>
  </header>
</div>
<div class="ruler"></div>
'''

FOOT = '''<footer>
    <p>本页所有数字——五种打分的 EER、各向异性扫描、校准表、自助法置信区间与功效、
    时长/注册/信道失配、AS-norm、四种分类头的对照实验、中文音节熵、
    误唤醒的次/天换算、级联功耗与端侧算力阶梯、
    误唤醒率的泊松置信区间（蒙特卡洛核对过覆盖率）、
    谱减过减量对唤醒的影响、自定义唤醒词的注册与跨说话人代价——
    都由随书脚本计算生成，可复算。</p>
    <p>嵌入是按两协方差模型仿真出来的（类间 <b>B</b>、类内 <b>W</b> 都已知），
    所以"PLDA 能拿到多少"有客观上界，"余弦差在哪"才说得清楚；
    07 节那个网络是真训的（纯 numpy、手写反传），测试说话人训练时没见过。
    代价是它们都不是真录音：绝对数值不能直接和 VoxCeleb 上的结果比，
    可比的是<b>形状和量级</b>。唤醒那几节的负样本分布是<em>假设</em>的三高斯混合，
    参数取自公开评测里常见的量级；给定那组假设之后，次/天、功效、功耗的换算本身是精确的。</p>
    <p>书里有三处我把<b>自己猜错的假说连同否掉它的对照实验一起留着</b>：
    margin 与各向同性、EER 阈值的可迁移性、级联的功耗拐点在哪。
    留着是因为错误的归因比正确的结论更常见。</p>
    <p>姊妹篇：<a href="https://claude.ai/artifact/NL7s2XicLUVjGk8uq4jXvw">ASR 链路手册</a>
    ——语音识别从 GMM-HMM 到 LLM-ASR 的七代脉络；
    <a href="https://claude.ai/artifact/JkNwTFLFyfWYejCCzykVLQ">麦克风阵列手册</a>
    ——从物理上限到工程落地；
    <a href="https://claude.ai/artifact/JoVn5ZfQeMhCGQbfScKuwC">TTS 合成手册</a>
    ——从文字到声音的七代技术。四本共用同一套记号与算例风格。</p>
  </footer>
'''


def fix_text(html):
    """只在文本节点里做排版修正：ASCII 负号 → 真负号；不碰标签、svg、script、style。"""
    parts = re.split(r'(<svg.*?</svg>|<script.*?</script>|<style.*?</style>|<pre>.*?</pre>)',
                     html, flags=re.S)
    for i in range(0, len(parts), 2):
        seg = re.split(r'(<[^>]*>)', parts[i])
        for j in range(0, len(seg), 2):
            seg[j] = re.sub(r'(^|[\s（(>])-(?=\d)', lambda m: m.group(1) + '−', seg[j])
            seg[j] = re.sub(r'(^|[\s（(>])-(?=\d)', lambda m: m.group(1) + '−', seg[j])
        parts[i] = ''.join(seg)
    return ''.join(parts)


def main():
    import book1, book2
    body = fix_text(book1.build() + book2.build())
    html = (HEAD + EXTRA + MAST + '<div class="wrap">\n<div class="cols">\n'
            + toc_html() + '\n<main>\n' + body + FOOT + '\n</main>\n</div>\n</div>\n')
    io.open('sv-handbook.html', 'w', encoding='utf-8').write(html)
    print('sv-handbook.html  %.1f KB' % (len(html.encode()) / 1024))
    for t in ('section', 'h2', 'figure', 'table'):
        print('  <%s> %d / </%s> %d' % (t, len(re.findall('<%s[ >]' % t, html)),
                                        t, html.count('</%s>' % t)))


if __name__ == '__main__':
    main()
