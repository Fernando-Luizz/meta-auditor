"""Limpeza de texto para relatórios (sem emojis pictográficos)."""

from __future__ import annotations

import html
import re

from markupsafe import Markup, escape

# Tags HTML citadas em prosa (não viram elementos no relatório).
_HTML_TAG_LITERAL_RE = re.compile(
    r"</?(?:main|nav|header|footer|aside|section|article|ul|ol|li|div|span|"
    r"p|a|img|button|input|label|form|h[1-6]|code|pre|br|noscript)\b[^>]*>",
    re.IGNORECASE,
)

# Blocos Unicode frequentes em saídas de LLM (não inclui LATIN acentuado).
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
    """Remove emojis; preserva pontuação e PT."""
    if not text:
        return ""
    t = str(text)
    t = _EMOJI_RE.sub("", t)
    t = re.sub(r"[\uFE0F\u200D]{1,}", "", t)
    return re.sub(r" {2,}", " ", t).strip()


# Travessão / meia-ráquia / menos matemático em títulos LH/IA.
_RANGE_DASH = re.compile(r"(\d)\s*[\u2013\u2014\u2212]\s*(\d)")

# Lexicais frequentes (EN/ES infiltrado).
_PT_WORD_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bConductar\b", re.IGNORECASE), "Realizar"),
)

# JSON «prioridade» = severidade da barreira, não P1–P3.
_SEVERIDADE_LEX_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bbarreiras de alta prioridade\b", re.I), "barreiras de severidade alta"),
    (re.compile(r"\bbarreira de alta prioridade\b", re.I), "barreira de severidade alta"),
    (re.compile(r"\bbarreiras de média prioridade\b", re.I), "barreiras de severidade média"),
    (re.compile(r"\bbarreira de média prioridade\b", re.I), "barreira de severidade média"),
    (re.compile(r"\bbarreiras de baixa prioridade\b", re.I), "barreiras de severidade baixa"),
    (re.compile(r"\bbarreira de baixa prioridade\b", re.I), "barreira de severidade baixa"),
    (re.compile(r"\b(\d+)\s+de\s+alta\s+prioridade\b", re.I), r"\1 de severidade alta"),
    (re.compile(r"\b(\d+)\s+de\s+média\s+prioridade\b", re.I), r"\1 de severidade média"),
    (re.compile(r"\b(\d+)\s+de\s+baixa\s+prioridade\b", re.I), r"\1 de severidade baixa"),
    (re.compile(r"\bconsolidada como alta prioridade\b", re.I), "consolidada com severidade alta"),
    (re.compile(r"\bbarreiras altas\b", re.I), "barreiras de severidade alta"),
)


def _apply_pt_word_fixes(text: str) -> str:
    t = text
    for pattern, replacement in _PT_WORD_FIXES:
        t = pattern.sub(replacement, t)
    return t


def _apply_severidade_lex_fixes(text: str) -> str:
    t = text
    for pattern, replacement in _SEVERIDADE_LEX_FIXES:
        t = pattern.sub(replacement, t)
    return t


_LABEL_IN_NAME_CORRECAO = (
    "O nome acessível deve conter o texto visível do link, preferencialmente no início, "
    "para que usuários de controle por voz consigam acionar o elemento pelo texto que enxergam na tela."
)

_LABEL_IN_NAME_CARTAO_CORRECAO = (
    "O nome acessível deve conter o texto visível do cartão, preferencialmente no início, "
    "para que usuários de controle por voz consigam acionar o elemento pelo texto exibido na tela."
)

_IDENTICO_LABEL_IN_NAME_RE = re.compile(
    r"O texto visível[^.]*idêntic[^.]+\.",
    re.IGNORECASE,
)
_WCAG_253_NIVEL_AA_RE = re.compile(
    r"(2\.5\.3\s+Label in Name:\s*)Nível\s+AA",
    re.IGNORECASE,
)
_CARTAO_SERVICO_RE = re.compile(
    r"service-card|carta[_\s-]?de[_\s-]?servi[cç]o|cart[aã]o de servi[cç]o",
    re.IGNORECASE,
)
_REFLETIR_EXATAMENTE_ARIA_RE = re.compile(
    r"O aria-label deve refletir exatamente o que o usuário lê na tela[^.]*\.",
    re.IGNORECASE,
)


def _barrier_is_cartao_servico(barrier: dict) -> bool:
    parts: list[str] = []
    for k in (
        "como_corrigir_claro",
        "explicacao_usuario",
        "justificativa_gerencial",
        "acao_gerencial",
        "versao_dev",
    ):
        parts.append(str(barrier.get(k) or ""))
    for item in barrier.get("locais") or barrier.get("evidencias") or []:
        if isinstance(item, dict):
            parts.append(str(item.get("seletor") or ""))
            parts.append(str(item.get("snippet") or ""))
        else:
            parts.append(str(item))
    for code in barrier.get("evcodes") or []:
        parts.append(str(code))
    tk = barrier.get("texto_ticket")
    if isinstance(tk, dict):
        for k in ("titulo", "descricao", "criterio_de_pronto"):
            parts.append(str(tk.get(k) or ""))
    return bool(_CARTAO_SERVICO_RE.search(" ".join(parts)))


def _is_label_in_name_barrier(barrier: dict) -> bool:
    oid = (barrier.get("issue_id_original") or "").lower()
    tipo = (barrier.get("issue_tipo_normalizado") or "").lower()
    wg = (barrier.get("wcag_criterio") or "").lower()
    return (
        "label-content-name-mismatch" in oid
        or "label-in-name" in oid
        or "rotulo_difere" in tipo
        or "2.5.3" in wg
    )


def _apply_label_in_name_cartao_wording(text: str) -> str:
    t = text
    if t == _LABEL_IN_NAME_CORRECAO or re.search(
        r"nome acessível deve conter o texto visível do link", t, re.I
    ):
        t = _LABEL_IN_NAME_CARTAO_CORRECAO
    t = _REFLETIR_EXATAMENTE_ARIA_RE.sub(_LABEL_IN_NAME_CARTAO_CORRECAO, t)
    return t


def _fix_label_in_name_text(text: str, *, cartao_servico: bool = False) -> str:
    if not text:
        return text
    t = _WCAG_253_NIVEL_AA_RE.sub(r"\1Nível A", text)
    t = re.sub(
        r"(2\.5\.3\s+Label in Name)\s*:\s*Nível\s+AA",
        r"\1: Nível A",
        t,
        flags=re.I,
    )
    if _IDENTICO_LABEL_IN_NAME_RE.search(t):
        repl = (
            _LABEL_IN_NAME_CARTAO_CORRECAO
            if re.search(r"cart[aã]o", t, re.I)
            else _LABEL_IN_NAME_CORRECAO
        )
        t = _IDENTICO_LABEL_IN_NAME_RE.sub(repl, t)
    elif re.search(r"\bidêntic|\bidentic", t, re.I):
        t = (
            _LABEL_IN_NAME_CARTAO_CORRECAO
            if re.search(r"cart[aã]o", t, re.I)
            else _LABEL_IN_NAME_CORRECAO
        )
    elif re.search(r"exatamente essa frase|reconhecer exatamente", t, re.I):
        if re.search(r"nome acessível deve conter", t, re.I):
            t = re.split(r"\.\s+Quando o usuário lê", t, maxsplit=1, flags=re.I)[0].strip()
            if t and not t.endswith("."):
                t += "."
        elif re.search(r"cart[aã]o", t, re.I):
            t = _LABEL_IN_NAME_CARTAO_CORRECAO
        else:
            t = _LABEL_IN_NAME_CORRECAO
    if cartao_servico:
        t = _apply_label_in_name_cartao_wording(t)
    return t


def barrier_exec_text(text: str | None, barrier: dict | None) -> str:
    """Texto executivo/IA com normalização + Label in Name."""
    t = normalize_executive_plaintext(text)
    if isinstance(barrier, dict) and _is_label_in_name_barrier(barrier):
        cartao = _barrier_is_cartao_servico(barrier)
        t = _fix_label_in_name_text(t, cartao_servico=cartao)
    return t


def normalize_html_breaks(text: str | None) -> str:
    """Converte <br> / &lt;br&gt; (e escapes aninhados) em '\\n'."""
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
    """Texto executivo: sem <br>; travessões → ':'; emoji e lexicais."""
    t = normalize_html_breaks(text)
    if not t:
        return ""
    t = t.replace("—", ": ").replace("–", ": ")
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\s+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r":\s*:", ": ", t)
    t = strip_emoji(t)
    t = _apply_pt_word_fixes(t)
    t = _apply_severidade_lex_fixes(t)
    return t.strip()


def normalize_barrier_ai_texts(barrier: dict) -> None:
    """Re-normaliza campos IA in-place (cache legado / BD)."""
    if not isinstance(barrier, dict):
        return
    from app.services.contrast_elements import criterio_pronto_contraste_det, is_contrast_barrier

    label_in_name = _is_label_in_name_barrier(barrier)
    cartao = _barrier_is_cartao_servico(barrier) if label_in_name else False
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
            if label_in_name:
                barrier[k] = _fix_label_in_name_text(barrier[k], cartao_servico=cartao)
    tk = barrier.get("texto_ticket")
    if isinstance(tk, dict):
        for k in ("titulo", "descricao", "criterio_de_pronto"):
            v = tk.get(k)
            if isinstance(v, str) and v.strip():
                tk[k] = normalize_executive_plaintext(v)
                if label_in_name:
                    tk[k] = _fix_label_in_name_text(tk[k], cartao_servico=cartao)
        if is_contrast_barrier(barrier):
            tk["criterio_de_pronto"] = criterio_pronto_contraste_det(barrier)


def normalize_report_markup_text(text: str | None) -> str:
    """Desescapa entidades e remove <code>; devolve texto simples (sem |safe)."""
    if text is None:
        return ""

    t = str(text)

    for _ in range(6):
        new_t = html.unescape(t)
        if new_t == t:
            break
        t = new_t

    t = re.sub(r"(?is)<\s*/?\s*code\s*>", "", t)
    t = re.sub(r"(?is)<\s*br\s*/?\s*>", "\n", t)
    t = re.sub(r"(?is)<\s*/\s*br\s*>", "\n", t)

    t = normalize_report_dashes(t)
    t = strip_emoji(t)
    t = _apply_pt_word_fixes(t)

    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\s+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)

    return t.strip()


def format_html_tag_literals(text: str | None) -> Markup:
    """Exibe tags HTML como <code> escapado (ex.: &lt;main&gt;)."""
    if not text:
        return Markup("")
    s = str(text)
    parts: list[Markup | str] = []
    last = 0
    for match in _HTML_TAG_LITERAL_RE.finditer(s):
        if match.start() > last:
            parts.append(escape(s[last : match.start()]))
        tag = match.group(0)
        parts.append(Markup(f"<code>{escape(tag)}</code>"))
        last = match.end()
    if last < len(s):
        parts.append(escape(s[last:]))
    return Markup("").join(parts)


_TRUNC_TAIL_STOPWORDS = frozenset(
    {"a", "o", "e", "de", "do", "da", "dos", "das", "ou", "em", "no", "na", "nos", "nas", "um", "uma", "uns", "umas"}
)


def truncate_words(text: str | None, length: int = 320, suffix: str = "...") -> str:
    """Corta no limite de chars na última palavra completa."""
    if text is None:
        return ""
    t = str(text).strip()
    if not t or length <= 0:
        return t
    if len(t) <= length:
        return t
    cut = t[:length]
    if len(t) > length and t[length : length + 1].strip():
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
    elif " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    while cut and " " in cut:
        tail = cut.rsplit(" ", 1)[-1].lower().rstrip(".,;:")
        if len(tail) > 2 and tail not in _TRUNC_TAIL_STOPWORDS:
            break
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + suffix


def normalize_report_dashes(text: str | None) -> str:
    """Intervalos numéricos → hífen; travessões em prosa → ': '."""
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
