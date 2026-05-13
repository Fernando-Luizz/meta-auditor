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
        "publico_afetado": "Cegos e leitores de tela: não conseguem identificar o destino do link",
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
        "publico_afetado": "Leitores de tela e preenchimento de formulários",
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
        "publico_afetado": "Baixa visão e leitura em diferentes condições de luz",
    },
    "target-size": {
        "issue_tipo_normalizado": "alvo_interacao_pequeno",
        "titulo_tecnico": "Alvo de toque ou clique insuficiente (tamanho ou espaçamento)",
        "wcag_criterio": "2.5.8 Target Size (Minimum)",
        "publico_afetado": "Usuários móveis, com tremor motor ou uso com polegar",
    },
    "meta-viewport": {
        "issue_tipo_normalizado": "viewport_meta_problematico",
        "titulo_tecnico": "Meta viewport impede zoom ou acessibilidade móvel",
        "wcag_criterio": "1.4.4 Resize text",
        "publico_afetado": "Usuários móveis e que precisam ampliar conteúdo",
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
        "publico_afetado": "Surdos e usuários em ambientes silenciosos",
    },
    "audio-caption": {
        "issue_tipo_normalizado": "audio_sem_alternativa",
        "titulo_tecnico": "Áudio sem alternativa equivalente",
        "wcag_criterio": "1.2.1 Audio-only and Video-only",
        "publico_afetado": "Surdos e baixa audição",
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
        "publico_afetado": "Usuários de leitores de tela e navegação por teclado que pulam para o conteúdo principal",
    },
    "aria-prohibited-attr": {
        "issue_tipo_normalizado": "aria_atributo_proibido",
        "titulo_tecnico": "Atributo ARIA proibido para o papel do elemento",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Leitores de tela: o atributo proibido pode causar comportamento inesperado",
    },
    "aria-hidden-focus": {
        "issue_tipo_normalizado": "aria_hidden_com_foco",
        "titulo_tecnico": "Elemento aria-hidden=true contém descendentes focalizáveis",
        "wcag_criterio": "4.1.2 Name, Role, Value, 1.3.1 Info and Relationships",
        "publico_afetado": "Navegação por teclado e leitores de tela: foco pode entrar em região oculta",
    },
    "list": {
        "issue_tipo_normalizado": "lista_filhos_invalidos",
        "titulo_tecnico": "Lista com elementos filhos inválidos",
        "wcag_criterio": "1.3.1 Info and Relationships",
        "publico_afetado": "Leitores de tela: a semântica da lista é quebrada",
    },
    "listitem": {
        "issue_tipo_normalizado": "item_lista_fora_de_lista",
        "titulo_tecnico": "Elemento <li> fora de <ul>, <ol> ou <menu>",
        "wcag_criterio": "1.3.1 Info and Relationships",
        "publico_afetado": "Leitores de tela: o item perde a semântica de lista",
    },
    "link-in-text-block": {
        "issue_tipo_normalizado": "link_distinguivel_somente_por_cor",
        "titulo_tecnico": "Link diferenciado apenas por cor no bloco de texto",
        "wcag_criterio": "1.4.1 Use of Color",
        "publico_afetado": "Usuários com daltonismo ou deficiência de percepção de cor",
    },
    # Mapeamento preventivo (passam hoje em muitos sites)
    "html-lang-valid": {
        "issue_tipo_normalizado": "idioma_html_invalido",
        "titulo_tecnico": "Valor do atributo [lang] do <html> inválido",
        "wcag_criterio": "3.1.1 Language of Page",
        "publico_afetado": "Leitores de tela: a pronúncia e o idioma de leitura ficam incorretos",
    },
    "skip-link": {
        "issue_tipo_normalizado": "skip_link_nao_focalizavel",
        "titulo_tecnico": "Link de pulo (skip link) não é focalizável",
        "wcag_criterio": "2.4.1 Bypass Blocks",
        "publico_afetado": "Navegação por teclado: impede pular para o conteúdo principal",
    },
    "accesskeys": {
        "issue_tipo_normalizado": "accesskey_duplicado",
        "titulo_tecnico": "Valores de [accesskey] duplicados na página",
        "wcag_criterio": "2.1.1 Keyboard",
        "publico_afetado": "Navegação por teclado: atalhos entram em conflito",
    },
    "tabindex": {
        "issue_tipo_normalizado": "tabindex_positivo",
        "titulo_tecnico": "Elemento com [tabindex] positivo (maior que 0)",
        "wcag_criterio": "2.4.3 Focus Order",
        "publico_afetado": "Navegação por teclado: altera a ordem de foco esperada",
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
        "publico_afetado": "Leitores de tela: comportamento pode variar por implementação",
    },
    "aria-hidden-body": {
        "issue_tipo_normalizado": "body_aria_hidden",
        "titulo_tecnico": "Elemento <body> marcado com aria-hidden=true",
        "wcag_criterio": "4.1.2 Name, Role, Value",
        "publico_afetado": "Toda a página fica inacessível a leitores de tela",
    },
    "label-content-name-mismatch": {
        "issue_tipo_normalizado": "rotulo_difere_do_nome_acessivel",
        "titulo_tecnico": "Rótulo visível diferente do nome acessível",
        "wcag_criterio": "2.5.3 Label in Name",
        "publico_afetado": "Usuários de controle por voz",
    },
    "select-name": {
        "issue_tipo_normalizado": "campo_select_sem_label",
        "titulo_tecnico": "Campo select sem label",
        "wcag_criterio": "1.3.1 Info and Relationships, 4.1.2 Name, Role, Value",
        "publico_afetado": "Usuários de leitores de tela e formulários",
    },
}

# WAVE: (categoria, item_id) -> meta (categoria distingue contrast vs error com mesmo id)
WAVE_NORMALIZATION: dict[tuple[str, str], NormalizedMeta] = {
    ("error", "label_missing"): {
        "issue_tipo_normalizado": "formulario_sem_rotulo",
        "titulo_tecnico": "Rótulo de formulário ausente",
        "wcag_criterio": "1.3.1, 3.3.2",
        "publico_afetado": "Leitores de tela e formulários",
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
        "publico_afetado": "Usuários de leitores de tela e cognitivo",
    },
    ("alert", "accesskey"): {
        "issue_tipo_normalizado": "wave_alert_accesskey",
        "titulo_tecnico": "Accesskey",
        "wcag_criterio": "2.4.1 Bypass Blocks (uso de accesskey pode conflituar com atalhos do sistema)",
        "publico_afetado": "Usuários de teclado e leitores de tela",
    },
    ("alert", "alt_duplicate"): {
        "issue_tipo_normalizado": "wave_alert_alt_duplicate",
        "titulo_tecnico": "Imagem próxima com o mesmo texto alternativo",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Leitores de tela (diferenciação de conteúdo)",
    },
    ("alert", "link_redundant"): {
        "issue_tipo_normalizado": "wave_alert_link_redundant",
        "titulo_tecnico": "Link redundante",
        "wcag_criterio": "2.4.4 Link Purpose (In Context)",
        "publico_afetado": "Navegação por leitor de tela e teclado",
    },
    ("alert", "noscript"): {
        "issue_tipo_normalizado": "wave_alert_noscript",
        "titulo_tecnico": "Elemento noscript",
        "wcag_criterio": "1.1.1 (conteúdo equivalente quando JS está desativado, conforme uso)",
        "publico_afetado": "Usuários sem JavaScript ou com restrições",
    },
    ("alert", "text_small"): {
        "issue_tipo_normalizado": "wave_alert_text_small",
        "titulo_tecnico": "Texto muito pequeno",
        "wcag_criterio": "1.4.4 Resize text, 1.4.12 Text Spacing",
        "publico_afetado": "Baixa visão e leitura em telas pequenas",
    },
    ("alert", "underline"): {
        "issue_tipo_normalizado": "wave_alert_underline",
        "titulo_tecnico": "Sublinhado em texto que não é link",
        "wcag_criterio": "3.2.4 Consistent Identification",
        "publico_afetado": "Usuários que associam sublinhado a links",
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
        "publico_afetado": "Leitores de tela: tabelas de layout podem confundir a ordem de leitura",
    },
    ("error", "alt_link_missing"): {
        "issue_tipo_normalizado": "imagem_link_sem_texto_alternativo",
        "titulo_tecnico": "Imagem de link sem texto alternativo",
        "wcag_criterio": "1.1.1 Non-text Content, 2.4.4 Link Purpose (In Context)",
        "publico_afetado": "Cegos: não conseguem determinar o destino do link",
    },
    ("alert", "alt_redundant"): {
        "issue_tipo_normalizado": "wave_alert_alt_redundant",
        "titulo_tecnico": "Texto alternativo redundante: mesmo texto de outra imagem próxima",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Leitores de tela: conteúdo repetido sem diferenciação",
    },
    ("alert", "alt_long"): {
        "issue_tipo_normalizado": "wave_alert_alt_longo",
        "titulo_tecnico": "Texto alternativo excessivamente longo",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Cegos: alt longo causa ruído na leitura; prefer aria-describedby",
    },
    ("alert", "alt_suspicious"): {
        "issue_tipo_normalizado": "wave_alert_alt_suspeito",
        "titulo_tecnico": "Texto alternativo suspeito (genérico ou nome de arquivo)",
        "wcag_criterio": "1.1.1 Non-text Content",
        "publico_afetado": "Cegos: descrição não comunica o conteúdo real da imagem",
    },
    ("alert", "heading_possible"): {
        "issue_tipo_normalizado": "wave_alert_possivel_titulo",
        "titulo_tecnico": "Texto que parece ser um título mas não usa elemento heading",
        "wcag_criterio": "1.3.1 Info and Relationships, 2.4.6 Headings and Labels",
        "publico_afetado": "Leitores de tela e navegação por estrutura: perde-se na hierarquia",
    },
    ("alert", "fieldset_missing"): {
        "issue_tipo_normalizado": "wave_alert_fieldset_ausente",
        "titulo_tecnico": "Grupo de controles de formulário sem <fieldset>",
        "wcag_criterio": "1.3.1 Info and Relationships, 3.3.2 Labels or Instructions",
        "publico_afetado": "Leitores de tela: controles relacionados não são agrupados semanticamente",
    },
    ("alert", "label_orphaned"): {
        "issue_tipo_normalizado": "wave_alert_label_orfao",
        "titulo_tecnico": "Label de formulário sem controle associado",
        "wcag_criterio": "1.3.1 Info and Relationships, 3.3.2 Labels or Instructions",
        "publico_afetado": "Leitores de tela: label existe mas não aponta para nenhum campo",
    },
    ("alert", "link_pdf"): {
        "issue_tipo_normalizado": "wave_alert_link_pdf",
        "titulo_tecnico": "Link para documento PDF",
        "wcag_criterio": "2.4.4 Link Purpose (In Context), 3.1.1 Language of Page",
        "publico_afetado": "Cegos e leitores de tela: PDF pode ter marcação inacessível",
    },
    ("alert", "youtube_video"): {
        "issue_tipo_normalizado": "wave_alert_youtube_video",
        "titulo_tecnico": "Vídeo do YouTube incorporado",
        "wcag_criterio": "1.2.2 Captions (Prerecorded), 1.2.3 Audio Description",
        "publico_afetado": "Surdos: verificar se legendas automáticas estão ativas e corretas",
    },
    ("alert", "html5_video_audio"): {
        "issue_tipo_normalizado": "wave_alert_video_audio_html5",
        "titulo_tecnico": "Elemento HTML5 de vídeo ou áudio",
        "wcag_criterio": "1.2.1 Audio-only/Video-only, 1.2.2 Captions, 1.2.3 Audio Description",
        "publico_afetado": "Surdos e deficientes visuais: verificar alternativas e legendas",
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
        "publico_afetado": "Leitores de tela e preenchimento de formulários",
    },
    ("error", "label_multiple"): {
        "issue_tipo_normalizado": "campo_com_multiplos_labels",
        "titulo_tecnico": "Campo com múltiplos labels",
        "wcag_criterio": "1.3.1 Info and Relationships",
        "publico_afetado": "Leitores de tela",
    },
    ("error", "title_invalid"): {
        "issue_tipo_normalizado": "title_invalido",
        "titulo_tecnico": "Atributo title inválido",
        "wcag_criterio": "3.1.1 Language of Page",
        "publico_afetado": "Leitores de tela",
    },
}


DEFAULT_CORRECAO_BY_TIPO: dict[str, str] = {
    "controle_sem_nome_acessivel": "Adicionar atributo aria-label ou texto visível ao botão/controle.",
    "contraste_insuficiente": "Aumentar contraste para razão mínima de 4,5:1 (texto normal) ou 3:1 (texto grande).",
    "imagem_sem_texto_alternativo": "Adicionar atributo alt descritivo. Para imagens decorativas usar alt=\"\".",
    "imagem_link_sem_texto_alternativo": (
        "Adicione alt descritivo à imagem dentro do link. "
        "O alt deve indicar o destino do link, não apenas o conteúdo visual. "
        "Exemplo: <img src='banner.jpg' alt='Acesse a página de inscrição'>. "
        "O atributo alt é obrigatório mesmo quando vazio."
    ),
    "link_sem_nome_acessivel": (
        "Adicione texto descritivo dentro do <a> ou use aria-label com o destino ou ação. "
        "Links com apenas ícone ou imagem sem alt são invisíveis para leitores de tela. "
        "Exemplo: <a href='/sobre' aria-label='Conheça nossa equipe'>...</a>."
    ),
    "formulario_sem_rotulo": "Associar campo a um <label for='id'> ou usar aria-label/aria-labelledby.",
    "campo_select_sem_label": "Adicionar label associado ao select ou aria-label descrevendo o campo.",
    "rotulo_difere_do_nome_acessivel": "Garantir que o nome acessível contenha o texto visível do controle (Label in Name).",
    "iframe_sem_titulo": "Adicionar atributo title descritivo em todo iframe/frame.",
    "idioma_documento_ausente": "Definir atributo lang no elemento <html>, por exemplo lang='pt-BR'.",
    "titulo_pagina_ausente_ou_vazio": "Definir um <title> único e descritivo para cada página.",
}


def _resolve_correcao(meta: NormalizedMeta, fallback_tipo: str = "") -> str:
    explicit = (meta.get("correcao_sugerida") or "").strip()
    if explicit:
        return explicit
    tipo = (meta.get("issue_tipo_normalizado") or fallback_tipo or "").strip()
    if tipo and tipo in DEFAULT_CORRECAO_BY_TIPO:
        return DEFAULT_CORRECAO_BY_TIPO[tipo]
    return "Corrigir o elemento conforme o critério WCAG indicado e validar novamente com Lighthouse/WAVE."


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
