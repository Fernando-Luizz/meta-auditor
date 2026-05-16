"""Normalização Lighthouse / WAVE -> tipos e metadados WCAG."""
import pytest

from app.services.normalize_maps import normalize_lighthouse_audit, normalize_wave_item


def test_lighthouse_link_name_aligns_with_wave_link_empty():
    lh = normalize_lighthouse_audit("link-name", "Links", "")
    wv = normalize_wave_item("error", "link_empty", "Empty link")
    assert lh["issue_tipo_normalizado"] == wv["issue_tipo_normalizado"] == "link_sem_nome_acessivel"
    assert lh["wcag_criterio"]
    assert wv["wcag_criterio"]


def test_lighthouse_color_contrast_aligns_with_wave_contrast():
    lh = normalize_lighthouse_audit("color-contrast", "Contrast", "")
    wv = normalize_wave_item("contrast", "contrast", "Very low contrast")
    assert lh["issue_tipo_normalizado"] == wv["issue_tipo_normalizado"] == "contraste_insuficiente"


def test_wave_alert_maps_have_wcag():
    for cat, iid in [
        ("alert", "accesskey"),
        ("alert", "alt_duplicate"),
        ("alert", "link_redundant"),
        ("alert", "noscript"),
        ("alert", "text_small"),
    ]:
        m = normalize_wave_item(cat, iid, "x")
        assert m["wcag_criterio"].strip(), f"{cat}/{iid}"
        assert m["publico_afetado"].strip(), f"{cat}/{iid}"


def test_unmapped_wave_falls_back_empty_wcag():
    m = normalize_wave_item("alert", "totally_unknown_xyz", "desc")
    assert m["issue_tipo_normalizado"].startswith("wave_alert_")
    assert m["wcag_criterio"] == ""


@pytest.mark.parametrize(
    ("audit_id", "expected_tipo"),
    [
        ("landmark-one-main", "ausencia_landmark_main"),
        ("aria-prohibited-attr", "aria_atributo_proibido"),
        ("aria-hidden-focus", "aria_hidden_com_foco"),
        ("list", "lista_filhos_invalidos"),
        ("listitem", "item_lista_fora_de_lista"),
        ("link-in-text-block", "link_distinguivel_somente_por_cor"),
        ("html-lang-valid", "idioma_html_invalido"),
        ("empty-heading", "heading_sem_conteudo"),
        ("skip-link", "skip_link_nao_focalizavel"),
        ("accesskeys", "accesskey_duplicado"),
        ("tabindex", "tabindex_positivo"),
        ("aria-command-name", "controle_interativo_sem_nome_aria"),
        ("aria-conditional-attr", "aria_atributo_condicional_invalido"),
        ("aria-deprecated-role", "aria_role_obsoleto"),
        ("aria-hidden-body", "body_aria_hidden"),
    ],
)
def test_lighthouse_new_and_preventive_maps(audit_id, expected_tipo):
    m = normalize_lighthouse_audit(audit_id, "t", "")
    assert m["issue_tipo_normalizado"] == expected_tipo
    assert m["wcag_criterio"].strip()
    assert m["publico_afetado"].strip()


@pytest.mark.parametrize(
    ("cat", "item_id", "expected_tipo"),
    [
        ("alert", "table_layout", "wave_alert_tabela_layout"),
        ("error", "alt_link_missing", "imagem_link_sem_texto_alternativo"),
        ("alert", "alt_redundant", "wave_alert_alt_redundant"),
        ("alert", "alt_long", "wave_alert_alt_longo"),
        ("alert", "alt_suspicious", "wave_alert_alt_suspeito"),
        ("alert", "heading_possible", "wave_alert_possivel_titulo"),
        ("alert", "fieldset_missing", "wave_alert_fieldset_ausente"),
        ("alert", "label_orphaned", "wave_alert_label_orfao"),
        ("alert", "link_pdf", "wave_alert_link_pdf"),
        ("alert", "youtube_video", "wave_alert_youtube_video"),
        ("alert", "html5_video_audio", "wave_alert_video_audio_html5"),
    ],
)
def test_wave_new_items_map(cat, item_id, expected_tipo):
    m = normalize_wave_item(cat, item_id, "d")
    assert m["issue_tipo_normalizado"] == expected_tipo
    assert m["wcag_criterio"].strip()
    assert m["publico_afetado"].strip()
