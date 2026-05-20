import tempfile
from pathlib import Path
from typing import Optional
from PIL import Image
from io import BytesIO
from config import logger


async def _render_html(html: str, viewport_size: tuple[int, int]) -> Optional[Image.Image]:
    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(html)
            tmp_path = Path(tmp.name)

        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage",
                      "--disable-gpu", "--disable-setuid-sandbox"],
            )
            page = await browser.new_page(
                viewport={"width": viewport_size[0], "height": viewport_size[1]},
                device_scale_factor=1,
            )
            await page.goto(tmp_path.as_uri(), wait_until="networkidle", timeout=30_000)
            try:
                await page.wait_for_function(
                    "() => document.readyState === 'complete'", timeout=8_000)
            except Exception:
                pass
            await page.wait_for_timeout(1200)
            shot = await page.screenshot(type="png", full_page=True)
            await browser.close()
        return Image.open(BytesIO(shot)).convert("RGB")
    except Exception as exc:
        logger.error("Render failed: %s", exc)
        return None
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
