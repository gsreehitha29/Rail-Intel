"""E-600 — graph v1.3 build, staged.  usage: run.py <stage> [part nparts]"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from railgraph import v13
st = sys.argv[1]; t0 = time.time()
if st == 's1': r = v13.stage1()
elif st == 's2a': r = v13.stage2a()
elif st == 's2b': r = v13.stage2b(int(sys.argv[2]), int(sys.argv[3]))
else: r = getattr(v13, st)(*sys.argv[2:])
r = dict(stage=st, **{k: v for k, v in r.items() if k != 'seconds'}, seconds=round(time.time()-t0, 1))
p = v13.STG / 'stage_log.jsonl'; p.parent.mkdir(parents=True, exist_ok=True)
open(p, 'a').write(json.dumps(r, default=str) + '\n'); print(json.dumps(r, default=str)[:1500])
