#!/usr/bin/env bash
# Run implementer as a headless Claude session (fresh context, 1h cache) for a long task.
# Usage (from the factory root): .claude/tools/implement-long.sh <project> [task...]
# Logs to .claude/runs/<project>-<time>.log.
set -uo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
project="${1:-}"
shift || true
task="$*"

design="$root/$project/docs/design.md"
if [[ -z "$project" || ! -f "$design" ]]; then
  echo "implement-long: no design file: ${design}" >&2
  exit 2
fi

runs="$root/.claude/runs"
mkdir -p "$runs"
run="$project-$(date +%Y%m%d-%H%M%S)"
log="$runs/$run.log"     # stream-json: every event, with usage
state="$runs/$run.json"  # status + usage summary (implement-long-stats.py)

prompt="Project folder: $project
Implement the design in $project/docs/design.md. Keep progress in
$project/docs/handoff.md. You run headless: nobody can answer questions or
approve actions. If you need a decision or an action is denied, stop, write it
under \"Open points\" in the handoff, commit, and finish with your summary.
${task:+Task: $task}"

echo "implement-long: $project -> $log"
cd "$root" || exit 2
claude -p --agent implementer --permission-mode auto --output-format stream-json --verbose \
  "$prompt" >"$log" 2>&1 &
pid=$!
jq -n --arg name "$project" --arg log "$log" --argjson pid "$pid" \
  '{name: $name, log: $log, pid: $pid, started: now, status: "running"}' >"$state"
wait "$pid"
code=$?
python3 -I "$root/.claude/tools/implement-long-stats.py" finish "$state" "$code"
exit $code
