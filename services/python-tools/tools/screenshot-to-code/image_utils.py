import base64
from io import BytesIO
from typing import Optional
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim_fn
from config import COMPRESS_MAX_PX, COMPRESS_JPEG_QUALITY, SLICE_ASPECT_THRESHOLD, SLICE_N, DIFF_PIXEL_THRESHOLD, logger


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
