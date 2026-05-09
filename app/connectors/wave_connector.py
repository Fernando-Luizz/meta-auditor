"""
Conector à API WAVE (WebAIM).
GET https://wave.webaim.org/api/request — salva JSON bruto em data/raw/.
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import DATA_RAW_DIR, MAX_TIMEOUT, WAVE_API_KEY, WAVE_BASE_URL, WAVE_REPORT_TYPE

# Serviço compartilhado WAVE: no máximo 2 requisições simultâneas por conta.
_wave_concurrency = asyncio.Semaphore(2)


class WaveAPIError(Exception):
    """Resposta WAVE com status.success == false ou corpo inesperado."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _safe_filename(url: str) -> str:
    parsed = urlparse(str(url))
    domain = parsed.netloc or "unknown"
    domain = re.sub(r"[^\w\-.]", "_", domain)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"wave_{domain}_{timestamp}.json"


async def run_wave(url: str) -> tuple[dict, Path]:
    if not WAVE_API_KEY:
        raise WaveAPIError("WAVE_API_KEY não configurada no ambiente (.env).")

    url_str = url if isinstance(url, str) else str(url)
    params = {
        "key": WAVE_API_KEY,
        "url": url_str,
        "format": "json",
        "reporttype": str(WAVE_REPORT_TYPE),
    }

    async with _wave_concurrency:
        async with httpx.AsyncClient(timeout=MAX_TIMEOUT) as client:
            response = await client.get(WAVE_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

    status_block = data.get("status") if isinstance(data, dict) else None
    if not isinstance(status_block, dict) or not status_block.get("success"):
        err = ""
        if isinstance(status_block, dict):
            err = str(status_block.get("error") or status_block.get("message") or "")
        raise WaveAPIError(err or "WAVE API retornou success=false sem mensagem.")

    raw_path = DATA_RAW_DIR / _safe_filename(url_str)
    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return data, raw_path
