---
description: Hand a long phase of a project's approved design to impl-lead in a headless session (fresh context, 1h cache, auto permissions).
argument-hint: <project-folder> [task]
disable-model-invocation: true
---
Project folder and task: $ARGUMENTS

1. The first word is the project folder. If none is given, or
   `<project>/docs/design.md` does not exist, stop and say so.
2. Run with Bash, `run_in_background: true`:
   `bash "$CLAUDE_PROJECT_DIR/.claude/tools/implement-long.sh" <project> <rest of the arguments>`
3. Tell the user in one line: started, the log path the script prints, and
   that you will report when it exits. Then end your turn. Do not poll the
   log or wait in a loop: you are notified when it exits.
4. When notified: read the script's output (status, exit code, cost,
   tokens per model, subagents, permission denials, impl-lead's summary;
   the log is stream-json, don't read it whole),
   `<project>/docs/handoff.md` (open points, next steps), and
   `git -C <project> log --oneline -10`. Report short and numbered, next
   action first: per acceptance criterion pass / fail / not checked, open
   points, last commit, cost and tokens. A non-zero exit or a permission
   denial is a finding, not a pass.
