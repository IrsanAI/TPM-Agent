# GitHub PR Konflikte lösen – Merge-Checkliste (praktisch)

## Mini-Merksatz für die Zukunft

> # current = dein PR
> # incoming = main
> # both = zusammenführen + prüfen
>
> **Und ganz wichtig: „rot" heißt nicht automatisch löschen, sondern nur „hier kollidieren zwei Änderungen".**

## Was bedeuten die 3 Buttons im GitHub-Konflikteditor?

- **Accept current change** → nimm nur den oberen Block (dein PR-Branch).
- **Accept incoming change** → nimm nur den unteren Block (Zielbranch, meist `main`).
- **Accept both changes** → nimm beide Blöcke, dann manuell aufräumen (Reihenfolge, Duplikate, Widersprüche).

## 7-Schritte-Checkliste pro Konfliktblock

1. **Kontext lesen**: Welche Überschrift/Section ist das? (z. B. Runtime, Windows, LOP)
2. **Fachziel klären**: Welche Version passt zum aktuellen Produktziel?
3. **Current prüfen**: Bringt dein PR neue, beabsichtigte Inhalte?
4. **Incoming prüfen**: Enthält `main` parallel sinnvolle Ergänzungen?
5. **Entscheiden**:
   - nur PR-Inhalt korrekt → **Accept current**
   - nur Main-Inhalt korrekt → **Accept incoming**
   - beide wichtig → **Accept both** + manuelles Bereinigen
6. **Marker entfernen**: `<<<<<<<`, `=======`, `>>>>>>>` dürfen nicht bleiben.
7. **Finaler Smoke-Check**: Datei lesen, Links/Codeblöcke/Überschriften prüfen.

## Schnellregeln (80/20)

- **Doku-Block nur ergänzt, main hat nichts Neues** → meist **current**.
- **Beide haben neue Zeilen in derselben Section** → meist **both** + cleanup.
- **Main ist klar neuer/korrekter, PR veraltet** → **incoming**.

## Live-Beispiel (aus `docs/i18n/README.bs.md`)

Konflikt zwischen:
- PR-Block: `### Windows two-path quick access (synchronized)`
- Main-Block: direkter Sprung zu `## TPM Playground`

Richtige Entscheidung in diesem Fall:
- **Accept current change**, weil der Windows-2-Wege-Block eine gezielte neue Nutzerführung ergänzt.
- Danach prüfen, dass `## TPM Playground` direkt darunter weiterhin sauber folgt.

## Häufige Fehler vermeiden

- Nicht reflexartig auf **current** klicken, nur weil der Bereich rot markiert ist.
- Nicht reflexartig **both** klicken, ohne Duplikate danach zu bereinigen.
- Keine Konfliktmarker im finalen Commit lassen.

## Teamregel (empfohlen)

Wenn EN/DE als kanonisch definiert sind, gilt bei i18n-Konflikten:
- Inhaltlich am EN/DE-Stand ausrichten,
- lokale Übersetzungen ergänzen,
- strukturelle Abschnitte synchron halten (Runtime/Windows/LOP).
