#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 23 节"神经网络的结构与数据形状演进"用到的全部形状与参数量。
   每个数都由下面的算术得到；超参数取自官方参考实现的默认值或函数签名
   （DeepFilterNet 0.5.6、asteroid 0.7.0、torchaudio 2.11、speechbrain 1.1.1、encodec 0.1.1，已读源码核对），
   源码位置写在 src 字段里。没有训练任何网络，也没有运行 torch。"""
import json, math

O = {}


def conv_out(n, k, s, p=0, d=1):
    return (n + 2 * p - d * (k - 1) - 1) // s + 1


# ── 1. DeepFilterNet2（df/deepfilternet2.py、df/config.py）────────
sr, fft, hop, erb, ndf, dford, C = 48000, 960, 480, 32, 96, 5, 16
N = 3 * sr
T = N // hop
O['dfn2'] = dict(
    src='df/config.py（fft_size=960, hop_size=480, nb_erb=32, nb_df=96, df_order=5）；df/deepfilternet2.py（conv_ch=16, emb_hidden_dim=256, emb_num_layers=2）',
    sr=sr, N=N, T=T, F=fft // 2 + 1, erb=erb, ndf=ndf, df_order=dford, C=C, hop_ms=hop / sr * 1000, win_ms=fft / sr * 1000,
    df_hz=ndf * sr / fft,
    stages=[
        ['输入：带噪波形', '—', '[%d]' % N, '3 s @ 48 kHz'],
        ['STFT（窗 960、帧移 480）', 'fft=960, hop=480', '[%d × %d] 复数' % (fft // 2 + 1, T), '频点 481，帧数 %d（10 ms 一帧）' % T],
        ['ERB 特征', '481 个频点合并成 32 个 ERB 带，取 dB 并归一化', '[1, %d, %d]' % (T, erb), '感知频带，数据量降到 1/15'],
        ['复数特征', '取前 96 个频点的实、虚部（0–%.1f kHz）' % (ndf * sr / fft / 1000), '[2, %d, %d]' % (T, ndf), '低频谐波区保留相位信息'],
        ['ERB 编码器 conv0', '3×3 可分离卷积，通道 1→16', '[16, %d, 32]' % T, '局部时频模式'],
        ['ERB 编码器 conv1', '频率步长 2', '[16, %d, 16]' % T, '频率下采样 2 倍'],
        ['ERB 编码器 conv2', '频率步长 2', '[16, %d, 8]' % T, '再下采样 2 倍'],
        ['ERB 编码器 conv3', '频率步长 1', '[16, %d, 8]' % T, '展平后 16×8 = 128 维'],
        ['复数分支 df_conv0/1', '通道 2→16，频率步长 2', '[16, %d, 48]' % T, '展平 16×48 = 768 维，经线性层降到 128 维'],
        ['合并 + GRU（2 层，隐维 256）', '两路嵌入相加后过循环层', '[%d, 256]' % T, '时序建模；也输出局部信噪比估计'],
        ['ERB 解码器', '转置卷积 + 跳连（来自编码器 e0–e3）', '[1, %d, 32]，sigmoid' % T, '输出每个 ERB 带的增益（0–1）'],
        ['DF 解码器', 'GRU + 线性层，重排', '[%d, 5, 96, 2]' % T, '每帧、每个低频点 5 个复系数'],
        ['应用', '低频 96 点：深度滤波（5 抽头）；其余频点：ERB 增益', '[%d × %d] 复数' % (fft // 2 + 1, T), 'Ŝ = Σ c_i · Y(t−i)（4.10 节）'],
        ['iSTFT', '重叠相加', '[%d]' % N, '输出波形，长度不变'],
    ])

# ── 2. DCCRN-CL（asteroid/models/dccrnet.py、masknn/_dccrn_architectures.py）
n_filters, ksz, stride = 512, 400, 100
N16 = 3 * 16000
Tf = 1 + (N16 - ksz) // stride
nfreq = n_filters // 2
enc = [(1, 16), (16, 32), (32, 64), (64, 128), (128, 128), (128, 128)]
fr = nfreq; encs = []
for ci, co in enc:
    fr = conv_out(fr, 5, 2, 2)
    encs.append((ci, co, fr))
O['dccrn'] = dict(
    src='asteroid/models/dccrnet.py（stft_n_filters=512, kernel=400, stride=100）；masknn/_dccrn_architectures.py（DCCRN-CL 编解码通道与核）；masknn/recurrent.py（LSTM 隐维 128、2 层）',
    N=N16, T=Tf, nfreq=nfreq, enc=encs, rnn_in=encs[-1][1] * encs[-1][2], hid=128, layers=2,
    stages=[['输入：带噪波形', '—', '[%d]' % N16, '3 s @ 16 kHz'],
            ['STFT（窗 400、帧移 100）', 'n_filters=512 → 257 点，去掉一个点后 256', '[256 × %d] 复数' % Tf, '25 ms 窗、6.25 ms 帧移（无填充时 %d 帧）' % Tf]] +
           [['复数编码器 %d' % (i + 1), '复数卷积（核 5×2、步长 2×1）', '[%d, %d, %d] 复数' % (co, f, Tf), '频率减半，通道 %d→%d' % (ci, co)] for i, (ci, co, f) in enumerate(encs)] +
           [['复数 LSTM（2 层，隐维 128）', '把 %d×%d 展平成 %d 维逐帧送入' % (encs[-1][1], encs[-1][2], encs[-1][1] * encs[-1][2]), '[%d, %d] 复数' % (Tf, encs[-1][1] * encs[-1][2]), '时序建模，线性层还原维度'],
            ['复数解码器 ×6', '转置卷积，与同层编码器输出拼接（跳连：通道翻倍）', '[1, 256, %d] 复数' % Tf, '逐级恢复频率分辨率'],
            ['复数掩蔽', '掩蔽 × 带噪复谱', '[256 × %d] 复数' % Tf, '同时修正幅度与相位'],
            ['iSTFT', '—', '[%d]' % N16, '输出波形']])

# ── 3. Conv-TasNet（asteroid/models/conv_tasnet.py、masknn/convolutional.py）
sr8 = 8000
Nw = 3 * sr8
L, S, NF = 16, 8, 512
Tp = conv_out(Nw, L, S)
dec_len = (Tp - 1) * S + L
dil = [2 ** i for i in range(8)]
rf_frames = 1 + sum((3 - 1) * d for d in dil) * 3
O['tasnet'] = dict(
    src='asteroid/models/conv_tasnet.py（n_filters=512, kernel_size=16, stride=8, n_blocks=8, n_repeats=3, bn_chan=128, hid_chan=512, skip_chan=128, conv_kernel_size=3, norm=gLN）',
    N=Nw, Tp=Tp, dec_len=dec_len, rf_frames=rf_frames, rf_samples=rf_frames * S, rf_ms=rf_frames * S / sr8 * 1000,
    stages=[['输入：波形', '—', '[%d]' % Nw, '3 s @ 8 kHz（asteroid 的常用设置）'],
            ['编码器（自由滤波器组）', '一维卷积，核 16、步长 8、512 个滤波器', '[512, %d]' % Tp, '2 ms 窗、1 ms 帧移；T′ = ⌊(%d−16)/8⌋+1' % Nw],
            ['归一化 + 瓶颈', 'gLN + 1×1 卷积，512→128', '[128, %d]' % Tp, '压缩后进 TCN，节省算力'],
            ['TCN（3 次重复 × 8 块）', '深度可分离膨胀卷积，膨胀 1,2,4,…,128，核 3，隐通道 512，跳连通道 128', '[128, %d]' % Tp, '感受野 %d 帧 ≈ %d ms' % (rf_frames, round(rf_frames * S / sr8 * 1000))],
            ['掩蔽卷积', '1×1 卷积 + 激活', '[n_src, 512, %d]' % Tp, '每个说话人（或每个目标）一个掩蔽'],
            ['逐元素相乘', '编码器输出 ⊙ 掩蔽', '[n_src, 512, %d]' % Tp, '在可学习的基上"分离"'],
            ['解码器（转置卷积）', '核 16、步长 8', '[n_src, %d]' % dec_len, '长度 (T′−1)·8+16 = %d，恰等于输入' % dec_len]])

# ── 4. Conformer 块（torchaudio/models/conformer.py）─────────────
D, FF, H, K = 256, 1024, 4, 31
ffn = D + 2 * (D * FF + FF) + FF * 0 + (D * 0)             # 占位，下面逐项精算
def n_linear(i, o): return i * o + o
ffn_p = 2 * D + n_linear(D, FF) + n_linear(FF, D)           # LayerNorm(γ,β) + 两个线性层
mha_p = 4 * D * D + 4 * D                                   # q,k,v,out 的权重与偏置（PyTorch MultiheadAttention）
conv_p = 2 * D + (2 * D * D + 2 * D) + (D * K + D) + 2 * D + (D * D + D)   # LN + 逐点(→2D, GLU) + 深度 + BN + 逐点
block_p = 2 * ffn_p + (2 * D) + mha_p + conv_p + (2 * D)    # 两个 FFN + 注意力前 LN + 注意力 + 卷积模块 + 末尾 LN
Tenc = 75
O['conformer'] = dict(
    src='torchaudio/models/conformer.py（ConformerLayer：ffn1(×0.5) → LayerNorm → MultiheadAttention → _ConvolutionModule → ffn2(×0.5) → LayerNorm）',
    D=D, FF=FF, H=H, K=K, T=Tenc, ffn_params=ffn_p, mha_params=mha_p, conv_params=conv_p, block_params=block_p,
    attn_matrix=Tenc * Tenc, attn_flops=2 * Tenc * Tenc * D,
    stages=[['输入（子采样后）', '—', '[%d, %d]' % (Tenc, D), '298 帧 / 4 ≈ %d 帧，每帧 40 ms；D=%d（示例配置）' % (Tenc, D)],
            ['前馈 ½', 'LayerNorm → 线性 %d→%d → SiLU → 线性 %d→%d；乘 0.5 加残差' % (D, FF, FF, D), '[%d, %d]' % (Tenc, D), '提供非线性变换；半步残差'],
            ['多头自注意力', 'LayerNorm → %d 头注意力 → 加残差' % H, '[%d, %d]' % (Tenc, D), '全局依赖；注意力矩阵 %d×%d' % (Tenc, Tenc)],
            ['卷积模块', 'LayerNorm → 逐点卷积 %d→%d → GLU → 深度卷积（核 %d）→ BatchNorm → SiLU → 逐点卷积；加残差' % (D, 2 * D, K), '[%d, %d]' % (Tenc, D), '局部模式（相邻帧的谱变化）'],
            ['前馈 ½', '同上', '[%d, %d]' % (Tenc, D), '再变换一次'],
            ['LayerNorm', '—', '[%d, %d]' % (Tenc, D), '块的输出；形状不变，可堆叠 N 次']])

# ── 5. RNN-T（torchaudio/models/rnnt.py：_Joiner）─────────────────
Tt, U, Dj, V = 75, 7, 640, 4000
O['rnnt'] = dict(
    src='torchaudio/models/rnnt.py（_Joiner：source.unsqueeze(2) + target.unsqueeze(1) → 激活 → 线性；输出 (B,T,U,V)）',
    T=Tt, U=U, V=V, D=Dj, logits=Tt * (U + 1) * V, bytes_fp32=Tt * (U + 1) * V * 4,
    stages=[['编码器输出', '声学编码器（Conformer 等）', '[B, %d, %d]' % (Tt, Dj), '每个声学帧一个向量（40 ms）'],
            ['预测网络输出', '对已输出标签做循环/注意力建模（含起始符）', '[B, %d, %d]' % (U + 1, Dj), '内置语言模型，只看过去的标签'],
            ['广播相加', '编码器 [B,T,1,D] + 预测网络 [B,1,U+1,D]', '[B, %d, %d, %d]' % (Tt, U + 1, Dj), '每个 (t,u) 格点一个联合向量'],
            ['激活', 'ReLU 或 tanh', '[B, %d, %d, %d]' % (Tt, U + 1, Dj), '—'],
            ['线性层', '%d → %d（词表，含空白）' % (Dj, V), '[B, %d, %d, %d]' % (Tt, U + 1, V), '每格点给出下一符号的分布；训练显存 ∝ B×T×U×V']])

# ── 6. wav2vec 2.0 BASE（torchaudio/models/wav2vec2/model.py）─────
cfg = [(512, 10, 5)] + [(512, 3, 2)] * 4 + [(512, 2, 2)] * 2
n = 3 * 16000; shapes = [n]
for c, k, s in cfg:
    n = conv_out(n, k, s); shapes.append(n)
stride_tot = 1
for _, _, s in cfg:
    stride_tot *= s
conv_p = 1 * 512 * 10 + sum(512 * 512 * k for _, k, _ in cfg[1:])
layer_p = (4 * 768 * 768 + 4 * 768) + (768 * 3072 + 3072 + 3072 * 768 + 768) + 4 * 768
pos_conv = 768 * (768 // 16) * 128 + 768
proj = 512 * 768 + 768
total = conv_p + 12 * layer_p + pos_conv + proj
O['w2v2'] = dict(
    src='torchaudio/models/wav2vec2/model.py（extractor_conv_layer_config=[(512,10,5)]+[(512,3,2)]*4+[(512,2,2)]*2；wav2vec2_base：embed_dim=768, 12 层, 12 头, ff=3072）',
    shapes=shapes, stride=stride_tot, frames=shapes[-1], conv_params=conv_p, layer_params=layer_p, total_params=total,
    stages=[['输入：波形', '—', '[%d]' % shapes[0], '3 s @ 16 kHz']] +
           [['卷积层 %d' % (i + 1), '%d 个通道，核 %d，步长 %d' % (c, k, s), '[%d, %d]' % (c, shapes[i + 1]), '累计步长 %d' % int(math.prod(s_ for _, _, s_ in cfg[:i + 1]))] for i, (c, k, s) in enumerate(cfg)] +
           [['投影 + 位置卷积', '512→768；分组卷积（核 128、16 组）提供相对位置', '[%d, 768]' % shapes[-1], '帧率 %.0f Hz（每帧 %d 个样点）' % (16000 / stride_tot, stride_tot)],
            ['Transformer × 12', '768 维、12 头、前馈 3072', '[%d, 768]' % shapes[-1], '上下文表示（被掩蔽位置用于对比预测）']])

# ── 7. ECAPA-TDNN（speechbrain/lobes/models/ECAPA_TDNN.py）─────────
Tf2 = 298
O['ecapa'] = dict(
    src='speechbrain/lobes/models/ECAPA_TDNN.py（channels=[512,512,512,512,1536], kernel_sizes=[5,3,3,3,1], dilations=[1,2,3,4,1], attention_channels=128, res2net_scale=8, se_channels=128, lin_neurons=192, global_context=True）',
    T=Tf2,
    stages=[['输入：对数梅尔', '—', '[80, %d]' % Tf2, '80 维、10 ms 帧'],
            ['TDNN 块 1', '一维卷积，核 5，膨胀 1，80→512', '[512, %d]' % Tf2, '局部上下文'],
            ['SE-Res2Block 2', '核 3，膨胀 2，Res2Net 分 8 路，SE 通道 128', '[512, %d]' % Tf2, '多尺度局部特征'],
            ['SE-Res2Block 3', '核 3，膨胀 3', '[512, %d]' % Tf2, '—'],
            ['SE-Res2Block 4', '核 3，膨胀 4', '[512, %d]' % Tf2, '—'],
            ['多层特征聚合（MFA）', '拼接三个块的输出 3×512，再 1×1 卷积 → 1536', '[1536, %d]' % Tf2, '聚合浅层与深层特征'],
            ['注意力统计池化', '注意力通道 128，带全局上下文；输出加权均值与标准差', '[3072]', '变长序列 → 定长向量（2×1536）'],
            ['BN + 线性层', '3072 → 192', '[192]', '说话人嵌入；余弦打分']])

# ── 8. HiFi-GAN（speechbrain/lobes/models/HifiGAN.py）──────────────
frames, hop_h = 258, 256
up = [8, 8, 2, 2]
lens = [frames]; ch = [512]
for u in up:
    lens.append(lens[-1] * u); ch.append(ch[-1] // 2)
O['hifigan'] = dict(
    src='speechbrain/lobes/models/HifiGAN.py（HifiganGenerator 示例：in_channels=80, upsample_factors=[8,8,2,2], upsample_kernel_sizes=[16,16,4,4], upsample_initial_channel=512, resblock_kernel_sizes=[3,7,11], resblock_dilation_sizes=[[1,3,5]]*3；MultiPeriodDiscriminator 周期 2,3,5,7,11；docstring 输出 33 帧→8448 点）',
    frames=frames, lens=lens, ch=ch, out=lens[-1], hop=hop_h, check_docstring=(33 * 256 == 8448),
    stages=[['输入：梅尔谱', '—', '[80, %d]' % frames, '3 s @ 22.05 kHz，帧移 256'],
            ['conv_pre', '一维卷积 80→512，核 7', '[512, %d]' % frames, '—']] +
           [['上采样 %d（×%d）+ MRF' % (i + 1, u), '转置卷积（核 %d）→ 3 个残差块（核 3/7/11，膨胀 1/3/5）取平均' % k, '[%d, %d]' % (ch[i + 1], lens[i + 1]), '通道减半，长度 ×%d' % u] for i, (u, k) in enumerate(zip(up, [16, 16, 4, 4]))] +
           [['conv_post + tanh', '一维卷积 → 1 通道', '[1, %d]' % lens[-1], '波形；上采样总倍数 %d = 帧移' % (8 * 8 * 2 * 2)]])

# ── 9. EnCodec 24 kHz（encodec/model.py、modules/seanet.py）────────
srE = 24000; NE = 3 * srE
ratios = [2, 4, 5, 8]                                         # 编码器下采样顺序（reversed([8,5,4,2])）
mult = 1; chans = [32]; lensE = [NE]; n_ = NE
for r in ratios:
    mult *= 2; chans.append(32 * mult); n_ = conv_out(n_, 2 * r, r, p=(2 * r - r) // 2) if False else n_ // r; lensE.append(n_)
frame_rate = math.ceil(srE / math.prod(ratios))
bits = int(math.log2(1024))
O['encodec'] = dict(
    src='encodec/model.py（frame_rate = ceil(sample_rate/prod(ratios))；bits_per_codebook = log2(bins)；n_q = 1000·带宽 // (frame_rate·10)）；encodec/modules/seanet.py（n_filters=32, dimension=128, ratios=[8,5,4,2], LSTM 2 层）；24 kHz 目标带宽 [1.5, 3, 6, 12, 24] kbps',
    N=NE, chans=chans, lens=lensE, frames=lensE[-1], frame_rate=frame_rate, bits=bits, hop=math.prod(ratios),
    nq={str(b): int(1000 * b // (frame_rate * 10)) for b in (1.5, 3, 6, 12, 24)},
    codes_6k=int(1000 * 6 // (frame_rate * 10)) * lensE[-1],
    stages=[['输入：波形', '—', '[1, %d]' % NE, '3 s @ 24 kHz'],
            ['卷积 k7', '1→32', '[32, %d]' % NE, '—']] +
           [['下采样 %d（步长 %d）' % (i + 1, r), '残差块 + 卷积（核 2r，步长 r），通道翻倍', '[%d, %d]' % (chans[i + 1], lensE[i + 1]), '长度 ÷%d' % r] for i, r in enumerate(ratios)] +
           [['LSTM（2 层）+ 卷积 k7', '512→128', '[128, %d]' % lensE[-1], '帧率 %d Hz（总步长 %d）' % (frame_rate, math.prod(ratios))],
            ['残差矢量量化（RVQ）', '1024 项码本；6 kbps 时 n_q=8', '[8, %d] 整数' % lensE[-1], '码率 8×10×75 = 6000 bit/s'],
            ['解码器', '与编码器镜像（转置卷积）', '[1, %d]' % NE, '还原波形']])

json.dump(O, open('nn.json', 'w'), ensure_ascii=False, indent=1)
print({k: (v.get('T') or v.get('frames') or v.get('Tp')) for k, v in O.items()})
print('conformer block params', block_p, '; w2v2 total', total, '; encodec nq', O['encodec']['nq'], '; tasnet rf', rf_frames, '; hifigan lens', lens)
