
import json
from pathlib import Path
import re

def update_readme_translations(repo_root: Path):
    master_json_path = repo_root / "i18n_master.json"
    if not master_json_path.exists():
        print(f"Error: {master_json_path} not found. Please run create_i18n_master.py first.")
        return

    with open(master_json_path, "r", encoding="utf-8") as f:
        i18n_data = json.load(f)

    # Lade die englische README als Referenz
    en_readme_path = repo_root / "README.md"
    if not en_readme_path.exists():
        print(f"Error: {en_readme_path} not found.")
        return
    en_lines = en_readme_path.read_text(encoding="utf-8").splitlines()

    # Liste der zu aktualisierenden README-Dateien
    target_readmes = [
        repo_root / "README.de.md",
    ]
    for file in (repo_root / "docs" / "i18n").glob("README.*.md"):
        target_readmes.append(file)

    for target_path in target_readmes:
        lang_code = target_path.stem.split(".")[-1] if "." in target_path.stem else target_path.stem.split("_")[-1]
        if lang_code == "README": # Should not happen with the current glob, but as a safeguard
            continue
        
        print(f"Updating {target_path} for language {lang_code}...")
        
        translated_lines = []
        for line in en_lines:
            # Handle the language header separately
            if re.match(r'^\[🇬🇧 English\].*', line):
                translated_lines.append(f'[🇬🇧 English](./README.md) | [{lang_code.upper()} {lang_code.capitalize()}](./{target_path.relative_to(repo_root)}) |')
            else:
                # Check if the exact line exists as a key in i18n_data
                if line in i18n_data and lang_code in i18n_data[line] and i18n_data[line][lang_code]:
                    translated_lines.append(i18n_data[line][lang_code])
                else:
                    # If not found or no translation, keep the original English line
                    translated_lines.append(line)

        # Schreibe den aktualisierten Inhalt zurück
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("\n".join(translated_lines))
        print(f"Finished updating {target_path}.")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    update_readme_translations(repo_root)
