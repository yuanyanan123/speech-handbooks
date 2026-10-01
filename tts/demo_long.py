#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""32 节算例：长文本——一次生成多长，上下文、显存与算力各自在哪里撞墙；分段要付什么代价。

   不训练任何东西，把乘加和字节数点出来（和 23 节同一个做法）。
   输入里只有 token 速率是本书实测的（19 节 RVQ：每秒 86.1 帧 × 码本级数）；
   解码器的形状是<strong>假设</strong>的一个典型值（24 层、d=1024、fp16，仿 LLM-TTS 常见规模），
   换一组参数把常量改一行重跑即可——重点是平方项什么时候压过线性项，而不是小数点后一位。
"""
import json
import numpy as np

OUT = {}
RVQ = json.load(open('demo_rvq.json'))
CK = json.load(open('demo_chunk.json'))
LAYERS, D = 24, 1024
BYTES = 2                                      # fp16
LIN = 12 * D * D * LAYERS                      # 每个 token 的线性层乘加（QKVO 4d² + MLP 8d²）
KV_PER_TOK = 2 * LAYERS * D * BYTES            # K 与 V

LADDER = {r['nq']: r for r in RVQ['ladder']}
OUT['const'] = {'layers': LAYERS, 'd': D, 'bytes': BYTES, 'lin_per_tok': LIN, 'kv_per_tok': KV_PER_TOK,
                'fps': RVQ['data']['fps'], 'tok_s': {str(k): LADDER[k]['tok_s'] for k in (1, 4, 8) if k in LADDER}}
print('每个 token：线性层 %.2f MMAC，KV %.0f KB' % (LIN / 1e6, KV_PER_TOK / 1024))

# ① 一次生成 D 秒：上下文长度、KV 显存、注意力 vs 线性乘加
DURS = (10, 30, 120, 600, 3600)
NQS = (1, 4, 8)
OUT['single'] = []
for nq in NQS:
    ts = LADDER[nq]['tok_s']
    for sec in DURS:
        n = ts * sec
        kv = n * KV_PER_TOK / 1e9
        att = LAYERS * D * n * n                      # 生成 n 个 token，第 i 个对前 i 个做注意力：Σ 2·i·d·layers ≈ layers·d·n²
        lin = n * LIN
        OUT['single'].append({'nq': nq, 'tok_s': ts, 'sec': sec, 'tokens': int(n), 'kv_gb': round(kv, 2),
                              'att_tmac': round(att / 1e12, 2), 'lin_tmac': round(lin / 1e12, 2),
                              'att_over_lin': round(att / lin, 2)})
S = {(r['nq'], r['sec']): r for r in OUT['single']}
# 注意力 = 线性 的交叉点：n = 12 d
cross_tok = 12 * D
OUT['cross'] = {'tokens': cross_tok, 'sec_nq4': round(cross_tok / LADDER[4]['tok_s'], 1), 'sec_nq8': round(cross_tok / LADDER[8]['tok_s'], 1),
                'sec_nq1': round(cross_tok / LADDER[1]['tok_s'], 1)}
print('注意力乘加追平线性层的上下文长度 n=12d=%d token：nq=1 %.0f s，nq=4 %.0f s，nq=8 %.0f s'
      % (cross_tok, OUT['cross']['sec_nq1'], OUT['cross']['sec_nq4'], OUT['cross']['sec_nq8']))

# ② 分段：每段 c 秒，带 p 秒上一段的尾巴当提示
TOTAL = 600                                       # 十分钟
nq = 4
ts = LADDER[nq]['tok_s']
OUT['chunk'] = []
print('\n十分钟、nq=%d（%.1f token/s），分段 c 秒 + 提示 p 秒' % (nq, ts))
n_single = ts * TOTAL
att_single = LAYERS * D * n_single ** 2
lin_single = n_single * LIN
for c in (10, 30, 60, 120):
    for p in (0, 2, 5):
        k = int(np.ceil(TOTAL / c))
        n_ctx = ts * (c + p)
        # 每段：提示 token 只需前向一次（prefill，线性），生成 c 秒的 token，注意力对（提示 + 已生成）
        att = k * LAYERS * D * (ts * c) * (ts * p * 2 + ts * c) / 1.0   # 近似：Σ_i 2·(p_tok + i)·d·layers ≈ layers·d·(2 p_tok n + n²) 的 1/2×2
        lin = k * (ts * (c + p)) * LIN
        kv = n_ctx * KV_PER_TOK / 1e9
        OUT['chunk'].append({'c': c, 'p': p, 'chunks': k, 'ctx_tok': int(n_ctx), 'kv_gb': round(kv, 2),
                             'att_tmac': round(att / 1e12, 3), 'lin_tmac': round(lin / 1e12, 3),
                             'total_tmac': round((att + lin) / 1e12, 3),
                             'rel': round((att + lin) / (att_single + lin_single), 4),
                             'overhead_pct': round(100 * p / c, 1)})
        print('  c=%3d s p=%d s  段数 %2d  上下文 %6d token  KV %.2f GB  总乘加 %.2f T（单次的 %.1f%%）'
              % (c, p, k, n_ctx, kv, OUT['chunk'][-1]['total_tmac'], 100 * OUT['chunk'][-1]['rel']))
OUT['single10min'] = {'tokens': int(n_single), 'kv_gb': round(n_single * KV_PER_TOK / 1e9, 1),
                      'att_tmac': round(att_single / 1e12, 1), 'lin_tmac': round(lin_single / 1e12, 1),
                      'ratio': round(att_single / lin_single, 1)}
print('十分钟一次生成：%d token，KV %.1f GB，注意力 %.1f T 乘加 / 线性 %.1f T（%.1f 倍）'
      % (n_single, OUT['single10min']['kv_gb'], OUT['single10min']['att_tmac'], OUT['single10min']['lin_tmac'], OUT['single10min']['ratio']))

C = {(r['c'], r['p']): r for r in OUT['chunk']}
OUT['note'] = {
    'tok_s4': LADDER[4]['tok_s'], 'tok_s8': LADDER[8]['tok_s'], 'tok_s1': LADDER[1]['tok_s'],
    'tok_10s_nq4': S[(4, 10)]['tokens'], 'tok_10s_nq8': S[(8, 10)]['tokens'],
    'kv_per_tok_kb': round(KV_PER_TOK / 1024), 'lin_mmac': round(LIN / 1e6, 1),
    'cross_tok': cross_tok, 'cross_sec_nq4': OUT['cross']['sec_nq4'], 'cross_sec_nq8': OUT['cross']['sec_nq8'],
    'h1_nq4_tok': S[(4, 3600)]['tokens'], 'h1_nq4_kv': S[(4, 3600)]['kv_gb'],
    'm10_tok': OUT['single10min']['tokens'], 'm10_kv': OUT['single10min']['kv_gb'],
    'm10_ratio': OUT['single10min']['ratio'],
    'c30p5_rel': C[(30, 5)]['rel'], 'c30p5_kv': C[(30, 5)]['kv_gb'], 'c30p0_rel': C[(30, 0)]['rel'],
    'c10p5_rel': C[(10, 5)]['rel'], 'c60p5_rel': C[(60, 5)]['rel'], 'c120p5_rel': C[(120, 5)]['rel'],
    'c30p5_ctx': C[(30, 5)]['ctx_tok'], 'c30p5_overhead': C[(30, 5)]['overhead_pct'],
    'seam_db': CK['xfade'][0]['db'], 'seam_xf': CK['xfade'][-1]['db'],
}
print(json.dumps(OUT['note'], ensure_ascii=False))
json.dump(OUT, open('demo_long.json', 'w'), ensure_ascii=False)
print('写出 demo_long.json')
