import asyncio
import base64
import os
import time
from typing import Optional
from PIL import Image
from openai import OpenAI
from config import (
    MODEL_CODER, MODEL_JUDGE, OXLO_BASE_URL, MAX_TOKENS_CODE, MAX_TOKENS_JUDGE,
    SWARM_STRATEGIES, SSIM_SHIP_THRESHOLD, SSIM_HEAL_THRESHOLD, MAX_HEALING_PASSES,
    SLICE_N, CODER_SYSTEM_BASE, CODER_USER, HEALER_SYSTEM, JUDGE_SYSTEM, logger
)
from api_utils import _call_api
from image_utils import (
    compress_image, _normalise_viewport, compute_ssim, _image_to_b64,
    _generate_diff_mask, _ocr_extract_text_blocks, _should_slice,
    _find_slice_boundaries, _slice_image_to_b64
)
from html_utils import _clean_html, _stitch_html_sections, _inject_upload_script, _inject_edit_script
from render_utils import _render_html


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
