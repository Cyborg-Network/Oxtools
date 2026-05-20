"""
LangGraph Pipeline
==================
Orchestrates the image-to-palette workflow using LangGraph.

Pipeline Flow:
1. Validate Input → 2. Extract Colors → 3. Refine Palette → 4. Output Formatting
"""

import logging
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
import sys
from pathlib import Path

# Ensure this tool's directory is in sys.path for imports
_TOOL_DIR = Path(__file__).parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

logger = logging.getLogger(__name__)


class PipelineState(TypedDict):
    """State object for the pipeline."""
    image_base64: str
    user_preferences: str
    num_colors: int
    extracted_colors: list
    refined_palette: dict
    final_output: dict
    error: str
    status: str


async def validate_input(state: PipelineState) -> PipelineState:
    """Validate input image and parameters."""
    try:
        logger.info("Validating input...")
        
        if not state.get("image_base64"):
            state["error"] = "No image provided"
            state["status"] = "failed"
            return state
        
        state["status"] = "input_validated"
        logger.info("Input validation passed")
        return state
    
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        state["error"] = str(e)
        state["status"] = "failed"
        return state


async def extract_colors(state: PipelineState) -> PipelineState:
    """Extract dominant colors from image."""
    try:
        from color_extractor import ColorExtractor
        
        if state.get("error"):
            return state
        
        logger.info("Extracting colors from image...")
        
        num_colors = state.get("num_colors", 8)
        extractor = ColorExtractor(num_colors=num_colors)
        
        colors = extractor.extract_from_base64(state["image_base64"])
        
        state["extracted_colors"] = colors
        state["status"] = "colors_extracted"
        logger.info(f"Extracted {len(colors)} colors: {colors}")
        
        return state
    
    except Exception as e:
        logger.error(f"Color extraction failed: {e}")
        state["error"] = f"Color extraction failed: {str(e)}"
        state["status"] = "failed"
        return state


async def refine_palette(state: PipelineState) -> PipelineState:
    """Refine extracted colors using LLM."""
    try:
        from llm_refiner import PaletteRefiner
        
        if state.get("error"):
            return state
        
        logger.info("Refining palette with LLM...")
        
        refiner = PaletteRefiner()
        refined = await refiner.refine_palette(
            state["extracted_colors"],
            state.get("user_preferences", "")
        )
        
        # Ensure WCAG compliance
        if "palette" in refined:
            refined["palette"] = PaletteRefiner.ensure_wcag_compliance(refined["palette"])
        
        state["refined_palette"] = refined
        state["status"] = "palette_refined"
        logger.info("Palette refinement completed")
        
        return state
    
    except Exception as e:
        logger.error(f"Palette refinement failed: {e}")
        state["error"] = f"Palette refinement failed: {str(e)}"
        state["status"] = "failed"
        return state


async def format_output(state: PipelineState) -> PipelineState:
    """Format final output for frontend."""
    try:
        if state.get("error"):
            return state
        
        logger.info("Formatting output...")
        
        refined = state.get("refined_palette", {})
        
        # Build comprehensive output
        final_output = {
            "success": True,
            "palette": refined.get("palette", {}),
            "roles": refined.get("roles", {}),
            "colorTheory": refined.get("colorTheory", ""),
            "cssVariables": refined.get("cssVariables", ""),
            "tailwindConfig": refined.get("tailwindConfig", ""),
            "wcagCompliance": refined.get("wcagCompliance", ""),
            "extractedColors": state.get("extracted_colors", []),
        }
        
        state["final_output"] = final_output
        state["status"] = "complete"
        logger.info("Output formatting completed")
        
        return state
    
    except Exception as e:
        logger.error(f"Output formatting failed: {e}")
        state["error"] = f"Output formatting failed: {str(e)}"
        state["status"] = "failed"
        return state


def build_pipeline_graph(*, skip_extract: bool = False):
    """Build the LangGraph workflow.
    
    If skip_extract is True, the graph assumes `extracted_colors` is already present
    in the state and jumps directly from validate → refine.
    """
    
    # Create graph
    graph = StateGraph(PipelineState)
    
    # Add nodes
    graph.add_node("validate", validate_input)
    graph.add_node("extract", extract_colors)
    graph.add_node("refine", refine_palette)
    graph.add_node("format", format_output)
    
    # Add edges
    if skip_extract:
        graph.add_edge("validate", "refine")
    else:
        graph.add_edge("validate", "extract")
        graph.add_edge("extract", "refine")
    graph.add_edge("refine", "format")
    graph.add_edge("format", END)
    
    # Set entry point
    graph.set_entry_point("validate")
    
    return graph.compile()


async def execute_pipeline(image_base64: str, 
                          user_preferences: str = "",
                          num_colors: int = 8,
                          extracted_colors: list | None = None) -> dict:
    """
    Execute the complete palette extraction pipeline.
    
    Args:
        image_base64: Base64-encoded image with data URI prefix
        user_preferences: Optional user preferences string
        num_colors: Number of colors to extract
        
    Returns:
        Final formatted output
    """
    
    # Build pipeline
    pipeline = build_pipeline_graph(skip_extract=bool(extracted_colors))
    
    # Initialize state
    initial_state: PipelineState = {
        "image_base64": image_base64,
        "user_preferences": user_preferences,
        "num_colors": num_colors,
        "extracted_colors": extracted_colors or [],
        "refined_palette": {},
        "final_output": {},
        "error": "",
        "status": "started",
    }
    
    # Execute pipeline
    logger.info("Starting image palette extraction pipeline...")
    result = await pipeline.ainvoke(initial_state)
    
    # Handle errors
    if result.get("error"):
        return {
            "success": False,
            "error": result["error"],
            "status": result.get("status", "failed")
        }
    
    logger.info(f"Pipeline completed with status: {result.get('status')}")
    return result.get("final_output", {})
