"""Simulate the subagent prompt-cache cost with a 1h TTL instead of 5m.

A turn that rewrote a large context with almost no cache read is counted as a
rebuild after an expired cache; with a 1h TTL it would have been a read plus a
small write. Every other cache write costs 2x input (1h) instead of 1.25x (5m).
"""
import json, glob, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import transcripts_dir

root = transcripts_dir()
IN = {'sonnet': 2.0, 'haiku': 0.10, 'opus': 4.0}    # input $/MTok
RD = {'sonnet': 0.10, 'haiku': 0.01, 'opus': 0.20}  # cache read $/MTok
res = collections.defaultdict(lambda: [0.0, 0.0, 0])
for f in glob.glob(root + '/*/subagents/*.jsonl'):
    meta = f.replace('.jsonl', '.meta.json')
    role = json.load(open(meta)).get('agentType') if os.path.exists(meta) else '?'
    seen = set(); first = True
    for line in open(f):
        d = json.loads(line); m = d.get('message') or {}; u = m.get('usage')
        if d.get('type') != 'assistant' or not u or m.get('id') in seen:
            continue
        seen.add(m['id']); fam = m['model'].split('-')[1]
        pi, pr = IN[fam] / 1e6, RD[fam] / 1e6
        cw, cr = u.get('cache_creation_input_tokens', 0), u.get('cache_read_input_tokens', 0)
        now = cw * 1.25 * pi + cr * pr
        if not first and cw > 30000 and cr < 1000:
            new = 5000; h1 = (cw - new) * pr + new * 2 * pi; res[role][2] += 1
        else:
            h1 = cw * 2 * pi + cr * pr
        res[role][0] += now; res[role][1] += h1; first = False
for r, (a, b, n) in sorted(res.items()):
    print(f"{r:10} cache cost 5m=${a:.2f}  1h=${b:.2f}  diff=${b - a:+.2f} ({(b - a) / a * 100:+.1f}%)  rebuilds avoided={n}")
