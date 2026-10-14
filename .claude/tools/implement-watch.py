#!/usr/bin/env python3
"""Show an /implement run (stream-json log) as a readable chat.

  implement-watch.py <project | log path> [--once] [--full]

<project> picks the newest .claude/runs/<project>-*.log. Without --once it
follows the log until the run ends (Ctrl-C to stop watching; the run goes on).
--once prints what is there and exits. --full does not shorten tool input and
results. Subagent (grunt) events are indented under the Agent call that
started them.
"""
import glob
import json
import os
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


def show(ev):
    """Print one event. Return True when the run has ended."""
    kind = ev.get("type")
    parent = ev.get("parent_tool_use_id")
    label = agents.get(parent, "subagent") if parent else "implementer"
    pad = "    " if parent else ""
    if kind == "system" and ev.get("subtype") == "init":
        print(f"--- session {ev.get('session_id', '?')} model {ev.get('model', '?')}")
    elif kind == "assistant":
        for c in ev.get("message", {}).get("content", []):
            if c.get("type") == "text" and c.get("text", "").strip():
                print(f"{pad}[{label}] {c['text'].strip() if full else short(c['text'])}")
            elif c.get("type") == "tool_use":
                inp = c.get("input") or {}
                if c.get("name") == "Agent":
                    agents[c.get("id")] = inp.get("subagent_type", "subagent")
                print(f"{pad}[{label}] -> {c.get('name')}: {short(tool_input(c.get('name'), inp))}")
    elif kind == "user":
        for c in ev.get("message", {}).get("content", []):
            if isinstance(c, dict) and c.get("type") == "tool_result":
                mark = "ERROR" if c.get("is_error") else "<-"
                print(f"{pad}    {mark} {short(result_text(c.get('content')))}")
    elif kind == "result" and not parent:
        cost = ev.get("total_cost_usd")
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
        for line in lines(log):
            if line is None:
                idle += 1
                if idle % 10 == 0 and not running(log):
                    print("--- run is not running any more")
                    return
                continue
            idle = 0
            if not line.startswith("{"):
                print(line.rstrip())
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if show(ev):
                return
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n--- stopped watching (the run goes on)")


main()
