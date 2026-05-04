"""
Code Security Scanner V2 — Tool Entry Point
=============================================
v3.0: Multi-file support with ZIP upload.

Architecture:
  sec_file_parser.py — Multi-file input parsing (ZIP, markers, single)
  sec_scanners.py    — 4 per-file deterministic scanners
  sec_cross_file.py  — 5 cross-file scanners (import graph, taint, config, obfuscation, CVE)
  sec_agents.py      — LangGraph: Scanner → Auditor → Fixer → Reporter
  sec_prompts.py     — Agent prompts with cross-file awareness
  sec_config.py      — Model fallbacks, limits, API config
"""

from sec_agents import build_graph, SecurityState
from sec_config import OXLO_API_KEY

MANIFEST = {
    "id": "code-security-scanner-v2",
    "name": "Code Security Scanner (Agentic V2)",
    "description": (
        "Multi-file agentic security pipeline: cross-file taint tracking, "
        "import chain analysis, obfuscation decoding, dependency CVE checks "
        "(osv.dev), config correlation + comprehensive LLM deep audit"
    ),
    "author": "Oxlo Team",
    "version": "3.0.0",
    "requires": ["langgraph", "langchain-openai", "langchain-core", "bandit", "httpx"],
}


async def run(data: dict):
    """Execute the security audit pipeline."""
    if not OXLO_API_KEY:
        return {"error": "OXLO_API_KEY not configured. Set it in .env"}

    code = data.get("code", "")
    files_data = data.get("files", "")

    if not code.strip() and not files_data.strip():
        return {"error": "No code provided. Upload files or paste code to scan."}

    language = data.get("language", "auto").lower()
    user_model = data.get("model", "")

    graph = build_graph()
    initial: SecurityState = {
        "code": code,
        "files_data": files_data,
        "language": language,
        "user_model": user_model,
        "parsed_files": [],
        "file_count": 0,
        "raw_findings": [],
        "scanner_summary": "",
        "import_graph": [],
        "taint_chains": [],
        "config_risks": [],
        "decoded_payloads": [],
        "cve_findings": [],
        "exec_eval_findings": [],
        "timing_findings": [],
        "triage_results": [],
        "deep_findings": [],
        "severity_score": 0,
        "fixes": "",
        "final_report": "",
        "status": "starting",
    }

    # Track state across the stream so we can build a fallback report on crash
    last_state = {}

    async def stream():
        nonlocal last_state
        try:
            async for event in graph.astream(initial):
                for node_name, node_output in event.items():
                    last_state.update(node_output)
                    status = node_output.get("status", "processing")
                    yield f"[{node_name}] {status}\n"

                    if node_name == "scanner":
                        file_count = node_output.get("file_count", 0)
                        yield f"  > Scanned {file_count} files\n"
                        if node_output.get("scanner_summary"):
                            yield f"  > {node_output['scanner_summary']}\n"

                        # Cross-file intelligence summary
                        tc = len(node_output.get("taint_chains", []))
                        ig = len(node_output.get("import_graph", []))
                        dp = len(node_output.get("decoded_payloads", []))
                        cve = len(node_output.get("cve_findings", []))
                        cr = len(node_output.get("config_risks", []))
                        if any([tc, ig, dp, cve, cr]):
                            yield f"  > Cross-file: {tc} taint chains, {ig} imports, {dp} decoded payloads, {cve} CVEs, {cr} config risks\n"

                    if node_name == "auditor":
                        triage = node_output.get("triage_results", [])
                        deep = node_output.get("deep_findings", [])
                        confirmed = sum(1 for t in triage if t.get("classification") == "true_positive")
                        dismissed = sum(1 for t in triage if t.get("classification") == "false_positive")
                        yield f"  > Triage: {confirmed} confirmed, {dismissed} dismissed\n"
                        yield f"  > Deep analysis: {len(deep)} additional vulnerabilities\n"
                        yield f"  > Severity score: {node_output.get('severity_score', 0)}\n"

                    if node_name == "fixer":
                        yield f"  > Secure patches generated\n"

                    if node_name == "reporter" and "final_report" in node_output:
                        yield "\n---REPORT_START---\n"
                        yield node_output["final_report"]

        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger("security-scanner")
            logger.error(f"[Pipeline] Stream crashed: {e}")
            logger.error(traceback.format_exc())

            # Emit error info to the user
            yield f"\n[error] Pipeline error: {str(e)}\n"

            # Build a fallback report from whatever state we accumulated
            triage = last_state.get("triage_results", [])
            deep = last_state.get("deep_findings", [])
            confirmed = [t for t in triage if t.get("classification") == "true_positive"]
            score = last_state.get("severity_score", 0)
            file_count = last_state.get("file_count", 0)

            if confirmed or deep:
                yield "\n---REPORT_START---\n"
                yield f"# 🛡️ Security Audit Report\n\n"
                yield f"⚠️ *Note: Report compilation encountered an error. Showing raw findings.*\n\n"
                yield f"## Summary\n"
                yield f"Scanned **{file_count}** files. Found **{len(confirmed)}** confirmed vulnerabilities"
                if deep:
                    yield f" and **{len(deep)}** additional deep findings"
                yield f".\n\nSeverity Score: **{score}**\n\n"

                if confirmed:
                    yield "## Confirmed Vulnerabilities\n\n"
                    yield "| # | Severity | Title | File | Line | CWE |\n"
                    yield "|---|---|---|---|---|---|\n"
                    for i, v in enumerate(confirmed, 1):
                        yield f"| {i} | {v.get('adjusted_severity', 'N/A')} | {v.get('title', 'Unknown')} | {v.get('file', '')} | {v.get('line', '')} | {v.get('cwe_id', '')} |\n"
                    yield "\n"

                if deep:
                    yield "## Deep Analysis Findings\n\n"
                    for i, d in enumerate(deep, 1):
                        yield f"{i}. **{d.get('title', 'Unknown')}** — Severity: {d.get('severity', 'N/A')}\n"
                        if d.get("description"):
                            yield f"   {d['description']}\n"
                    yield "\n"

                # CVEs
                cve_findings = last_state.get("cve_findings", [])
                if cve_findings:
                    yield f"## Known CVEs ({len(cve_findings)})\n\n"
                    for cve in cve_findings[:20]:
                        yield f"- **{cve.get('cve_id', 'N/A')}**: {cve.get('package', '')} — {cve.get('summary', '')}\n"
                    yield "\n"

                # Config risks
                config_risks = last_state.get("config_risks", [])
                if config_risks:
                    yield f"## Configuration Risks ({len(config_risks)})\n\n"
                    for cr in config_risks[:15]:
                        if isinstance(cr, dict):
                            yield f"- {cr.get('risk', str(cr))}\n"
                        else:
                            yield f"- {cr}\n"
                    yield "\n"

    return stream()

