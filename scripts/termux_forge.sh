#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="$REPO_ROOT/state"
PID_FILE="$STATE_DIR/termux_forge.pid"
LOG_FILE="$STATE_DIR/termux_forge.log"
PORT="${PORT:-8787}"
URL="http://127.0.0.1:${PORT}"

mkdir -p "$STATE_DIR"

start() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Forge already running at $URL"
    exit 0
  fi
  cd "$REPO_ROOT"
  nohup python -m uvicorn production.forge_runtime:app --host 0.0.0.0 --port "$PORT" >"$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  sleep 1
  echo "Forge started: $URL"
  echo "Open in browser: $URL"
  if command -v termux-open-url >/dev/null 2>&1; then
    termux-open-url "$URL" || true
  fi
}

stop() {
  if [ ! -f "$PID_FILE" ]; then
    echo "No PID file. Forge appears stopped."
    exit 0
  fi
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    sleep 1
  fi
  rm -f "$PID_FILE"
  echo "Forge stopped. State persisted under $STATE_DIR"
}

status() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Forge running at $URL (pid $(cat "$PID_FILE"))"
  else
    echo "Forge stopped"
  fi
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop || true; start ;;
  status) status ;;
  logs) tail -f "$LOG_FILE" ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
