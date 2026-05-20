from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.pipeline import PipelineResult
    from core.llm_client import RCAResponse


# ── Severity styling ──────────────────────────────────────────────────────

_SEVERITY_LABEL = {
    "P1": "P1 — CRITICAL",
    "P2": "P2 — HIGH",
    "P3": "P3 — MEDIUM",
    "P4": "P4 — LOW",
}

_PRIORITY_LABEL = {
    "HIGH":   "[HIGH]",
    "MEDIUM": "[MEDIUM]",
    "LOW":    "[LOW]",
}


def _span(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def _conf_bar(conf: float) -> str:
    filled = round(conf * 10)
    return "█" * filled + "░" * (10 - filled)


# ── Main assembler ────────────────────────────────────────────────────────

def assemble_report(pipeline: "PipelineResult", rca: "RCAResponse") -> str:
    s   = pipeline.stats
    c   = pipeline.correlations
    sections: list[str] = []
    severity_display = _SEVERITY_LABEL.get(rca.severity, rca.severity or "Unknown")

    # ── Header ────────────────────────────────────────────────────────────
    severity_display = _SEVERITY_LABEL.get(rca.severity, rca.severity or "Unknown")
    sections.append(f"# System Log Analysis Report")

    # ── Executive summary ─────────────────────────────────────────────────
    if rca.executive_summary:
        sev_line = (
            f"\n\n**Severity:** {severity_display}"
            + (f" — {rca.severity_rationale}" if rca.severity_rationale else "")
        )
        sections.append(f"## Executive Summary\n\n{rca.executive_summary}{sev_line}")

    # ── Incident timeline ─────────────────────────────────────────────────
    if rca.incident_timeline:
        rows = "\n".join(
            f"| `{e.get('time', '')}` | {e.get('event', '')} |"
            for e in rca.incident_timeline
        )
        sections.append(
            f"## Incident Timeline\n\n"
            f"| Time | Event |\n|---|---|\n{rows}"
        )

    # ── Level distribution ────────────────────────────────────────────────
    if s.level_distribution:
        rows = "\n".join(
            f"| `{lvl}` | {cnt:,} |"
            for lvl, cnt in sorted(s.level_distribution.items(), key=lambda x: x[1], reverse=True)
        )
        sections.append(f"## Level Distribution\n\n| Level | Count |\n|---|---|\n{rows}")

    # ── Top error patterns ────────────────────────────────────────────────
    if s.top_errors:
        rows = "\n".join(
            f"| `{pat[:90]}` | {cnt:,} |"
            for pat, cnt in s.top_errors[:10]
        )
        sections.append(
            f"## Top Error Patterns\n\n"
            f"| Pattern | Occurrences |\n|---|---|\n{rows}"
        )

    # ── Burst windows ─────────────────────────────────────────────────────
    if s.burst_windows:
        items = "\n".join(
            f"- `{b.start}` → `{b.end}` — "
            f"**{b.error_count} errors** at **{b.rate_multiplier}x** baseline rate"
            for b in s.burst_windows
        )
        sections.append(f"## Burst Windows\n\n{items}")

    # ── Root causes ───────────────────────────────────────────────────────
    if rca.root_causes:
        parts = []
        for i, rc in enumerate(rca.root_causes, 1):
            conf  = rc.get("confidence", 0.0)
            bar   = _conf_bar(conf)
            svcs  = rc.get("affected_services", [])
            svc_line = (
                f"\n\n**Affected services:** {', '.join(f'`{s}`' for s in svcs)}"
                if svcs else ""
            )
            parts.append(
                f"### {i}. {rc.get('title', 'Unknown')}\n\n"
                f"**Confidence:** `{conf:.0%}` {bar}"
                f"{svc_line}\n\n"
                f"{rc.get('evidence', '')}"
            )
        sections.append("## Root Causes\n\n" + "\n\n---\n\n".join(parts))

    # ── Immediate actions ─────────────────────────────────────────────────
    if rca.immediate_actions:
        items = "\n".join(f"- {a}" for a in rca.immediate_actions)
        sections.append(f"## Immediate Actions\n\n{items}")

    # ── Recommended fixes ─────────────────────────────────────────────────
    if rca.fixes:
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_fixes = sorted(
            rca.fixes,
            key=lambda f: priority_order.get(f.get("priority", "LOW"), 2)
        )
        parts = []
        for fix in sorted_fixes:
            p       = fix.get("priority", "MEDIUM")
            label   = _PRIORITY_LABEL.get(p, p)
            effort  = fix.get("effort", "Unknown")
            addr    = fix.get("addresses", "")
            addr_line = f"\n\n*Addresses:* {addr}" if addr else ""
            parts.append(
                f"### {label} — {fix.get('description', '')}\n\n"
                f"**Effort:** {effort}{addr_line}"
            )
        sections.append("## Recommended Fixes\n\n" + "\n\n".join(parts))

    # ── Prevention strategies ─────────────────────────────────────────────
    if rca.prevention_strategies:
        items = "\n".join(f"- {p}" for p in rca.prevention_strategies)
        sections.append(f"## Prevention Strategies\n\n{items}")

    # ── Monitoring recommendations ────────────────────────────────────────
    if rca.monitoring_recommendations:
        items = "\n".join(f"- {m}" for m in rca.monitoring_recommendations)
        sections.append(f"## Monitoring Recommendations\n\n{items}")

    # ── Cascade chains ────────────────────────────────────────────────────
    if c.cascade_chains:
        items = "\n".join(
            f"- **Root:** `{ch.root[:70]}`  \n"
            f"  Chain: {' > '.join(node[:60] for node in ch.chain)}"
            for ch in c.cascade_chains[:5]
        )
        sections.append(f"## Cascade Chains (Local Detection)\n\n{items}")

    # ── Correlated error pairs ────────────────────────────────────────────
    if c.correlated_pairs:
        rows = "\n".join(
            f"| `{p.pattern_a[:45]}` | `{p.pattern_b[:45]}` | "
            f"{p.co_occurrence_count} | "
            f"{'%.1fs' % p.avg_lag_seconds if p.avg_lag_seconds is not None else 'n/a'} | "
            f"{p.confidence:.0%} |"
            for p in c.correlated_pairs[:8]
        )
        sections.append(
            f"## Correlated Error Pairs (Local Detection)\n\n"
            f"| Pattern A | Pattern B | Co-occurrences | Avg Lag | Confidence |\n"
            f"|---|---|---|---|---|\n{rows}"
        )

    # ── Follow-up questions ───────────────────────────────────────────────
    if rca.follow_up_questions:
        items = "\n".join(f"- {q}" for q in rca.follow_up_questions)
        sections.append(f"## Suggested Follow-up Investigations\n\n{items}")

    return "\n\n---\n\n".join(sections)