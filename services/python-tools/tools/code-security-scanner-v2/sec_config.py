"""
Code Security Scanner V2 — Configuration
==========================================
Model assignments per agent role, API config, and severity thresholds.
"""

import os

# ─── API Configuration ─────────────────────────────────────────────────
OXLO_API_KEY = os.getenv("OXLO_API_KEY", "")
OXLO_BASE_URL = os.getenv("OXLO_BASE_URL", "https://api.oxlo.ai/v1")

# ─── OSV (CVE) API ────────────────────────────────────────────────────
OSV_API_URL = "https://api.osv.dev/v1/query"

# ─── Model Assignments ────────────────────────────────────────────────
SCANNER_MODEL = None              # No LLM — pure deterministic
AUDITOR_MODEL = "deepseek-r1-0528"
FIXER_MODEL = "llama-3.3-70b"       # Fast model — fixer just formats patches, no deep reasoning needed
REPORTER_MODEL = "llama-3.3-70b"

# ─── Severity Thresholds ──────────────────────────────────────────────
SEVERITY_WEIGHTS = {
    "CRITICAL": 10,
    "HIGH": 7,
    "MEDIUM": 4,
    "LOW": 1,
}

# ─── Multi-File Limits ────────────────────────────────────────────────
MAX_FILES = 50
MAX_TOTAL_SIZE_MB = 10
MAX_SINGLE_FILE_BYTES = 500_000  # 500KB per file

# ─── Supported Languages ──────────────────────────────────────────────
LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "go": ".go",
    "java": ".java",
    "c": ".c",
    "cpp": ".cpp",
    "ruby": ".rb",
    "php": ".php",
    "rust": ".rs",
}

# Extensions that are config/dependency files (not code)
CONFIG_EXTENSIONS = {
    ".env", ".ini", ".cfg", ".toml", ".yaml", ".yml", ".json",
    ".lock", ".txt",  # requirements.txt, package-lock.json, etc.
}

CONFIG_FILENAMES = {
    "settings.py", "config.py", "manage.py",
    ".env", ".env.local", ".env.production",
    "requirements.txt", "Pipfile", "setup.py", "pyproject.toml",
    "package.json", "package-lock.json", "yarn.lock",
    "Gemfile", "composer.json", "go.mod", "Cargo.toml",
}
