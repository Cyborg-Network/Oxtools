"""
Image Palette Extractor Tool
=============================
Entry point for the unified Python tool runner.
Extracts dominant colors from images and generates production-ready palettes.

Agentic Architecture:
- LangGraph for orchestration
- LangChain for LLM integration
- KMeans clustering for color extraction
- WCAG compliance validation

Processing Flow:
Image (base64) → Preprocessing → Color Extraction (KMeans) 
→ Palette Refinement (LLM) → WCAG Validation → Structured Output
"""

import json
import logging
import sys
from pathlib import Path
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Ensure tool directory is in sys.path BEFORE any imports
_TOOL_DIR = Path(__file__).parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))


# ─── MANIFEST ──────────────────────────────────────────────────────────
MANIFEST = {
    "id": "color-palette",
    "name": "Color Palette Generator (Agentic)",
    "description": "Extract dominant colors from images using KMeans clustering and LLM-powered refinement with WCAG compliance",
    "author": "Oxlo Team",
    "version": "1.0.0",
    "requires": [
        "langgraph>=0.1.0",
        "langchain-openai>=0.1.0",
        "Pillow>=10.0.0",
        "scikit-learn>=1.3.0",
        "numpy>=1.24.0",
    ],
}


# ─── RUN (called by the unified runner) ──────────────────────────
async def run(data: dict):
    """
    Execute the image palette extraction pipeline.
    
    Inputs (from frontend):
    - image: base64-encoded image (required)
    - description: text description (optional)
    - style: style preference (optional)
    - count: number of colors (optional, default 8)
    
    Returns:
    Async generator streaming status updates + final JSON output
    """
    
    try:
        # Import here to avoid module loading issues at startup
        from pipeline import execute_pipeline
        
        # Validate inputs
        image_base64 = data.get("image", "")
        description = data.get("description", "")
        style = data.get("style", "")
        count = data.get("count", "8")
        
        logger.info("Processing image mode with color extraction")
        
        # Parse color count
        try:
            num_colors = min(int(count), 12)  # Cap at 12 colors
            num_colors = max(num_colors, 4)   # Min 4 colors
        except (ValueError, TypeError):
            num_colors = 8
        
        # Validate image is provided
        if not image_base64:
            error_msg = "Image is required for color extraction"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        logger.info("Processing image mode with agentic pipeline...")
        
        # Build user preferences from optional fields
        user_prefs = []
        if style:
            user_prefs.append(f"Style: {style}")
        if description:
            user_prefs.append(f"Additional notes: {description}")
        user_preferences = ". ".join(user_prefs) if user_prefs else ""
        
        # Execute pipeline with streaming
        async def stream():
            yield "[VALIDATE] Validating image input...\n"
            yield "[EXTRACT] Extracting dominant colors with KMeans...\n"
            
            try:
                # Extract first, so the UI can render quickly
                from color_extractor import ColorExtractor

                extractor = ColorExtractor(num_colors=num_colors)
                extracted_colors = extractor.extract_from_base64(image_base64)

                # Generate a downscaled preview image on the server but DO NOT include
                # the full pixel map in the response (frontend will sample pixels from canvas).
                image_base64_clean, pixel_map, img_width, img_height = extractor.get_pixel_map(
                    image_base64, max_pixels=0, max_dim=800
                )

                # Ensure image is formatted as data URI for immediate frontend display
                if not image_base64_clean.startswith("data:"):
                    image_data_uri = f"data:image/jpeg;base64,{image_base64_clean}"
                else:
                    image_data_uri = image_base64_clean

                # Stream a lightweight, machine-parsable block inside logs with image and colors
                # (frontend reads this before the final OUTPUT_START JSON for immediate display)
                yield "\n---EXTRACTED_COLORS_START---\n"
                yield json.dumps(
                    {
                        "success": True,
                        "extractedColors": extracted_colors,
                        "numColors": num_colors,
                        "image": image_data_uri,
                        "imageWidth": img_width,
                        "imageHeight": img_height,
                        # stable key for potential frontend caching
                        "imageKey": hashlib.sha256(image_base64.encode("utf-8")).hexdigest()[:16],
                    }
                )
                yield "\n---EXTRACTED_COLORS_END---\n\n"

                yield "[REFINE] Refining palette with LLM...\n"
                yield "[FORMAT] Formatting output...\n"

                try:
                    result = await execute_pipeline(
                        image_base64=image_base64,
                        user_preferences=user_preferences,
                        num_colors=num_colors,
                        extracted_colors=extracted_colors,
                    )
                except Exception as llm_error:
                    logger.warning(f"LLM refinement failed ({llm_error}), using extracted colors as fallback")
                    # CREATE FALLBACK PALETTE from extracted colors
                    result = {
                        "success": True,
                        "palette": {color: color for color in extracted_colors[:min(num_colors, len(extracted_colors))]},
                        "roles": {
                            "primary": extracted_colors[0] if extracted_colors else "#000000",
                            "secondary": extracted_colors[1] if len(extracted_colors) > 1 else extracted_colors[0],
                            "accent": extracted_colors[2] if len(extracted_colors) > 2 else extracted_colors[0],
                            "background": "#ffffff",
                            "surface": "#f5f5f5",
                            "text": "#333333",
                            "muted": "#999999",
                        },
                        "colorTheory": "Extracted from image using KMeans clustering",
                        "extractedColors": extracted_colors,
                    }

                # Ensure image data is properly formatted as data URI and include resized preview
                result["image"] = image_base64_clean if image_base64_clean.startswith("data:") else f"data:image/png;base64,{image_base64_clean}"
                result["imageWidth"] = img_width
                result["imageHeight"] = img_height

                # Safety: cap final JSON size; drop optional heavy fields if too large
                serialized = json.dumps(result)
                if len(serialized.encode("utf-8")) > 2_000_000:
                    # Remove pixel map if present
                    if "pixels" in result:
                        del result["pixels"]
                    serialized = json.dumps(result)
                    if len(serialized.encode("utf-8")) > 2_000_000:
                        # As a last resort, remove the image preview to keep payload small
                        if "image" in result:
                            del result["image"]

                logger.info(f"Result prepared: image preview present={ 'image' in result }, pixels_sent={ 'pixels' in result }, dimensions={img_width}x{img_height}")

                yield "\n---OUTPUT_START---\n"
                yield json.dumps(result, indent=2)
                yield "\n---OUTPUT_END---\n"
                
            except Exception as e:
                logger.error(f"Pipeline execution failed: {e}")
                import traceback
                traceback.print_exc()
                error_response = {
                    "success": False,
                    "error": str(e),
                    "status": "failed"
                }
                yield json.dumps(error_response, indent=2)
        
        return stream()
    
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "status": "error"
        }
