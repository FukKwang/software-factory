# Cost findings

Measured on one real project: a Go PDF parser with forensic checks, built in
phases over two days (October 2026) with this workflow. Costs are estimates
at API list prices from the Claude Code transcripts, made with
`.claude/tools/session-cost/`. Output tokens in transcripts are undercounted,
so the totals are a floor.

Prices used (October 2026, per million tokens): Opus 5.5 $4 in / $20 out,
Sonnet 5.5 $2 / $10, Haiku 5.5 $0.10 / $0.50. Cache reads: Opus $0.20,
Sonnet $0.20 (cut to $0.10 on 2026-10-11). Cache writes: 1.25x input for a
5-minute TTL, 2x input for a 1-hour TTL.

## 1. Before: the lead's context was the bill

First version of the workflow: the Sonnet lead was told to "delegate
mechanical work" to Haiku.

| Role | Runs | Cost | Share |
|------|------|------|-------|
| impl-lead (Sonnet) | 13 | $56.31 | 72 % |
| main session (Opus) | 9 | $21.41 | 27 % |
| grunt (Haiku) | 22 | $0.32 | 0.4 % |

- $43 of the lead's $56 was **cache reads**: 214M tokens over 1,048 turns,
  about 205k tokens of context re-read on every turn. Its real output cost
  almost nothing.
- One lead run: 219 turns, mean context 377k, max 553k, no Haiku call at
  all: about $18, 23 % of everything.
- What filled the context: thinking (about 120k), whole files rewritten
  through Bash heredocs (about 86k), and code read with `cat`/`sed` and test
  output (about 110k).
- The lead ran 391 test/check commands itself. Subagents use a 5-minute
  prompt cache; when `check.sh` or fuzzing ran longer, the cache expired and
  the next turn rewrote 110k-366k tokens. That happened 12 times.
- Haiku did more than expected when it was used: one task built a whole
  package from design sections (102 turns, about $0.10); another found a real
  bug while it wrote tests. A whole Haiku task cost less than one lead turn
  at 200k context.

## 2. The change

See `.claude/agents/impl-lead.md` and `grunt.md`.

- The lead plans and reviews; Haiku writes code, tests and docs and runs
  every long command.
- Hard rules for the lead: no long test runs, no reading more than about 100
  lines of code to understand it (ask Haiku for a summary), no heredoc file
  rewrites, commit before every delegation, stop at about 150k context and
  hand off.
- Haiku changes only the files its task lists (parallel tasks get disjoint
  file sets), never changes git state, and reports failures only.
- Every project is a git repo, so a bad Haiku edit is one `git restore` away.
  (Before, a parallel Haiku task truncated a test file with no way back.)

## 3. After: one validation run

Task: make the project's `check.sh` faster without losing coverage.

| Measure | Result |
|---------|--------|
| Cost of the whole run | **$0.41** (lead $0.39, two Haiku tasks $0.02) |
| Lead turns / mean context / max context | 10 / 26k / 32k |
| Long commands run by the lead | 0 |
| Outcome | `check.sh` 13 min 38 s -> 6 min 35 s, green |

Review in the main session still mattered: it found that two timeout tests
had dropped out of the race-detector run and added them back. The lead's own
report pointed at the risk, which made it quick to find.

## 4. Should subagents use a 1-hour cache TTL?

Claude Code can set it (`subagentPromptCacheTtl` setting,
`CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL` env var, or per agent
`experimental: { cacheTtl: "1h" }` in the frontmatter). Simulated on the same
transcripts, with Sonnet cache reads at $0.10:

| Lead runs | 5m TTL | 1h TTL | Difference |
|-----------|--------|--------|------------|
| Before (big context) | $34.63 | $33.74 | −2.5 % |
| After (small context) | $0.45 | $0.49 | +11 % |

- A 1h TTL avoids rebuilds after long waits, but makes every cache write 2x
  input instead of 1.25x. With a small context, rebuilds are cheap and the
  extra write price wins.
- One wait over 5 minutes costs about context size x $2.50/MTok on Sonnet:
  30k -> $0.08, 150k -> $0.38. Waiting itself costs nothing.
- Rule of thumb: 1h pays off only above about 3 long waits per run. For long
  phases, run the lead as its own session (`claude --agent impl-lead`),
  which already uses the main-session 1h TTL. See "Small task or big phase"
  in `CLAUDE.md`.

## Takeaways

1. In a lead/helper setup, the lead's context size is the cost. Which model
   writes the code matters much less.
2. "Delegate mechanical work" is too vague; the lead keeps everything. Hard
   rules plus a cost reason in the agent prompt changed its behaviour.
3. A cheap model can do real implementation work when the task names the
   design sections, the files, the interface and the check.
4. Give helpers a safety net (git) and disjoint files, and keep a review step.
