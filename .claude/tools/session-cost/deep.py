import json, glob, os, collections
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from _paths import transcripts_dir
root = transcripts_dir()
for f in sorted(glob.glob(root + '/*/subagents/*.jsonl')):
    meta = json.load(open(f.replace('.jsonl', '.meta.json')))
    if meta.get('agentType') not in ('implementer', 'impl-lead'): continue
    uses = {}; big = []; seen = {}; tool_tokens = collections.Counter(); calls = collections.Counter()
    order = []
    for line in open(f):
        d = json.loads(line); m = d.get('message') or {}
        if d.get('type') == 'assistant':
            for c in m.get('content') or []:
                if isinstance(c, dict) and c.get('type') == 'tool_use':
                    inp = c['input']; key = inp.get('command') or inp.get('file_path') or inp.get('pattern') or inp.get('description') or ''
                    uses[c['id']] = (c['name'], str(key)[:80]); calls[c['name']] += 1
                    if c['name'] in ('Write', 'Edit'): tool_tokens[c['name'] + '(input)'] += len(json.dumps(inp)) // 4
            if m.get('usage') and m.get('id') not in seen:
                seen[m['id']] = 1; u = m['usage']; order.append((u.get('cache_creation_input_tokens', 0), u.get('cache_read_input_tokens', 0)))
        if d.get('type') == 'user':
            for c in m.get('content') or []:
                if isinstance(c, dict) and c.get('type') == 'tool_result':
                    cc = c.get('content'); s = cc if isinstance(cc, str) else json.dumps(cc)
                    n, k = uses.get(c['tool_use_id'], ('?', ''))
                    tool_tokens[n] += len(s) // 4; big.append((len(s) // 4, n, k))
    misses = [(i, cw, cr) for i, (cw, cr) in enumerate(order) if cw > 30000]
    print(f"== {f.split('/')[-3][:8]}/{f.split('/')[-1][6:14]} turns={len(order)} calls={dict(calls)}")
    print('   tokens added by tool:', dict(tool_tokens.most_common(6)))
    print('   cache rebuilds >30k (turn,write,read):', misses[:8], 'n=', len(misses))
    for b in sorted(big, reverse=True)[:5]: print('   big:', b)
