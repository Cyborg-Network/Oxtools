"""
Screenshot to Code — Multi-Agent Consensus Pipeline (v7.0)
===========================================================

Architecture:
  STEP 1 — Spatial Extraction   : qwen-3-32b    → layout_json  [SKIPPED for fresh gen]
  STEP 2 — Parallel Syntax Swarm: deepseek-coder-33b × 3 → [html_1, html_2, html_3]
  STEP 3 — Frontier Judge       : llama-3.3-70b → best_index
  STEP 4 — Chromium Render      : Playwright SSIM scoring

Fixes in v7.0:
  FIX #1 — Step 1 removed from fresh generation path (image sent directly to coder)
  FIX #2 — Token limits raised to 8192; JSON truncation guard replaces silent fallback
  FIX #3 — device_scale_factor=1 (was 2); Playwright wait increased to 1200ms
  FIX #4 — Inter/Roboto/DM Sans injected into HTML before render
  FIX #5 — Viewport normalised: retina screenshots halved, clamped to sane bounds
  FIX #6 — SSIM win_size=21 + gaussian_weights=True (less sensitive to sub-px shifts)
"""

import os
import asyncio
import base64
import json
import tempfile
import time
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
from openai import OpenAI
from PIL import Image
from skimage.metrics import structural_similarity as ssim_fn

logger = logging.getLogger("screenshot-to-code")

# ─── MANIFEST ─────────────────────────────────────────────────────────────────
MANIFEST = {
    "id": "screenshot-to-code",
    "name": "Screenshot to Code",
    "description": "Upload a UI screenshot and get Tailwind/HTML code via Multi-Agent Consensus Pipeline",
    "author": "ArunMadhavan EVR",
    "version": "7.0.0",
}

# ─── Config ───────────────────────────────────────────────────────────────────
COMPRESS_MAX_PX       = 1920  
COMPRESS_JPEG_QUALITY = 90

# Models
MODEL_EXTRACTOR = "Kimi-K2.6"   
MODEL_CODER     = "Kimi-K2.5"        
MODEL_JUDGE     = "Kimi-K2.6"  

OXLO_BASE_URL = "https://api.oxlo.ai/v1"

# Reverted to 4096 — free tier context limit
MAX_TOKENS_EXTRACT = 12000 
MAX_TOKENS_CODE    = 12000  
MAX_TOKENS_JUDGE   = 16   

SWARM_TEMPERATURES = [0.0, 0.1, 0.2]

# FIX #4 — font injection block added to every rendered HTML
FONT_INJECT = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Inter:wght@400;500;600;700&'
    'family=Roboto:wght@400;500;700&'
    'family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap" rel="stylesheet">'
    '<style>*,*::before,*::after{font-family:"Inter","Roboto","DM Sans",ui-sans-serif,system-ui,sans-serif;}</style>'
)

# ─── Step 1 Prompt — Spatial Extractor (used only for iterative edits) ───────
EXTRACTOR_SYSTEM = """You are an elite Computer Vision layout extractor.
Map this UI screenshot into a strict JSON layout array.

For each visible element output an object with these fields (all required):
{
  "id":        "unique-slug",
  "type":      "container" | "text" | "button" | "input" | "image" | "icon" | "divider" | "list-item",
  "tag":       "div" | "h1" | "p" | "button" | "input" | "img" | "svg" | "hr" | "a" | "li" | "span" | …,
  "layout":    "flex-row" | "flex-col" | "grid-N" | "block" | "absolute",
  "x_pct":     0-100,
  "y_pct":     0-100,
  "w_pct":     0-100,
  "h_pct":     0-100,
  "bg_color":  "#rrggbb" | "transparent",
  "text_color":"#rrggbb" | null,
  "font_size_px": number | null,
  "font_weight":  400 | 500 | 600 | 700 | null,
  "border_radius_px": number | null,
  "text_content": "exact visible string" | null,
  "href_visible": "domain string if link" | null,
  "children":  [ …nested objects… ] | []
}

RULES:
- COPY TEXT EXACTLY. Every string must be a verbatim copy of visible text. No placeholders, no guesses.
- For list-heavy UIs (news feeds, forums, tables): extract the header in full, then ALL visible list items — do not skip any readable row.
- Use exact hex colors sampled from the screenshot. No approximations.
- Maintain full structural nesting.
- DO NOT write HTML. DO NOT add commentary.
- Output ONLY a raw valid JSON array starting with [."""

EXTRACTOR_USER = (
    "Extract the COMPLETE JSON layout from this screenshot. "
    "Include every visible list item, link, and text string — do not skip any rows. "
    "Output ONLY the raw JSON array. No explanation, no markdown."
)

# ─── Step 2 Prompt — Syntax Swarm (Kimi-K2-Thinking) ────────────────────────
# FIX #1 — coder now receives raw screenshot directly, no JSON intermediary
CODER_SYSTEM = """You are a pixel-perfect UI compiler with vision capabilities.
You will be shown a UI screenshot. Reproduce it as HTML using Tailwind CSS.

CRITICAL RULES — violations will cause rejection:
1. Look at the screenshot carefully before writing a single line of HTML.
2. Use Tailwind arbitrary values for EVERY color, size, spacing: bg-[#1a1a2e] text-[13px] w-[340px] gap-[12px].
3. Copy ALL visible text character-for-character. Never invent, paraphrase, or omit any text.
4. Reproduce exact background colors, text colors, border colors from the screenshot.
5. Match layout structure: if it's a mobile screen, use a mobile-width container. If it's a desktop, use full width.
6. Render EVERY visible row, list item, and element — do not truncate dense lists.
7. Simple icons (back arrow, checkmark, search, hamburger): inline SVG matching the screenshot shape.
8. Profile photos, product images, logos: <img src="https://placehold.co/WxH/bgHex/fgHex"> with correct dimensions.
9. Status bar elements (time, battery, signal): reproduce as text/SVG, do not skip.
10. Bottom navigation bars: reproduce all tabs with correct icons and labels.
11. Include <script src="https://cdn.tailwindcss.com"></script> in <head>. No other scripts.
12. No JavaScript. No invented content.
13.CRITICAL: If the screenshot shows a browser window with tabs/address bar,reproduce ONLY the inner page content — not the browser chrome itself. The output must be the webpage content only, starting from the top of the page body.

OUTPUT: Raw HTML only, starting with <!DOCTYPE html>. Zero explanation. Zero markdown fences."""

CODER_USER = (
    "Look at this screenshot carefully. "
    "Identify: the exact background color, all text content word-for-word, "
    "every UI element and its position, and the overall layout structure. "
    "Then produce pixel-perfect HTML with Tailwind CSS reproducing it exactly. "
    "Output ONLY raw HTML starting with <!DOCTYPE html>. No explanation."
)

# ─── Step 3 Prompt — Frontier Judge (DeepSeek-R1-0528) ──────────────────────
JUDGE_SYSTEM = """You are a UI fidelity judge. Given 2-3 HTML candidates, pick the one that best matches a UI screenshot.

Score each candidate on:
- Text accuracy: does it have the exact same text as the screenshot? (most important)
- Color accuracy: correct background and text colors?
- Layout: correct structure, mobile vs desktop, element positions?
- Completeness: no missing rows, buttons, nav items?

Return ONLY the digit 1, 2, or 3. No explanation."""


# ─── Image helpers ─────────────────────────────────────────────────────────────
def compress_image(raw_bytes: bytes) -> tuple[str, str, Image.Image]:
    img = Image.open(BytesIO(raw_bytes))

    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode not in ("RGB",):
        img = img.convert("RGB")

    img.thumbnail((COMPRESS_MAX_PX, COMPRESS_MAX_PX), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=COMPRESS_JPEG_QUALITY, optimize=True)
    encoded = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    logger.info("Compressed image to %dx%d", *img.size)
    return encoded, "image/jpeg", img


# ─── FIX #5 — Viewport normalisation ──────────────────────────────────────────
def _normalise_viewport(ref_image: Image.Image) -> tuple[tuple[int, int], Image.Image]:
    """
    Return (viewport_size, normalised_ref_image) — both at the same resolution.
    CRITICAL: ref_image must be resized to match viewport or SSIM comparison is invalid.
    - If width > 1920 (retina), halves BOTH viewport AND ref_image
    - Clamps viewport to 320x400 minimum, 1920 max width
    """
    w, h = ref_image.size
    if w > 1920:
        w, h = w // 2, h // 2
        ref_image = ref_image.resize((w, h), Image.LANCZOS)
        logger.info("Retina detected — ref_image halved to %dx%d for SSIM alignment", w, h)
    w = max(320, min(w, 1920))
    h = max(400, h)
    return (w, h), ref_image


# ─── FIX #6 — SSIM with larger window ────────────────────────────────────────
def compute_ssim(ref: Image.Image, rendered: Image.Image) -> float:
    """
    Structural Similarity Index (0–100).
    win_size=21 + gaussian_weights=True makes it less sensitive to
    sub-pixel positional shifts that don't affect visual quality.
    """
    rendered_rgb = rendered.convert("RGB")
    ref_resized  = ref.resize(rendered_rgb.size, Image.LANCZOS).convert("RGB")

    ref_arr    = np.array(ref_resized,  dtype=np.float32)
    render_arr = np.array(rendered_rgb, dtype=np.float32)

    score = ssim_fn(
        ref_arr, render_arr,
        data_range=255.0,
        channel_axis=2,
        win_size=21,           # was 7 — less penalty for small positional shifts
        gaussian_weights=True, # perceptually weighted
    )
    return max(0.0, float(score)) * 100.0


# ─── Generic API call helper ──────────────────────────────────────────────────
def _call_api(
    client: OpenAI,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0.0,
    attempt_limit: int = 3,
) -> str:
    last_exc: Exception = RuntimeError("No attempts made")

    for attempt in range(attempt_limit):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""

        except Exception as exc:
            last_exc = exc
            err = str(exc)
            is_rate   = "429" in err
            is_server = err[:1] == "5"

            if (is_rate or is_server) and attempt < attempt_limit - 1:
                wait = 4 ** attempt
                logger.warning("[%s] attempt %d failed (%s...), retry in %ds",
                               model, attempt + 1, err[:60], wait)
                time.sleep(wait)
            else:
                break

    raise RuntimeError(f"[{model}] failed after {attempt_limit} attempts: {last_exc}")


# ─── HTML cleanup + FIX #4 font injection ────────────────────────────────────
def _clean_html(raw: str) -> str:
    """Strip markdown fences, anchor to <!DOCTYPE, inject fonts."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    lower = raw.lower()
    for tag in ("<!doctype", "<html"):
        idx = lower.find(tag)
        if idx != -1:
            raw = raw[idx:]
            break

    # FIX #4 — inject Google Fonts after </head> open tag so fonts load before render
    if "</head>" in raw.lower():
        insert_at = raw.lower().find("</head>")
        raw = raw[:insert_at] + FONT_INJECT + raw[insert_at:]
    elif "<head>" in raw.lower():
        insert_at = raw.lower().find("<head>") + len("<head>")
        raw = raw[:insert_at] + FONT_INJECT + raw[insert_at:]

    return raw


# ─── FIX #3 — Playwright render with scale_factor=1 and longer wait ──────────
async def _render_html(html: str, viewport_size: tuple[int, int]) -> Optional[Image.Image]:
    """
    Render HTML in headless Chromium.
    FIX #3: device_scale_factor=1 (was 2 — caused 2x pixel mismatch in SSIM).
    FIX #3: wait increased to 1200ms + Tailwind readiness check.
    """
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
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-setuid-sandbox",
                ],
            )
            page = await browser.new_page(
                viewport={"width": viewport_size[0], "height": viewport_size[1]},
                device_scale_factor=1,  # FIX #3: was 2, caused 2x pixel dims
            )
            await page.goto(tmp_path.as_uri(), wait_until="networkidle", timeout=30_000)

            # FIX #3: wait for Tailwind CDN to finish applying classes
            try:
                await page.wait_for_function(
                    "() => document.readyState === 'complete'",
                    timeout=8_000,
                )
            except Exception:
                pass  # proceed even if check times out

            await page.wait_for_timeout(1200)  # FIX #3: was 700ms

            shot = await page.screenshot(type="png", full_page=True)
            await browser.close()

        return Image.open(BytesIO(shot)).convert("RGB")

    except Exception as exc:
        logger.error("Render failed: %s", exc)
        return None
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Spatial Extraction (used ONLY for iterative edits, not fresh gen)
# ═══════════════════════════════════════════════════════════════════════════════
def _step1_extract_layout(client: OpenAI, image_b64: str, mime: str) -> str:
    """
    Sends the image to qwen-3-32b and returns layout JSON.
    Only called in iterative edit mode, NOT in fresh generation.
    FIX #2: raises RuntimeError on unrecoverable JSON instead of silently passing broken data.
    """
    logger.info("[Step 1] Spatial extraction via %s", MODEL_EXTRACTOR)
    messages = [
        {"role": "system", "content": EXTRACTOR_SYSTEM},
        {"role": "user", "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"}},
            {"type": "text", "text": EXTRACTOR_USER},
        ]},
    ]
    raw = _call_api(client, MODEL_EXTRACTOR, messages, MAX_TOKENS_EXTRACT, temperature=0.0)

    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    # FIX #2 — replace silent fallback with truncation guard
    try:
        json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("[Step 1] JSON invalid (%s) — attempting truncation repair", e)
        last_bracket = raw.rfind("}")
        if last_bracket != -1:
            raw = raw[:last_bracket + 1] + "]"
        try:
            json.loads(raw)
            logger.info("[Step 1] Truncation repair succeeded")
        except json.JSONDecodeError:
            raise RuntimeError(f"[Step 1] Unrecoverable JSON after repair: {e}")

    logger.info("[Step 1] Layout extracted (%d chars)", len(raw))
    return raw


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Parallel Syntax Swarm (deepseek-coder-33b × 3)
# FIX #1 — sends screenshot directly, no JSON intermediary for fresh generation
# ═══════════════════════════════════════════════════════════════════════════════
async def _step2_syntax_swarm(
    client: OpenAI,
    image_b64: str,
    mime: str,
    layout_json: Optional[str] = None,
) -> list[str]:
    """
    Fires 3 parallel deepseek-coder-33b calls.
    FIX #1: For fresh generation, sends raw screenshot directly (layout_json=None).
    For iterative edits with layout_json, appends JSON as additional context.
    """
    logger.info("[Step 2] Syntax swarm — %d × %s in parallel", len(SWARM_TEMPERATURES), MODEL_CODER)

    # FIX #1 — direct screenshot path, no JSON needed
    if layout_json:
        # iterative path: include JSON as extra context (rare)
        extra = f"\n\nAdditional layout context (JSON):\n```json\n{layout_json}\n```"
        user_text = CODER_USER + extra
    else:
        user_text = CODER_USER

    def _make_coder_call(temperature: float) -> str:
        messages = [
            {"role": "system", "content": CODER_SYSTEM},
            {"role": "user", "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"}},
                {"type": "text", "text": user_text},
            ]},
        ]
        return _call_api(client, MODEL_CODER, messages, MAX_TOKENS_CODE, temperature=temperature)

    loop = asyncio.get_event_loop()
    logger.info("[Step 2] image_b64 length: %d chars — model: %s", len(image_b64), MODEL_CODER)
    tasks = [loop.run_in_executor(None, _make_coder_call, t) for t in SWARM_TEMPERATURES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    candidates: list[str] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.warning("[Step 2] Candidate %d failed: %s", i + 1, r)
        else:
            html = _clean_html(r)
            candidates.append(html)
            logger.info("[Step 2] Candidate %d OK (%d chars)", i + 1, len(html))

    if not candidates:
        raise RuntimeError("[Step 2] All swarm candidates failed")

    return candidates


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Frontier Judge (Kimi-K2-Thinking — vision model)
# ═══════════════════════════════════════════════════════════════════════════════
def _step3_judge(
    client: OpenAI,
    candidates: list[str],
    image_b64: str,
    mime: str,
    layout_json: Optional[str] = None,
) -> int:
    """
    Picks the best HTML candidate.
    Judge receives the original screenshot so it can compare visually, not just by HTML text.
    Uses layout_json as ground truth if available.
    """
    if len(candidates) == 1:
        logger.info("[Step 3] Only 1 candidate — skipping judge")
        return 0

    logger.info("[Step 3] Judging %d candidates via %s", len(candidates), MODEL_JUDGE)

    parts = []
    if layout_json:
        parts.append(f"REFERENCE JSON (ground truth):\n```json\n{layout_json}\n```\n")
        parts.append("Judge which HTML candidate best implements this JSON layout.")
    else:
        parts.append("The image above is the original UI screenshot. Judge which HTML candidate best reproduces it.")
        parts.append("Check for: exact text content, correct colors, correct layout, no hallucinations.")

    for i, html in enumerate(candidates, 1):
        preview = html if len(html) <= 10_000 else html[:10_000] + "\n… [truncated]"
        parts.append(f"\nCANDIDATE {i}:\n```html\n{preview}\n```")

    parts.append("\nReply with ONLY the digit 1, 2, or 3.")
    user_text = "\n".join(parts)

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": [
            # Judge sees the original screenshot for visual comparison
            {"type": "image_url",
             "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"}},
            {"type": "text", "text": user_text},
        ]},
    ]

    raw = _call_api(client, MODEL_JUDGE, messages, MAX_TOKENS_JUDGE, temperature=0.0)
    raw = raw.strip()
    logger.info("[Step 3] Judge raw response: %r", raw)

    for ch in raw:
        if ch.isdigit():
            idx = int(ch) - 1
            if 0 <= idx < len(candidates):
                logger.info("[Step 3] Judge selected candidate %d", idx + 1)
                return idx

    logger.warning("[Step 3] Could not parse judge response %r, falling back to 0", raw)
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Chromium Render + SSIM Score
# ═══════════════════════════════════════════════════════════════════════════════
async def _step4_render_and_score(
    html: str,
    ref_image: Image.Image,
) -> tuple[float, Optional[Image.Image]]:
    # _normalise_viewport returns BOTH viewport size AND the resized ref_image
    # so SSIM always compares images at identical resolution
    target_size, ref_image = _normalise_viewport(ref_image)
    logger.info("[Step 4] Rendering in Chromium at %dx%d", *target_size)
    rendered = await _render_html(html, target_size)
    if rendered is None:
        logger.error("[Step 4] Render failed — SSIM set to 0")
        return 0.0, None

    # Crop rendered to ref height before SSIM — full_page=True captures
    # entire scroll height but ref is only viewport height
    ref_h = ref_image.size[1]
    if rendered.size[1] > ref_h:
        rendered = rendered.crop((0, 0, rendered.size[0], ref_h))

    score = compute_ssim(ref_image, rendered)
    logger.info("[Step 4] SSIM = %.1f%%", score)
    return score, rendered


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
async def _run_pipeline(
    raw_bytes: bytes,
    prev_code: Optional[str] = None,
    update_prompt: Optional[str] = None,
) -> dict:
    api_key = os.getenv("OXLO_API_KEY", "")
    if not api_key:
        return {"error": "OXLO_API_KEY not configured"}

    client = OpenAI(api_key=api_key, base_url=OXLO_BASE_URL)
    t0 = time.perf_counter()

    image_b64, mime, ref_image = compress_image(raw_bytes)

    # ── Iterative edit shortcut ───────────────────────────────────────────────
    if prev_code and update_prompt:
        logger.info("Iterative edit mode — single-model direct call")
        loop = asyncio.get_event_loop()
        edit_user = (
            f"Previously generated HTML:\n```html\n{prev_code}\n```\n\n"
            f"Update request: {update_prompt}\n\n"
            "Return ONLY the complete updated HTML starting with <!DOCTYPE html>. No explanation."
        )
        raw = await loop.run_in_executor(
            None, _call_api, client, MODEL_CODER,
            [
                {"role": "system", "content": CODER_SYSTEM},
                {"role": "user", "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"}},
                    {"type": "text", "text": edit_user},
                ]},
            ],
            MAX_TOKENS_CODE, 0.0, 3,
        )
        html = _clean_html(raw)
        ssim_score, rendered = await _step4_render_and_score(html, ref_image)
        total_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "code":               html,
            "accuracy_score":     f"{ssim_score:.1f}%",
            "ssim_score":         f"{ssim_score:.1f}%",
            "generation_time_ms": total_ms,
            "pass_count":         1,
            "layout_json":        None,
        }

    # ── FIX #1 — STEP 1 SKIPPED for fresh generation ─────────────────────────
    # Screenshot goes directly to the coder swarm. No JSON extraction step.
    # layout_json kept as None — judge will evaluate HTML quality directly.

    # ── STEP 2: Parallel Syntax Swarm (image → HTML directly) ────────────────
    candidates = await _step2_syntax_swarm(client, image_b64, mime, layout_json=None)

    # ── STEP 3: Frontier Judge ────────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    best_idx = await loop.run_in_executor(
        None, _step3_judge, client, candidates, image_b64, mime, None
    )
    best_html = candidates[best_idx]
    logger.info("Judge selected candidate %d / %d", best_idx + 1, len(candidates))

    # ── STEP 4: Chromium Render + SSIM ───────────────────────────────────────
    ssim_score, rendered = await _step4_render_and_score(best_html, ref_image)

    total_ms = int((time.perf_counter() - t0) * 1000)
    logger.info("Pipeline complete in %dms — SSIM %.1f%%", total_ms, ssim_score)

    if rendered:
        try:
            rendered.save("debug_final_render.png")
        except Exception:
            pass

    return {
        "code":               best_html,
        "accuracy_score":     f"{ssim_score:.1f}%",
        "ssim_score":         f"{ssim_score:.1f}%",
        "generation_time_ms": total_ms,
        "pass_count":         1,
        "layout_json":        None,       # Step 1 skipped in fresh gen
        "candidate_count":    len(candidates),
        "selected_candidate": best_idx + 1,
    }


# ─── Public entry point ───────────────────────────────────────────────────────
async def run(data: dict) -> dict:
    """
    Execute the Multi-Agent Consensus Pipeline.

    Input dict keys:
      image          — base64 image string (with or without data: prefix)  [required]
      previous_code  — prior HTML for iterative editing                     [optional]
      update_prompt  — instruction for the edit                             [optional]

    Returns:
      code               — best generated HTML
      accuracy_score     — SSIM % string e.g. "87.3%"
      ssim_score         — same as accuracy_score
      generation_time_ms — total wall-clock ms
      pass_count         — always 1 for this pipeline
      layout_json        — None (Step 1 skipped for fresh gen)
      candidate_count    — how many swarm candidates were produced
      selected_candidate — 1-based index of the judge's pick
      error              — present only on failure
    """
    image_b64 = data.get("image", "")
    if not image_b64:
        return {"error": "No image provided. Send base64 image in 'image' field."}

    try:
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]
        raw_bytes = base64.b64decode(image_b64)
    except Exception as exc:
        return {"error": f"Invalid base64 image: {exc}"}

    try:
        return await _run_pipeline(
            raw_bytes,
            prev_code=data.get("previous_code"),
            update_prompt=data.get("update_prompt"),
        )
    except Exception as exc:
        logger.error("Pipeline error: %s", exc, exc_info=True)
        return {"error": str(exc)}