
import subprocess
from pathlib import Path
import sys

def run_script(script_name: str, repo_root: Path):
    script_path = repo_root / "scripts" / script_name
    print(f"Running {script_name}...")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, check=True, encoding="utf-8"
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}:")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)

def main():
    repo_root = Path(__file__).resolve().parents[1]
    
    # 1. Create/Update the master i18n JSON from all sources
    run_script("create_i18n_master.py", repo_root)
    
    # 2. Update all README files based on the master JSON
    run_script("update_readme_translations.py", repo_root)
    
    # 3. Update all WebUI HTML files based on the master JSON
    run_script("update_webui_locales.py", repo_root)
    
    print("All i18n synchronizations completed successfully.")

if __name__ == "__main__":
    main()
