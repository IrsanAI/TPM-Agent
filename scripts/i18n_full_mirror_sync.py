#!/usr/bin/env python3
"""Safeguarded i18n parity helper.

This script no longer force-overwrites localized files with English content.
It validates mirror structure and can optionally refresh only language navigation links.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = ROOT / "docs" / "i18n"

LANG_NAV = (
    "[🇬🇧 English](../../README.md) | [🇩🇪 Deutsch](../../README.de.md) | "
    "[🇪🇸 Español](./README.es.md) | [🇮🇹 Italiano](./README.it.md) | "
    "[🇧🇦 Bosanski](./README.bs.md) | [🇷🇺 Русский](./README.ru.md) | "
    "[🇨🇳 中文](./README.zh-CN.md) | [🇫🇷 Français](./README.fr.md) | "
    "[🇧🇷 Português (BR)](./README.pt-BR.md) | [🇮🇳 हिन्दी](./README.hi.md) | "
    "[🇹🇷 Türkçe](./README.tr.md) | [🇯🇵 日本語](./README.ja.md)"
)


def sync_nav_only() -> None:
    for file in sorted(I18N_DIR.glob("README.*.md")):
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) < 3:
            continue
        replaced = False
        for idx, line in enumerate(lines[:12]):
            if line.startswith("[🇬🇧 English]"):
                lines[idx] = LANG_NAV
                replaced = True
                break
        if replaced:
            file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"updated nav {file.relative_to(ROOT)}")
        else:
            print(f"warning: nav marker not found in {file.relative_to(ROOT)}")


def audit_only() -> int:
    issues = 0
    for file in sorted(I18N_DIR.glob("README.*.md")):
        text = file.read_text(encoding="utf-8")
        if "./docs/i18n/README." in text:
            print(f"issue: broken nested i18n links in {file.relative_to(ROOT)}")
            issues += 1
    if issues == 0:
        print("i18n audit OK: no nested docs/i18n link issues found.")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync-nav", action="store_true", help="Update only language-nav lines in i18n README files")
    args = parser.parse_args()

    issues = audit_only()
    if args.sync_nav:
        sync_nav_only()
    else:
        print("No content overwritten. Use --sync-nav to normalize nav links only.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
