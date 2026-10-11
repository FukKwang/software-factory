# software-factory

A Claude Code setup for building many small, independent projects with three
models:

- **Opus** designs with you in the main session and reviews the results.
- **Sonnet** (`impl-lead` agent) plans the implementation and reviews it.
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
2. Run `claude` in this root folder. The session uses Opus
   (`.claude/settings.json`).
3. Discuss the requirements and the design. When you approve it, say:
   "Write the design to `my-app/docs/design.md`." Subagents do not see the
   conversation, so the design file must be complete.
4. Implement:
   - **Small task** (under about 30 minutes): `/implement my-app <task>`.
     `impl-lead` runs as a subagent and returns a summary.
   - **Big phase** (hours, many test runs): in a new terminal in this folder,
     `claude --agent impl-lead`, then "Implement phase N of my-app per
     docs/design.md". You talk to Sonnet directly, and the main-session
     prompt cache (1 hour) makes long test waits cheap.
5. Review in the Opus session: read the summary, `my-app/docs/handoff.md`,
   `git log` and `git diff`. Run the project's checks yourself; summaries
   can be wrong.

## Files

| Path | What it is |
|------|------------|
| `CLAUDE.md` | Rules and workflow for Claude in this folder. |
| `.claude/settings.json` | Opus as the main model. Put personal settings in `.claude/settings.local.json` (not committed). |
| `.claude/agents/impl-lead.md` | Sonnet lead: plans, delegates, reviews. Hard rules on context size. |
| `.claude/agents/grunt.md` | Haiku worker: implements fully specified tasks, runs checks, short reports. |
| `.claude/skills/implement/SKILL.md` | The `/implement <project> [task]` command. |
| `.claude/tools/session-cost/` | Scripts that read your Claude Code transcripts and report cost per agent. |
| `cost-findings.md` | What the workflow cost before and after the current rules, and the cache TTL analysis. |

## Measure your own runs

```bash
python3 -I .claude/tools/session-cost/cost.py     # $ per role
python3 -I .claude/tools/session-cost/detail.py   # context size per run
python3 -I .claude/tools/session-cost/ttl.py      # would a 1h subagent cache TTL help?
```

Prices are hard-coded in the scripts (October 2026). Check current prices
first.
