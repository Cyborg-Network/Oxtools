from __future__ import annotations

import re
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
    "HIGH":   "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW":    "LOW",
}


def _conf_bar(conf: float) -> str:
    filled = round(conf * 10)
    return "█" * filled + "░" * (10 - filled)


def _scrub(text: str) -> str:
    """Strip ALL model artefacts: ::: callout blocks, <think> traces.
    Handles both closed and UNCLOSED blocks (model truncated at token limit).
    """
    # 1. Closed ::: callout blocks
    text = re.sub(
        r":::[^\n]*\n.*?(?:\n\s*:::[ \t]*|\s*:::[ \t]*\Z)",
        "",
        text,
        flags=re.DOTALL,
    )
    # 2. UNCLOSED ::: callout — strip from opener to end-of-string
    text = re.sub(r":::[^\n]*\n.*\Z", "", text, flags=re.DOTALL)
    # 3. Closed <think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # 4. UNCLOSED <think> block
    text = re.sub(r"<think>.*\Z", "", text, flags=re.DOTALL)
    # 5. Any leftover ::: lines
    text = re.sub(r"^[ \t]*:::.*$", "", text, flags=re.MULTILINE)
    return text.strip()


# ── Main assembler ────────────────────────────────────────────────────────

def assemble_report(pipeline: "PipelineResult", rca: "RCAResponse", report_type: str = "detailed") -> str:
    s = pipeline.stats
    c = pipeline.correlations
    sections: list[str] = []

    severity_display = _SEVERITY_LABEL.get(rca.severity, rca.severity or "Unknown")
    executive_summary = _scrub(rca.executive_summary) if rca.executive_summary else ""
    sev_rationale = f" — {rca.severity_rationale}" if getattr(rca, "severity_rationale", None) else ""

    # ── Header ────────────────────────────────────────────────────────────
    sections.append("# System Log Analysis Report")

    # ── Severity badge ────────────────────────────────────────────────────
    sections.append(f"> **{severity_display}**{sev_rationale}")

    # ── What Happened (brief summary) ────────────────────────────────────
    if executive_summary:
        detail_hint = (
            "\n\n> *Full breakdown including timeline and patterns is in the **Detailed Analysis** section below.*"
            if report_type != "fix_only" else ""
        )
        sections.append(f"## What Happened\n\n{executive_summary}{detail_hint}")

    # ── Solution ──────────────────────────────────────────────────────────
    solution_parts = []

    if rca.immediate_actions:
        items = "\n".join(f"- {a}" for a in rca.immediate_actions)
        solution_parts.append(f"### Immediate Actions\n\n{items}")

    if rca.fixes:
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_fixes = sorted(
            rca.fixes,
            key=lambda f: priority_order.get(f.get("priority", "LOW"), 2),
        )
        fix_items = []
        for fix in sorted_fixes:
            p         = fix.get("priority", "MEDIUM")
            label     = _PRIORITY_LABEL.get(p, p)
            effort    = fix.get("effort", "Unknown")
            addr      = fix.get("addresses", "")
            addr_line = f"\n\n*Addresses:* {addr}" if addr else ""
            fix_items.append(
                f"#### `{label}` — {fix.get('description', '')}\n\n"
                f"**Effort:** {effort}{addr_line}"
            )
        solution_parts.append("### Recommended Fixes\n\n" + "\n\n".join(fix_items))
        
    solution_section = ""
    if solution_parts:
        solution_section = "## Solution\n\n" + "\n\n".join(solution_parts)
    else:
        solution_section = "## Solution\n\nNo specific solutions were identified."

    if report_type == "fix_only":
        # Compact report: severity → brief summary → solution only.
        # Deliberately excludes timeline, root causes, patterns, and all
        # detailed-analysis sections so the developer can act immediately.
        fix_only_parts: list[str] = [f"> **{severity_display}**{sev_rationale}"]
        if executive_summary:
            fix_only_parts.append(f"## What Happened\n\n{executive_summary}")
        fix_only_parts.append(solution_section)
        return "\n\n---\n\n".join(fix_only_parts)

    # Add solution to main sections for detailed report
    sections.append(solution_section)

    # ── Detailed Analysis ─────────────────────────────────────────────────
    sections.append("## Detailed Analysis")

    # ── Incident timeline ─────────────────────────────────────────────────
    if rca.incident_timeline:
        rows = "\n".join(
            f"| `{e.get('time', '')}` | {e.get('event', '')} |"
            for e in rca.incident_timeline
        )
        sections.append(
            f"### Incident Timeline\n\n"
            f"| Time | Event |\n|---|---|\n{rows}"
        )

    # ── Root causes ───────────────────────────────────────────────────────
    if rca.root_causes:
        parts = []
        for i, rc in enumerate(rca.root_causes, 1):
            conf     = rc.get("confidence", 0.0)
            bar      = _conf_bar(conf)
            svcs     = rc.get("affected_services", [])
            svc_line = (
                f"\n\n**Affected services:** {', '.join(f'`{svc}`' for svc in svcs)}"
                if svcs else ""
            )
            parts.append(
                f"#### {i}. {rc.get('title', 'Unknown')}\n\n"
                f"**Confidence:** `{conf:.0%}` {bar}"
                f"{svc_line}\n\n"
                f"{rc.get('evidence', '')}"
            )
        sections.append("### Root Causes\n\n" + "\n\n---\n\n".join(parts))

    # ── Prevention strategies — right after root causes ───────────────────
    if rca.prevention_strategies:
        items = "\n".join(f"- {p}" for p in rca.prevention_strategies)
        sections.append(f"### Prevention Strategies\n\n{items}")

    # ── Monitoring recommendations — right after prevention ───────────────
    if rca.monitoring_recommendations:
        items = "\n".join(f"- {m}" for m in rca.monitoring_recommendations)
        sections.append(f"### Monitoring Recommendations\n\n{items}")

    # ── Level distribution ────────────────────────────────────────────────
    if s.level_distribution:
        rows = "\n".join(
            f"| `{lvl}` | {cnt:,} |"
            for lvl, cnt in sorted(s.level_distribution.items(), key=lambda x: x[1], reverse=True)
        )
        sections.append(f"### Level Distribution\n\n| Level | Count |\n|---|---|\n{rows}")

    # ── Top error patterns ────────────────────────────────────────────────
    if s.top_errors:
        rows = "\n".join(
            f"| `{pat[:90]}` | {cnt:,} |"
            for pat, cnt in s.top_errors[:10]
        )
        sections.append(
            f"### Top Error Patterns\n\n"
            f"| Pattern | Occurrences |\n|---|---|\n{rows}"
        )

    # ── Burst windows ─────────────────────────────────────────────────────
    if s.burst_windows:
        items = "\n".join(
            f"- `{b.start}` → `{b.end}` — "
            f"**{b.error_count} errors** at **{b.rate_multiplier}x** baseline rate"
            for b in s.burst_windows
        )
        sections.append(f"### Burst Windows\n\n{items}")

    # ── Cascade chains ────────────────────────────────────────────────────
    if c.cascade_chains:
        items = "\n".join(
            f"- **Root:** `{ch.root[:70]}`  \n"
            f"  Chain: {' → '.join(node[:60] for node in ch.chain)}"
            for ch in c.cascade_chains[:5]
        )
        sections.append(f"### Cascade Chains\n\n{items}")

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
            f"### Correlated Error Pairs\n\n"
            f"| Pattern A | Pattern B | Co-occurrences | Avg Lag | Confidence |\n"
            f"|---|---|---|---|---|\n{rows}"
        )

    # ── Follow-up questions ───────────────────────────────────────────────
    if rca.follow_up_questions:
        items = "\n".join(f"- {q}" for q in rca.follow_up_questions)
        sections.append(f"### Suggested Follow-up Investigations\n\n{items}")

    return "\n\n---\n\n".join(sections)