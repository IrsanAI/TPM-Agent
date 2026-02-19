#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="$HOME/IrsanAI-TPM/data/irsanai_production.db"
if [[ -f "$BASE/data/irsanai_production.db" ]]; then
  DB="$BASE/data/irsanai_production.db"
fi
LOGDIR="$BASE/logs"
STATEDIR="$BASE/state"

mkdir -p "$LOGDIR" "$STATEDIR"

LOCKFILE="$STATEDIR/health_monitor.lock"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "$(date '+%F %T') [MON] Already running. Exit."
  exit 0
fi

log() {
  echo "$(date '+%F %T') [MON-v3] $*"
}

check_data_quality() {
  local market="$1"
  local prices
  prices=$(sqlite3 "$DB" "SELECT price FROM price_history WHERE market='$market' ORDER BY timestamp DESC LIMIT 5" 2>/dev/null || echo "")

  if [[ -z "$prices" ]]; then
    echo "0"
    return
  fi

  local count unique
  count=$(echo "$prices" | wc -l)
  unique=$(echo "$prices" | sort -u | wc -l)

  if [[ "$count" -eq 0 ]]; then
    echo "0"
  elif [[ "$unique" -eq 1 ]]; then
    echo "0.3"
  else
    echo "1.0"
  fi
}

log_metric() {
  local agent="$1" metric="$2" value="$3"
  sqlite3 "$DB" "INSERT INTO performance_metrics (agent_name, metric_type, value) VALUES ('$agent', '$metric', $value)" 2>/dev/null || true
}

log_event() {
  local event_type="$1" agent="$2" details="$3"
  sqlite3 "$DB" "INSERT INTO system_events (event_type, agent_name, details) VALUES ('$event_type', '$agent', '$details')" 2>/dev/null || true
}

MARKETS=("BTC" "COFFEE")
CHECK_INTERVAL=20

log "Health Monitor v3 starting..."

while true; do
  for M in "${MARKETS[@]}"; do
    sess_ok=0
    proc_ok=0
    tmux has-session -t "irsanai_$M" 2>/dev/null && sess_ok=1
    pgrep -f "tpm_agent_process.py --market $M" >/dev/null 2>&1 && proc_ok=1

    dage=$(sqlite3 "$DB" "SELECT CASE WHEN MAX(timestamp) IS NULL THEN 999999 ELSE (strftime('%s','now') - strftime('%s', MAX(timestamp))) END FROM price_history WHERE market='$M';" 2>/dev/null || echo 999999)

    quality=$(check_data_quality "$M")

    log "$M sess=$sess_ok proc=$proc_ok db_age=${dage}s quality=$quality"

    log_metric "$M" "db_age" "$dage"
    log_metric "$M" "quality_score" "$quality"

    unhealthy=""
    if [[ "$sess_ok" -eq 0 || "$proc_ok" -eq 0 ]]; then
      unhealthy="process_missing"
    elif [[ "$dage" -gt 180 ]]; then
      unhealthy="db_stale"
    elif [[ "$quality" == "0" || "$quality" == "0.3" ]]; then
      unhealthy="low_quality"
    fi

    if [[ -n "$unhealthy" ]]; then
      log "$M unhealthy: $unhealthy → restarting"
      log_event "RESTART" "$M" "$unhealthy"
      tmux kill-session -t "irsanai_$M" 2>/dev/null || true
      sleep 2
      bash "$BASE/scripts/start_agents.sh" "$M"
    fi
  done

  sleep "$CHECK_INTERVAL"
done
