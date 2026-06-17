"""
Deep Research Agent — Configuration
"""

import os

# Oxlo API
OXLO_API_KEY = os.getenv("OXLO_API_KEY", "")
OXLO_BASE_URL = os.getenv("OXLO_BASE_URL", "https://api.oxlo.ai/v1")

# Tavily web search
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Model assignments per agent role
PLANNER_MODEL = "deepseek-r1-0528"
SEARCHER_MODEL = "llama-3.3-70b"
ANALYZER_MODEL = "deepseek-r1-0528"
VERIFIER_MODEL = "deepseek-r1-0528"
WRITER_MODEL = "llama-3.3-70b"
