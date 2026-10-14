---
description: Hand a straightforward task to manager, which splits it into small pieces run in parallel waves of grunt (Haiku) agents. No design doc needed.
argument-hint: <task description>
context: fork
agent: manager
background: false
disable-model-invocation: true
---
Task: $ARGUMENTS

If no task is given, stop and say so.
