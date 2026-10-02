#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""算法处理框图与公式图示（手绘内联 SVG，主题感知）。"""
import json, math, html

OUT = {}

def defs(uid):
    """每张图自带箭头 marker，id 唯一，避免跨 SVG 冲突。"""
    return (f'<defs>'
            f'<marker id="{uid}a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--text-2)"/></marker>'
            f'<marker id="{uid}h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--hot)"/></marker>'
            f'<marker id="{uid}s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" '
            f'markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="var(--s1)"/></marker>'
            f'</defs>')

def box(x, y, w, h, title, sub=None, cls='bx', rx=4):
    t = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>'
    if sub:
        t += (f'<text x="{x+w/2}" y="{y+h/2-3}" class="blab" text-anchor="middle">{title}</text>'
              f'<text x="{x+w/2}" y="{y+h/2+11}" class="bsub" text-anchor="middle">{sub}</text>')
    else:
        t += f'<text x="{x+w/2}" y="{y+h/2+4}" class="blab" text-anchor="middle">{title}</text>'
    return t

def arrow(x1, y1, x2, y2, uid, cls='ar', mk='a', label=None, lx=None, ly=None, anchor='middle'):
    t = (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}" '
         f'marker-end="url(#{uid}{mk})"/>')
    if label:
        t += (f'<text x="{lx if lx is not None else (x1+x2)/2}" '
              f'y="{ly if ly is not None else (y1+y2)/2-6}" class="arlab halo" '
              f'text-anchor="{anchor}">{label}</text>')
    return t

def path(d, uid, cls='ar', mk='a'):
    return f'<path d="{d}" class="{cls}" marker-end="url(#{uid}{mk})"/>'

def svg(w, h, body, label, uid):
    return (f'<svg viewBox="0 0 {w} {h}" class="chart diag" role="img" '
            f'aria-label="{html.escape(label)}">\n{defs(uid)}\n{body}\n</svg>')

# ════════════════════════════════════════════════════════════════
# A. 远场前端完整信号链（§12）—— 正确顺序 + 两个不能调换的地方
# ════════════════════════════════════════════════════════════════
def fig_chain():
    u = 'ch'; o = []
    BW, BH, Y = 78, 40, 50
    names = [('同步校准', '时钟 / 幅相'), ('AEC', '每通道各一路'),
             ('去混响', 'WPE'), ('波束成形', '空间滤波'),
             ('后置滤波', '单通道'), ('AGC / 限幅', '')]
    xs = [42 + i * 99 for i in range(6)]
    o.append('<text x="10" y="18" class="ct">远场前端的规范顺序'
             '<tspan class="cu"> · 每一步都为下一步创造它需要的前提</tspan></text>')
    o.append(f'<text x="8" y="{Y+BH/2-6}" class="bsub">M 路</text>')
    o.append(arrow(8, Y + BH / 2 + 6, xs[0] - 4, Y + BH / 2 + 6, u))
    for i, (n, s) in enumerate(names):
        cls = 'bx-a' if n == '波束成形' else 'bx'
        o.append(box(xs[i], Y, BW, BH, n, s or None, cls))
        if i < 5:
            o.append(arrow(xs[i] + BW, Y + BH / 2, xs[i + 1] - 4, Y + BH / 2, u))
    o.append(arrow(xs[5] + BW, Y + BH / 2, xs[5] + BW + 22, Y + BH / 2, u))
    o.append(f'<text x="{xs[5]+BW+26}" y="{Y+BH/2-6}" class="bsub">1 路</text>')
    o.append(f'<text x="{xs[5]+BW+26}" y="{Y+BH/2+8}" class="bsub">→ ASR</text>')
    # 通道数标注
    o.append(f'<line x1="{xs[0]-6}" y1="{Y+BH+12}" x2="{xs[3]-6}" y2="{Y+BH+12}" class="ar-d" '
             f'marker-end="none"/>')
    o.append(f'<text x="{(xs[0]+xs[3])/2-6}" y="{Y+BH+26}" class="arlab" text-anchor="middle">'
             f'这一段必须保持多通道</text>')
    o.append(f'<line x1="{xs[4]-6}" y1="{Y+BH+12}" x2="{xs[5]+BW}" y2="{Y+BH+12}" class="ar-d" '
             f'marker-end="none"/>')
    o.append(f'<text x="{(xs[4]+xs[5]+BW)/2}" y="{Y+BH+26}" class="arlab" text-anchor="middle">'
             f'已降到单通道</text>')
    # 两个反例
    Y2 = 150
    o.append(f'<text x="10" y="{Y2-8}" class="ct">两处调换会直接失效'
             f'<tspan class="cu"> · 不是"效果差一点"，是原理上不成立</tspan></text>')
    bad = [('波束 → AEC', '波束权重随时变，回声路径跟着变，AEC 永远追不上'),
           ('波束 → 去混响', 'WPE 要靠多通道预测晚期混响，波束后只剩一路')]
    for i, (t, why) in enumerate(bad):
        yy = Y2 + i * 44
        o.append(f'<rect x="10" y="{yy}" width="128" height="30" rx="4" class="bx-h"/>')
        o.append(f'<text x="74" y="{yy+19}" class="blab" text-anchor="middle" '
                 f'fill="var(--hot)">✗ {t}</text>')
        o.append(f'<text x="150" y="{yy+19}" class="bsub">{why}</text>')
    return svg(700, 246, '\n'.join(o),
               '远场前端的信号链顺序：同步校准、AEC、去混响、波束成形、后置滤波、增益控制；'
               '并列出把波束放到 AEC 或去混响之前会失效的两种错误顺序', u)

OUT['chain'] = fig_chain()

# ════════════════════════════════════════════════════════════════
# B. GSC 结构（§17）
# ════════════════════════════════════════════════════════════════
def fig_gsc():
    u = 'gs'; o = []
    o.append('<text x="10" y="18" class="ct">GSC：把带约束的问题拆成"固定波束 + 无约束自适应"'
             '<tspan class="cu"> · 与 MVDR 等价</tspan></text>')
    o.append(f'<text x="14" y="108" class="bsub">x(ω)</text>')
    o.append(f'<line x1="46" y1="100" x2="86" y2="100" class="ar" marker-end="none"/>')
    o.append(f'<circle cx="86" cy="100" r="3" fill="var(--text-2)"/>')
    # 上支路
    o.append(f'<path d="M86,100 L86,58 L126,58" class="ar" marker-end="url(#{u}a)"/>')
    o.append(box(130, 38, 108, 40, '固定波束 w_f', '指向目标，不自适应', 'bx-a'))
    o.append(arrow(238, 58, 320, 58, u, label='d(ω)：目标 + 噪声', lx=244, ly=50, anchor='start'))
    o.append(box(324, 38, 66, 40, '延迟对齐', None))
    o.append(arrow(390, 58, 452, 58, u))
    # 下支路
    o.append(f'<path d="M86,100 L86,150 L126,150" class="ar" marker-end="url(#{u}a)"/>')
    o.append(box(130, 130, 108, 40, '阻塞矩阵 B', 'B·a = 0，目标被挡掉', 'bx-a'))
    o.append(arrow(238, 150, 320, 150, u, label='u(ω)：只剩噪声', lx=244, ly=142, anchor='start'))
    o.append(box(324, 130, 66, 40, '自适应 a', None))
    o.append(f'<path d="M390,150 L462,150 L462,80" class="ar" marker-end="url(#{u}a)"/>')
    # 求和
    o.append('<circle cx="462" cy="58" r="15" class="bx-a"/>')
    o.append('<text x="462" y="63" class="blab" text-anchor="middle">Σ</text>')
    o.append('<text x="447" y="46" class="bsub">+</text>')
    o.append('<text x="447" y="82" class="bsub">−</text>')
    o.append(arrow(477, 58, 528, 58, u))
    o.append('<text x="532" y="62" class="blab">y(ω)</text>')
    o.append('<text x="532" y="78" class="bsub">= d − aᴴu</text>')
    # 失效路径
    o.append(f'<path d="M184,170 L184,194 L232,194" class="ar-h" marker-end="url(#{u}h)" '
             f'stroke-dasharray="4 3"/>')
    o.append('<text x="240" y="198" class="bsub" fill="var(--hot)">'
             '导向有误差 → B 挡不干净 → 目标漏进参考支路 → 被当噪声消掉</text>')
    o.append('<text x="14" y="224" class="arlab">"目标抵消"在 GSC 里的位置因此非常具体：'
             '不在自适应算法，在阻塞矩阵。</text>')
    return svg(700, 238, '\n'.join(o),
               'GSC 的两条支路：上支路固定波束输出目标加噪声，下支路阻塞矩阵挡掉目标只留噪声参考，'
               '自适应滤波后相减；导向误差让目标漏过阻塞矩阵，造成目标抵消', u)

OUT['gsc'] = fig_gsc()

# ════════════════════════════════════════════════════════════════
# C. mask-based 神经波束（§20）
# ════════════════════════════════════════════════════════════════
def fig_maskbf():
    u = 'mb'; o = []
    o.append('<text x="10" y="18" class="ct">Mask-based 神经波束：网络只出掩码，空间滤波仍是闭式解'
             '<tspan class="cu"> · 当前的工业最优组合</tspan></text>')
    o.append(f'<text x="12" y="72" class="bsub">M 路时域</text>')
    o.append(arrow(72, 66, 104, 66, u))
    o.append(box(108, 46, 70, 40, 'STFT', None))
    o.append(arrow(178, 66, 212, 66, u))
    o.append(box(216, 40, 96, 52, '神经网络', '通常只吃 1 路幅度谱', 'bx-a'))
    o.append(arrow(312, 66, 352, 66, u, label='掩码', ly=58))
    o.append(box(356, 34, 100, 30, 'M_s 目标掩码', None))
    o.append(box(356, 70, 100, 30, 'M_n 噪声掩码', None))
    o.append(f'<path d="M456,49 L478,49 L478,66 L492,66" class="ar" marker-end="url(#{u}a)"/>')
    o.append(f'<path d="M456,85 L478,85 L478,66" class="ar" marker-end="none"/>')
    o.append(box(496, 46, 92, 40, '加权估协方差', 'R_s / R_n', 'bx-a'))
    o.append(f'<path d="M542,86 L542,120 L306,120" class="ar" marker-end="url(#{u}a)"/>')
    o.append(box(206, 126, 100, 40, 'MVDR / GEV', '闭式解，无训练', 'bx-a'))
    o.append(f'<path d="M178,66 L178,146 L202,146" class="ar" marker-end="url(#{u}a)"/>')
    o.append(f'<text x="140" y="112" class="arlab">原始 M 路谱</text>')
    o.append(arrow(306, 146, 356, 146, u))
    o.append(box(360, 126, 62, 40, 'BAN', 'GEV 才需要'))
    o.append(arrow(422, 146, 466, 146, u))
    o.append(box(470, 126, 70, 40, 'ISTFT', None))
    o.append(arrow(540, 146, 580, 146, u))
    o.append('<text x="584" y="150" class="bsub">增强信号</text>')
    o.append('<text x="10" y="196" class="arlab">关键在于：网络<tspan class="hot-t">不直接输出音频</tspan>，'
             '只输出"哪些时频点是噪声"。所以它不引入非线性失真，</text>')
    o.append('<text x="10" y="212" class="arlab">换个房间也不会崩——'
             '崩的只是掩码精度，而波束依旧是那个有解析保证的解。</text>')
    return svg(700, 226, '\n'.join(o),
               'Mask-based 神经波束流程：STFT 后网络输出目标与噪声掩码，'
               '用掩码加权估计协方差矩阵，再用 MVDR 或 GEV 的闭式解做空间滤波', u)

OUT['maskbf'] = fig_maskbf()

# ════════════════════════════════════════════════════════════════
# D. 球谐处理链（§27）
# ════════════════════════════════════════════════════════════════
def fig_shchain():
    u = 'sc'; o = []
    o.append('<text x="10" y="18" class="ct">球阵处理链：先换基，再均衡，最后才谈波束'
             '<tspan class="cu"> · 与线阵最大的结构差别</tspan></text>')
    o.append('<text x="12" y="76" class="bsub">Q 路球面麦</text>')
    o.append(arrow(78, 70, 110, 70, u))
    o.append(box(114, 50, 96, 40, '球谐变换', 'p_nm = Yᴴ p', 'bx-a'))
    o.append(arrow(210, 70, 252, 70, u))
    o.append('<text x="231" y="106" class="arlab" text-anchor="middle">(N+1)² 个模态</text>')
    o.append(box(256, 50, 110, 40, '模态均衡 1/b_n', '把球的散射除掉', 'bx-h'))
    o.append(arrow(366, 70, 408, 70, u))
    o.append(box(412, 50, 100, 40, '选 c_n', '决定方向图形状', 'bx-a'))
    o.append(arrow(512, 70, 552, 70, u))
    o.append(box(556, 50, 96, 40, '任意转向', '只换 Y(û)，不重算'))
    o.append(arrow(604, 90, 604, 116, u))
    o.append('<text x="614" y="112" class="bsub">y(û)</text>')
    # 三个注解
    notes = [(114, '换基：把"哪个麦"换成"哪个空间模式"，此后与阵元位置无关'),
             (256, '全部代价在这：第 n 阶 |b_n| ∝ (kr)ⁿ，除它就是放大 6n dB/oct'),
             (412, 'c_n 全取 1 = 最大指向性；加权可换成旁瓣更低的形状')]
    for i, (x, t) in enumerate(notes):
        yy = 148 + i * 21
        col = 'var(--hot)' if i == 1 else 'var(--text-3)'
        o.append(f'<text x="14" y="{yy}" class="arlab" fill="{col}">'
                 f'{"①②③"[i]}　{t}</text>')
    o.append('<text x="14" y="214" class="arlab">对比线阵：线阵的权重把"频率"和"指向"绑在一起，'
             '换个方向要重算整组权重；球谐把这两件事彻底拆开了。</text>')
    return svg(700, 226, '\n'.join(o),
               '球阵处理链：球谐变换换基、模态均衡除以 b_n、选择模态权重 c_n、再任意转向；'
               '模态均衡是低频噪声放大的来源', u)

OUT['shchain'] = fig_shchain()

# ════════════════════════════════════════════════════════════════
# E. 双耳处理链（§28）
# ════════════════════════════════════════════════════════════════
def fig_binchain():
    u = 'bc'; o = []
    o.append('<text x="10" y="18" class="ct">双耳系统：两台设备，一个联合解，两路输出'
             '<tspan class="cu"> · 输出是给人耳听的，不是给识别器吃的</tspan></text>')
    o.append(box(16, 58, 92, 44, '左耳设备', '前 / 后 2 麦', 'bx'))
    o.append(box(16, 168, 92, 44, '右耳设备', '前 / 后 2 麦', 'bx'))
    o.append(f'<path d="M108,80 L152,80 L152,135 L186,135" class="ar" marker-end="url(#{u}a)"/>')
    o.append(f'<path d="M108,190 L152,190 L152,135" class="ar" marker-end="none"/>')
    o.append('<text x="116" y="127" class="bsub" fill="var(--hot)">无线链路</text>')
    o.append('<text x="116" y="141" class="bsub" fill="var(--hot)">带宽 / 延迟</text>')
    o.append('<text x="116" y="155" class="bsub" fill="var(--hot)">预算都在这</text>')
    o.append(box(190, 114, 104, 42, '联合协方差', '4 通道 R_n', 'bx-a'))
    o.append(arrow(294, 135, 328, 135, u))
    o.append(box(332, 114, 108, 42, 'MVDR 解', 'w = R⁻¹a / aᴴR⁻¹a', 'bx-a'))
    o.append(f'<path d="M440,124 L464,124 L464,80 L494,80" class="ar" marker-end="url(#{u}a)"/>')
    o.append(f'<path d="M440,146 L464,146 L464,190 L494,190" class="ar" marker-end="url(#{u}a)"/>')
    o.append(box(498, 60, 78, 40, '× a*_L', '左耳 RTF', 'bx-a'))
    o.append(box(498, 170, 78, 40, '× a*_R', '右耳 RTF', 'bx-a'))
    # 回混：从原始信号短接到输出前的加法点
    for yy, lab in [(80, 'L'), (190, 'R')]:
        o.append(f'<circle cx="606" cy="{yy}" r="12" class="bx-a"/>')
        o.append(f'<text x="606" y="{yy+5}" class="blab" text-anchor="middle">Σ</text>')
        o.append(arrow(576, yy, 592, yy, u))
        o.append(arrow(618, yy, 648, yy, u))
    o.append('<text x="652" y="84" class="blab">左耳</text>')
    o.append('<text x="652" y="194" class="blab">右耳</text>')
    o.append(f'<path d="M62,58 L62,38 L606,38 L606,66" class="ar-d" marker-end="url(#{u}a)"/>')
    o.append(f'<path d="M62,212 L62,232 L606,232 L606,204" class="ar-d" marker-end="url(#{u}a)"/>')
    o.append('<text x="330" y="246" class="arlab" text-anchor="middle">'
             '虚线：η · 该耳的原始带噪信号回混（MWF-N），上下各一路</text>')
    o.append('<text x="14" y="272" class="arlab">"× RTF"这一步就是双耳的全部：'
             '它让两耳输出保持目标本来的 ITD 与 ILD。η 则是买回干扰方位感的代价开关。</text>')
    return svg(700, 284, '\n'.join(o),
               '双耳处理链：两台设备的四个麦克风通过无线链路共享，解出一个联合 MVDR 权重，'
               '再分别乘以左右耳的相对传递函数，并按 η 回混该耳的原始带噪信号', u)

OUT['binchain'] = fig_binchain()

# ════════════════════════════════════════════════════════════════
# F. 导向矢量的程差几何（§01）
# ════════════════════════════════════════════════════════════════
def fig_steer():
    u = 'st'; o = []
    o.append('<text x="10" y="18" class="ct">导向矢量是从一条程差里长出来的'
             '<tspan class="cu"> · 相邻阵元的声程差 d·cosθ</tspan></text>')
    y0 = 168
    xs = [150, 240, 330, 420]
    # 阵元
    for i, x in enumerate(xs):
        o.append(f'<circle cx="{x}" cy="{y0}" r="7" class="bx-a"/>')
        o.append(f'<text x="{x}" y="{y0+26}" class="bsub" text-anchor="middle">{i+1}</text>')
    o.append(f'<line x1="130" y1="{y0}" x2="440" y2="{y0}" class="ar-d" marker-end="none"/>')
    # 波前（入射角 40° 自左上）
    ang = math.radians(40)
    dx, dy = math.cos(ang), math.sin(ang)          # 传播方向
    for k, off in enumerate([-60, 0, 60, 120]):
        cx0, cy0 = 214 + off * dx, 76 + off * dy
        o.append(f'<line x1="{cx0-118*dy:.1f}" y1="{cy0+118*dx:.1f}" '
                 f'x2="{cx0+62*dy:.1f}" y2="{cy0-62*dx:.1f}" '
                 f'stroke="var(--s1)" stroke-width="1.4" opacity="0.5"/>')
    o.append(f'<line x1="42" y1="52" x2="{42+64*dx:.0f}" y2="{52+64*dy:.0f}" class="ar" '
             f'marker-end="url(#{u}s)" stroke="var(--s1)"/>')
    o.append(f'<text x="14" y="46" class="blab" fill="var(--s1)">来波方向</text>')
    # 程差标注：阵元 2 到 3 之间
    x2, x3 = xs[1], xs[2]
    # 垂足：从阵元3 向 过阵元2 的波前作垂线
    px = x3 - (x3 - x2) * dx * dx
    py = y0 - (x3 - x2) * dx * dy
    o.append(f'<line x1="{x3}" y1="{y0}" x2="{px:.1f}" y2="{py:.1f}" '
             f'stroke="var(--hot)" stroke-width="2.2"/>')
    o.append(f'<text x="{(x3+px)/2+8:.0f}" y="{(y0+py)/2+4:.0f}" class="blab" '
             f'fill="var(--hot)">Δ = d·cosθ</text>')
    # θ 角
    o.append(f'<path d="M{x2+34},{y0} A 34 34 0 0 0 {x2+34*math.cos(ang):.1f},'
             f'{y0-34*math.sin(ang):.1f}" fill="none" stroke="var(--text-3)" stroke-width="1.2"/>')
    o.append(f'<text x="{x2+42}" y="{y0-14}" class="bsub">θ</text>')
    o.append(f'<line x1="{x2}" y1="{y0}" x2="{x2+90*math.cos(ang):.0f}" '
             f'y2="{y0-90*math.sin(ang):.0f}" class="ar-d" marker-end="none"/>')
    # 间距 d
    o.append(f'<line x1="{xs[0]}" y1="{y0+40}" x2="{xs[1]}" y2="{y0+40}" class="ar-d" '
             f'marker-end="none"/>')
    o.append(f'<text x="{(xs[0]+xs[1])/2}" y="{y0+54}" class="bsub" text-anchor="middle">d</text>')
    # 右侧结论
    o.append('<text x="470" y="96" class="blab">每多走一段 Δ，</text>')
    o.append('<text x="470" y="114" class="blab">就多一个相位 kΔ</text>')
    o.append('<text x="470" y="140" class="bsub">k = 2πf/c</text>')
    o.append('<text x="470" y="162" class="bsub">第 m 个阵元：</text>')
    o.append('<text x="470" y="180" class="blab" fill="var(--s1)">e^(−jk·(m−1)d·cosθ)</text>')
    o.append('<text x="470" y="204" class="bsub">把 M 个相位排成一列，</text>')
    o.append('<text x="470" y="220" class="bsub">就是导向矢量 a。</text>')
    return svg(700, 244, '\n'.join(o),
               '平面波斜入射到四元线阵，相邻阵元之间的声程差等于间距乘以入射角余弦，'
               '对应的相位差是波数乘以这个程差，把各阵元的相位排成一列就得到导向矢量', u)

OUT['steergeo'] = fig_steer()

# ════════════════════════════════════════════════════════════════
# J. 头部几何：ITD 与 ILD 的来源（§28）
# ════════════════════════════════════════════════════════════════
def fig_head():
    u = 'hd'; o = []
    o.append('<text x="10" y="18" class="ct">两条线索，两套物理'
             '<tspan class="cu"> · 一个来自绕行的路程，一个来自被挡住的能量</tspan></text>')
    cx, cy, R = 170, 130, 58
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" class="bx"/>')
    o.append(f'<text x="{cx}" y="{cy+4}" class="bsub" text-anchor="middle">头 a ≈ 8.75 cm</text>')
    # 双耳
    for sgn, lab in [(-1, 'L'), (1, 'R')]:
        ex, ey = cx + sgn * R * math.cos(math.radians(10)), cy - R * math.sin(math.radians(10))
        o.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="5" class="bx-a"/>')
        o.append(f'<text x="{ex+sgn*14:.0f}" y="{ey+4:.0f}" class="blab" '
                 f'text-anchor="{"end" if sgn<0 else "start"}">{lab}</text>')
    # 声源在右前方
    sx, sy = cx + 168, cy - 96
    o.append(f'<circle cx="{sx}" cy="{sy}" r="6" fill="var(--s1)"/>')
    o.append(f'<text x="{sx+12}" y="{sy+4}" class="blab" fill="var(--s1)">声源</text>')
    # 直达到右耳
    exR, eyR = cx + R * math.cos(math.radians(10)), cy - R * math.sin(math.radians(10))
    o.append(f'<line x1="{sx}" y1="{sy}" x2="{exR:.1f}" y2="{eyR:.1f}" stroke="var(--s1)" '
             f'stroke-width="2"/>')
    # 绕行到左耳
    o.append(f'<path d="M{sx},{sy} L{cx+18},{cy-R+6} A {R} {R} 0 0 0 '
             f'{cx-R*math.cos(math.radians(10)):.1f},{cy-R*math.sin(math.radians(10)):.1f}" '
             f'fill="none" stroke="var(--s2)" stroke-width="2" stroke-dasharray="5 3"/>')
    o.append(f'<text x="{cx-4}" y="{cy-R-10}" class="blab" fill="var(--s2)" '
             f'text-anchor="middle">绕行</text>')
    # 声影
    o.append(f'<path d="M{cx-R},{cy} A {R} {R} 0 0 0 {cx},{cy+R} L{cx-96},{cy+66} Z" '
             f'fill="var(--hot)" opacity="0.10"/>')
    o.append(f'<text x="{cx-72}" y="{cy+58}" class="bsub" fill="var(--hot)">声影区</text>')
    # 右侧两栏
    X = 372
    o.append(f'<line x1="{X-18}" y1="40" x2="{X-18}" y2="232" class="ar-d" marker-end="none"/>')
    o.append(f'<text x="{X}" y="56" class="blab" fill="var(--s2)">ITD　时间差</text>')
    o.append(f'<text x="{X}" y="76" class="bsub">绕行多出来的路程 ÷ 声速</text>')
    o.append(f'<text x="{X}" y="94" class="bsub">低频 3(a/c)sinθ → 765 µs</text>')
    o.append(f'<text x="{X}" y="112" class="bsub">高频 2(a/c)sinθ → 510 µs</text>')
    o.append(f'<text x="{X}" y="130" class="bsub" fill="var(--hot)">'
             f'超过 762 Hz 相位开始有歧义</text>')
    o.append(f'<text x="{X}" y="162" class="blab" fill="var(--s1)">ILD　声级差</text>')
    o.append(f'<text x="{X}" y="182" class="bsub">头挡住了对侧耳的能量</text>')
    o.append(f'<text x="{X}" y="200" class="bsub">250 Hz 只有 0.3 dB（挡不住）</text>')
    o.append(f'<text x="{X}" y="218" class="bsub">8 kHz 可达 20 dB 以上</text>')
    o.append(f'<text x="{X}" y="236" class="bsub" fill="var(--hot)">'
             f'分界在头径 = λ，约 1960 Hz</text>')
    return svg(700, 250, '\n'.join(o),
               '头部几何决定两条双耳线索：绕到对侧耳的额外路程产生时间差，'
               '头部对高频的遮挡产生声级差；两者的有效频段互补', u)

OUT['head'] = fig_head()

# ════════════════════════════════════════════════════════════════
# K. 双耳 MVDR 的线索塌缩（§28）—— 处理前 vs 处理后
# ════════════════════════════════════════════════════════════════
def fig_collapse():
    u = 'cl'; o = []
    o.append('<text x="10" y="18" class="ct">双耳 MVDR 只做对了一半'
             '<tspan class="cu"> · 目标的方位保住了，其他一切都塌到目标方向上</tspan></text>')
    CY, R = 214, 108
    for k, (ox, title) in enumerate([(14, '处理前　听到的空间'), (366, '双耳 MVDR 之后')]):
        cx = ox + 160
        o.append(f'<text x="{cx}" y="44" class="blab" text-anchor="middle">{title}</text>')
        for rr in (R, R * 0.62):
            o.append(f'<path d="M{cx-rr},{CY} A {rr} {rr} 0 0 1 {cx+rr},{CY}" fill="none" '
                     f'class="grid"/>')
        o.append(f'<line x1="{cx-R-14}" y1="{CY}" x2="{cx+R+14}" y2="{CY}" class="grid"/>')
        o.append(f'<circle cx="{cx}" cy="{CY}" r="11" class="bx"/>')
        o.append(f'<text x="{cx}" y="{CY+26}" class="bsub" text-anchor="middle">听者</text>')
        o.append(f'<circle cx="{cx}" cy="{CY-96}" r="8" fill="var(--s1)"/>')
        o.append(f'<text x="{cx}" y="{CY-(108 if k==0 else 122)}" class="blab" '
                 f'text-anchor="middle" fill="var(--s1)">目标 0°</text>')
        if k == 0:
            ax = math.radians(60)
            ix, iy = cx + 96 * math.sin(ax), CY - 96 * math.cos(ax)
            o.append(f'<circle cx="{ix:.1f}" cy="{iy:.1f}" r="8" fill="var(--s2)"/>')
            o.append(f'<text x="{ix+13:.0f}" y="{iy+4:.0f}" class="blab" fill="var(--s2)">'
                     f'干扰 60°</text>')
            for a_ in (-72, -46, -20, 22, 38):           # 扩散噪声，只在上半圆
                t = math.radians(a_)
                o.append(f'<circle cx="{cx+R*math.sin(t):.1f}" cy="{CY-R*math.cos(t):.1f}" '
                         f'r="3.2" fill="var(--text-3)" opacity="0.55"/>')
            o.append(f'<text x="{cx-R-4}" y="{CY-52}" class="bsub" fill="var(--text-3)">'
                     f'扩散噪声</text>')
            o.append(f'<text x="{cx}" y="{CY+48}" class="bsub" text-anchor="middle">'
                     f'三样东西在三个方位</text>')
        else:
            o.append(f'<circle cx="{cx-14}" cy="{CY-95}" r="7" fill="var(--s2)" opacity="0.9"/>')
            o.append(f'<circle cx="{cx+13}" cy="{CY-92}" r="3.4" fill="var(--text-3)"/>')
            o.append(f'<circle cx="{cx+7}" cy="{CY-106}" r="3.2" fill="var(--text-3)"/>')
            o.append(f'<circle cx="{cx-6}" cy="{CY-82}" r="3" fill="var(--text-3)"/>')
            o.append(f'<path d="M{cx+86},{CY-52} C {cx+54},{CY-84} {cx+34},{CY-92} '
                     f'{cx+16},{CY-95}" class="ar-h" marker-end="url(#{u}h)"/>')
            o.append(f'<text x="{cx+92}" y="{CY-46}" class="bsub" fill="var(--hot)">被搬过来</text>')
            o.append(f'<text x="{cx}" y="{CY+48}" class="bsub" text-anchor="middle" '
                     f'fill="var(--hot)">全部重合在目标方向</text>')
    o.append('<text x="14" y="296" class="arlab">残余噪声在两耳上的比值变成了 a_L/a_R——'
             '那正是目标的双耳传函。听感上背景从"环绕着你"变成"贴在说话人脸上"，</text>')
    o.append('<text x="14" y="312" class="arlab">'
             '而听者恰恰要靠背景的方位感判断"旁边还有没有人"。这就是双耳前端与单通道前端的根本分歧。</text>')
    return svg(700, 324, '\n'.join(o),
               '处理前听者能分辨正前方的目标、右侧六十度的干扰和四周的扩散噪声；'
               '双耳 MVDR 之后目标方位保持不变，但干扰和噪声全部塌缩到目标所在的正前方', u)

OUT['collapse'] = fig_collapse()

json.dump(OUT, open('figs3.json', 'w'))
print('figs3.json:', ', '.join('%s %.1fKB' % (k, len(v) / 1024) for k, v in OUT.items()))
