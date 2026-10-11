import json, glob, os, collections
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from _paths import transcripts_dir
root = transcripts_dir()
for f in sorted(glob.glob(root + '/*/subagents/*.jsonl')):
    if json.load(open(f.replace('.jsonl', '.meta.json'))).get('agentType') != 'grunt': continue
    lines = [json.loads(l) for l in open(f)]
    task = lines[0]['message']['content']; task = task if isinstance(task, str) else ' '.join(x.get('text', '') for x in task if isinstance(x, dict))
    seen = set(); ctx = []; calls = collections.Counter(); last = ''
    for d in lines:
        m = d.get('message') or {}
        if d.get('type') == 'assistant':
            for c in m.get('content') or []:
                if isinstance(c, dict) and c.get('type') == 'tool_use': calls[c['name']] += 1
                if isinstance(c, dict) and c.get('type') == 'text': last = c['text']
            u = m.get('usage')
            if u and m.get('id') not in seen: seen.add(m['id']); ctx.append(u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0))
    print(f"{f.split('/')[-1][6:14]} turns={len(ctx)} maxctx={max(ctx)//1000}k task={len(task)//4}tok report={len(last)//4}tok calls={dict(calls)}")
    print('   TASK:', task[:230].replace('\n', ' '))
    print('   REPORT:', last[:200].replace('\n', ' '))
