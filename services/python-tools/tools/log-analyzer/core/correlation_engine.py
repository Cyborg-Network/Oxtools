from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional, Set, Tuple

from .log_parser import LogEntry, LogLevel
from .statistical_analyzer import _normalise_message


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class CorrelatedPair:
    pattern_a: str
    pattern_b: str
    co_occurrence_count: int
    avg_lag_seconds: Optional[float]   # None if no timestamps
    confidence: float                  # 0.0–1.0


@dataclass
class CascadeChain:
    root: str
    chain: List[str]          # root → ... → leaf
    total_occurrences: int


@dataclass
class CorrelationResult:
    correlated_pairs: List[CorrelatedPair]
    cascade_chains: List[CascadeChain]
    source_hotspots: Dict[str, int]     # source → error count


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CorrelationEngine:
    """
    Detects cascading / co-occurring error patterns.

    Parameters
    ----------
    time_window_seconds:
        Maximum gap between two events to be considered temporally related.
    min_co_occurrences:
        Minimum times a pair must co-occur to be reported.
    max_chain_depth:
        Maximum cascade chain length.
    """

    def __init__(
        self,
        time_window_seconds: float = 30.0,
        min_co_occurrences: int = 2,
        max_chain_depth: int = 5,
    ) -> None:
        self._window = time_window_seconds
        self._min_co = min_co_occurrences
        self._max_chain_depth = max_chain_depth

    def correlate(self, entries: List[LogEntry]) -> CorrelationResult:
        error_entries = [
            e for e in entries
            if e.level in (LogLevel.ERROR, LogLevel.CRITICAL, LogLevel.WARNING)
        ]

        source_hotspots = self._source_hotspots(error_entries)
        co_occurrence = self._build_co_occurrence(error_entries)
        pairs = self._build_pairs(error_entries, co_occurrence)
        chains = self._build_chains(co_occurrence)

        return CorrelationResult(
            correlated_pairs=pairs,
            cascade_chains=chains,
            source_hotspots=source_hotspots,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _source_hotspots(self, entries: List[LogEntry]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for e in entries:
            if e.source:
                counts[e.source] += 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def _build_co_occurrence(
        self, entries: List[LogEntry]
    ) -> Dict[str, Dict[str, List[Optional[float]]]]:
        """
        Returns: pattern_a → {pattern_b: [lag_seconds, ...]}
        """
        co: Dict[str, Dict[str, List[Optional[float]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for i, ea in enumerate(entries):
            norm_a = _normalise_message(ea.message)
            for eb in entries[i + 1:]:
                norm_b = _normalise_message(eb.message)
                if norm_a == norm_b:
                    continue

                # Time-gate
                if ea.timestamp and eb.timestamp:
                    lag = (eb.timestamp - ea.timestamp).total_seconds()
                    if lag < 0 or lag > self._window:
                        break  # entries are ordered; no point continuing
                    co[norm_a][norm_b].append(lag)
                else:
                    # No timestamps — use sequential proximity (within 10 entries)
                    if (eb is entries[min(i + 10, len(entries) - 1)]) or True:
                        co[norm_a][norm_b].append(None)
                    break

        return co

    def _build_pairs(
        self,
        entries: List[LogEntry],
        co: Dict[str, Dict[str, List[Optional[float]]]],
    ) -> List[CorrelatedPair]:
        pairs: List[CorrelatedPair] = []

        # Total occurrences of each pattern (for confidence)
        totals: Dict[str, int] = defaultdict(int)
        for e in entries:
            totals[_normalise_message(e.message)] += 1

        for pattern_a, successors in co.items():
            for pattern_b, lags in successors.items():
                count = len(lags)
                if count < self._min_co:
                    continue
                numeric_lags = [l for l in lags if l is not None]
                avg_lag = (
                    sum(numeric_lags) / len(numeric_lags)
                    if numeric_lags else None
                )
                confidence = min(count / max(totals.get(pattern_a, 1), 1), 1.0)
                pairs.append(CorrelatedPair(
                    pattern_a=pattern_a[:100],
                    pattern_b=pattern_b[:100],
                    co_occurrence_count=count,
                    avg_lag_seconds=round(avg_lag, 2) if avg_lag is not None else None,
                    confidence=round(confidence, 3),
                ))

        pairs.sort(key=lambda p: p.co_occurrence_count, reverse=True)
        return pairs[:30]  # cap to top 30 to keep payload small

    def _build_chains(
        self, co: Dict[str, Dict[str, List[Optional[float]]]]
    ) -> List[CascadeChain]:
        chains: List[CascadeChain] = []
        visited: Set[str] = set()

        # Find roots: nodes that appear as pattern_a but not (or rarely) as pattern_b
        all_bs: Set[str] = {b for successors in co.values() for b in successors}
        roots = [a for a in co if a not in all_bs]

        for root in roots:
            chain = self._dfs(root, co, set(), depth=0)
            if len(chain) >= 2:
                total = sum(len(v) for v in co.get(root, {}).values())
                chains.append(CascadeChain(
                    root=root[:100],
                    chain=[c[:100] for c in chain],
                    total_occurrences=total,
                ))

        chains.sort(key=lambda c: c.total_occurrences, reverse=True)
        return chains[:10]

    def _dfs(
        self,
        node: str,
        co: Dict[str, Dict[str, List[Optional[float]]]],
        visited: Set[str],
        depth: int,
    ) -> List[str]:
        if depth >= self._max_chain_depth or node in visited:
            return [node]
        visited = visited | {node}
        successors = co.get(node, {})
        if not successors:
            return [node]
        # Follow the highest-confidence edge
        best = max(successors.items(), key=lambda kv: len(kv[1]))
        return [node] + self._dfs(best[0], co, visited, depth + 1)