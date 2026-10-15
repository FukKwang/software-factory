#!/usr/bin/env python3
"""PreToolUse hook for the architect agent: Edit/Write only design docs and memory.

Allowed: <project>/docs/design*.md (design.md, design-phase2.md, docs/design/*.md),
<project>/docs/handoff.md (the board) and ~/.claude/projects/*/memory/*.md.
Builders forked from the architect session (/implement -> implementer, which
spawns grunt) are let through: the hook input carries their agent_id/agent_type.
A grunt the architect started itself is read-only: it may write only to the
temp dir. The subagent's meta file tells them apart: a grunt started by
implementer has a parentAgentId, one started by the architect has none.
Anything else is blocked (exit 2); the reason goes back to the agent.
"""
import json
import os
import sys
import tempfile

BUILDERS = {"implementer", "grunt"}


def started_by_architect(inp):
    """True if this grunt was started by the main session (the architect).

    Unknown (meta file missing or unreadable) counts as False, so a build is
    never blocked by a missing file.
    """
    path = inp.get("transcript_path") or ""
    agent = inp.get("agent_id")
    if os.path.basename(path).startswith("agent-"):
        meta = path[:-len(".jsonl")] + ".meta.json"
    else:
        meta = os.path.join(os.path.dirname(path), inp.get("session_id", ""),
                            "subagents", f"agent-{agent}.meta.json")
    try:
        with open(meta) as f:
            return not json.load(f).get("parentAgentId")
    except (OSError, ValueError):
        return False


data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path") or ""
path = os.path.realpath(os.path.expanduser(path))
home = os.path.realpath(os.path.expanduser("~"))

if data.get("agent_id") and data.get("agent_type") in BUILDERS:
    if data.get("agent_type") != "grunt" or not started_by_architect(data):
        sys.exit(0)
    tmp = os.path.realpath(tempfile.gettempdir())
    if path.startswith(tmp + os.sep):
        sys.exit(0)
    print(
        f"architect grunt: blocked write to {path}. A grunt started by the "
        "architect is read-only: change no files (logs go to /tmp). Report "
        "what you found instead.",
        file=sys.stderr,
    )
    sys.exit(2)

design = ("/docs/design" in path and path.endswith(".md")) or path.endswith("/docs/handoff.md")
memory = (path.startswith(os.path.join(home, ".claude", "projects") + os.sep)
          and "/memory/" in path and path.endswith(".md"))

if design or memory:
    sys.exit(0)

print(
    f"architect: blocked write to {path}. The architect only writes "
    "<project>/docs/design.md, the board in <project>/docs/handoff.md (and "
    "memory). Put the change in the design doc, update the board, commit, and "
    "start the build with Skill(\"implement\", \"<project>\").",
    file=sys.stderr,
)
sys.exit(2)
