"""Inferência de tipos de elemento para barreiras de contraste (a partir do A1 / seletores)."""
from __future__ import annotations

import re
from typing import Any

from app.services.normalize_maps import (
    CONTRASTE_IMPACTO_CLAUSE,
    CONTRASTE_IMPACTO_DIFICULDADE_LEITURA,
    CONTRASTE_IMPACTO_DIFICULDADE_NAVEGACAO,
)


def _final_selector_segment(raw: str) -> str:
    """Último trecho do caminho (após o último '>') — elemento afetado, não ancestrais."""
    s = (raw or "").strip()
    if ">" in s:
        s = s.split(">")[-1].strip()
    return s


def _iter_localizacao_strings(barreira: dict[str, Any]) -> list[str]:
    """Lista bruta de strings de localização (uma por entrada do A1)."""
    out: list[str] = []
    campos = [
        barreira.get("evidencia_localizacao"),
        barreira.get("selectors"),
        barreira.get("seletores"),
        barreira.get("locais"),
        barreira.get("locations"),
        barreira.get("raw_locations"),
        barreira.get("entradas_tecnicas"),
        barreira.get("nodes"),
    ]
    for campo in campos:
        if not campo:
            continue
        if isinstance(campo, str):
            out.append(campo)
        elif isinstance(campo, list):
            for item in campo:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, dict):
                    for k in (
                        "selector",
                        "css_selector",
                        "node",
                        "html",
                        "target",
                        "path",
                        "snippet",
                    ):
                        if item.get(k):
                            out.append(str(item.get(k)))
    return out


def _collect_selector_text(barreira: dict[str, Any]) -> str:
    """Agrega apenas o elemento final de cada caminho/seletor (não ancestrais no path)."""
    segmentos = [
        _final_selector_segment(s).lower()
        for s in _iter_localizacao_strings(barreira)
        if s and s.strip()
    ]
    return " ".join(segmentos)


def _detect_tipos(bruto: str) -> list[str]:
    """Retorna rótulos humanos dos tipos de elemento encontrados nos seletores."""
    tipos: list[str] = []

    def tem(pattern: str) -> bool:
        return re.search(pattern, bruto, flags=re.I) is not None

    if tem(r"\bh1\b|<h1[\s>]| h1\b"):
        tipos.append("título principal")
    if tem(r"\bh2\b|<h2[\s>]| h2\b"):
        tipos.append("título de seção")
    if tem(r"\bh3\b|<h3[\s>]| h3\b"):
        tipos.append("subtítulo")
    if tem(r"\bp\b|<p[\s>]| p\b"):
        tipos.append("parágrafo")
    if tem(r"\ba\b|<a[\s>]|role=[\"']?link|\blink\b"):
        tipos.append("link")
    has_button = tem(
        r"\bbutton\b|<button[\s>]|role=[\"']?button|input\[type=['\"]?(submit|button)"
    )
    if has_button:
        tipos.append("botão")
    if tem(r"\bnav\b|<nav[\s>]|menu|navbar"):
        tipos.append("menu de navegação")
    if tem(r"\btextarea\b|<textarea[\s>]|select\b|<select[\s>]|form\b|<form[\s>]"):
        tipos.append("campo de formulário")
    elif tem(r"\binput\b|<input[\s>]") and not has_button:
        tipos.append("campo de formulário")
    if tem(r"card|noticia|notícia|banner"):
        tipos.append("card ou banner")

    return list(dict.fromkeys(tipos))


def inferir_onde_esta_contraste(barreira: dict[str, Any]) -> str:
    """Onde está o contraste (prioriza main/content sobre header)."""
    hay = " ".join(_iter_localizacao_strings(barreira)).lower()
    bruto = _collect_selector_text(barreira).lower()
    combined = f"{hay} {bruto}"

    has_text_or_table = re.search(
        r"\bmain\b|<main|content|section|\bh[1-6]\b|<p[\s>]|paragraph|\btable\b|<table|tbody|thead|\btd\b|\bth\b",
        combined,
        re.I,
    )
    has_nav = re.search(r"\bnav\b|<nav|menu|navbar", combined, re.I)
    has_header = re.search(r"\bheader\b|<header|cabec|topbar", combined, re.I)
    has_table = re.search(r"\btable\b|<table|tbody|thead|\btd\b|\bth\b", combined, re.I)

    if has_nav and not has_text_or_table:
        return "Menu de navegação"
    if has_header and not has_text_or_table:
        return "Cabeçalho da página"

    base = "Conteúdo principal da página"
    if has_table:
        return f"{base}, em elementos de texto e tabela"
    if has_text_or_table or has_header:
        return base
    return base


def inferir_elementos_contraste(barreira: dict[str, Any]) -> str:
    """
    Descrição humana dos elementos afetados para frases do tipo:
    «Os {retorno} {clause}.»
    """
    bruto = _collect_selector_text(barreira).lower()
    tipos = _detect_tipos(bruto)

    if not tipos:
        return "elementos indicados pela ferramenta"

    if len(tipos) == 1:
        t = tipos[0]
        if t == "botão":
            return "botões indicados pela ferramenta"
        if t == "link":
            return "links indicados pela ferramenta"
        if t == "menu de navegação":
            return "itens de menu de navegação indicados pela ferramenta"
        if t == "campo de formulário":
            return "campos de formulário indicados pela ferramenta"
        if t == "card ou banner":
            return "cards ou banners indicados pela ferramenta"
        if t in ("título principal", "título de seção", "subtítulo", "parágrafo"):
            return f"elementos de texto indicados pela ferramenta, como {t}"
        return f"{t} indicado pela ferramenta"

    textos = {"título principal", "título de seção", "subtítulo", "parágrafo"}
    only_text = all(t in textos for t in tipos)
    has_button = "botão" in tipos
    has_link = "link" in tipos or "menu de navegação" in tipos

    if only_text:
        if len(tipos) == 2:
            lista = f"{tipos[0]} e {tipos[1]}"
        else:
            lista = ", ".join(tipos)
        return f"elementos de texto indicados pela ferramenta, como {lista}"

    if has_button and not has_link and len(tipos) == 1:
        return "botões indicados pela ferramenta"

    if has_link and "botão" not in tipos and len([t for t in tipos if t in ("link", "menu de navegação")]) == len(tipos):
        if "menu de navegação" in tipos and "link" in tipos:
            return "links e itens de menu de navegação indicados pela ferramenta"
        if "menu de navegação" in tipos:
            return "itens de menu de navegação indicados pela ferramenta"
        return "links indicados pela ferramenta"

    if len(tipos) == 2:
        return f"{tipos[0]} e {tipos[1]} indicados pela ferramenta"

    return f"elementos como {', '.join(tipos[:3])} indicados pela ferramenta"


def elementos_contraste_onde_procurar(barreira: dict[str, Any]) -> str:
    """Fragmento curto para «…em X» no card Onde procurar."""
    el = inferir_elementos_contraste(barreira)
    if ", como " in el:
        return el.split(", como ", 1)[1]
    if el.startswith("elementos como "):
        return el.replace("elementos como ", "").replace(" indicados pela ferramenta", "")
    return el.replace(" indicados pela ferramenta", "").replace(" indicado pela ferramenta", "")


def frase_onde_procurar_contraste(barreira: dict[str, Any]) -> str:
    """Frase completa após «…na página, em …»."""
    el = barreira.get("elementos_contraste_humano") or inferir_elementos_contraste(barreira)
    if ", como " in el:
        return f"elementos de texto como {el.split(', como ', 1)[1]}"
    onde = elementos_contraste_onde_procurar(barreira)
    if onde:
        return onde
    return "elementos indicados pela ferramenta"


def is_contrast_barrier(barreira: dict[str, Any]) -> bool:
    tipo = (barreira.get("issue_tipo_normalizado") or "").lower()
    oid = (barreira.get("issue_id_original") or "").lower()
    hay = f"{tipo} {oid}"
    if "contraste_insuficiente" in hay:
        return True
    if re.search(r"(?:^|[\s_])(?:color-)?contrast(?:$|[\s_])", hay):
        return True
    return (barreira.get("wave_categoria") or "").lower() == "contrast"


def impacto_contraste_executivo() -> str:
    """Primeiro parágrafo de impacto na camada executiva (sem «bloqueia o acesso»)."""
    return (
        "Esta barreira pode impedir a leitura do conteúdo afetado por pessoas com baixa visão, "
        "especialmente em baixa iluminação, telas pequenas ou uso de ampliação."
    )


def impacto_contraste_deterministico(barreira: dict[str, Any]) -> str:
    elementos = barreira.get("elementos_contraste_humano") or inferir_elementos_contraste(barreira)
    bruto = _collect_selector_text(barreira).lower()

    base = f"Os {elementos} {CONTRASTE_IMPACTO_CLAUSE}. "

    if "botão" in elementos or re.search(r"button|role=[\"']?button", bruto, re.I):
        return (
            base
            + "Pessoas com baixa visão podem não conseguir identificar ou ler a ação disponível, "
            "prejudicando a conclusão da tarefa."
        )
    if (
        "link" in elementos
        or "menu" in elementos
        or "navegação" in elementos
        or re.search(r"\bnav\b|<a[\s>]|role=[\"']?link", bruto, re.I)
    ):
        return (
            base
            + f"Pessoas com baixa visão {CONTRASTE_IMPACTO_DIFICULDADE_NAVEGACAO}."
        )
    return base + f"Pessoas com baixa visão {CONTRASTE_IMPACTO_DIFICULDADE_LEITURA}."


def criterio_pronto_contraste_det(barreira: dict[str, Any]) -> str:
    """Critério de pronto para WCAG 1.4.3 (contraste de texto, não componentes gráficos)."""
    occ = max(1, int(barreira.get("ocorrencias_count") or 1))
    elem = "elemento" if occ == 1 else "elementos"
    return (
        f"Aumentar o contraste dos {occ} {elem} para razão mínima de 4.5:1 em texto normal "
        f"ou 3:1 em texto grande. Validar conformidade com WCAG 1.4.3 usando ferramenta de contraste "
        f"e confirmar legibilidade em baixa iluminação, com ampliação de tela e simulação de baixa visão."
    )


def correcao_contraste_deterministica(barreira: dict[str, Any]) -> str:
    elementos = barreira.get("elementos_contraste_humano") or inferir_elementos_contraste(barreira)
    return (
        f"Revisar as combinações de cor dos {elementos}, ajustando a cor do texto e/ou do fundo. "
        "Validar a razão de contraste mínima exigida pela WCAG: 4.5:1 para texto normal "
        "e 3:1 para texto grande."
    )


def enrich_contrast_fields(barreira: dict[str, Any]) -> None:
    """Preenche campos derivados para templates e IA (in-place)."""
    if not is_contrast_barrier(barreira):
        return
    barreira["is_contraste"] = True
    barreira["impacto_contraste_executivo"] = impacto_contraste_executivo()
    barreira["elementos_contraste_humano"] = inferir_elementos_contraste(barreira)
    barreira["elementos_contraste_onde"] = elementos_contraste_onde_procurar(barreira)
    barreira["elementos_contraste_onde_frase"] = frase_onde_procurar_contraste(barreira)
    barreira["impacto_contraste_det"] = impacto_contraste_deterministico(barreira)
    barreira["correcao_contraste_det"] = correcao_contraste_deterministica(barreira)
    barreira["criterio_pronto_contraste_det"] = criterio_pronto_contraste_det(barreira)
    barreira["onde_esta"] = inferir_onde_esta_contraste(barreira)
