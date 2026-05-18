from __future__ import annotations

import asyncio
import json
import logging
import re
from urllib.parse import urlparse

import httpx

from app.config import AI_ANTHROPIC_CONCURRENCY, AI_ANTHROPIC_REQUEST_TIMEOUT
from app.services.text_clean import (
    normalize_barrier_ai_texts,
    normalize_executive_plaintext,
    normalize_html_breaks,
)

_log = logging.getLogger("uvicorn.error")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
REQUEST_TIMEOUT = AI_ANTHROPIC_REQUEST_TIMEOUT
# Nível 2 dividido: dev (com seletores) + ticket (contexto curto) — evita truncamento.
NIVEL2_DEV_MAX_TOKENS = 700
NIVEL2_DEV_REPAIR_MAX_TOKENS = 400
NIVEL2_TICKET_MAX_TOKENS = 600
NIVEL2_TICKET_REPAIR_MAX_TOKENS = 350

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


def _iter_json_objects(text: str):
    """Yield each balanced {...} block found in text, in order of appearance.

    Counts brace depth so nested objects are captured correctly.
    Yields the first complete block, then continues scanning for more —
    caller can stop at the first successful parse.
    """
    depth = 0
    start: int | None = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    yield text[start : i + 1]
                    start = None


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    # Strip markdown fences
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence) :]
            if "```" in text:
                text = text[: text.rfind("```")]
            break
    text = text.strip()
    # Direct parse (happy path — covers prefill responses that start with "{")
    try:
        return json.loads(text)
    except Exception:
        pass
    # Fallback: try each balanced {...} block in the response in order.
    # Stops at the first one that parses successfully — handles preamble text,
    # stray braces like {x}, and multiple JSON blocks without capturing too much.
    for candidate in _iter_json_objects(text):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return {}


def _normalize_pt_text(text: str) -> str:
    """Normaliza pontuação, espaços e quebras de linha em textos executivos."""
    return normalize_executive_plaintext(text)


def _strip_br_literals(s: str) -> str:
    """Converte marcas <br> (incl. entidades escapadas) em quebras antes da normalização completa."""
    return normalize_html_breaks(s)


def _nivel2_ticket_normalized(parsed2: dict) -> tuple[str, dict]:
    """Extrai versao_dev e texto_ticket com chaves canónicas e texto normalizado."""
    tk = parsed2.get("texto_ticket", {})
    if not isinstance(tk, dict):
        tk = {}
    return (
        _normalize_pt_text(parsed2.get("versao_dev", "")),
        {
            "titulo": _normalize_pt_text(tk.get("titulo", "")),
            "descricao": _normalize_pt_text(tk.get("descricao", "")),
            "criterio_de_pronto": _normalize_pt_text(_strip_br_literals(str(tk.get("criterio_de_pronto", "")))),
        },
    )


async def _call_claude(prompt: str, api_key: str, max_tokens: int = 900, prefill: str = "") -> str:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    messages: list[dict] = [{"role": "user", "content": prompt}]
    if prefill:
        # Assistant prefill: forces the model to continue from this token,
        # guaranteeing the output begins with the prefill string.
        messages.append({"role": "assistant", "content": prefill})
    body = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "temperature": 0,  # Saída JSON — máxima estabilidade, mínima variação
        "messages": messages,
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(ANTHROPIC_API_URL, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
            # When prefill is used the API returns only what follows it — prepend it back.
            return (prefill + text) if prefill else text
    except Exception as exc:
        _log.warning("ai_enhancer: chamada Claude falhou — %s", exc)
        return ""


# Ação gerencial específica por tipo — evita frases genéricas de "confirmar correção".
_ACAO_GERENCIAL_POR_TIPO: dict[str, str] = {
    "contraste_insuficiente": (
        "Encaminhar para o time de design e solicitar revisão completa das cores e do contraste de textos e botões."
    ),
    "link_distinguivel_somente_por_cor": (
        "Encaminhar para o time de design e solicitar que links no texto tenham indicação além da cor."
    ),
    "formulario_sem_rotulo": (
        "Encaminhar para o time web e solicitar revisão de todos os campos de formulário e seus rótulos."
    ),
    "formulario_so_title_sem_label": (
        "Encaminhar para o time web e solicitar rótulos visíveis em todos os campos que só têm title."
    ),
    "campo_select_sem_label": (
        "Encaminhar para o time web e solicitar rótulos descritivos em todos os campos de seleção."
    ),
    "link_sem_nome_acessivel": (
        "Encaminhar para o time web e solicitar revisão de todos os links sem texto descritivo."
    ),
    "controle_sem_nome_acessivel": (
        "Encaminhar para o time web e solicitar revisão de botões e controles sem nome acessível."
    ),
    "controle_interativo_sem_nome_aria": (
        "Encaminhar para o time web e solicitar nomes acessíveis em todos os controles interativos."
    ),
    "botao_completamente_vazio": (
        "Encaminhar para o time web e solicitar texto ou rótulo em todos os botões vazios."
    ),
    "imagem_sem_texto_alternativo": (
        "Encaminhar para o time de conteúdo e solicitar revisão das descrições alternativas de imagens."
    ),
    "imagem_link_sem_texto_alternativo": (
        "Encaminhar para o time de conteúdo e solicitar revisão das imagens usadas como links."
    ),
    "input_imagem_sem_alt": (
        "Encaminhar para o time web e solicitar texto alternativo em todos os botões de imagem."
    ),
    "hierarquia_titulos_incorreta": (
        "Incluir no planejamento e solicitar ao time web a reorganização dos títulos das páginas."
    ),
    "heading_sem_conteudo": (
        "Encaminhar para o time web e solicitar correção dos títulos vazios na página."
    ),
    "h1_ausente": (
        "Encaminhar para o time web e solicitar um título principal em cada página."
    ),
    "alvo_interacao_pequeno": (
        "Encaminhar para o time de produto e solicitar aumento das áreas de toque e clique."
    ),
    "skip_link_nao_focalizavel": (
        "Encaminhar para o time web e solicitar correção do link de pular para o conteúdo principal."
    ),
    "ausencia_landmark_main": (
        "Encaminhar para o time web e solicitar marcação da região principal de conteúdo."
    ),
    "idioma_documento_ausente": (
        "Encaminhar para o time web e solicitar declaração do idioma da página."
    ),
    "idioma_html_invalido": (
        "Encaminhar para o time web e solicitar correção do código de idioma da página."
    ),
    "titulo_pagina_ausente_ou_vazio": (
        "Encaminhar para o time web e solicitar títulos descritivos em todas as páginas."
    ),
    "viewport_meta_problematico": (
        "Encaminhar para o time web e solicitar permissão de zoom no site mobile."
    ),
    "video_sem_legendas": (
        "Encaminhar para o time de conteúdo e solicitar legendas em todos os vídeos."
    ),
    "audio_sem_alternativa": (
        "Encaminhar para o time de conteúdo e solicitar alternativa em texto para conteúdos de áudio."
    ),
    "rotulo_difere_do_nome_acessivel": (
        "Encaminhar para o time de produto e solicitar alinhamento entre texto visível e nome acessível dos controles."
    ),
    "body_aria_hidden": (
        "Encaminhar para o time web como prioridade alta e solicitar remoção do bloqueio de leitura da página."
    ),
    "lista_filhos_invalidos": (
        "Encaminhar para o time web e solicitar correção da marcação de listas na página."
    ),
    "item_lista_fora_de_lista": (
        "Encaminhar para o time web e solicitar que itens de lista fiquem dentro de ul, ol ou menu."
    ),
}


def _acao_gerencial_hint(barrier: dict) -> str:
    """Frase-modelo de ação gerencial amarrada ao tipo da barreira."""
    tipo = str(barrier.get("issue_tipo_normalizado") or "").strip().lower()
    if tipo in _ACAO_GERENCIAL_POR_TIPO:
        return _ACAO_GERENCIAL_POR_TIPO[tipo]
    if "contraste" in tipo:
        return _ACAO_GERENCIAL_POR_TIPO["contraste_insuficiente"]
    if "formulario" in tipo or "rotulo" in tipo or "label" in tipo or "fieldset" in tipo:
        return _ACAO_GERENCIAL_POR_TIPO["formulario_sem_rotulo"]
    if "imagem" in tipo or "alt" in tipo or "objeto_embed" in tipo:
        return _ACAO_GERENCIAL_POR_TIPO["imagem_sem_texto_alternativo"]
    if "link" in tipo:
        return _ACAO_GERENCIAL_POR_TIPO["link_sem_nome_acessivel"]
    if "heading" in tipo or "titulo" in tipo or "hierarquia" in tipo or "h1" in tipo:
        return _ACAO_GERENCIAL_POR_TIPO["hierarquia_titulos_incorreta"]
    if "aria" in tipo:
        return "Encaminhar para o time web e solicitar correção dos atributos e papéis ARIA indicados."
    if any(k in tipo for k in ("teclado", "tabindex", "accesskey", "skip", "foco", "landmark")):
        return _ACAO_GERENCIAL_POR_TIPO["skip_link_nao_focalizavel"]
    if "video" in tipo or "audio" in tipo or "legenda" in tipo:
        return _ACAO_GERENCIAL_POR_TIPO["video_sem_legendas"]
    if "idioma" in tipo or "lang" in tipo:
        return _ACAO_GERENCIAL_POR_TIPO["idioma_documento_ausente"]
    if "viewport" in tipo or "zoom" in tipo:
        return _ACAO_GERENCIAL_POR_TIPO["viewport_meta_problematico"]
    if "controle" in tipo or "botao" in tipo or "button" in tipo:
        return _ACAO_GERENCIAL_POR_TIPO["controle_sem_nome_acessivel"]
    return (
        "Encaminhar para o time web e solicitar correção do problema descrito no contexto acima, "
        "sem usar apenas confirmação genérica."
    )


def _context_block(barrier: dict) -> str:
    sels = _selectors(barrier)
    sel_txt = "\n".join(f"  • {s}" for s in sels) if sels else "  (não disponíveis)"
    prio_map = {
        "alta": "ALTA: corrigir com urgência",
        "media": "MÉDIA: planejar correção",
        "baixa": "BAIXA: melhorar oportunisticamente",
        "revisao_manual": "REQUER REVISÃO MANUAL",
    }
    ferr_map = {
        "automatico_convergente": "Lighthouse + WAVE (confirmado por ambas)",
        "automatico_detectado": "Lighthouse ou WAVE (ferramenta única)",
    }
    # Remove contagens do texto de correcao_sugerida para a IA não repetir counts de uma
    # ferramenta só (ex.: Lighthouse 37 vs consolidado 48). O número oficial está em Ocorrências.
    correcao_raw = barrier.get("correcao_sugerida") or "(sem texto base)"
    correcao_sem_count = re.sub(
        r"\b\d+\s*(elementos?|itens?|ocorrências?|instances?|items?\s+affected)",
        "N elementos",
        correcao_raw,
        flags=re.IGNORECASE,
    )
    return (
        "CONTEXTO DETERMINÍSTICO (fonte de verdade: não alterar):\n"
        f"  Tipo normalizado  : {barrier.get('issue_tipo_normalizado', '—')}\n"
        f"  Título técnico    : {barrier.get('titulo_tecnico', '—')}\n"
        f"  Critério WCAG     : {barrier.get('wcag_criterio', '—')}\n"
        f"  Público afetado   : {barrier.get('publico_afetado', '—')}\n"
        f"  Prioridade        : {prio_map.get(barrier.get('prioridade', ''), barrier.get('prioridade', '—'))}\n"
        f"  Ferramenta origem : {ferr_map.get(barrier.get('status_deteccao', ''), barrier.get('status_deteccao', '—'))}\n"
        f"  Ocorrências       : {_safe_int(barrier.get('ocorrencias_count'), 0)} elemento(s) afetado(s)\n"
        f"  Como corrigir base: {correcao_sem_count}\n"
        f"  Seletores CSS     :\n{sel_txt}"
    )


def _prompt_nivel1(barrier: dict) -> str:
    prio_map = {
        "alta": "ALTA: corrigir com urgência",
        "media": "MÉDIA: planejar na próxima entrega",
        "baixa": "BAIXA: melhorar quando possível",
    }
    prio_label = prio_map.get(barrier.get("prioridade", ""), "NÃO DEFINIDA")
    acao_hint = _acao_gerencial_hint(barrier)
    return (
        "Você é especialista em acessibilidade web e comunicação executiva.\n\n"
        + _context_block(barrier)
        + f"\n  Prioridade traduzida : {prio_label}\n"
        + f"\n  Ação gerencial esperada (use como base — mantenha a ação específica, ajuste só urgência/time):\n  {acao_hint}\n"
        + """\n\nCom base APENAS no contexto acima, gere 4 campos de comunicação.
NÃO invente dados. NÃO altere severidade. NÃO afirme conformidade legal.

REGRAS ABSOLUTAS DE ESCRITA:
1. Português do Brasil direto. Sem enrolação.
2. PROIBIDO: travessões (—), reticências (...), ponto-e-vírgula excessivo.
3. PROIBIDO: "é importante notar", "vale ressaltar", "cabe destacar", "é fundamental", "neste sentido", "portanto", "dessa forma", "desta forma", "assim sendo", "impossibilitando", "possibilitando", "proporcionando", "tecnologias assistivas", "interfaces alternativas".
4. PROIBIDO em justificativa_gerencial e acao_gerencial: IDs de critérios WCAG (ex: 1.4.3, 2.5.8), siglas técnicas (HTML, CSS, ARIA, DOM), nomes de ferramentas (Lighthouse, WAVE), números de pixels ou proporções de contraste.
5. PROIBIDO em como_corrigir_claro e acao_gerencial: nomes de atributos HTML/CSS/ARIA, seletores CSS, código, siglas técnicas.
6. PROIBIDO em qualquer campo: mencionar número exato de ocorrências ou elementos afetados — esses dados já aparecem nos campos técnicos do relatório.
7. PROIBIDO em qualquer campo: "Utilizadores" — use sempre "Usuários" (português do Brasil).
8. PROIBIDO em qualquer campo: afirmar impacto financeiro ou de negócio não demonstrado pela auditoria.
   Exemplos proibidos: "reduz conversão", "causa abandono de carrinho", "prejudica receita", "impacto nas vendas", "risco legal crescente", "exposição jurídica".
   A auditoria detecta barreiras técnicas de acessibilidade — não realiza análise de negócio nem estima consequências financeiras.
   Explique apenas quem é excluído e por que a correção é importante — sem prometer ou projetar resultados.

INSTRUÇÕES POR CAMPO:

justificativa_gerencial (1-2 frases):
  Audiência: gestor ou diretor. Por que esta barreira tem esta prioridade?
  Responda em termos de: quais usuários são excluídos + por que isso é grave na experiência (sem alegações financeiras ou jurídicas).
  Exemplo bom: "Usuários com baixa visão não conseguem ler textos e botões do site, impedindo que completem compras. Por ser um problema frequente e de alto impacto, a correção deve ser tratada com urgência."
  Exemplo ruim: "A barreira WCAG 1.4.3 afeta 37 elementos com contraste insuficiente."

explicacao_usuario (2-3 frases):
  Audiência: qualquer pessoa, inclusive quem nunca pensou em acessibilidade.
  Descreva a experiência real de quem tem a deficiência indicada. Use analogia do cotidiano.
  Exemplo: "Quem tem baixa visão precisa de muito contraste para enxergar textos. Quando as cores do site são parecidas com o fundo, é como tentar ler uma carta escrita a lápis fraco num papel amarelado."

como_corrigir_claro (1-3 frases):
  Audiência: product owner ou gerente de produto.
  Descreva O QUÊ precisa mudar pelo comportamento que o usuário vai ver, não pelo código.
  Exemplo bom: "Os textos e botões do cabeçalho precisam ter cores que contrastem claramente com o fundo, para que qualquer pessoa consiga lê-los mesmo com pouca luz ou visão reduzida."
  Exemplo ruim: "Adicione aria-label ao elemento <button> e ajuste color:#333 no CSS."

acao_gerencial (1 frase curta):
  Audiência: gestor. O que ele deve fazer com essa informação agora.
  Verbo de gestão no infinitivo. Máximo 18 palavras.
  PROIBIDO absolutamente:
    - Prazos ou tempo específico ("48 horas", "3 dias", "semana que vem", "até sexta")
    - Ferramentas ("Lighthouse", "WAVE", "axe", qualquer nome de software)
    - Referências a testes ou dispositivos ("teste em dispositivo real", "teste no navegador")
    - Termos técnicos ("deploy", "seletores", "validar com ferramenta", "revalidação com ferramenta")
  Use verbos de gestão: encaminhar, incluir no planejamento, agendar revisão, priorizar, solicitar.
  IMPORTANTE: a frase deve especificar O QUE o time deve fazer, não só "confirmar a correção".
  Use o campo "Ação gerencial esperada" do contexto como ponto de partida — preserve a ação concreta.
  Exemplos bons — note como cada um nomeia a ação específica:
    Contraste: "Encaminhar para o time de design e solicitar revisão completa das cores do site."
    Formulário sem rótulo: "Encaminhar para o time web e solicitar revisão de todos os campos de formulário."
    Imagem sem alt: "Encaminhar para o time de conteúdo e solicitar revisão das descrições de imagens."
    Hierarquia de títulos: "Incluir no planejamento e solicitar ao time web a reorganização dos títulos das páginas."
    Link sem nome: "Encaminhar para o time web como prioridade alta e solicitar revisão de todos os links sem texto."
  Exemplo ruim: "Encaminhar para o time web e solicitar confirmação após a correção." — genérico demais, não diz o que fazer.
  Exemplo ruim: "Solicitar revalidação com ferramenta de acessibilidade após o deploy."
  Exemplo ruim: "Pedir confirmação da correção dentro de 48 horas."
  Exemplo ruim: "Encaminhar e solicitar confirmação após a correção ser implementada."

Responda SOMENTE com JSON válido, sem markdown:

{
  "justificativa_gerencial": "...",
  "explicacao_usuario": "...",
  "como_corrigir_claro": "...",
  "acao_gerencial": "..."
}"""
    )


def _prompt_nivel2_dev(barrier: dict) -> str:
    """Prompt A do nível 2: gera apenas versao_dev (instrução técnica para o dev)."""
    return (
        "Você é especialista em acessibilidade web.\n\n"
        + _context_block(barrier)
        + """\n\nCom base APENAS no contexto acima, escreva uma instrução técnica para o desenvolvedor.
NÃO invente dados. NÃO altere critério WCAG.

REGRA DE CONTAGEM: use o número do campo "Ocorrências" — nunca números do campo "Como corrigir base".

versao_dev:
  Instrução técnica direta. Inclua: o que está errado + onde está + como corrigir + exemplo antes/depois.
  Seja preciso com atributos, seletores e valores.
  Escreva em português do Brasil. NÃO use travessões (—).

Responda SOMENTE com JSON válido, sem markdown:

{"versao_dev": "..."}"""
    )


def _prompt_nivel2_ticket(barrier: dict) -> str:
    """Prompt B do nível 2: gera apenas texto_ticket — contexto sem seletores CSS longos."""
    prio_map = {
        "alta": "ALTA — corrigir com urgência",
        "media": "MÉDIA — planejar na próxima entrega",
        "baixa": "BAIXA — melhorar quando possível",
    }
    ctx = (
        "CONTEXTO (fonte de verdade):\n"
        f"  Tipo normalizado : {barrier.get('issue_tipo_normalizado', '—')}\n"
        f"  Título técnico   : {barrier.get('titulo_tecnico', '—')}\n"
        f"  Critério WCAG    : {barrier.get('wcag_criterio', '—')}\n"
        f"  Público afetado  : {barrier.get('publico_afetado', '—')}\n"
        f"  Prioridade       : {prio_map.get(barrier.get('prioridade', ''), '—')}\n"
        f"  Ocorrências      : {_safe_int(barrier.get('ocorrencias_count'), 0)} elemento(s)\n"
    )
    return (
        "Você é especialista em acessibilidade web e gestão de backlog ágil.\n\n"
        + ctx
        + """\n\nCom base APENAS no contexto acima, crie um ticket de backlog para a equipe.
NÃO invente dados técnicos. NÃO altere critério WCAG.

texto_ticket.titulo:
  Máximo 80 caracteres. Formato: verbo no infinitivo + problema + contexto.

texto_ticket.descricao:
  3-4 frases: o que foi detectado + quem é afetado + critério WCAG violado + impacto funcional.

texto_ticket.criterio_de_pronto:
  2-3 itens verificáveis, separados por \\n. Cada item começa com verbo.

Responda SOMENTE com JSON válido, sem markdown:

{"texto_ticket": {"titulo": "...", "descricao": "...", "criterio_de_pronto": "..."}}"""
    )


def _prompt_executive(
    barriers: list[dict],
    domain: str,
    lh_score: float | None,
    wave_score: float | None,
    score_risco: dict | None,
) -> str:
    _ = lh_score  # Lighthouse omitido do prompt executivo (evita jargão "estrutura técnica")

    alta = [b for b in barriers if b.get("prioridade") == "alta"]
    media = [b for b in barriers if b.get("prioridade") == "media"]

    if wave_score is not None:
        wv_qual = (
            "boa"
            if wave_score >= 7
            else "com problemas importantes"
            if wave_score >= 4
            else "crítica"
        )
    else:
        wv_qual = "não disponível"

    risco_nivel = "—"
    if isinstance(score_risco, dict):
        risco_nivel = score_risco.get("nivel", "—")

    publicos_raw: list[str] = []
    for b in barriers:
        pub = b.get("publico_afetado") or ""
        if pub:
            publicos_raw.append(pub.strip())
    publicos_unicos = list(dict.fromkeys(publicos_raw))
    publicos_txt = "\n".join(f"  • {p}" for p in publicos_unicos) if publicos_unicos else "  • usuários com deficiência"

    def _barrier_line(b: dict) -> str:
        pub = b.get("publico_afetado") or "usuários com deficiência"
        prio = b.get("prioridade", "")
        tipo = b.get("issue_tipo_normalizado") or b.get("titulo_tecnico") or "barreira não nomeada"
        urgencia = "URGENTE" if prio == "alta" else "IMPORTANTE" if prio == "media" else "OPCIONAL"
        return f"  • [{urgencia}] {tipo}: afeta {pub}"

    lista = "\n".join(_barrier_line(b) for b in barriers)
    n_alta, n_media = len(alta), len(media)
    total = len(barriers)

    def _plural(n: int, singular: str, plural: str) -> str:
        return singular if n == 1 else plural

    b_word = _plural(total, "barreira", "barreiras")
    a_desc = f"{n_alta} de alta prioridade" if n_alta > 0 else ""
    m_desc = f"{n_media} de média prioridade" if n_media > 0 else ""
    prio_parts = [p for p in [a_desc, m_desc] if p]
    prio_str = " e ".join(prio_parts) if prio_parts else ""

    if prio_str:
        contagem = f"{total} {b_word} de acessibilidade, sendo {prio_str}"
    else:
        contagem = f"{total} {b_word} de acessibilidade"

    u_word = _plural(n_alta, "urgente", "urgentes")
    i_word = _plural(n_media, "importante", "importantes")
    totais_prioridade = f"{n_alta} {u_word}, {n_media} {i_word}"

    situacao = (
        "crítica"
        if risco_nivel in ("ALTO", "alto")
        else "de atenção"
        if risco_nivel in ("MÉDIO", "medio")
        else "controlada"
    )

    return (
        "Você é consultor sênior de acessibilidade digital. Escreva um resumo executivo para um diretor ou gerente geral.\n\n"
        "DADOS DA AUDITORIA (use APENAS estes dados — não invente nem extrapole):\n"
        f"  Portal                           : {domain}\n"
        f"  Qualidade da experiência do usuário: {wv_qual}\n"
        f"  Situação geral                   : {situacao}\n"
        f"  Total de barreiras               : {total} ({totais_prioridade})\n"
        f"  Barreiras encontradas:\n{lista}\n\n"
        f"  PÚBLICOS AFETADOS (use SOMENTE estes — não adicione outros):\n{publicos_txt}\n\n"
        "REGRAS ABSOLUTAS (violá-las invalida a resposta):\n"
        "1. NUNCA mencione scores, índices ou números técnicos (ex: 90/100, 1.7, 2.8/3).\n"
        "2. NUNCA mencione pixels, HTML, CSS, ARIA, atributos, seletores ou nomes de ferramentas.\n"
        "3. NUNCA use linguagem de sprint, release, estimativa de horas ou prazos específicos.\n"
        "4. NUNCA faça projeção de score futuro.\n"
        "5. NUNCA mencione IDs de critérios WCAG (ex: 1.4.3, 2.5.8).\n"
        "6. NUNCA use: 'Utilizadores' — escreva sempre 'Usuários'.\n"
        "7. NUNCA use: travessões (—), 'é importante notar', 'vale ressaltar', 'dessa forma', 'desta forma', 'assim sendo', 'impossibilitando', 'possibilitando', 'tecnologias assistivas'.\n"
        "8. NUNCA mencione deficiências ou públicos fora da lista acima. A lista é completa e fechada.\n"
        "   Use os rótulos EXATAMENTE como aparecem na lista — sem adicionar sintomas, detalhes anatômicos ou elaborações.\n"
        "   CORRETO (se na lista): 'Limitação motora' | 'Cegos e leitores de tela' | 'Baixa visão'\n"
        "   ERRADO (mesmo que o rótulo esteja na lista, não elabore): 'pessoas com tremor nas mãos', 'quem usa o polegar', 'idosos', 'usuários em ônibus'\n"
        "   Regra simples: se a palavra não está na lista acima, não use.\n"
        "9. NUNCA use 'estrutura técnica' — substitua por 'funcionamento do site' ou 'organização das páginas'.\n"
        "10. Parágrafo 1: MÁXIMO 3 frases. Não escreva uma frase por barreira — agrupe os públicos afetados.\n"
        "11. Parágrafo 2: MÁXIMO 3 frases. Sem projeções, sem promessas de resultado.\n"
        "12. NUNCA afirme impacto financeiro ou jurídico não demonstrado (conversão, abandono de carrinho, receita, vendas, risco legal crescente, exposição jurídica). A auditoria mapeia barreiras de acessibilidade, não análise de negócio.\n\n"
        "ESTRUTURA OBRIGATÓRIA:\n"
        f"  Parágrafo 1 — Primeira frase OBRIGATÓRIA: 'O portal apresenta {contagem}.'\n"
        "  Depois: em 1-2 frases, descreva quem é prejudicado e como — agrupando públicos similares.\n"
        "  Parágrafo 2 — O que a gestão deve encaminhar como prioridade e por que não agir tem consequências reais.\n\n"
        "Responda SOMENTE com JSON válido, sem markdown:\n\n"
        '{"resumo_executivo_ai": "<parágrafo 1>\\n\\n<parágrafo 2>"}'
    )


def _prompt_repair_nivel2_dev(raw: str) -> str:
    return (
        "A resposta abaixo deveria ser um JSON válido com esta estrutura:\n\n"
        '{"versao_dev": "..."}\n\n'
        "Reformate o conteúdo nessa estrutura. NÃO altere o conteúdo — corrija só a formatação. "
        "Responda SOMENTE com JSON válido, sem markdown:\n\n"
        f"{raw}"
    )


def _prompt_repair_nivel2_ticket(raw: str) -> str:
    return (
        "A resposta abaixo deveria ser um JSON válido com esta estrutura:\n\n"
        '{"texto_ticket": {"titulo": "...", "descricao": "...", "criterio_de_pronto": "..."}}\n\n'
        "Reformate o conteúdo nessa estrutura. NÃO altere o conteúdo — corrija só a formatação. "
        "Responda SOMENTE com JSON válido, sem markdown:\n\n"
        f"{raw}"
    )


def _looks_valid_dev_text(text: str) -> bool:
    """Rejeita versao_dev que seja um placeholder curto ou texto inútil."""
    t = (text or "").strip()
    if len(t) < 40:
        return False
    if t.lower() in {"1.0", "v1", "v1.0", "versão 1.0", "versao 1.0"}:
        return False
    return True


def _validate_nivel1(parsed: dict) -> tuple[bool, str]:
    required = (
        "justificativa_gerencial",
        "explicacao_usuario",
        "como_corrigir_claro",
        "acao_gerencial",
    )
    missing = [k for k in required if not str(parsed.get(k, "")).strip()]
    if missing:
        return False, f"campos ausentes: {', '.join(missing)}"
    return True, ""


def _prompt_repair_nivel1(raw: str) -> str:
    return (
        "A resposta abaixo deveria ser um JSON válido com exatamente esta estrutura:\n\n"
        '{"justificativa_gerencial":"...",'
        '"explicacao_usuario":"...",'
        '"como_corrigir_claro":"...",'
        '"acao_gerencial":"..."}\n\n'
        "Reformate o conteúdo abaixo nessa estrutura JSON. "
        "NÃO altere o conteúdo — corrija apenas a formatação. "
        "Responda SOMENTE com JSON válido, sem markdown:\n\n"
        f"{raw}"
    )


async def _enrich_barrier(barrier: dict, api_key: str, level: int) -> None:
    if level >= 2 and str(barrier.get("versao_dev") or "").strip():
        normalize_barrier_ai_texts(barrier)
        return

    cache_key = json.dumps(
        {
            "tipo": barrier.get("issue_tipo_normalizado", ""),
            "titulo": barrier.get("titulo_tecnico", ""),
            "wcag": barrier.get("wcag_criterio", ""),
            "prioridade": barrier.get("prioridade", ""),
            "publico": barrier.get("publico_afetado", ""),
            "ocorrencias": int(barrier.get("ocorrencias_count") or 0),
            "onde": barrier.get("onde_esta", ""),
            "level": level,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    if cache_key in _cache:
        barrier.update(_cache[cache_key])
        normalize_barrier_ai_texts(barrier)
        return

    result: dict = {}

    # ── Nível 1: camada gerencial ─────────────────────────────────────────────
    raw1 = await _call_claude(_prompt_nivel1(barrier), api_key, max_tokens=1000, prefill="{")
    parsed1 = _parse_json(raw1)

    if not parsed1 and raw1:
        _log.info(
            "ai_enhancer: nivel1 repair-retry para '%s'",
            barrier.get("issue_tipo_normalizado", "?"),
        )
        raw1_repair = await _call_claude(
            _prompt_repair_nivel1(raw1), api_key, max_tokens=500, prefill="{"
        )
        parsed1 = _parse_json(raw1_repair)

    ok1, motivo1 = _validate_nivel1(parsed1) if parsed1 else (False, "JSON inválido")

    if not raw1:
        result["ai_nivel1_status"] = "falhou"
        result["ai_nivel1_motivo"] = "timeout ou erro de API na chamada do nível 1"
    elif not parsed1:
        result["ai_nivel1_status"] = "falhou"
        result["ai_nivel1_motivo"] = "resposta não produziu JSON válido nem após repair-retry"
    elif not ok1:
        result["ai_nivel1_status"] = "parcial"
        result["ai_nivel1_motivo"] = f"JSON válido mas incompleto — {motivo1}"
    else:
        result["ai_nivel1_status"] = "ok"
        result["ai_nivel1_motivo"] = ""

    result.update(
        {
            "justificativa_gerencial": _normalize_pt_text(parsed1.get("justificativa_gerencial", ""))
            if parsed1
            else "",
            "explicacao_usuario": _normalize_pt_text(parsed1.get("explicacao_usuario", "")) if parsed1 else "",
            "como_corrigir_claro": _normalize_pt_text(parsed1.get("como_corrigir_claro", "")) if parsed1 else "",
            "acao_gerencial": _normalize_pt_text(parsed1.get("acao_gerencial", "")) if parsed1 else "",
        }
    )

    if level >= 2:
        tipo = barrier.get("issue_tipo_normalizado", "?")

        # ── Chamada A: versao_dev ─────────────────────────────────────────────
        raw_dev = await _call_claude(
            _prompt_nivel2_dev(barrier),
            api_key,
            max_tokens=NIVEL2_DEV_MAX_TOKENS,
            prefill="{",
        )
        parsed_dev = _parse_json(raw_dev)

        if not parsed_dev and raw_dev:
            _log.info("ai_enhancer: nivel2-dev repair-retry para '%s'", tipo)
            raw_dev_repair = await _call_claude(
                _prompt_repair_nivel2_dev(raw_dev),
                api_key,
                max_tokens=NIVEL2_DEV_REPAIR_MAX_TOKENS,
                prefill="{",
            )
            parsed_dev = _parse_json(raw_dev_repair)

        versao_dev = _normalize_pt_text(parsed_dev.get("versao_dev", "")) if parsed_dev else ""
        if versao_dev and not _looks_valid_dev_text(versao_dev):
            versao_dev = ""

        # ── Chamada B: texto_ticket ─────────────────────────────────────────
        raw_ticket = await _call_claude(
            _prompt_nivel2_ticket(barrier),
            api_key,
            max_tokens=NIVEL2_TICKET_MAX_TOKENS,
            prefill="{",
        )
        parsed_ticket = _parse_json(raw_ticket)

        if not parsed_ticket and raw_ticket:
            _log.info("ai_enhancer: nivel2-ticket repair-retry para '%s'", tipo)
            raw_ticket_repair = await _call_claude(
                _prompt_repair_nivel2_ticket(raw_ticket),
                api_key,
                max_tokens=NIVEL2_TICKET_REPAIR_MAX_TOKENS,
                prefill="{",
            )
            parsed_ticket = _parse_json(raw_ticket_repair)

        tk_raw = parsed_ticket.get("texto_ticket", {}) if parsed_ticket else {}
        if not isinstance(tk_raw, dict):
            tk_raw = {}

        _, tk_norm = _nivel2_ticket_normalized({"versao_dev": "", "texto_ticket": tk_raw})

        missing_ticket = [f for f in ("titulo", "descricao", "criterio_de_pronto") if not tk_norm.get(f)]

        if not raw_dev and not raw_ticket:
            result["ai_nivel2_status"] = "falhou"
            result["ai_nivel2_motivo"] = "timeout ou erro de API nas chamadas do nível 2"
        elif versao_dev and not missing_ticket:
            result["ai_nivel2_status"] = "ok"
            result["ai_nivel2_motivo"] = ""
        elif versao_dev or not missing_ticket:
            result["ai_nivel2_status"] = "parcial"
            parts: list[str] = []
            if not versao_dev:
                parts.append("versao_dev ausente ou inválido")
            if missing_ticket:
                parts.append(f"ticket incompleto: {', '.join(missing_ticket)}")
            result["ai_nivel2_motivo"] = "; ".join(parts)
        else:
            result["ai_nivel2_status"] = "falhou"
            result["ai_nivel2_motivo"] = "versao_dev e texto_ticket não gerados"

        result["versao_dev"] = versao_dev
        result["texto_ticket"] = tk_norm

    normalize_barrier_ai_texts(result)
    nivel1_ok = any(
        result.get(f)
        for f in (
            "justificativa_gerencial",
            "explicacao_usuario",
            "como_corrigir_claro",
            "acao_gerencial",
        )
    )
    nivel2_solicitado_e_falhou = (
        level >= 2
        and result.get("ai_nivel2_status") in ("falhou", None)
        and not result.get("versao_dev")
    )
    if nivel1_ok and not nivel2_solicitado_e_falhou:
        _cache[cache_key] = result
    barrier.update(result)
    normalize_barrier_ai_texts(barrier)


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
    texto = _normalize_pt_text(parsed.get("resumo_executivo_ai", ""))
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

    sem = asyncio.Semaphore(AI_ANTHROPIC_CONCURRENCY)

    async def _safe_barrier_limited(b: dict) -> None:
        async with sem:
            await _safe_barrier(b)

    async def _safe_exec_limited() -> None:
        async with sem:
            await _safe_exec()

    await asyncio.gather(*[_safe_barrier_limited(b) for b in barriers], _safe_exec_limited())

    report["ai_enhanced"] = True
    report["ai_enhancement_level"] = level
    _log.info("ai_enhancer: concluído · %s", domain)
