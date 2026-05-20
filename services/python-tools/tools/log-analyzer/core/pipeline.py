from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .redaction_engine import RedactionEngine, RedactionResult
from .log_parser import LogParser, LogEntry
from .statistical_analyzer import StatisticalAnalyzer, AnalysisResult
from .correlation_engine import CorrelationEngine, CorrelationResult
from .context_compressor import ContextCompressor


@dataclass
class PipelineResult:
    # Stage outputs (kept locally, never fully sent to API)
    redaction: RedactionResult
    entries: List[LogEntry]
    stats: AnalysisResult
    correlations: CorrelationResult

    # Stage 5 output — this IS sent to the API
    compressed: Dict[str, Any]

    # Metadata
    wall_time_ms: float
    format_detected: str
    warnings: List[str] = field(default_factory=list)

    # Redacted raw excerpt — sent alongside the payload so the model
    # sees actual error content even when statistics are sparse
    raw_log_excerpt: str = ""

    @property
    def payload_json(self) -> str:
        return self.compressed["payload_json"]

    @property
    def estimated_tokens(self) -> int:
        return self.compressed["estimated_tokens"]


class Pipeline:
    

    def __init__(
        self,
        redaction_engine: Optional[RedactionEngine] = None,
        log_parser: Optional[LogParser] = None,
        statistical_analyzer: Optional[StatisticalAnalyzer] = None,
        correlation_engine: Optional[CorrelationEngine] = None,
        context_compressor: Optional[ContextCompressor] = None,
    ) -> None:
        self._redactor   = redaction_engine     or RedactionEngine()
        self._parser     = log_parser           or LogParser()
        self._stats      = statistical_analyzer or StatisticalAnalyzer()
        self._correlator = correlation_engine   or CorrelationEngine()
        self._compressor = context_compressor   or ContextCompressor()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, raw_text: str, user_query: str = "", query: str = "") -> PipelineResult:
        # Accept both 'user_query' and 'query' as the question parameter
        effective_query = user_query or query
        t0 = time.perf_counter()
        warnings: List[str] = []

        # --- Stage 1: Redaction ---
        redaction = self._redactor.redact(raw_text)
        if redaction.stats:
            warnings.append(
                f"Redacted: {', '.join(f'{v} {k}(s)' for k, v in redaction.stats.items())}"
            )

        # --- Stage 2: Parse ---
        entries = self._parser.parse(redaction.redacted_text)
        if not entries:
            warnings.append("No log entries could be parsed from the input.")

        # --- Stage 3: Statistical analysis ---
        stats = self._stats.analyze(entries)

        # --- Stage 4: Correlation ---
        correlations = self._correlator.correlate(entries)

        # --- Stage 5: Compress ---
        compressed = self._compressor.compress(stats, correlations, effective_query)
        if compressed.get("compression_notes"):
            warnings.extend(compressed["compression_notes"])

        # Dominant format detection
        formats = [e.format_detected for e in entries]
        dominant = max(set(formats), key=formats.count) if formats else "unknown"

        # Build raw excerpt — prioritises high-signal lines so the model
        # sees the actual error content even when stats are sparse
        raw_log_excerpt = self._build_excerpt(redaction.redacted_text, entries)

        elapsed = (time.perf_counter() - t0) * 1000

        return PipelineResult(
            redaction=redaction,
            entries=entries,
            stats=stats,
            correlations=correlations,
            compressed=compressed,
            wall_time_ms=round(elapsed, 2),
            format_detected=dominant,
            warnings=warnings,
            raw_log_excerpt=raw_log_excerpt,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_excerpt(redacted_text: str, entries: list) -> str:
        """
        Build a concise excerpt of the most informative lines from the
        redacted log text.  Priority order:
          1. Lines containing ERROR / CRITICAL / exception / HTTP 4xx-5xx keywords
          2. Lines mentioning endpoints, URLs, services, or deployments
          3. Remaining lines up to the cap

        Max 30 lines / 4000 chars — enough context without wasting tokens.
        """
        lines = [l for l in redacted_text.splitlines() if l.strip()]

        _HIGH = re.compile(
            r'error|critical|fatal|exception|traceback|failed|failure'
            r'|timeout|refused|unavailable|crash|panic|killed'
            r'|\b[45]\d{2}\b|404|500|502|503|401|403',
            re.IGNORECASE,
        )
        _MED = re.compile(
            r'warn|url|endpoint|http|https|api|service|module|deploy|route',
            re.IGNORECASE,
        )

        high, med, low = [], [], []
        for line in lines:
            if _HIGH.search(line):
                high.append(line)
            elif _MED.search(line):
                med.append(line)
            else:
                low.append(line)

        selected = (high + med + low)[:30]
        excerpt = "\n".join(selected)

        if len(excerpt) > 4000:
            excerpt = excerpt[:3997] + "..."

        return excerpt