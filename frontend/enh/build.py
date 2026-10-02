#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把《单通道增强手册》拼起来。"""
import json, io, re

HEAD = io.open('_head.html', encoding='utf-8').read()
HEAD = HEAD.replace('<title>麦克风阵列手册</title>', '<title>单通道增强手册</title>')

EXTRA = '''
<style>
.dp{min-width:0;font-family:var(--f-mono);font-variant-numeric:tabular-nums;font-size:12.5px}
.dp td,.dp th{padding:6px 11px;text-align:center}
.dp td:first-child,.dp th:first-child{text-align:left;color:var(--text-3)}
.dp .best{background:var(--accent-soft);color:var(--accent);font-weight:600}
.matrix table{min-width:600px;font-size:12.5px}
.matrix td,.matrix th{padding:7px 10px}
.matrix thead th{font-size:10px;text-align:center;line-height:1.3;white-space:normal;min-width:54px}
.matrix thead th:first-child{text-align:left;min-width:132px}
.matrix td.m{text-align:center;font-size:13px}
.matrix .yes{color:var(--hot)}
.matrix .no{color:var(--text-3);opacity:.5}
.matrix .part-y{color:var(--accent)}
.matrix tbody td:first-child{white-space:nowrap}
.matrix .era{font-family:var(--f-mono);font-size:10.5px;color:var(--text-3);display:block;font-weight:400}
.unit{display:grid;grid-template-columns:repeat(auto-fill,minmax(176px,1fr));gap:6px;
      margin:12px 0 18px;font-family:var(--f-mono);font-size:12px}
.unit span{background:var(--surface-2);border:1px solid var(--border);border-radius:3px;
           padding:5px 8px;letter-spacing:.03em}
.unit span b{color:var(--accent);font-weight:600}
.two{display:grid;grid-template-columns:1fr 1fr;gap:0 26px;margin:16px 0 20px}
.two>div{border-left:2px solid var(--border-2);padding-left:14px}
.two h4{margin:0 0 6px;font-size:13px}
.two p{margin:0 0 8px;font-size:14px;line-height:1.7}
@media(max-width:620px){.two{grid-template-columns:1fr;gap:16px}}
</style>
'''

TOC = [
    ('导读', [('s0', '—', '这本手册怎么读')]),
    ('Ⅰ 问题本身', [('s1', '01', '自由度为零'),
                ('s2', '02', '两个信噪比与一个记分板'),
                ('s3', '03', '时频变换与延迟预算')]),
    ('Ⅱ 增益函数', [('s4', '04', '谱减与它的两个补丁'),
                ('s5', '05', '维纳：最小均方的那一支'),
                ('s6', '06', 'MMSE-STSA 与 log-MMSE'),
                ('s7', '07', '音乐噪声是什么')]),
    ('Ⅲ 两个估计', [('s8', '08', '判决引导：其实是个开关'),
                ('s9', '09', '噪声功率谱怎么估'),
                ('s10', '10', '语音存在概率与 OM-LSA')]),
    ('Ⅳ 相位', [('s11', '11', '相位到底值多少'),
              ('s12', '12', '复数掩码与相位重建')]),
    ('Ⅴ 神经降噪', [('s13', '13', '它到底改变了什么'),
                ('s14', '14', '输出什么：掩码、映射、复数'),
                ('s15', '15', '损失函数'),
                ('s16', '16', '因果、延迟与算力'),
                ('s17', '17', '数据与泛化')]),
    ('Ⅵ 评测', [('s18', '18', '四个指标，四种排序'),
              ('s19', '19', '给机器听的增强')]),
    ('Ⅶ 落地', [('s20', '20', '三档场景的完整预算'),
              ('s21', '21', '十个翻车点'),
              ('s22', '22', '当前的真正难点与趋势')]),
    ('附录', [('s23', '23', '公式、算例与自测'), ('s24', '24', '术语表')]),
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
    <p class="eyebrow">一路麦克风 · 从谱减到神经降噪 · 每个数都可复算</p>
    <h1>单通道增强手册</h1>
    <p class="dek">只有一路信号时，空间自由度是零，能依靠的只剩下统计假设：
    噪声比语音平稳、语音在时频上稀疏、幅度服从某个分布。
    每一代方法都是在换一个更好的假设，而每个假设失效时都有一种特定的听感失真。
    全书二十五节、十四张自绘图、二十八个公式块，每个数字都由随书脚本算出，可以自己复算。</p>
    <dl class="specstrip">
      <div class="spec"><dt>音乐噪声的理论零点</dt><dd>5.57<small>dB</small></dd></div>
      <div class="spec"><dt>判决引导的捕获阈值</dt><dd>6.75<small>dB</small></dd></div>
      <div class="spec"><dt>噪声变大后失灵</dt><dd>768<small>ms</small></dd></div>
      <div class="spec"><dt>相位还值多少</dt><dd>6.6<small>dB</small></dd></div>
      <div class="spec"><dt>复数掩码的兑现率</dt><dd>25.4<small>%</small></dd></div>
      <div class="spec"><dt>失配本身 ÷ 覆盖不足</dt><dd>3.5<small>倍</small></dd></div>
      <div class="spec"><dt>耳机档算力是会议档的</dt><dd>4.1<small>倍</small></dd></div>
      <div class="spec"><dt>增强后声纹 EER</dt><dd>变差<small>全部</small></dd></div>
    </dl>
  </header>
</div>
<div class="ruler"></div>
'''

FOOT = '''<footer>
    <p>本页所有数字——四种增益函数的形状、误差的正交分解、音乐噪声的理论零点与实测、
    判决引导的不动点与捕获阈值、三种噪声估计器的追踪延迟、幅度与相位的分家实验、
    窗长与延迟的扫描、神经网络的训练与泛化、输出参数化的上界与兑现率、
    六个数据维度的消融、三档预算的完整结算、五个指标的名次分歧、
    增强对声纹的影响、以及"删掉了"与"编出来了"两类错误的此消彼长——
    都由随书脚本计算生成，可复算。</p>
    <p>干净语音是用<b>源-滤波模型合成</b>的：基频曲线、共振峰轨迹、每个音段的起止都是已知真值，
    所以"增强丢了什么"才有客观答案。19 节的说话人身份是声道长度与基频区间，
    因此那一节是<b>文本相关</b>的说话人确认代理，不是真实的声纹系统。
    神经网络那几节是真训的（纯 numpy、手写反传、严格因果），测试语音训练时没见过。</p>
    <p>代价要说清楚：这些都不是真录音，<b>绝对数值不能直接和 DNS 或 VoiceBank 上的结果比</b>。
    可比的是形状、量级和趋势——而这本书要讲的恰好是形状。
    其中 LSD 在合成语音上偏大（谐波谷比真语音深），只用于相对比较；
    STOI* 是简化的可懂度代理，不是标准 STOI。</p>
    <p>书里有<b>八处</b>我把<b>自己猜错的假说连同否掉它的对照实验一起留着</b>：
    判决引导只是"平滑"、短窗系统可以不管相位、时频分辨率对非平稳噪声更值钱、
    级联式的直觉在这里也不成立、理想幅度掩码落在 [0,1] 里、
    上界高的参数化至少不会更差、电平覆盖的代价取决于特征有没有归一化、
    以及"把削掉的填回去只是化妆，客观指标一定变差"。
    留着是因为错误的归因比错误的结论更常见。</p>
    <p>姊妹篇：<a href="https://claude.ai/artifact/JkNwTFLFyfWYejCCzykVLQ">麦克风阵列手册</a>
    ——多通道前端，从物理上限到工程落地；
    <a href="https://claude.ai/artifact/NL7s2XicLUVjGk8uq4jXvw">ASR 链路手册</a>
    ——语音识别的七代脉络；
    <a href="https://claude.ai/artifact/JoVn5ZfQeMhCGQbfScKuwC">TTS 合成手册</a>
    ——从文字到声音；
    <a href="https://claude.ai/artifact/WMzwGqiwAy6vi8MrLwJpgg">声纹与唤醒手册</a>
    ——说话人确认与关键词唤醒。五本共用同一套记号与算例风格。</p>
  </footer>
'''


def fix_text(html):
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
    io.open('enh-handbook.html', 'w', encoding='utf-8').write(html)
    print('enh-handbook.html  %.1f KB' % (len(html.encode()) / 1024))
    for t in ('section', 'h2', 'figure', 'table'):
        print('  <%s> %d / </%s> %d' % (t, len(re.findall('<%s[ >]' % t, html)),
                                        t, html.count('</%s>' % t)))


if __name__ == '__main__':
    main()
