# -*- coding: utf-8 -*-
"""第 23 节的网络结构图（内联 SVG）。形状与超参数来自 nn.json（nn_specs.py 算出，源码核对）。"""
import json
N = json.load(open('nn.json'))
C1, C2, C3 = 'var(--s1)', 'var(--s2)', 'var(--s3)'
T2, T3, TX = 'var(--text-2)', 'var(--text-3)', 'var(--text)'
OUT = {}


def svg(w, h, o, label):
    return ('<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label="%s"><defs><marker id="ah" viewBox="0 0 8 8" refX="7" refY="4" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 z" fill="var(--text-2)"/></marker></defs>%s</svg>'
            % (w, h, label, ''.join(o)))


def box(o, x, y, w, h, col, t1, t2='', t3=''):
    o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="5" fill="var(--surface)" stroke="%s" stroke-width="1.7"/>' % (x, y, w, h, col))
    cy = y + h / 2
    n = 1 + bool(t2) + bool(t3)
    y0 = cy - (n - 1) * 7.5 + 4
    o.append('<text x="%g" y="%g" text-anchor="middle" font-size="11.5" font-weight="600" fill="%s">%s</text>' % (x + w / 2, y0, TX, t1))
    if t2:
        o.append('<text x="%g" y="%g" text-anchor="middle" font-size="9.5" fill="%s">%s</text>' % (x + w / 2, y0 + 15, T3, t2))
    if t3:
        o.append('<text x="%g" y="%g" text-anchor="middle" font-size="9.5" fill="%s">%s</text>' % (x + w / 2, y0 + 29, T3, t3))


def arr(o, x1, y1, x2, y2, col=T2, dash=None, w=1.5):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    o.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g"%s marker-end="url(#ah)"/>' % (x1, y1, x2, y2, col, w, d))


def poly(o, pts, col=T2, dash=None, w=1.5, arrow=True):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    m = ' marker-end="url(#ah)"' if arrow else ''
    o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%g"%s%s/>' % (' '.join('%g,%g' % p for p in pts), col, w, d, m))


def txt(o, x, y, s, col=T3, size=10, anchor='start', weight=''):
    wt = ' font-weight="%s"' % weight if weight else ''
    o.append('<text x="%g" y="%g" text-anchor="%s" font-size="%g" fill="%s"%s>%s</text>' % (x, y, anchor, size, col, wt, s))


def chain(o, y, items, x0=14, w=96, h=50, gap=12, cols=None):
    """一行方框，自动连箭头；items = [(t1,t2,t3), ...]；返回各框 (x, y, w, h)"""
    pos = []
    for i, it in enumerate(items):
        x = x0 + i * (w + gap)
        box(o, x, y, w, h, (cols or [C1] * len(items))[i], *it)
        pos.append((x, y, w, h))
        if i:
            arr(o, x - gap, y + h / 2, x - 1, y + h / 2)
    return pos


# ── 1 DeepFilterNet2 ──────────────────────────────────────────────
def f_dfn2():
    d = N['dfn2']; T = d['T']
    o = []; W, H = 700, 372
    box(o, 14, 150, 80, 50, T2, 'STFT', '960 / 480', '[481×%d]' % T)
    box(o, 130, 40, 110, 50, C1, 'ERB 特征', '[1,%d,32]' % T, 'dB 并归一化')
    box(o, 130, 262, 110, 50, C1, '复数特征', '[2,%d,96]' % T, '前 96 点 (<4.8 kHz)')
    arr(o, 94, 165, 130, 70); arr(o, 94, 185, 130, 285)
    box(o, 275, 40, 120, 50, C1, 'ERB 编码器', 'conv0–3 (C=16)', '[16,%d,8]' % T)
    box(o, 275, 262, 120, 50, C1, '复数分支', 'df_conv0/1', '[16,%d,48]' % T)
    arr(o, 240, 65, 275, 65); arr(o, 240, 287, 275, 287)
    box(o, 430, 150, 110, 50, C2, 'GRU ×2', '隐维 256', '[%d,256]' % T)
    poly(o, [(395, 65), (415, 65), (415, 165), (430, 165)]); poly(o, [(395, 287), (415, 287), (415, 185), (430, 185)])
    box(o, 575, 40, 110, 50, C3, 'ERB 解码器', '转置卷积 + 跳连', '增益 [1,%d,32]' % T)
    box(o, 575, 262, 110, 50, C3, 'DF 解码器', 'GRU + 线性', '[%d,5,96,2]' % T)
    arr(o, 540, 160, 575, 80); arr(o, 540, 190, 575, 280)
    poly(o, [(335, 40), (335, 20), (630, 20), (630, 40)], dash='4 3')
    txt(o, 470, 15, '跳连：编码器 e0–e3 → ERB 解码器', T3, 9.5, 'middle')
    box(o, 575, 150, 110, 50, T2, '应用', '低频：5 抽头滤波', '其余：ERB 增益')
    poly(o, [(630, 90), (630, 150)]); poly(o, [(630, 262), (630, 200)])
    txt(o, 14, 355, '每个低频点：Ŝ(t,k) = Σᵢ cᵢ(t,k)·Y(t−i,k)，i = 0…4；iSTFT 后输出与输入等长。', T3, 10)
    return svg(W, H, o, 'DeepFilterNet2 结构图：ERB 增益分支与深度滤波分支')


# ── 2 DCCRN-CL ────────────────────────────────────────────────────
def f_dccrn():
    d = N['dccrn']; enc = d['enc']
    o = []; W, H = 700, 304
    labels = ['E%d' % (i + 1) for i in range(6)]
    bw, gap, x0 = 82, 10, 40
    ytop, ybot = 40, 200
    for i, (ci, co, f) in enumerate(enc):
        x = x0 + i * (bw + gap)
        box(o, x, ytop, bw, 56, C1, 'E%d' % (i + 1), '%d→%d' % (ci, co), '频 %d' % f)
        if i:
            arr(o, x - gap, ytop + 28, x - 1, ytop + 28)
    # LSTM 在最右
    xl = x0 + 6 * (bw + gap) - 6
    box(o, xl, 112, 80, 56, C2, '复数 LSTM', '2 层 × 128', '%d 维' % d['rnn_in'])
    arr(o, x0 + 5 * (bw + gap) + bw, ytop + 28, xl + 40, 112) if False else None
    poly(o, [(x0 + 5 * (bw + gap) + bw / 2, ytop + 56), (x0 + 5 * (bw + gap) + bw / 2, 140), (xl, 140)])
    for i in range(6):
        j = 5 - i
        x = x0 + j * (bw + gap)
        ci, co, f = enc[j]
        box(o, x, ybot, bw, 56, C3, 'D%d' % (j + 1), '拼接后 %d→%d' % (2 * co if j < 5 else 2 * co, ci if ci > 1 else 1), '频 %d' % f)
    poly(o, [(xl + 40, 168), (xl + 40, 228), (x0 + 5 * (bw + gap) + bw, 228)])
    for j in range(5, 0, -1):
        arr(o, x0 + j * (bw + gap) - 1, ybot + 28, x0 + (j - 1) * (bw + gap) + bw + 1, ybot + 28)
    for j in range(6):
        xx = x0 + j * (bw + gap) + bw / 2
        arr(o, xx, ytop + 56, xx, ybot, dash='3 3', col=T3)
    txt(o, 14, 276, '跳连（虚线）：Eᵢ 的输出与 Dᵢ 的输入在通道上拼接。', T3, 10)
    txt(o, 14, 292, '输入 STFT [256 × %d] 复数（实虚部各一路），编码器核 5×2、步长 2×1（频率 ÷2）；输出复数掩蔽 × 带噪谱 → iSTFT。' % d['T'], T3, 10)
    return svg(W, H, o, 'DCCRN-CL 结构图：六级复数编码器、复数 LSTM、六级复数解码器与跳连')


# ── 3 Conv-TasNet ─────────────────────────────────────────────────
def f_tasnet():
    d = N['tasnet']; Tp = d['Tp']
    o = []; W, H = 700, 250
    items = [('编码器', 'Conv1d k16 s8', '[512,%d]' % Tp), ('gLN+1×1', '512→128', '[128,%d]' % Tp), ('TCN', '3×8 块 · 膨胀 1…128', '[128,%d]' % Tp),
             ('掩蔽', '1×1 conv + 激活', '[n,512,%d]' % Tp), ('⊙', '逐元素相乘', '[n,512,%d]' % Tp), ('解码器', 'ConvT k16 s8', '[n,%d]' % d['dec_len'])]
    pos = chain(o, 70, items, 14, 100, 56, 14, [C1, C1, C2, C2, T2, C3])
    txt(o, 14, 20, '输入波形 [%d]，输出波形 [n,%d]' % (d['N'], d['dec_len']), T3, 10)
    poly(o, [(64, 70), (64, 40), (474, 40), (474, 70)], dash='4 3')
    txt(o, 270, 34, '编码器输出直接送到 ⊙（被掩蔽的就是它）', T3, 9.5, 'middle')
    # 一个 Conv1D 块
    y = 170
    blk = [('1×1 conv', '128→512'), ('PReLU+gLN', ''), ('D-conv k3', '膨胀 2ˣ'), ('PReLU+gLN', ''), ('1×1 conv', '→128 残差/跳连')]
    txt(o, 14, 160, 'TCN 里的一个 Conv1D 块：', TX, 10.5, weight='600')
    for i, (a, b) in enumerate(blk):
        x = 14 + i * 134
        box(o, x, y, 120, 40, C2, a, b)
        if i:
            arr(o, x - 14, y + 20, x - 1, y + 20)
    txt(o, 14, 238, '感受野：1 + 2·3·(1+2+…+128) = %d 帧 ≈ %d ms（8 kHz，步长 8）。' % (d['rf_frames'], round(d['rf_ms'])), T3, 10)
    return svg(W, H, o, 'Conv-TasNet 结构图：编码器、TCN 掩蔽估计、解码器')


# ── 4 Conformer 块 ────────────────────────────────────────────────
def f_conformer():
    d = N['conformer']
    o = []; W, H = 700, 350
    x, w = 250, 200
    ys = [22, 82, 142, 202, 262]
    names = [('前馈 ×½', 'LN → Linear %d→%d → SiLU → Linear' % (d['D'], d['FF'])), ('多头自注意力', 'LN → %d 头 MHSA' % d['H']),
             ('卷积模块', 'LN→逐点→GLU→深度 k%d→BN→SiLU→逐点' % d['K']), ('前馈 ×½', '同上'), ('LayerNorm', '')]
    cols = [C1, C2, C1, C1, T2]
    for i, ((a, b), y) in enumerate(zip(names, ys)):
        box(o, x, y, w, 44, cols[i], a, b)
        if i:
            arr(o, x + w / 2, ys[i - 1] + 44, x + w / 2, y)
    arr(o, x + w / 2, 2, x + w / 2, ys[0])
    txt(o, x - 10, 14, '输入 [T, D]（T≈75，D=%d）' % d['D'], T3, 9.5, 'end')
    arr(o, x + w / 2, ys[4] + 44, x + w / 2, 336)
    txt(o, x + w / 2, 346, '输出 [T, D]（形状不变，可堆叠）', T3, 9.5, 'middle')
    # 残差：每个子层的输入处分出一条虚线，绕过该子层，在其输出处相加
    for i in range(4):
        yin = ys[i] - 10 if i else 10
        yout = ys[i] + 44 + 9
        poly(o, [(x + w / 2, yin), (x + w + 22, yin), (x + w + 22, yout), (x + w / 2 + 6, yout)], dash='3 3', col=T3)
        o.append('<circle cx="%g" cy="%g" r="6" fill="var(--surface)" stroke="%s" stroke-width="1.3"/>' % (x + w / 2, yout, T3))
        txt(o, x + w / 2, yout + 3.5, '+', T3, 10, 'middle')
    txt(o, x + w + 30, 182, '残差相加', T3, 9.5)
    txt(o, 14, 40, '示例配置（不是论文数字）：', TX, 10.5, weight='600')
    for k, s in enumerate(['D = %d，前馈隐维 %d' % (d['D'], d['FF']), '%d 头注意力，卷积核 %d' % (d['H'], d['K']),
                           '参数量 / 块：%s' % format(d['block_params'], ','), '  其中前馈 %s×2' % format(d['ffn_params'], ','),
                           '  注意力 %s' % format(d['mha_params'], ','), '  卷积模块 %s' % format(d['conv_params'], ',')]):
        txt(o, 14, 60 + k * 18, s, T3, 10)
    return svg(W, H, o, 'Conformer 块结构图')


# ── 5 RNN-T ───────────────────────────────────────────────────────
def f_rnnt():
    d = N['rnnt']
    o = []; W, H = 700, 270
    box(o, 14, 30, 150, 56, C1, '声学编码器', 'Conformer 等', '[T, %d]' % d['D'])
    box(o, 14, 150, 150, 56, C2, '预测网络', '循环 / 注意力，只看已输出标签', '[U+1, %d]' % d['D'])
    txt(o, 14, 20, '声学帧（%d × 40 ms）' % d['T'], T3, 9.5)
    txt(o, 14, 225, '标签前缀（含起始符，U = %d）' % d['U'], T3, 9.5)
    box(o, 250, 88, 130, 60, T2, '联合网络', 'enc[:,None] + pred[None,:]', '[T, U+1, %d]' % d['D'])
    arr(o, 164, 58, 250, 108); arr(o, 164, 178, 250, 130)
    box(o, 440, 88, 110, 60, C3, '激活 + 线性', '%d → %d' % (d['D'], d['V']), '[T, U+1, %d]' % d['V'])
    arr(o, 380, 118, 440, 118)
    box(o, 590, 88, 96, 60, C3, 'softmax', '词表含空白', '每格点一个分布')
    arr(o, 550, 118, 590, 118)
    # 格子示意
    gx, gy = 440, 175
    for i in range(6):
        for j in range(4):
            o.append('<circle cx="%g" cy="%g" r="3.2" fill="%s"/>' % (gx + i * 20, gy + j * 17, T3))
    poly(o, [(gx, gy), (gx + 20, gy), (gx + 40, gy), (gx + 40, gy + 17), (gx + 60, gy + 17), (gx + 60, gy + 34), (gx + 80, gy + 34), (gx + 100, gy + 34), (gx + 100, gy + 51)], col=C1, w=2, arrow=False)
    txt(o, 575, 205, '一条对齐路径：', T3, 9.5)
    txt(o, 575, 219, '→ 空白（t+1）', T3, 9.5); txt(o, 575, 233, '↓ 标签（u+1）', T3, 9.5)
    txt(o, 14, 258, '训练显存 ∝ B×T×U×V：本例每个样本 %d×%d×%d = %s 个 float，约 %.1f MB（fp32）。' % (d['T'], d['U'] + 1, d['V'], format(d['logits'], ','), d['bytes_fp32'] / 1e6), T3, 10)
    return svg(W, H, o, 'RNN-T 结构图：编码器、预测网络、联合网络与格子路径')


# ── 6 wav2vec 2.0 ────────────────────────────────────────────────
def f_w2v2():
    d = N['w2v2']; sh = d['shapes']
    o = []; W, H = 700, 266
    txt(o, 14, 20, '输入波形 [%d]（3 s @ 16 kHz）' % sh[0], T3, 10)
    cfg = [(10, 5), (3, 2), (3, 2), (3, 2), (3, 2), (2, 2), (2, 2)]
    for i, (k, s) in enumerate(cfg):
        x = 14 + i * 56
        box(o, x, 40, 50, 64, C1, '卷积%d' % (i + 1), 'k%d s%d' % (k, s), '%d' % sh[i + 1])
        if i:
            arr(o, x - 6, 72, x - 1, 72)
    txt(o, 14, 142, '特征编码器：7 层一维卷积，512 通道，累计步长 %d → 每 %d 个样点（20 ms）一帧' % (d['stride'], d['stride']), T3, 10)
    box(o, 14, 162, 110, 52, C1, '投影 + 位置卷积', '512→768 · 核128/16组', '[%d,768]' % d['frames'])
    box(o, 160, 162, 150, 52, C2, 'Transformer ×12', '768 维 · 12 头 · 前馈 3072', '[%d,768]' % d['frames'])
    box(o, 346, 162, 130, 52, C3, '上下文表示 c_t', '对被掩蔽位置做对比预测', '见 7 节 InfoNCE')
    arr(o, 124, 188, 160, 188); arr(o, 310, 188, 346, 188)
    poly(o, [(14 + 6 * 56 + 25, 104), (14 + 6 * 56 + 25, 122), (69, 122), (69, 162)])
    txt(o, 14, 238, '参数量（算术）：卷积 %.1f M + 12 层 × %.2f M + 位置卷积 + 投影 ≈ %.1f M。' % (d['conv_params'] / 1e6, d['layer_params'] / 1e6, d['total_params'] / 1e6), T3, 10)
    txt(o, 14, 256, '各卷积层输出帧数：' + ' → '.join(str(v) for v in sh), T3, 9.5)
    return svg(W, H, o, 'wav2vec 2.0 BASE 结构图：卷积特征编码器与 12 层 Transformer')


# ── 7 ECAPA-TDNN ─────────────────────────────────────────────────
def f_ecapa():
    d = N['ecapa']; T = d['T']
    o = []; W, H = 700, 260
    items = [('对数梅尔', '', '[80,%d]' % T), ('TDNN', 'k5 d1', '[512,%d]' % T), ('SE-Res2 ①', 'k3 d2', '[512,%d]' % T), ('SE-Res2 ②', 'k3 d3', '[512,%d]' % T),
             ('SE-Res2 ③', 'k3 d4', '[512,%d]' % T)]
    pos = chain(o, 40, items, 14, 104, 56, 14, [T2, C1, C2, C2, C2])
    box(o, 14, 150, 130, 56, C3, 'MFA', '拼接 3×512 → 1×1 卷积', '[1536,%d]' % T)
    box(o, 180, 150, 150, 56, C3, '注意力统计池化', '注意力通道 128 · 全局上下文', '[3072] = 均值 + 标准差')
    box(o, 366, 150, 130, 56, C3, 'BN + 线性', '3072 → 192', '[192] 嵌入')
    arr(o, 144, 178, 180, 178); arr(o, 330, 178, 366, 178)
    for i in (2, 3, 4):
        x = 14 + i * 118 + 52
        poly(o, [(x, 96), (x, 128), (79, 128), (79, 150)], dash='3 3', col=T3)
    txt(o, 14, 232, '三个 SE-Res2Block 的输出各 512 通道，拼接后做多层特征聚合；池化把变长序列压成定长向量。', T3, 10)
    return svg(W, H, o, 'ECAPA-TDNN 结构图')


# ── 8 FastSpeech2（结构：speechbrain docstring）──────────────────
def f_fs2():
    o = []; W, H = 700, 260
    items = [('音素序列', 'm = 14', '[14]'), ('嵌入 + 位置', '', '[14,D]'), ('编码器', 'FFT 块堆叠', '[14,D]'), ('方差适配器', '时长·音高·能量', ''), ('长度调节器', '按时长展开', '[258,D]'),
             ('解码器', 'FFT 块堆叠', '[258,D]'), ('线性 → 梅尔', '', '[258,80]')]
    chain(o, 40, items, 14, 90, 56, 9, [T2, C1, C2, C3, C3, C2, T2])
    box(o, 280, 130, 270, 70, C3, '方差适配器内部', '时长预测器 → d_i（整数帧）', '音高预测器、能量预测器（嵌入后加回）')
    arr(o, 380, 96, 380, 130, dash='3 3', col=T3)
    txt(o, 14, 232, '训练时用真值时长展开（teacher forcing）；推理时用预测时长。结构取自 speechbrain 的 FastSpeech2 说明；超参数不在此给出。', T3, 10)
    txt(o, 14, 248, 'm = 14 个音素、T = 258 帧：来自 21 节的数值算例（3 s @ 22.05 kHz，帧移 256）。', T3, 10)
    return svg(W, H, o, 'FastSpeech2 结构图：编码器、方差适配器、长度调节器、解码器')


# ── 9 HiFi-GAN ───────────────────────────────────────────────────
def f_hifigan():
    d = N['hifigan']; lens = d['lens']; ch = d['ch']
    o = []; W, H = 700, 320
    box(o, 14, 30, 80, 56, T2, '梅尔谱', '', '[80,%d]' % d['frames'])
    box(o, 112, 30, 76, 56, C1, 'conv_pre', 'k7', '[512,%d]' % d['frames'])
    arr(o, 94, 58, 112, 58)
    x = 206
    for i, u in enumerate([8, 8, 2, 2]):
        box(o, x, 30, 88, 56, C1, '上采样 ×%d' % u, '转置卷积 + MRF', '[%d,%d]' % (ch[i + 1], lens[i + 1]))
        arr(o, x - 18 if i == 0 else x - 6, 58, x - 1, 58)
        x += 96
    txt(o, 14, 108, '生成器：每级上采样后接多感受野融合（MRF）：3 个残差块（核 3/7/11，膨胀 1/3/5）取平均；末级 conv_post + tanh 得 [1, %d]。' % lens[-1], T3, 10)
    txt(o, 14, 124, '上采样总倍数 8×8×2×2 = %d = 帧移；%d 帧 × %d = %d 点。' % (8 * 8 * 2 * 2, d['frames'], d['hop'], lens[-1]), T3, 10)
    txt(o, 14, 156, '判别器（对抗训练的另一半）：', TX, 10.5, weight='600')
    box(o, 14, 170, 300, 70, C2, '多周期判别器 MPD', '周期 2、3、5、7、11（素数，减少重叠）', '波形 [1,T] 折成 [T/p, p] 的二维图再卷积')
    box(o, 340, 170, 300, 70, C2, '多尺度判别器 MSD', '3 个尺度：原始、×2 平均池化、×4', '一维卷积，看不同时间分辨率')
    txt(o, 14, 262, '损失：最小二乘对抗 + 特征匹配 + 梅尔谱 L1（12 节公式）。MPD 利用语音的周期性，MSD 看长程结构。', T3, 10)
    txt(o, 14, 278, '核对：speechbrain 的 HifiganGenerator 示例输入 33 帧输出 8448 点（=33×256）；MPD 周期取自 MultiPeriodDiscriminator 源码。', T3, 10)
    return svg(W, H, o, 'HiFi-GAN 结构图：生成器、多周期与多尺度判别器')


# ── 10 EnCodec ───────────────────────────────────────────────────
def f_encodec():
    d = N['encodec']; ch = d['chans']; ln = d['lens']
    o = []; W, H = 700, 300
    box(o, 14, 30, 70, 56, T2, '波形', '', '[1,%d]' % d['N'])
    box(o, 98, 30, 64, 56, C1, 'conv k7', '', '[32,%d]' % ln[0])
    arr(o, 84, 58, 98, 58)
    x = 176
    for i, r in enumerate([2, 4, 5, 8]):
        box(o, x, 30, 72, 56, C1, '下采样 s%d' % r, '通道×2', '[%d,%d]' % (ch[i + 1], ln[i + 1]))
        arr(o, x - 14, 58, x - 1, 58)
        x += 82
    box(o, x, 30, 80, 56, C2, 'LSTM + conv', '512→128', '[128,%d]' % ln[-1])
    arr(o, x - 14, 58, x - 1, 58)
    txt(o, 14, 108, '编码器（SEANet）：总步长 2×4×5×8 = %d，帧率 %d Hz。' % (d['hop'], d['frame_rate']), T3, 10)
    txt(o, 14, 132, '残差矢量量化（RVQ）：每帧 128 维向量，逐级量化残差：', TX, 10.5, weight='600')
    for k in range(4):
        bx = 14 + k * 112
        box(o, bx, 144, 100, 40, C3, '码本 %d' % (k + 1), '1024 项 = 10 bit' if k < 3 else '… 共 n_q 级')
        if k:
            arr(o, bx - 12, 164, bx - 1, 164)
    txt(o, 14, 204, '解码器与编码器镜像（转置卷积），输出 [1, %d]。' % d['N'], T3, 10)
    nq = d['nq']
    txt(o, 14, 228, '目标带宽 → 码本数 n_q = 1000·带宽 // (帧率 × 10)：' + '；'.join('%s kbps → %d' % (k, v) for k, v in nq.items()), T3, 10)
    txt(o, 14, 246, '6 kbps 时 n_q = %d，一段 3 s 音频编码为 [%d, %d] 的整数矩阵（%d 个 token）；码率 %d × %d × %d = %d bit/s。' % (nq['6'], nq['6'], ln[-1], nq['6'] * ln[-1], nq['6'], d['bits'], d['frame_rate'], nq['6'] * d['bits'] * d['frame_rate']), T3, 10)
    return svg(W, H, o, 'EnCodec 结构图：SEANet 编码器、RVQ、解码器')


# ── 11 条件流匹配声学模型（概念图，未对照具体论文）──────────────
def f_cfm():
    o = []; W, H = 700, 250
    box(o, 14, 30, 100, 56, T2, '文本 / 音素', '', '[m] → 嵌入 [m,D]')
    box(o, 14, 130, 100, 56, T2, '噪声样本 x₀', 'N(0, I)', '[T, 80]')
    box(o, 160, 80, 120, 56, C1, '条件拼接', '展开 + 说话人/提示', '[T, D+80]')
    arr(o, 114, 58, 160, 100); arr(o, 114, 158, 160, 118)
    box(o, 316, 80, 150, 56, C2, '向量场网络 v_θ', 'U-Net 或 Transformer', '输入 (x_t, t, c) → [T,80]')
    arr(o, 280, 108, 316, 108)
    box(o, 502, 80, 90, 56, C3, 'ODE 积分', 'NFE 步欧拉', 'x_{t+Δ}=x_t+Δ·v')
    arr(o, 466, 108, 502, 108)
    box(o, 610, 80, 76, 56, T2, '梅尔谱', '', '[T, 80]')
    arr(o, 592, 108, 610, 108)
    poly(o, [(546, 136), (546, 180), (390, 180), (390, 136)], dash='3 3', col=T3)
    txt(o, 470, 196, '迭代 NFE 次（每步一次前向；带引导则两次）', T3, 9.5, 'middle')
    txt(o, 14, 232, '概念图：只表达条件流匹配声学模型的数据流，没有对照具体论文或实现，不给超参数。训练目标见 11 节、19 节。', T3, 10)
    return svg(W, H, o, '条件流匹配声学模型的数据流（概念图）')


for k, f in (('dfn2', f_dfn2), ('dccrn', f_dccrn), ('tasnet', f_tasnet), ('conformer', f_conformer), ('rnnt', f_rnnt), ('w2v2', f_w2v2),
             ('ecapa', f_ecapa), ('fs2', f_fs2), ('hifigan', f_hifigan), ('encodec', f_encodec), ('cfm', f_cfm)):
    OUT[k] = f()
json.dump(OUT, open('figs_nn.json', 'w'), ensure_ascii=False)
print(list(OUT))
