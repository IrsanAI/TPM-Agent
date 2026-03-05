#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_URL="https://github.com/IrsanAI/TPM-Agent.git"
TARGET_DIR="$HOME/TPM-Agent"
INSTALL_PORT="8788"

say() {
  echo "[IrsanAI Android OneClick] $*"
}

ensure_pkg() {
  local pkg_name="$1"
  if ! command -v "$pkg_name" >/dev/null 2>&1; then
    say "Installing missing package: $pkg_name"
    pkg install -y "$pkg_name"
  fi
}

say "Preparing Termux environment"
pkg update -y
pkg upgrade -y

ensure_pkg git
ensure_pkg python
ensure_pkg python-pip
ensure_pkg termux-api

if [ -d ".git" ] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  say "Already in a git repository: $(pwd)"
  if [ -f "scripts/termux_bootstrap.sh" ]; then
    TARGET_DIR="$(pwd)"
  fi
fi

if [ ! -d "$TARGET_DIR/.git" ]; then
  say "Cloning TPM-Agent into $TARGET_DIR"
  git clone "$REPO_URL" "$TARGET_DIR"
else
  say "Repository already exists in $TARGET_DIR (syncing latest)"
  git -C "$TARGET_DIR" pull --ff-only || true
fi

cd "$TARGET_DIR"
say "Running IrsanAI installer"
bash scripts/termux_bootstrap.sh

say "Starting install cockpit on port $INSTALL_PORT"
nohup python scripts/install_dashboard_server.py --port "$INSTALL_PORT" >/dev/null 2>&1 &
sleep 1

URL="http://127.0.0.1:${INSTALL_PORT}"
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "$URL" || true
elif command -v am >/dev/null 2>&1; then
  am start -a android.intent.action.VIEW -d "$URL" >/dev/null 2>&1 || true
fi

say "Install cockpit opened at $URL"
say "You can now close this Termux session if desired."
exit 0
