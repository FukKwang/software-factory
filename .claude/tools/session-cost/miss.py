import json, glob, os
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from _paths import transcripts_dir
root = transcripts_dir()
for f in sorted(glob.glob(root + '/*/subagents/*.jsonl')):
    lines = [json.loads(l) for l in open(f)]
    seen = set()
    for i, d in enumerate(lines):
        m = d.get('message') or {}; u = m.get('usage')
        if d.get('type') != 'assistant' or not u or m.get('id') in seen: continue
        seen.add(m.get('id'))
        if u.get('cache_creation_input_tokens', 0) > 30000 and u.get('cache_read_input_tokens', 0) < 1000:
            prev = []
            for p in lines[max(0, i - 4):i]:
                pm = p.get('message') or {}; c = pm.get('content')
                desc = p.get('type') + ':' + (p.get('subtype') or '')
                if isinstance(c, list): desc += ' ' + ','.join((x.get('type') + ('(' + x.get('name', '') + ')' if x.get('name') else '') + (('=' + str(x.get('content'))[:120].replace('\n', ' ')) if x.get('type') == 'tool_result' else '')) for x in c if isinstance(x, dict))
                elif isinstance(c, str): desc += ' ' + c[:150].replace('\n', ' ')
                elif p.get('content'): desc += ' ' + str(p.get('content'))[:150]
                prev.append(desc)
            print(f.split('/')[-1][:14], 'model', m.get('model'), 'cw', u['cache_creation_input_tokens'], 'speed', u.get('speed'), u.get('service_tier'))
            for x in prev: print('    ', x[:260])
