
import json
from pathlib import Path
import re

def to_js_object_string(data: dict) -> str:
    """Converts a Python dictionary to a JavaScript object literal string."""
    def format_value(value):
        if isinstance(value, dict):
            return to_js_object_string(value)
        elif isinstance(value, str):
            # Escape backslashes and single quotes, then wrap in single quotes
            # Also escape newlines and tabs to be valid JS string literals
            return f"'" + value.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t").replace("\'", "\\'") + "'"
        elif isinstance(value, bool):
            return str(value).lower()
        elif value is None:
            return "null"
        else:
            return str(value)

    parts = []
    for key, value in data.items():
        # Keys in JS objects can be unquoted if they are valid identifiers
        # For simplicity, we'll assume they are valid identifiers here.
        # If keys can contain special characters, they should be quoted.
        formatted_key = key # Assuming keys are simple identifiers
        parts.append(f"{formatted_key}: {format_value(value)}")
    return "{" + ", ".join(parts) + "}"

def update_webui_locales(repo_root: Path):
    master_json_path = repo_root / "i18n_master.json"
    if not master_json_path.exists():
        print(f"Error: {master_json_path} not found. Please run create_i18n_master.py first.")
        return

    with open(master_json_path, "r", encoding="utf-8") as f:
        i18n_data = json.load(f)

    # Prepare the I18N object for JavaScript
    js_i18n_object = {}
    # Iterate through each English key in i18n_data
    for en_key, translations in i18n_data.items():
        for lang_code, translated_text in translations.items():
            if lang_code not in js_i18n_object:
                js_i18n_object[lang_code] = {}
            js_i18n_object[lang_code][en_key] = translated_text

    # Convert the Python dict to a JavaScript object literal string
    js_i18n_str = to_js_object_string(js_i18n_object)

    target_html_files = [
        repo_root / "playground" / "forge_dashboard.html",
        repo_root / "playground" / "index.html",
    ]

    for html_path in target_html_files:
        if not html_path.exists():
            print(f"Warning: {html_path} not found, skipping.")
            continue

        print(f"Updating I18N in {html_path}...")
        html_content = html_path.read_text(encoding="utf-8")

        # Escape backslashes in js_i18n_str for re.sub to treat them as literals
        # This is crucial because re.sub interprets backslashes in the replacement string as escape sequences.
        escaped_js_i18n_str = js_i18n_str.replace('\\', '\\\\')

        # Find the I18N block and replace it
        updated_html_content = re.sub(
            r"(const I18N = )({.*?})(;)",
            f"\1{escaped_js_i18n_str}\3",
            html_content,
            flags=re.DOTALL
        )

        if updated_html_content != html_content:
            html_path.write_text(updated_html_content, encoding="utf-8")
            print(f"Successfully updated {html_path}.")
        else:
            print(f"No changes needed for {html_path}.")

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    update_webui_locales(repo_root)
