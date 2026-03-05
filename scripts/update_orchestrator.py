#!/usr/bin/env python3
"""IrsanAI update orchestrator with backup + graceful shutdown workflow."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"
STATUS_FILE = STATE / "update_status.json"
MAINT_FILE = STATE / "maintenance_mode.json"
BACKUP_ROOT = ROOT / "backups"


MIN_FREE_MB = 512


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, check=check)


def read_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "ts": now_iso(),
        "phase": "idle",
        "progress_pct": 0,
        "message": "idle",
        "steps": [],
        "update_available": False,
    }


def write_status(**updates: object) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    st = read_status()
    st.update(updates)
    st["ts"] = now_iso()
    STATUS_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def append_step(name: str, status: str, detail: str = "") -> None:
    st = read_status()
    steps = st.get("steps", [])
    steps.append({"ts": now_iso(), "step": name, "status": status, "detail": detail})
    write_status(steps=steps)


def git_branch() -> str:
    r = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return (r.stdout or "work").strip() or "work"


def git_head() -> str:
    r = run(["git", "rev-parse", "HEAD"])
    return (r.stdout or "").strip()


def remote_head(branch: str) -> str:
    r = run(["git", "ls-remote", "origin", f"refs/heads/{branch}"])
    if r.returncode != 0 or not r.stdout.strip():
        return ""
    return r.stdout.split()[0]


def check_update() -> dict:
    branch = git_branch()
    local = git_head()
    remote = remote_head(branch)
    available = bool(remote and local and remote != local)
    msg = "update available" if available else "already up to date"
    write_status(
        phase="check",
        progress_pct=100,
        message=msg,
        update_available=available,
        branch=branch,
        local_head=local,
        remote_head=remote,
    )
    return read_status()


def set_maintenance(enabled: bool, reason: str = "") -> None:
    if enabled:
        MAINT_FILE.write_text(json.dumps({"enabled": True, "reason": reason, "ts": now_iso()}, indent=2), encoding="utf-8")
    else:
        if MAINT_FILE.exists():
            MAINT_FILE.unlink()


def free_disk_mb(path: Path) -> int:
    usage = shutil.disk_usage(path)
    return int(usage.free / (1024 * 1024))


def db_lock_check() -> tuple[bool, str]:
    db = ROOT / "data" / "irsanai_production.db"
    if not db.exists():
        return True, "database file not present (skipped)"
    try:
        conn = sqlite3.connect(str(db), timeout=1)
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("ROLLBACK;")
        conn.close()
        return True, "database lock check passed"
    except Exception as exc:
        return False, f"database lock check failed: {exc}"


def remote_connectivity_check() -> tuple[bool, str]:
    r = run(["git", "ls-remote", "origin", "HEAD"])
    if r.returncode == 0 and r.stdout.strip():
        return True, "remote connectivity ok"
    detail = (r.stderr or r.stdout or "remote connectivity failed").strip()[:240]
    return False, detail


def preflight_guards() -> tuple[bool, list[str]]:
    issues: list[str] = []
    free_mb = free_disk_mb(ROOT)
    if free_mb < MIN_FREE_MB:
        issues.append(f"insufficient disk space: {free_mb}MB available (< {MIN_FREE_MB}MB)")

    ok_db, db_msg = db_lock_check()
    append_step("preflight_db", "done" if ok_db else "error", db_msg)
    if not ok_db:
        issues.append(db_msg)

    ok_remote, remote_msg = remote_connectivity_check()
    append_step("preflight_network", "done" if ok_remote else "error", remote_msg)
    if not ok_remote:
        issues.append(remote_msg)

    append_step("preflight_disk", "done" if free_mb >= MIN_FREE_MB else "error", f"free disk: {free_mb}MB")
    return (len(issues) == 0, issues)


def graceful_shutdown() -> None:
    append_step("shutdown", "start", "stopping tmux agent sessions and monitor loops")
    for session in ["irsanai_BTC", "irsanai_COFFEE"]:
        run(["tmux", "kill-session", "-t", session])
    run(["pkill", "-f", "production/tpm_live_monitor.py"])
    run(["pkill", "-f", "production/tpm_agent_process.py"])
    run(["pkill", "-f", "scripts/health_monitor_v3.sh"])
    append_step("shutdown", "done", "processes signaled")


def backup_all() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = BACKUP_ROOT / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    append_step("backup", "start", f"creating backup under {out_dir}")

    db = ROOT / "data" / "irsanai_production.db"
    if db.exists():
        try:
            conn = sqlite3.connect(str(db))
            conn.execute("PRAGMA wal_checkpoint(FULL);")
            conn.close()
        except Exception:
            pass

    for item in ["data", "state", "config"]:
        src = ROOT / item
        if src.exists():
            dst = out_dir / item
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    user_bundle = out_dir / "user_knowledge_bundle.tar.gz"
    with tarfile.open(user_bundle, "w:gz") as tf:
        for rel in ["state", "data", "config/reserve_pool.json"]:
            path = ROOT / rel
            if path.exists():
                tf.add(path, arcname=rel)

    append_step("backup", "done", f"backup finished: {out_dir.name}")
    return out_dir


def apply_update() -> dict:
    write_status(phase="apply", progress_pct=1, message="starting orchestrated update", update_available=False)
    set_maintenance(True, "update in progress")

    try:
        write_status(progress_pct=8, message="running preflight guards")
        ok_preflight, issues = preflight_guards()
        if not ok_preflight:
            msg = "; ".join(issues)
            append_step("preflight", "error", msg)
            set_maintenance(False)
            write_status(phase="error", progress_pct=100, message=f"preflight failed: {msg}")
            return read_status()
        append_step("preflight", "done", "all preflight checks passed")

        write_status(progress_pct=18, message="checking upstream")
        st = check_update()
        if not st.get("update_available", False):
            append_step("check", "done", "no update available")
            set_maintenance(False)
            write_status(phase="done", progress_pct=100, message="already up to date")
            return read_status()

        write_status(progress_pct=30, message="graceful shutdown")
        graceful_shutdown()

        write_status(progress_pct=50, message="backup in progress")
        backup_dir = backup_all()

        write_status(progress_pct=70, message="pulling update")
        append_step("git_pull", "start", "git fetch + pull --ff-only")
        branch = git_branch()
        run(["git", "fetch", "origin"])
        pull = run(["git", "pull", "--ff-only", "origin", branch])
        if pull.returncode != 0:
            append_step("git_pull", "error", (pull.stderr or pull.stdout or "git pull failed")[:500])
            raise RuntimeError("git pull failed")
        append_step("git_pull", "done", "repository updated")

        write_status(progress_pct=85, message="restoring user bundle")
        for rel in ["data", "state", "config"]:
            (ROOT / rel).mkdir(parents=True, exist_ok=True)
        append_step("restore", "done", "user data paths ensured")

        old = st.get("local_head", "")
        new = git_head()
        notes = run(["git", "log", "--oneline", "--max-count", "8", f"{old}..{new}"])
        changelog = notes.stdout.strip().splitlines() if notes.stdout.strip() else []

        set_maintenance(False)
        write_status(
            phase="done",
            progress_pct=100,
            message="update complete",
            update_available=False,
            previous_head=old,
            local_head=new,
            backup_dir=str(backup_dir.relative_to(ROOT)),
            changelog=changelog,
            launch_hint="Start with: python scripts/tpm_cli.py live",
        )
        append_step("finish", "done", "update completed successfully")
        return read_status()
    except Exception as exc:
        append_step("fatal", "error", str(exc))
        set_maintenance(False)
        write_status(phase="error", progress_pct=100, message=f"update failed: {exc}")
        return read_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="IrsanAI update orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="check if remote update exists")
    sub.add_parser("status", help="print last update status json")
    sub.add_parser("apply", help="run full orchestrated update flow")

    args = parser.parse_args()

    if args.command == "check":
        st = check_update()
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return 0
    if args.command == "status":
        print(json.dumps(read_status(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "apply":
        st = apply_update()
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return 0 if st.get("phase") == "done" else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
