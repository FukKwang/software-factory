#!/usr/bin/env python3
"""PreToolUse hook for the architect agent: the architect starts no sub-agents.

architect lists Agent(implementer, grunt) only so that /implement works: a
subagent may start only the agent types the main session's agent allows, so
without it the forked implementer could not start grunt. Agent calls from
inside a subagent (the hook input carries agent_id) are let through; calls
from the architect itself are blocked.
"""
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

if data.get("tool_name") not in ("Agent", "Task") or data.get("agent_id"):
    sys.exit(0)

reason = (
    "Blocked: the architect starts no sub-agents. Find facts yourself (Read, "
    "Grep, git). To build, tell the user to run `/implement <project>` or "
    "`/implement-detach <project>`."
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
}))
sys.exit(0)
