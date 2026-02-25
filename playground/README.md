# TPM Playground + Forge Runtime UI

## 1) Playground (simulation onboarding)

A lightweight browser playground to explore TPM concepts interactively:
- single-agent weak-signal anomaly detection
- mini swarm consensus pressure
- cross-domain transfer resonance (synthetic)

Run:

```bash
python -m http.server 8765
# open http://localhost:8765/playground/index.html
```

## 2) Forge Runtime UI (production-like finance start)

The production web runtime starts finance with BTC + COFFEE by default and supports adding agents via web API/UI.

Run:

```bash
uvicorn production.forge_runtime:app --host 0.0.0.0 --port 8787
# open http://localhost:8787
```

API:
- `GET /api/frame`
- `GET /api/agents`
- `POST /api/agents`
- `POST /api/tick`

## Scope

Runtime is designed for immersive operations visibility and iterative agent expansion.
It is not an order execution engine.


## Windows dependencies (easy install)

- Python 3.10+
- pip (bundled with Python)
- Optional: Docker Desktop (for click-start fallback)

Fast path:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/tpm_cli.py forge-dashboard --open-browser --port 8787
```

Click-start path:

```text
scripts/windows_click_start.bat
```

