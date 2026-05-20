from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .log_parser import LogEntry, LogLevel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NORMALISE_RE = re.compile(r'(0x[0-9a-fA-F]+|\b\d+\b|"[^"]*"|\'[^\']*\'|`[^`]*`)')

def _normalise_message(msg: str) -> str:
    """Replace variable tokens (numbers, hex, quoted strings) with '?'."""
    return _NORMALISE_RE.sub("?", msg).strip()


def _bucket_key(dt: datetime, bucket_minutes: int = 1) -> str:
    truncated = dt.replace(second=0, microsecond=0)
    minutes = (truncated.minute // bucket_minutes) * bucket_minutes
    truncated = truncated.replace(minute=minutes)
    return truncated.isoformat()


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class BurstWindow:
    start: str          # ISO timestamp
    end: str
    error_count: int
    rate_multiplier: float   # vs. baseline


@dataclass
class EscalationEvent:
    timestamp: str
    from_level: LogLevel
    to_level: LogLevel
    message: str


@dataclass
class AnalysisResult:
    total_entries: int
    level_distribution: Dict[str, int]
    top_errors: List[Tuple[str, int]]          # (normalised_msg, count), sorted desc
    unique_error_count: int
    burst_windows: List[BurstWindow]
    escalation_events: List[EscalationEvent]
    timeline_buckets: Dict[str, Dict[str, int]]  # minute → {level: count}
    has_timestamps: bool
    time_span_seconds: Optional[float]


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class StatisticalAnalyzer:
    
    def __init__(
        self,
        burst_threshold_multiplier: float = 3.0,
        top_n_errors: int = 20,
        bucket_minutes: int = 1,
    ) -> None:
        self._burst_threshold = burst_threshold_multiplier
        self._top_n = top_n_errors
        self._bucket_minutes = bucket_minutes

    def analyze(self, entries: List[LogEntry]) -> AnalysisResult:
        if not entries:
            return self._empty_result()

        level_dist: Counter[str] = Counter()
        error_freq: Counter[str] = Counter()
        timeline: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        timestamps: List[datetime] = []
        escalation_events: List[EscalationEvent] = []

        prev_level: Optional[LogLevel] = None
        prev_ts: Optional[str] = None

        for entry in entries:
            level_dist[entry.level.value] += 1

            norm = _normalise_message(entry.message)
            if entry.level in (LogLevel.ERROR, LogLevel.CRITICAL, LogLevel.WARNING):
                error_freq[norm] += 1

            if entry.timestamp:
                timestamps.append(entry.timestamp)
                bk = _bucket_key(entry.timestamp, self._bucket_minutes)
                timeline[bk][entry.level.value] += 1

                # Escalation detection
                if prev_level and self._is_escalation(prev_level, entry.level):
                    escalation_events.append(EscalationEvent(
                        timestamp=entry.timestamp.isoformat(),
                        from_level=prev_level,
                        to_level=entry.level,
                        message=entry.message[:120],
                    ))
                prev_ts = entry.timestamp.isoformat()
                prev_level = entry.level
            else:
                prev_level = entry.level

        burst_windows = self._detect_bursts(timeline) if timestamps else []
        top_errors = error_freq.most_common(self._top_n)
        time_span = (
            (max(timestamps) - min(timestamps)).total_seconds()
            if len(timestamps) >= 2 else None
        )

        return AnalysisResult(
            total_entries=len(entries),
            level_distribution=dict(level_dist),
            top_errors=top_errors,
            unique_error_count=len(error_freq),
            burst_windows=burst_windows,
            escalation_events=escalation_events,
            timeline_buckets={k: dict(v) for k, v in sorted(timeline.items())},
            has_timestamps=bool(timestamps),
            time_span_seconds=time_span,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    _LEVEL_SEVERITY: Dict[LogLevel, int] = {
        LogLevel.TRACE: 0, LogLevel.DEBUG: 1, LogLevel.INFO: 2,
        LogLevel.NOTICE: 3, LogLevel.WARNING: 4, LogLevel.ERROR: 5,
        LogLevel.CRITICAL: 6, LogLevel.UNKNOWN: -1,
    }

    def _is_escalation(self, prev: LogLevel, curr: LogLevel) -> bool:
        return (
            self._LEVEL_SEVERITY.get(curr, -1) > self._LEVEL_SEVERITY.get(prev, -1)
            and self._LEVEL_SEVERITY.get(curr, -1) >= self._LEVEL_SEVERITY[LogLevel.WARNING]
        )

    def _detect_bursts(self, timeline: Dict[str, Dict[str, int]]) -> List[BurstWindow]:
        buckets = sorted(timeline.keys())
        if len(buckets) < 2:
            return []

        error_counts = [
            sum(v for lv, v in timeline[b].items()
                if lv in (LogLevel.ERROR.value, LogLevel.CRITICAL.value, LogLevel.WARNING.value))
            for b in buckets
        ]
        if not any(error_counts):
            return []

        avg = sum(error_counts) / len(error_counts)
        if avg == 0:
            return []

        bursts: List[BurstWindow] = []
        i = 0
        while i < len(error_counts):
            if error_counts[i] >= avg * self._burst_threshold:
                j = i
                while j < len(error_counts) and error_counts[j] >= avg * self._burst_threshold:
                    j += 1
                bursts.append(BurstWindow(
                    start=buckets[i],
                    end=buckets[j - 1],
                    error_count=sum(error_counts[i:j]),
                    rate_multiplier=round(max(error_counts[i:j]) / avg, 2),
                ))
                i = j
            else:
                i += 1
        return bursts

    @staticmethod
    def _empty_result() -> AnalysisResult:
        return AnalysisResult(
            total_entries=0,
            level_distribution={},
            top_errors=[],
            unique_error_count=0,
            burst_windows=[],
            escalation_events=[],
            timeline_buckets={},
            has_timestamps=False,
            time_span_seconds=None,
        )