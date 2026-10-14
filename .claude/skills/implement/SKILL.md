---
description: Hand the approved design of a project to implementer in a headless background session (fresh context, auto permissions), so it can delegate to grunt.
argument-hint: <project-folder> [task]
disable-model-invocation: true
---
Project folder and task: $ARGUMENTS

implementer runs as its own headless session, not as a subagent: a subagent
cannot start subagents, so it could not delegate to grunt.

1. The first word is the project folder. If none is given, or
   `<project>/docs/design.md` does not exist, stop and say so.
2. Run with Bash, `run_in_background: true`:
   `bash "<base directory of this skill>/../../tools/implement.sh" <project> <rest of the arguments>`
   (use the base directory shown above this text; `$CLAUDE_PROJECT_DIR` is
   not set in the Bash tool). The script changes to the factory root itself.
3. Tell the user in one line: started, the log path the script prints, how
   to watch it live (`! python3 -I .claude/tools/implement-watch.py <project>`
   here for a snapshot with `--once`, or without `--once` in another
   terminal), and that you will report when it exits. Then end your turn. Do not poll the
   log or wait in a loop: you are notified when it exits.
4. When notified: read the script's output (status, exit code, cost,
   tokens per model, subagents, permission denials, implementer's summary;
   the log is stream-json, don't read it whole),
   `<project>/docs/handoff.md` (open points, next steps), and
   `git -C <project> log --oneline -10`. Report short and numbered, next
   action first: per acceptance criterion pass / fail / not checked, open
   points, last commit, cost and tokens. A non-zero exit or a permission
   denial is a finding, not a pass. If the summary says grunt was not
   available, say so: it means the delegation failed.
