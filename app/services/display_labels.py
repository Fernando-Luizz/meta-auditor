"""
Rótulos humanos para relatório executivo e agrupamento POUR estável.

O identificador issue_tipo_normalizado permanece para consolidação e cache;
rotulo_exibicao e categoria_executiva são derivados para PDF e resumos.
"""

from __future__ import annotations

from app.services.normalize_maps import LIGHTHOUSE_NORMALIZATION, WAVE_NORMALIZATION

# Ajustes finos (prevalecem sobre titulo_tecnico automático quando necessário)
DISPLAY_LABEL_OVERRIDES: dict[str, str] = {
    "controle_sem_nome_acessivel": "Controle sem nome acessível",
    "ausencia_landmark_main": "Ausência da região principal <main>",
    "viewport_meta_problematico": "Viewport impede ampliação ou zoom",
    "botao_completamente_vazio": "Botão sem texto",
    "button_empty": "Botão sem texto",
    "heading_sem_conteudo": "Cabeçalho sem texto",
    "empty-heading": "Cabeçalho sem texto",
    "hierarquia_titulos_incorreta": "Hierarquia de títulos incorreta",
    "lista_filhos_invalidos": "Lista com estrutura inválida",
    "item_lista_fora_de_lista": "Item de lista fora de lista",
    "skip_link_nao_focalizavel": "Skip link não focalizável",
    "wave_alert_accesskey": "Atalho accesskey conflitante",
    "accesskey_duplicado": "Atalho accesskey duplicado",
}


def _build_issue_display_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    for meta in LIGHTHOUSE_NORMALIZATION.values():
        t = (meta.get("issue_tipo_normalizado") or "").strip()
        if not t:
            continue
        labels[t] = (meta.get("titulo_tecnico") or t).strip()
    for meta in WAVE_NORMALIZATION.values():
        t = (meta.get("issue_tipo_normalizado") or "").strip()
        if not t:
            continue
        tt = (meta.get("titulo_tecnico") or "").strip()
        prev = labels.get(t, "")
        if not prev or (tt and len(tt) > len(prev)):
            labels[t] = tt or prev or t
    labels.update(DISPLAY_LABEL_OVERRIDES)
    return labels


ISSUE_DISPLAY_LABELS: dict[str, str] = _build_issue_display_labels()


def issue_display_label(
    issue_tipo_normalizado: str | None,
    titulo_tecnico: str | None = None,
    issue_id_original: str | None = None,
) -> str:
    """Rótulo curto para PDF e UI; nunca devolve string vazia se houver tipo."""
    tipo = (issue_tipo_normalizado or "").strip()
    if tipo in ISSUE_DISPLAY_LABELS:
        return ISSUE_DISPLAY_LABELS[tipo]
    tt = (titulo_tecnico or "").strip()
    if tt and tt != tipo:
        return tt
    oid = (issue_id_original or "").strip()
    if oid and oid != tipo:
        return oid.replace("-", " ").replace("_", " ").strip().title()
    if tipo:
        return tipo.replace("_", " ").strip().title()
    return "–"


def executive_group_for(issue_tipo_normalizado: str | None) -> str:
    """
    Família executiva canónica para agregação POUR e contadores.
    Mantém o resumo estável mesmo com muitos tipos técnicos distintos.
    """
    t = (issue_tipo_normalizado or "").lower().strip()
    if not t:
        return "Outros"

    if "contraste" in t or t == "link_distinguivel_somente_por_cor" or "wave_alert_text_small" in t:
        return "Contraste e legibilidade"
    if (
        "imagem" in t
        or "alt" in t
        or "video" in t
        or "audio" in t
        or "youtube" in t
        or "embed" in t
        or "object" in t
        or "input_imagem" in t
        or "texto_alternativo" in t
    ):
        return "Imagens e mídia"
    if (
        "button" in t
        or "botao" in t
        or "controle_sem_nome" in t
        or "controle_interativo" in t
        or "label_vazio" in t
        or "link_sem_nome" in t
    ):
        return "Links e controles sem nome"
    if "link" in t or "texto_link" in t or "link_pdf" in t or "link_redundant" in t:
        return "Links e destinos"
    if (
        "formulario" in t
        or "label" in t
        or "campo_select" in t
        or "fieldset" in t
        or "orfao" in t
        or "multiplos_labels" in t
        or "formulario_so_title" in t
    ):
        return "Formulários e rótulos"
    if (
        "heading" in t
        or "hierarquia" in t
        or "h1_ausente" in t
        or "titulo_pagina" in t
        or "titulo_redundante" in t
        or "possivel_titulo" in t
    ):
        return "Títulos e estrutura"
    if "landmark" in t or "skip_link" in t or "duplicate-id" in t:
        return "Estrutura da página"
    if "viewport" in t:
        return "Viewport e zoom móvel"
    if "idioma" in t or "lang" in t or "codigo_idioma" in t:
        return "Idioma e metadados"
    if (
        "aria" in t
        or "lista_filhos" in t
        or "item_lista" in t
        or "id_duplicado" in t
        or "body_aria" in t
        or "aria_hidden" in t
        or "aria_referencia" in t
        or "rotulo_difere" in t
    ):
        return "ARIA e semântica"
    if (
        "target" in t
        or "alvo" in t
        or "tabindex" in t
        or "accesskey" in t
        or "focus" in t
        or "keyboard" in t
        or "event_handler" in t
        or "noscript" in t
        or "tabela_layout" in t
    ):
        return "Teclado e interação"
    if t.startswith("wave_alert_") or t.startswith("wave_"):
        return "Alertas WAVE"
    if t.startswith("lighthouse_"):
        return "Outros (Lighthouse)"

    return "Outros"


# Família executiva → bucket estável dos gráficos de categoria (7 colunas do relatório).
_EXEC_CHART_BUCKETS: dict[str, str] = {
    "Contraste e legibilidade": "contraste",
    "Imagens e mídia": "imagem",
    "Links e controles sem nome": "botao",
    "Links e destinos": "link",
    "Formulários e rótulos": "form",
    "Títulos e estrutura": "outro",
    "Estrutura da página": "outro",
    "Viewport e zoom móvel": "outro",
    "Idioma e metadados": "form",
    "ARIA e semântica": "aria",
    "Teclado e interação": "botao",
    "Alertas WAVE": "outro",
    "Outros (Lighthouse)": "outro",
    "Outros": "outro",
}


def chart_bucket_for_executive(cat: str | None) -> str:
    c = (cat or "").strip()
    if not c:
        return "outro"
    return _EXEC_CHART_BUCKETS.get(c, "outro")


def attach_display_fields(rows: list[dict] | None) -> None:
    """Preenche rotulo_exibicao, categoria_executiva e categoria_grafico in-place."""
    if not rows:
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        tipo = (row.get("issue_tipo_normalizado") or "").strip()
        row["rotulo_exibicao"] = issue_display_label(
            tipo,
            row.get("titulo_tecnico"),
            row.get("issue_id_original"),
        )
        row["categoria_executiva"] = executive_group_for(tipo)
        row["categoria_grafico"] = chart_bucket_for_executive(row["categoria_executiva"])
