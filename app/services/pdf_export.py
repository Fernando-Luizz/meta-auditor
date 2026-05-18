"""Geração de PDF do relatório via Playwright (sem window.print / cabeçalho do navegador)."""
from __future__ import annotations

import importlib
import os
from pathlib import Path

# Margens alinhadas ao @page final do template (cabeçalho fixo desativado no PDF)
_PDF_MARGIN_TOP = "10mm"
_PDF_MARGIN_SIDE = "8mm"
_PDF_MARGIN_BOTTOM = "12mm"


def build_pdf_target_urls(audit_id: int, request_base: str = "") -> list[str]:
    """
    URLs candidatas para o Playwright abrir o relatório HTML.

    Em Docker, o cliente acessa :8010 mas o Playwright dentro do container
    deve preferir META_AUDITOR_INTERNAL_BASE_URL (ex.: http://127.0.0.1:8000).
    """
    urls: list[str] = []

    env_base = os.getenv("META_AUDITOR_INTERNAL_BASE_URL", "").strip()
    if env_base:
        urls.append(f"{env_base.rstrip('/')}/audits/{audit_id}/report.html?pdf=1")

    base = (request_base or "").strip().rstrip("/")
    if base:
        urls.append(f"{base}/audits/{audit_id}/report.html?pdf=1")

    urls.extend(
        [
            f"http://127.0.0.1:8000/audits/{audit_id}/report.html?pdf=1",
            f"http://localhost:8000/audits/{audit_id}/report.html?pdf=1",
            f"http://127.0.0.1:8010/audits/{audit_id}/report.html?pdf=1",
            f"http://localhost:8010/audits/{audit_id}/report.html?pdf=1",
        ]
    )

    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _chromium_launch_kwargs() -> dict:
    chromium_path = os.getenv("CHROMIUM_PATH", "").strip() or None
    launch_kwargs: dict = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--font-render-hinting=none",
            "--disable-gpu",
        ],
    }
    if chromium_path:
        launch_kwargs["executable_path"] = chromium_path
    return launch_kwargs


def render_report_pdf_from_urls(target_urls: list[str], out_path: Path) -> None:
    """
    Abre report.html?pdf=1 no Chromium e grava PDF em out_path.

    Substitui window.print() / report.html?print=1 (motor de impressão do navegador).
    """
    try:
        pw_mod = importlib.import_module("playwright.sync_api")
        sync_playwright = pw_mod.sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright não instalado. Instale com: "
            "pip install playwright && python -m playwright install chromium"
        ) from exc

    out_path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**_chromium_launch_kwargs())
        try:
            page = browser.new_page(
                viewport={"width": 1240, "height": 1754},
                device_scale_factor=1,
            )
            page.emulate_media(media="print")

            try:
                page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
                page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            except Exception:
                pass

            loaded = False
            for url in target_urls:
                try:
                    response = page.goto(url, wait_until="load", timeout=120_000)
                    if response is not None and response.status >= 400:
                        raise RuntimeError(f"HTTP {response.status} ao abrir {url}")
                    loaded = True
                    break
                except Exception as exc:
                    last_error = exc
                    continue

            if not loaded:
                raise RuntimeError(
                    "Não foi possível abrir o relatório HTML para gerar PDF. "
                    f"Último erro: {last_error}"
                )

            try:
                page.evaluate(
                    """
                    async () => {
                        if (document.fonts && document.fonts.ready) {
                            await document.fonts.ready;
                        }
                        const imgs = Array.from(document.images || []);
                        await Promise.all(imgs.map(img => {
                            if (img.complete) return Promise.resolve();
                            return new Promise(resolve => {
                                img.onload = resolve;
                                img.onerror = resolve;
                                setTimeout(resolve, 3000);
                            });
                        }));
                    }
                    """
                )
            except Exception:
                pass

            page.wait_for_timeout(750)

            page.pdf(
                path=str(out_path),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=False,
                margin={
                    "top": "0",
                    "right": "0",
                    "bottom": "0",
                    "left": "0",
                },
            )
        finally:
            browser.close()


def render_report_pdf(html: str, *, timeout_ms: int = 120_000) -> bytes:
    """
    Renderiza HTML do relatório em PDF A4 (string em memória).

    Usado por scripts/offline; o endpoint HTTP prefere render_report_pdf_from_urls.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright não instalado. Execute: python -m playwright install chromium"
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**_chromium_launch_kwargs())
        try:
            page = browser.new_page()
            page.emulate_media(media="print")
            page.set_content(html, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(300)
            return page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=False,
                margin={
                    "top": _PDF_MARGIN_TOP,
                    "right": _PDF_MARGIN_SIDE,
                    "bottom": _PDF_MARGIN_BOTTOM,
                    "left": _PDF_MARGIN_SIDE,
                },
            )
        finally:
            browser.close()
