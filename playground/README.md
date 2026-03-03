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
- `GET /api/suggestions`
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


## Windows Docker + Android completion path

- **Windows Docker:**
  - install Docker Desktop
  - run: `docker compose up --build tpm-forge-web`
  - open: `http://localhost:8787`
- **Android (Termux):**
  - full setup + clone:
    - `pkg update -y && pkg upgrade -y`
    - `pkg install -y git python curl termux-api`
    - `git clone https://github.com/IrsanAI/TPM-Agent.git && cd TPM-Agent`
    - `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`
  - start local web runtime:
    - `bash scripts/termux_forge.sh start`
  - stop later:
    - `bash scripts/termux_forge.sh stop`

### Dynamic market onboarding behavior

- UI now proposes suggested markets per available source (binance/kraken/alphavantage).
- Suggestions include markets observed/active in runtime.
- If a market is not available from built-in sources, user must provide explicit URL and credentials (`api_key` where required).



### Android Termux service control

```bash
bash scripts/termux_forge.sh start
bash scripts/termux_forge.sh status
bash scripts/termux_forge.sh stop
```

State remains in `state/` (agent overrides, runtime cache) for restart continuity.
Web dashboard provides start/stop controls and a progress bar for transition status.
