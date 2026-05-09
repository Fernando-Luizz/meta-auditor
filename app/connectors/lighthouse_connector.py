"""
Conector ao Google PageSpeed Insights (Lighthouse).
Recebe uma URL, chama a API, armazena o JSON bruto e retorna o resultado.
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import (
    DATA_RAW_DIR,
    MAX_TIMEOUT,
    PSI_API_KEY,
    PSI_BASE_URL,
    PSI_RETRY_BASE_DELAY,
    PSI_RETRY_MAX,
)

_log = logging.getLogger(__name__)

# Códigos HTTP do PSI que justificam retry (erros transientes).
_PSI_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


def _safe_filename(url: str) -> str:
    """Gera um nome de arquivo seguro a partir da URL e timestamp."""
    parsed = urlparse(str(url))
    domain = parsed.netloc or "unknown"
    domain = re.sub(r"[^\w\-.]", "_", domain)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"lighthouse_{domain}_{timestamp}.json"


async def _do_psi_request(url_str: str) -> tuple[dict, Path]:
    """Faz UMA requisição ao PSI — sem retry. Levanta httpx.HTTPStatusError em falha."""
    params = {
        "url": url_str,
        "strategy": "DESKTOP",
        "category": "ACCESSIBILITY",
    }
    if PSI_API_KEY:
        params["key"] = PSI_API_KEY

    async with httpx.AsyncClient(timeout=MAX_TIMEOUT) as client:
        response = await client.get(PSI_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

    raw_path = DATA_RAW_DIR / _safe_filename(url_str)
    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data, raw_path


async def run_lighthouse(url: str) -> tuple[dict, Path]:
    """
    Executa auditoria Lighthouse/PSI com retry + backoff exponencial.

    Estratégia:
      - Tentativas totais: PSI_RETRY_MAX + 1  (padrão: 4).
      - Retry apenas em erros transientes: 429, 500, 502, 503, 504, Timeout.
      - Delays: PSI_RETRY_BASE_DELAY × 2^tentativa  →  2s, 4s, 8s por padrão.
      - Erros permanentes (400, 401, 403…) são propagados imediatamente.

    Returns:
        Tupla (resposta PSI, caminho do JSON bruto em data/raw).

    Raises:
        httpx.HTTPStatusError: erro HTTP não transiente ou esgotadas as tentativas.
        httpx.TimeoutException: timeout esgotadas as tentativas.
    """
    url_str = url if isinstance(url, str) else str(url)
    last_exc: Exception | None = None

    for attempt in range(PSI_RETRY_MAX + 1):
        try:
            return await _do_psi_request(url_str)

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status not in _PSI_RETRY_STATUS:
                raise  # 400, 401, 403 — não retenta
            last_exc = exc
            if attempt < PSI_RETRY_MAX:
                delay = PSI_RETRY_BASE_DELAY * (2**attempt)
                _log.warning(
                    "PSI %s (tentativa %d/%d) — aguardando %.0fs antes de retentar",
                    status,
                    attempt + 1,
                    PSI_RETRY_MAX + 1,
                    delay,
                )
                await asyncio.sleep(delay)

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            if attempt < PSI_RETRY_MAX:
                delay = PSI_RETRY_BASE_DELAY * (2**attempt)
                _log.warning(
                    "PSI timeout/connect (tentativa %d/%d) — aguardando %.0fs",
                    attempt + 1,
                    PSI_RETRY_MAX + 1,
                    delay,
                )
                await asyncio.sleep(delay)

    raise last_exc  # type: ignore[misc]


def extract_accessibility_audits(psi_response: dict) -> list[dict]:
    """
    Extrai os audits de acessibilidade do resultado do PSI.

    Usa lighthouseResult.categories.accessibility.auditRefs para garantir que
    só os audits daquela categoria sejam retornados (e nao todos os audits do
    lighthouseResult).
    """
    result = []
    lhr = psi_response.get("lighthouseResult") or {}
    audits = lhr.get("audits") or {}

    categories = lhr.get("categories") or {}
    a11y_category = categories.get("accessibility") or {}
    audit_refs = a11y_category.get("auditRefs") or []

    category_groups = lhr.get("categoryGroups") or {}

    # Sem categoria (ex.: falha em rodar ACCESSIBILITY), retorna lista vazia.
    if not isinstance(audit_refs, list):
        return result

    for ref in audit_refs:
        if not isinstance(ref, dict):
            continue
        audit_id = ref.get("id")
        if not audit_id:
            continue

        audit = audits.get(audit_id) or {}
        if not isinstance(audit, dict):
            continue

        group_id = ref.get("group") or ""
        group_meta = category_groups.get(group_id) or {}

        result.append({
            "id": audit_id,
            "title": audit.get("title", ""),
            "description": audit.get("description", ""),
            "score": audit.get("score"),
            "scoreDisplayMode": audit.get("scoreDisplayMode", ""),
            "displayValue": audit.get("displayValue"),
            "details": audit.get("details"),
            "explanation": audit.get("explanation"),
            "errorMessage": audit.get("errorMessage"),
            "warnings": audit.get("warnings"),
            "weight": ref.get("weight"),
            "group": group_id,
            "group_title": group_meta.get("title"),
            "group_description": group_meta.get("description"),
        })

    return result


def get_accessibility_category(psi_response: dict) -> dict:
    """Retorna lighthouseResult.categories.accessibility (quando existir)."""
    lhr = psi_response.get("lighthouseResult") or {}
    categories = lhr.get("categories") or {}
    return categories.get("accessibility") or {}


def get_accessibility_score(psi_response: dict) -> float | None:
    """Retorna o score de acessibilidade (0–1) quando disponível."""
    a11y = get_accessibility_category(psi_response)
    if isinstance(a11y.get("score"), (int, float)):
        return float(a11y["score"])
    return None


def classify_accessibility_audits(audits: list[dict]) -> dict[str, list[dict]]:
    """
    Classifica audits de acessibilidade com base em scoreDisplayMode.

    - binary: score 0 => failed; score 1 => passed
    - manual: manual checks
    - notApplicable: nao aplicavel
    - informative: informativo (nao impede, mas e guia)
    - error: ocorreu erro ao coletar informacoes do audit
    """
    failed: list[dict] = []
    passed: list[dict] = []
    manual: list[dict] = []
    not_applicable: list[dict] = []
    informative: list[dict] = []
    errors: list[dict] = []

    for audit in audits:
        if not isinstance(audit, dict):
            continue

        mode = audit.get("scoreDisplayMode") or ""
        mode_str = str(mode).strip()
        mode_lower = mode_str.lower()

        score = audit.get("score")

        if mode_lower == "manual":
            manual.append(audit)
        elif mode_lower in ("notapplicable", "not-applicable", "not_applicable"):
            not_applicable.append(audit)
        elif mode_lower == "informative":
            informative.append(audit)
        elif mode_lower == "error":
            errors.append(audit)
        elif mode_lower == "binary":
            if score == 0:
                failed.append(audit)
            elif score == 1:
                passed.append(audit)
            else:
                informative.append(audit)
        else:
            # Fallback defensivo: se tiver score numerico, decide por 0/1.
            if score == 0:
                failed.append(audit)
            elif score == 1:
                passed.append(audit)
            elif mode_lower:
                informative.append(audit)

    return {
        "failed": failed,
        "passed": passed,
        "manual": manual,
        "not_applicable": not_applicable,
        "informative": informative,
        "errors": errors,
    }


def compute_score_breakdown(psi_response: dict) -> dict:
    """
    Calcula a decomposição do score de acessibilidade do Lighthouse.

    Formula: score = Soma(peso x resultado) / Soma(todos os pesos)
    Apenas audits com scoreDisplayMode='binary' e weight > 0 entram no calculo.
    """
    lhr = psi_response.get("lighthouseResult") or {}
    audits_map = lhr.get("audits") or {}
    a11y_category = (lhr.get("categories") or {}).get("accessibility") or {}
    audit_refs = a11y_category.get("auditRefs") or []
    category_groups = lhr.get("categoryGroups") or {}

    total_weight = 0
    weighted_sum = 0.0
    failed_list: list[dict] = []
    passed_count = 0

    for ref in audit_refs:
        if not isinstance(ref, dict):
            continue
        aid = ref.get("id") or ""
        weight = ref.get("weight") or 0
        if not (isinstance(weight, (int, float)) and weight > 0):
            continue

        audit = audits_map.get(aid) or {}
        mode = str(audit.get("scoreDisplayMode") or "").lower()
        score = audit.get("score")

        if mode != "binary" or score is None:
            continue

        weight_int = int(weight)
        total_weight += weight_int
        weighted_sum += float(score) * weight_int

        if score == 0:
            group_id = ref.get("group") or ""
            group_title = (category_groups.get(group_id) or {}).get("title") or group_id
            failed_list.append(
                {
                    "id": aid,
                    "title": str(audit.get("title") or ""),
                    "weight": weight_int,
                    "group": group_title,
                    "_weight_lost": weight_int,
                }
            )
        elif score == 1:
            passed_count += 1

    if total_weight > 0:
        for item in failed_list:
            item["impact_pts"] = round(item["_weight_lost"] / total_weight * 100, 2)
            del item["_weight_lost"]
        score_calc = round(weighted_sum / total_weight * 100, 1)
    else:
        for item in failed_list:
            item["impact_pts"] = 0.0
            del item["_weight_lost"]
        score_calc = 0.0

    failed_list.sort(key=lambda x: -x["impact_pts"])
    effective_weight = total_weight - sum(item["weight"] for item in failed_list)

    return {
        "total_weight": total_weight,
        "effective_weight": effective_weight,
        "score_calculated": score_calc,
        "failed_audits": failed_list,
        "passed_audits_count": passed_count,
        "scored_audits_count": (passed_count + len(failed_list)) if total_weight else 0,
    }
