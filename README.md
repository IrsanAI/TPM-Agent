# IrsanAI TPM Agent Forge (Bootstrap)

Dieses Repository ist ein sauberer Neustart für dein autonomes Multi-Agent-Setup (BTC, COFFEE, später weitere Märkte).

## Was enthalten ist

- `production/preflight_manager.py` – robustes Source-Probing mit TradingView-Fallback für COFFEE.
- `production/tpm_agent_process.py` – einfacher Agent-Prozess pro Markt, der zyklisch Daten sammelt.
- `scripts/start_agents.sh` – startet Agenten sauber in `tmux` Sessions.
- `scripts/health_monitor_v3.sh` – Single-Instance Health-Monitor mit Lockfile, Cooldown und Eskalation.
- `core/init_db_v2.py` – idempotente DB-Initialisierung + sichere Schema-Migration.
- `core/scout.py` – Fitness-Scoring Dashboard für aktive Agenten.
- `core/reserve_manager.py` – Reserve-Bank für neue Agenten (VALIDATE → ACTIVATE).

## Quickstart

```bash
python core/init_db_v2.py
chmod +x scripts/start_agents.sh scripts/health_monitor_v3.sh
bash scripts/start_agents.sh BTC
bash scripts/start_agents.sh COFFEE
tmux new-session -d -s irsan_supervisor "bash -lc './scripts/health_monitor_v3.sh >> ./logs/health_v3.log 2>&1'"
python core/scout.py
python core/reserve_manager.py dashboard
```

## Architekturidee (kompakt)

1. **TPM Agents** liefern kontinuierlich Rohdaten in `price_history`.
2. **Health Monitor** hält Agents am Leben und protokolliert Metriken/Events.
3. **Scout** bewertet Agent-Fitness (Latenz, Freshness, Aktivität).
4. **Reserve Manager** lässt neue Märkte erst nach Validierung ins „Spielfeld".

## Nächste Ausbaustufen

- Transfer-Entropy Modul für Kausalitätsanalyse zwischen Märkten.
- Optimizer mit Policy-Updates auf Basis historischer Performance.
- Alerting (Telegram/Signal) + Boot-Persistenz.
