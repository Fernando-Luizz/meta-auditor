# Pacote de entrega final (ZIP limpo)

O núcleo do Meta-Auditor está preparado para avaliação; o que costuma falhar na **entrega** é incluir lixo de desenvolvimento ou segredos no arquivo ZIP. Este guia define o que **não** vai no pacote e como gerar um ZIP **reprodutível**.

## O que **não** incluir no ZIP institucional

| Item | Motivo |
|------|--------|
| `.venv/` | Ambiente por SO/arquitetura; não é portátil (ex.: Windows vs Linux). Quem recebe cria o seu com `python -m venv` + `pip install -r requirements.txt`. |
| `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Cache de ferramentas; irrelevante para execução. |
| `__pycache__/` e `*.pyc` | Bytecode regenerável. |
| `.env` | Pode conter chaves PSI/WAVE; usar só `.env.example` como modelo. |
| `data/meta_auditor.db` | Base local de desenvolvimento; é criada ao executar a aplicação. |
| `data/raw/*.json` | JSON brutos por auditoria; pesados e desnecessários para instalar o sistema. |
| `data/evidence/*.png` | Evidências geradas em runtime. |
| `.git/` | Opcional: incluir só se a instituição pedir histórico Git; aumenta o tamanho. |

## O que **sim** deve ir no ZIP

Código-fonte (`app/`, `tests/`), `requirements.txt`, `pytest.ini`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `.gitignore`, `README.md`, `LICENSE`, `ENTREGA.md`, `.github/workflows/` (CI), e `data/raw/.gitkeep` + `data/evidence/.gitkeep` para manter pastas vazias.

## Supplementary artifacts

The `artifacts/` directory must be included in the review package.

It contains:

- the specification of the 80 normalization mappings;
- the complete technical evaluation material for CP01–CP09;
- the acceptance-evaluation reports for AP01–AP05;
- the pseudonymized TAM qualitative mapping;
- the figures associated with the article.

The exclusion of runtime-generated files under `data/` does not apply to
the frozen evaluation material stored under `artifacts/`.

## Gerar o ZIP automaticamente (Windows)

Na raiz do repositório:

```powershell
.\scripts\package_entrega.ps1
```

É criado um arquivo `meta-auditor-entrega-YYYYMMDD-HHmm.zip` na raiz do projeto, sem os artefatos acima.

## Teste de fumo (portabilidade)

Em uma pasta **nova** (ou máquina virtual / outro usuário):

1. Descompactar o ZIP limpo (ou `git clone` sem `.venv`).
2. `python -m venv .venv` e ativar o venv.
3. `pip install -r requirements.txt`
4. `copy .env.example .env` e preencher pelo menos `PSI_API_KEY` (e `WAVE_API_KEY` se quiser WAVE).
5. `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
6. Verificar `GET /health`, depois `POST /audit` com uma URL pública e abrir o relatório HTML.

**Docker (recomendado para validar entrega):**

```bash
cp .env.example .env
# Editar .env com chaves
docker compose up --build
```

Acesse `http://127.0.0.1:8010` (mapeamento no `docker-compose.yml`) e repita `/health` + uma auditoria.

## Nota sobre `GET /audits/{id}/export.zip`

Esse endpoint exporta **uma auditoria** (JSON/HTML da corrida), não o projeto completo, e **não** inclui `.env`.
