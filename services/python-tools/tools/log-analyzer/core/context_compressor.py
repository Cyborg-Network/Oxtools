from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from .statistical_analyzer import AnalysisResult
from .correlation_engine import CorrelationResult


# ---------------------------------------------------------------------------
# Short-name mapping (saves ~30% tokens on field names)
# ---------------------------------------------------------------------------
# Full name → compact alias used in the JSON sent to the LLM.
# The LLM system prompt explains these aliases once, paying the cost
# a single time rather than per-request.

_COMPACT = {
    "total_entries":        "n",
    "level_distribution":   "lvls",
    "top_errors":           "errs",
    "unique_error_count":   "u_errs",
    "burst_windows":        "bursts",
    "escalation_events":    "escalations",
    "has_timestamps":       "has_ts",
    "time_span_seconds":    "span_s",
    "correlated_pairs":     "corr",
    "cascade_chains":       "chains",
    "source_hotspots":      "hotspots",
    "pattern_a":            "a",
    "pattern_b":            "b",
    "co_occurrence_count":  "cnt",
    "avg_lag_seconds":      "lag",
    "confidence":           "conf",
    "root":                 "r",
    "chain":                "ch",
    "total_occurrences":    "tot",
    "start":                "s",
    "end":                  "e",
    "error_count":          "ec",
    "rate_multiplier":      "mx",
    "timestamp":            "ts",
    "from_level":           "f",
    "to_level":             "t",
    "message":              "m",
}


def _compact(d: Dict[str, Any]) -> Dict[str, Any]:
    return {_COMPACT.get(k, k): v for k, v in d.items()}


def _q(v: Optional[float]) -> Optional[float]:
    """Quantise to 2 decimal places."""
    return round(v, 2) if v is not None else None


def _trunc(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


# ---------------------------------------------------------------------------
# Rough token estimator (character-based, ~4 chars/token for JSON)
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


# ---------------------------------------------------------------------------
# Compressor
# ---------------------------------------------------------------------------

class ContextCompressor:
    """
    Produces a token-minimised JSON payload from pipeline stage outputs.

    Parameters
    ----------
    max_top_errors:
        Number of top error patterns to include (default 15).
    max_correlated_pairs:
        Number of correlation pairs to include (default 10).
    max_cascade_chains:
        Number of cascade chains to include (default 5).
    max_timeline_buckets:
        Busiest N time buckets to include (default 10).
    max_escalations:
        Number of escalation events to include (default 10).
    pattern_min_count:
        Drop error patterns occurring fewer than this many times.
    """

    def __init__(
        self,
        max_top_errors: int = 15,
        max_correlated_pairs: int = 10,
        max_cascade_chains: int = 5,
        max_timeline_buckets: int = 10,
        max_escalations: int = 10,
        pattern_min_count: int = 1,
    ) -> None:
        self._max_errors = max_top_errors
        self._max_pairs = max_correlated_pairs
        self._max_chains = max_cascade_chains
        self._max_buckets = max_timeline_buckets
        self._max_escalations = max_escalations
        self._min_count = pattern_min_count

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress(
        self,
        stats: AnalysisResult,
        correlations: CorrelationResult,
        user_query: str = "",
    ) -> Dict[str, Any]:
        """
        Returns a dict with keys:
            "payload"        — the compressed JSON object (send to LLM)
            "payload_json"   — serialised string of payload
            "estimated_tokens" — rough token count of payload_json
            "compression_notes" — human-readable summary of what was dropped
        """
        payload = self._build_payload(stats, correlations)
        payload_json = json.dumps(payload, separators=(",", ":"))

        notes = self._compression_notes(stats, correlations, payload)

        return {
            "payload": payload,
            "payload_json": payload_json,
            "estimated_tokens": _estimate_tokens(payload_json),
            "user_query": user_query,
            "compression_notes": notes,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        s: AnalysisResult,
        c: CorrelationResult,
    ) -> Dict[str, Any]:
        # --- Top errors (filter + truncate) ---
        top_errs = [
            {"p": _trunc(pattern), "c": count}
            for pattern, count in s.top_errors[: self._max_errors]
            if count >= self._min_count
        ]

        # --- Burst windows ---
        bursts = [
            _compact({
                "start": b.start,
                "end": b.end,
                "error_count": b.error_count,
                "rate_multiplier": _q(b.rate_multiplier),
            })
            for b in s.burst_windows
        ]

        # --- Escalation events (most recent N) ---
        escalations = [
            _compact({
                "timestamp": e.timestamp,
                "from_level": e.from_level.value,
                "to_level": e.to_level.value,
                "message": _trunc(e.message, 80),
            })
            for e in s.escalation_events[-self._max_escalations :]
        ]

        # --- Timeline: top-N busiest error buckets ---
        timeline = self._prune_timeline(s.timeline_buckets)

        # --- Correlation pairs ---
        pairs = [
            _compact({
                "pattern_a": _trunc(p.pattern_a, 80),
                "pattern_b": _trunc(p.pattern_b, 80),
                "co_occurrence_count": p.co_occurrence_count,
                "avg_lag_seconds": _q(p.avg_lag_seconds),
                "confidence": _q(p.confidence),
            })
            for p in c.correlated_pairs[: self._max_pairs]
        ]

        # --- Cascade chains ---
        chains = [
            _compact({
                "root": _trunc(ch.root, 80),
                "chain": [_trunc(s, 80) for s in ch.chain],
                "total_occurrences": ch.total_occurrences,
            })
            for ch in c.cascade_chains[: self._max_chains]
        ]

        # --- Source hotspots (top 10) ---
        hotspots = dict(list(c.source_hotspots.items())[:10])

        return _compact({
            "total_entries": s.total_entries,
            "has_timestamps": s.has_timestamps,
            "time_span_seconds": _q(s.time_span_seconds),
            "level_distribution": s.level_distribution,
            "unique_error_count": s.unique_error_count,
            "top_errors": top_errs,
            "burst_windows": bursts,
            "escalation_events": escalations,
            "timeline": timeline,
            "correlated_pairs": pairs,
            "cascade_chains": chains,
            "source_hotspots": hotspots,
        })

    def _prune_timeline(
        self, buckets: Dict[str, Dict[str, int]]
    ) -> Dict[str, Dict[str, int]]:
        """Return the N busiest error/warn buckets, sorted chronologically."""
        if not buckets:
            return {}

        def bucket_error_count(v: Dict[str, int]) -> int:
            return sum(
                cnt for lv, cnt in v.items()
                if lv in ("ERROR", "CRITICAL", "WARNING")
            )

        sorted_by_activity = sorted(
            buckets.items(),
            key=lambda kv: bucket_error_count(kv[1]),
            reverse=True,
        )[: self._max_buckets]

        # Re-sort chronologically
        return dict(sorted(sorted_by_activity, key=lambda kv: kv[0]))

    def _compression_notes(
        self,
        s: AnalysisResult,
        c: CorrelationResult,
        payload: Dict[str, Any],
    ) -> List[str]:
        notes: List[str] = []

        dropped_errors = s.unique_error_count - len(payload.get("errs", []))
        if dropped_errors > 0:
            notes.append(f"Dropped {dropped_errors} low-frequency error patterns.")

        dropped_pairs = len(c.correlated_pairs) - len(payload.get("corr", []))
        if dropped_pairs > 0:
            notes.append(f"Dropped {dropped_pairs} low-confidence correlation pairs.")

        dropped_buckets = len(s.timeline_buckets) - len(payload.get("timeline", {}))
        if dropped_buckets > 0:
            notes.append(f"Pruned {dropped_buckets} quiet timeline buckets.")

        return notes