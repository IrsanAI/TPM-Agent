# IrsanAI TPM Agent Forge

[🇬🇧 English](../../README.md) | [🇩🇪 Deutsch](../../README.de.md) | [🇪🇸 Español](./README.es.md) | [🇮🇹 Italiano](./README.it.md) | [🇧🇦 Bosanski](./README.bs.md) | [🇷🇺 Русский](./README.ru.md) | [🇨🇳 中文](./README.zh-CN.md) | [🇫🇷 Français](./README.fr.md) | [🇧🇷 Português (BR)](./README.pt-BR.md) | [🇮🇳 हिन्दी](./README.hi.md) | [🇹🇷 Türkçe](./README.tr.md) | [🇯🇵 日本語](./README.ja.md)

Bu sayfa, TPM Forge için Türkçe giriş ve senkronizasyon landing page'idir.
Detaylı teknik içeriğin kanonik sürümleri İngilizce ve Almanca README dosyalarıdır.

## Hızlı Başlangıç

```bash
python scripts/tpm_cli.py env
python scripts/tpm_cli.py validate
python scripts/tpm_cli.py preflight --market ALL
python scripts/tpm_cli.py live --history-csv btc_real_24h.csv --poll-seconds 3600
```

## Forge Production Web Runtime (BTC + COFFEE, extensible)

Bu runtime artık EN/DE kanonik sürümleriyle senkronize edilmiştir:

- Varsayılan olarak finans alanında **BTC** ve **COFFEE** için birer TPM agent ile başlar.
- Kullanıcılar web arayüzünden yeni pazar/agent ekleyebilir (`/api/agents`).
- Servis sürekli çalışır ve canlı frame görünürlüğü sağlar (`/api/frame`).

### Start (local)

```bash
uvicorn production.forge_runtime:app --host 0.0.0.0 --port 8787
# open http://localhost:8787
```

### Start (Docker)

```bash
docker compose up tpm-forge-web
# open http://localhost:8787
```

## Senkronizasyon Notu

Diğer i18n README dosyaları EN/DE sürümlerine göre eşitlenmiştir.
Yerel dilde farklılık varsa referans kaynağı olarak önce İngilizce ve Almanca metinler esas alınır.

## LOP (Endnote – prioritized)

1. **P1 Expand real-data evidence:** benchmarking with explicit acceptance criteria (precision/recall/FPR/drift).
2. **P2 Finalize reflexive governance:** define strict auto safe-mode rules for uncertainty.
3. **P3 Standardize collective memory:** versioned learning patterns with per-domain review process.
4. **P4 Continue web immersion rollout:** role-based views for additional TPM sectors on top of the responsive runtime layout.

**Platform note:** current primary focus is **Windows + smartphone**. **Add later at the end of LOP:** macOS, Linux, and further platform profiles.
