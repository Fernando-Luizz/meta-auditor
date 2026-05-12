"""
Rasteriza app/static/favicon.svg → apple-touch-icon.png (180×180) e favicon.ico (16×16 + 32×32).

Requer: Chromium do Playwright (`playwright install chromium`) e Pillow.

    python scripts/generate_favicon_assets.py
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
SVG_PATH = STATIC / "favicon.svg"


def main() -> None:
    if not SVG_PATH.is_file():
        raise SystemExit(f"Arquivo não encontrado: {SVG_PATH}")

    b64 = base64.standard_b64encode(SVG_PATH.read_bytes()).decode()
    data_url = f"data:image/svg+xml;base64,{b64}"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=1)
        page.set_content(
            f"""<!DOCTYPE html><html><head>
<meta charset="utf-8"><style>html,body{{margin:0;padding:0;background:#fff;}}</style></head><body>
<img id="i" src="{data_url}" width="256" height="256" alt="" />
</body></html>"""
        )
        page.wait_for_selector("#i")
        png_bytes = page.locator("#i").screenshot(type="png")
        browser.close()

    master = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    master.resize((180, 180), Image.Resampling.LANCZOS).save(
        STATIC / "apple-touch-icon.png", "PNG"
    )
    im32 = master.resize((32, 32), Image.Resampling.LANCZOS)
    im16 = master.resize((16, 16), Image.Resampling.LANCZOS)
    im16.save(
        STATIC / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32)],
        append_images=[im32],
    )
    print(f"OK: {STATIC / 'apple-touch-icon.png'}")
    print(f"OK: {STATIC / 'favicon.ico'}")


if __name__ == "__main__":
    main()
