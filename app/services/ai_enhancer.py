from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlparse

import httpx

_log = logging.getLogger("uvicorn.error")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
REQUEST_TIMEOUT = 30.0

_cache: dict[str, dict] = {}


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


def _safe_int(v: object, default: int = 0) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _selectors(barrier: dict, n: int = 3) -> list[str]:
    ev = barrier.get("evidencia_localizacao") or []
    if isinstance(ev, list):
        return [str(s) for s in ev[:n] if s]
    return []


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence) :]
            if "```" in text:
                text = text[: text.rfind("```")]
            break
    try:
        return json.loads(text.strip())
    except Exception:
        return {}


async def _call_claude(prompt: str, api_key: str, max_tokens: int = 900) -> str:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(ANTHROPIC_API_URL, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]
    except Exception as exc:
        _log.warning("ai_enhancer: chamada Claude falhou — %s", exc)
        return ""


def _context_block(barrier: dict) -> str:
    sels = _selectors(barrier)
    sel_txt = "\n".join(f"  • {s}" for s in sels) if sels else "  (não disponíveis)"
    prio_map = {
        "alta": "ALTA — corrigir com urgência",
        "media": "MÉDIA — planejar correção",
        "baixa": "BAIXA — melhorar oportunisticamente",
        "revisao_manual": "REQUER REVISÃO MANUAL",
    }
    ferr_map = {
        "automatico_convergente": "Lighthouse + WAVE (confirmado por ambas)",
        "automatico_detectado": "Lighthouse ou WAVE (ferramenta única)",
    }
    return (
        "CONTEXTO DETERMINÍSTICO (fonte de verdade — não alterar):\n"
        f"  Tipo normalizado  : {barrier.get('issue_tipo_normalizado', '—')}\n"
        f"  Título técnico    : {barrier.get('titulo_tecnico', '—')}\n"
        f"  Critério WCAG     : {barrier.get('wcag_criterio', '—')}\n"
        f"  Público afetado   : {barrier.get('publico_afetado', '—')}\n"
        f"  Prioridade        : {prio_map.get(barrier.get('prioridade', ''), barrier.get('prioridade', '—'))}\n"
        f"  Ferramenta origem : {ferr_map.get(barrier.get('status_deteccao', ''), barrier.get('status_deteccao', '—'))}\n"
        f"  Ocorrências       : {_safe_int(barrier.get('ocorrencias_count'), 0)} elemento(s) afetado(s)\n"
        f"  Como corrigir base: {barrier.get('correcao_sugerida') or '(sem texto base)'}\n"
        f"  Seletores CSS     :\n{sel_txt}"
    )


def _prompt_nivel1(barrier: dict) -> str:
    return (
        "Você é especialista em acessibilidade web (WCAG 2.1, ARIA, comunicação técnica).\n\n"
        + _context_block(barrier)
        + """\n\nCom base APENAS no contexto acima, gere texto de explicação e comunicação.
NÃO invente WCAG, NÃO altere severidade, NÃO afirme conformidade legal.

Responda SOMENTE com JSON válido, sem markdown:

{
  "justificativa_gerencial": "<1-2 frases: por que esta prioridade foi atribuída, em linguagem de negócios>",
  "explicacao_usuario": "<2-3 frases: impacto real sobre pessoas com deficiência, com exemplo concreto>",
  "como_corrigir_claro": "<instrução prática em português simples, sem jargão — aplicável por dev sem experiência em acessibilidade>"
}"""
    )


def _prompt_nivel2(barrier: dict) -> str:
    return (
        "Você é especialista em acessibilidade web e gestão de backlog ágil.\n\n"
        + _context_block(barrier)
        + """\n\nCom base APENAS no contexto acima, gere material de apoio para a equipe.
NÃO invente dados técnicos. NÃO altere critério WCAG ou severidade.

Responda SOMENTE com JSON válido, sem markdown:

{
  "versao_gestor": "<1-2 frases no estilo executivo: problema + quem afeta + risco de não corrigir>",
  "versao_dev": "<instrução técnica direta com exemplo antes/depois se aplicável>",
  "texto_ticket": {
    "titulo": "<máximo 80 chars: verbo + problema + contexto>",
    "descricao": "<3-4 frases: problema detectado, quem é afetado, WCAG violado, impacto funcional>",
    "criterio_de_pronto": "<2-3 itens verificáveis que confirmam a correção>"
  }
}"""
    )


def _prompt_executive(
    barriers: list[dict],
    domain: str,
    lh_score: float | None,
    wave_score: float | None,
    score_risco: dict | None,
) -> str:
    alta = [b for b in barriers if b.get("prioridade") == "alta"]
    media = [b for b in barriers if b.get("prioridade") == "media"]
    lista = "\n".join(f"  • {b.get('titulo_tecnico', '—')}" for b in barriers)
    lh_txt = f"{int(lh_score * 100)}/100" if lh_score is not None else "indisponível"
    wv_txt = f"{wave_score:.1f}/10" if wave_score is not None else "indisponível"
    risco = score_risco.get("nivel", "—") if isinstance(score_risco, dict) else "—"
    valor_r = score_risco.get("valor", "—") if isinstance(score_risco, dict) else "—"
    return (
        "Você é consultor sênior de acessibilidade digital.\n\n"
        "DADOS DA AUDITORIA (fonte de verdade — não alterar):\n"
        f"  Portal            : {domain}\n"
        f"  Score Lighthouse  : {lh_txt}  (estrutura HTML)\n"
        f"  WAVE AIMscore     : {wv_txt}  (página renderizada)\n"
        f"  Score de Risco    : {valor_r}/3 — {risco}\n"
        f"  Total de barreiras: {len(barriers)} ({len(alta)} alta, {len(media)} média)\n"
        f"  Barreiras encontradas:\n{lista}\n\n"
        "NÃO invente dados. NÃO afirme conformidade legal. Use os dados acima.\n\n"
        "Escreva um resumo executivo em PT-BR com EXATAMENTE dois parágrafos:\n"
        "  1. Situação atual: o que os scores e barreiras significam em linguagem de negócios.\n"
        "  2. Recomendação: ações priorizadas, estimativa de esforço, risco de não agir.\n\n"
        "Responda SOMENTE com JSON válido, sem markdown:\n\n"
        '{"resumo_executivo_ai": "<parágrafo 1>\\n\\n<parágrafo 2>"}'
    )


async def _enrich_barrier(barrier: dict, api_key: str, level: int) -> None:
    cache_key = f"{barrier.get('issue_tipo_normalizado', '?')},{barrier.get('prioridade', '?')},{level}"
    if cache_key in _cache:
        barrier.update(_cache[cache_key])
        return

    result: dict = {}

    raw1 = await _call_claude(_prompt_nivel1(barrier), api_key)
    parsed1 = _parse_json(raw1)
    result.update(
        {
            "justificativa_gerencial": parsed1.get("justificativa_gerencial", ""),
            "explicacao_usuario": parsed1.get("explicacao_usuario", ""),
            "como_corrigir_claro": parsed1.get("como_corrigir_claro", ""),
        }
    )

    if level >= 2:
        raw2 = await _call_claude(_prompt_nivel2(barrier), api_key)
        parsed2 = _parse_json(raw2)
        result.update(
            {
                "versao_gestor": parsed2.get("versao_gestor", ""),
                "versao_dev": parsed2.get("versao_dev", ""),
                "texto_ticket": parsed2.get("texto_ticket", {}),
            }
        )

    _cache[cache_key] = result
    barrier.update(result)


async def _enrich_executive(
    report: dict,
    domain: str,
    lh_score: float | None,
    wave_score: float | None,
    api_key: str,
) -> None:
    barriers = report.get("barreiras_automaticas") or []
    score_risco = report.get("score_risco")
    raw = await _call_claude(
        _prompt_executive(barriers, domain, lh_score, wave_score, score_risco),
        api_key,
        max_tokens=600,
    )
    parsed = _parse_json(raw)
    texto = parsed.get("resumo_executivo_ai", "")
    if texto:
        report["resumo_executivo_ai"] = texto


async def enhance_report(
    report: dict,
    url: str,
    api_key: str | None,
    lh_score: float | None = None,
    wave_score: float | None = None,
    level: int = 2,
) -> None:
    if not api_key:
        return

    barriers: list[dict] = report.get("barreiras_automaticas") or []
    if not barriers:
        return

    domain = _domain(url)
    level = max(1, min(level, 2))

    _log.info("ai_enhancer: %d barreira(s) · nível %d · %s", len(barriers), level, domain)

    async def _safe_barrier(b: dict) -> None:
        try:
            await _enrich_barrier(b, api_key, level)
        except Exception as exc:
            _log.warning(
                "ai_enhancer: barreira '%s' falhou — %s", b.get("issue_tipo_normalizado", "?"), exc
            )

    async def _safe_exec() -> None:
        try:
            await _enrich_executive(report, domain, lh_score, wave_score, api_key)
        except Exception as exc:
            _log.warning("ai_enhancer: resumo executivo falhou — %s", exc)

    await asyncio.gather(*[_safe_barrier(b) for b in barriers], _safe_exec())

    report["ai_enhanced"] = True
    report["ai_enhancement_level"] = level
    _log.info("ai_enhancer: concluído · %s", domain)
