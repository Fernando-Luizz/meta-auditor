import asyncio
import io
import os
import json
import logging
import hashlib
import base64
import importlib
import re
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import (
    AI_ENHANCE_LEVEL,
    AI_ENHANCE_REPORT,
    ANTHROPIC_API_KEY,
    APP_VERSION,
    DATA_EVIDENCE_DIR,
    DB_PATH,
    DEBUG,
    PROJECT_ROOT,
    PSI_API_KEY,
    REPORT_FOOTER_AUTHOR,
    REPORT_FOOTER_ORG,
    REPORT_HTML_EVIDENCE_MAX,
    WAVE_API_KEY,
    WAVE_REPORT_TYPE,
)
from app.connectors.lighthouse_connector import (
    classify_accessibility_audits,
    compute_score_breakdown,
    extract_accessibility_audits,
    get_accessibility_category,
    get_accessibility_score,
    run_lighthouse,
)
from app.connectors.wave_connector import WaveAPIError, run_wave
from app.database import (
    count_audits,
    get_audit,
    get_historico_url,
    init_db,
    list_audits,
    save_audit,
    search_urls,
    update_report,
)
from app.models.request_models import AuditRequest
from app.services.consolidation import build_report, inferir_wcag_nivel
from app.services.pdf_export import build_pdf_target_urls, render_report_pdf, render_report_pdf_from_urls
from app.services.display_labels import attach_display_fields, issue_display_label, lighthouse_passed_label, pour_bucket_for
from app.services.text_clean import (
    barrier_exec_text,
    normalize_barrier_ai_texts,
    normalize_executive_plaintext,
    normalize_report_dashes,
    normalize_report_markup_text,
    strip_emoji,
    truncate_words,
)
from app.services.extractors import (
    extract_lighthouse_issues,
    extract_passed_tipo_set,
    extract_wave_items,
    wave_items_to_issues,
)

_log = logging.getLogger("uvicorn.error")

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
_jinja_env.filters["strip_emoji"] = strip_emoji
_jinja_env.filters["normalize_report_dashes"] = normalize_report_dashes
_jinja_env.filters["clean_report_text"] = normalize_report_markup_text


def _filter_issue_display_label(b: object) -> str:
    if not isinstance(b, dict):
        return str(b or "")
    return issue_display_label(
        b.get("issue_tipo_normalizado"),
        b.get("titulo_tecnico"),
        b.get("issue_id_original"),
    )


_jinja_env.filters["issue_display_label"] = _filter_issue_display_label
_jinja_env.filters["normalize_executive_plaintext"] = normalize_executive_plaintext
_jinja_env.filters["pour_bucket_for"] = pour_bucket_for
_jinja_env.filters["inferir_wcag_nivel"] = inferir_wcag_nivel
_jinja_env.filters["barrier_exec_text"] = barrier_exec_text
_jinja_env.filters["truncate_words"] = truncate_words
_jinja_env.filters["lighthouse_passed_label"] = lighthouse_passed_label


def _embed_evidence_into_row(audit_row: dict) -> dict:
    """Embute evidencia_b64 por barreira: EMBEDDED → LH_CROP → PLAYWRIGHT → UNAVAILABLE."""
    import copy

    row = copy.deepcopy(audit_row)
    report = row.get("report")
    if isinstance(report, dict):
        attach_display_fields(report.get("barreiras_automaticas"))
        attach_display_fields(report.get("alertas_revisao"))
        attach_display_fields(report.get("informativos_wave"))
        attach_display_fields(report.get("checks_manuais"))
        attach_display_fields(report.get("divergencias"))

    if not isinstance(report, dict):
        return row
    bars = report.get("barreiras_automaticas")
    if not isinstance(bars, list) or not bars:
        return row

    lh_raw: dict | None = None
    lh_path = _resolved_raw_path(row.get("lighthouse_raw_path"))
    if lh_path is not None:
        try:
            lh_raw = json.loads(lh_path.read_text(encoding="utf-8"))
        except Exception:
            lh_raw = None

    audit_id: int | None = row.get("id")
    audit_url: str = str(row.get("url") or "")

    for idx, b in enumerate(bars):
        if not isinstance(b, dict):
            continue
        normalize_barrier_ai_texts(b)

        # 1) EMBEDDED
        evidencias = b.get("evidencias")
        if isinstance(evidencias, list) and evidencias:
            ev0 = evidencias[0] if isinstance(evidencias[0], dict) else {}
            if ev0.get("screenshot_base64"):
                b["evidencia_b64"] = "data:image/png;base64," + ev0["screenshot_base64"]
                b["evidence_source"] = "EMBEDDED"
                continue

        # 2) LH_CROP
        if lh_raw is not None:
            lhids: list[str] = []
            raw_lhids = b.get("evidencia_lhids")
            if isinstance(raw_lhids, list):
                lhids = [str(x) for x in raw_lhids if x]
            if lhids:
                try:
                    png = _crop_lh_screenshot_evidence(lh_raw, lhids)
                    if png:
                        b["evidencia_b64"] = "data:image/png;base64," + base64.b64encode(png).decode()
                        b["evidence_source"] = "LH_CROP"
                        continue
                except Exception:
                    pass

        # 3) PLAYWRIGHT (somente cache em disco; não roda ao vivo no render)
        if audit_id is not None and audit_url:
            lhids_for_key: list[str] = [str(x) for x in (b.get("evidencia_lhids") or []) if x]
            sels_for_key = _barrier_selector_candidates(b)
            cached = _cache_key_for_barrier(audit_id, idx, audit_url, lhids_for_key, sels_for_key)
            if cached.exists():
                try:
                    png = cached.read_bytes()
                    if _evidence_is_good(png):
                        b["evidencia_b64"] = "data:image/png;base64," + base64.b64encode(png).decode()
                        b["evidence_source"] = "PLAYWRIGHT"
                        continue
                    try:
                        cached.unlink()
                        _log.info("Cache de evidência rejeitado e removido: %s", cached.name)
                    except Exception:
                        pass
                except Exception:
                    pass

        # 4) UNAVAILABLE
        b["evidence_source"] = "UNAVAILABLE"

    return row


async def _ensure_nivel2(audit_id: int, row: dict) -> dict:
    """Re-enriquece versao_dev (nível 2) se faltar, antes de HTML/PDF."""
    if not ANTHROPIC_API_KEY or AI_ENHANCE_LEVEL < 2:
        return row

    report = row.get("report") or {}
    barriers = report.get("barreiras_automaticas") or []
    missing = [b for b in barriers if not b.get("versao_dev")]
    if not missing:
        return row

    _log.info(
        "_ensure_nivel2: audit=%d — %d barreira(s) sem nível 2, re-enriquecendo",
        audit_id,
        len(missing),
    )

    try:
        from app.services.ai_enhancer import enhance_report

        await enhance_report(
            report=report,
            url=row.get("url", ""),
            api_key=ANTHROPIC_API_KEY,
            lh_score=row.get("lh_score"),
            wave_score=row.get("wave_aim_score"),
            level=AI_ENHANCE_LEVEL,
        )
        await update_report(DB_PATH, audit_id, report)
        row = dict(row)
        row["report"] = report
        _log.info("_ensure_nivel2: audit=%d — nível 2 completo e salvo no banco", audit_id)
    except Exception as exc:
        _log.warning("_ensure_nivel2: audit=%d falhou (não crítico): %s", audit_id, exc)

    return row


def _build_report_html(audit_row: dict, *, pdf_mode: bool = False) -> str:
    """HTML do relatório a partir de um registro completo da tabela `audits`."""
    enriched = _embed_evidence_into_row(audit_row)
    return _jinja_env.get_template("report.html").render(
        audit=enriched,
        app_version=APP_VERSION,
        report_evidence_max=REPORT_HTML_EVIDENCE_MAX,
        report_footer_org=REPORT_FOOTER_ORG,
        report_footer_author=REPORT_FOOTER_AUTHOR,
        now_year=datetime.now().year,
        pdf_mode=pdf_mode,
    )


def _raw_path_for_db(file_path: Path) -> str:
    """Caminho relativo à raiz do projeto (segmentos com /)."""
    return str(file_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")


def _resolved_raw_path(rel: str | None) -> Path | None:
    """Resolve caminho bruto sob PROJECT_ROOT, se existir."""
    if not rel or not isinstance(rel, str):
        return None
    p = (PROJECT_ROOT / rel.replace("\\", "/")).resolve()
    try:
        p.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None


def _audit_export_zip_bytes(audit_id: int, row: dict) -> bytes:
    """ZIP com brutos Lighthouse/WAVE, relatório consolidado (JSON) e HTML (testes)."""
    report = row.get("report")
    if not isinstance(report, dict):
        report = {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = (
            "Meta-Auditor — pacote temporário para testes\n"
            f"auditoria_id={audit_id}\n"
            f"url={row.get('url') or ''}\n"
            f"created_at={row.get('created_at') or ''}\n"
            "\n"
            "Conteúdo:\n"
            "  01_lighthouse_psi_bruto.json — resposta bruta PageSpeed (Lighthouse)\n"
            "  02_wave_bruto.json — resposta bruta WAVE\n"
            "  03_relatorio_consolidado.json — relatório normalizado (consolidação)\n"
            "  04_relatorio.html — relatório em HTML (mesmo do navegador)\n"
        )
        zf.writestr("00_leia-me.txt", readme)

        lh_p = _resolved_raw_path(row.get("lighthouse_raw_path"))
        if lh_p is not None:
            zf.write(lh_p, "01_lighthouse_psi_bruto.json")
        else:
            zf.writestr(
                "01_lighthouse_psi_bruto_AUSENTE.txt",
                "Arquivo Lighthouse/PSI bruto indisponível (caminho não salvo, arquivo "
                "removido ou auditoria antiga sem esta coluna no banco de dados).\n",
            )

        wv_p = _resolved_raw_path(row.get("wave_raw_path"))
        if wv_p is not None:
            zf.write(wv_p, "02_wave_bruto.json")
        else:
            zf.writestr(
                "02_wave_bruto_AUSENTE.txt",
                "Arquivo WAVE bruto indisponível (caminho não salvo, arquivo removido ou "
                "auditoria antiga sem esta coluna no banco de dados).\n",
            )

        zf.writestr(
            "03_relatorio_consolidado.json",
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        )
        zf.writestr("04_relatorio.html", _build_report_html(row))
    return buf.getvalue()


def _wave_category_count(categories: object, name: str) -> int:
    if not isinstance(categories, dict):
        return 0
    block = categories.get(name)
    if isinstance(block, dict):
        return int(block.get("count") or 0)
    return 0


def _wave_aim_score_from_raw(raw_wave: dict) -> float | None:
    stats = raw_wave.get("statistics")
    if not isinstance(stats, dict):
        return None
    v = stats.get("AIMscore")
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _find_screenshot_data_url(obj: object) -> str | None:
    """Procura o primeiro data URL de imagem no JSON bruto do Lighthouse."""
    if isinstance(obj, dict):
        data = obj.get("data")
        if isinstance(data, str) and data.startswith("data:image/"):
            return data
        for v in obj.values():
            found = _find_screenshot_data_url(v)
            if found:
                return found
    elif isinstance(obj, list):
        for x in obj:
            found = _find_screenshot_data_url(x)
            if found:
                return found
    return None


def _crop_lh_screenshot_evidence(lh_raw: dict, lhids: list[str]) -> bytes | None:
    """Crop do fullPageScreenshot Lighthouse via nodes[lhId] (sem rede)."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except ImportError:
        _log.warning("Pillow não instalado — crop de evidência Lighthouse indisponível.")
        return None

    try:
        lr = lh_raw.get("lighthouseResult") or lh_raw
        fps = lr.get("fullPageScreenshot")
        if not isinstance(fps, dict):
            return None

        screenshot_info = fps.get("screenshot") or {}
        nodes_map = fps.get("nodes") or {}
        if not isinstance(nodes_map, dict):
            nodes_map = {}

        data_url = screenshot_info.get("data") or ""
        img_w = int(screenshot_info.get("width") or 0)
        img_h = int(screenshot_info.get("height") or 0)
        if not data_url or not img_w or not img_h:
            return None

        if "," not in data_url:
            return None
        _, b64part = data_url.split(",", 1)
        img_bytes = base64.b64decode(b64part)
        full_img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

        rect = None
        matched_lhid = None
        for lhid in lhids:
            node = nodes_map.get(lhid)
            if isinstance(node, dict):
                rect = node
                matched_lhid = lhid
                break

        if rect is None:
            return None

        el_top = float(rect.get("top") or 0)
        el_left = float(rect.get("left") or 0)
        el_w = float(rect.get("width") or 0)
        el_h = float(rect.get("height") or 0)

        if el_w < 1 or el_h < 1:
            return None

        pad_v = max(80, int(el_h * 0.5))
        pad_h = max(80, int(el_w * 0.5))

        crop_left = max(0, int(el_left - pad_h))
        crop_top = max(0, int(el_top - pad_v))
        crop_right = min(img_w, int(el_left + el_w + pad_h))
        crop_bottom = min(img_h, int(el_top + el_h + pad_v))

        if (crop_right - crop_left) < 10 or (crop_bottom - crop_top) < 10:
            return None

        cropped = full_img.crop((crop_left, crop_top, crop_right, crop_bottom))
        out_img = cropped.convert("RGB")
        draw = ImageDraw.Draw(out_img, "RGBA")

        box_left = int(el_left - crop_left)
        box_top = int(el_top - crop_top)
        box_right = box_left + int(el_w)
        box_bottom = box_top + int(el_h)

        overlay_color = (220, 38, 38, 60)
        draw.rectangle([box_left, box_top, box_right, box_bottom], fill=overlay_color)

        border_color = (220, 38, 38, 255)
        for offset in range(3):
            draw.rectangle(
                [box_left - offset, box_top - offset, box_right + offset, box_bottom + offset],
                outline=border_color,
            )

        label = f" {matched_lhid or '?'} "
        label_x = max(0, box_left - 1)
        label_y = max(0, box_top - 18)
        label_bg = (220, 38, 38, 220)
        label_fg = (255, 255, 255, 255)

        font = None
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
        except Exception:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
            except Exception:
                try:
                    from pathlib import Path as _Path

                    win_arial = _Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf"
                    if win_arial.is_file():
                        font = ImageFont.truetype(str(win_arial), 11)
                except Exception:
                    font = ImageFont.load_default()

        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((label_x, label_y), label, font=font)
        draw.rectangle(bbox, fill=label_bg)
        draw.text((label_x, label_y), label, fill=label_fg, font=font)

        buf = io.BytesIO()
        out_img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    except Exception as exc:
        _log.warning("_crop_lh_screenshot_evidence falhou: %s", exc)
        return None


def _placeholder_evidence_png(
    title: str = "Imagem indisponível",
    reason: str = "",
    selector: str = "",
) -> bytes | None:
    """PNG placeholder (CAPTCHA/bloqueio/timeout)."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except ImportError:
        return None

    W, H = 520, 140
    img = Image.new("RGB", (W, H), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, W, 32], fill=(251, 191, 36))
    draw.rectangle([0, 0, W - 1, H - 1], outline=(203, 213, 225), width=1)

    ft_bold = ft_reg = ft_sm = None
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        try:
            ft_bold = ImageFont.truetype(path, 13)
            ft_reg = ImageFont.truetype(path, 12)
            ft_sm = ImageFont.truetype(path, 10)
            break
        except Exception:
            continue
    if ft_bold is None:
        ft_bold = ft_reg = ft_sm = ImageFont.load_default()

    draw.text((8, 9), title, fill=(92, 62, 0), font=ft_bold)

    y = 40
    if reason:
        draw.text((8, y), f"Motivo: {reason[:72]}", fill=(107, 114, 128), font=ft_reg)
        y += 18
    if selector:
        short = selector[:68] + ("…" if len(selector) > 68 else "")
        draw.text((8, y), f"Seletor: {short}", fill=(107, 114, 128), font=ft_sm)
        y += 16
    draw.text(
        (8, y + 4),
        "Use os seletores CSS no relatório para inspecionar manualmente.",
        fill=(156, 163, 175),
        font=ft_sm,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _normalize_selector(raw: str) -> str:
    s = " ".join(str(raw).strip().split())
    if not s:
        return ""
    if "BODY >" in s.upper():
        tail = s.upper().rfind("BODY >")
        s = "body > " + s[tail + len("BODY >") :]
    s = re.sub(r"^\s*HTML\s*>\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\s*BODY\s*>\s*", "body > ", s, flags=re.IGNORECASE)
    return s.strip()


def _barrier_selector_candidates(barrier: dict) -> list[str]:
    ev = barrier.get("evidencia_localizacao")
    if not isinstance(ev, list):
        ev = []
    out: list[str] = []
    seen: set[str] = set()

    def strip_lh_preface(line: str) -> str:
        """Remove prefixo '[lhId]' e texto após separador."""
        s = line.strip()
        s = re.sub(r"^\[[^\]\s]+\]\s*", "", s)
        for sep in (" — ", " – ", " - ", ": "):
            if sep in s:
                s = s.split(sep, 1)[0].strip()
                break
        return s

    def add(sel: str) -> None:
        s = _normalize_selector(sel)
        if not s or s in seen:
            return
        seen.add(s)
        out.append(s)

    for e in ev:
        s_raw = str(e or "").strip()
        if not s_raw or s_raw.startswith("<") or s_raw.lower().startswith("xpath"):
            continue
        s_use = strip_lh_preface(s_raw)
        add(s_use)
        m_id = re.search(r"#([A-Za-z_][\w:-]*)", s_use)
        if m_id:
            add(f"#{m_id.group(1)}")
        m_class = re.search(r"\.([A-Za-z_][\w:-]*)", s_use)
        if m_class:
            add(f".{m_class.group(1)}")
    return out


_HIGHLIGHT_INJECT_JS = """
(sel) => {
    try {
        const el = document.querySelector(sel);
        if (!el) return false;
        el.style.setProperty('outline', '3px solid #DC2626', 'important');
        el.style.setProperty('outline-offset', '2px', 'important');
        el.style.setProperty('background-color', 'rgba(220,38,38,0.10)', 'important');
        el.dataset.metaHighlight = '1';
        return true;
    } catch { return false; }
}
"""

_HIGHLIGHT_REMOVE_JS = """
() => {
    document.querySelectorAll('[data-meta-highlight]').forEach(el => {
        el.style.removeProperty('outline');
        el.style.removeProperty('outline-offset');
        el.style.removeProperty('background-color');
        delete el.dataset.metaHighlight;
    });
}
"""


def _add_pillow_label(png_bytes: bytes, label: str) -> bytes:
    """Faixa vermelha com label no topo do PNG."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore

        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        bar_h = 22
        new_img = Image.new("RGB", (img.width, img.height + bar_h), (220, 38, 38))
        new_img.paste(img, (0, bar_h))
        draw = ImageDraw.Draw(new_img)
        font = None
        for font_path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]:
            try:
                font = ImageFont.truetype(font_path, 12)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        draw.text((6, 4), label, fill=(255, 255, 255), font=font)
        buf = io.BytesIO()
        new_img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception as exc:
        _log.warning("_add_pillow_label falhou: %s", exc)
        return png_bytes


async def _capture_barrier_image(
    url: str,
    selectors: list[str],
    out_file: Path,
    compact: bool,
    barrier_label: str = "",
) -> None:
    def _run_sync() -> None:
        png = _capture_barrier_image_sync_bytes(
            url=url,
            selectors=selectors,
            compact=compact,
            barrier_label=barrier_label,
        )
        if png:
            DATA_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            out_file.write_bytes(png)

    await asyncio.to_thread(_run_sync)


def _evidence_is_good(png_bytes: bytes) -> bool:
    """Reprova PNG <80px, pouco vermelho de highlight (<0,15%) ou fundo uniforme."""
    try:
        from PIL import Image  # type: ignore
        import statistics as _stats

        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        w, h = img.size
        if w < 80 or h < 80:
            return False

        pixels = img.load()
        red_like = 0
        sampled = 0
        sample_r: list[int] = []

        for y in range(0, h, 3):
            for x in range(0, w, 3):
                r, g, b = pixels[x, y]
                sampled += 1
                sample_r.append(r)
                if r > 180 and g < 120 and b < 120:
                    red_like += 1

        red_ratio = red_like / max(sampled, 1)
        if red_ratio < 0.0015:
            return False
        if len(sample_r) > 4 and _stats.variance(sample_r) < 50:
            return False
        return True
    except Exception:
        return False


def _cache_key_for_barrier(
    audit_id: int,
    barrier_idx: int,
    url: str,
    lhids: list[str],
    selectors: list[str],
) -> Path:
    """Caminho do PNG cacheado para a barreira (compact=True, igual ao endpoint)."""
    key_src = f"{audit_id}|{barrier_idx}|True|{url}|{'|'.join(lhids)}|{'|'.join(selectors)}"
    key = hashlib.sha256(key_src.encode("utf-8", errors="replace")).hexdigest()[:20]
    return DATA_EVIDENCE_DIR / f"audit-{audit_id}-barreira-{barrier_idx}-{key}.png"


def _capture_barrier_image_sync_bytes(
    url: str,
    selectors: list[str],
    compact: bool = True,
    barrier_label: str = "",
) -> bytes | None:
    """Playwright ao vivo → PNG validado, ou None (sem screenshot genérico)."""
    try:
        pw_mod = importlib.import_module("playwright.sync_api")
        sync_playwright = pw_mod.sync_playwright
    except ImportError:
        _log.warning("Playwright não instalado — captura ao vivo indisponível.")
        return None

    vw = 800 if compact else 1366
    vh = 520 if compact else 900

    def _run() -> bytes | None:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                viewport={"width": vw, "height": vh},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as exc:
                browser.close()
                _log.warning("Playwright goto falhou (%s): %s", url, exc)
                return None

            result: bytes | None = None
            for sel in selectors[:10]:
                try:
                    loc = page.locator(sel).first
                    if loc.count() < 1:
                        continue

                    loc.scroll_into_view_if_needed(timeout=4000)
                    page.wait_for_timeout(300)
                    page.evaluate(_HIGHLIGHT_INJECT_JS, sel)
                    page.wait_for_timeout(150)

                    bbox = loc.bounding_box()
                    if not (bbox and bbox["width"] > 0 and bbox["height"] > 0):
                        try:
                            page.evaluate(_HIGHLIGHT_REMOVE_JS)
                        except Exception:
                            pass
                        continue

                    pad = 80
                    clip = {
                        "x": max(0.0, bbox["x"] - pad),
                        "y": max(0.0, bbox["y"] - pad),
                        "width": min(float(vw), bbox["width"] + pad * 2),
                        "height": min(float(vh), bbox["height"] + pad * 2),
                    }
                    if clip["x"] + clip["width"] > vw:
                        clip["width"] = vw - clip["x"]
                    if clip["y"] + clip["height"] > vh:
                        clip["height"] = vh - clip["y"]

                    png_bytes = page.screenshot(type="png", clip=clip)

                    try:
                        page.evaluate(_HIGHLIGHT_REMOVE_JS)
                    except Exception:
                        pass

                    # Valida a imagem sem adicionar faixa artificial no topo.
                    # A legenda do relatório já identifica a barreira.
                    if _evidence_is_good(png_bytes):
                        result = png_bytes
                        break
                except Exception:
                    try:
                        page.evaluate(_HIGHLIGHT_REMOVE_JS)
                    except Exception:
                        pass
                    continue

            browser.close()
            return result

    try:
        return _run()
    except Exception as exc:
        _log.warning("_capture_barrier_image_sync_bytes falhou (%s): %s", url, exc)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log.warning(
        "Meta-Auditor %s | PROJECT_ROOT=%s | WAVE_REPORT_TYPE=%s | DB=%s",
        APP_VERSION,
        PROJECT_ROOT,
        WAVE_REPORT_TYPE,
        DB_PATH,
    )
    await init_db(DB_PATH)
    yield


app = FastAPI(
    title="Meta-Auditor de Acessibilidade",
    version=APP_VERSION,
    description="Auditoria de URLs: Lighthouse/PSI (score + audits) e WAVE (achados + localização).",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def root_favicon():
    """Fallback: browsers pedem /favicon.ico mesmo com <link rel="icon">."""
    p = _STATIC_DIR / "favicon.ico"
    if not p.is_file():
        raise HTTPException(status_code=404, detail="favicon.ico não gerado — rode scripts/generate_favicon_assets.py")
    return FileResponse(p, media_type="image/x-icon")


@app.get("/apple-touch-icon.png", include_in_schema=False)
async def root_apple_touch_icon():
    """iOS costuma pedir na raiz ao guardar na tela inicial."""
    p = _STATIC_DIR / "apple-touch-icon.png"
    if not p.is_file():
        raise HTTPException(status_code=404, detail="apple-touch-icon.png não gerado — rode scripts/generate_favicon_assets.py")
    return FileResponse(p, media_type="image/png")


@app.get("/", response_class=HTMLResponse)
async def root():
    """UI mínima (formulário + histórico); documentação interativa em /docs."""
    html = _jinja_env.get_template("index.html").render(app_version=APP_VERSION)
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


@app.get("/info")
async def api_info():
    return {
        "service": "Meta-Auditor de Acessibilidade",
        "ui": "/",
        "docs": "/docs",
        "health": "/health",
        "audit": "POST /audit com body {\"url\": \"https://...\"}",
        "audits": "GET /audits?limit=50 | GET /audits/{id} | GET /audits/{id}/report.html",
        "export": "GET /audits/{id}/export.html | export.json | export.zip | export.pdf (PDF sem cabeçalho do navegador)",
    }


@app.get("/audits/{audit_id}/export.zip")
async def audit_export_zip(audit_id: int):
    """Brutos LH+WAVE + relatorio JSON + HTML num único ZIP (apoiar testes)."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    payload = _audit_export_zip_bytes(audit_id, row)
    name = f"meta-auditoria-{audit_id}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.get("/audits/{audit_id}/export.json", response_class=JSONResponse)
async def audit_export_json(audit_id: int):
    """Registo completo em JSON (mesmo conteúdo que GET /audits/{id}) com cabeçalho de descarga."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    name = f"meta-auditoria-{audit_id}.json"
    return JSONResponse(
        content=row,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.get("/audits/{audit_id}/export.html", response_class=HTMLResponse)
async def audit_export_html(audit_id: int):
    """Relatório HTML como arquivo (download); não abre na aba do navegador."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    row = await _ensure_nivel2(audit_id, row)
    html = _build_report_html(row)
    name = f"relatorio-acessibilidade-{audit_id}.html"
    return HTMLResponse(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.get("/audits/{audit_id}/export.pdf")
async def audit_export_pdf(audit_id: int, request: Request):
    """PDF via Playwright server-side (não use window.print — corta blocos e injeta localhost)."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    row = await _ensure_nivel2(audit_id, row)

    export_dir = PROJECT_ROOT / "data" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / f"relatorio-acessibilidade-{audit_id}.pdf"

    # pdf_mode alinha HTML de download e PDF (sem barra de exportação).
    html = _build_report_html(row, pdf_mode=True)
    try:
        pdf_bytes = await asyncio.to_thread(render_report_pdf, html)
        out_path.write_bytes(pdf_bytes)
    except Exception as inline_exc:
        _log.warning(
            "PDF inline (render_report_pdf) falhou para auditoria %s: %s — tentando via URL",
            audit_id,
            inline_exc,
        )
        target_urls = build_pdf_target_urls(audit_id, str(request.base_url))
        try:
            await asyncio.to_thread(render_report_pdf_from_urls, target_urls, out_path)
        except Exception as exc:
            _log.exception("Falha ao gerar PDF da auditoria %s", audit_id)
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao gerar PDF: {exc}",
            ) from exc

    return FileResponse(
        str(out_path),
        media_type="application/pdf",
        filename=f"relatorio-acessibilidade-{audit_id}.pdf",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/audits/{audit_id}/report.html", response_class=HTMLResponse)
async def audit_report_html(
    audit_id: int,
    pdf: int = Query(0, ge=0, le=1, description="1 = modo renderização PDF (sem barra de export)"),
    print_mode: int = Query(0, alias="print", ge=0, le=1),
):
    """Relatório legível (HTML) a partir do registro no banco de dados — sem CDN."""
    if print_mode:
        return RedirectResponse(url=f"/audits/{audit_id}/export.pdf", status_code=303)

    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    html = _build_report_html(row, pdf_mode=bool(pdf))
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


@app.get("/audits/{audit_id}/evidence-image")
async def audit_evidence_image(audit_id: int, barrier_idx: int = Query(0, ge=0), compact: bool = True):
    """Evidência visual: cache → LH_CROP → Playwright; 404 se UNAVAILABLE."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    report = row.get("report") if isinstance(row.get("report"), dict) else {}
    bars = report.get("barreiras_automaticas") if isinstance(report.get("barreiras_automaticas"), list) else []
    if barrier_idx >= len(bars):
        raise HTTPException(status_code=404, detail="Barreira não encontrada")
    barrier = bars[barrier_idx] if isinstance(bars[barrier_idx], dict) else {}

    url = str(row.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=404, detail="URL da auditoria indisponível")

    lhids: list[str] = [str(x) for x in (barrier.get("evidencia_lhids") or []) if x]
    selectors = _barrier_selector_candidates(barrier)
    out_file = _cache_key_for_barrier(audit_id, barrier_idx, url, lhids, selectors)

    # 1) cache em disco
    if out_file.exists():
        png = out_file.read_bytes()
        if _evidence_is_good(png):
            return Response(
                content=png,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=86400", "X-Meta-Evidence": "cached"},
            )
        try:
            out_file.unlink()
            _log.info("Cache de evidência inválido removido: %s", out_file.name)
        except Exception:
            pass

    # 2) LH_CROP
    if lhids:
        lh_path = _resolved_raw_path(row.get("lighthouse_raw_path"))
        if lh_path is not None:
            try:
                lh_raw = json.loads(lh_path.read_text(encoding="utf-8"))
                png_bytes = _crop_lh_screenshot_evidence(lh_raw, lhids)
                if png_bytes and _evidence_is_good(png_bytes):
                    DATA_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
                    out_file.write_bytes(png_bytes)
                    _log.info("Evidência LH_CROP: audit=%d barreira=%d lhids=%s", audit_id, barrier_idx, lhids)
                    return Response(
                        content=png_bytes,
                        media_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400", "X-Meta-Evidence": "lh_crop"},
                    )
            except Exception as exc:
                _log.warning("LH_CROP falhou (audit=%d barreira=%d): %s", audit_id, barrier_idx, exc)

    # 3) Playwright ao vivo
    if selectors:
        try:
            png_bytes = await asyncio.to_thread(
                _capture_barrier_image_sync_bytes,
                url,
                selectors,
                compact,
                "",
            )
            if png_bytes:
                DATA_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
                out_file.write_bytes(png_bytes)
                _log.info("Evidência Playwright: audit=%d barreira=%d", audit_id, barrier_idx)
                return Response(
                    content=png_bytes,
                    media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400", "X-Meta-Evidence": "playwright"},
                )
            _log.info(
                "Playwright não gerou evidência confiável (audit=%d barreira=%d) — UNAVAILABLE",
                audit_id,
                barrier_idx,
            )
        except Exception as exc:
            _log.warning("Playwright falhou (audit=%d barreira=%d): %s", audit_id, barrier_idx, exc)

    # 4) UNAVAILABLE — sem fallback genérico
    _log.info("Evidência indisponível: audit=%d barreira=%d", audit_id, barrier_idx)
    raise HTTPException(
        status_code=404,
        detail="Evidência visual indisponível: sem LH crop confiável e Playwright não encontrou o elemento.",
    )


@app.get("/audits")
async def audits_list(
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros (mais recentes primeiro)"),
    url: str | None = Query(None, description="Filtrar por URL exata e retornar histórico comparativo."),
    order_by: str = Query(
        "created_at",
        description="Campo para ordenação: created_at | score_risco | lh_score | wave_aim_score | barreiras_count",
    ),
    order_dir: str = Query("desc", description="Direção da ordenação: asc | desc"),
):
    """Lista auditorias; com ?url retorna série temporal da URL (ASC)."""
    if url:
        rows = await get_historico_url(DB_PATH, url=url, limit=limit)
        return {"url": url, "total": len(rows), "audits": rows}

    rows = await list_audits(DB_PATH, limit=limit, order_by=order_by, order_dir=order_dir)
    total = await count_audits(DB_PATH)
    return {"total": total, "audits": rows}


@app.get("/audits/buscar-urls")
async def audits_search_urls(
    q: str = Query("", description="Substring para autocomplete das URLs auditadas."),
    limit: int = Query(10, ge=1, le=50),
):
    urls = await search_urls(DB_PATH, q=q, limit=limit)
    return {"urls": urls}


@app.get("/audits/{audit_id}")
async def audits_get(audit_id: int):
    """Relatório completo de uma auditoria (report + score_breakdown como dict)."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    return row


async def _fetch_wave_optional(url: str) -> tuple[dict, Path | None]:
    """Chama WAVE só se existir API key; caso contrário devolve dados vazio sem erro."""
    if not WAVE_API_KEY:
        return {}, None
    return await run_wave(url)


@app.post("/audit")
async def start_audit(request: AuditRequest):
    """PSI + WAVE em paralelo; 502 só se ambos falharem. Sem WAVE_API_KEY → só Lighthouse."""
    url = str(request.url)
    raw_psi: dict = {}
    raw_wave: dict = {}
    lh_raw_path: Path | None = None
    wave_raw_path: Path | None = None
    psi_error: str | None = None
    wave_error: str | None = None
    wave_skipped_no_key = not bool(WAVE_API_KEY)

    psi_result, wave_result = await asyncio.gather(
        run_lighthouse(url),
        _fetch_wave_optional(url),
        return_exceptions=True,
    )

    if isinstance(psi_result, Exception):
        psi_error = _describe_psi_exception(psi_result)
        _log.warning("PSI indisponivel para %s: %s", url, psi_error)
    else:
        raw_psi, lh_raw_path = psi_result

    if isinstance(wave_result, Exception):
        wave_error = _describe_wave_exception(wave_result)
        _log.warning("WAVE indisponivel para %s: %s", url, wave_error)
    else:
        raw_wave, wave_raw_path = wave_result

    has_lighthouse = not psi_error
    has_wave = wave_raw_path is not None

    if not has_lighthouse and not has_wave:
        parts = []
        if psi_error:
            parts.append(f"PSI={psi_error}")
        if wave_skipped_no_key:
            parts.append(
                "WAVE omitido (sem WAVE_API_KEY); PSI não devolveu dados — "
                "adicione WAVE_API_KEY ao .env ou aguarde cota PSI / use PSI_API_KEY"
            )
        elif wave_error:
            parts.append(f"WAVE={wave_error}")
        msg = " | ".join(parts) if parts else "Nenhum dado PSI/WAVE disponível"
        raise HTTPException(status_code=502, detail=msg)

    if psi_error and has_wave:
        _log.info("Auditoria parcial apenas WAVE para %s (%s)", url, psi_error)

    lhr = raw_psi.get("lighthouseResult") or {}
    categories_returned = list((lhr.get("categories") or {}).keys())

    a11y_category = get_accessibility_category(raw_psi)
    score = get_accessibility_score(raw_psi)

    audits = extract_accessibility_audits(raw_psi)
    classified = classify_accessibility_audits(audits) if audits else {
        "failed": [],
        "passed": [],
        "manual": [],
        "not_applicable": [],
        "informative": [],
        "errors": [],
    }
    score_breakdown = compute_score_breakdown(raw_psi) if raw_psi and (raw_psi.get("lighthouseResult")) else None
    failed_audits = classified["failed"]

    lh_auto, lh_manual = extract_lighthouse_issues(
        classified["failed"],
        classified["manual"],
        url,
    )

    wave_flat = extract_wave_items(raw_wave)
    w_bar, w_alert, w_info = wave_items_to_issues(wave_flat, url)
    lh_passed_tipo_set = extract_passed_tipo_set(classified["passed"])
    lh_passed_audits = classified["passed"]
    report = build_report(
        lh_auto,
        w_bar,
        w_alert,
        w_info,
        lh_manual,
        lh_passed_tipo_set=lh_passed_tipo_set,
        lh_passed_audits=lh_passed_audits,
    )

    if AI_ENHANCE_REPORT and ANTHROPIC_API_KEY:
        try:
            from app.services.ai_enhancer import enhance_report

            await enhance_report(
                report=report,
                url=url,
                api_key=ANTHROPIC_API_KEY,
                lh_score=score,
                wave_score=_wave_aim_score_from_raw(raw_wave),
                level=AI_ENHANCE_LEVEL,
            )
        except Exception as _ai_exc:
            _log.warning("enhance_report falhou (não crítico): %s", _ai_exc)

    wave_cats = raw_wave.get("categories") if isinstance(raw_wave.get("categories"), dict) else {}
    wave_error_count = _wave_category_count(wave_cats, "error")
    wave_contrast_count = _wave_category_count(wave_cats, "contrast")
    barreiras_count = len(report.get("barreiras_automaticas") or [])
    divergencias_count = len(report.get("divergencias") or [])
    score_risco = (report.get("score_risco") or {}).get("valor")

    if wave_skipped_no_key:
        wave_meta = {"status": "skipped_no_key", "error": None}
    elif wave_error:
        wave_meta = {"status": "failed", "error": wave_error}
    else:
        wave_meta = {"status": "ok", "error": None}

    _lh_version = (lhr.get("lighthouseVersion") or "") if not psi_error else ""
    collection_meta = {
        "lighthouse": {
            "status": "ok" if not psi_error else "failed",
            "error": psi_error,
            "version": _lh_version,
        },
        "wave": wave_meta,
    }
    report["metadados_coleta"] = collection_meta

    audit_id = await save_audit(
        DB_PATH,
        url=url,
        lh_score=score,
        wave_aim_score=_wave_aim_score_from_raw(raw_wave),
        lh_failed_count=len(failed_audits),
        wave_error_count=wave_error_count,
        wave_contrast_count=wave_contrast_count,
        barreiras_count=barreiras_count,
        divergencias_count=divergencias_count,
        score_risco=score_risco,
        score_breakdown=score_breakdown,
        report=report,
        lighthouse_raw_path=_raw_path_for_db(lh_raw_path) if lh_raw_path else None,
        wave_raw_path=_raw_path_for_db(wave_raw_path) if wave_raw_path else None,
    )

    wave_stats = raw_wave.get("statistics") if isinstance(raw_wave.get("statistics"), dict) else {}
    wave_categories_summary: dict = {}
    for cname, cdata in wave_cats.items():
        if isinstance(cdata, dict):
            wave_categories_summary[cname] = {
                "description": cdata.get("description"),
                "count": cdata.get("count"),
            }

    body = {
        "app_version": APP_VERSION,
        "audit_id": audit_id,
        "url": url,
        "status": "completed",
        "lighthouse": {
            "categories_returned": categories_returned,
            "accessibility_score": score,
            "score_breakdown": score_breakdown,
            "failed_audits_count": len(failed_audits),
            "accessibility": {
                "score": score,
                "title": a11y_category.get("title"),
                "description": a11y_category.get("description"),
                "manual_checks_count": len(classified["manual"]),
                "passed_audits_count": len(classified["passed"]),
                "not_applicable_count": len(classified["not_applicable"]),
                "error_count": len(classified["errors"]),
                "failed_audits": classified["failed"],
                "manual_checks": classified["manual"],
            },
        },
        "wave": {
            "reporttype": WAVE_REPORT_TYPE,
            "statistics": wave_stats,
            "categories_summary": wave_categories_summary,
            "items_extracted_count": len(wave_flat),
        },
        "providers": collection_meta,
        "ai_usage": report.get("ai_usage"),
        "report": report,
        "raw_saved": {
            "lighthouse": bool(lh_raw_path),
            "wave": bool(wave_raw_path),
        },
    }
    if DEBUG:
        body["debug"] = {"project_root": str(PROJECT_ROOT)}
    return JSONResponse(content=body, status_code=200)


def _raise_429():
    raise HTTPException(
        status_code=429,
        detail=(
            "Google PageSpeed Insights está limitando requisições (429). "
            "Aguarde 10–30 minutos e tente de novo. "
            "Confira em GET /health se psi_api_key_configured é true; se for false, ative a .venv e reinicie o uvicorn."
        ),
    )


def _raise_400(google_message: str = ""):
    msg = (google_message or "").upper()
    if (
        "FAILED_DOCUMENT_REQUEST" in msg
        or "ERR_TIMED_OUT" in msg
        or "UNABLE TO RELIABLY LOAD" in msg
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "O Lighthouse não conseguiu carregar a página a tempo (timeout). "
                "A URL pode estar lenta, indisponível ou bloqueando o servidor do Google. "
                "Tente outra URL (ex.: https://example.com) ou teste de novo mais tarde."
            ),
        )
    base = (
        "Google PageSpeed Insights recusou a requisição (400). "
        "Confira: (1) A API 'PageSpeed Insights API' está ativada no projeto no Google Cloud; "
        "(2) A chave em .env está correta e sem espaços; (3) Se a chave tem restrição, permita 'PageSpeed Insights API'. "
    )
    if google_message:
        base += f"Resposta do Google: {google_message[:500]}"
    raise HTTPException(status_code=400, detail=base)


def _describe_psi_exception(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        body = ""
        try:
            body = (exc.response.text or "")[:500]
        except Exception:
            body = ""
        body_up = body.upper()
        if status == 429:
            return "429 Too Many Requests (quota/rate-limit no PageSpeed Insights)"
        if status == 400 and (
            "NO_FCP" in body_up or "FAILED_DOCUMENT_REQUEST" in body_up or "ERR_TIMED_OUT" in body_up
        ):
            return "400 NO_FCP/timeout: Lighthouse nao conseguiu renderizar a pagina no PSI"
        return f"HTTP {status}: {body or str(exc)}"
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return f"Timeout/conexao no PSI: {exc!s}"
    return str(exc)


def _describe_wave_exception(exc: Exception) -> str:
    if isinstance(exc, WaveAPIError):
        return exc.message or "erro retornado pela API WAVE"
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        body = ""
        try:
            body = (exc.response.text or "")[:500]
        except Exception:
            body = ""
        return f"HTTP {status}: {body or str(exc)}"
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return f"Timeout/conexao na API WAVE: {exc!s}"
    return str(exc)


@app.get("/health")
async def health_check():
    data = {
        "status": "ok",
        "version": APP_VERSION,
        "psi_api_key_configured": bool(PSI_API_KEY),
        "wave_api_key_configured": bool(WAVE_API_KEY),
        "wave_report_type": WAVE_REPORT_TYPE,
        "ai_enhance_configured": bool(ANTHROPIC_API_KEY),
        "ai_enhance_enabled": AI_ENHANCE_REPORT,
        "ai_enhance_level": AI_ENHANCE_LEVEL,
    }
    if DEBUG:
        data["project_root"] = str(PROJECT_ROOT)
    return data
