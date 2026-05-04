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
    "version": "9.0.0",
}

# ─── Config ───────────────────────────────────────────────────────────────────
COMPRESS_MAX_PX       = 1920
COMPRESS_JPEG_QUALITY = 90

MODEL_CODER = "kimi-k2.5"
MODEL_JUDGE = "kimi-k2.5"

OXLO_BASE_URL = "https://api.oxlo.ai/v1"

# NEW #9 — raised from 12000
MAX_TOKENS_EXTRACT = 12000
MAX_TOKENS_CODE    = 16000
# NEW #8 — raised from 16. Judge now has room to reason before answering.
# The system prompt instructs it to still end with just the digit,
# but giving it 512 tokens lets it think through the candidates properly.
MAX_TOKENS_JUDGE   = 2048

# ── Strategy swarm (unchanged from v8.0) ─────────────────────────────────────
SWARM_STRATEGIES = [
    {
        "name": "structure-first",
        "temperature": 0.0,
        "prefix": (
            "═══ STRATEGY: STRUCTURE-FIRST ═══\n"
            "Before writing a single HTML tag, reason through:\n"
            "  1. What is the outermost container? (full-width, fixed-width, mobile?)\n"
            "  2. What are the major layout sections? (header, sidebar, main, footer?)\n"
            "  3. What CSS layout system governs each section? (flex-row, flex-col, grid?)\n"
            "  4. What are the background colors of each section? (sample exact hex)\n"
            "Only then write the HTML, outside-in from largest container to smallest leaf.\n\n"
        ),
    },
    {
        "name": "typography-first",
        "temperature": 0.0,
        "prefix": (
            "═══ STRATEGY: TYPOGRAPHY-FIRST ═══\n"
            "Before writing a single HTML tag, inventory every text element:\n"
            "  1. List every visible string, its approximate px size, weight, and color.\n"
            "  2. Identify heading hierarchy (h1/h2/h3) from visual prominence.\n"
            "  3. Note any monospace, italic, or special-weight text.\n"
            "  4. Mark interactive text (links, buttons, labels) separately.\n"
            "Build the HTML by placing text elements first, then wrap them in layout containers.\n\n"
        ),
    },
    {
        "name": "component-first",
        "temperature": 0.0,
        "prefix": (
            "═══ STRATEGY: COMPONENT-FIRST ═══\n"
            "Before writing a single HTML tag, decompose the UI into components:\n"
            "  1. Identify discrete, reusable UI components (navbar, card, badge, list-row, tab-bar).\n"
            "  2. For each component: note its exact background, border, shadow, and padding.\n"
            "  3. Identify which components repeat (list items, table rows, grid cards).\n"
            "  4. Note the exact count of repeating items — do NOT truncate lists.\n"
            "Implement each component as a self-contained HTML block, then compose the full page.\n\n"
        ),
    },
]

# ── NEW #12 — Healing constants (raised thresholds for higher quality bar) ────
SSIM_SHIP_THRESHOLD  = 92.0   # NEW #12: was 88 — keep healing until 92%
SSIM_HEAL_THRESHOLD  = 55.0   # abort floor — below this model is lost
MAX_HEALING_PASSES   = 3      # NEW #11: was 2
DIFF_PIXEL_THRESHOLD = 12.0   # slightly tighter than v8.0's 15.0

# ── Slice constants (unchanged) ───────────────────────────────────────────────
SLICE_ASPECT_THRESHOLD = 2.5
SLICE_N                = 3

# ── Font injection (unchanged from v7.0) ─────────────────────────────────────
FONT_INJECT = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Inter:wght@400;500;600;700&'
    'family=Roboto:wght@400;500;700&'
    'family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap" rel="stylesheet">'
    '<style>*,*::before,*::after{font-family:"Inter","Roboto","DM Sans",ui-sans-serif,system-ui,sans-serif;}</style>'
)

# ─── Step 1 — Spatial Extractor system (iterative edits only) ─────────────────

EXTRACTOR_USER = (
    "Extract the COMPLETE JSON layout from this screenshot. "
    "Include every visible list item, link, and text string — do not skip any rows. "
    "Output ONLY the raw JSON array. No explanation, no markdown."
)

# ─── Step 2 — Coder system (base, strategies prepended per-candidate) ─────────
CODER_SYSTEM_BASE = """You are a pixel-perfect UI compiler with vision capabilities.
You will be shown a UI screenshot. Reproduce it as HTML using Tailwind CSS.

CRITICAL RULES — violations will cause rejection:
1. Examine the screenshot at maximum detail before writing a single line of HTML.
2. Use Tailwind arbitrary values for EVERY color, size, spacing: bg-[#1a1a2e] text-[13px] w-[340px] gap-[12px].
3. Copy ALL visible text character-for-character. Never invent, paraphrase, or omit any text.
4. Reproduce exact background colors, text colors, border colors from the screenshot.
5. Match layout structure exactly: if it is a mobile screen, use a mobile-width container. If it is a desktop, use full width.
6. Render EVERY visible row, list item, and element. Do not truncate dense lists under any circumstances.
7. Simple icons (back arrow, checkmark, search, hamburger): inline SVG matching the screenshot shape exactly.
8. Profile photos, product images, logos: <img src="https://placehold.co/WxH/bgHex/fgHex"> with correct dimensions and colors.
9. Status bar elements (time, battery, signal): reproduce as text/SVG, never skip.
10. Bottom navigation bars: reproduce all tabs with correct icons and labels.
11. Include <script src="https://cdn.tailwindcss.com"></script> in <head>. No other scripts.
12. No JavaScript. No invented content whatsoever.
13. CRITICAL: If the screenshot shows a browser window with tabs/address bar, reproduce ONLY the inner page content — not the browser chrome.
14. Shadows, borders, border-radius: match exactly using arbitrary Tailwind values.
15. Gradients: reproduce using Tailwind bg-gradient-to-* classes with exact from/via/to hex values.
16. Opacity: match exactly using opacity-[N] or text-[#rrggbbAA] where relevant.

OUTPUT: Raw HTML only, starting with <!DOCTYPE html>. Zero explanation. Zero markdown fences."""

CODER_USER = (
    "Study this screenshot in full detail. "
    "Before writing HTML, mentally note:\n"
    "  - The exact background color of the page and each section\n"
    "  - Every text string, its size, weight, and color\n"
    "  - Every UI component and its precise spacing\n"
    "  - The layout system (flex/grid) used at each level\n"
    "  - Any gradients, shadows, borders, or special effects\n\n"
    "Then produce pixel-perfect HTML with Tailwind CSS that is indistinguishable from the screenshot.\n"
    "Output ONLY raw HTML starting with <!DOCTYPE html>. No explanation."
)

# ─── NEW #1/#13 — Healer system (full context, detail=high) ──────────────────
HEALER_SYSTEM = """You are a pixel-perfect UI debugger with vision capabilities.
You are given three images in order:
  IMAGE 1 — The ORIGINAL UI screenshot (ground truth target)
  IMAGE 2 — Your PREVIOUS HTML rendered in a browser
  IMAGE 3 — A DIFF MASK: red pixels = wrong, green tint = correct

Your ONLY job: fix the HTML so every red zone disappears.

CRITICAL RULES:
1. DO NOT rewrite sections that are correct (green zones). Touch only what is broken.
2. For each red zone, compare IMAGE 1 vs IMAGE 2 and diagnose the root cause:
   - Wrong spacing?         → Fix padding/margin/gap arbitrary value precisely.
   - Wrong color?           → Sample the exact hex from IMAGE 1 and correct bg-[#xxx] or text-[#xxx].
   - Wrong font size/weight? → Fix text-[Npx] or font-weight class.
   - Missing element?       → Add the complete missing HTML block.
   - Wrong layout?          → Fix flex-row ↔ flex-col or grid column count.
   - Wrong border/shadow?   → Correct border-[#xxx], rounded-[Npx], or shadow class.
   - Wrong gradient?        → Fix from-[#xxx] via-[#xxx] to-[#xxx] and direction.
   - Wrong image dimensions? → Fix the placehold.co URL with correct W×H.
3. Be surgical. The goal is zero red pixels in the next render.
4. Preserve ALL text strings exactly — do not alter any text content.
5. Return the COMPLETE corrected HTML starting with <!DOCTYPE html>.

OUTPUT: Raw HTML only, starting with <!DOCTYPE html>. Zero explanation. Zero markdown fences."""

# ─── NEW #6/#13 — Judge system (full HTML, reasons before deciding) ───────────
JUDGE_SYSTEM = """You are a UI fidelity judge with vision capabilities.
You are given the original UI screenshot and 2-3 complete HTML candidates.
Your job: select the candidate that most faithfully reproduces the screenshot.

Evaluate each candidate on these criteria IN ORDER OF IMPORTANCE:
  1. TEXT ACCURACY     — every visible string present, verbatim, correct position
  2. COLOR ACCURACY    — exact background, text, border, and accent colors
  3. LAYOUT FIDELITY   — correct flex/grid structure, correct hierarchy
  4. COMPLETENESS      — no missing rows, nav items, icons, or sections
  5. SPACING           — correct padding, margin, gap values
  6. VISUAL EFFECTS    — shadows, borders, gradients, border-radius

Think through each candidate systematically. Then on the VERY LAST LINE of your
response, write ONLY the single digit 1, 2, or 3 — nothing else on that line."""


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE HELPERS (unchanged from v7.0 / v8.0)
# ═══════════════════════════════════════════════════════════════════════════════
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


def _normalise_viewport(ref_image: Image.Image) -> tuple[tuple[int, int], Image.Image]:
    w, h = ref_image.size
    if w > 1920:
        w, h = w // 2, h // 2
        ref_image = ref_image.resize((w, h), Image.LANCZOS)
        logger.info("Retina detected — ref_image halved to %dx%d", w, h)
    w = max(320, min(w, 1920))
    h = max(400, h)
    return (w, h), ref_image


def compute_ssim(ref: Image.Image, rendered: Image.Image) -> float:
    rendered_rgb = rendered.convert("RGB")
    ref_resized  = ref.resize(rendered_rgb.size, Image.LANCZOS).convert("RGB")
    ref_arr    = np.array(ref_resized,  dtype=np.float32)
    render_arr = np.array(rendered_rgb, dtype=np.float32)
    try:
        win_size = min(21, rendered_rgb.size[0], rendered_rgb.size[1])
        win_size = win_size if win_size % 2 == 1 else win_size - 1
        if win_size < 3:
            return 0.0
        score = ssim_fn(
            ref_arr, render_arr,
            data_range=255.0,
            channel_axis=2,
            win_size=win_size,
            gaussian_weights=True,
        )
        return max(0.0, float(score)) * 100.0
    except Exception as exc:
        logger.warning("SSIM computation failed: %s", exc)
        return 0.0


# ─── NEW #10 — _call_api with 600s timeout, 3 attempts ───────────────────────
def _call_api(
    client: OpenAI,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0.0,
    attempt_limit: int = 3,
) -> str:
    """
    NEW #10: timeout raised to 600s per attempt.
    The judge with full HTML context can take 4-5 minutes to respond.
    Total max wait = 3 attempts × 600s + 2 × 8s backoff = ~30 minutes worst case.
    That is acceptable for maximum fidelity.
    """
    import httpx
    last_exc: Exception = RuntimeError("No attempts made")

    for attempt in range(attempt_limit):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=float(os.getenv("OXLO_API_TIMEOUT", "600.0")),  # NEW #10: was 180s
            )
            return resp.choices[0].message.content or ""

        except Exception as exc:
            last_exc = exc
            err_str = str(exc).lower()
            is_rate    = "429" in err_str
            is_server  = any(c in err_str for c in ("500", "502", "503", "504"))
            is_timeout = "timeout" in err_str or isinstance(exc, httpx.TimeoutException)

            if (is_rate or is_server or is_timeout) and attempt < attempt_limit - 1:
                wait = 4 ** (attempt + 1)  # 4s, 16s
                logger.warning(
                    "[%s] attempt %d failed (%s...), retry in %ds",
                    model, attempt + 1, err_str[:80], wait
                )
                time.sleep(wait)
            else:
                break

    raise RuntimeError(f"[{model}] failed after {attempt_limit} attempts: {last_exc}")


def _clean_html(raw: str) -> str:
    import re as _re
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
            lower = raw.lower()
            break
    # Issue 15: locate </head> safely — only match the real tag, not one inside
    # a <script> block or string literal. Strategy: find the first </head> that
    # appears BEFORE any <script> opener, which is where the real head closes.
    script_start = lower.find("<script")
    head_close   = lower.find("</head>")
    if head_close != -1 and (script_start == -1 or head_close < script_start):
        raw = raw[:head_close] + FONT_INJECT + raw[head_close:]
    elif "<head>" in lower:
        insert_at = lower.find("<head>") + len("<head>")
        raw = raw[:insert_at] + FONT_INJECT + raw[insert_at:]
    return raw


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


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 0 — OCR Text Anchoring (unchanged from v8.0)
# ═══════════════════════════════════════════════════════════════════════════════
def _ocr_extract_text_blocks(pil_image: Image.Image) -> Optional[str]:
    try:
        import pytesseract
        data = pytesseract.image_to_data(
            pil_image, output_type=pytesseract.Output.DICT, config="--psm 11"
        )
        blocks: list[str] = []
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if text and conf > 40:
                h = data["height"][i]
                approx_px = max(8, round(h * 0.75))
                blocks.append(f'  "{text}" (~{approx_px}px)')
        if not blocks:
            return None
        anchor = (
            "═══ OCR TEXT ANCHOR (verbatim — use these exact strings) ═══\n"
            "Every string below was extracted directly from the screenshot.\n"
            "You MUST use these exact strings in your HTML. Do not paraphrase or omit any:\n"
            + "\n".join(blocks)
            + "\n═══ END OCR ANCHOR ═══\n\n"
        )
        logger.info("[Step 0] OCR extracted %d text blocks", len(blocks))
        return anchor
    except ImportError:
        logger.info("[Step 0] pytesseract not installed — skipping OCR anchor")
        return None
    except Exception as exc:
        logger.warning("[Step 0] OCR failed: %s — continuing without anchor", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Strategy Swarm (full context, detail=high)
# ═══════════════════════════════════════════════════════════════════════════════
async def _step2_syntax_swarm(
    client: OpenAI,
    image_b64: str,
    mime: str,
    layout_json: Optional[str] = None,
    text_blocks: Optional[str] = None,
) -> list[str]:
    logger.info("[Step 2] Strategy swarm — %d strategies × %s in parallel",
                len(SWARM_STRATEGIES), MODEL_CODER)

    def _make_coder_call(strategy: dict) -> str:
        system_prompt = strategy["prefix"] + CODER_SYSTEM_BASE
        user_text_parts = []
        if text_blocks:
            user_text_parts.append(text_blocks)
        if layout_json:
            user_text_parts.append(
                f"Additional layout context (JSON):\n```json\n{layout_json}\n```\n"
            )
        user_text_parts.append(CODER_USER)
        user_text = "\n".join(user_text_parts)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "image_url",
                 # NEW #7: detail=high on all swarm calls — maximum pixel information
                 "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"}},
                {"type": "text", "text": user_text},
            ]},
        ]
        return _call_api(client, MODEL_CODER, messages, MAX_TOKENS_CODE,
                         temperature=strategy["temperature"])

    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, _make_coder_call, strategy)
        for strategy in SWARM_STRATEGIES
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    candidates: list[str] = []
    for i, r in enumerate(results):
        strategy_name = SWARM_STRATEGIES[i]["name"]
        if isinstance(r, Exception):
            logger.warning("[Step 2] Candidate %d (%s) failed: %s", i + 1, strategy_name, r)
        else:
            html = _clean_html(r)
            candidates.append(html)
            logger.info("[Step 2] Candidate %d (%s) OK (%d chars)",
                        i + 1, strategy_name, len(html))

    if not candidates:
        raise RuntimeError("[Step 2] All swarm candidates failed")
    return candidates


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Frontier Judge
# NEW #6: Full HTML sent (no truncation).
# NEW #7: detail=high image.
# NEW #8: MAX_TOKENS_JUDGE=512 lets the judge reason before picking.
# ═══════════════════════════════════════════════════════════════════════════════
def _step3_judge(
    client: OpenAI,
    candidates: list[str],
    image_b64: str,
    mime: str,
    layout_json: Optional[str] = None,
) -> int:
    if len(candidates) == 1:
        logger.info("[Step 3] Only 1 candidate — skipping judge")
        return 0

    logger.info("[Step 3] Judging %d candidates via %s (full HTML, detail=high)",
                len(candidates), MODEL_JUDGE)

    parts = []
    if layout_json:
        # For iterative edits: give judge the full layout JSON as ground truth
        parts.append(f"REFERENCE JSON (ground truth):\n```json\n{layout_json}\n```\n")
        parts.append("Judge which HTML candidate best implements this JSON layout.")
    else:
        parts.append(
            "The image above is the original UI screenshot at full resolution.\n"
            "Judge which HTML candidate best reproduces it pixel-for-pixel."
        )

    for i, html in enumerate(candidates, 1):
        
        parts.append(f"\nCANDIDATE {i} (complete HTML, {len(html)} chars):\n```html\n{html}\n```")

    parts.append(
        "\nThink through each candidate carefully against the screenshot.\n"
        "On the very last line of your response, write ONLY the digit 1, 2, or 3."
    )
    user_text = "\n".join(parts)

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": [
            
            {"type": "image_url",
             "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"}},
            {"type": "text", "text": user_text},
        ]},
    ]

    try:
       
        raw = _call_api(client, MODEL_JUDGE, messages, MAX_TOKENS_JUDGE, temperature=0.0, attempt_limit=2)
        raw = raw.strip()
        logger.info("[Step 3] Judge full response (%d chars): %r", len(raw), raw[-200:])

        
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.isdigit():
                idx = int(line) - 1
                if 0 <= idx < len(candidates):
                    logger.info("[Step 3] Judge selected candidate %d", idx + 1)
                    return idx

        # Fallback: scan each line for a lone digit — avoids greedy char-by-char scan
        # that would misread "2 wins because of 3 reasons" as candidate 3.
        import re as _re
        for line in raw.splitlines():
            m = _re.match(r'^\s*(\d)\s*$', line.strip())
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(candidates):
                    logger.warning("[Step 3] Used line-isolated fallback, selected %d", idx + 1)
                    return idx

        logger.warning("[Step 3] Could not parse judge response, falling back to candidate 0")
        return 0

    except Exception as exc:
        logger.warning("[Step 3] Judge failed or timed out (%s) — fast-falling back to candidate 1", exc)
        return 0


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Render + SSIM with smart Y-axis alignment
# ═══════════════════════════════════════════════════════════════════════════════
async def _step4_render_and_score(
    html: str,
    ref_image: Image.Image,
) -> tuple[float, Optional[Image.Image]]:
    target_size, ref_image_norm = _normalise_viewport(ref_image)
    logger.info("[Step 4] Rendering in Chromium at %dx%d", *target_size)

    rendered = await _render_html(html, target_size)
    if rendered is None:
        logger.error("[Step 4] Render failed — SSIM set to 0")
        return 0.0, None

    try:
        import cv2
        ref_arr = np.array(ref_image_norm.convert('L'))
        render_arr = np.array(rendered.convert('L'))

        # THE FIX 1: Reduce template to top 80px. 
        # This grabs the header bar but ignores compounded text-spacing errors below it.
        template_h = min(80, render_arr.shape[0], ref_arr.shape[0])
        w = render_arr.shape[1]

        # Use middle 50% to avoid edge-padding hallucinations
        x_start, x_end = int(w * 0.25), int(w * 0.75)
        template = render_arr[0:template_h, x_start:x_end]
        ref_search = ref_arr[:, x_start:x_end]

        if template.shape[0] > 0 and template.shape[1] > 0:
            res = cv2.matchTemplate(ref_search, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            _, y_offset = max_loc

            # THE FIX 2: Strict 60% confidence threshold.
            if y_offset > 0 and max_val > 0.60:
                logger.info("[Step 4] Browser chrome offset detected: %dpx (conf: %.2f) — cropping reference", y_offset, max_val)
                ref_cropped = ref_image_norm.crop((
                    0, y_offset,
                    ref_image_norm.width,
                    y_offset + rendered.height
                ))
            else:
                # If confidence is low, ASSUME NO BROWSER CHROME (0px offset). 
                # This prevents disastrous 174px false-positive crops.
                if y_offset > 0:
                    logger.warning("[Step 4] Ignored false-positive offset %dpx (low conf: %.2f). Assuming 0px.", y_offset, max_val)
                ref_cropped = ref_image_norm

            final_h        = min(rendered.height, ref_cropped.height)
            rendered_final = rendered.crop((0, 0, rendered.width, final_h))
            ref_final      = ref_cropped.crop((0, 0, ref_cropped.width, final_h))
        else:
            raise ValueError("Template too small")

    except Exception as exc:
        logger.warning("[Step 4] Smart alignment skipped (%s) — using simple crop", exc)
        ref_h          = ref_image_norm.size[1]
        rendered_final = rendered.crop((0, 0, rendered.size[0], ref_h)) if rendered.size[1] > ref_h else rendered
        ref_final      = ref_image_norm

    score = compute_ssim(ref_final, rendered_final)
    logger.info("[Step 4] SSIM = %.1f%%", score)
    return score, rendered_final


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Auto-Healing Loop
# NEW #11: 3 passes (was 2)
# NEW #12: ships at 92% (was 88%)
# Full HTML + full image sent to healer every pass
# ═══════════════════════════════════════════════════════════════════════════════
def _image_to_b64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = BytesIO()
    img.save(buf, format=fmt)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def _generate_diff_mask(ref: Image.Image, rendered: Image.Image) -> tuple[str, float]:
    """
    Red = wrong pixels, green tint = correct pixels.
    DIFF_PIXEL_THRESHOLD = 12.0 (tighter than v8.0's 15.0).
    """
    rendered_rs  = rendered.resize(ref.size, Image.LANCZOS).convert("RGB")
    ref_arr      = np.array(ref.convert("RGB"),  dtype=np.float32)
    rendered_arr = np.array(rendered_rs,          dtype=np.float32)

    diff       = np.abs(ref_arr - rendered_arr).max(axis=2)
    wrong_mask = diff > DIFF_PIXEL_THRESHOLD
    correct_mask = ~wrong_mask
    changed_ratio = wrong_mask.mean()

    output = rendered_arr.astype(np.uint8).copy()
    output[wrong_mask] = [220, 50, 50]
    green_overlay = output[correct_mask].astype(np.int16)
    green_overlay[:, 1] = np.clip(green_overlay[:, 1] + 20, 0, 255)
    output[correct_mask] = green_overlay.astype(np.uint8)

    diff_img = Image.fromarray(output, "RGB")
    buf = BytesIO()
    diff_img.save(buf, format="PNG")
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    logger.info("[Diff] Changed pixel ratio: %.1f%%", changed_ratio * 100)
    return b64, float(changed_ratio)


async def _healing_pass(
    client: OpenAI,
    html: str,
    image_b64: str,
    rendered_b64: str,
    diff_b64: str,
    mime: str,
    pass_number: int,
) -> str:
    logger.info("[Heal pass %d] Sending full context to %s", pass_number, MODEL_CODER)
    loop = asyncio.get_event_loop()

    user_text = (
        f"HEALING PASS {pass_number} of {MAX_HEALING_PASSES}.\n\n"
        "Three images provided:\n"
        "  IMAGE 1 = ORIGINAL screenshot (pixel-perfect ground truth)\n"
        "  IMAGE 2 = YOUR render (what your HTML produced)\n"
        "  IMAGE 3 = DIFF MASK (red = wrong zones, green tint = correct zones)\n\n"
        "For each red zone:\n"
        "  1. Compare IMAGE 1 vs IMAGE 2 to identify the exact discrepancy\n"
        "  2. Diagnose the CSS cause (wrong color, spacing, missing element, etc.)\n"
        "  3. Apply the surgical fix in the HTML\n\n"
        "Constraints:\n"
        "  - Fix ONLY red zones. Never touch green zones.\n"
        "  - Do not change any text strings unless they were factually wrong.\n"
        "  - Every fix must target a specific Tailwind class or HTML element.\n\n"
        "Return the COMPLETE corrected HTML starting with <!DOCTYPE html>.\n"
        "No explanation. No markdown fences."
    )

    messages = [
        {"role": "system", "content": HEALER_SYSTEM},
        {"role": "user", "content": [
            # NEW #7: All three images at detail=high
            {"type": "image_url",
             "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"}},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{rendered_b64}", "detail": "high"}},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{diff_b64}", "detail": "high"}},
            {"type": "text", "text": user_text},
        ]},
    ]

    raw = await loop.run_in_executor(
        None, _call_api, client, MODEL_CODER, messages, MAX_TOKENS_CODE, 0.0, 3,
    )
    return _clean_html(raw)


async def _run_healing_loop(
    client: OpenAI,
    html: str,
    ref_image: Image.Image,
    image_b64: str,
    mime: str,
) -> tuple[str, float, Optional[Image.Image], int]:
    current_html = html
    ssim_score, rendered = await _step4_render_and_score(current_html, ref_image)
    passes_run = 0

    for pass_num in range(1, MAX_HEALING_PASSES + 1):
        if ssim_score >= SSIM_SHIP_THRESHOLD:
            logger.info("[Heal] SSIM %.1f%% ≥ %.1f%% — shipping", ssim_score, SSIM_SHIP_THRESHOLD)
            break

        if pass_num >= 2 and ssim_score < SSIM_HEAL_THRESHOLD:
            logger.warning("[Heal] Pass %d: SSIM %.1f%% < floor %.1f%% — model is lost, aborting",
                           pass_num, ssim_score, SSIM_HEAL_THRESHOLD)
            break

        if rendered is None:
            logger.warning("[Heal] No rendered image — aborting heal loop")
            break

        rendered_b64            = _image_to_b64(rendered)
        diff_b64, changed_ratio = _generate_diff_mask(ref_image, rendered)

        if changed_ratio < 0.01:
            logger.info("[Heal] Changed ratio %.2f%% < 1%% — visually perfect, skipping", changed_ratio * 100)
            break

        logger.info("[Heal] Pass %d — SSIM %.1f%%, changed pixels %.1f%%, running heal...",
                    pass_num, ssim_score, changed_ratio * 100)

        healed_html = await _healing_pass(
            client, current_html, image_b64, rendered_b64, diff_b64, mime, pass_num
        )
        new_ssim, new_rendered = await _step4_render_and_score(healed_html, ref_image)

        if new_ssim > ssim_score:
            logger.info("[Heal] Pass %d ACCEPTED: %.1f%% → %.1f%% (+%.1f%%)",
                        pass_num, ssim_score, new_ssim, new_ssim - ssim_score)
            current_html = healed_html
            ssim_score   = new_ssim
            rendered     = new_rendered
            passes_run   = pass_num
        else:
            logger.warning("[Heal] Pass %d REJECTED: %.1f%% → %.1f%% (regression), keeping previous",
                           pass_num, ssim_score, new_ssim)
            break

    return current_html, ssim_score, rendered, passes_run




# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Smart Image Slicing (unchanged from v8.0)
# ═══════════════════════════════════════════════════════════════════════════════
def _should_slice(img: Image.Image) -> bool:
    w, h = img.size
    ratio = h / max(w, 1)
    logger.info("[Slice] Aspect ratio: %.2f (threshold: %.1f)", ratio, SLICE_ASPECT_THRESHOLD)
    return ratio > SLICE_ASPECT_THRESHOLD


def _find_slice_boundaries(img: Image.Image, n_slices: int = SLICE_N) -> list[int]:
    arr     = np.array(img.convert("L"), dtype=np.float32)
    h, w    = arr.shape
    row_var = arr.var(axis=1)
    boundaries = []
    segment_h = h // n_slices
    for i in range(1, n_slices):
        center     = i * segment_h
        zone_start = max(0, center - h // 10)
        zone_end   = min(h, center + h // 10)
        zone_vars  = row_var[zone_start:zone_end]
        best_local = int(np.argmin(zone_vars)) + zone_start
        boundaries.append(best_local)
        logger.info("[Slice] Boundary %d at y=%d (row_var=%.1f)", i, best_local, row_var[best_local])
    return boundaries


def _slice_image_to_b64(img: Image.Image, boundaries: list[int]) -> list[tuple[str, str, Image.Image]]:
    h    = img.size[1]
    cuts = [0] + boundaries + [h]
    slices = []
    for i in range(len(cuts) - 1):
        y0, y1 = cuts[i], cuts[i + 1]
        slc = img.crop((0, y0, img.size[0], y1))
        buf = BytesIO()
        slc.save(buf, format="JPEG", quality=90)
        b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
        slices.append((b64, "image/jpeg", slc))
        logger.info("[Slice] Slice %d: y=%d→%d (%dpx)", i + 1, y0, y1, y1 - y0)
    return slices


def _stitch_html_sections(sections: list[str]) -> str:
    if len(sections) == 1:
        return sections[0]
    first      = sections[0]
    head_start = first.lower().find("<head>")
    head_end   = first.lower().find("</head>")
    shared_head = first[head_start:head_end + len("</head>")] if head_start != -1 else "<head></head>"
    body_parts = []
    for i, html in enumerate(sections):
        body_start = html.lower().find("<body")
        body_end   = html.lower().rfind("</body>")
        if body_start != -1 and body_end != -1:
            inner_start = html.find(">", body_start) + 1
            body_parts.append(
                f'<!-- SECTION {i+1} -->\n<div class="slice-section">\n'
                + html[inner_start:body_end].strip()
                + "\n</div>"
            )
        else:
            body_parts.append(f'<!-- SECTION {i+1} -->\n{html}')
    stitched = (
        '<!DOCTYPE html>\n<html lang="en">\n'
        + shared_head + "\n"
        + "<body>\n"
        + "\n".join(body_parts)
        + "\n</body>\n</html>"
    )
    logger.info("[Stitch] Merged %d sections (%d chars)", len(sections), len(stitched))
    return stitched


async def _run_slice_pipeline(
    client: OpenAI,
    ref_image: Image.Image,
    image_b64: str,
    mime: str,
    text_blocks: Optional[str],
) -> str:
    logger.info("[Slice] Tall page — running slice pipeline")
    boundaries   = _find_slice_boundaries(ref_image)
    image_slices = _slice_image_to_b64(ref_image, boundaries)
    section_htmls: list[str] = []

    for i, (slice_b64, slice_mime, slice_img) in enumerate(image_slices):
        logger.info("[Slice] Processing section %d / %d", i + 1, len(image_slices))
        candidates = await _step2_syntax_swarm(
            client, slice_b64, slice_mime,
            layout_json=None, text_blocks=text_blocks,
        )
        loop    = asyncio.get_event_loop()
        best_idx = await loop.run_in_executor(
            None, _step3_judge, client, candidates, slice_b64, slice_mime, None
        )
        section_htmls.append(candidates[best_idx])

    return _clean_html(_stitch_html_sections(section_htmls))


# ═══════════════════════════════════════════════════════════════════════════════
# UPLOAD SCRIPT INJECTOR  (v2 — all 6 edge cases)
# ═══════════════════════════════════════════════════════════════════════════════
def _inject_upload_script(html: str) -> str:
    script = """
<script>
(function(){
  var swaps=window.__imageSwaps=window.__imageSwaps||{};
  var hist=window.__imageHistory=window.__imageHistory||[];
  var tip=null;
  function showTip(e){
    if(!tip){tip=document.createElement('div');
      tip.style.cssText='position:fixed;z-index:99999;background:#1e293b;color:#fff;font-size:11px;padding:3px 8px;border-radius:4px;pointer-events:none;white-space:nowrap;transition:opacity .1s';
      document.body.appendChild(tip);}
    tip.textContent=e.currentTarget._tipText||'Click to replace';
    tip.style.display='block';
  }
  function moveTip(e){if(tip){tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY-28)+'px';}}
  function hideTip(){if(tip)tip.style.display='none';}
  function openPicker(cb){
    var inp=document.createElement('input');inp.type='file';inp.accept='image/*';
    inp.onchange=function(e){var f=e.target.files[0];if(!f)return;
      var r=new FileReader();r.onload=function(ev){cb(ev.target.result);};r.readAsDataURL(f);};
    inp.click();
  }
  function pushHist(el,prev){hist.push({el:el,prev:prev});if(hist.length>20)hist.shift();}
  document.addEventListener('keydown',function(e){
    if((e.ctrlKey||e.metaKey)&&e.key==='z'){e.preventDefault();
      var entry=hist.pop();if(!entry)return;
      if(entry.el.tagName==='IMG')entry.el.src=entry.prev;
      else entry.el.style.backgroundImage=entry.prev;}
  });
  function wireImg(img,idx){
    if(img.dataset.wired)return;img.dataset.wired='1';
    img.style.cursor='pointer';
    img._tipText='Click to replace image';
    img.addEventListener('mouseenter',function(e){img.style.outline='2px solid #3b82f6';img.style.outlineOffset='2px';showTip(e);});
    img.addEventListener('mousemove',moveTip);
    img.addEventListener('mouseleave',function(){img.style.outline='';img.style.outlineOffset='';hideTip();});
    img.addEventListener('click',function(e){
      e.stopPropagation();
      var prev=img.src;
      openPicker(function(d){
        pushHist(img,prev);
        img.src=d;
        swaps[idx]=d;
        // Strip rigid Tailwind size classes that distort product images
        img.className=img.className.replace(/\b(w-\d+|h-\d+|w-full|h-full)\b/g,'').trim();
        // Bulletproof scaling so any image fits its container
        img.style.objectFit='contain';
        img.style.objectPosition='center';
        img.style.maxWidth='100%';
        img.style.maxHeight='100%';
        // Immediately sync the updated DOM (with new Base64) to the React parent
        // Issue 3 fix: use restricted origin same as edit script
        var _upOrigin = window.__allowedOrigin ||
          (document.referrer ? new URL(document.referrer).origin : '*');
        window.parent.postMessage({type:'html-snapshot',html:document.documentElement.outerHTML}, _upOrigin);
      });
    });
  }
  function wireBg(el){
    if(el.dataset.bgWired)return;
    var bg=el.style.backgroundImage||getComputedStyle(el).backgroundImage;
    if(!bg||bg==='none'||bg.indexOf('url(')<0)return;
    el.dataset.bgWired='1';
    if(getComputedStyle(el).position==='static')el.style.position='relative';
    var btn=document.createElement('button');
    btn.innerHTML='&#128247;';
    btn.style.cssText='position:absolute;bottom:4px;right:4px;z-index:10;width:24px;height:24px;background:rgba(0,0,0,.6);border:none;border-radius:4px;cursor:pointer;font-size:13px;line-height:1;';
    btn._tipText='Click to replace background';
    btn.addEventListener('mouseenter',showTip);btn.addEventListener('mousemove',moveTip);btn.addEventListener('mouseleave',hideTip);
    btn.addEventListener('click',function(e){e.stopPropagation();
      var prev=el.style.backgroundImage;
      openPicker(function(d){pushHist(el,prev);el.style.backgroundImage='url('+d+')';});});
    el.appendChild(btn);
  }
  function scanAll(){
    document.querySelectorAll('img').forEach(function(img,i){wireImg(img,i);});
    document.querySelectorAll('*').forEach(wireBg);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',scanAll);else scanAll();
  new MutationObserver(function(muts){
    muts.forEach(function(m){
      m.addedNodes.forEach(function(n){
        if(!n.querySelectorAll)return;
        if(n.tagName==='IMG')wireImg(n,Date.now());
        n.querySelectorAll('img').forEach(function(img,i){wireImg(img,i+10000);});
        wireBg(n);n.querySelectorAll('*').forEach(wireBg);
      });
    });
  }).observe(document.body,{childList:true,subtree:true});
})();
</script>"""
    if '</body>' in html.lower():
        idx = html.lower().rfind('</body>')
        return html[:idx] + script + html[idx:]
    return html + script


# ═══════════════════════════════════════════════════════════════════════════════
# EDIT SCRIPT INJECTOR  (postMessage-based live editing)
# ═══════════════════════════════════════════════════════════════════════════════
def _inject_edit_script(html: str) -> str:
    script = """
<script>
(function(){
  // Issue 3 fix: restrict postMessage to the parent origin, not wildcard.
  // The parent sets window.__allowedOrigin via a one-time init message before
  // any toolbar interaction.  Fall back to the referrer origin as a safe default.
  var _allowedOrigin = window.__allowedOrigin ||
    (document.referrer ? new URL(document.referrer).origin : '*');
  window.addEventListener('message', function(e) {
    if (e.origin !== window.location.origin) return;
    if (e.data && e.data.type === '__init_origin__') {
      _allowedOrigin = e.origin;
      window.__allowedOrigin = e.origin;
    }
  }, { once: false });
  function _postToParent(data) { window.parent.postMessage(data, _allowedOrigin); }
  var sel=null;
  document.addEventListener('click',function(e){
    // deselect previous
    if(sel){sel.style.boxShadow='';sel.removeAttribute('data-edit-sel');}
    sel=e.target;
    sel.setAttribute('data-edit-sel','1');
    sel.style.boxShadow='inset 0 0 0 2px #8b5cf6';
    var r=sel.getBoundingClientRect();
    _postToParent({type:'element-select',
      tag:sel.tagName.toLowerCase(),
      classes:(sel.getAttribute('class')||''),
      text:(sel.textContent||'').trim().slice(0,300),
      rect:{top:r.top,left:r.left,width:r.width,height:r.height}});
  },true);
  window.addEventListener('message',function(e){
    if (e.origin !== window.location.origin) return;
    var m=e.data;if(!m||!m.type)return;
    if(m.type==='apply-style'&&sel){sel.style[m.property]=m.value;}
    else if(m.type==='apply-text'&&sel){
      // Use TreeWalker to target only text nodes — never destroys embedded SVGs/icons
      var walker=document.createTreeWalker(sel,NodeFilter.SHOW_TEXT,null,false);
      var firstText=walker.nextNode();
      if(firstText){firstText.nodeValue=m.value;}else{sel.textContent=m.value;}
    }
    else if(m.type==='get-html'){_postToParent({type:'html-snapshot',html:document.documentElement.outerHTML});}
    else if(m.type==='reset'){window.location.reload();}
  });
})();
</script>"""
    if '</body>' in html.lower():
        idx = html.lower().rfind('</body>')
        return html[:idx] + script + html[idx:]
    return html + script


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE (v9.0)
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
    t0     = time.perf_counter()

    image_b64, mime, ref_image = compress_image(raw_bytes)

    # STEP 0: OCR anchor (non-blocking)
    loop        = asyncio.get_event_loop()
    text_blocks = await loop.run_in_executor(None, _ocr_extract_text_blocks, ref_image)
    logger.info("[Step 0] OCR anchor: %s", "ready" if text_blocks else "unavailable")

    # Iterative edit path
    if prev_code and update_prompt:
        logger.info("Iterative edit mode")
        edit_user_parts = []
        if text_blocks:
            edit_user_parts.append(text_blocks)
        edit_user_parts.append(
            f"Previously generated HTML:\n```html\n{prev_code}\n```\n\n"
            f"Update request: {update_prompt}\n\n"
            "Return ONLY the complete updated HTML starting with <!DOCTYPE html>. No explanation."
        )
        raw = await loop.run_in_executor(
            None, _call_api, client, MODEL_CODER,
            [
                {"role": "system", "content": CODER_SYSTEM_BASE},
                {"role": "user", "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"}},
                    {"type": "text", "text": "\n".join(edit_user_parts)},
                ]},
            ],
            MAX_TOKENS_CODE, 0.0, 3,
        )
        html = _clean_html(raw)
        html, ssim_score, rendered, passes_run = await _run_healing_loop(
            client, html, ref_image, image_b64, mime
        )
        total_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "code":               _inject_upload_script(_inject_edit_script(html)),
            "accuracy_score":     f"{ssim_score:.1f}%",
            "ssim_score":         f"{ssim_score:.1f}%",
            "generation_time_ms": total_ms,
            "pass_count":         passes_run,
            "layout_json":        None,
            "ocr_anchored":       text_blocks is not None,
        }

    # Slicing decision
    did_slice = _should_slice(ref_image)
    if did_slice:
        logger.info("[Pipeline] Tall page — routing to slice pipeline")
        best_html = await _run_slice_pipeline(client, ref_image, image_b64, mime, text_blocks)
    else:
        # STEP 2: Strategy swarm
        candidates = await _step2_syntax_swarm(
            client, image_b64, mime,
            layout_json=None, text_blocks=text_blocks,
        )
        # STEP 3: Judge (full HTML, full image, reasoning mode)
        best_idx = await loop.run_in_executor(
            None, _step3_judge, client, candidates, image_b64, mime, None
        )
        best_html = candidates[best_idx]
        logger.info("Judge selected candidate %d / %d", best_idx + 1, len(candidates))

    # STEP 5: Healing loop (3 passes, 92% threshold)
    best_html, ssim_score, rendered, passes_run = await _run_healing_loop(
        client, best_html, ref_image, image_b64, mime
    )

    total_ms = int((time.perf_counter() - t0) * 1000)
    logger.info("Pipeline complete in %dms — SSIM %.1f%%", total_ms, ssim_score)


    return {
        "code":               _inject_upload_script(_inject_edit_script(best_html)),
        "accuracy_score":     f"{ssim_score:.1f}%",
        "ssim_score":         f"{ssim_score:.1f}%",
        "generation_time_ms": total_ms,
        "pass_count":         passes_run,
        "layout_json":        None,
        "ocr_anchored":       text_blocks is not None,
        "sliced":             did_slice,
        "candidate_count":    SLICE_N if did_slice else len(candidates),
        "swarm_strategies":   [s["name"] for s in SWARM_STRATEGIES],
    }


# ─── Public entry point ───────────────────────────────────────────────────────
async def run(data: dict) -> dict:
    """
    Execute the Maximum Fidelity Pipeline v9.0.

    Input (identical to v8.0):
      image          — base64 image  [required]
      previous_code  — prior HTML    [optional]
      update_prompt  — edit request  [optional]

    Returns:
      code, accuracy_score, ssim_score, generation_time_ms,
      pass_count, layout_json, ocr_anchored, sliced,
      candidate_count, swarm_strategies, error
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