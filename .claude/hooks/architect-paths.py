#!/usr/bin/env python3
"""PreToolUse hook for the architect agent: Edit/Write only design docs and memory.

Allowed: <project>/docs/design*.md (design.md, design-phase2.md, docs/design/*.md)
and ~/.claude/projects/*/memory/*.md. Anything else is blocked (exit 2); the
reason goes back to the agent.
"""
import json
import os
import sys

data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path") or ""
path = os.path.realpath(os.path.expanduser(path))
home = os.path.realpath(os.path.expanduser("~"))

design = "/docs/design" in path and path.endswith(".md")
memory = (path.startswith(os.path.join(home, ".claude", "projects") + os.sep)
          and "/memory/" in path and path.endswith(".md"))

if design or memory:
    sys.exit(0)

print(
    f"architect: blocked write to {path}. The architect only writes "
    "<project>/docs/design.md (and memory). Put the change in the design doc "
    "and tell the user to run /implement or /implement-long <project>.",
    file=sys.stderr,
)
sys.exit(2)
