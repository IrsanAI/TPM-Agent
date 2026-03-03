#!/usr/bin/env python3
"""Mirror README.md into all docs/i18n/README.*.md files for full parity.

Use this when strict cross-language content parity is prioritized over partial translations.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON = (ROOT / "README.md").read_text(encoding="utf-8")
I18N_DIR = ROOT / "docs" / "i18n"

for file in sorted(I18N_DIR.glob("README.*.md")):
    code = file.stem.split(".", 1)[1]
    header = (
        f"# TPM-Agent ({code}) — Full Canonical Mirror\n\n"
        "> This localized file is maintained in full parity with `README.md` to avoid content gaps across languages.\n"
        "> Automatic mirror mode ensures all sections, mermaid diagrams, commands and runbooks are identical in scope.\n\n"
    )
    file.write_text(header + CANON, encoding="utf-8")
    print(f"synced {file.relative_to(ROOT)}")
