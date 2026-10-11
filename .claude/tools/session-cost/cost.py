import json, glob, os, collections, re
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from _paths import transcripts_dir
root = transcripts_dir()
PR = {'opus': (4, 20, .20), 'sonnet': (2, 10, .10), 'haiku': (.10, .50, .01)}  # in, out, cache read $/MTok
cost = collections.Counter(); parts = collections.defaultdict(collections.Counter); runs = collections.Counter()
checks = collections.Counter()
for f in glob.glob(root + '/**/*.jsonl', recursive=True):
    meta = f.replace('.jsonl', '.meta.json')
    role = json.load(open(meta)).get('agentType') if os.path.exists(meta) else 'MAIN(opus)'
    seen = set(); runs[role] += 1
    for line in open(f):
        d = json.loads(line); m = d.get('message') or {}
        if d.get('type') != 'assistant': continue
        for c in m.get('content') or []:
            if isinstance(c, dict) and c.get('type') == 'tool_use' and c['name'] == 'Bash':
                cmd = c['input'].get('command', '')
                if re.search(r'check\.sh|go test|eval|fuzz', cmd): checks[role] += 1
        u = m.get('usage')
        if not u or m.get('id') in seen: continue
        seen.add(m['id']); fam = m['model'].split('-')[1]; pi, po, pr = PR[fam]
        cc = u.get('cache_creation') or {}
        w5 = cc.get('ephemeral_5m_input_tokens', 0); w1 = cc.get('ephemeral_1h_input_tokens', 0)
        if not cc: w5 = u.get('cache_creation_input_tokens', 0)
        p = {'cache_read': u.get('cache_read_input_tokens', 0) * pr, 'cache_write': w5 * pi * 1.25 + w1 * pi * 2,
             'output': u.get('output_tokens', 0) * po, 'input': u.get('input_tokens', 0) * pi}
        for k, v in p.items(): parts[role][k] += v / 1e6
tot = sum(sum(c.values()) for c in parts.values())
for r, c in sorted(parts.items(), key=lambda x: -sum(x[1].values())):
    s = sum(c.values()); print(f"{r:11} runs={runs[r]:3} ${s:6.2f} ({100*s/tot:4.1f}%)  " + '  '.join(f"{k}=${v:.2f}" for k, v in c.items()) + f"  test/check cmds={checks[r]}")
print(f"TOTAL ${tot:.2f}")
