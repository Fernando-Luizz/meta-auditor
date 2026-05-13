"""Limpeza de texto para relatórios (sem emojis pictográficos)."""

from __future__ import annotations

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
