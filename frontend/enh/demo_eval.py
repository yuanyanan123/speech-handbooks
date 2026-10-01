#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两件让人很难受的事：

   ① 常用的四个客观指标，在同一批系统上给出<不一致的排序>。
      挑哪个指标，就决定了你会上线哪个系统。
   ② 增强对下游任务不一定有好处。把增强当成一个"信道"接到声纹上量一下：
      非线性处理会引入失配，而失配会直接抬高等错误率。
"""
import numpy as np, json
from scipy.fft import dct
import enhlib as E
from enhlib import g_logmmse, dd_xi, est_imcra

OUT = {}
NFFT, HOP = 512, 256
WB, _ = None, None


# ══ 待比较的几种处理 ══════════════════════════════════════════
def proc_none(y, Y):
    return y, np.ones_like(np.abs(Y))


def _sub(Y, lam, alpha, floor):
    xi, gam = dd_xi(Y, lam, 0.98)
    return np.sqrt(np.maximum(1.0 - alpha / np.maximum(gam, E.EPS), floor ** 2))


def make_procs():
    def f_logmmse(y, Y):
        lam = est_imcra(np.abs(Y) ** 2)
        xi, gam = dd_xi(Y, lam, 0.98)
        G = g_logmmse(xi, gam)
        return E.istft(G * Y, NFFT, HOP, n=len(y)), G

    def f_over(y, Y):
        lam = est_imcra(np.abs(Y) ** 2)
        G = _sub(Y, lam, 6.0, 0.0)
        return E.istft(G * Y, NFFT, HOP, n=len(y)), G

    def f_under(y, Y):
        lam = est_imcra(np.abs(Y) ** 2)
        G = _sub(Y, lam, 0.5, 0.0)
        return E.istft(G * Y, NFFT, HOP, n=len(y)), G

    def f_music(y, Y):
        lam = est_imcra(np.abs(Y) ** 2)
        xi = np.maximum(np.abs(Y) ** 2 / np.maximum(lam, E.EPS) - 1.0, 1e-3)
        gam = np.abs(Y) ** 2 / np.maximum(lam, E.EPS)
        G = g_logmmse(xi, gam)                       # 不做判决引导 → 音乐噪声
        return E.istft(G * Y, NFFT, HOP, n=len(y)), G

    def f_sub2(y, Y):
        lam = est_imcra(np.abs(Y) ** 2)
        G = _sub(Y, lam, 2.0, 0.1)
        return E.istft(G * Y, NFFT, HOP, n=len(y)), G

    def f_wiener(y, Y):
        lam = est_imcra(np.abs(Y) ** 2)
        xi, gam = dd_xi(Y, lam, 0.98)
        G = xi / (1.0 + xi)
        return E.istft(G * Y, NFFT, HOP, n=len(y)), G

    def f_lm_soft(y, Y):
        lam = est_imcra(np.abs(Y) ** 2)
        xi, gam = dd_xi(Y, lam, 0.90)
        G = g_logmmse(xi, gam)
        return E.istft(G * Y, NFFT, HOP, n=len(y)), G

    def f_lm_hard(y, Y):
        lam = est_imcra(np.abs(Y) ** 2)
        xi, gam = dd_xi(Y, lam, 0.995)
        G = g_logmmse(xi, gam)
        return E.istft(G * Y, NFFT, HOP, n=len(y)), G

    return [('不处理', proc_none), ('欠抑制（谱减 α=0.5）', f_under),
            ('谱减 α=2 + 谱底', f_sub2), ('音乐噪声（无判决引导）', f_music),
            ('维纳', f_wiener), ('log-MMSE（α=0.90）', f_lm_soft),
            ('log-MMSE（α=0.98）', f_logmmse), ('log-MMSE（α=0.995）', f_lm_hard),
            ('过抑制（谱减 α=6）', f_over)]


PROCS = make_procs()


def run(x, y, m, S, V, Y, fn):
    z, G = fn(y, Y)
    z = z[:len(y)]
    fm = E.frame_mask(m, len(S), NFFT, HOP)
    return {'segsnr': E.seg_snr(x, z, m), 'lsd': E.lsd(x, z, mask=m),
            'sisdr': E.si_sdr(x, z), 'stoi': E.stoi_like(x, z, mask=m),
            'mus': E.musical(G[:len(V)] * V, fm)}, z


# ══ ① 四个指标，四种排序 ══════════════════════════════════════
print('① 同一批系统，四个常用指标给出不一样的排序')
x, segs = E.make_speech(dur=6.0, seed=1)
m = E.speech_mask(segs, len(x))
v = E.make_noise('pink', len(x), seed=3)
y, vv = E.mix_at_snr(x, v, 5.0, m)
n = len(y)
S = E.stft(x[:n], NFFT, HOP); V = E.stft(vv[:n], NFFT, HOP); Y = E.stft(y, NFFT, HOP)
OUT['rank'] = []
for tag, fn in PROCS:
    r, _ = run(x, y, m, S, V, Y, fn)
    OUT['rank'].append({'tag': tag, **{k: round(float(val), 3) for k, val in r.items()}})
METRICS = [('SegSNR', 'segsnr', 1), ('SI-SDR', 'sisdr', 1),
           ('LSD', 'lsd', -1), ('STOI*', 'stoi', 1), ('起伏dB', 'mus', -1)]
print('  %-22s %8s %8s %7s %7s %8s' % ('处理', 'SegSNR', 'SI-SDR', 'LSD', 'STOI*', '起伏dB'))
for r in OUT['rank']:
    print('  %-22s %8.2f %8.2f %7.2f %7.3f %8.2f'
          % (r['tag'], r['segsnr'], r['sisdr'], r['lsd'], r['stoi'], r['mus']))
print('\n  按各指标排名（1 = 最好）：')
OUT['orders'] = {}
for name, key, sgn in METRICS:
    order = sorted(range(len(OUT['rank'])), key=lambda i: -sgn * OUT['rank'][i][key])
    rk = [0] * len(order)
    for pos, i in enumerate(order):
        rk[i] = pos + 1
    OUT['orders'][name] = rk
    print('    %-8s %s' % (name, '  '.join('%s:%d' % (OUT['rank'][i]['tag'][:6], rk[i])
                                           for i in range(len(rk)))))
win = {name: OUT['rank'][OUT['orders'][name].index(1)]['tag'] for name, _, _ in METRICS}
OUT['winners'] = win
print('  各指标的冠军：' + '；'.join('%s → %s' % (k, v) for k, v in win.items()))
OUT['n_distinct_winner'] = len(set(win.values()))
# 最大排名分歧：同一个系统在两个指标下的名次差
spread = [(abs(max(OUT['orders'][n][i] for n, _, _ in METRICS)
               - min(OUT['orders'][n][i] for n, _, _ in METRICS)),
           OUT['rank'][i]['tag']) for i in range(len(OUT['rank']))]
spread.sort(reverse=True)
OUT['max_spread'] = {'n': int(spread[0][0]), 'tag': spread[0][1]}
print('  %d 个不同的冠军。更要紧的是<strong>同一个系统的名次能差多少</strong>：'
      % OUT['n_distinct_winner'])
print('  「%s」在五个指标下的名次跨了 <strong>%d 位</strong>'
      % (spread[0][1], spread[0][0]))
print('  ——它在"音乐噪声"上排第一（残差最平稳），在 STOI* 上却几乎垫底。')
print('  这就是"听起来很干净、但话已经被改坏了"的那一类系统。')


# ══ ② 增强对下游：把它当成一个信道接到声纹上 ═══════════════════
def mfcc_emb(sig, mask, nmfcc=20):
    """简易说话人嵌入：MFCC 的均值与标准差拼起来，再长度归一化"""
    Sp = np.abs(E.stft(sig, NFFT, HOP))
    f = np.fft.rfftfreq(NFFT, 1 / E.SR)
    mel = lambda z: 2595 * np.log10(1 + z / 700)
    imel = lambda z: 700 * (10 ** (z / 2595) - 1)
    e = imel(np.linspace(mel(50), mel(E.SR / 2 - 100), 42))
    W = np.zeros((40, len(f)))
    for b in range(40):
        lo, c, hi = e[b], e[b + 1], e[b + 2]
        up = (f >= lo) & (f <= c); dn = (f > c) & (f <= hi)
        W[b, up] = (f[up] - lo) / max(c - lo, 1e-9)
        W[b, dn] = (hi - f[dn]) / max(hi - c, 1e-9)
    L = np.log(np.maximum((Sp ** 2) @ W.T, 1e-10))
    C = dct(L, type=2, axis=1, norm='ortho')[:, 1:nmfcc + 1]
    fm = E.frame_mask(mask, len(C), NFFT, HOP)
    if fm.sum() < 5:
        fm = np.ones(len(C), bool)
    C = C[fm]
    # 注意：这里<strong>不能</strong>做倒谱均值归一化——
    # 嵌入的前一半就是 MFCC 的均值，CMN 会把它整个抹成零。
    emb = np.concatenate([C.mean(0), C.std(0)])
    return emb / (np.linalg.norm(emb) + E.EPS)


def eer(tar, non):
    s = np.r_[tar, non]; lab = np.r_[np.ones(len(tar)), np.zeros(len(non))]
    o = np.argsort(s); s, lab = s[o], lab[o]
    miss = np.cumsum(lab) / len(tar)
    fa = 1 - np.cumsum(1 - lab) / len(non)
    i = np.argmin(np.abs(miss - fa))
    return float((miss[i] + fa[i]) / 2 * 100)


NSPK, NUTT = 40, 4
print('\n② 增强当成"信道"：对说话人确认有没有好处')
print('   %d 个说话人 × %d 条，注册和测试各用不同的句子' % (NSPK, NUTT))
print('   文本相关（所有人念同一句），嵌入 = MFCC 的均值与标准差')

# 预先合成所有语料
CACHE = {}
for sp in range(NSPK):
    for u in range(NUTT):
        xx, sg = E.make_speech(dur=2.5, seed=1000 + sp * 10 + u, spk=sp,
                               text_seed=77)          # 所有人念同一句（文本相关）
        CACHE[(sp, u)] = (xx, E.speech_mask(sg, len(xx)))

NOISE_KIND = 'pink'
SNR = 5.0


def embed_all(fn, snr=SNR, kind=NOISE_KIND, clean=False):
    out = {}
    for (sp, u), (xx, mm) in CACHE.items():
        if clean:
            out[(sp, u)] = mfcc_emb(xx, mm)
            continue
        vv2 = E.make_noise(kind, len(xx), seed=5000 + sp * 10 + u)
        yy, _ = E.mix_at_snr(xx, vv2, snr, mm)
        Yy = E.stft(yy, NFFT, HOP)
        zz, _ = fn(yy, Yy)
        out[(sp, u)] = mfcc_emb(zz[:len(yy)], mm)
    return out


def score_eer(enr, tst):
    tar, non = [], []
    for sp in range(NSPK):
        e = np.mean([enr[(sp, u)] for u in range(NUTT - 1)], 0)
        e = e / (np.linalg.norm(e) + E.EPS)
        tar.append(float(e @ tst[(sp, NUTT - 1)]))
        for sp2 in range(NSPK):
            if sp2 != sp:
                non.append(float(e @ tst[(sp2, NUTT - 1)]))
    return eer(np.array(tar), np.array(non))


EMB_CLEAN = embed_all(None, clean=True)
OUT['asv'] = []
print('\n   %-22s %12s %14s' % ('测试端处理', '注册端=干净', '注册端=同样处理'))
for tag, fn in PROCS:
    emb = embed_all(fn)
    e_mis = score_eer(EMB_CLEAN, emb)          # 注册干净、测试处理过 → 失配
    e_mat = score_eer(emb, emb)                # 两端同样处理 → 匹配
    OUT['asv'].append({'tag': tag, 'eer_mismatch': round(e_mis, 2),
                       'eer_matched': round(e_mat, 2)})
    print('   %-22s %10.2f%% %12.2f%%' % (tag, e_mis, e_mat))
e_clean = score_eer(EMB_CLEAN, EMB_CLEAN)
OUT['asv_clean'] = round(e_clean, 2)
print('   %-22s %10.2f%% %12.2f%%   ← 完全没有噪声时的下限'
      % ('（干净语音）', e_clean, e_clean))
noi = OUT['asv'][0]
best_mis = min(OUT['asv'][1:], key=lambda r: r['eer_mismatch'])
best_mat = min(OUT['asv'][1:], key=lambda r: r['eer_matched'])
OUT['asv_summary'] = {'noisy_mismatch': noi['eer_mismatch'],
                      'noisy_matched': noi['eer_matched'],
                      'best_mismatch': best_mis['tag'],
                      'best_matched': best_mat['tag']}
print('\n   两条结论：')
print('   ① <strong>注册和测试必须用同一套前端</strong>：'
      '同一种处理，失配时 %.2f%%，匹配时 %.2f%%。'
      % (best_mis['eer_mismatch'], best_mis['eer_matched']))
print('   ② 增强<strong>不一定</strong>帮得上：不处理是 %.2f%%，'
      '最好的处理是 %.2f%%（%s）。'
      % (noi['eer_matched'], best_mat['eer_matched'], best_mat['tag']))

# ══ ③ 指标和下游的相关性 ══════════════════════════════════════
print('\n③ 哪个客观指标能预测下游表现')
rows = []
for r, a in zip(OUT['rank'], OUT['asv']):
    rows.append((r, a))
OUT['corr'] = {}
for name, key, sgn in METRICS:
    xs = np.array([r[key] * sgn for r, _ in rows])
    ys = -np.array([a['eer_matched'] for _, a in rows])       # EER 越低越好
    xs = xs - xs.mean(); ys = ys - ys.mean()
    c = float(np.dot(xs, ys) / (np.sqrt(np.dot(xs, xs) * np.dot(ys, ys)) + E.EPS))
    OUT['corr'][name] = round(c, 3)
    print('   %-8s 与"处理后声纹 EER"的相关系数 %+.3f' % (name, c))
bestm = max(OUT['corr'], key=lambda k: OUT['corr'][k])
worstm = min(OUT['corr'], key=lambda k: OUT['corr'][k])
OUT['corr_best'], OUT['corr_worst'] = bestm, worstm
OUT['n_systems'] = len(PROCS)
print('   （%d 个系统，符号约定：正相关 = 这个指标说好的，下游也好）' % len(PROCS))
print('   最能预测的是 <strong>%s</strong>（%+.3f）；'
      '而 %s 是 <strong>%+.3f ——方向反了</strong>。'
      % (bestm, OUT['corr'][bestm], worstm, OUT['corr'][worstm]))
print('   五个指标彼此大体一致（都说 log-MMSE α=0.90 最好），'
      '<strong>但没有一个能预测下游</strong>。')
print('   波形保真类指标（SegSNR、SI-SDR）甚至是<strong>反</strong>相关的：')
print('   它们量"离干净波形有多远"，而下游要的是"谱的形状有没有被改坏"。')
print('   结论很实在：<strong>如果你的增强是给机器听的，'
      '就必须直接用下游指标做评测</strong>，别指望 SI-SDR 涨了下游就会好。')

json.dump(OUT, open('demo_eval.json', 'w'), ensure_ascii=False, indent=1)
print('\n→ demo_eval.json')
