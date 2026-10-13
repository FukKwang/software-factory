# software-factory

A Claude Code setup for building many small, independent projects with three
models:

- **Opus** designs with you in the main session and reviews the results.
- **Sonnet** (`implementer` agent) plans the implementation and reviews it.
- **Haiku** (`grunt` agent) writes most of the code, tests and docs, and runs
  every long command.

The rules are written to keep the Sonnet lead's context small, because that
was most of the bill. Measured result on a real project: a task that used to
cost several dollars per lead run cost $0.41. Details in
[cost-findings.md](cost-findings.md).

## Setup

1. Use this repo as a template, or clone it, into a folder of its own.
2. Each project goes in its own top-level folder and is its own git repo.
   The root `.gitignore` ignores every project folder, so this repo only
   holds the workflow.
3. Requirements: Claude Code with access to Opus, Sonnet and Haiku.
   Python 3 for the cost scripts (optional).

## Workflow

1. Create a project: `mkdir my-app && cd my-app && git init && cd ..`.
   Optional: write the project rules in `my-app/CLAUDE.md`.
2. Run `claude --agent architect` in this root folder (Opus). The architect
   grills you on the design in rounds of numbered questions, each with its
   recommended answer, until every decision is settled. It only writes
   `my-app/docs/design.md`; a hook blocks it from editing code. (Plain
   `claude` also uses Opus, `.claude/settings.json`, without these rules.)
3. Confirm the design. The architect writes `my-app/docs/design.md` with a
   `Size: small | long` line. Subagents do not see the conversation, so the
   design file must be complete.
4. Implement:
   - **Small task** (`Size: small`, under about 30 minutes):
     `/implement my-app <task>`. `implementer` runs as a subagent and returns
     a summary.
   - **Long phase** (`Size: long`, hours, many test runs):
     `/implement-long my-app <task>`. `implementer` runs as a headless
     `claude -p --permission-mode auto` session in the background, with a
     fresh context and the main-session prompt cache (1 hour). Your session
     stays free and is notified when it exits; the log is in
     `.claude/runs/`. It can't ask you anything, so open points go to
     `my-app/docs/handoff.md`.
   - Or talk to Sonnet directly: `claude --agent implementer` in a new
     terminal, then "Implement phase N of my-app per docs/design.md".
5. Review in the Opus session: read the summary, `my-app/docs/handoff.md`,
   `git log` and `git diff`. Run the project's checks yourself; summaries
   can be wrong.

## Files

| Path | What it is |
|------|------------|
| `CLAUDE.md` | Rules and workflow for Claude in this folder. |
| `.claude/settings.json` | Opus as the main model. Put personal settings in `.claude/settings.local.json` (not committed). |
| `.claude/agents/architect.md` | Opus architect: grills you on the design, writes `docs/design.md`, reviews builds. Never builds. |
| `.claude/hooks/architect-paths.py` | Blocks the architect's Edit/Write outside `docs/design*.md` and memory. |
| `.claude/agents/implementer.md` | Sonnet lead: plans, delegates, reviews. Hard rules on context size. |
| `.claude/agents/grunt.md` | Haiku worker: implements fully specified tasks, runs checks, short reports. |
| `.claude/skills/implement/SKILL.md` | The `/implement <project> [task]` command. |
| `.claude/skills/implement-long/SKILL.md`, `.claude/tools/implement-long.sh` | The `/implement-long <project> [task]` command: headless implementer in the background. |
| `.claude/tools/implement-long-stats.py` | Usage of `/implement-long` runs: `finish` prints cost, tokens per model, subagents and permission denials at the end; `status` prints running and recent runs as JSON for a status line. |
| `.claude/tools/session-cost/` | Scripts that read your Claude Code transcripts and report cost per agent. |
| `cost-findings.md` | What the workflow cost before and after the current rules, and the cache TTL analysis. |

## Measure your own runs

`/implement-long` prints each run's cost, tokens per model, subagent count and
permission denials when it exits, and keeps them in `.claude/runs/<run>.json`.
For a live view, have your status line call
`python3 -I .claude/tools/implement-long-stats.py status`: a JSON list of
running runs and runs that finished in the last 2 hours, with
`name, status, elapsed_s, tokens, ctx, cost_usd`.

```bash
python3 -I .claude/tools/session-cost/cost.py     # $ per role
python3 -I .claude/tools/session-cost/detail.py   # context size per run
python3 -I .claude/tools/session-cost/ttl.py      # would a 1h subagent cache TTL help?
```

Prices are hard-coded in the scripts (October 2026). Check current prices
first.
