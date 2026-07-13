<p align="center">
  <img src="app/static/apple-touch-icon.png" width="84" alt="Meta-Auditor">
</p>

# Meta-Auditor

Web accessibility auditing tool that runs Google Lighthouse and WAVE against a public URL in parallel and consolidates both outputs into a single, prioritized report.

![Python](https://img.shields.io/badge/python-3.11%2B-1A6B3C?style=flat-square)
![Lighthouse](https://img.shields.io/badge/lighthouse-PageSpeed%20API-1464C8?style=flat-square)
![WAVE](https://img.shields.io/badge/WAVE-WebAIM%20API-0A6B60?style=flat-square)
![License](https://img.shields.io/badge/license-academic%20use-6b7280?style=flat-square)

This repository is the supplementary material for *Meta-Auditor: A Meta-Auditing Approach for Web Accessibility Quality Assessment*, submitted under double-anonymous review. Evaluation data (raw tool outputs, consolidated results, generated reports) lives under [`artifacts/`](artifacts/README.md).

## Overview

Lighthouse and WAVE rarely agree on what counts as an accessibility barrier: each tool catches a different subset of problems on the same page. Meta-Auditor does not just run both and print two reports side by side. It normalizes every finding to a common vocabulary, merges the ones both tools agree on, keeps the ones only one tool caught, and ranks the result by an aggregate risk score instead of relying on either tool's raw pass/fail score alone.

Pipeline, end to end:

1. Accept a public URL through the web interface or `POST /audit`.
2. Run Lighthouse (PSI API, desktop mode, Accessibility category) and, if configured, WAVE, in parallel.
3. Normalize each finding to a WCAG criterion, affected audience, and correction guidance.
4. Consolidate matching findings into three origin categories, intersection, Lighthouse-only, WAVE-only, and flag divergences between the tools as a complementary marker.
5. Compute the aggregate Risk Score (0-3) and assign a P1 / P2 / P3 correction priority to each consolidated barrier.
6. Persist everything to SQLite and render an HTML report with per-element evidence.
7. Keep an audit history so scores can be tracked over time.

## Requirements

- Python 3.11 or later, or Docker (see [Docker](#docker))
- A Google PageSpeed Insights API key is recommended. Without one, requests are rate-limited and may return `429`. Get one from the [Google Cloud Console](https://console.cloud.google.com/).
- A WAVE API key is optional. Without it, audits fall back to Lighthouse only. Get one from [wave.webaim.org/api](https://wave.webaim.org/api/).

## Getting started

### Without Docker

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv            # Linux / macOS
source .venv/bin/activate
py -3 -m venv .venv               # Windows
.\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables (see Configuration below)
cp .env.example .env

# 4. Start the server
uvicorn app.main:app --reload --port 8000
# Windows alternative: .\run_dev.ps1 (defaults to port 8010)
```

### Docker

```bash
cp .env.example .env
docker compose up --build          # foreground
docker compose up --build -d       # background
docker compose down                # stop
```

Data under `data/` persists across restarts through a Docker volume. The image bundles Playwright and Chromium for WAVE's visual evidence, so the first build takes longer and the image is larger than a plain Python image.

### Server port

| Start command | URL |
|---|---|
| `uvicorn ... --port 8000` | http://127.0.0.1:8000 |
| `.\run_dev.ps1` (Windows default) | http://127.0.0.1:8010 |
| `$env:META_AUDITOR_PORT` before `run_dev.ps1` | custom port |
| `docker compose up` (`8010:8000` in `docker-compose.yml`) | http://127.0.0.1:8010 |

The `curl` examples below use `8000`; swap in `8010` if you started the app with `run_dev.ps1` or Docker.

## Configuration

Meta-Auditor does not ship with API credentials. Copy `.env.example` to `.env` and add your own keys there. `.env` is gitignored and should never be committed or shared.

| Variable | Required | Default | Description |
|---|---|---|---|
| `PSI_API_KEY` | No | - | Google PageSpeed Insights key |
| `WAVE_API_KEY` | No | - | WAVE API key; without it, audits run Lighthouse only |
| `ANTHROPIC_API_KEY` | No | - | Only needed if `AI_ENHANCE_REPORT=true` |
| `WAVE_REPORT_TYPE` | No | `4` | `4` = items + CSS selectors, `2` = counts only |
| `PSI_RETRY_MAX` | No | `3` | Max retries on `429` / timeout |
| `PSI_RETRY_BASE_DELAY` | No | `2.0` | Base delay (s) for exponential backoff |
| `APP_ENV` | No | `development` | Application environment |
| `MAX_TIMEOUT` | No | `90` | HTTP timeout for collection, in seconds |
| `DEBUG` | No | `false` | `true` exposes `project_root` in responses |
| `REPORT_HTML_EVIDENCE_MAX` | No | `20` | Max evidence items per HTML report section |
| `REPORT_FOOTER_ORG` | No | `Meta-Auditor` | Organization label in the report footer |
| `REPORT_FOOTER_AUTHOR` | No | - | Optional author name in the report footer |
| `AI_ENHANCE_REPORT` | No | `false` | `true` enables the optional AI-assisted text (see below) |
| `AI_ENHANCE_LEVEL` | No | `2` | `1` = explanations only, `2` = adds ticket and executive summary |

The deterministic pipeline (Lighthouse, WAVE, normalization, consolidation, Risk Score, priorities) works with no language-model key at all. None of the credentials used to produce the results reported in the paper are distributed with this repository.

## Using Meta-Auditor

### Web interface

Open the URL from [Server port](#server-port) above, enter a URL, and click **Auditar**. An audit typically takes 20 to 40 seconds.

### REST API

```bash
# Audit a URL
curl -X POST http://localhost:8000/audit \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.example.com"}'

# History (last 20)
curl "http://localhost:8000/audits?limit=20"

# History for a specific URL
curl "http://localhost:8000/audits?url=https://www.example.com"

# HTML report
curl http://localhost:8000/audits/1/report.html

# Export a single audit as ZIP
curl -O http://localhost:8000/audits/1/export.zip

# Health check
curl http://localhost:8000/health
```

### Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Web interface |
| `POST` | `/audit` | Audit a URL |
| `GET` | `/audits` | History (`?limit=N`, `?url=...`) |
| `GET` | `/audits/{id}` | Report as JSON |
| `GET` | `/audits/{id}/report.html` | HTML report (print button generates a PDF) |
| `GET` | `/audits/{id}/export.zip` | Export a single audit |
| `GET` | `/audits/buscar-urls` | URL autocomplete (`?q=substring`) |
| `GET` | `/health` | API status |
| `GET` | `/docs` | Swagger UI |

## Understanding the results

### Risk Score (0-3)

| Level | Rule | Suggested action |
|---|---|---|
| CRÍTICO | Score ≥ 2.80 | Immediate remediation |
| ALTO | Score < 2.80, with at least one high-severity barrier | Urgent remediation |
| MÉDIO | Score ≥ 1.50, no high-severity barriers | Plan for the next cycle |
| BAIXO | Everything else | Monitor |

### Origin categories

| Category | Meaning |
|---|---|
| Intersection | Confirmed by both Lighthouse and WAVE, highest confidence |
| Lighthouse-only | Detected only by Lighthouse |
| WAVE-only | Detected only by WAVE |
| Divergence | Complementary marker: one tool flagged it, the other passed the equivalent check |

## Project structure

```
meta-auditor/
├── app/
│   ├── config.py
│   ├── main.py
│   ├── database.py
│   ├── connectors/
│   ├── services/
│   │   ├── normalize_maps.py   # 80 mapping rules: 42 Lighthouse + 38 WAVE
│   │   ├── extractors.py
│   │   ├── consolidation.py
│   │   └── ai_enhancer.py      # optional AI extension
│   ├── models/
│   └── templates/
├── artifacts/                  # evaluation artifacts, see artifacts/README.md
├── data/
├── scripts/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── LICENSE
└── requirements.txt
```

## Tests

```bash
pytest
pytest -v
pytest tests/test_consolidation.py
```

## License

See [LICENSE](LICENSE).
