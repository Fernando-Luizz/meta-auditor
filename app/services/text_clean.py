"""Limpeza de texto para relatórios (sem emojis pictográficos)."""

from __future__ import annotations

import html
import re

# Blocos Unicode frequentes em saídas de LLM e mensagens de UI (não inclui letras acentuadas LATIN).
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # símbolos e pictogramas
    "\U0001F680-\U0001F6FF"  # transporte e mapas
    "\U0001F1E0-\U0001F1FF"  # bandeiras
    "\U0001F900-\U0001F9FF"  # suplemento símbolos
    "\U0001FA00-\U0001FAFF"  # extensão-A pictogramas
    "\U00002600-\U000026FF"  # misc symbols
    "\U00002700-\U000027BF"  # dingbats
    "\U00002300-\U000023FF"  # misc técnico (⌚ etc.)
    "\U000020D0-\U000020FF"  # combining marks for symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"  # ZWJ
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str | None) -> str:
    """Remove pictogramas / emojis; preserva pontuação e texto em português."""
    if not text:
        return ""
    t = str(text)
    t = _EMOJI_RE.sub("", t)
    t = re.sub(r"[\uFE0F\u200D]{1,}", "", t)
    return re.sub(r" {2,}", " ", t).strip()


# Travessão (U+2014), meia-ráquia (U+2013), menos matemático (U+2212) em títulos Lighthouse / IA.
_RANGE_DASH = re.compile(r"(\d)\s*[\u2013\u2014\u2212]\s*(\d)")


def normalize_html_breaks(text: str | None) -> str:
    """
    Converte fragmentos HTML de quebra de linha em '\\n'.

    Cobre tags com espaços, `</br>`, entidades escapadas uma ou mais vezes
    (ex.: `&lt;br&gt;`, `&amp;lt;br&amp;gt;`) via `html.unescape` em loop limitado.
    """
    if text is None:
        return ""
    t = str(text).strip()
    if not t:
        return ""
    br_pat = re.compile(r"(?i)<\s*br\b[^>]*>")
    close_br_pat = re.compile(r"(?i)<\s*/\s*br\s*>")
    for _ in range(6):
        prev = t
        t = html.unescape(t)
        t = close_br_pat.sub("\n", t)
        t = br_pat.sub("\n", t)
        if t == prev:
            break
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    return t.strip()


def normalize_executive_plaintext(text: str | None) -> str:
    """
    Texto executivo / apêndice IA: sem tags <br>; quebras ficam em '\\n'.
    Usar no backend, no cache e na renderização (filtro Jinja).
    """
    t = normalize_html_breaks(text)
    if not t:
        return ""
    t = t.replace("—", ": ").replace("–", ": ")
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\s+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r":\s*:", ": ", t)
    t = strip_emoji(t)
    return t.strip()


def normalize_barrier_ai_texts(barrier: dict) -> None:
    """Re-normaliza campos de texto da IA (cache legado, JSON da BD). In-place."""
    if not isinstance(barrier, dict):
        return
    for k in (
        "justificativa_gerencial",
        "explicacao_usuario",
        "como_corrigir_claro",
        "acao_gerencial",
        "versao_dev",
    ):
        v = barrier.get(k)
        if isinstance(v, str) and v.strip():
            barrier[k] = normalize_executive_plaintext(v)
    tk = barrier.get("texto_ticket")
    if isinstance(tk, dict):
        for k in ("titulo", "descricao", "criterio_de_pronto"):
            v = tk.get(k)
            if isinstance(v, str) and v.strip():
                tk[k] = normalize_executive_plaintext(v)


def normalize_report_dashes(text: str | None) -> str:
    """
    Suaviza travessões para leitura em relatório: intervalos numéricos viram hífen ASCII;
    travessões tipográficos em frases viram dois-pontos, sem destruir «30–40%».
    """
    if not text:
        return ""
    t = str(text)
    t = _RANGE_DASH.sub(r"\1-\2", t)
    t = t.replace(" \u2014 ", ": ").replace(" \u2013 ", ": ")
    t = t.replace("\u2014 ", ": ").replace("\u2013 ", ": ")
    t = t.replace(" \u2014", ":").replace(" \u2013", ":")
    t = t.replace("\u2014", ": ")
    t = t.replace("\u2013", "-")
    t = t.replace("\u2212", "-")
    return re.sub(r" {2,}", " ", t).strip()
