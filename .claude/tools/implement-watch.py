#!/usr/bin/env python3
"""Show an /implement run (stream-json log) as a readable chat.

  implement-watch.py <project | log path> [--once] [--full]

<project> picks the newest .claude/runs/<project>-*.log. Without --once it
follows the log until the run ends (Ctrl-C to stop watching; the run goes on).
--once prints what is there and exits. --full does not shorten tool input and
results. Subagent (grunt) events are indented under the Agent call that
started them.

Each line shows the agent's context size when it was written ([grunt 31k]).
When a subagent ends, and at the end of the run (or the --once snapshot), it
prints the usage per agent: turns, peak context, new input (input + cache
writes), cache reads, output, model.
"""
import glob
import json
import os
import re
import sys
import time

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runs")
SHORT = 300

args = [a for a in sys.argv[1:] if not a.startswith("--")]
once = "--once" in sys.argv
full = "--full" in sys.argv
if len(args) != 1:
    sys.exit(__doc__.strip())


def find_log(arg):
    if os.path.isfile(arg):
        return arg
    logs = sorted(glob.glob(os.path.join(RUNS, f"{glob.escape(arg)}-*.log")), key=os.path.getmtime)
    if not logs:
        sys.exit(f"implement-watch: no log for '{arg}' in {os.path.normpath(RUNS)}")
    return logs[-1]


def short(text):
    text = " ".join(str(text).split())
    return text if full or len(text) <= SHORT else text[:SHORT] + " ..."


def tool_input(name, inp):
    for key in ("command", "file_path", "pattern", "description"):
        if key in inp:
            extra = f" ({inp['subagent_type']})" if name == "Agent" and "subagent_type" in inp else ""
            return f"{inp[key]}{extra}"
    return json.dumps(inp)


def result_text(content):
    if isinstance(content, list):
        content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    return content or ""


agents = {}  # Agent tool_use id -> subagent label
usage = {}   # None (implementer) or Agent tool_use id -> usage of that agent
seen = set()  # message ids: one message can span several events


def k(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n // 1000}k" if n >= 1000 else str(n)


def family(model):
    m = re.search(r"fable|opus|sonnet|haiku", model or "")
    return m.group(0) if m else (model or "?")


def count(parent, label, msg):
    """Add one assistant message's usage to its agent."""
    u = msg.get("usage") or {}
    mid = msg.get("id")
    if not u or msg.get("model") == "<synthetic>" or (mid and mid in seen):
        return
    if mid:
        seen.add(mid)
    a = usage.setdefault(parent, {"label": label, "model": set(), "turns": 0, "ctx": 0,
                                  "peak": 0, "new": 0, "read": 0, "out": 0})
    inp = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
    read = u.get("cache_read_input_tokens") or 0
    a["model"].add(family(msg.get("model")))
    a["turns"] += 1
    a["ctx"] = inp + read
    a["peak"] = max(a["peak"], a["ctx"])
    a["new"] += inp
    a["read"] += read
    a["out"] += u.get("output_tokens") or 0


def line(a):
    return (f"{a['turns']} turns, peak ctx {k(a['peak'])}, new in {k(a['new'])}, "
            f"cache read {k(a['read'])}, out {k(a['out'])}, {'/'.join(sorted(a['model']))}")


def summary():
    if not usage:
        return
    print("--- usage per agent")
    for a in usage.values():
        print(f"    {a['label']:<12} {line(a)}")
    fams = {}
    for a in usage.values():
        f = fams.setdefault("/".join(sorted(a["model"])), [0, 0, 0])
        f[0] += a["new"]; f[1] += a["read"]; f[2] += a["out"]
    for fam, (new, read, out) in fams.items():
        print(f"    total {fam:<6} new in {k(new)}, cache read {k(read)}, out {k(out)}")


def show(ev):
    """Print one event. Return True when the run has ended."""
    kind = ev.get("type")
    parent = ev.get("parent_tool_use_id")
    label = agents.get(parent, "subagent") if parent else "implementer"
    pad = "    " if parent else ""
    if kind == "assistant":
        count(parent, label, ev.get("message", {}))
    ctx = usage.get(parent, {}).get("ctx")
    tag = f"{label} {k(ctx)}" if ctx else label
    if kind == "system" and ev.get("subtype") == "init":
        print(f"--- session {ev.get('session_id', '?')} model {ev.get('model', '?')}")
    elif kind == "assistant":
        for c in ev.get("message", {}).get("content", []):
            if c.get("type") == "text" and c.get("text", "").strip():
                print(f"{pad}[{tag}] {c['text'].strip() if full else short(c['text'])}")
            elif c.get("type") == "tool_use":
                inp = c.get("input") or {}
                if c.get("name") == "Agent":
                    agents[c.get("id")] = inp.get("subagent_type", "subagent")
                print(f"{pad}[{tag}] -> {c.get('name')}: {short(tool_input(c.get('name'), inp))}")
    elif kind == "user":
        for c in ev.get("message", {}).get("content", []):
            if isinstance(c, dict) and c.get("type") == "tool_result":
                mark = "ERROR" if c.get("is_error") else "<-"
                print(f"{pad}    {mark} {short(result_text(c.get('content')))}")
                done = usage.get(c.get("tool_use_id"))
                if done:
                    print(f"{pad}    -- {done['label']} done: {line(done)}")
    elif kind == "result" and not parent:
        cost = ev.get("total_cost_usd")
        summary()
        print(f"--- end: {ev.get('subtype', '?')}, {ev.get('num_turns', '?')} turns"
              + (f", ${cost:.2f}" if isinstance(cost, (int, float)) else ""))
        return True
    return False


def lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        buf = ""
        while True:
            chunk = f.readline()
            if chunk:
                buf += chunk
                if buf.endswith("\n"):
                    yield buf
                    buf = ""
            elif once:
                return
            else:
                yield None  # no new data yet
                time.sleep(0.5)


def running(path):
    """False when the run's state file says it finished (or the run is gone)."""
    try:
        with open(path[:-4] + ".json") as f:
            st = json.load(f)
    except (OSError, ValueError):
        return True
    if st.get("status") != "running":
        return False
    try:
        os.kill(st["pid"], 0)
    except (OSError, KeyError, TypeError):
        return False
    return True


def main():
    log = find_log(args[0])
    print(f"--- {log}")
    idle = 0
    try:
        for raw in lines(log):
            if raw is None:
                idle += 1
                if idle % 10 == 0 and not running(log):
                    summary()
                    print("--- run is not running any more")
                    return
                continue
            idle = 0
            if not raw.startswith("{"):
                print(raw.rstrip())
                continue
            try:
                ev = json.loads(raw)
            except ValueError:
                continue
            if show(ev):
                return
            sys.stdout.flush()
        summary()  # --once: the log ended before the run did
    except KeyboardInterrupt:
        summary()
        print("--- stopped watching (the run goes on)")


main()
