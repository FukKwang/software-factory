---
description: Hand the approved design of a project to the Sonnet implementation lead, as a background subagent that delegates to grunt.
argument-hint: <project-folder> [extra instructions]
context: fork
agent: implementer
background: true
---
Project folder and instructions: $ARGUMENTS

Implement the design in <project-folder>/docs/design.md. If no project folder
is given, or it has no docs/design.md, stop and say so.

If the Agent tool is missing or cannot start grunt, stop at once: write
"grunt not available" and the exact error under "Open points" in
<project-folder>/docs/handoff.md, commit, and finish. Do not do grunt's work
yourself. (The main session's agent must allow implementer and grunt, for
example `Agent(implementer, grunt)` in architect.md; a subagent can only start
the agent types the main session's agent allows.)
