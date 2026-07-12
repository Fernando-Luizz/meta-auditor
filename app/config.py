import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# .env do projeto prevalece sobre variáveis já definidas na sessão (ex. WAVE_REPORT_TYPE)
load_dotenv(_PROJECT_ROOT / ".env", override=True)
load_dotenv()  # cwd: só preenche chaves ainda ausentes

APP_VERSION = "1.0.0"

PSI_API_KEY = os.getenv("PSI_API_KEY", "").strip()
PSI_BASE_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
try:
    PSI_RETRY_MAX = max(0, int(os.getenv("PSI_RETRY_MAX", "3")))
except ValueError:
    PSI_RETRY_MAX = 3
try:
    PSI_RETRY_BASE_DELAY = float(os.getenv("PSI_RETRY_BASE_DELAY", "2.0"))
except ValueError:
    PSI_RETRY_BASE_DELAY = 2.0

WAVE_API_KEY = os.getenv("WAVE_API_KEY", "").strip()
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
# Texto auxiliar opcional; núcleo do relatório não depende de IA.
AI_ENHANCE_REPORT: bool = os.getenv("AI_ENHANCE_REPORT", "false").lower() == "true"
try:
    AI_ENHANCE_LEVEL = int(os.getenv("AI_ENHANCE_LEVEL", "2"))
except ValueError:
    AI_ENHANCE_LEVEL = 2
# Semáforo Anthropic; 5 equilibra throughput e timeouts.
try:
    AI_ANTHROPIC_CONCURRENCY = max(1, min(20, int(os.getenv("AI_ANTHROPIC_CONCURRENCY", "5"))))
except ValueError:
    AI_ANTHROPIC_CONCURRENCY = 5
try:
    AI_ANTHROPIC_REQUEST_TIMEOUT = float(os.getenv("AI_ANTHROPIC_REQUEST_TIMEOUT", "60"))
except ValueError:
    AI_ANTHROPIC_REQUEST_TIMEOUT = 60.0
WAVE_BASE_URL = "https://wave.webaim.org/api/request"
# 4 = itens+CSS (3 créd.); 3 = XPath; 2 = só contagens (2 créd.).
try:
    _wrt = int(os.getenv("WAVE_REPORT_TYPE", "4"))
except ValueError:
    _wrt = 4
WAVE_REPORT_TYPE = _wrt if _wrt in (1, 2, 3, 4) else 4

APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
MAX_TIMEOUT = int(os.getenv("MAX_TIMEOUT", "90"))

PROJECT_ROOT = _PROJECT_ROOT
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_EVIDENCE_DIR = PROJECT_ROOT / "data" / "evidence"
DATA_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = PROJECT_ROOT / "data" / "meta_auditor.db"

try:
    REPORT_HTML_EVIDENCE_MAX = max(1, int(os.getenv("REPORT_HTML_EVIDENCE_MAX", "20")))
except ValueError:
    REPORT_HTML_EVIDENCE_MAX = 20
REPORT_FOOTER_ORG = os.getenv("REPORT_FOOTER_ORG", "Meta-Auditor").strip()
REPORT_FOOTER_AUTHOR = os.getenv("REPORT_FOOTER_AUTHOR", "").strip()
