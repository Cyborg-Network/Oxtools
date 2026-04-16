"""
Screenshot to Code — Tool Entry Point
=======================================
Converts UI screenshots to HTML + Tailwind code using vision models.

Pipeline: Upload → Compress → Vision Model → HTML → Chromium Render → Pixel Diff
"""

import os
import asyncio
import base64
import tempfile
import time
import threading
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

from openai import OpenAI
from PIL import Image, ImageChops

logger = logging.getLogger("screenshot-to-code")

# ─── MANIFEST ──────────────────────────────────────────────────────────
MANIFEST = {
    "id": "screenshot-to-code",
    "name": "Screenshot to Code",
    "description": "Upload a UI screenshot and get Tailwind/React code instantly with pixel-accuracy scoring",
    "author": "ArunMadhavan EVR",
    "version": "4.0.0",
}

# ─── Config ────────────────────────────────────────────────────────────
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 800
COMPRESS_MAX_PX = 1024
COMPRESS_JPEG_QUALITY = 85
RATE_LIMIT_MAX = 5

_rate_store: dict[str, int] = {}
_rate_lock = threading.Lock()

SYSTEM_PROMPT = """You are an expert frontend developer and UI architect. Recreate the provided UI screenshot identically using HTML and Tailwind CSS.
CRITICAL INSTRUCTIONS:
1. Structure First: Analyze the layout. Rigorously use Flexbox and CSS Grid.
2. Pixel Perfection: Use exact Tailwind arbitrary values (e.g., `w-[15px]`, `bg-[#ff6600]`).
3. Typography: Replicate font sizes, weights, and alignments exactly.
4. Images & Icons: Generate accurate inline SVG for icons. Use placehold.co for images.
5. Zero Interactivity: NO <script> tags or JavaScript.
OUTPUT FORMAT: Return ONLY raw HTML starting with <!DOCTYPE html>. Include the Tailwind CDN."""


# ─── Image Processing ─────────────────────────────────────────────────
def compress_image(raw_bytes: bytes) -> tuple[str, str, Image.Image]:
    """Compress uploaded image for vision model."""
    img = Image.open(BytesIO(raw_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((COMPRESS_MAX_PX, COMPRESS_MAX_PX))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=COMPRESS_JPEG_QUALITY)
    encoded = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return encoded, "image/jpeg", img


def call_vision_model(client: OpenAI, image_b64: str, mime: str,
                      prev_code: Optional[str] = None, update_prompt: Optional[str] = None) -> str:
    """Call vision model to generate HTML from screenshot."""
    for attempt in range(2):
        try:
            if prev_code and update_prompt:
                text = f"Previously generated HTML:\n```html\n{prev_code}\n```\nUpdate: {update_prompt}\nReturn ONLY updated HTML."
            else:
                text = "Convert this UI screenshot into a complete HTML document using Tailwind CSS. Return ONLY raw HTML."

            response = client.chat.completions.create(
                model="kimi-k2.5",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                        {"type": "text", "text": text},
                    ]},
                ],
                max_tokens=2048,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            if "429" in str(exc) and "Concurrency" in str(exc) and attempt == 0:
                time.sleep(5)
                continue
            raise exc
    raise RuntimeError("Vision API failed after retry")


async def render_and_diff(html: str, ref_image: Image.Image) -> Optional[str]:
    """Render HTML in headless Chromium and compute pixel-diff accuracy."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as tmp:
            tmp.write(html)
            tmp_path = Path(tmp.name)

        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
            await page.goto(tmp_path.as_uri(), wait_until="networkidle")
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            await browser.close()

        rendered = Image.open(BytesIO(screenshot_bytes)).convert("RGB")
        ref_resized = ref_image.resize(rendered.size, Image.LANCZOS)
        diff = ImageChops.difference(ref_resized, rendered).convert("L")
        pixels = list(diff.getdata())
        identical = sum(1 for p in pixels if p == 0)
        accuracy = (identical / len(pixels)) * 100.0
        return f"{accuracy:.1f}%"
    except Exception:
        return None
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# ─── RUN (called by unified runner) ──────────────────────────────────
async def run(data: dict) -> dict:
    """
    Execute screenshot-to-code pipeline.

    Expects data with base64 image or file bytes.
    Returns: {"code": "<html>...", "accuracy_score": "94.2%" | null}
    """
    api_key = os.getenv("OXLO_API_KEY")
    if not api_key:
        return {"error": "OXLO_API_KEY not configured"}

    # Handle base64 image from frontend
    image_b64 = data.get("image", "")
    if not image_b64:
        return {"error": "No image provided. Send base64 image in 'image' field."}

    # Decode base64 to bytes
    try:
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]
        raw_bytes = base64.b64decode(image_b64)
    except Exception as e:
        return {"error": f"Invalid base64 image: {e}"}

    # Compress
    compressed_b64, mime, ref_image = compress_image(raw_bytes)

    # Generate code
    client = OpenAI(api_key=api_key, base_url="https://api.oxlo.ai/v1")
    prev_code = data.get("previous_code")
    update_prompt = data.get("update_prompt")

    loop = asyncio.get_event_loop()
    html = await loop.run_in_executor(
        None, call_vision_model, client, compressed_b64, mime, prev_code, update_prompt
    )

    # Render and diff
    accuracy = await render_and_diff(html, ref_image)

    return {"code": html, "accuracy_score": accuracy}
