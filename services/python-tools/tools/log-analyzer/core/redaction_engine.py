from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Pattern registry
# ---------------------------------------------------------------------------

# Each tuple: (category_key, compiled_regex)
# Patterns are evaluated in order; earlier patterns take precedence.
_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    # --- secrets / credentials ---
    ("SECRET",  re.compile(r'(?i)(password|passwd|pwd|secret|token|api[_-]?key|auth[_-]?key)\s*[=:\s]\s*[\'"]?[\w!@#$%^&*()+=,.?/-]{4,}[\'"]?', re.IGNORECASE)),
    ("SECRET",  re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*')),
    ("SECRET",  re.compile(r'(?i)authorization:\s*\S+')),

    # --- network ---
    ("IP",      re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')),
    ("CIDR",    re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b')),
    ("MAC",     re.compile(r'\b(?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b')),
    ("URL",     re.compile(r'https?://[^\s"\'<>]+')),

    # --- PII ---
    ("EMAIL",   re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')),
    ("USER",    re.compile(r'(?i)(?:user(?:name)?|login|account)[=:\s]+([A-Za-z0-9_@.\-]+)')),
    ("PHONE",   re.compile(r'(?<![:\d])(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?){1,2}\d{4}\b')),

    # --- infrastructure identifiers ---
    ("HOST",    re.compile(r'\b(?:[a-z][a-z0-9\-]*\.){2,}[a-z]{2,}\b')),  # FQDNs
    ("PATH",    re.compile(r'(?<!\w)/(?:[a-zA-Z0-9_.\-]+/){2,}[a-zA-Z0-9_.\-]*')),  # deep paths with likely PII
    ("UUID",    re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE)),
]

# How to turn a sequential counter into a human-readable suffix
# 0→A, 1→B … 25→Z, 26→AA, 27→AB …
def _counter_to_label(n: int) -> str:
    letters = string.ascii_uppercase
    result = ""
    n += 1
    while n:
        n, remainder = divmod(n - 1, 26)
        result = letters[remainder] + result
    return result


@dataclass
class RedactionResult:
    redacted_text: str
    mapping: Dict[str, str]   # placeholder → original value
    stats: Dict[str, int]     # category → count of distinct values


class RedactionEngine:
    
    def __init__(self, extra_patterns: List[Tuple[str, re.Pattern[str]]] | None = None) -> None:
        self._patterns: List[Tuple[str, re.Pattern[str]]] = list(_PATTERNS)
        if extra_patterns:
            self._patterns.extend(extra_patterns)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def redact(self, raw_text: str) -> RedactionResult:
        """Run the full redaction pipeline over *raw_text*."""
        # value → placeholder (for dedup within a session)
        value_to_placeholder: Dict[str, str] = {}
        # placeholder → original value (returned to caller, never sent to API)
        placeholder_to_value: Dict[str, str] = {}
        # category → distinct-value counter
        counters: Dict[str, int] = {}

        text = raw_text

        for category, pattern in self._patterns:
            text = self._replace(
                text, pattern, category,
                value_to_placeholder, placeholder_to_value, counters,
            )

        stats = {cat: counters.get(cat, 0) for cat, _ in self._patterns}
        # collapse duplicate categories
        stats = {k: v for k, v in stats.items() if v}

        return RedactionResult(
            redacted_text=text,
            mapping=placeholder_to_value,
            stats=stats,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _replace(
        text: str,
        pattern: re.Pattern[str],
        category: str,
        value_to_placeholder: Dict[str, str],
        placeholder_to_value: Dict[str, str],
        counters: Dict[str, int],
    ) -> str:
        def _sub(m: re.Match[str]) -> str:
            raw = m.group(0)
            if raw in value_to_placeholder:
                return value_to_placeholder[raw]
            idx = counters.get(category, 0)
            counters[category] = idx + 1
            label = _counter_to_label(idx)
            placeholder = f"<{category}_{label}>"
            value_to_placeholder[raw] = placeholder
            placeholder_to_value[placeholder] = raw
            return placeholder

        return pattern.sub(_sub, text)