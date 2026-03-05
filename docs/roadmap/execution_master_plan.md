# IrsanAI TPM – Master Execution Plan (Step-by-Step)

Dieses Dokument ist der **konkrete Abarbeitungsplan** für die nächsten Versionen.
Ziel: **Feature-Parität + verlässlicher Betrieb** auf Android/Termux und Docker/Windows,
parallel mit sauberem Ausbau für Linux, macOS und iPhone (Web-Client).

---

## 0) Aktueller Stand (Baseline)

### Bereits verfügbar
- Prediction Oracle mit Persistenz, Validation-Rounds, Reason-Codes und Confidence-Decomposition.
- Live-Monitor-Integration inkl. Snapshot-Datei für den Hub.
- Unified Web Hub (`/api/oracle`, `/api/update/status`, `/api/capabilities`).
- Update-Orchestrator + Update-Cockpit + Handover-Mechanik.
- Docker Compose Services für Web/Cockpit/Live + persistente Volumes.

### Noch offen (strategisch)
- Echte Lernschleife aus Misses (adaptive Kalibrierung pro Markt mit auditierbaren Regeln).
- Einheitliches Operations-Runbook pro Plattform (Boot, Restart, Recovery, Rollback).
- Linux/macOS Service-Templates.
- iPhone Web-Client-Produktisierung (PWA/Remote host profile).

---

## 1) Leitprinzipien für die nächsten Sprints

1. **Android/Termux und Docker zuerst** (Pflicht-Parität).
2. **Gleiche API-Verträge** auf allen Plattformen.
3. **Erst Stabilität, dann Features** (observability > gimmicks).
4. **Jeder Schritt messbar** (Smoke-Test + Abnahme-Kriterium).
5. **Rollback-fähig deployen** (niemals Update ohne Rückweg).

---

## 2) Roadmap in 6 Releases

## Release R1 – Runtime Stabilization (1–2 Wochen)

### Ziele
- Betriebssicherheit erhöhen, ohne API-Brüche.

### Tasks
- [ ] Health-Endpoints ergänzen (`/api/health`, `/api/ready`).
- [ ] Update-Orchestrator um Preflight-Guards erweitern (Diskspace, DB lock check, network reachability).
- [ ] Snapshot-Schreibpfad absichern (atomic write/rename).
- [ ] Einheitliche Fehlercodes im Web Hub (`error_code`, `error_detail`).

### Done-Kriterien
- [ ] 24h Soak-Test auf Termux ohne ungeplanten Prozessabbruch.
- [ ] 24h Soak-Test auf Docker mit Restart-Policy.

---

## Release R2 – Explainable Oracle v2 (1–2 Wochen)

### Ziele
- Vertrauen durch Erklärung: warum Prediction gut/schlecht ist.

### Tasks
- [ ] Reason-Code-Taxonomie finalisieren (enum + docs).
- [ ] Confidence-Decomposition versionieren (`confidence_schema_version`).
- [ ] ETA-Fenster verbessern (volatilitätsbasiert statt fixer Prozentregel).
- [ ] Replay-Snapshot pro Prediction-ID speichern (`state/replay/*.json`).

### Done-Kriterien
- [ ] UI zeigt pro Hop Grund + Confidence + Delta.
- [ ] Reproduzierbarer Replay für letzte 20 Predictions.

---

## Release R3 – Learning Loop & Calibration (2 Wochen)

### Ziele
- Misses aktiv in bessere Folgeprognosen überführen.

### Tasks
- [ ] Miss-Klassifikation (`timing_miss`, `volatility_miss`, `regime_flip`, `source_lag`).
- [ ] Markt-spezifische Kalibrierparameter einführen (`state/calibration/{market}.json`).
- [ ] Adaptive Toleranz + adaptive base_confidence mit Guardrails (min/max drift).
- [ ] Drift-Report im Hub anzeigen ("Model drift: low/medium/high").

### Done-Kriterien
- [ ] Über 3 Tage sinkende Miss-Rate in kontrolliertem Backfill-Szenario.
- [ ] Keine confidence-explosions > definierter Schwellwerte.

---

## Release R4 – Update UX & Ops Hardening (1 Woche)

### Ziele
- Update-Prozess „idiotensicher“ für Endnutzer.

### Tasks
- [ ] Cockpit mit Phase-Timestamps + geschätzter Restdauer.
- [ ] Backup-Verifikation nach Erstellung (checksum + restore probe).
- [ ] Optionaler Auto-Restart (cockpit -> hub) mit Konflikt-Detection auf Ports.
- [ ] "What's New" strukturieren: Breaking/Feature/Fix.

### Done-Kriterien
- [ ] Simulierter Fehler im Update führt zu sauberem Rollback.
- [ ] Nutzer kann nach Update in ≤2 Klicks wieder live gehen.

---

## Release R5 – Platform Expansion Pack (2 Wochen)

### Linux
- [ ] systemd Units (`tpm-web.service`, `tpm-live.service`, `tpm-cockpit.service`).
- [ ] `scripts/linux_install.sh` mit idempotentem Setup.

### macOS
- [ ] launchd plist templates + helper scripts.
- [ ] macOS spezifischer Runbook-Abschnitt (Pfadrechte, auto-start).

### iPhone (Web-Client)
- [ ] PWA manifest + install prompts.
- [ ] Remote-host profile dokumentieren (iPhone als UI, Backend auf Docker/Linux).
- [ ] Mobile-safe notification bridge (ohne Termux APIs).

### Done-Kriterien
- [ ] Linux/macOS One-command Start verifiziert.
- [ ] iPhone Home-Screen PWA lädt Hub zuverlässig.

---

## Release R6 – Production Readiness & Governance (1 Woche)

### Ziele
- Betriebsreife + klare Verantwortlichkeit.

### Tasks
- [ ] SLA/SLO definieren (Hub availability, update success rate, prediction freshness).
- [ ] Audit-Log für Updates, Calibration und Critical Actions.
- [ ] Security pass (secret handling, command execution boundaries, endpoint hardening).
- [ ] Finales cross-platform runbook veröffentlichen.

### Done-Kriterien
- [ ] Go/No-Go Checklist erfüllt.
- [ ] Rollback-Probe + Disaster-Recovery-Test bestanden.

---

## 3) Plattform-Parität (was überall gleich sein muss)

## Pflicht-Parität (Termux + Docker + Linux + macOS)
- `tpm_cli.py` Kernkommandos (`env`, `live`, `web`, `update`, `update-cockpit`).
- API-Verträge: `/api/oracle`, `/api/update/status`, `/api/capabilities`.
- Update-Orchestrierung inkl. Backup + Recovery.
- Oracle Snapshot Schema (inkl. Reason/Confidence/ETA-Fenster).

## Plattform-spezifisch erlaubt
- Termux: native Notifications/Vibration.
- Docker: erweiterte Restart-Policies, Rolling-Update-Optionen.
- iPhone: nur Web/PWA-Client, keine lokale Runtime.

---

## 4) Konkrete Abarbeitung (Sprint-Board ready)

## Sprint A (sofort starten)
- [ ] R1 Task 1–4
- [ ] R2 Task 1
- [ ] Abnahme: Smoke + 24h Soak (Termux + Docker)

## Sprint B
- [ ] R2 Task 2–4
- [ ] R3 Task 1–2
- [ ] Abnahme: Replay + Miss-Klassifikation sichtbar im UI

## Sprint C
- [ ] R3 Task 3–4
- [ ] R4 komplett
- [ ] Abnahme: Fehlerpfad-Update + Rollback erfolgreich

## Sprint D
- [ ] R5 komplett
- [ ] R6 Task 1–2

## Sprint E
- [ ] R6 Task 3–4
- [ ] Finale Plattformabnahme + Launch

---

## 5) Definition of Done pro Ticket

Ein Ticket gilt nur als „Done“, wenn:
1. Code + Doku aktualisiert sind.
2. Mindestens 1 automatischer Check dokumentiert ist.
3. Plattformauswirkung explizit benannt ist (Termux/Docker/Linux/macOS/iPhone).
4. Rollback-Auswirkung bewertet wurde.

---

## 6) Nächster sofortiger Schritt (Empfehlung)

**Jetzt direkt starten mit R1 Sprint A**:
1. Health/Ready Endpoints,
2. Update-Preflight-Guards,
3. atomischer Snapshot-Write,
4. einheitliche Fehlercodes im Hub.

Das bringt die größte Stabilitätsrendite für alle User – unabhängig von Plattform.
