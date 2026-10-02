#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑全部仿真检验，写 sim.json（供手册第 22 节引用）。"""
import json, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import sim_array, sim_aec, sim_enh, sim_asr, sim_tts, sim_misc

t0 = time.time()
for m in (sim_array, sim_aec, sim_enh, sim_asr, sim_tts, sim_misc):
    t = time.time(); m.run(); print('%-10s %5.1fs  累计 %d 项' % (m.__name__, time.time() - t, len(common.ROWS)))
rows = common.ROWS
bad = [r for r in rows if not r['ok']]
out = dict(rows=rows, n=len(rows), n_ok=len(rows) - len(bad), runtime_s=round(time.time() - t0, 1))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sim.json'), 'w'), ensure_ascii=False, indent=1)
print('共 %d 项，通过 %d，未通过 %d' % (len(rows), len(rows) - len(bad), len(bad)))
for r in bad:
    print('  ✗', r['id'], r['what'], r['pred'], r['sim'], r['dev'])
sys.exit(1 if bad else 0)
