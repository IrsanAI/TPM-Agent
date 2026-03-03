
import json
from pathlib import Path
import re
import sys
import subprocess

def extract_i18n_from_html(html_content: str) -> dict:
    """Extracts the I18N JavaScript object from HTML content and parses it using Node.js."""
    i18n_data = {}
    match = re.search(r"const I18N = ({.*?});", html_content, re.DOTALL)
    if not match:
        return {}

    js_object_str = match.group(1)

    # Create a temporary JavaScript file to parse the object
    js_script_content = f"""
        const I18N = {js_object_str};
        console.log(JSON.stringify(I18N));
    """
    temp_js_path = Path("/tmp/extract_i18n.js")
    temp_js_path.write_text(js_script_content, encoding="utf-8")

    try:
        # Execute the JavaScript file using Node.js
        result = subprocess.run(
            ["node", str(temp_js_path)],
            capture_output=True, text=True, check=True, encoding="utf-8"
        )
        json_output = result.stdout.strip()
        
        # Parse the JSON output
        parsed_i18n = json.loads(json_output)
        
        for lang_code, translations in parsed_i18n.items():
            if isinstance(translations, dict):
                for key, value in translations.items():
                    if key not in i18n_data:
                        i18n_data[key] = {}
                    i18n_data[key][lang_code] = value
            else:
                print(f"Warning: Expected dictionary for language {lang_code}, got {type(translations)}")

    except subprocess.CalledProcessError as e:
        print(f"Error executing Node.js script: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output from Node.js: {e}")
        print(f"Problematic JSON output: {json_output[max(0, e.pos-100):e.pos+100]}")
    finally:
        temp_js_path.unlink(missing_ok=True) # Clean up the temporary file

    return i18n_data

def create_i18n_master(repo_root: Path):
    """Creates a master i18n JSON file from various sources."""
    master_json_path = repo_root / "i18n_master.json"
    en_readme_path = repo_root / "README.md"
    forge_dashboard_path = repo_root / "playground" / "forge_dashboard.html"
    index_html_path = repo_root / "playground" / "index.html"
    
    i18n_data = {}

    # Lade vorhandene Übersetzungen aus i18n_localize.py COMMON
    try:
        sys.path.append(str(repo_root / "scripts"))
        from i18n_localize import COMMON
        for en_key, translations in COMMON.items():
            i18n_data[en_key] = {"en": en_key}
            for lang, translated_text in translations.items():
                i18n_data[en_key][lang] = translated_text
    except ImportError:
        print("Could not import i18n_localize.py. Proceeding without its COMMON data.")

    # Extrahiere Strings aus README.md
    if en_readme_path.exists():
        readme_content = en_readme_path.read_text(encoding="utf-8")
        for line in readme_content.splitlines():
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith("#") or stripped_line.startswith("```") or re.match(r"^[🇬🇧 English].*", stripped_line):
                continue
            
            clean_line = re.sub(r"\*\*([^\*]+?)\*\*", r"\1", stripped_line) # Remove bold markdown
            clean_line = re.sub(r"`([^`]+?)`", r"\1", clean_line) # Remove inline code markdown
            clean_line = re.sub(r"^- ", "", clean_line) # Remove list item markdown
            clean_line = re.sub(r"^> ", "", clean_line) # Remove blockquote markdown
            clean_line = re.sub(r"^\|\s*(.*?)\s*\|.*", r"\1", clean_line) # Extract first column from table
            clean_line = clean_line.strip()

            if clean_line and clean_line not in i18n_data:
                i18n_data[clean_line] = {"en": clean_line}
                for lang_code in ["de", "es", "it", "fr", "pt-BR", "ru", "zh-CN", "hi", "ja", "tr", "bs"]:
                    if lang_code not in i18n_data[clean_line]:
                        i18n_data[clean_line][lang_code] = ""

    # Extrahiere Strings aus forge_dashboard.html
    if forge_dashboard_path.exists():
        html_content = forge_dashboard_path.read_text(encoding="utf-8")
        extracted_html_i18n = extract_i18n_from_html(html_content)
        for key, translations in extracted_html_i18n.items():
            if key not in i18n_data:
                i18n_data[key] = {"en": key}
            for lang, value in translations.items():
                i18n_data[key][lang] = value # Overwrite or add translations

    # Extrahiere Strings aus index.html
    if index_html_path.exists():
        html_content = index_html_path.read_text(encoding="utf-8")
        extracted_html_i18n = extract_i18n_from_html(html_content)
        for key, translations in extracted_html_i18n.items():
            if key not in i18n_data:
                i18n_data[key] = {"en": key}
            for lang, value in translations.items():
                i18n_data[key][lang] = value # Overwrite or add translations

    # Speichere die Master-JSON
    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(i18n_data, f, ensure_ascii=False, indent=2)

    print(f"i18n_master.json created/updated at {master_json_path}")

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    create_i18n_master(repo_root)
