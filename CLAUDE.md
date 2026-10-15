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
2. After the user confirms the design, the architect starts `/implement <project> [task]` itself (background subagent; `architect-launch-guard.py` allows it only from a committed `ready-to-build` board), reviews the result when it finishes, and starts the next already-designed phase if every criterion passed (at most 2 builds per user message). For a long phase the user runs `/implement-detach <project> [task]` (headless session). The `implementer` agent (Sonnet) plans the work and reviews it. The `grunt` agent (Haiku) writes most of the code, tests, and docs, and runs all long checks. implementer commits before each delegation, so grunt's changes can be reviewed with `git diff` and reverted.
3. `implementer` updates the board and returns a summary. The architect reviews it against the design and stops for the user on a failed criterion, an open question, or a new design decision.

Shared state between the architect and implementer sessions is the board at the top of `<project>/docs/handoff.md` (`## Now`, `## Open questions`, `## Log`) plus git. Both read it on every message and update and commit it when they hand over. All new work goes on a branch (recorded as `Branch:` on the board), never on `master`/`main`; commit explicit paths only, never `git add -A`.

**Standing permission to commit.** The user has asked, once for all sessions, that `architect`, `implementer` and `manager` commit their own work without asking first, whenever their agent file says to commit: the architect its design docs and board, implementer its phase's files and board, manager its task's files. Do not ask "Shall I commit?" and do not leave that work uncommitted. The limits stay: explicit paths only, on the board's branch, never on `master`/`main`, no scratch files. Pushing, merging, and adding a remote still need the user's request, with one exception:

**Standing permission to push and merge (architect only).** The architect pushes the board's work branch to the project's existing `origin` after each of its commits. When a review passes every criterion and the board goes to `done`, it merges the branch into the default branch (`--no-ff`) and pushes that too. Never `--force`, never a new remote; on a merge conflict it aborts and asks the user. implementer and manager still need the user's request.

For a straightforward task with no design, use `claude --agent manager` (or `/manager <task>`). The `manager` agent (Sonnet) always delegates: it splits the task into small pieces with disjoint files and runs them in waves of up to 5 parallel `grunt` agents. It may start only `grunt` (tool allowlist `Agent(grunt)` plus the `manager-grunt-only.py` hook).

Subagents do not see this conversation. The design file is the only handoff, so make `docs/design.md` complete: goal, requirements, file layout, interfaces, decisions, and how to test.

## Running implementer

| Mode | How to run it | Prompt cache TTL |
|---|---|---|
| Subagent (default) | In the Opus session: `/implement <project> <task>`. implementer runs as a background subagent and starts grunts; the subagent panel shows the tree. | 5 min |
| Detached | In the Opus session: `/implement-detach <project> <task>` (headless `claude -p --agent implementer --permission-mode auto` in the background, fresh context, log in `.claude/runs/`, watch with `python3 -I .claude/tools/implement-watch.py <project>`). For long phases. | 1 h (main session) |
| Interactive | New terminal in this folder: `claude --agent implementer`, then `next <project>` (builds the phase on the board) | 1 h (main session) |

A subagent can start only the agent types the main session's agent allows. So the session that runs `/implement` must allow `implementer` and `grunt`: `architect.md` lists `Agent(implementer, grunt)` (a hook lets the architect itself start only `grunt`, for read-only tasks: wide fact finding, running checks, summing up big diffs; up to 3 at once), and plain `claude` allows all agents. Without that, implementer gets no Agent tool and does grunt's work itself.

- Waiting costs nothing; the first turn after a wait of more than 5 minutes rewrites the context to cache (about context size x $2.50/MTok on Sonnet 5.5). At 30k context that is about $0.08 per wait; at 150k about $0.38. A 1h TTL pays off only above about 3 such waits per run, so `/implement` keeps the 5 min default.
- In any implementer session the context limit still applies: at about 150k, implementer updates `docs/handoff.md` and commits; then run `/clear` and tell it to continue from the handoff.
- The handoff between sessions is always the files: `docs/design.md` (Opus writes), the board in `docs/handoff.md` (both update) and the git log. The Opus review reads those, plus `git diff`.
- To give subagents a 1h TTL for one session only, start it with `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL=1h claude`.
- Cost analysis and the measurements behind these numbers: `cost-findings.md`. Measure your own runs with `.claude/tools/session-cost/`.
