# session-cost

Scripts that read the Claude Code transcripts of this folder
(`~/.claude/projects/<this folder's path with / replaced by ->/`, found by
`_paths.py`; pass another folder as the first argument) and report
token use and estimated cost per agent. Run each with `python3 -I <script>`.

| Script | Output |
|---|---|
| `cost.py` | Estimated $ per role (main, implementer, grunt), split into cache read, cache write, output; count of test/check commands per role. |
| `detail.py` | One line per transcript: model, turns, context avg/max, grunt calls. |
| `deep.py` | implementer runs: tokens added per tool, biggest tool results, full cache rebuilds. |
| `deep2.py` | implementer and main: thinking vs tool input size, heredoc edits, cache TTL of writes. |
| `miss.py` | The events just before each full cache rebuild. |
| `ttl.py` | Simulated cache cost of subagents with a 1h TTL instead of 5m. |
| `grunt.py` | Each grunt task: size, turns, max context, start of task and report. |

Prices are hard-coded (October 2026 list prices): Opus 5.5 $4/$20 (cache read
$0.20), Sonnet 5.5 $2/$10 (cache read $0.10 since 2026-10-11), Haiku 5.5
$0.10/$0.50 (cache read assumed $0.01). Check current prices before you trust
the totals.
Cache writes: 5m TTL 1.25x input, 1h TTL 2x input. Output tokens in the
transcripts are undercounted, so totals are a floor.
