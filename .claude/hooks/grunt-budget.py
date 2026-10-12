#!/usr/bin/env python3
"""PostToolUse hook for the grunt agent: warns it when its task gets too big.

Reads the subagent's own transcript, takes the current context size (last
assistant usage) and the time since the task started, and adds a note to the
agent's context:

- soft limit (once): finish the current step, start no new experiments;
- hard limit (after every tool call): stop and report.

Limits can be changed with GRUNT_SOFT_TOKENS, GRUNT_HARD_TOKENS,
GRUNT_SOFT_MIN, GRUNT_HARD_MIN. Any error makes the hook silent: it must
never block grunt's work.
"""
import json
import os
import sys
import tempfile
from datetime import datetime

SOFT_TOKENS = int(os.environ.get("GRUNT_SOFT_TOKENS", 80_000))
HARD_TOKENS = int(os.environ.get("GRUNT_HARD_TOKENS", 110_000))
SOFT_MIN = float(os.environ.get("GRUNT_SOFT_MIN", 15))
HARD_MIN = float(os.environ.get("GRUNT_HARD_MIN", 25))

SOFT_MSG = (
    "Budget soft limit ({why}). Finish the step you are on, then run the "
    "task's check once and report. Start no new experiments, sweeps, or "
    "probe files. Read no more whole files."
)
HARD_MSG = (
    "Budget hit ({why}). Stop now. Leave the code compiling (revert a "
    "half-done edit if needed), delete probe files, and report: what is "
    "done, what is left, the last check result, and what filled your "
    "context (files read, edits, runs), so the lead can split the rest."
)


def transcript_of(inp):
    path = inp.get("transcript_path") or ""
    if os.path.basename(path).startswith("agent-"):
        return path
    agent = inp.get("agent_id")
    if not agent:
        return None
    return os.path.join(os.path.dirname(path), inp["session_id"],
                        "subagents", f"agent-{agent}.jsonl")


def measure(path):
    first = last = None
    ctx = 0
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            ts = r.get("timestamp")
            if ts:
                t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                first = first or t
                last = t
            u = (r.get("message") or {}).get("usage")
            if u:
                ctx = (u.get("input_tokens", 0)
                       + u.get("cache_read_input_tokens", 0)
                       + u.get("cache_creation_input_tokens", 0))
    minutes = (last - first).total_seconds() / 60 if first else 0.0
    return ctx, minutes


def main():
    inp = json.load(sys.stdin)
    path = transcript_of(inp)
    if not path or not os.path.exists(path):
        return
    ctx, minutes = measure(path)
    why = f"context {ctx // 1000}k tokens, {minutes:.0f} min"
    if ctx >= HARD_TOKENS or minutes >= HARD_MIN:
        msg = HARD_MSG.format(why=why)
    elif ctx >= SOFT_TOKENS or minutes >= SOFT_MIN:
        flag = os.path.join(tempfile.gettempdir(),
                            f"grunt-budget-{inp.get('agent_id', 'x')}.soft")
        if os.path.exists(flag):
            return
        open(flag, "w").close()
        msg = SOFT_MSG.format(why=why)
    else:
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse", "additionalContext": msg}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
