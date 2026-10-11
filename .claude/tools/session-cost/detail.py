import json, glob, os, collections
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from _paths import transcripts_dir
root = transcripts_dir()
out = []
for f in sorted(glob.glob(root + '/**/*.jsonl', recursive=True)):
    meta = f.replace('.jsonl', '.meta.json')
    at = json.load(open(meta)).get('agentType') if os.path.exists(meta) else 'MAIN'
    seen = {}; ts0 = ts1 = None; tools = collections.Counter(); desc = None; spawns = collections.Counter()
    for line in open(f):
        try: d = json.loads(line)
        except: continue
        if d.get('timestamp'): ts0 = ts0 or d['timestamp']; ts1 = d['timestamp']
        m = d.get('message') or {}
        if d.get('type') == 'assistant':
            for c in m.get('content') or []:
                if isinstance(c, dict) and c.get('type') == 'tool_use':
                    tools[c['name']] += 1
                    if c['name'] in ('Agent', 'Task'): spawns[c['input'].get('subagent_type', '?')] += 1
                    if c['name'] == 'Skill': spawns['skill:' + c['input'].get('skill', '')] += 1
            if m.get('usage'): seen[m.get('id')] = (m.get('model'), m['usage'])
        if d.get('type') == 'user' and desc is None:
            c = m.get('content'); c = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c or [] if isinstance(x, dict))
            if c.strip() and not c.startswith('<'): desc = c[:110].replace('\n', ' ')
    ctx = [u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0) + u.get('input_tokens', 0) for _, u in seen.values()]
    models = collections.Counter(mo for mo, _ in seen.values())
    out.append(dict(f=f.replace(root + '/', ''), agent=at, models=dict(models), turns=len(seen), ts0=ts0, ts1=ts1,
        ctx_sum=sum(ctx), ctx_max=max(ctx or [0]), ctx_avg=int(sum(ctx) / max(len(ctx), 1)),
        out=sum(u.get('output_tokens', 0) for _, u in seen.values()), cw=sum(u.get('cache_creation_input_tokens', 0) for _, u in seen.values()),
        tools=dict(tools.most_common(6)), spawns=dict(spawns), desc=desc))
json.dump(out, open('/tmp/sf-analysis/detail.json', 'w'))
for r in sorted(out, key=lambda r: r['ts0'] or ''):
    print(f"{r['f'][:8]} {'SUB' if 'subagents' in r['f'] else 'MAIN'} {r['agent']:9} {','.join(m.split('-')[1] for m in r['models']):12} turns={r['turns']:4} ctxsum={r['ctx_sum']/1e6:6.1f}M avg={r['ctx_avg']//1000:4}k max={r['ctx_max']//1000:4}k out={r['out']//1000:3}k {r['ts0'][:16] if r['ts0'] else ''} spawns={r['spawns']}")
    print('     ', r['desc'])
