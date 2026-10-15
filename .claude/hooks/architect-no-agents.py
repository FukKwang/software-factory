#!/usr/bin/env python3
"""PreToolUse hook for the architect agent: the architect may start only grunt.

architect lists Agent(implementer, grunt) so that /implement works: a
subagent may start only the agent types the main session's agent allows, so
without it the forked implementer could not start grunt. The architect itself
may start `grunt` for read-only work (fact finding, running checks, summing up
diffs) to keep its own context small. Starting `implementer` (or any other
type) directly is blocked: the build starts only through the `implement`
skill. Agent calls from inside a subagent (the hook input carries agent_id)
are let through.
"""
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

if data.get("tool_name") not in ("Agent", "Task") or data.get("agent_id"):
    sys.exit(0)

subagent = ((data.get("tool_input") or {}).get("subagent_type") or "").strip()
if subagent == "grunt":
    sys.exit(0)

reason = (
    f"Blocked: the architect starts only `grunt` (read-only tasks), not "
    f"`{subagent or 'default'}`. To build, commit the board as ready-to-build "
    "and call Skill(\"implement\", \"<project>\")."
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
}))
sys.exit(0)
