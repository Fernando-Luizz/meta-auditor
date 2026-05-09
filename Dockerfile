FROM python:3.11-slim

# Metadados
LABEL maintainer="Fernando Luiz da Silva Freire"
LABEL description="Meta-Auditor de Acessibilidade Web — Lighthouse + WAVE"

# Variáveis de build
ARG APP_DIR=/app

# Diretório de trabalho
WORKDIR ${APP_DIR}

# Instalar dependências de sistema (mínimas)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (aproveitar cache de layers)
COPY requirements.txt .

# Instalar dependências Python (+ Playwright para evidências visuais WAVE)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Chromium para capturas headless (/audits/.../evidence-image para barreiras WAVE)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir -p /ms-playwright \
    && python -m playwright install --with-deps chromium

# Copiar código da aplicação
COPY app/ ./app/

# Diretório de dados e evidências
RUN mkdir -p data/raw data/evidence && chmod -R 755 data/

# Usuário não-root; precisa ler os browsers em /ms-playwright
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser ${APP_DIR} /ms-playwright
USER appuser
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Porta padrão
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
