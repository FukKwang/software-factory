# software-factory

This folder holds many independent projects. Each top-level folder is one project.

## Rules

- Each project folder is self-contained. Do not share or reuse code, configs, or dependencies between projects. Do not create shared folders at the root.
- Work in one project at a time. Do not read or change files in other project folders unless the user asks.
- Each project has its own requirements. Read `<project>/CLAUDE.md` (if it exists) and `<project>/docs/design.md` before you work in a project.
- Every project uses its own dependency setup (its own `package.json`, `pyproject.toml`, virtualenv, and so on) inside its folder.
- Every project is its own local git repo (`git init` when you create the project). The root folder is a separate repo that tracks only the workflow files (`CLAUDE.md`, `README.md`, `cost-findings.md`, `.claude/`); its `.gitignore` ignores every project folder. Never commit project code to the root repo. Do not add a remote or push unless the user asks.

## Project layout

```
<project>/
  CLAUDE.md        # project requirements and rules (optional)
  docs/design.md   # approved design, the handoff to implementation
  ...              # project code
```

## Workflow: design with Opus, implement with Sonnet and Haiku

1. Main session (Opus, best as `claude --agent architect`): discuss the requirements and the design with the user. When the user approves the design, write it to `<project>/docs/design.md`.
2. The user runs `/implement <project> [task]`. It starts `implementer` as a headless background session (`claude -p`), not as a subagent: a subagent cannot start subagents, so it could not delegate to `grunt`. The `implementer` agent (Sonnet) plans the work and reviews it. The `grunt` agent (Haiku) writes most of the code, tests, and docs, and runs all long checks. implementer commits before each delegation, so grunt's changes can be reviewed with `git diff` and reverted.
3. `implementer` updates the board and returns a summary. Review it in the main session against the design.

Shared state between the architect and implementer sessions is the board at the top of `<project>/docs/handoff.md` (`## Now`, `## Open questions`, `## Log`) plus git. Both read it on every message and update and commit it when they hand over. All new work goes on a branch (recorded as `Branch:` on the board), never on `master`/`main`; commit explicit paths only, never `git add -A`.

For a straightforward task with no design, use `claude --agent manager` (or `/manager <task>`). The `manager` agent (Sonnet) always delegates: it splits the task into small pieces with disjoint files and runs them in waves of up to 5 parallel `grunt` agents. It may start only `grunt` (tool allowlist `Agent(grunt)` plus the `manager-grunt-only.py` hook).

Subagents do not see this conversation. The design file is the only handoff, so make `docs/design.md` complete: goal, requirements, file layout, interfaces, decisions, and how to test.

## Running implementer

| Mode | How to run it | Prompt cache TTL |
|---|---|---|
| Unattended (default) | In the Opus session: `/implement <project> <task>` (headless `claude -p --agent implementer --permission-mode auto` in the background, fresh context, log in `.claude/runs/`) | 1 h (main session) |
| Interactive | New terminal in this folder: `claude --agent implementer`, then `next <project>` (builds the phase on the board) | 1 h (main session) |

- Waiting costs nothing; the first turn after a wait of more than 5 minutes rewrites the context to cache (about context size x $2.50/MTok on Sonnet 5.5). At 30k context that is about $0.08 per wait; at 150k about $0.38. A 1h TTL pays off only above about 3 such waits per run.
- In any implementer session the context limit still applies: at about 150k, implementer updates `docs/handoff.md` and commits; then run `/clear` and tell it to continue from the handoff.
- The handoff between sessions is always the files: `docs/design.md` (Opus writes), the board in `docs/handoff.md` (both update) and the git log. The Opus review reads those, plus `git diff`.
- To give subagents a 1h TTL for one session only, start it with `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL=1h claude`.
- Cost analysis and the measurements behind these numbers: `cost-findings.md`. Measure your own runs with `.claude/tools/session-cost/`.
