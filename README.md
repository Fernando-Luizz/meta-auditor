# Meta-Auditor

System that audits the accessibility of any public URL by combining
**Google Lighthouse** (via the PageSpeed Insights API) and **WAVE**
(WebAIM) in parallel, consolidating the results into a unified report
with actionable findings.

---

## What the system does

1. Accepts a public URL via `POST /audit` or the web UI at `/`
2. Runs **Lighthouse** (PSI API, **desktop** mode, Accessibility category) and, when configured, **WAVE** in parallel
3. **Normalizes** each finding to a WCAG criterion, affected audience and correction suggestion
4. **Consolidates** findings into three origin categories — intersection, Lighthouse-only and WAVE-only — with divergence as a complementary marker
5. Computes an aggregate **Risk Score** (0–3) in addition to the standard Lighthouse score
6. Persists results in SQLite and generates an **HTML report** with per-element evidence
7. Keeps an **audit history** with score evolution over time

---

## Requirements

- **Python 3.11+** (or Docker — see Docker section)
- **Google PSI key**: recommended — obtain from the [Google Cloud Console](https://console.cloud.google.com/) enabling "PageSpeed Insights API" (without it usage is limited and subject to 429)
- **WAVE API key**: optional — without it the audit uses only Lighthouse when PSI responds; with a key from [wave.webaim.org/api](https://wave.webaim.org/api/) the report includes WAVE

---

## API credentials

This repository does not include API credentials. Each user must
obtain and configure their own API keys.

1. Copy `.env.example` to `.env`.
2. Add your own credentials only to the local `.env` file.
3. Never commit or share the `.env` file.

Available variables:

- `PSI_API_KEY`: personal Google PageSpeed Insights API key;
- `WAVE_API_KEY`: personal WebAIM WAVE API key, required for the
  complete dual-tool audit;
- `ANTHROPIC_API_KEY`: personal Anthropic API key, required only when
  `AI_ENHANCE_REPORT=true`.

The deterministic audit pipeline works without the Anthropic key.
No credential used to produce the published results is distributed
with this repository.

---

## Local installation (without Docker)

```bash
# 1. Create and activate a virtual environment
py -3 -m venv .venv              # Windows
python3 -m venv .venv            # Linux / macOS
source .venv/bin/activate        # Linux / macOS
.\.venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your own keys only (never commit .env)

# 4. Start the server
uvicorn app.main:app --reload --port 8000
# Windows (recommended): .\run_dev.ps1 — port **8010** by default
```

---

## Server port

| How you started | Typical URL |
|-----------------|-------------|
| `uvicorn ... --port 8000` | http://127.0.0.1:8000 |
| `.\run_dev.ps1` (Windows, default) | http://127.0.0.1:8010 |
| `$env:META_AUDITOR_PORT` before `run_dev.ps1` | custom port |
| `docker compose up` (`8010:8000` in `docker-compose.yml`) | http://127.0.0.1:8010 |

In the `curl` examples below, use **8010** instead of **8000** when using `run_dev.ps1` or Docker on the host.

---

## Docker installation

```bash
# 1. Configure .env
cp .env.example .env
# Edit .env with your own keys

# 2. Start
docker compose up --build

# Background
docker compose up --build -d

# Stop
docker compose down
```

Data under `data/` persists across restarts via a Docker volume.

The Docker image includes **Playwright/Chromium** (visual evidence for WAVE barriers / live fallback): the first `--build` takes longer and the image is larger.

---

## How to use

### Web UI

Open the URL from the **Server port** section above, enter a URL and click **Auditar**. An audit typically takes about 20–40 seconds.

### REST API

```bash
# Audit a URL (use :8010 if using run_dev.ps1 or Docker on the host)
curl -X POST http://localhost:8000/audit \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.example.com"}'

# History (last 20)
curl "http://localhost:8000/audits?limit=20"

# History for a specific URL
curl "http://localhost:8000/audits?url=https://www.example.com"

# HTML report
curl http://localhost:8000/audits/1/report.html

# Export as ZIP
curl -O http://localhost:8000/audits/1/export.zip

# Status
curl http://localhost:8000/health
```

---

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Web UI |
| `POST` | `/audit` | Audit a URL |
| `GET` | `/audits` | History (`?limit=N`, `?url=https://...`) |
| `GET` | `/audits/{id}` | Report as JSON |
| `GET` | `/audits/{id}/report.html` | HTML report (print button for PDF) |
| `GET` | `/audits/{id}/export.zip` | Export full audit |
| `GET` | `/audits/buscar-urls` | URL autocomplete (`?q=substring`) |
| `GET` | `/health` | API status |
| `GET` | `/docs` | Swagger UI |

---

## Project structure

```
meta-auditor/
├── app/
│   ├── config.py
│   ├── main.py
│   ├── database.py
│   ├── connectors/
│   ├── services/
│   │   ├── normalize_maps.py   # 80 entries: 42 Lighthouse + 38 WAVE
│   │   ├── extractors.py
│   │   ├── consolidation.py
│   │   └── ai_enhancer.py      # optional AI extension
│   ├── models/
│   └── templates/
├── artifacts/                  # evaluation artifacts (see artifacts/README.md)
├── data/
├── scripts/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── LICENSE
└── requirements.txt
```

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WAVE_API_KEY` | No | — | WAVE API key; empty = Lighthouse only when PSI OK |
| `PSI_API_KEY` | No | — | Google PageSpeed Insights key |
| `WAVE_REPORT_TYPE` | No | `4` | `4` = items + selectors; `2` = counts only |
| `PSI_RETRY_MAX` | No | `3` | Max retries on 429/timeout |
| `PSI_RETRY_BASE_DELAY` | No | `2.0` | Base delay (s) for exponential backoff |
| `APP_ENV` | No | `development` | Application environment |
| `MAX_TIMEOUT` | No | `90` | HTTP timeout for collection (seconds) |
| `DEBUG` | No | `false` | `true` exposes `project_root` in responses |
| `REPORT_HTML_EVIDENCE_MAX` | No | `20` | Max evidence items per HTML section |
| `REPORT_FOOTER_ORG` | No | `Meta-Auditor` | Organization label in report footer |
| `REPORT_FOOTER_AUTHOR` | No | — | Optional author name in report footer |
| `ANTHROPIC_API_KEY` | No | — | Only for optional AI extension |
| `AI_ENHANCE_REPORT` | No | `false` | `true` enables AI auxiliary text |
| `AI_ENHANCE_LEVEL` | No | `2` | If AI on: `1` = explanations; `2` = + ticket / executive summary |

---

## Optional AI extension

The core pipeline (Lighthouse, WAVE, WCAG normalization, consolidation, risk score, report) works **without** any language-model key.

An optional module (`ai_enhancer.py`) can add auxiliary paragraphs when `AI_ENHANCE_REPORT=true` and `ANTHROPIC_API_KEY` is set. It is **off** by default.

---

## Tests

```bash
pytest
pytest -v
pytest tests/test_consolidation.py
```

---

## Understanding the results

### Risk Score (0–3)

| Level | Rule | Recommended action |
|-------|------|--------------------|
| **CRÍTICO** | Score ≥ 2.80 | Immediate remediation |
| **ALTO** | At least one high-severity barrier and Score < 2.80 | Urgent remediation |
| **MÉDIO** | Score ≥ 1.50 with no high-severity barriers | Plan fixes in the next cycle |
| **BAIXO** | Remaining cases | Monitor |

### Origin categories

| Category | Meaning |
|----------|---------|
| **Intersection** | LH and WAVE confirm — highest confidence |
| **Lighthouse-only** | Detected only by Lighthouse |
| **WAVE-only** | Detected only by WAVE |
| **Divergence** | Complementary marker (e.g. LH passed, WAVE detected) |

---

## Packaging notes

Do not ship a project ZIP that includes `.venv`, caches, a filled `.env`, the SQLite database or raw JSON under `data/raw/`.

- The `.env` file is gitignored; ship only `.env.example`.
- `GET /audits/{id}/export.zip` exports **one audit**, not the whole project, and does **not** include `.env`.

---

## License

See `LICENSE`.
