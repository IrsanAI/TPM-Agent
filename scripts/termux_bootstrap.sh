#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_URL="https://github.com/IrsanAI/TPM-Agent.git"
TARGET_DIR="$HOME/TPM-Agent"
STATUS_FILE="$TARGET_DIR/state/install_status.json"

log_status() {
  local phase="$1"
  local progress="$2"
  local module="$3"
  local note="$4"
  mkdir -p "$TARGET_DIR/state" 2>/dev/null || true
  cat > "$STATUS_FILE" <<JSON
{
  "phase": "$phase",
  "progress_pct": $progress,
  "module": "$module",
  "note": "$note",
  "ts": $(date +%s)
}
JSON
  echo "[IrsanAI][${progress}%] $phase :: $module :: $note"
}

log_status "bootstrap" 2 "init" "Termux bootstrap started"
pkg update -y
pkg upgrade -y

log_status "packages" 15 "termux-packages" "Installing OS packages (python/git/termux-api/numpy)"
pkg install -y git python python-pip termux-api python-numpy

if [ ! -d "$TARGET_DIR/.git" ]; then
  log_status "clone" 30 "git" "Cloning TPM-Agent"
  git clone "$REPO_URL" "$TARGET_DIR"
else
  log_status "clone" 30 "git" "Repo already present, pulling latest"
  git -C "$TARGET_DIR" pull --ff-only || true
fi

cd "$TARGET_DIR"

log_status "python" 45 "pip" "Upgrading pip/setuptools/wheel"
python -m pip install --upgrade pip setuptools wheel

log_status "python" 62 "requirements-termux" "Installing Termux-safe python deps"
python -m pip install --no-build-isolation --no-cache-dir -r requirements-termux.txt

log_status "validation" 80 "numpy-check" "Verifying NumPy import from Termux package"
python - <<'PY'
import numpy
print("numpy ok", numpy.__version__)
PY

log_status "runtime" 92 "install-dashboard" "Preparing install dashboard"
python scripts/install_dashboard_server.py --snapshot >/dev/null 2>&1 || true

log_status "done" 100 "complete" "Environment ready"

echo "Next:"
echo "  cd $TARGET_DIR"
echo "  python scripts/tpm_cli.py env"
echo "  python scripts/tpm_cli.py preflight --market ALL"
echo "  python scripts/tpm_cli.py live --history-csv btc_real_24h.csv --notify --vibrate-ms 1000"
echo
echo "Optional install cockpit (mobile/web):"
echo "  python scripts/install_dashboard_server.py --port 8788"
echo "  open http://127.0.0.1:8788"
