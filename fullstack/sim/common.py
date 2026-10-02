# -*- coding: utf-8 -*-
"""仿真验证的公共件：每条检验返回一行 {id, 章节, 公式, 预测, 仿真, 偏差, 判据, 通过}。
   原则：预测值一律来自书里的公式（闭式或递推），仿真值一律来自独立的数值模拟或暴力枚举；
   二者必须在写明的容差内一致，否则这一行记为未通过。"""
import numpy as np

ROWS = []


def check(rid, sec, formula, what, pred, sim, tol, kind='abs', unit=''):
    """kind: abs 绝对偏差 / rel 相对偏差 / le 要求 sim <= pred（不等式）/ ge 要求 sim >= pred"""
    pred, sim = float(pred), float(sim)
    if kind == 'abs':
        dev = abs(sim - pred); ok = dev <= tol; crit = '|偏差| ≤ %g%s' % (tol, unit)
    elif kind == 'rel':
        dev = abs(sim - pred) / max(abs(pred), 1e-12); ok = dev <= tol; crit = '相对偏差 ≤ %g%%' % (tol * 100)
    elif kind == 'le':
        dev = sim - pred; ok = sim <= pred + tol; crit = '仿真 ≤ 预测'
    else:
        dev = pred - sim; ok = sim >= pred - tol; crit = '仿真 ≥ 预测'
    ROWS.append(dict(id=rid, sec=sec, formula=formula, what=what, pred=round(pred, 4), sim=round(sim, 4),
                     dev=round(float(dev), 4), crit=crit, ok=bool(ok)))
    return ok


def rng(seed=0):
    return np.random.default_rng(seed)


def cn(g, *shape):
    """标准复高斯 CN(0,1)"""
    return (g.standard_normal(shape) + 1j * g.standard_normal(shape)) / np.sqrt(2)
