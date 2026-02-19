#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGDIR="$BASE/logs"
mkdir -p "$LOGDIR"

MARKET="${1:-}"
if [[ -z "$MARKET" ]]; then
  echo "Usage: $0 <BTC|COFFEE>"
  exit 1
fi

case "$MARKET" in
  BTC) interval=20 ;;
  COFFEE) interval=20 ;;
  *) echo "Unsupported market: $MARKET"; exit 1 ;;
esac

SESSION="irsanai_${MARKET}"
LOGFILE="$LOGDIR/irsanai_${MARKET}.log"

tmux kill-session -t "$SESSION" 2>/dev/null || true
tmux new-session -d -s "$SESSION" "bash -lc 'cd "$BASE" && python -u production/tpm_agent_process.py --market $MARKET --interval $interval >> "$LOGFILE" 2>&1'"
echo "Starting $MARKET agent..."
