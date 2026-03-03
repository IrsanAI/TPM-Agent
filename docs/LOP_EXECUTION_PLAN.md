# LOP Execution Plan (Integration-to-Done)

This plan operationalizes the current open LOP items into concrete deliverables, acceptance criteria, and "Done" conditions.

## Scope

Source open points are listed in:
- `README.md` → "Hinweis für Entwickler (LOP – Liste offener Punkte)"
- `README.de.md` → same section.

## Execution model

Each item moves through:
1. **Spec** (rules and data contract defined)
2. **Build** (code + config + docs + UI)
3. **Evidence** (tests, smoke checks, artifacts)
4. **Done** (acceptance criteria met and status flipped)

---

## 1) Alerting (Telegram/Signal)

### Integration plan
- Add `alerts/policies.yaml` with severity matrix (`info/warn/critical`) and route map.
- Add alert event schema (`event_type`, `agent`, `market`, `severity`, `context`).
- Add rate limiting + dedup window to avoid alert storms.

### Done criteria
- Alert policy file in repo and loaded by runtime.
- At least 3 event types covered (runtime stop, source outage, anomaly spike).
- End-to-end smoke command documented and tested.

### Evidence
- Unit test for policy matching.
- Runtime smoke log showing one alert per severity.

---

## 2) Boot-Persistenz / Dauerbetrieb

### Integration plan
- Provide platform runbooks:
  - Docker: restart policy + healthcheck + volume persistence.
  - Linux: systemd service template.
  - Termux: boot trigger + watchdog command set.
- Add `scripts/runtime_healthcheck.sh` with non-zero exit on degraded runtime.

### Done criteria
- Reboot-survival tested on Docker and one mobile profile.
- Recovery guide from crash to healthy state in <= 5 commands.

### Evidence
- `docker compose` profile with `restart: unless-stopped` + healthcheck.
- Runbook doc with verified command transcripts.

---

## 3) Koordiniertes Meta-Layer (Regime policy)

### Integration plan
- Introduce explicit regime detector (`trend`, `shock`, `sideways`) from rolling statistics.
- Add policy map from regime → weight multipliers / cull thresholds.
- Surface active regime in `/api/frame` and dashboard pill.

### Done criteria
- Regime transitions visible in runtime payload and UI.
- Policy impact measurable (weight changes logged per tick).

### Evidence
- Integration test with synthetic regime sequence.
- Screenshot/log excerpt of regime change and policy application.

---

## 4) Collective Memory

### Integration plan
- Define memory record schema (`pattern_id`, `domain`, `trigger_signature`, `outcome`, `confidence`, `version`).
- Add `state/collective_memory.jsonl` append-only store.
- Add review flow: candidate → approved → deprecated.

### Done criteria
- Memory writes triggered by configurable event conditions.
- Versioned read API available and documented.

### Evidence
- Schema doc + validation test.
- Sample records committed under fixture folder.

---

## 5) Reflexive Governance (safe mode)

### Integration plan
- Define uncertainty index from missing data ratio, volatility spikes, source disagreement.
- Hard thresholds to auto-switch runtime to conservative mode.
- UI state banner + manual override endpoint.

### Done criteria
- Deterministic switch conditions implemented and tested.
- Runtime emits explicit governance mode in status endpoint.

### Evidence
- Test case proving auto-enter/auto-exit safe mode.
- Dashboard indicator visible in screenshot.

---

## 6) Domain expansion beyond Finance/Weather

### Integration plan
- Deliver one pilot domain pack (recommended: **Energy**).
- Add domain-specific agent templates, source contracts, UI cards, and KPI panel.
- Add onboarding path to enable/disable domain pack.

### Done criteria
- New domain runs in Forge with at least 2 agents and visible domain summary.
- Domain documentation + sample config included.

### Evidence
- Config snippet, runtime frame sample, and dashboard screenshot.

---

## 7) Real-data scientific evidence

### Integration plan
- Add benchmark harness on real datasets with fixed acceptance gates:
  - precision, recall, false-positive rate, drift tolerance.
- Save run artifacts under `state/benchmarks/`.

### Done criteria
- Benchmark command produces reproducible report with pass/fail thresholds.
- Results referenced in README validation section.

### Evidence
- Benchmark JSON + markdown report checked in (or generated in CI artifact docs).

---

## 8) i18n synchronization process

### Integration plan
- Add source-of-truth sections list for EN/DE canonical docs.
- Add `scripts/i18n_sync_check.py` for missing-section detection across locale files.
- Add PR checklist item requiring i18n sync status.

### Done criteria
- Script runs in CI/preflight and fails on missing required sections.
- i18n update workflow documented in contribution guide.

### Evidence
- Sync check output and sample failure message documented.

---

## Recommended rollout order

1. Boot-Persistenz + Reflexive Governance (operational risk reduction first)
2. Regime policy + Alerting (control loop maturity)
3. Collective Memory + Real-data benchmarks (learning + evidence)
4. Domain expansion + i18n automation (scale-out)

## Status update policy

Only flip an item from `Offen 🔴/Teilweise erledigt 🟡` to `Erledigt ✅` when:
- code exists,
- docs and runbook exist,
- acceptance evidence is attached (test/log/screenshot),
- and rollout impact is validated on desktop + Docker + Android parity where applicable.
