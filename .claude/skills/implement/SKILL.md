---
description: Hand the approved design of a project to the Sonnet implementation lead.
argument-hint: <project-folder> [extra instructions]
context: fork
agent: impl-lead
background: false
disable-model-invocation: true
---
Project folder and instructions: $ARGUMENTS

Implement the design in <project-folder>/docs/design.md. If no project folder
is given, or it has no docs/design.md, stop and say so.
