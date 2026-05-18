"""
Mapeamento de IDs das ferramentas para issue_tipo_normalizado e metadados WCAG (extensível).
"""
from __future__ import annotations

from typing import TypedDict


class NormalizedMeta(TypedDict, total=False):
    issue_tipo_normalizado: str
    titulo_tecnico: str
    wcag_criterio: str
    publico_afetado: str
    correcao_sugerida: str


# Lighthouse: audit id -> meta
LIGHTHOUSE_NORMALIZATION: dict[str, NormalizedMeta] = {
    "image-alt": {
        "issue_tipo_normalizado": "imagem_sem_texto_alternativo",
        "titulo_tecnico": "Imagens sem texto alternativo",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Cegos e leitores de tela",
    },
    "link-name": {
        "issue_tipo_normalizado": "link_sem_nome_acessivel",
        "titulo_tecnico": "Links sem nome acessível",
        "wcag_criterio": "2.4.4 Link Purpose (In Context), 4.1.2 Name, Role, Value",
        "publico_afetado": "Cegos e leitores de tela",
    },
    "button-name": {
        "issue_tipo_normalizado": "controle_sem_nome_acessivel",
        "titulo_tecnico": "Botões ou controles sem nome acessível",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "label": {
        "issue_tipo_normalizado": "formulario_sem_rotulo",
        "titulo_tecnico": "Elementos de formulário sem rótulo associado",
        "wcag_criterio": "1.3.1 Info and Relationships, 3.3.2 Labels or Instructions",
        "publico_afetado": "Leitores de tela",
    },
    "html-has-lang": {
        "issue_tipo_normalizado": "idioma_documento_ausente",
        "titulo_tecnico": "Idioma do documento não declarado",
        "wcag_criterio": "3.1.1 Language of Page",
        "publico_afetado": "Cegos e leitores de tela",
    },
    "document-title": {
        "issue_tipo_normalizado": "titulo_pagina_ausente_ou_vazio",
        "titulo_tecnico": "Título da página ausente ou inadequado",
        "wcag_criterio": "2.4.2 Page Titled",
        "publico_afetado": "Navegação e orientação",
    },
    "color-contrast": {
        "issue_tipo_normalizado": "contraste_insuficiente",
        "titulo_tecnico": "Contraste de cores insuficiente",
        "wcag_criterio": "1.4.3 Contrast (Minimum)",
        "publico_afetado": "Baixa visão",
    },
    "target-size": {
        "issue_tipo_normalizado": "alvo_interacao_pequeno",
        "titulo_tecnico": "Alvo de toque ou clique insuficiente (tamanho ou espaçamento)",
        "wcag_criterio": "2.5.8 Target Size (Minimum)",
        "publico_afetado": "Limitação motora",
    },
    "meta-viewport": {
        "issue_tipo_normalizado": "viewport_meta_problematico",
        "titulo_tecnico": "Meta viewport impede zoom ou acessibilidade móvel",
        "wcag_criterio": "1.4.4 Resize text",
        "publico_afetado": "Baixa visão",
    },
    "duplicate-id-aria": {
        "issue_tipo_normalizado": "id_duplicado_aria",
        "titulo_tecnico": "IDs duplicados afetando ARIA ou rótulos",
        "wcag_criterio": "4.1.1 Parsing (4.1.2 em WCAG 2.2)",
        "publico_afetado": "Leitores de tela",
    },
    "heading-order": {
        "issue_tipo_normalizado": "hierarquia_titulos_incorreta",
        "titulo_tecnico": "Ordem ou níveis de cabeçalhos incorretos",
        "wcag_criterio": "1.3.1 Info and Relationships, 2.4.6 Headings and Labels",
        "publico_afetado": "Navegação por estrutura e leitores de tela",
    },
    "empty-heading": {
        "issue_tipo_normalizado": "heading_sem_conteudo",
        "titulo_tecnico": "Cabeçalho sem texto",
        "wcag_criterio": "1.3.1 Info and Relationships, 2.4.6 Headings and Labels",
        "publico_afetado": "Navegação por estrutura e leitores de tela",
    },
    "html-xml-lang-mismatch": {
        "issue_tipo_normalizado": "idioma_html_xml_inconsistente",
        "titulo_tecnico": "Atributos de idioma inconsistentes",
        "wcag_criterio": "3.1.1 Language of Page",
        "publico_afetado": "Leitores de tela",
    },
    "valid-lang": {
        "issue_tipo_normalizado": "codigo_idioma_invalido",
        "titulo_tecnico": "Código de idioma inválido",
        "wcag_criterio": "3.1.1 Language of Page",
        "publico_afetado": "Leitores de tela",
    },
    "frame-title": {
        "issue_tipo_normalizado": "iframe_sem_titulo",
        "titulo_tecnico": "Frame ou iframe sem título",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "input-image-alt": {
        "issue_tipo_normalizado": "input_imagem_sem_alt",
        "titulo_tecnico": "Input imagem sem texto alternativo",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Leitores de tela",
    },
    "object-alt": {
        "issue_tipo_normalizado": "objeto_embed_sem_alternativa",
        "titulo_tecnico": "Object/embed sem alternativa em texto",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Leitores de tela",
    },
    "video-caption": {
        "issue_tipo_normalizado": "video_sem_legendas",
        "titulo_tecnico": "Vídeo sem legendas",
        "wcag_criterio": "1.2.2 Captions (Prerecorded)",
        "publico_afetado": "Surdez",
    },
    "audio-caption": {
        "issue_tipo_normalizado": "audio_sem_alternativa",
        "titulo_tecnico": "Áudio sem alternativa equivalente",
        "wcag_criterio": "1.2.1 Audio-only and Video-only",
        "publico_afetado": "Baixa audição",
    },
    "aria-allowed-attr": {
        "issue_tipo_normalizado": "aria_atributo_nao_permitido",
        "titulo_tecnico": "Atributo ARIA não permitido para o papel do elemento",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "aria-required-attr": {
        "issue_tipo_normalizado": "aria_atributo_obrigatorio_ausente",
        "titulo_tecnico": "Atributo ARIA obrigatório ausente",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "aria-valid-attr-value": {
        "issue_tipo_normalizado": "aria_valor_invalido",
        "titulo_tecnico": "Valor de atributo ARIA inválido",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "aria-valid-attr": {
        "issue_tipo_normalizado": "aria_atributo_invalido",
        "titulo_tecnico": "Atributo ARIA inválido",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "aria-roles": {
        "issue_tipo_normalizado": "aria_papel_invalido",
        "titulo_tecnico": "Papel ARIA inválido",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "aria-required-children": {
        "issue_tipo_normalizado": "aria_filhos_obrigatorios_ausentes",
        "titulo_tecnico": "Filhos obrigatórios ausentes para papel ARIA",
        "wcag_criterio": "1.3.1 Info and Relationships",
        "publico_afetado": "Leitores de tela",
    },
    "aria-required-parent": {
        "issue_tipo_normalizado": "aria_pai_obrigatorio_ausente",
        "titulo_tecnico": "Pai obrigatório ausente para papel ARIA",
        "wcag_criterio": "1.3.1 Info and Relationships",
        "publico_afetado": "Leitores de tela",
    },
    # Audits que falharam nos 8 sites e antes caíam no fallback de slug
    "landmark-one-main": {
        "issue_tipo_normalizado": "ausencia_landmark_main",
        "titulo_tecnico": "Ausência do landmark <main>",
        "wcag_criterio": "1.3.6 Identify Purpose (WCAG 2.1 AAA), 1.3.1 Info and Relationships",
        "publico_afetado": "Navegação por teclado e leitores de tela",
    },
    "aria-prohibited-attr": {
        "issue_tipo_normalizado": "aria_atributo_proibido",
        "titulo_tecnico": "Atributo ARIA proibido para o papel do elemento",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "aria-hidden-focus": {
        "issue_tipo_normalizado": "aria_hidden_com_foco",
        "titulo_tecnico": "Elemento aria-hidden=true contém descendentes focalizáveis",
        "wcag_criterio": "4.1.2 Name, Role, Value, 1.3.1 Info and Relationships",
        "publico_afetado": "Navegação por teclado e leitores de tela",
    },
    "list": {
        "issue_tipo_normalizado": "lista_filhos_invalidos",
        "titulo_tecnico": "Lista com elementos filhos inválidos",
        "wcag_criterio": "1.3.1 Info and Relationships",
        "publico_afetado": "Leitores de tela",
    },
    "listitem": {
        "issue_tipo_normalizado": "item_lista_fora_de_lista",
        "titulo_tecnico": "Elemento <li> fora de <ul>, <ol> ou <menu>",
        "wcag_criterio": "1.3.1 Info and Relationships",
        "publico_afetado": "Leitores de tela",
    },
    "link-in-text-block": {
        "issue_tipo_normalizado": "link_distinguivel_somente_por_cor",
        "titulo_tecnico": "Link diferenciado apenas por cor no bloco de texto",
        "wcag_criterio": "1.4.1 Use of Color",
        "publico_afetado": "Daltonismo",
    },
    # Mapeamento preventivo (passam hoje em muitos sites)
    "html-lang-valid": {
        "issue_tipo_normalizado": "idioma_html_invalido",
        "titulo_tecnico": "Valor do atributo [lang] do <html> inválido",
        "wcag_criterio": "3.1.1 Language of Page",
        "publico_afetado": "Leitores de tela",
    },
    "skip-link": {
        "issue_tipo_normalizado": "skip_link_nao_focalizavel",
        "titulo_tecnico": "Link de pulo (skip link) não é focalizável",
        "wcag_criterio": "2.4.1 Bypass Blocks",
        "publico_afetado": "Navegação por teclado",
    },
    "accesskeys": {
        "issue_tipo_normalizado": "accesskey_duplicado",
        "titulo_tecnico": "Valores de [accesskey] duplicados na página",
        "wcag_criterio": "2.1.1 Keyboard",
        "publico_afetado": "Navegação por teclado",
    },
    "tabindex": {
        "issue_tipo_normalizado": "tabindex_positivo",
        "titulo_tecnico": "Elemento com [tabindex] positivo (maior que 0)",
        "wcag_criterio": "2.4.3 Focus Order",
        "publico_afetado": "Navegação por teclado",
    },
    "aria-command-name": {
        "issue_tipo_normalizado": "controle_interativo_sem_nome_aria",
        "titulo_tecnico": "Botão, link ou menuitem sem nome acessível via ARIA",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "aria-conditional-attr": {
        "issue_tipo_normalizado": "aria_atributo_condicional_invalido",
        "titulo_tecnico": "Atributo ARIA condicional usado fora da especificação do role",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "aria-deprecated-role": {
        "issue_tipo_normalizado": "aria_role_obsoleto",
        "titulo_tecnico": "Role ARIA obsoleto em uso",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "aria-hidden-body": {
        "issue_tipo_normalizado": "body_aria_hidden",
        "titulo_tecnico": "Elemento <body> marcado com aria-hidden=true",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    "label-content-name-mismatch": {
        "issue_tipo_normalizado": "rotulo_difere_do_nome_acessivel",
        "titulo_tecnico": "Rótulo visível diferente do nome acessível",
        "wcag_criterio": "2.5.3 Label in Name",
        "publico_afetado": "Controle por voz",
    },
    "select-name": {
        "issue_tipo_normalizado": "campo_select_sem_label",
        "titulo_tecnico": "Campo select sem label",
        "wcag_criterio": "1.3.1 Info and Relationships, 4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
}

# WAVE: (categoria, item_id) -> meta (categoria distingue contrast vs error com mesmo id)
WAVE_NORMALIZATION: dict[tuple[str, str], NormalizedMeta] = {
    ("error", "label_missing"): {
        "issue_tipo_normalizado": "formulario_sem_rotulo",
        "titulo_tecnico": "Rótulo de formulário ausente",
        "wcag_criterio": "1.3.1, 3.3.2",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "link_empty"): {
        "issue_tipo_normalizado": "link_sem_nome_acessivel",
        "titulo_tecnico": "Link vazio",
        "wcag_criterio": "2.4.4, 4.1.2",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "language_missing"): {
        "issue_tipo_normalizado": "idioma_documento_ausente",
        "titulo_tecnico": "Idioma do documento não indicado",
        "wcag_criterio": "3.1.1",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "alt_missing"): {
        "issue_tipo_normalizado": "imagem_sem_texto_alternativo",
        "titulo_tecnico": "Texto alternativo ausente em imagem",
        "wcag_criterio": "1.1.1",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "alt_spacer_missing"): {
        "issue_tipo_normalizado": "imagem_sem_texto_alternativo",
        "titulo_tecnico": "Imagem espaçadora sem alternativa",
        "wcag_criterio": "1.1.1",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "alt_redundant"): {
        "issue_tipo_normalizado": "texto_alternativo_redundante",
        "titulo_tecnico": "Texto alternativo redundante",
        "wcag_criterio": "1.1.1",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "aria_reference_broken"): {
        "issue_tipo_normalizado": "aria_referencia_quebrada",
        "titulo_tecnico": "Referência ARIA quebrada (aria-labelledby / aria-describedby / etc.)",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Cegos e leitores de tela",
    },
    ("contrast", "contrast"): {
        "issue_tipo_normalizado": "contraste_insuficiente",
        "titulo_tecnico": "Contraste muito baixo",
        "wcag_criterio": "1.4.3",
        "publico_afetado": "Baixa visão",
    },
    ("alert", "heading_skipped"): {
        "issue_tipo_normalizado": "hierarquia_titulos_incorreta",
        "titulo_tecnico": "Nível de cabeçalho pulado",
        "wcag_criterio": "1.3.1",
        "publico_afetado": "Navegação por estrutura",
    },
    ("alert", "h1_missing"): {
        "issue_tipo_normalizado": "h1_ausente",
        "titulo_tecnico": "Cabeçalho de nível 1 ausente",
        "wcag_criterio": "1.3.1",
        "publico_afetado": "Orientação na página",
    },
    ("alert", "link_suspicious"): {
        "issue_tipo_normalizado": "texto_link_suspeito",
        "titulo_tecnico": "Texto de link suspeito ou genérico",
        "wcag_criterio": "2.4.4",
        "publico_afetado": "Leitores de tela",
    },
    ("alert", "title_redundant"): {
        "issue_tipo_normalizado": "titulo_redundante",
        "titulo_tecnico": "Título redundante ou pouco útil",
        "wcag_criterio": "2.4.2",
        "publico_afetado": "Orientação",
    },
    ("alert", "label_title"): {
        "issue_tipo_normalizado": "formulario_so_title_sem_label",
        "titulo_tecnico": "Campo só com title, sem label visível associado",
        "wcag_criterio": "3.3.2",
        "publico_afetado": "Leitores de tela",
    },
    ("alert", "accesskey"): {
        "issue_tipo_normalizado": "wave_alert_accesskey",
        "titulo_tecnico": "Accesskey",
        "wcag_criterio": "2.4.1 Bypass Blocks (uso de accesskey pode conflituar com atalhos do sistema)",
        "publico_afetado": "Navegação por teclado e leitores de tela",
    },
    ("alert", "alt_duplicate"): {
        "issue_tipo_normalizado": "wave_alert_alt_duplicate",
        "titulo_tecnico": "Imagem próxima com o mesmo texto alternativo",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Leitores de tela",
    },
    ("alert", "link_redundant"): {
        "issue_tipo_normalizado": "wave_alert_link_redundant",
        "titulo_tecnico": "Link redundante",
        "wcag_criterio": "2.4.4 Link Purpose (In Context)",
        "publico_afetado": "Navegação por teclado e leitores de tela",
    },
    ("alert", "noscript"): {
        "issue_tipo_normalizado": "wave_alert_noscript",
        "titulo_tecnico": "Elemento noscript",
        "wcag_criterio": "1.1.1 (conteúdo equivalente quando JS está desativado, conforme uso)",
        "publico_afetado": "Usuários sem JavaScript",
    },
    ("alert", "text_small"): {
        "issue_tipo_normalizado": "wave_alert_text_small",
        "titulo_tecnico": "Texto muito pequeno",
        "wcag_criterio": "1.4.4 Resize text, 1.4.12 Text Spacing",
        "publico_afetado": "Baixa visão",
    },
    ("alert", "underline"): {
        "issue_tipo_normalizado": "wave_alert_underline",
        "titulo_tecnico": "Sublinhado em texto que não é link",
        "wcag_criterio": "3.2.4 Consistent Identification",
        "publico_afetado": "Baixa visão e daltonismo",
    },
    ("alert", "event_handler"): {
        "issue_tipo_normalizado": "wave_alert_event_handler",
        "titulo_tecnico": "Event handler em elemento não interativo",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Navegação por teclado e leitores de tela",
    },
    # WAVE devolve item_id "table_layout" (não "layout_table")
    ("alert", "table_layout"): {
        "issue_tipo_normalizado": "wave_alert_tabela_layout",
        "titulo_tecnico": "Tabela usada para layout (não para dados)",
        "wcag_criterio": "1.3.2 Meaningful Sequence",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "alt_link_missing"): {
        "issue_tipo_normalizado": "imagem_link_sem_texto_alternativo",
        "titulo_tecnico": "Imagem de link sem texto alternativo",
        "wcag_criterio": "1.1.1 Non-text Content, 2.4.4 Link Purpose (In Context)",
        "publico_afetado": "Cegos e leitores de tela",
    },
    ("alert", "alt_redundant"): {
        "issue_tipo_normalizado": "wave_alert_alt_redundant",
        "titulo_tecnico": "Texto alternativo redundante: mesmo texto de outra imagem próxima",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Leitores de tela",
    },
    ("alert", "alt_long"): {
        "issue_tipo_normalizado": "wave_alert_alt_longo",
        "titulo_tecnico": "Texto alternativo excessivamente longo",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Cegos e leitores de tela",
    },
    ("alert", "alt_suspicious"): {
        "issue_tipo_normalizado": "wave_alert_alt_suspeito",
        "titulo_tecnico": "Texto alternativo suspeito (genérico ou nome de arquivo)",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Cegos e leitores de tela",
    },
    ("alert", "heading_possible"): {
        "issue_tipo_normalizado": "wave_alert_possivel_titulo",
        "titulo_tecnico": "Texto que parece ser um título mas não usa elemento heading",
        "wcag_criterio": "1.3.1 Info and Relationships, 2.4.6 Headings and Labels",
        "publico_afetado": "Navegação por estrutura e leitores de tela",
    },
    ("alert", "fieldset_missing"): {
        "issue_tipo_normalizado": "wave_alert_fieldset_ausente",
        "titulo_tecnico": "Grupo de controles de formulário sem <fieldset>",
        "wcag_criterio": "1.3.1 Info and Relationships, 3.3.2 Labels or Instructions",
        "publico_afetado": "Leitores de tela",
    },
    ("alert", "label_orphaned"): {
        "issue_tipo_normalizado": "wave_alert_label_orfao",
        "titulo_tecnico": "Label de formulário sem controle associado",
        "wcag_criterio": "1.3.1 Info and Relationships, 3.3.2 Labels or Instructions",
        "publico_afetado": "Leitores de tela",
    },
    ("alert", "link_pdf"): {
        "issue_tipo_normalizado": "wave_alert_link_pdf",
        "titulo_tecnico": "Link para documento PDF",
        "wcag_criterio": "2.4.4 Link Purpose (In Context), 3.1.1 Language of Page",
        "publico_afetado": "Cegos e leitores de tela",
    },
    ("alert", "youtube_video"): {
        "issue_tipo_normalizado": "wave_alert_youtube_video",
        "titulo_tecnico": "Vídeo do YouTube incorporado",
        "wcag_criterio": "1.2.2 Captions (Prerecorded), 1.2.3 Audio Description",
        "publico_afetado": "Surdez",
    },
    ("alert", "html5_video_audio"): {
        "issue_tipo_normalizado": "wave_alert_video_audio_html5",
        "titulo_tecnico": "Elemento HTML5 de vídeo ou áudio",
        "wcag_criterio": "1.2.1 Audio-only/Video-only, 1.2.2 Captions, 1.2.3 Audio Description",
        "publico_afetado": "Surdez e baixa visão",
    },
    ("error", "button_empty"): {
        "issue_tipo_normalizado": "botao_completamente_vazio",
        "titulo_tecnico": "Botão completamente vazio",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "heading_empty"): {
        "issue_tipo_normalizado": "heading_sem_conteudo",
        "titulo_tecnico": "Heading sem conteúdo",
        "wcag_criterio": "1.3.1 Info and Relationships",
        "publico_afetado": "Navegação por estrutura e leitores de tela",
    },
    ("error", "label_empty"): {
        "issue_tipo_normalizado": "label_vazio",
        "titulo_tecnico": "Label vazio",
        "wcag_criterio": "1.3.1 Info and Relationships, 3.3.2 Labels or Instructions",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "label_multiple"): {
        "issue_tipo_normalizado": "campo_com_multiplos_labels",
        "titulo_tecnico": "Campo com múltiplos labels",
        "wcag_criterio": "1.3.1 Info and Relationships",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "title_invalid"): {
        "issue_tipo_normalizado": "titulo_pagina_invalido",
        "titulo_tecnico": "Título da página ausente ou inadequado",
        "wcag_criterio": "2.4.2 Page Titled",
        "publico_afetado": "Navegação e orientação",
    },
}


DEFAULT_CORRECAO_BY_TIPO: dict[str, str] = {
    # ── Ativação e controle ──────────────────────────────────────────────────
    "controle_sem_nome_acessivel": (
        "Há botões na página sem texto ou rótulo. Para quem usa leitor de tela, esses botões não existem: "
        "o software não anuncia a função do controle e o usuário não sabe se deve clicar. "
        "O time de produto precisa dar a cada botão um nome acessível que diga claramente o que ele faz, "
        "usando texto visível, aria-label ou aria-labelledby."
    ),
    "link_sem_nome_acessivel": (
        "Há links na página sem nenhum texto. O leitor de tela ou anuncia a URL crua ou pula sem dizer nada: "
        "em ambos os casos, impossível saber para onde o link vai. "
        "O time de produto precisa colocar um texto descritivo em cada um, indicando claramente o destino."
    ),
    "formulario_sem_rotulo": (
        "Campos do formulário estão sem etiqueta. Quem usa leitor de tela chega ao campo e ouve apenas "
        '"campo de texto": sem saber o que deve preencher. '
        "O time de produto precisa vincular um rótulo a cada campo para que o nome do campo "
        "seja anunciado quando o foco chegar nele."
    ),
    "rotulo_difere_do_nome_acessivel": (
        "O texto que o usuário lê no controle é diferente do nome que o código registrou. "
        "Quem usa comando de voz fala o que vê na tela, mas o sistema espera outra palavra: o comando falha em silêncio. "
        "O time de produto precisa alinhar o rótulo visível ao nome interno, sem deixar os dois divergirem."
    ),
    "contraste_insuficiente": (
        "Parte dos textos e botões usa combinações de cor com contraste baixo demais. "
        "Em má iluminação ou para quem tem visão reduzida, esse conteúdo some. "
        "O time de design deve revisar a paleta e garantir contraste mínimo AA antes da próxima publicação."
    ),
    # ── Perda de conteúdo (imagens) ─────────────────────────────────────────
    "imagem_sem_texto_alternativo": (
        "Há imagens com informação útil sem descrição alternativa. Para quem usa leitor de tela, "
        "esse conteúdo simplesmente não chega. "
        "O time de conteúdo e desenvolvimento deve revisar cada imagem e decidir: quando ela transmite informação, "
        "escrever um texto alternativo curto e claro; quando for apenas decorativa, "
        "usar alt vazio para que ela seja ignorada corretamente."
    ),
    "imagem_link_sem_texto_alternativo": (
        "Há links representados apenas por imagem sem texto alternativo que indique o destino. "
        "Para quem usa leitor de tela, ouvir 'imagem, link' sem descrição é o mesmo que uma placa sem texto. "
        "O time de conteúdo e desenvolvimento precisa garantir que cada imagem-link tenha um texto alternativo "
        "que explique a ação ou o destino — não apenas o que a imagem mostra visualmente."
    ),
    "input_imagem_sem_alt": (
        "Há botões de imagem (input type=image) sem texto alternativo. "
        "Para quem usa leitor de tela, esses controles ficam sem nome e a ação associada fica invisível. "
        "O time precisa adicionar um atributo alt que descreva claramente a ação do botão, não apenas a imagem."
    ),
    "objeto_embed_sem_alternativa": (
        "Há objetos incorporados (flash, embed, object) sem conteúdo alternativo em texto. "
        "Quando o objeto não carrega ou não é suportado, o usuário não recebe nenhuma informação equivalente. "
        "O time deve fornecer um equivalente em texto acessível ou substituir o objeto por tecnologia nativa do navegador."
    ),
    # ── Desorientação estrutural ─────────────────────────────────────────────
    "ausencia_landmark_main": (
        "Sem uma região principal bem definida, quem navega por teclado ou leitor de tela perde um dos atalhos "
        "mais importantes para chegar diretamente ao conteúdo central da página. "
        "O time web deve marcar a área de conteúdo principal com um único elemento de região principal "
        "e garantir que eventuais links de atalho apontem para ela."
    ),
    "lista_filhos_invalidos": (
        "Quando uma lista é montada com estrutura semântica incorreta, o leitor de tela deixa de anunciar "
        "corretamente a quantidade, a sequência e a relação entre os itens. "
        "O time web precisa reconstruir a lista usando marcação válida, "
        "preservando a hierarquia do conteúdo — não apenas sua aparência visual."
    ),
    "heading_sem_conteudo": (
        "Há um título na página sem conteúdo textual. Para quem navega pela lista de títulos do leitor de tela, "
        "isso cria uma seção sem nome e quebra a orientação pelo conteúdo. "
        "O time web deve preencher esse heading com texto real e significativo "
        "ou remover a tag de título se ela estiver sendo usada apenas para efeito visual."
    ),
    "hierarquia_titulos_incorreta": (
        "A hierarquia de títulos da página está fora de ordem: há títulos de nível 4 ou 5 sem que antes exista "
        "um nível 1 ou 2. Para quem navega pelo índice de títulos com leitor de tela, a estrutura da página fica incoerente. "
        "O time web precisa reorganizar os títulos em sequência lógica, do mais geral para o mais específico."
    ),
    # ── Família ARIA ─────────────────────────────────────────────────────────
    "aria_atributo_nao_permitido": (
        "Há atributos ARIA aplicados em elementos ou papéis que não os aceitam. "
        "Isso introduz ruído semântico e pode levar tecnologias assistivas a anunciar informação incorreta "
        "ou ignorar o componente. "
        "O time deve remover atributos ARIA inválidos e manter apenas os que forem compatíveis "
        "com o papel e a função real do elemento."
    ),
    "aria_atributo_obrigatorio_ausente": (
        "Há componentes com papel ARIA declarado, mas sem os atributos obrigatórios que definem o estado "
        "ou o valor do elemento. O leitor de tela anuncia o papel sem conseguir descrever o estado atual, "
        "deixando o usuário sem informação para agir. "
        "O time deve adicionar os atributos obrigatórios para cada papel ARIA usado."
    ),
    "aria_valor_invalido": (
        "Atributos ARIA estão presentes, mas com valores que não são aceitos para aquele atributo. "
        "O comportamento do leitor de tela fica imprevisível: pode ignorar o atributo ou interpretar de forma errada. "
        "O time deve corrigir os valores para os aceitos pela especificação ARIA."
    ),
    "aria_atributo_invalido": (
        "Há atributos ARIA usados que não existem na especificação. "
        "Tecnologias assistivas ignoram atributos desconhecidos, tornando o componente menos previsível. "
        "O time deve substituir pelos atributos corretos ou remover os inválidos."
    ),
    "aria_papel_invalido": (
        "Há elementos com role ARIA inválido ou inexistente. O leitor de tela não consegue categorizar "
        "o elemento corretamente, o que compromete navegação e interação. "
        "O time deve substituir por um role válido compatível com a função do elemento "
        "ou remover o atributo quando HTML nativo já oferece a semântica necessária."
    ),
    "aria_filhos_obrigatorios_ausentes": (
        "Alguns componentes usam papéis ARIA que exigem estrutura interna específica, "
        "mas essa hierarquia está incompleta. O leitor de tela reconhece o papel do componente, "
        "mas não encontra as partes necessárias para anunciá-lo corretamente. "
        "O time deve completar a estrutura exigida ou substituir o componente por HTML nativo equivalente, "
        "que já traz semântica correta por padrão."
    ),
    "aria_pai_obrigatorio_ausente": (
        "Alguns elementos com papel ARIA foram colocados fora do elemento pai esperado pela especificação. "
        "O leitor de tela pode anunciar o elemento de forma isolada, sem o contexto necessário para entendê-lo. "
        "O time deve reestruturar o componente para que os elementos filhos estejam dentro do pai correto."
    ),
    # ── Outros ──────────────────────────────────────────────────────────────
    "campo_select_sem_label": (
        "Há campos de seleção sem rótulo associado. "
        "Quem usa leitor de tela chega ao campo e ouve apenas 'caixa de seleção', sem saber o que está escolhendo. "
        "O time de produto precisa vincular um rótulo descritivo a cada campo de seleção."
    ),
    "iframe_sem_titulo": (
        "Há frames ou iframes sem título descritivo. Para quem usa leitor de tela, "
        "entrar num frame sem nome é como abrir uma janela anônima sem saber o que contém. "
        "O time web precisa adicionar um atributo title claro em cada frame, descrevendo seu conteúdo ou função."
    ),
    "idioma_documento_ausente": (
        "O código da página não declara o idioma. O leitor de tela então aplica as regras de pronúncia padrão, "
        "em geral inglês, ao conteúdo em português, produzindo um áudio difícil de entender. "
        "O time web resolve isso com uma linha só no código-fonte."
    ),
    "titulo_pagina_ausente_ou_vazio": (
        "A página não tem título definido ou o título está vazio. "
        "Quem navega entre abas ou usa leitor de tela perde a referência de onde está. "
        "O time web precisa definir um título único e descritivo para cada página."
    ),
}


def _resolve_correcao(meta: NormalizedMeta, fallback_tipo: str = "") -> str:
    explicit = (meta.get("correcao_sugerida") or "").strip()
    if explicit:
        return explicit
    tipo = (meta.get("issue_tipo_normalizado") or fallback_tipo or "").strip()
    if tipo and tipo in DEFAULT_CORRECAO_BY_TIPO:
        return DEFAULT_CORRECAO_BY_TIPO[tipo]
    wcag = (meta.get("wcag_criterio") or "").strip()
    if wcag:
        return (
            f"Esta barreira viola o critério {wcag}. "
            "O time técnico deve revisar os elementos indicados nos seletores do Apêndice Técnico "
            "e corrigir conforme as diretrizes do critério correspondente."
        )
    return (
        "O time técnico deve revisar os elementos indicados no Apêndice Técnico "
        "e corrigir conforme as diretrizes WCAG do critério correspondente."
    )


def normalize_lighthouse_audit(audit_id: str, title: str, description: str) -> NormalizedMeta:
    meta = LIGHTHOUSE_NORMALIZATION.get(audit_id)
    if meta:
        return {
            "issue_tipo_normalizado": meta["issue_tipo_normalizado"],
            "titulo_tecnico": meta.get("titulo_tecnico") or title,
            "wcag_criterio": meta.get("wcag_criterio", ""),
            "publico_afetado": meta.get("publico_afetado", ""),
            "correcao_sugerida": _resolve_correcao(meta),
        }
    slug = f"lighthouse_{audit_id.replace('-', '_')}"
    return {
        "issue_tipo_normalizado": slug,
        "titulo_tecnico": title or audit_id,
        "wcag_criterio": "",
        "publico_afetado": "",
        "correcao_sugerida": _resolve_correcao({}, slug),
    }


def normalize_wave_item(wave_category: str, item_id: str, description: str) -> NormalizedMeta:
    key = (wave_category.lower(), item_id.lower())
    meta = WAVE_NORMALIZATION.get(key)
    if meta:
        return {
            "issue_tipo_normalizado": meta["issue_tipo_normalizado"],
            "titulo_tecnico": meta.get("titulo_tecnico") or description or item_id,
            "wcag_criterio": meta.get("wcag_criterio", ""),
            "publico_afetado": meta.get("publico_afetado", ""),
            "correcao_sugerida": _resolve_correcao(meta),
        }
    slug = f"wave_{wave_category}_{item_id}".lower().replace(" ", "_")
    return {
        "issue_tipo_normalizado": slug,
        "titulo_tecnico": description or item_id,
        "wcag_criterio": "",
        "publico_afetado": "",
        "correcao_sugerida": _resolve_correcao({}, slug),
    }
