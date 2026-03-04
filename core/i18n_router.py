"""Simple locale-aware content path resolver for repository docs.

This module centralizes locale fallback logic so callers can resolve
language-specific documentation paths recursively (if localized files exist)
without hardcoding per-language branches.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPPORTED = {"de", "en", "es", "it", "bs", "ru", "zh-CN", "fr", "pt-BR", "hi", "ja"}
DEFAULT_LOCALE = "en"


@dataclass(frozen=True)
class LocaleContext:
    locale: str = DEFAULT_LOCALE

    @property
    def normalized(self) -> str:
        return self.locale if self.locale in SUPPORTED else DEFAULT_LOCALE


def resolve_readme(locale: str) -> Path:
    """Return the best README path for a locale with deterministic fallback."""
    loc = LocaleContext(locale).normalized
    root = Path(__file__).resolve().parents[1]
    if loc == "en":
        return root / "README.md"
    if loc == "de":
        return root / "README.de.md"

    candidate = root / "docs" / "i18n" / f"README.{loc}.md"
    return candidate if candidate.exists() else root / "README.md"


def localized_variant(path: Path, locale: str) -> Path:
    """Resolve a localized sibling variant if available, else return input path.

    Example: docs/guide.md + locale=es -> docs/i18n/guide.es.md (if present).
    """
    loc = LocaleContext(locale).normalized
    root = Path(__file__).resolve().parents[1]
    rel = path.resolve().relative_to(root)
    stem = rel.stem
    suffix = rel.suffix

    candidate = root / rel.parent / "i18n" / f"{stem}.{loc}{suffix}"
    return candidate if candidate.exists() else path
