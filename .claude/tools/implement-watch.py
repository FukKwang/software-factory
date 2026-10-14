#!/usr/bin/env python3
"""Show an /implement run (stream-json log) as a readable chat.

  implement-watch.py <project | log path> [--once] [--results] [--full] [--no-color]

<project> picks the newest .claude/runs/<project>-*.log. Without --once it
follows the log until the run ends (Ctrl-C to stop watching; the run goes on).
--once prints what is there and exits.

What it shows: each agent's messages, one line per tool call, errors, each
subagent's start, report and usage, and at the end the usage per agent.
Output tokens appear only in the end totals: stream-json writes a message's
usage before the message is generated, so its output count is too low.
Subagents are numbered (grunt#1, grunt#2) and get their own color. The number
after the name is the agent's context size. --results also shows one line per
tool result; --full does not shorten anything.
"""
import glob
import json
import os
import re
import shutil
import sys
import textwrap
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(TOOLS, "..", ".."))
RUNS = os.path.join(ROOT, ".claude", "runs")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
once = "--once" in sys.argv
full = "--full" in sys.argv
results = "--results" in sys.argv or full
color = sys.stdout.isatty() and "--no-color" not in sys.argv and not os.environ.get("NO_COLOR")
if len(args) != 1:
    sys.exit(__doc__.strip())
WIDTH = max(60, shutil.get_terminal_size((120, 40)).columns)

PALETTE = ["36", "33", "35", "32", "34", "91", "93", "95", "92", "94"]  # implementer first


def c(code, text):
    return f"\033[{code}m{text}\033[0m" if color else text


def dim(text):
    return c("2", text)


def find_log(arg):
    if os.path.isfile(arg):
        return arg
    logs = sorted(glob.glob(os.path.join(RUNS, f"{glob.escape(arg)}-*.log")), key=os.path.getmtime)
    if not logs:
        sys.exit(f"implement-watch: no log for '{arg}' in {RUNS}")
    return logs[-1]


def rel(text):
    """Paths relative to the factory root (and the project in it)."""
    return str(text).replace(ROOT + "/", "")


def one_line(text, room):
    text = " ".join(rel(text).split())
    if full or len(text) <= room:
        return text
    return text[:max(10, room - 1)] + "…"


def wrapped(text, indent, lines=None):
    """Wrap a message to the terminal; at most `lines` lines unless --full."""
    out = []
    for para in rel(text).strip().splitlines():
        out += textwrap.wrap(para, WIDTH - len(indent)) or [""]
    if lines and not full and len(out) > lines:
        out = out[:lines] + [f"… ({len(out) - lines} more lines)"]
    return "\n".join(indent + s for s in out)


def tool_arg(name, inp):
    if name == "Agent":
        return inp.get("description") or inp.get("prompt", "")
    for key in ("command", "file_path", "pattern", "url", "query", "message", "description"):
        if key in inp:
            return inp[key]
    return json.dumps(inp)


def result_text(content):
    if isinstance(content, list):
        content = "\n".join(x.get("text", "") for x in content if isinstance(x, dict))
    return content or ""


def k(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n // 1000}k" if n >= 1000 else str(n)


def family(model):
    m = re.search(r"fable|opus|sonnet|haiku", model or "")
    return m.group(0) if m else (model or "?")


agents = {None: {"label": "implementer", "color": PALETTE[0], "pad": "", "key": None}}  # key: Agent tool_use id
tools = {}    # tool_use id -> (agent key, tool name)
usage = {}    # agent key -> usage
seen = set()  # message ids: one message can span several events
kinds = {}    # subagent type -> how many started


def agent(key):
    return agents.get(key) or agents.setdefault(
        key, {"label": "subagent", "color": PALETTE[len(agents) % len(PALETTE)], "pad": "  ", "key": key})


def name(a):
    ctx = usage.get(a["key"], {}).get("ctx")
    return c("1;" + a["color"], a["label"]) + (dim(f" {k(ctx)}") if ctx else "")


def count(key, msg):
    """Add one assistant message's usage to its agent."""
    u = msg.get("usage") or {}
    mid = msg.get("id")
    if not u or msg.get("model") == "<synthetic>" or (mid and mid in seen):
        return
    if mid:
        seen.add(mid)
    a = usage.setdefault(key, {"model": set(), "turns": 0, "ctx": 0, "peak": 0,
                               "new": 0, "read": 0})
    inp = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
    read = u.get("cache_read_input_tokens") or 0
    a["model"].add(family(msg.get("model")))
    a["turns"] += 1
    a["ctx"] = inp + read
    a["peak"] = max(a["peak"], a["ctx"])
    a["new"] += inp
    a["read"] += read


def usage_line(u):
    return (f"{u['turns']} turns, peak ctx {k(u['peak'])}, new in {k(u['new'])}, "
            f"cache read {k(u['read'])}, {'/'.join(sorted(u['model']))}")


def summary(models=None):
    """Usage per agent; with the result event's modelUsage, exact totals per model."""
    if not usage:
        return
    print(c("1", "── usage per agent"))
    width = max(len(agent(key)["label"]) for key in usage)
    for key, u in usage.items():
        a = agent(key)
        print(f"   {c(a['color'], a['label'].ljust(width))}  {usage_line(u)}")
    if models:
        for model, m in models.items():
            new = (m.get("inputTokens") or 0) + (m.get("cacheCreationInputTokens") or 0)
            cost = m.get("costUSD")
            print(f"   total {family(model)}: new in {k(new)}, cache read {k(m.get('cacheReadInputTokens') or 0)}, "
                  f"out {k(m.get('outputTokens') or 0)}" + (f", ${cost:.2f}" if isinstance(cost, (int, float)) else ""))


def show(ev):
    """Print one event. Return True when the run has ended."""
    kind = ev.get("type")
    key = ev.get("parent_tool_use_id")
    a = agent(key)
    pad = a["pad"]
    if kind == "system" and ev.get("subtype") == "init":
        print(c("1", f"── session {ev.get('session_id', '?')}, {family(ev.get('model'))}"))
    elif kind == "assistant":
        msg = ev.get("message", {})
        count(key, msg)
        for b in msg.get("content", []):
            if b.get("type") == "text" and b.get("text", "").strip():
                print(f"{pad}{name(a)}")
                print(wrapped(b["text"], pad + "  ", lines=12))
            elif b.get("type") == "tool_use":
                tool, inp = b.get("name"), b.get("input") or {}
                tools[b.get("id")] = (key, tool)
                if tool == "Agent":
                    sub = inp.get("subagent_type", "subagent")
                    kinds[sub] = kinds.get(sub, 0) + 1
                    new = agent(b.get("id"))
                    new["label"] = f"{sub}#{kinds[sub]}"
                    print(f"{pad}{name(a)} {c('1', '▶ starts')} {c('1;' + new['color'], new['label'])}"
                          f": {one_line(tool_arg(tool, inp), WIDTH - len(pad) - 40)}")
                elif tool == "SubagentHandback":
                    print(f"{pad}{name(a)} {c('1', 'reports:')}")
                    print(wrapped(inp.get("message", ""), pad + "  ", lines=15))
                else:
                    who = c(a["color"], a["label"]) + " " if key else ""  # parallel grunts interleave
                    head = f"{pad}  {dim('⎿')} {who}{c(a['color'], tool)} "
                    room = WIDTH - len(pad) - len(tool) - 6 - (len(a["label"]) + 1 if key else 0)
                    print(head + dim(one_line(tool_arg(tool, inp), room)))
    elif kind == "user":
        for b in ev.get("message", {}).get("content", []):
            if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                continue
            owner, tool = tools.get(b.get("tool_use_id"), (key, "?"))
            text = result_text(b.get("content"))
            if b.get("tool_use_id") in usage:  # a subagent ended
                sub = agent(b.get("tool_use_id"))
                print(f"{pad}{c('1;' + sub['color'], '■ ' + sub['label'] + ' done')}"
                      f"  {dim(usage_line(usage[b.get('tool_use_id')]))}")
            elif b.get("is_error"):
                print(f"{pad}    {c('31', '✗ ' + tool + ':')} {one_line(text, WIDTH - len(pad) - 12)}")
            elif results:
                n = text.count("\n") + 1
                print(f"{pad}    {dim(f'→ {n} lines: ' + one_line(text, WIDTH - len(pad) - 20))}")
    elif kind == "result" and not key:
        cost = ev.get("total_cost_usd")
        summary(ev.get("modelUsage"))
        print(c("1", f"── end: {ev.get('subtype', '?')}, {ev.get('num_turns', '?')} turns"
                + (f", ${cost:.2f}" if isinstance(cost, (int, float)) else "")))
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
    print(c("1", f"── {rel(log)}"))
    idle = 0
    try:
        for raw in lines(log):
            if raw is None:
                idle += 1
                if idle % 10 == 0 and not running(log):
                    summary()
                    print(c("1", "── run is not running any more"))
                    return
                continue
            idle = 0
            if not raw.startswith("{"):
                print(rel(raw.rstrip()))
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
        print()
        summary()
        print(c("1", "── stopped watching (the run goes on)"))


try:
    main()
except BrokenPipeError:  # e.g. piped into head
    os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
