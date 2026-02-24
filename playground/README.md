# TPM Playground + Forge Runtime UI

## 1) Playground (simulation onboarding)

## 1) Playground (simulation onboarding)

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
