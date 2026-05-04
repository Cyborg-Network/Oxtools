"""
JSON to Schema V2 — Configuration
===================================
Model assignments and API config.

KEY FIX: Use user's selected model for Architect (main analysis node).
"""

import os

# ─── API Configuration ─────────────────────────────────────────────────
OXLO_API_KEY = os.getenv("OXLO_API_KEY", "")
OXLO_BASE_URL = os.getenv("OXLO_BASE_URL", "https://api.oxlo.ai/v1")

# ─── Model Assignments (fallbacks — user model takes priority) ─────────
PARSER_MODEL = None                      # No LLM — pure Python
ARCHITECT_MODEL = "deepseek-r1-0528"     # Fallback for schema design
REVIEWER_MODEL = "deepseek-r1-0528"      # Fallback for review
COMPILER_MODEL = None                    # No LLM — deterministic
DOCUMENTER_MODEL = "llama-3.3-70b"       # Fast model for docs

# ─── Compiler Defaults ────────────────────────────────────────────────
DEFAULT_OUTPUT_FORMAT = "postgresql"
MAX_JSON_SIZE = 100_000  # 100KB max input

# ─── Refinement Config ────────────────────────────────────────────────
MAX_REVIEW_ITERATIONS = 2
