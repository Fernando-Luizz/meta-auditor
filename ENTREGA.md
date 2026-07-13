# Submission package

The Meta-Auditor codebase is ready for review. What usually goes wrong at submission time is shipping development clutter or secrets inside the ZIP. This document defines what stays out of the package and how to generate a clean, reproducible one.

## Excluded from the package

| Item | Why |
|---|---|
| `.venv/` | Tied to a specific OS and architecture; recipients recreate it with `python -m venv` and `pip install -r requirements.txt`. |
| `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Tool caches, irrelevant to running the project. |
| `__pycache__/`, `*.pyc` | Regenerable bytecode. |
| `.env` | May contain PSI/WAVE keys; `.env.example` ships instead, as a template. |
| `data/meta_auditor.db` | Local development database, created automatically on first run. |
| `data/raw/*.json` | Raw per-audit JSON, large and unnecessary to run the system. |
| `data/evidence/*.png` | Evidence images generated at runtime. |
| `.git/` | Optional; include only if reviewers specifically need commit history. |

## Included in the package

Source code (`app/`, `tests/`), `requirements.txt`, `pytest.ini`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `.gitignore`, `README.md`, `LICENSE`, `ENTREGA.md`, `.github/workflows/`, and `data/raw/.gitkeep` plus `data/evidence/.gitkeep` to keep the empty folders in version control.

## Supplementary artifacts

`artifacts/` must be included in the review package. It contains:

- the specification of the 80 normalization mappings;
- the complete technical-evaluation material for CP01-CP09;
- the acceptance-evaluation reports for AP01-AP05;
- the pseudonymized TAM qualitative mapping;
- the figures used in the paper.

The exclusions above apply to `data/`, which holds runtime-generated files. They do not apply to `artifacts/`, which is frozen evaluation material.

## Generating the ZIP (Windows)

From the repository root:

```powershell
.\scripts\package_entrega.ps1
```

This creates `meta-auditor-entrega-YYYYMMDD-HHmm.zip` at the project root, excluding everything listed above.

## Smoke test (portability)

In a fresh folder, VM, or user account:

1. Unzip the clean package (or `git clone` without `.venv`).
2. `python -m venv .venv` and activate it.
3. `pip install -r requirements.txt`
4. `copy .env.example .env` and fill in at least `PSI_API_KEY` (add `WAVE_API_KEY` to test WAVE too).
5. `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
6. Check `GET /health`, then `POST /audit` with a public URL and open the HTML report.

Docker is the recommended way to validate a submission package:

```bash
cp .env.example .env
# edit .env with your keys
docker compose up --build
```

Open `http://127.0.0.1:8010` (mapped in `docker-compose.yml`) and repeat the `/health` check and an audit.

## About `GET /audits/{id}/export.zip`

This endpoint exports a single audit (its JSON and HTML), not the whole project, and never includes `.env`.
