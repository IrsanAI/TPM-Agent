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


## Wissenschaftliche Validierung (B + D in 2in1)

Das Repo enthält jetzt ein kombiniertes Backtest+Statistik-Framework:

```bash
python core/tpm_scientific_validation.py
```

Output-Artefakte:
- `state/TPM_Scientific_Report.md`
- `state/TPM_test_results.json`

Damit prüfst du in einem Lauf Klassifikation, Lead-Time, Alpha-Separation, False-Positive-Rate und eine Sharpe-Proxy-Strategie.

Optional kannst du Parameter variieren, z.B.:
```bash
python core/tpm_scientific_validation.py --ticks 12000 --window-size 20 --percentile 98
```

Die Validierung enthält eine robuste Chi²-Auswertung mit Zero-Cell-Guards, damit keine Abstürze bei leeren Kontingenzfeldern auftreten.


## Live-Monitor (BTC, Kraken)

Für Termux/Server gibt es jetzt einen Live-Monitor mit optionalem CSV-Warmstart, damit Alpha nicht erst nach vielen Stunden anspringt:

```bash
python production/tpm_live_monitor.py --history-csv btc_real_24h.csv --poll-seconds 3600
# Termux Benachrichtigung aktivieren:
python production/tpm_live_monitor.py --history-csv btc_real_24h.csv --poll-seconds 3600 --notify --vibrate-ms 1000
```

Nützliche Optionen:
- `--poll-seconds 60` für schnellen Testmodus
- `--window-size`, `--percentile`, `--safety-floor` für Kalibrierung
- `--min-alpha-delta` und `--cooldown` gegen Alert-Cluster/Spam
- `--notify` + `--vibrate-ms` für Toast/Vibration (Termux API)


## Datenquellen & Failover

`production/preflight_manager.py` nutzt für COFFEE standardmäßig Alpha Vantage (wenn `ALPHAVANTAGE_KEY` gesetzt ist) plus TradingView/Yahoo als Fallback und Cache-Backup in `state/latest_prices.json`.

```bash
export ALPHAVANTAGE_KEY="<dein_key>"
python production/preflight_manager.py
```

Stress-/Failover-Test (simulierter AlphaVantage-Ausfall, Ziel p95 < 1000ms):

```bash
python scripts/stress_test_suite.py
```

Output: `state/stress_test_report.json`


## Universal Quickstart (Termux, iPhone, Windows, Linux, Docker)

Empfohlener Einstieg für alle Plattformen ist der einheitliche Launcher:

```bash
python scripts/tpm_cli.py env
python scripts/tpm_cli.py validate
python scripts/tpm_cli.py preflight --market ALL
python scripts/tpm_cli.py live --history-csv btc_real_24h.csv --poll-seconds 3600
```

### Plattform-Hinweise
- **Android/Termux (Samsung etc.)**: `--notify` unterstützt Toast + Vibration via `termux-api`.
  ```bash
  pkg install termux-api -y
  python scripts/tpm_cli.py live --history-csv btc_real_24h.csv --notify --vibrate-ms 1000
  ```
- **iPhone (im Rahmen des Möglichen)**: nutze Shell-Umgebungen wie iSH/a-Shell; Notification-Hardwarehooks aus Termux sind dort nicht verfügbar.
- **Windows/Linux/macOS**: gleiche CLI-Befehle; optional in `tmux`/Task Scheduler/cron dauerhaft betreiben.

### Docker (einfachster Cross-OS Weg)

```bash
docker compose run --rm tpm-preflight
docker compose run --rm tpm-live
```

Optional mit Coffee-Key:
```bash
export ALPHAVANTAGE_KEY="<dein_key>"
docker compose run --rm tpm-preflight
```
