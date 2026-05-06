"""
Configuration and LLM setup for Image Palette Extractor
"""

import os
import logging
from langchain_openai import ChatOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Oxlo API key from environment
OXLO_API_KEY = os.getenv("OXLO_API_KEY", "")

# Initialize LLM with Oxlo API
# Using Oxlo's OpenAI-compatible API
LLM = ChatOpenAI(
    api_key=OXLO_API_KEY,
    model="kimi-k2.5",
    base_url="https://api.oxlo.ai/v1",
    temperature=0.7,
    max_tokens=4000,
) if OXLO_API_KEY else None

# System prompt for LLM palette refinement
REFINEMENT_SYSTEM_PROMPT = """You are a professional UI/UX designer and color theorist specializing in color harmony and accessibility.

CRITICAL: Your response MUST be ONLY valid JSON. Do NOT include any text before or after the JSON object.

Your task:
1. Analyze the provided extracted colors
2. Harmonize them into a cohesive palette
3. Assign semantic UI roles to each color
4. Ensure WCAG AA contrast compliance (4.5:1 minimum)
5. Generate CSS variables and Tailwind config
6. Provide color theory explanation

Return ONLY this JSON structure (no other text):
{
  "palette": {
    "primary": "#XXXXXX",
    "secondary": "#XXXXXX",
    "accent": "#XXXXXX",
    "background": "#XXXXXX",
    "surface": "#XXXXXX",
    "text": "#XXXXXX",
    "muted": "#XXXXXX",
    "success": "#XXXXXX",
    "error": "#XXXXXX"
  },
  "roles": {
    "primary": "Main brand color for CTAs and highlights",
    "secondary": "Supporting brand color for secondary actions",
    "accent": "Highlights and attention-drawing elements",
    "background": "Page/screen background",
    "surface": "Cards, panels, and elevated surfaces",
    "text": "Primary text color",
    "muted": "Secondary text and disabled states",
    "success": "Success messages and positive feedback",
    "error": "Error messages and alerts"
  },
  "colorTheory": "Explanation of color harmony and accessibility",
  "cssVariables": ":root { --primary: #XXXXXX; ... }",
  "tailwindConfig": "colors: { primary: { 50: '...', ... } }",
  "wcagCompliance": "Contrast analysis and accessibility notes"
}

IMPORTANT: Return ONLY the JSON object. No markdown, no code blocks, no explanations.
"""
