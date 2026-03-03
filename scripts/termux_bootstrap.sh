#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_URL="https://github.com/IrsanAI/TPM-Agent.git"
TARGET_DIR="$HOME/TPM-Agent"

echo "[IrsanAI] Termux bootstrap started"
pkg update -y
pkg upgrade -y
pkg install -y git python curl termux-api

if [ ! -d "$TARGET_DIR/.git" ]; then
  echo "[IrsanAI] Cloning TPM-Agent into $TARGET_DIR"
  git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
echo "[IrsanAI] Installing Termux-safe Python dependencies"
python -m pip install -r requirements-termux.txt

echo "[IrsanAI] Environment ready"
echo "Next:"
echo "  cd $TARGET_DIR"
echo "  python scripts/tpm_cli.py env"
echo "  bash scripts/termux_forge.sh start"
