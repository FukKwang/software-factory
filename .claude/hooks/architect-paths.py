#!/usr/bin/env python3
"""PreToolUse hook for the architect agent: Edit/Write only design docs and memory.

Allowed: <project>/docs/design*.md (design.md, design-phase2.md, docs/design/*.md),
<project>/docs/handoff.md (the board) and ~/.claude/projects/*/memory/*.md.
Subagents named implementer or grunt are let through (the hook input carries
their agent_id/agent_type). /implement runs implementer headless, outside this hook.
Anything else is blocked (exit 2); the reason goes back to the agent.
"""
import json
import os
import sys

BUILDERS = {"implementer", "grunt"}

data = json.load(sys.stdin)
if data.get("agent_id") and data.get("agent_type") in BUILDERS:
    sys.exit(0)

path = (data.get("tool_input") or {}).get("file_path") or ""
path = os.path.realpath(os.path.expanduser(path))
home = os.path.realpath(os.path.expanduser("~"))

design = ("/docs/design" in path and path.endswith(".md")) or path.endswith("/docs/handoff.md")
memory = (path.startswith(os.path.join(home, ".claude", "projects") + os.sep)
          and "/memory/" in path and path.endswith(".md"))

if design or memory:
    sys.exit(0)

print(
    f"architect: blocked write to {path}. The architect only writes "
    "<project>/docs/design.md, the board in <project>/docs/handoff.md (and "
    "memory). Put the change in the design doc, update the board, and tell the "
    "user to run `/implement <project>` here or send `next <project>` in the "
    "implementer session.",
    file=sys.stderr,
)
sys.exit(2)
