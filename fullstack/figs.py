# -*- coding: utf-8 -*-
import json
C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
T3, T2, TX = 'var(--text-3)', 'var(--text-2)', 'var(--text)'
OUT = {}


def svg(w, h, o, label):
    return '<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label="%s">%s</svg>' % (w, h, label, ''.join(o))


def box(o, x, y, w, h, col, t1, t2):
    o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="6" fill="var(--surface)" stroke="%s" stroke-width="1.8"/>' % (x, y, w, h, col))
    o.append('<text x="%d" y="%d" text-anchor="middle" font-size="12.5" font-weight="600" fill="%s">%s</text>' % (x + w / 2, y + 24, TX, t1))
    o.append('<text x="%d" y="%d" text-anchor="middle" font-size="10.5" fill="%s">%s</text>' % (x + w / 2, y + 42, T3, t2))


def arrow(o, x1, y1, x2, y2, col=T2, dash=None, w=1.6):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    o.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="%g"%s marker-end="url(#ah)"/>' % (x1, y1, x2, y2, col, w, d))


def fig_arch():
    o = ['<defs><marker id="ah" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
         '<path d="M0,0 L8,4 L0,8 z" fill="var(--text-2)"/></marker></defs>']
    W, H = 700, 372
    bw, bh, gap = 102, 58, 11
    xs = [14 + i * (bw + gap) for i in range(6)]
    # 分组标签
    o.append('<text x="14" y="16" font-size="11" font-weight="600" fill="%s">① 前端：阵列 → 回声 → 统计 → 入口门（1–5 节）</text>' % C1)
    ya, yb, yc = 52, 168, 288
    A = [('麦克风阵列', 'y_m[n]，M 路'), ('STFT', 'Y(t,k)，M×F×T'), ('回声消除', '减掉 g∗x'),
         ('波束成形', 'wᴴy → 1 路'), ('降噪·去混响', '增益 G(t,k)'), ('VAD·唤醒·声纹', '门控与身份')]
    for x, (a, b) in zip(xs, A):
        box(o, x, ya, bw, bh, C1, a, b)
    for i in range(5):
        arrow(o, xs[i] + bw, ya + bh // 2, xs[i + 1] - 1, ya + bh // 2)
    o.append('<text x="14" y="%d" font-size="11" font-weight="600" fill="%s">② 识别与理解（6–9 节）</text>' % (yb + bh + 16, C2))
    o.append('<text x="%d" y="%d" font-size="11" font-weight="600" fill="%s">③ 合成（10–13 节）</text>' % (xs[3], yb + bh + 16, C3))
    B = [('log-mel 特征', 'T′×80'), ('ASR', 'CTC·RNN-T·AED'), ('文本中枢', 'NLU / LLM'),
         ('文本前端', '规范化·G2P·韵律'), ('声学模型', 'mel / token'), ('声码器', '波形 x[n]')]
    cols = [C2, C2, T2, C3, C3, C3]
    for x, (a, b), c in zip(xs, B, cols):
        box(o, x, yb, bw, bh, c, a, b)
    for i in range(5):
        arrow(o, xs[i] + bw, yb + bh // 2, xs[i + 1] - 1, yb + bh // 2)
    # A5 → B0
    xm = xs[5] + bw // 2
    o.append('<polyline points="%d,%d %d,%d %d,%d %d,%d" fill="none" stroke="%s" stroke-width="1.6" marker-end="url(#ah)"/>'
             % (xm, ya + bh, xm, ya + bh + 28, xs[0] + bw // 2, ya + bh + 28, xs[0] + bw // 2, yb - 1, T2))
    # 喇叭
    box(o, xs[5], yc, bw, bh, T2, '功放·喇叭', '播放 x[n]')
    arrow(o, xm, yb + bh, xm, yc - 1)
    # 声学路径回到麦克风
    o.append('<polyline points="%d,%d %d,%d %d,%d %d,%d" fill="none" stroke="%s" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#ah)"/>'
             % (xs[5], yc + bh // 2, 7, yc + bh // 2, 7, ya + bh // 2, xs[0] - 1, ya + bh // 2, T2))
    o.append('<text x="%d" y="%d" font-size="10.5" fill="%s" text-anchor="middle">声学路径 g（房间）：自己播的声音又被麦克风拾到</text>' % (330, yc + bh // 2 + 18, T2))
    # 参考信号
    xr = xs[2] + bw // 2
    o.append('<polyline points="%d,%d %d,%d %d,%d %d,%d" fill="none" stroke="%s" stroke-width="1.6" stroke-dasharray="2 3" marker-end="url(#ah)"/>'
             % (xs[5] + bw, yc + bh // 2, 695, yc + bh // 2, 695, 40, xr, 40, T3))
    o.append('<line x1="%d" y1="40" x2="%d" y2="%d" stroke="%s" stroke-width="1.6" stroke-dasharray="2 3" marker-end="url(#ah)"/>' % (xr, xr, ya - 1, T3))
    o.append('<text x="%d" y="35" font-size="10.5" fill="%s" text-anchor="middle">参考 x[n]：播放信号的数字副本（AEC 的已知输入）</text>' % (430, T3))
    o.append('<text x="14" y="%d" font-size="10.5" fill="%s">一圈走完：输出回到输入。所以这条链路是闭环，不是单向流水线（14 节）。</text>' % (H - 10, T3))
    return svg(W, H, o, '全栈音频链路总图：前端、识别、理解、合成与回到麦克风的闭环')


OUT['arch'] = fig_arch()
json.dump(OUT, open('figs.json', 'w'), ensure_ascii=False)
print('figs', list(OUT))
