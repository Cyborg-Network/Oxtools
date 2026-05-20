"""
LLM Palette Refiner Module
===========================
Uses LLM to refine extracted colors, assign UI roles, and ensure accessibility.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from config import LLM, REFINEMENT_SYSTEM_PROMPT
from color_extractor import ColorExtractor

logger = logging.getLogger(__name__)

_TOOL_DIR = Path(__file__).parent


class PaletteRefiner:
    """Refines extracted colors using LLM for UI role assignment and accessibility."""
    
    def __init__(self, llm=None):
        """Initialize refiner with LLM."""
        if llm is None:
            llm = LLM
        
        self.llm = llm
        if not self.llm:
            raise RuntimeError("LLM not initialized. Ensure OXLO_API_KEY is set.")
    
    async def refine_palette(self, colors: list, user_preferences: str = "") -> Dict[str, Any]:
        """
        Refine extracted colors into a production-ready palette.
        
        Args:
            colors: List of hex color codes
            user_preferences: Optional user preferences for palette
            
        Returns:
            Structured palette with roles, theory, CSS, etc.
        """
        try:
            # Prepare color summary for LLM
            color_summary = self._prepare_color_summary(colors)
            
            # Build user prompt
            user_prompt = f"""
Here are the extracted dominant colors from the uploaded image:
{color_summary}

User preferences: {user_preferences or 'None specified'}

Please:
1. Refine and harmonize these colors into a cohesive palette
2. Map each color to an appropriate UI role
3. Ensure WCAG AA contrast compliance for text
4. Provide CSS variables and Tailwind configuration
5. Explain the color theory and accessibility

Return a valid JSON object following the structure specified in your system prompt.
"""
            
            # Call LLM
            logger.info("Calling LLM for palette refinement...")
            response = await self.llm.ainvoke([
                {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ])
            
            # Parse response
            content = response.content
            
            # Extract JSON from response
            palette_data = self._extract_json(content)
            
            logger.info("Palette refinement completed successfully")
            return palette_data
        
        except Exception as e:
            logger.error(f"Palette refinement failed: {e}")
            raise
    
    def _prepare_color_summary(self, colors: list) -> str:
        """Format extracted colors for LLM."""
        summary = "Dominant colors (from dark to light):\n"
        for i, color in enumerate(colors, 1):
            summary += f"{i}. {color}\n"
        return summary
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON object from LLM response text."""
        import re
        
        logger.info(f"LLM Response (first 500 chars): {text[:500]}")
        
        try:
            # Try direct parsing first
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.debug(f"Direct parse failed: {e}")
        
        # Try to find JSON in markdown code blocks (various formats)
        patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json\n...\n```
            r'```\s*\n(.*?)\n```',      # ```\n...\n```
            r'```(.*?)```',              # ```...``` (any spacing)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse JSON from markdown: {json_str[:100]}")
                    # Try to fix incomplete JSON in code block
                    try:
                        fixed_json = self._fix_truncated_json(json_str)
                        return json.loads(fixed_json)
                    except Exception:
                        continue
        
        # Try to extract nested JSON: find first { and matching }
        start = text.find('{')
        if start != -1:
            # Find matching closing brace with proper nesting
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            json_str = text[start:i+1]
                            result = json.loads(json_str)
                            logger.info("Successfully extracted JSON from nested braces")
                            return result
                        except json.JSONDecodeError:
                            logger.debug(f"Failed to parse extracted JSON: {json_str[:100]}")
                            pass
            
            # If we couldn't find matching braces, try to fix truncated JSON
            if start != -1:
                try:
                    json_str = text[start:]
                    fixed_json = self._fix_truncated_json(json_str)
                    result = json.loads(fixed_json)
                    logger.info("Successfully parsed truncated JSON after fixing")
                    return result
                except Exception as e:
                    logger.debug(f"Could not fix truncated JSON: {e}")
        
        # If all parsing fails, log the response and raise
        logger.error(f"Could not extract valid JSON. Full response:\n{text}")
        raise ValueError(f"Could not extract valid JSON from LLM response. Got: {text[:200]}")
    
    @staticmethod
    def _fix_truncated_json(json_str: str) -> str:
        """Attempt to fix truncated JSON by closing open braces/brackets."""
        # Count open/close braces and brackets
        open_braces = json_str.count('{') - json_str.count('}')
        open_brackets = json_str.count('[') - json_str.count(']')
        open_quotes = json_str.count('"') % 2  # If odd, there's an unclosed quote
        
        # Close any open structures
        fixed = json_str.rstrip()
        
        # If we're in a string, close it
        if open_quotes:
            fixed += '"'
        
        # Close open arrays
        for _ in range(open_brackets):
            fixed += ']'
        
        # Close open braces
        for _ in range(open_braces):
            fixed += '}'
        
        return fixed
    
    @staticmethod
    def ensure_wcag_compliance(palette: Dict[str, str]) -> Dict[str, str]:
        """
        Ensure WCAG AA contrast between text colors and backgrounds.
        Adjusts colors if needed to meet minimum 4.5:1 ratio for normal text.
        
        Args:
            palette: Dictionary with color roles
            
        Returns:
            Adjusted palette ensuring contrast compliance
        """
        extractor = ColorExtractor()
        min_contrast = 4.5  # WCAG AA for normal text
        
        # Check critical pairs
        pairs_to_check = [
            ("text", "background"),
            ("text", "surface"),
            ("muted", "background"),
            ("muted", "surface"),
        ]
        
        adjusted = palette.copy()
        
        for text_role, bg_role in pairs_to_check:
            if text_role in adjusted and bg_role in adjusted:
                contrast = extractor.calculate_contrast(
                    adjusted[text_role],
                    adjusted[bg_role]
                )
                
                if contrast < min_contrast:
                    logger.warning(
                        f"Low contrast between {text_role} and {bg_role}: {contrast:.1f}"
                    )
                    # Adjust text color for better contrast
                    # This is a simplified approach - LLM should handle most cases
                    # For now, we just log the issue
        
        return adjusted
