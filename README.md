# Meta-Auditor de Acessibilidade Web

Sistema que audita acessibilidade de qualquer URL pública combinando **Google Lighthouse** (via PageSpeed Insights API) e **WAVE** (WebAIM) em paralelo, consolida os resultados e gera um relatório unificado com diagnóstico acionável.

**Desenvolvido por:** Fernando Luiz da Silva Freire  
**Instituição:** UEA — Escola Superior de Tecnologia (EST)  
**Orientadora:** Prof.ª Dra. Marcia Sampaio

---

## O que o sistema faz

1. Recebe uma URL pública via `POST /audit` ou pela interface web em `/`
2. Executa **Lighthouse** (PSI API, modo **desktop**, categoria Accessibility) e, se configurada, **WAVE** em paralelo
3. **Normaliza** cada achado para critério WCAG, público afetado e sugestão de correção
4. **Consolida** em 4 tipos: Interseção · Exclusivo LH · Exclusivo WAVE · Divergência
5. Calcula **Score de Risco** agregado (0–3) além do score padrão do Lighthouse
6. Persiste no SQLite e gera **relatório HTML** com evidências por elemento
7. Mantém **histórico** com gráfico de evolução do score ao longo do tempo

---

## Requisitos

- **Python 3.11+** (ou Docker — veja seção Docker)
- **Chave Google PSI**: recomendada — obter no [Google Cloud Console](https://console.cloud.google.com/) ativando "PageSpeed Insights API" (sem ela o uso é limitado e sujeito a 429)
- **Chave WAVE API**: opcional — sem ela a auditoria usa só Lighthouse quando o PSI responder; com chave em [wave.webaim.org/api](https://wave.webaim.org/api/) o relatório inclui WAVE

---

## Instalação local (sem Docker)

```bash
# 1. Criar e ativar ambiente virtual
py -3 -m venv .venv              # Windows
python3 -m venv .venv            # Linux / macOS
source .venv/bin/activate        # Linux / macOS
.\.venv\Scripts\activate         # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env (recomendado: PSI_API_KEY; WAVE_API_KEY opcional para relatório completo)

# 4. Iniciar o servidor
uvicorn app.main:app --reload --port 8000
# Windows (recomendado): .\run_dev.ps1 — porta **8010** por padrão (evita conflito com outros serviços na 8000)
```

---

## Porta do servidor

| Como iniciou | URL típica |
|--------------|------------|
| `uvicorn ... --port 8000` | http://127.0.0.1:8000 |
| `.\run_dev.ps1` (Windows, porta padrão) | http://127.0.0.1:8010 |
| Variável `$env:META_AUDITOR_PORT` antes de `run_dev.ps1` | porta personalizada |
| `docker compose up` (mapeamento `8010:8000` no `docker-compose.yml`) | http://127.0.0.1:8010 |

Nos exemplos `curl` abaixo, use **8010** em vez de **8000** quando estiver com `run_dev.ps1` ou Docker no host.

---

## Instalação com Docker

```bash
# 1. Configurar .env
cp .env.example .env
# Editar .env com as chaves

# 2. Subir
docker compose up --build

# Em segundo plano
docker compose up --build -d

# Parar
docker compose down
```

Os dados (`data/`) persistem entre reinicializações via volume Docker.

A imagem Docker inclui **Playwright/Chromium** (evidências visuais de barreiras WAVE / fallback ao vivo): o primeiro `--build` demora mais e a imagem fica maior.

---

## Como usar

### Interface web

Abra a URL conforme a secção **Porta do servidor** acima (ex.: **http://127.0.0.1:8000** ou **http://127.0.0.1:8010**), insira uma URL e clique em **Auditar**. A auditoria demora cerca de 20–40 segundos.

### API REST

```bash
# Auditar uma URL (ajuste :8000 → :8010 se usar run_dev.ps1 ou Docker no host)
curl -X POST http://localhost:8000/audit \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.example.com"}'

# Histórico (últimas 20)
curl "http://localhost:8000/audits?limit=20"

# Histórico de uma URL específica (evolução)
curl "http://localhost:8000/audits?url=https://www.example.com"

# Relatório HTML
curl http://localhost:8000/audits/1/report.html

# Exportar como ZIP
curl -O http://localhost:8000/audits/1/export.zip

# Status
curl http://localhost:8000/health
```

---

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Interface web |
| `POST` | `/audit` | Auditar uma URL |
| `GET` | `/audits` | Histórico (`?limit=N`, `?url=https://...`) |
| `GET` | `/audits/{id}` | Relatório em JSON |
| `GET` | `/audits/{id}/report.html` | Relatório HTML (com botão imprimir para PDF) |
| `GET` | `/audits/{id}/export.zip` | Exportar auditoria completa |
| `GET` | `/audits/buscar-urls` | Autocomplete de URLs (`?q=substring`) |
| `GET` | `/health` | Status da API |
| `GET` | `/docs` | Swagger UI |

---

## Estrutura do projeto

```
meta auditor/
├── app/
│   ├── config.py                    # Variáveis de ambiente e constantes
│   ├── main.py                      # Rotas FastAPI e pipeline principal
│   ├── database.py                  # CRUD SQLite assíncrono (aiosqlite)
│   ├── connectors/
│   │   ├── lighthouse_connector.py  # PSI API com retry/backoff exponencial
│   │   └── wave_connector.py        # WAVE API com semáforo de concorrência
│   ├── services/
│   │   ├── normalize_maps.py        # 77 entradas: audit_id → WCAG + correção
│   │   ├── extractors.py            # Extrai evidências por elemento (lhId único)
│   │   ├── consolidation.py         # Merge, divergências, score de risco
│   │   └── ai_enhancer.py           # Extensão experimental (IA); núcleo não depende
│   ├── models/
│   │   └── request_models.py        # Pydantic: AuditRequest (corpo JSON do POST /audit)
│   └── templates/
│       ├── index.html               # Frontend SPA com gráfico SVG inline
│       └── report.html              # Relatório Jinja2 com CSS @media print
├── data/
│   ├── meta_auditor.db              # SQLite (criado automaticamente)
│   └── raw/                         # JSONs brutos (LH + WAVE por auditoria)
├── scripts/
│   └── package_entrega.ps1          # Gera ZIP limpo para entrega (Windows)
├── tests/
│   ├── test_consolidation.py
│   ├── test_normalize.py
│   └── test_database.py
├── ENTREGA.md                       # Checklist: o que vai / não vai no ZIP final
├── .github/
│   └── workflows/
│       └── ci.yml                 # pytest em push/PR (GitHub Actions)
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── LICENSE
├── requirements.txt
└── pytest.ini
```

---

## Variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `WAVE_API_KEY` | Não | — | Chave API WAVE (WebAIM); vazio = só Lighthouse quando PSI OK |
| `PSI_API_KEY` | Não | — | Chave Google PageSpeed Insights |
| `WAVE_REPORT_TYPE` | Não | `4` | `4` = itens + seletores; `2` = só contagens |
| `PSI_RETRY_MAX` | Não | `3` | Máximo de retentativas em 429/timeout |
| `PSI_RETRY_BASE_DELAY` | Não | `2.0` | Delay base (s) para backoff exponencial |
| `APP_ENV` | Não | `development` | Ambiente da aplicação |
| `MAX_TIMEOUT` | Não | `90` | Timeout HTTP relevante para coleta (segundos) |
| `DEBUG` | Não | `false` | `true` expõe `project_root` nas respostas |
| `REPORT_HTML_EVIDENCE_MAX` | Não | `20` | Máximo de evidências por secção no relatório HTML |
| `REPORT_FOOTER_ORG` | Não | texto UEA | Rodapé institucional no relatório |
| `REPORT_FOOTER_AUTHOR` | Não | — | Nome opcional no rodapé do relatório |
| `ANTHROPIC_API_KEY` | Não | — | Só para extensão experimental; vazio = sem chamadas à API |
| `AI_ENHANCE_REPORT` | Não | `false` | `true` ativa texto auxiliar por IA (requer chave Anthropic) |
| `AI_ENHANCE_LEVEL` | Não | `2` | Se IA ativa: `1` = explicações; `2` = + ticket / resumo executivo |

---

## Extensão experimental — texto auxiliar por IA (trabalho futuro)

O **objeto do trabalho** é o pipeline determinístico (Lighthouse, WAVE, normalização WCAG, consolidação, score de risco, relatório). Isso funciona **sem** qualquer chave ou chamada a modelo de linguagem.

Existe um módulo opcional (`ai_enhancer.py`) para, **se** `AI_ENHANCE_REPORT=true` e `ANTHROPIC_API_KEY` estiver definida, gerar parágrafos extras no relatório (ex.: linguagem mais acessível ao gestor, rascunho de ticket). Por defeito isso está **desligado** e pode ser apresentado no artigo como **evolução futura** ou experimentação, não como requisito de avaliação.

---

## Testes

```bash
pytest           # todos os testes
pytest -v        # verbose
pytest tests/test_consolidation.py  # só consolidação
```

Em repositórios no GitHub, o workflow `.github/workflows/ci.yml` executa `pytest` automaticamente em push e pull requests para `main`/`master`.

---

## Entendendo os resultados

### Score de Risco (0–3)

| Nível | Valor | Ação recomendada |
|-------|-------|-----------------|
| **BAIXO** | < 1.5 | Monitorar — barreiras leves |
| **MÉDIO** | 1.5–2.49 | Planejar correções no próximo ciclo |
| **ALTO** | ≥ 2.5 | Correção urgente — barreiras graves |

### Tipos de relação

| Tipo | Significado |
|------|-------------|
| **Interseção** | LH e WAVE confirmam — confiança máxima |
| **Exclusivo LH** | Só Lighthouse detectou |
| **Exclusivo WAVE** | Só WAVE detectou |
| **Divergência** | LH passou, WAVE detectou — WAVE prevalece |

---

## Antes de entregar (pacote ZIP)

Não envie um ZIP “da pasta do projeto” com `.venv`, caches, `.env` com chaves, base SQLite nem JSON brutos em `data/raw/` — o pacote fica pesado, não portátil e pode expor segredos.

- Guia completo e lista do que excluir: **`ENTREGA.md`**.
- No Windows, para gerar um arquivo limpo: **`.\scripts\package_entrega.ps1`** (cria `meta-auditor-entrega-*.zip` na raiz).
- O `.env` está em `.gitignore`; para entrega use só **`.env.example`**. O endpoint `GET /audits/{id}/export.zip` exporta **uma auditoria**, não o projeto inteiro, e **não** inclui `.env`.

---

## Licença

Projeto acadêmico — UEA / EST — 2026. Ver arquivo `LICENSE`.
