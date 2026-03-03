#!/usr/bin/env python3
"""Basic README sanity checks for accidental copy/paste artifacts.

Checks:
- consecutive duplicate non-empty lines
- duplicate section headers appearing directly one after another
- duplicate numbered list labels directly one after another (e.g. '1) ...')
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "README.md", ROOT / "README.de.md", ROOT / "playground" / "README.md", *sorted((ROOT / "docs" / "i18n").glob("README.*.md"))]

NUM_RE = re.compile(r"^\d+\)\s+")


def main() -> int:
    issues = 0
    for path in FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        for i in range(1, len(lines)):
            prev = lines[i - 1].strip()
            cur = lines[i].strip()
            if not prev or not cur:
                continue
            if prev == cur:
                print(f"{path.relative_to(ROOT)}:{i+1}: duplicate consecutive line -> {cur}")
                issues += 1
            if prev.startswith("##") and cur.startswith("##") and prev == cur:
                print(f"{path.relative_to(ROOT)}:{i+1}: duplicate heading")
                issues += 1
            if NUM_RE.match(prev) and NUM_RE.match(cur) and prev == cur:
                print(f"{path.relative_to(ROOT)}:{i+1}: duplicate numbered item")
                issues += 1

    if issues == 0:
        print("README sanity check passed: no duplicate consecutive lines detected.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
