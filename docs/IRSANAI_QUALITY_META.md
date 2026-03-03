# IrsanAI TPM-Agent – Qualitäts- und Anspruchs-Meta (SOLL vs IST)

Dieses Dokument übersetzt die in den letzten Iterationen sichtbare IrsanAI-Anforderung in ein belastbares Engineering- und Produkt-Qualitätsmodell.

## 1) Muster aus der Zusammenarbeit (Meta-kognitiver Qualitätsrahmen)

Aus der Kommunikation lassen sich stabile Qualitätsmuster ableiten:

1. **Zero-Guess-Onboarding**: Nutzer wollen klare Step-1/2/3-Flows ohne Interpretationsspielraum.
2. **Sofort sichtbarer Nutzen**: Nach Start muss ein klarer, visueller „Aha“-Moment erscheinen (nicht nur CLI-Logs).
3. **Cross-Platform-Parität**: Docker/Windows/Android müssen funktional gleich wirken (UI/UX und Kernfunktionen).
4. **Live-Transparenz statt Blackbox**: Marktdaten, Agentenleistung und Zustandswechsel müssen live sichtbar sein.
5. **Professioneller Eindruck**: Keine Flüchtigkeitsfehler, keine unklaren Begriffe, konsistente Terminologie.
6. **Skalierbarkeit über Finance hinaus**: Architektur und UI sollen für weitere Branchen ausrollbar sein.

## 2) SOLL vs IST (Zwischenstand)

| Bereich | SOLL | IST | Gap | Priorität |
|---|---|---|---|---|
| Onboarding (Docker/Android) | deterministischer Start inkl. Troubleshooting | Step-by-step vorhanden, localhost/0.0.0.0 erklärt | Android-Runbook noch tiefer operationalisierbar (Recovery, Hotspot/LAN) | Hoch |
| Live-Cockpit | Hauptcockpit mit Live-Markt/Agent-Einsichten | Live Market Cockpit + Agent Drilldown vorhanden | Echtzeit-Streaming aktuell polling-basiert | Hoch |
| Per-Agent Immersion | dedizierte Agent-Ansichten je Fokus | Modal-Insight pro Market/Agent vorhanden | separate Agent-Pages mit Rollenlayout fehlen | Hoch |
| Sprachintegration | alle Repo-Sprachen im Web nutzbar | Locale-Discovery + Selector + Doku-Link vorhanden | UI-Texte nur teilweise lokalisiert (EN/DE vollständig) | Mittel |
| Betriebsstabilität | robuste Defaults + Selbstheilung | Preflight DB-Bootstrap gefixt, Runtime-Control vorhanden | Health/Auto-Recover im Webbetrieb ausbaufähig | Hoch |
| Multi-Domain-Rollout | modulare Branchen-Templates | Finance-first umgesetzt, Struktur vorhanden | Domain-Kits (energy/health/industry) fehlen | Mittel |

## 3) Produkt-Roadmap (kausal aus SOLL/IST abgeleitet)

### P0 – UX/Betrieb sofort
- Websocket- oder SSE-Push für Live-Cockpit (statt reinem Polling).
- „Runtime Health Panel" (API-Latenz, letzte erfolgreiche Ticks, Source-Failrate).
- Persistente UI-Preferences (Sprache, bevorzugte Märkte, Layout).

### P1 – Agent-Immersion
- `/agent/<name>` Deep-Dive-Views mit:
  - Preis-/Fitness-/Reward-Timeline,
  - Source-Qualität/Fehlerquote,
  - Entscheidungen/Anomalie-Events.
- Rollenbasierte Oberflächen (`trader`, `ops`, `research`, `exec`).

### P2 – Android/Termux Operational Excellence
- „One-command demo mode" mit automatischem Warmup + URL-Ausgabe.
- Recovery-Kommandos (Port belegt, App im Hintergrund beendet, Cache reset).
- Mobile-first Touch UX (größere Hit-Areas, Low-bandwidth Mode).

### P3 – Multi-Domain Expansion
- Domain Packs (z. B. Energie, Gesundheit, Produktion, Logistik).
- Pro Domain: Datenadapter, Agenten-Templates, UI-Theme, KPI-Kacheln.
- Gemeinsame Governance-Regeln (vergleichbar mit Finance-Setup).

## 4) IrsanAI Quality-Gates für künftige PRs

Jede PR soll diese Gates sichtbar erfüllen:

1. **Run Gate**: documented Step-Flow funktioniert auf mind. 1 Local + 1 Container path.
2. **Visibility Gate**: UI zeigt nach Start unmittelbar Live-Zustand (kein leeres Gefühl).
3. **Parity Gate**: Feature ist in Docker und Android äquivalent nutzbar oder klar begrenzt dokumentiert.
4. **Clarity Gate**: README sanity + keine widersprüchlichen Startanweisungen.
5. **Evidence Gate**: Smoke-Checks inkl. API-Endpunkte und (bei UI-Änderung) Screenshot.

## 5) Definition of Done (DoD) – IrsanAI Premium

Ein Feature gilt erst als „IrsanAI-ready“, wenn:
- es **sichtbar** ist (UI-Effekt),
- **nutzbar** ist (klare Schritte),
- **stabil** ist (Fehlerpfade abgefangen),
- **portabel** ist (Docker + Android berücksichtigt),
- und **erklärbar** ist (README + kurze Troubleshooting-Hinweise).
