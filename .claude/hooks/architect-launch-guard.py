#!/usr/bin/env python3
"""PreToolUse hook (settings.json, every session): start /implement only from a ready board.

The architect (or any session) may call Skill("implement", "<project> ...")
itself (autopilot). This hook allows it only when:
  - <project>/docs/design.md and <project>/docs/handoff.md exist,
  - the board's `## Now` says State `ready-to-build` and Next `implementer`,
  - the project's git tree is clean (design and board committed),
  - the current branch is the board's `Branch:` and not master/main.
Other skills pass. Calls from forked builders (agent_id set) pass.
A failed check is a deny with the reason, so the architect fixes the board or
asks the user.
"""
import json
import os
import subprocess
import sys

data = json.load(sys.stdin)
if data.get("tool_name") != "Skill" or data.get("agent_id"):
    sys.exit(0)

tool_input = data.get("tool_input") or {}
skill = (tool_input.get("skill") or "").split(":")[-1]
if skill != "implement":
    sys.exit(0)


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "architect-launch-guard: " + reason,
        }
    }))
    sys.exit(0)


args = (tool_input.get("args") or "").split()
if not args:
    deny("no project folder. Call Skill(implement, \"<project> [task]\").")
root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
project = os.path.realpath(os.path.join(root, args[0]))
design = os.path.join(project, "docs", "design.md")
handoff = os.path.join(project, "docs", "handoff.md")
if not os.path.isfile(design):
    deny(f"{design} does not exist.")
if not os.path.isfile(handoff):
    deny(f"{handoff} does not exist. Write the board first.")

now = {}
in_now = False
with open(handoff, encoding="utf-8") as f:
    for line in f:
        if line.startswith("## "):
            in_now = line.strip() == "## Now"
            continue
        if in_now and line.startswith("- ") and ":" in line:
            key, _, value = line[2:].partition(":")
            now[key.strip().lower()] = value.strip()

state = now.get("state", "").split()[0:1]
nxt = now.get("next", "").split()[0:1]
branch = (now.get("branch", "").split() or [""])[0]
if state != ["ready-to-build"]:
    deny(f"board State is {now.get('state')!r}, not ready-to-build.")
if nxt != ["implementer"]:
    deny(f"board Next is {now.get('next')!r}, not implementer.")
if not branch or branch in ("master", "main"):
    deny(f"board Branch is {branch!r}: work must be on its own branch.")


def git(*cmd):
    r = subprocess.run(["git", "-C", project, *cmd], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


code, current = git("rev-parse", "--abbrev-ref", "HEAD")
if code != 0:
    deny(f"{project} is not a git repo.")
if current != branch:
    deny(f"on branch {current!r}, board says {branch!r}. git switch {branch} first.")
code, dirty = git("status", "--porcelain")
if dirty:
    deny("project tree not clean; commit the design doc and board first:\n" + dirty[:500])

sys.exit(0)
