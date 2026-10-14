#!/usr/bin/env bash
# Run implementer as a headless Claude session (fresh context, 1h cache).
# Usage (from the factory root): .claude/tools/implement.sh <project> [task...]
# Logs to .claude/runs/<project>-<time>.log.
set -uo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
project="${1:-}"
shift || true
task="$*"

design="$root/$project/docs/design.md"
if [[ -z "$project" || ! -f "$design" ]]; then
  echo "implement: no design file: ${design}" >&2
  exit 2
fi

runs="$root/.claude/runs"
mkdir -p "$runs"
run="$project-$(date +%Y%m%d-%H%M%S)"
log="$runs/$run.log"     # stream-json: every event, with usage
state="$runs/$run.json"  # status + usage summary (implement-stats.py)

prompt="Project folder: $project
Implement the design in $project/docs/design.md. Keep progress in
$project/docs/handoff.md. You run headless: nobody can answer questions or
approve actions. If you need a decision or an action is denied, stop, write it
under \"Open points\" in the handoff, commit, and finish with your summary.
${task:+Task: $task}"

cd "$root" || exit 2
# each project is its own git repo: branch, dirty files and commits are checked there
repo="$root/$project"
# git in a repo owned by another uid needs safe.directory; set it for git and claude only
export_git=(GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0="$repo")
top="$(env "${export_git[@]}" git -C "$repo" rev-parse --show-toplevel 2>/dev/null)"
if [[ "$top" != "$(realpath "$repo")" ]]; then
  echo "implement: $project is not its own git repo (git init it first)"
  exit 2
fi
# new work never goes on the default branch; headless can't switch branches itself
branch="$(env "${export_git[@]}" git -C "$repo" branch --show-current)"
if [[ "$branch" == "master" || "$branch" == "main" || -z "$branch" ]]; then
  echo "implement: $project on '${branch:-detached HEAD}'; switch to the work branch (Branch: on the board) first"
  exit 2
fi
dirty="$(env "${export_git[@]}" git -C "$repo" status --porcelain --untracked-files=no | cut -c4- | tr '\n' ' ')"
dirty="${dirty% }"
if [[ -n "$dirty" ]]; then
  echo "implement: uncommitted changes not yours: $dirty"
  prompt="$prompt
These tracked files had uncommitted changes when you started; they are not yours:
$dirty. Don't edit, stage or commit them. If your task needs one, write it under \"Open points\" and stop."
fi
prompt="$prompt
$project is its own git repo and you run from the factory root: run git only as
\`git -C $project <command>\` (add, commit, status, log, diff), with paths relative to $project."

echo "implement: $project -> $log"
g="git -C $project"
# --allowedTools / --disallowedTools take several values: "--" keeps the prompt out of them
env "${export_git[@]}" \
  claude -p --agent implementer --permission-mode auto --output-format stream-json --verbose \
  --allowedTools "Bash($g add *)" "Bash($g commit *)" "Bash($g status*)" "Bash($g log*)" "Bash($g diff*)" \
  --disallowedTools "Bash($g add -A*)" "Bash($g add --all*)" "Bash($g add .*)" "Bash(git add -A*)" \
    "Bash(git add --all*)" "Bash(git push*)" "Bash(git -C * push*)" \
  -- "$prompt" </dev/null >"$log" 2>&1 &
pid=$!
jq -n --arg name "$project" --arg log "$log" --argjson pid "$pid" \
  '{name: $name, log: $log, pid: $pid, started: now, status: "running"}' >"$state"
wait "$pid"
code=$?
python3 -I "$root/.claude/tools/implement-stats.py" finish "$state" "$code"
exit $code
