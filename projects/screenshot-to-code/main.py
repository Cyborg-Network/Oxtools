"""
main.py  —  Screenshot to Code API  (v3)

Pipeline
--------
1. Compress the uploaded image with Pillow (max 1024 px, RGB JPEG).
2. Send the compressed image to mistral-7b via the Oxlo API to generate
   a complete HTML + Tailwind document.
3. Render that HTML in a headless Chromium browser (Playwright) inside a
   temporary file, and capture a viewport screenshot.
4. Pixel-diff the original image (resized to viewport dimensions) against
   the Playwright screenshot using PIL.ImageChops.  Calculate an exact
   accuracy percentage from the ratio of identical pixels to total pixels.
5. Return { code, accuracy_score } to the caller.  If Playwright is
   unavailable or fails, accuracy_score is returned as null.

API surface
-----------
GET  /api/oxtools  →  tool manifest (list-wrapped for the Oxlo registry)
POST /api/generate →  multipart image upload; JSON response
GET  /             →  static/index.html
"""

from __future__ import annotations

import os
import json
import base64
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from openai import OpenAI
from PIL import Image, ImageChops

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(title="Screenshot to Code", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MANIFEST_PATH: Path = Path(__file__).parent / "oxlo-manifest.json"

# Viewport used for both Playwright rendering and image resizing.
# 1280 × 800 is a common baseline for UI diffing.
VIEWPORT_WIDTH: int = 1280
VIEWPORT_HEIGHT: int = 800

# Maximum longest-side dimension when compressing the uploaded image before
# sending it to the vision model.
COMPRESS_MAX_PX: int = 1024
COMPRESS_JPEG_QUALITY: int = 85

# ---------------------------------------------------------------------------
# Manifest endpoint
# ---------------------------------------------------------------------------


@app.get("/api/oxtools")
async def serve_tool_manifest() -> JSONResponse:
    """
    Return the contents of oxlo-manifest.json.

    The Oxlo registry client expects a JSON array; the manifest dict is
    therefore wrapped in a single-element list.

    Raises:
        HTTPException 404 if the manifest file does not exist on disk.
    """
    if not MANIFEST_PATH.exists():
        raise HTTPException(status_code=404, detail="oxlo-manifest.json not found.")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return JSONResponse(content=[data])


# ---------------------------------------------------------------------------
# Image compression
# ---------------------------------------------------------------------------


def compress_uploaded_image(raw_bytes: bytes) -> tuple[str, str, Image.Image]:
    """
    Decode, resize, and re-encode an uploaded image for vision-model delivery.

    Steps:
      - Open the raw bytes with Pillow.
      - Convert to RGB (removes alpha channel from PNGs and paletted images).
      - Constrain the longest side to COMPRESS_MAX_PX using thumbnail(), which
        preserves the aspect ratio.
      - Encode the result as a JPEG at COMPRESS_JPEG_QUALITY.

    Returns:
        Tuple of (base64_string, mime_type, pillow_image_object).
        The Pillow image object is returned so the caller can reuse it for
        the pixel-diff step without decoding a second time.

    Raises:
        HTTPException 422 if the bytes cannot be decoded as an image.
    """
    try:
        img: Image.Image = Image.open(BytesIO(raw_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((COMPRESS_MAX_PX, COMPRESS_MAX_PX))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=COMPRESS_JPEG_QUALITY)
        encoded = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
        return encoded, "image/jpeg", img
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Image pre-processing failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

_GENERATION_SYSTEM_PROMPT = """
You are a senior frontend developer specialising in HTML and Tailwind CSS.

Your task is to convert the provided UI screenshot into a complete, self-contained
HTML document that faithfully reproduces the layout, typography, colour scheme,
spacing, and every visible UI component.

Strict output rules:
  - Return raw HTML only.  No markdown code fences.  No prose explanations.
  - The document must include the Tailwind CSS CDN <script> tag in <head>.
  - Use semantic HTML5 elements: <header>, <main>, <section>, <nav>, <footer>.
  - Every interactive element (button, input, link) must include Tailwind hover
    and focus variants where applicable.
  - Do not invent content or UI that is not visible in the screenshot.
""".strip()


def build_image_url_part(b64: str, mime: str) -> dict:
    """Return a vision message part containing an inline base64 image."""
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}"},
    }


def call_vision_model(
    client: OpenAI,
    model: str,
    image_b64: str,
    mime_type: str,
) -> str:
    """
    Send the screenshot to the vision model and return the generated HTML.

    Args:
        client:     Initialised OpenAI client pointed at api.oxlo.ai/v1.
        model:      Model identifier (e.g. "mistral-7b").
        image_b64:  Base64-encoded JPEG of the compressed screenshot.
        mime_type:  MIME type string for the image data URI.

    Returns:
        Raw HTML string as returned by the model.

    Raises:
        HTTPException 502 on any API-level error.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _GENERATION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        build_image_url_part(image_b64, mime_type),
                        {
                            "type": "text",
                            "text": (
                                "Convert this UI screenshot into a complete HTML document "
                                "using Tailwind CSS.  Return only the HTML, no markdown."
                            ),
                        },
                    ],
                },
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Oxlo API request failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Headless render + pixel diff
# ---------------------------------------------------------------------------


async def render_html_and_diff(
    html_source: str,
    reference_image: Image.Image,
) -> Optional[str]:
    """
    Render the generated HTML in a headless Chromium browser and compute a
    pixel-accurate similarity score against the original screenshot.

    Algorithm:
      1. Write html_source to a temporary file.
      2. Launch Playwright Chromium with a fixed viewport (VIEWPORT_WIDTH ×
         VIEWPORT_HEIGHT).
      3. Navigate to the file URI and take a full-page screenshot as PNG bytes.
      4. Open the screenshot with Pillow.
      5. Resize the reference image to match the Playwright screenshot
         dimensions exactly (LANCZOS resampling for quality).
      6. Compute the per-channel absolute difference via PIL.ImageChops.difference.
      7. Convert the difference image to greyscale.
      8. Count pixels where the greyscale value is zero (identical pixels).
      9. accuracy = identical_pixels / total_pixels * 100.

    Returns:
        Formatted accuracy string such as "94.2%" on success, or None if
        Playwright cannot be initialised (e.g. browser not installed in the
        current environment).

    Note:
        The temporary HTML file is deleted in a finally block regardless of
        outcome.  No temp files are left on disk.
    """
    tmp_path: Optional[Path] = None
    try:
        # Write generated HTML to a named temporary file.
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".html",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(html_source)
            tmp_path = Path(tmp.name)

        # Import inside the function so the server still starts if the
        # playwright package is present but browsers are not installed.
        from playwright.async_api import async_playwright  # noqa: PLC0415

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(
                viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT}
            )
            await page.goto(tmp_path.as_uri(), wait_until="networkidle")
            screenshot_bytes: bytes = await page.screenshot(type="png", full_page=False)
            await browser.close()

        # Load the Playwright screenshot.
        rendered_img: Image.Image = Image.open(BytesIO(screenshot_bytes)).convert("RGB")
        render_w, render_h = rendered_img.size

        # Resize the reference image to exactly match the rendered dimensions
        # so the pixel arrays align for the diff operation.
        ref_resized: Image.Image = reference_image.resize(
            (render_w, render_h), Image.LANCZOS
        )

        # Pixel-by-pixel absolute difference across all channels.
        diff_img: Image.Image = ImageChops.difference(ref_resized, rendered_img)

        # Collapse RGB channels to a single greyscale channel.
        diff_grey = diff_img.convert("L")

        # Load pixel data as a flat sequence for counting.
        diff_pixels = list(diff_grey.getdata())
        total_pixels: int = len(diff_pixels)
        identical_pixels: int = sum(1 for p in diff_pixels if p == 0)

        accuracy: float = (identical_pixels / total_pixels) * 100.0
        return f"{accuracy:.1f}%"

    except ImportError:
        # Playwright package is installed but the async_api import failed —
        # treat as graceful degradation.
        return None
    except Exception:
        # Any browser launch or navigation error is non-fatal.
        return None
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# POST /api/generate
# ---------------------------------------------------------------------------


@app.post("/api/generate")
async def generate_code(file: UploadFile = File(...)) -> JSONResponse:
    """
    Accept a UI screenshot and return generated HTML with a pixel-diff score.

    Workflow:
      1. Validate the uploaded file is an image.
      2. Read API credentials from environment variables.
      3. Compress the image with Pillow.
      4. Call the Oxlo vision model to generate HTML.
      5. Render the HTML in headless Chromium and compute a pixel-diff score.
      6. Return { code, accuracy_score }.

    Response body:
        {
            "code":           "<complete HTML document>",
            "accuracy_score": "94.2%" | null
        }

    accuracy_score is null when Playwright is unavailable or the render fails.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file must be an image (PNG, JPG, or WEBP).",
        )

    api_key: Optional[str] = os.environ.get("OXLO_API_KEY")
    model: str = os.environ.get("OXLO_VISION_MODEL", "mistral-7b")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OXLO_API_KEY environment variable is not set.",
        )

    oxlo_client = OpenAI(api_key=api_key, base_url="https://api.oxlo.ai/v1")

    raw_bytes: bytes = await file.read()

    # Step 1: Compress and encode image for the vision API.
    image_b64, mime_type, reference_pil_image = compress_uploaded_image(raw_bytes)

    # Step 2: Generate HTML from the compressed screenshot.
    generated_html: str = call_vision_model(oxlo_client, model, image_b64, mime_type)

    # Step 3: Render in headless Chromium and pixel-diff against the original.
    accuracy_score: Optional[str] = await render_html_and_diff(
        generated_html, reference_pil_image
    )

    return JSONResponse(
        content={"code": generated_html, "accuracy_score": accuracy_score}
    )


# ---------------------------------------------------------------------------
# Static file serving
# Must be mounted last so /api/* routes are matched before the catch-all.
# ---------------------------------------------------------------------------

_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")