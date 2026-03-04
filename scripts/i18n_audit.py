#!/usr/bin/env python3
"""Lightweight localization audit for README i18n files.

Scans docs/i18n/README.*.md and reports lines that appear English-heavy,
so translators can iteratively close remaining localization gaps.
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "docs" / "i18n"
SKIP = {"README.bs.md"}

WORD_RE = re.compile(r"[A-Za-z]{3,}")
EN_STOP = re.compile(r"\b(the|and|with|from|for|you|your|what|when|where|this|that|only|run|check|next|steps|reliability|scientific|operator|investor|skeptic|trader|includes)\b", re.IGNORECASE)


def score_line(line: str) -> int:
    # keep commands/code low priority
    if line.strip().startswith("```") or line.strip().startswith("|"):
        return 0
    if "`" in line:
        return 0
    words = WORD_RE.findall(line)
    if not words:
        return 0
    stop = len(EN_STOP.findall(line))
    return stop + (1 if stop and len(words) > 5 else 0)


def main() -> int:
    files = sorted(I18N.glob("README*.md"))
    if not files:
        print("No i18n README files found.")
        return 1

    for path in files:
        if path.name in SKIP:
            continue
        offenders: list[tuple[int, int, str]] = []
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            score = score_line(line)
            if score >= 2:
                offenders.append((score, idx, line.strip()))

        print(f"\n[{path.relative_to(ROOT)}] potential English-heavy lines: {len(offenders)}")
        for score, idx, line in offenders[:12]:
            print(f"  L{idx:>3} (score {score}): {line[:120]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
