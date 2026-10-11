import json, glob, os, collections, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from _paths import transcripts_dir
root = transcripts_dir()
P = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
for f in sorted(glob.glob(root + '/*/subagents/*.jsonl')) + sorted(glob.glob(root + '/*.jsonl')):
    meta = f.replace('.jsonl', '.meta.json')
    at = json.load(open(meta)).get('agentType') if os.path.exists(meta) else 'MAIN'
    if at == 'grunt': continue
    sizes = collections.Counter(); bash_heredoc = 0; prev_ts = None; seen = set(); gaps = []; ttl = collections.Counter()
    for line in open(f):
        d = json.loads(line); m = d.get('message') or {}
        ts = d.get('timestamp')
        if d.get('type') == 'assistant':
            for c in m.get('content') or []:
                if not isinstance(c, dict): continue
                if c['type'] == 'thinking': sizes['thinking'] += len(c.get('thinking', '') + c.get('signature', '')) // 4
                elif c['type'] == 'text': sizes['text'] += len(c['text']) // 4
                elif c['type'] == 'tool_use':
                    n = len(json.dumps(c['input'])) // 4; sizes['tool_input:' + c['name']] += n
                    if c['name'] == 'Bash' and ('<<' in c['input'].get('command', '') or 'cat >' in c['input'].get('command', '')): bash_heredoc += 1
            u = m.get('usage')
            if u and m.get('id') not in seen:
                seen.add(m['id'])
                cc = u.get('cache_creation') or {}
                for k, v in cc.items(): ttl[k] += v
                if u.get('cache_creation_input_tokens', 0) > 30000 and u.get('cache_read_input_tokens', 0) < 1000 and prev_ts:
                    gaps.append((round((P(ts) - P(prev_ts)).total_seconds()), u['cache_creation_input_tokens']))
        if ts: prev_ts = ts
    if not seen: continue
    print(f"{f.split(root)[1][1:9]} {f.split('/')[-1][:14]:14} {at:9} {dict(sizes.most_common(5))} heredoc_edits={bash_heredoc}")
    print(f"     cache ttl writes={dict(ttl)} rebuilds(gap_s,tokens)={gaps}")
