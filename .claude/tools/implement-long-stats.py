#!/usr/bin/env python3
"""Usage stats for /implement-long runs (headless `claude -p --output-format stream-json`).

  implement-long-stats.py finish <state.json> <exit>   write the summary into the state
                                                        file, print it for the caller
  implement-long-stats.py status                       JSON list of recent runs (status line)

State files: .claude/runs/<run>.json, written by implement-long.sh:
  {"name", "log", "pid", "started", "status": "running" | "done" | "failed" | "died", ...}
"""
import glob
import json
import os
import re
import sys
import time

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runs")
SHOW_DONE_FOR = 2 * 3600  # finished runs stay in the status line this long


def family(model):
    m = re.search(r"fable|opus|sonnet|haiku", model or "")
    return m.group(0) if m else (model or "?")


def scan(log):
    """Read a stream-json log: tokens per model family, context, cost, final result."""
    out = {"tokens": {}, "ctx": None, "cost_usd": None, "session_id": None,
           "result": None, "last": None}
    seen = set()
    try:
        f = open(log, encoding="utf-8", errors="replace")
    except OSError:
        return out
    with f:
        for line in f:
            if not line.startswith("{"):
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            t = e.get("type")
            if t == "system" and e.get("subtype") == "init" and not out["session_id"]:
                out["session_id"] = e.get("session_id")
            elif t == "assistant":
                msg = e.get("message") or {}
                u = msg.get("usage") or {}
                mid = msg.get("id")
                if not u or msg.get("model") == "<synthetic>" or mid in seen:
                    continue
                seen.add(mid)
                n = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) \
                    + (u.get("output_tokens") or 0)
                fam = family(msg.get("model"))
                out["tokens"][fam] = out["tokens"].get(fam, 0) + n
                if e.get("parent_tool_use_id") is None:  # main thread: its context size
                    out["ctx"] = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) \
                        + (u.get("cache_creation_input_tokens") or 0)
            elif t == "result":
                out["last"] = e  # totals are cumulative: the last one is the whole run
                out["cost_usd"] = e.get("total_cost_usd", out["cost_usd"])
                if isinstance(e.get("result"), str) and e["result"].strip():
                    out["result"] = e["result"]
    return out


def k(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n // 1000}k" if n >= 1000 else str(n)


def dur(s):
    s = int(s)
    return f"{s // 3600}h {s % 3600 // 60}m" if s >= 3600 else f"{s // 60}m {s % 60}s"


def finish(state_path, code):
    st = json.load(open(state_path))
    s = scan(st["log"])
    last = s["last"] or {}
    models = {}
    for m, u in (last.get("modelUsage") or {}).items():
        models[m] = {"input": u.get("inputTokens", 0), "output": u.get("outputTokens", 0),
                     "cache_read": u.get("cacheReadInputTokens", 0),
                     "cache_write": u.get("cacheCreationInputTokens", 0),
                     "cost_usd": round(u.get("costUSD", 0), 4)}
    sub = last.get("subagent_stats") or {}
    denials = last.get("permission_denials") or []
    st.update({
        "status": "done" if code == 0 and not last.get("is_error") else "failed",
        "exit": code,
        "ended": time.time(),
        "wall_s": round(time.time() - st["started"]),
        "session_id": s["session_id"],
        "cost_usd": round(s["cost_usd"] or 0, 4),
        "tokens": s["tokens"],
        "models": models,
        "subagents": {x: sub.get(x, 0) for x in ("spawned", "completed", "failed")},
        "permission_denials": [d.get("tool_name", "?") for d in denials],
    })
    tmp = state_path + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, state_path)

    total = sum(s["tokens"].values())
    per = ", ".join(f"{f} {k(n)}" for f, n in sorted(s["tokens"].items(), key=lambda x: -x[1]))
    print(f"implement-long: {st['name']} {st['status']} (exit {code}) in {dur(st['wall_s'])}")
    print(f"  cost ${st['cost_usd']:.2f} · tokens {k(total)} ({per}) · session {s['session_id']}")
    for m, u in models.items():
        print(f"  {m}: in {k(u['input'])}, cache write {k(u['cache_write'])}, "
              f"cache read {k(u['cache_read'])}, out {k(u['output'])}, ${u['cost_usd']:.2f}")
    print(f"  subagents: {st['subagents']['spawned']} spawned, {st['subagents']['completed']} completed, "
          f"{st['subagents']['failed']} failed · permission denials: {len(denials)}"
          + (f" ({', '.join(st['permission_denials'])})" if denials else ""))
    print(f"  log {st['log']}  state {state_path}")
    print("--- impl-lead summary ---")
    print(s["result"] or "(no result text in the log)")


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def status():
    now = time.time()
    runs = []
    for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        try:
            st = json.load(open(p))
        except (OSError, ValueError):
            continue
        if st.get("status") == "running":
            if not alive(st.get("pid")):
                st["status"] = "died"
            s = scan(st["log"])
            runs.append({"name": st["name"], "status": st["status"],
                         "elapsed_s": round(now - st["started"]),
                         "tokens": sum(s["tokens"].values()), "ctx": s["ctx"],
                         "cost_usd": s["cost_usd"]})
        elif now - st.get("ended", 0) < SHOW_DONE_FOR:
            runs.append({"name": st["name"], "status": st["status"],
                         "elapsed_s": st.get("wall_s", 0),
                         "tokens": sum((st.get("tokens") or {}).values()), "ctx": None,
                         "cost_usd": st.get("cost_usd")})
    print(json.dumps(runs))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "finish":
        finish(sys.argv[2], int(sys.argv[3]))
    elif len(sys.argv) == 2 and sys.argv[1] == "status":
        status()
    else:
        sys.exit(__doc__)
