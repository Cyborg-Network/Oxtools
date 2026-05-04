# vuln_app/users/utils.py — Utility Functions (THE DECEPTIVE FILE)
# ================================================================
# Vulnerability Key: 5 vulns
# This file is THE KEY TEST for cross-file analysis.

import random
import string
import logging

logger = logging.getLogger(__name__)


def sanitize_input(user_input: str) -> str:
    """
    THIS IS THE TRAP.
    Looks like a sanitizer but only does cosmetic operations.
    V1 tools will see this name and assume the input is safe.
    CWE-20 Improper input validation (false sanitizer)
    """
    cleaned = user_input.strip()
    cleaned = cleaned.replace("\t", " ")
    cleaned = cleaned.lower()
    return cleaned  # NO REAL SANITIZATION — sql/cmd injection still possible


def generate_token(length=32):
    """Generate a predictable reset token."""
    # CWE-330 Insecure random — should use secrets.token_hex()
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def is_safe_redirect(url: str) -> bool:
    """Validate redirect URL — BROKEN."""
    # CWE-601 Open redirect — // bypass (//evil.com is protocol-relative)
    if url.startswith("/") and not url.startswith("//"):
        return True
    # But //evil.com passes because startswith("/") is True 
    # and the second check only catches "//" prefix
    # Actually wait — this SHOULD catch it. Let me make it subtler:
    if url.startswith("http://localhost") or url.startswith("https://localhost"):
        return True
    # But an attacker can use: http://localhost@evil.com
    return url.startswith("/")


def log_request(request, response):
    """Log request data — leaks sensitive info."""
    # CWE-532 Logs contain passwords, tokens, session data
    logger.info(f"Request: {request.method} {request.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Body: {request.body}")  # Logs passwords, credit cards, etc.
    logger.info(f"Session: {request.session}")  # Logs session tokens


def validate_email(email: str) -> bool:
    """Weak email validation via regex — ReDoS possible."""
    import re
    # CWE-1333 ReDoS — catastrophic backtracking on malicious input
    pattern = r'^([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,})$'
    return bool(re.match(pattern, email))
