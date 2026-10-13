#!/usr/bin/env python3
"""PreToolUse hook for the manager agent: allow only grunt sub-agents."""
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

if data.get("tool_name") not in ("Agent", "Task"):
    sys.exit(0)

agent = (data.get("tool_input") or {}).get("subagent_type") or ""
if agent == "grunt":
    sys.exit(0)

reason = (
    f"Blocked: manager may only start grunt sub-agents (got {agent or 'none'!r}). "
    "Retry with subagent_type: grunt."
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
}))
sys.exit(0)
