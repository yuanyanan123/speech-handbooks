#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中文 G2P 的真实统计：多音字到底有多严重、频率先验能走多远、变调规则触发多频繁。
   语料 = pypinyin 自带的 47111 条词组表（每条词组的读音是人工标注的），
   把它当成一份"带正确读音标注的语料"，所有数都可复算。"""
import json, math, collections
from pypinyin.constants import PINYIN_DICT, PHRASES_DICT

OUT = {}
OUT['dict'] = {'chars': len(PINYIN_DICT), 'phrases': len(PHRASES_DICT)}
print('单字表 %d 字，词组表 %d 条' % (len(PINYIN_DICT), len(PHRASES_DICT)))

# ══ ① 字表层面：多少字是多音字 ═══════════════════════════════
multi = {chr(k): v.split(',') for k, v in PINYIN_DICT.items()}
n_multi = sum(1 for v in multi.values() if len(v) > 1)
OUT['char_level'] = {'total': len(multi), 'poly': n_multi,
                     'poly_pct': round(n_multi / len(multi) * 100, 2)}
print('\n① 字表里 %d / %d = %.2f%% 的字有多个读音'
      % (n_multi, len(multi), n_multi / len(multi) * 100))

# ══ ② 语料层面：按出现次数加权，多音字占多少 ═══════════════
occ = collections.Counter()          # 字 → 出现次数
rd = collections.defaultdict(collections.Counter)   # 字 → {读音: 次数}
for w, py in PHRASES_DICT.items():
    for ch, p in zip(w, py):
        if not p:
            continue
        occ[ch] += 1
        rd[ch][p[0]] += 1

tot_occ = sum(occ.values())
poly_occ = sum(c for ch, c in occ.items() if len(rd[ch]) > 1)
OUT['token_level'] = {'total': tot_occ, 'poly': poly_occ,
                      'poly_pct': round(poly_occ / tot_occ * 100, 2)}
print('② 按词组里的实际出现次数加权：%d / %d = %.2f%% 的字位是多音字'
      % (poly_occ, tot_occ, poly_occ / tot_occ * 100))
print('   （字表里只有 %.1f%%，但常用字更容易是多音字——这就是它难缠的原因）'
      % OUT['char_level']['poly_pct'])

# ══ ③ 频率先验基线：永远读最常见的那个音 ═══════════════════
best = {ch: c.most_common(1)[0][0] for ch, c in rd.items()}
ok = sum(c[best[ch]] for ch, c in rd.items())
OUT['prior'] = {'char_acc': round(ok / tot_occ * 100, 3),
                'char_err': round((tot_occ - ok) / tot_occ * 100, 3)}
# 只看多音字上的表现
pol = [ch for ch in rd if len(rd[ch]) > 1]
ok_p = sum(rd[ch][best[ch]] for ch in pol)
tot_p = sum(sum(rd[ch].values()) for ch in pol)
OUT['prior']['poly_acc'] = round(ok_p / tot_p * 100, 2)
print('\n③ 只用"频率先验"（每个字永远读最常见的那个音）：')
print('   全部字位 正确率 %.3f%%   错误率 %.3f%%' % (OUT['prior']['char_acc'], OUT['prior']['char_err']))
print('   只看多音字 正确率 %.2f%%' % OUT['prior']['poly_acc'])
# 整句（整条词组）全对的比例
full = sum(1 for w, py in PHRASES_DICT.items()
           if all(p and best.get(ch) == p[0] for ch, p in zip(w, py)))
OUT['prior']['phrase_acc'] = round(full / len(PHRASES_DICT) * 100, 2)
print('   整条词组全对 %.2f%%  ← 字级 99%% 不代表句子对'
      % OUT['prior']['phrase_acc'])

# 基线 A：直接取单字表里的第一个读音（最朴素的实现）
first = {}
for k, v in PINYIN_DICT.items():
    first[chr(k)] = v.split(',')[0]


okA = sum(c.get(first.get(ch, ''), 0) for ch, c in rd.items())
OUT['naive'] = {'char_acc': round(okA / tot_occ * 100, 3)}
print('   对照：直接取单字表第一个读音 正确率 %.3f%%（频率先验 %.3f%%）'
      % (OUT['naive']['char_acc'], OUT['prior']['char_acc']))

# ══ ④ 错误集中在谁身上 ═══════════════════════════════════════
err = [(ch, sum(c.values()) - c[best[ch]], sum(c.values()), c) for ch, c in rd.items()
       if len(c) > 1]
err.sort(key=lambda x: -x[1])
tot_err = sum(e[1] for e in err)
cum, k50, k80 = 0, None, None
for i, e in enumerate(err, 1):
    cum += e[1]
    if k50 is None and cum >= tot_err * .5:
        k50 = i
    if k80 is None and cum >= tot_err * .8:
        k80 = i
OUT['tail'] = {'poly_chars': len(err), 'err_tokens': tot_err, 'k50': k50, 'k80': k80}
print('\n④ %d 个多音字一共贡献 %d 次错误；' % (len(err), tot_err))
print('   前 %d 个字占一半的错，前 %d 个字占八成 ← 长尾没那么长，值得逐字治'
      % (k50, k80))
OUT['top'] = []
for ch, e, n, c in err[:12]:
    tops = c.most_common(3)
    ent = -sum(v / n * math.log2(v / n) for v in c.values())
    OUT['top'].append({'ch': ch, 'err': e, 'n': n, 'H': round(ent, 2),
                       'rd': [[p, v] for p, v in tops]})
print('\n   最难的十二个字（按错误次数）：')
print('   字  出现  错  熵(bit)  读音分布')
for t in OUT['top']:
    print('   %s  %5d %5d   %.2f   %s' % (t['ch'], t['n'], t['err'], t['H'],
          '  '.join('%s %d' % (p, v) for p, v in t['rd'])))

# 加权平均熵：一个多音字平均要几 bit 才能定下来
Hbar = sum(sum(c.values()) * (-sum(v / sum(c.values()) * math.log2(v / sum(c.values()))
           for v in c.values())) for ch, c in rd.items() if len(c) > 1) / tot_p
OUT['entropy_bits'] = round(Hbar, 3)
print('\n   多音字字位的平均条件熵 %.3f bit ← 上下文必须提供这么多信息' % Hbar)

# ══ ⑤ 变调规则的触发率 ═══════════════════════════════════════
def tone(p):
    for c in p:
        if c in '1234':
            return c
    return '0'


# pypinyin 的词组表已经是"变调后"的表面读音，可以直接数
yi = collections.Counter(); bu = collections.Counter()
for w, py in PHRASES_DICT.items():
    for ch, p in zip(w, py):
        if not p:
            continue
        if ch == '一':
            yi[p[0]] += 1
        if ch == '不':
            bu[p[0]] += 1
OUT['sandhi'] = {'yi': yi.most_common(4), 'bu': bu.most_common(4)}
print('\n⑤ 变调：词组表里"一"和"不"的表面读音分布')
print('   一：', '  '.join('%s %d' % kv for kv in yi.most_common(4)))
print('   不：', '  '.join('%s %d' % kv for kv in bu.most_common(4)))
yi_alt = 1 - yi.most_common(1)[0][1] / sum(yi.values())
bu_alt = 1 - bu.most_common(1)[0][1] / sum(bu.values())
OUT['sandhi']['yi_alt_pct'] = round(yi_alt * 100, 1)
OUT['sandhi']['bu_alt_pct'] = round(bu_alt * 100, 1)
print('   "一"有 %.1f%% 的出现不是本调，"不"有 %.1f%%——规则触发率很高，不是边角料'
      % (yi_alt * 100, bu_alt * 100))

# 三声连读：相邻两个三声的出现频率
from pypinyin.style._utils import get_finals  # noqa
t3 = 0; pairs = 0
for w, py in PHRASES_DICT.items():
    tones = []
    for p in py:
        if not p:
            tones.append('0'); continue
        s = p[0]
        # 带调号的拼音 → 调号
        tones.append('3' if any(m in s for m in 'ǎěǐǒǔǚ') else 'x')
    for a, b in zip(tones, tones[1:]):
        pairs += 1
        if a == '3' and b == '3':
            t3 += 1
OUT['sandhi']['t3t3_pct'] = round(t3 / pairs * 100, 2)
OUT['sandhi']['t3t3_n'] = t3
print('   相邻两字都是三声的情形占全部相邻字对的 %.2f%%（%d 处）——'
      % (t3 / pairs * 100, t3))
print('   这些位置前一个字必须读成二声，而标注里写的还是三声：'
      '<strong>规则在拼音标注之外</strong>')

# ══ ⑥ 儿化 ═══════════════════════════════════════════════════
er = sum(1 for w, py in PHRASES_DICT.items() if w.endswith('儿'))
OUT['erhua'] = {'phrases': er, 'pct': round(er / len(PHRASES_DICT) * 100, 2)}
print('\n⑥ 以"儿"结尾的词条 %d 条（%.2f%%）——儿化要不要合并到前一个音节，'
      % (er, er / len(PHRASES_DICT) * 100))
print('   决定了音素序列长度，直接影响时长模型')

json.dump(OUT, open('demo_g2p.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_g2p.json')
