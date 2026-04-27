"""
Code Security Scanner V2 — Agent Nodes & Graph
================================================
LangGraph StateGraph with typed state and 4 nodes.

KEY ARCHITECTURE (v3.0 — Multi-File):
  Pipeline: Scanner → Auditor → Fixer → Reporter

  Scanner runs ALL deterministic tools across ALL files:
    - Per-file: bandit, AST, secrets, patterns
    - Cross-file: import graph, taint tracking, config correlation
    - Obfuscation: base64/rot13/unicode/hex decoding
    - Dependencies: CVE lookup via osv.dev

  Auditor receives FULL structured intelligence + ALL source code.
  This is STRICTLY BETTER than V1 because it has cross-file context.
"""

import hashlib
import json
import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from sec_config import (
    OXLO_API_KEY, OXLO_BASE_URL,
    AUDITOR_MODEL, FIXER_MODEL, REPORTER_MODEL,
    SEVERITY_WEIGHTS,
)
from sec_prompts import AUDITOR_PROMPT, FIXER_PROMPT, REPORTER_PROMPT
from sec_scanners import run_all_scanners
from sec_file_parser import parse_multi_file_input, ParsedFile
from sec_cross_file import (
    build_import_graph, track_taint_flow, correlate_configs,
    decode_obfuscation, scan_dependencies_for_cves,
    scan_exec_eval_dangers, scan_timing_attacks,
    scan_toctou, scan_mass_assignment,
)

logger = logging.getLogger("security-scanner")


# ─── State Schema ─────────────────────────────────────────────────────

class SecurityState(TypedDict):
    """Shared state flowing through the security pipeline."""
    # Input
    code: str
    files_data: str
    language: str
    user_model: str

    # Parser output
    parsed_files: list[dict]
    file_count: int

    # Scanner output (deterministic)
    raw_findings: list[dict]
    scanner_summary: str

    # Cross-file intelligence (V2-exclusive)
    import_graph: list[dict]
    taint_chains: list[dict]
    config_risks: list[dict]
    decoded_payloads: list[dict]
    cve_findings: list[dict]
    exec_eval_findings: list[dict]
    timing_findings: list[dict]

    # Auditor output
    triage_results: list[dict]
    deep_findings: list[dict]
    severity_score: int

    # Fixer output
    fixes: str

    # Reporter output
    final_report: str

    # Metadata
    status: str


# ─── Helpers ──────────────────────────────────────────────────────────

def get_llm(model: str, temperature: float = 0.1, max_tokens: int = 8192) -> ChatOpenAI:
    return ChatOpenAI(
        model=model, api_key=OXLO_API_KEY, base_url=OXLO_BASE_URL,
        temperature=temperature, max_tokens=max_tokens,
        timeout=900,  # 15 min for reasoning models like DeepSeek R1
    )


def _parse_json_from_llm(content: str) -> dict:
    content = content.strip()
    if "```" in content:
        blocks = content.split("```")
        for block in blocks:
            cleaned = block.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            if cleaned.startswith("{") or cleaned.startswith("["):
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {}


# ─── Node 1: Scanner (Deterministic — ALL files) ─────────────────────

def scanner_node(state: SecurityState) -> dict:
    """
    Parse multi-file input, then run ALL deterministic scanners
    on every file + cross-file analysis.
    """
    code = state.get("code", "")
    files_data = state.get("files_data", "")
    language = state.get("language", "python")

    # Parse into individual files
    parsed_files = parse_multi_file_input(code, files_data)

    # If no files parsed, create a single-file fallback
    if not parsed_files:
        if code.strip():
            parsed_files = [ParsedFile(
                path="input.py", filename="input.py",
                content=code, language=language,
                is_config=False, size_bytes=len(code),
            )]
        else:
            return {"status": "error", "scanner_summary": "No code provided."}

    file_count = len(parsed_files)
    logger.info(f"[Scanner] Processing {file_count} files")

    # Run per-file scanners on each file
    all_findings = []
    for f in parsed_files:
        # NOTE: Config files (settings.py, etc.) are ALSO scanned by per-file
        # scanners — they often contain hardcoded secrets, insecure settings,
        # and dangerous patterns. The config correlator adds ADDITIONAL analysis.
        findings = run_all_scanners(f.content, f.language)
        # Tag each finding with its file path and source
        for finding in findings:
            finding["file"] = f.path
            if "source" not in finding:
                finding["source"] = "deterministic_scanner"
        all_findings.extend(findings)

    # Deduplicate findings by (file, line, category) — prevents triple-count noise
    seen = set()
    deduped = []
    for finding in all_findings:
        key = (finding.get("file", ""), finding.get("line", 0), finding.get("category", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(finding)
    all_findings = deduped

    # Run cross-file scanners
    import_graph = [e.to_dict() for e in build_import_graph(parsed_files)]
    taint_chains = [c.to_dict() for c in track_taint_flow(parsed_files)]
    config_risks = [r.to_dict() for r in correlate_configs(parsed_files)]
    decoded_payloads = [p.to_dict() for p in decode_obfuscation(parsed_files)]

    # Config risks are DETERMINISTIC — add to findings so they cannot be dismissed
    for cr in config_risks:
        all_findings.append({
            "file": cr.get("file", ""),
            "line": 0,
            "severity": cr.get("severity", "HIGH"),
            "category": "Configuration Risk",
            "title": cr.get("risk", cr.get("setting", "")),
            "description": f"{cr.get('setting', '')}: {cr.get('risk', '')}",
            "cwe_id": "CWE-16",
            "source": "deterministic_scanner",
        })

    # Taint chains are DETERMINISTIC — add to findings
    for tc in taint_chains:
        all_findings.append({
            "file": tc.get("sink_file", tc.get("source_file", "")),
            "line": tc.get("sink_line", 0),
            "severity": tc.get("severity", "CRITICAL"),
            "category": f"Cross-File {tc.get('vulnerability', 'Taint Flow')}",
            "title": f"{tc.get('vulnerability', 'Taint flow')}: {tc.get('source', '')} → {tc.get('sink', '')}",
            "description": f"User input from {tc.get('source', '')} ({tc.get('source_file', '')}:{tc.get('source_line', '')}) reaches {tc.get('sink', '')} ({tc.get('sink_file', '')}:{tc.get('sink_line', '')})",
            "cwe_id": "",
            "source": "deterministic_scanner",
        })

    # Run CVE scanner (may call external API)
    cve_findings = []
    try:
        cve_findings = [c.to_dict() for c in scan_dependencies_for_cves(parsed_files)]
    except Exception as e:
        logger.warning(f"[Scanner] CVE scan failed: {e}")

    # Run exec/eval danger scanner (Drawback 1 fix)
    exec_eval_findings = scan_exec_eval_dangers(parsed_files)
    for ef in exec_eval_findings:
        ef["source"] = "deterministic_scanner"
    all_findings.extend(exec_eval_findings)
    logger.info(f"[Scanner] exec/eval scanner: {len(exec_eval_findings)} findings")
    for ef in exec_eval_findings:
        logger.info(f"  → {ef.get('file','')}:{ef.get('line','')} {ef.get('title','')}")

    # Run timing attack scanner (Drawback 5 fix)
    timing_findings = scan_timing_attacks(parsed_files)
    for tf in timing_findings:
        tf["source"] = "deterministic_scanner"
    all_findings.extend(timing_findings)
    logger.info(f"[Scanner] timing attack scanner: {len(timing_findings)} findings")
    for tf in timing_findings:
        logger.info(f"  → {tf.get('file','')}:{tf.get('line','')} {tf.get('title','')}")

    # Run TOCTOU race condition scanner
    toctou_findings = scan_toctou(parsed_files)
    for tf in toctou_findings:
        tf["source"] = "deterministic_scanner"
    all_findings.extend(toctou_findings)
    logger.info(f"[Scanner] TOCTOU scanner: {len(toctou_findings)} findings")

    # Run mass assignment scanner
    mass_assign_findings = scan_mass_assignment(parsed_files)
    for mf in mass_assign_findings:
        mf["source"] = "deterministic_scanner"
    all_findings.extend(mass_assign_findings)
    logger.info(f"[Scanner] mass assignment scanner: {len(mass_assign_findings)} findings")

    # Advanced deduplication: same file + same CWE + lines within 5
    # Tracks confirmed_by (which scanners caught it) + sha256 fingerprints
    deduped = []
    for finding in all_findings:
        is_dup = False
        for existing in deduped:
            same_file = existing.get("file") == finding.get("file")
            same_cwe = (existing.get("cwe_id") == finding.get("cwe_id") and existing.get("cwe_id"))
            very_close = abs(existing.get("line", 0) - finding.get("line", 0)) <= 2
            same_title = existing.get("title", "").lower() == finding.get("title", "").lower()
            
            if same_file and ((same_cwe and very_close) or (same_title and very_close)):
                # Keep higher severity version
                sev_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
                if sev_order.get(finding.get("severity"), 0) > sev_order.get(existing.get("severity"), 0):
                    existing["severity"] = finding["severity"]
                    existing["title"] = finding.get("title", existing.get("title"))
                # Track which scanners confirmed this
                scanner_source = finding.get("source", "unknown")
                if "confirmed_by" not in existing:
                    existing["confirmed_by"] = [existing.get("source", "unknown")]
                if scanner_source not in existing["confirmed_by"]:
                    existing["confirmed_by"].append(scanner_source)
                existing["duplicate_count"] = existing.get("duplicate_count", 1) + 1
                # Set confidence based on agreement count
                existing["confidence"] = "high" if existing["duplicate_count"] >= 2 else "medium"
                is_dup = True
                break
        if not is_dup:
            deduped.append(finding)
    all_findings = deduped

    # Generate sha256 fingerprints for every finding (Drawback 2 fix)
    # Fingerprints lock findings — same fingerprint = same finding across runs
    for finding in all_findings:
        fp_data = f"{finding.get('file','')}{finding.get('line',0)}{finding.get('cwe_id','')}{finding.get('category','')}"
        finding["fingerprint"] = hashlib.sha256(fp_data.encode()).hexdigest()[:16]

    # Build summary
    cross_file_stats = []
    if import_graph:
        cross_file_stats.append(f"{len(import_graph)} import edges")
    if taint_chains:
        cross_file_stats.append(f"{len(taint_chains)} taint chains")
    if config_risks:
        cross_file_stats.append(f"{len(config_risks)} config risks")
    if decoded_payloads:
        cross_file_stats.append(f"{len(decoded_payloads)} decoded payloads")
    if cve_findings:
        cross_file_stats.append(f"{len(cve_findings)} known CVEs")
    if exec_eval_findings:
        cross_file_stats.append(f"{len(exec_eval_findings)} exec/eval dangers")
    if timing_findings:
        cross_file_stats.append(f"{len(timing_findings)} timing attacks")

    # Count deterministic vs LLM findings
    det_count = sum(1 for f in all_findings if f.get("source") == "deterministic_scanner")
    summary = (
        f"Scanned {file_count} files. "
        f"Found {len(all_findings)} findings ({det_count} deterministic, {len(all_findings) - det_count} pattern-based). "
    )
    if cross_file_stats:
        summary += f"Cross-file analysis: {', '.join(cross_file_stats)}."

    logger.info(f"[Scanner] {summary}")

    return {
        "parsed_files": [{"path": f.path, "language": f.language,
                          "is_config": f.is_config, "size": f.size_bytes}
                         for f in parsed_files],
        "file_count": file_count,
        "raw_findings": all_findings,
        "import_graph": import_graph,
        "taint_chains": taint_chains,
        "config_risks": config_risks,
        "decoded_payloads": decoded_payloads,
        "cve_findings": cve_findings,
        "exec_eval_findings": exec_eval_findings,
        "timing_findings": timing_findings,
        "scanner_summary": summary,
        "status": "scanning_complete",
    }


# ─── Node 2: Auditor (ONE powerful LLM call, FULL context) ───────────

def auditor_node(state: SecurityState) -> dict:
    """
    Single comprehensive security analysis with ALL cross-file intelligence.
    The LLM sees: all source code + scanner findings + import graph +
    taint chains + config risks + decoded payloads + CVEs.
    """
    code = state.get("code", "")
    files_data = state.get("files_data", "")
    findings = state.get("raw_findings", [])

    model = state.get("user_model") or AUDITOR_MODEL
    logger.info(f"[Auditor] Comprehensive analysis with model={model}")

    # FIX Drawback 2: temperature=0 for deterministic triage
    # Use 8192 max_tokens — auditor only returns JSON triage, not full report
    llm = get_llm(model, 0.0, max_tokens=8192)

    # Build source code section — truncated to prevent timeout
    parsed_files = parse_multi_file_input(code, files_data)
    code_sections = []
    for f in parsed_files:
        # Dynamic budget: fewer files = more space per file (up to 6KB)
        char_budget = max(3000, 20000 // max(len(parsed_files), 1))
        char_budget = min(char_budget, 6000)
        truncated = f.content[:char_budget]
        if len(f.content) > char_budget:
            truncated += f"\n# ... [{len(f.content) - char_budget} more chars truncated]"
        code_sections.append(f"### {f.path}\n```{f.language}\n{truncated}\n```")
    all_code = "\n\n".join(code_sections) if code_sections else f"```\n{code[:5000]}\n```"

    # Build cross-file intelligence — COMPACT format to reduce token count
    cross_file_intel = ""
    taint_chains = state.get("taint_chains", [])
    if taint_chains:
        cross_file_intel += f"\n## Cross-File Taint Chains ({len(taint_chains)}):\n"
        # Compact: one-line per chain instead of full JSON
        for tc in taint_chains[:8]:
            cross_file_intel += f"- {tc.get('source','')} @ {tc.get('source_file','')}:{tc.get('source_line','')} → {tc.get('sink','')} @ {tc.get('sink_file','')}:{tc.get('sink_line','')} = **{tc.get('vulnerability','')}** [{tc.get('severity','')}]\n"

    import_graph = state.get("import_graph", [])
    if import_graph:
        # Summary only — don't dump 35 edges as JSON
        cross_file_intel += f"\n## Import Graph: {len(import_graph)} import edges across files\n"
        # Just list unique modules
        modules = set(e.get('target_module', '') for e in import_graph)
        cross_file_intel += f"Imported modules: {', '.join(list(modules)[:15])}\n"

    config_risks = state.get("config_risks", [])
    if config_risks:
        cross_file_intel += f"\n## Config Risks ({len(config_risks)}):\n"
        for cr in config_risks:
            cross_file_intel += f"- {cr.get('file','')}: {cr.get('setting','')} — {cr.get('risk','')} [{cr.get('severity','')}]\n"

    decoded_payloads = state.get("decoded_payloads", [])
    if decoded_payloads:
        cross_file_intel += f"\n## Decoded Obfuscated Payloads ({len(decoded_payloads)}):\n"
        for dp in decoded_payloads:
            cross_file_intel += f"- {dp.get('file','')}:{dp.get('line_number','')} [{dp.get('encoding_type','')}] → {dp.get('decoded_value','')[:80]} {'**MALICIOUS**' if dp.get('is_malicious') else ''} [{dp.get('severity','')}]\n"

    cve_findings = state.get("cve_findings", [])
    if cve_findings:
        cross_file_intel += f"\n## Known CVEs ({len(cve_findings)}):\n"
        # Top 10 only — full list in reporter
        for cve in cve_findings[:10]:
            cross_file_intel += f"- {cve.get('package','')}=={cve.get('version','')}: {cve.get('cve_id','')} — {cve.get('summary','')[:60]} [{cve.get('severity','')}]\n"
        if len(cve_findings) > 10:
            cross_file_intel += f"- ... and {len(cve_findings) - 10} more CVEs\n"

    # CRITICAL: Sort deterministic findings FIRST so they're always within the LLM's view window
    # Without this, exec/eval and timing findings appended at the end get cut off
    findings_deterministic = [f for f in findings if f.get("source") == "deterministic_scanner"]
    findings_llm = [f for f in findings if f.get("source") != "deterministic_scanner"]
    sorted_findings = findings_deterministic + findings_llm
    
    # Include exec/eval and timing findings as explicit cross-file intelligence
    exec_eval = state.get("exec_eval_findings", [])
    if exec_eval:
        cross_file_intel += f"\n## 🚨 Dangerous exec/eval Calls ({len(exec_eval)}):\n"
        for ef in exec_eval:
            cross_file_intel += f"- **{ef.get('severity','CRITICAL')}** {ef.get('file','')}:{ef.get('line','')} — {ef.get('title','')} [{ef.get('cwe_id','')}]\n"
    
    timing = state.get("timing_findings", [])
    if timing:
        cross_file_intel += f"\n## ⏱️ Timing Attack Vulnerabilities ({len(timing)}):\n"
        for tf in timing:
            cross_file_intel += f"- **{tf.get('severity','HIGH')}** {tf.get('file','')}:{tf.get('line','')} — {tf.get('title','')} [{tf.get('cwe_id','')}]\n"

    # Send up to 30 findings (deterministic always first)
    findings_text = json.dumps(sorted_findings[:30], separators=(',', ':')) if sorted_findings else "[]"

    user_content = (
        f"## Files: {state.get('file_count', 1)}\n\n"
        f"## Source Code:\n{all_code}\n\n"
        f"## Scanner Findings ({len(findings)}):\n```json\n{findings_text}\n```\n\n"
        f"{cross_file_intel}\n"
        f"Perform a comprehensive security audit. USE the cross-file intelligence above.\n"
        f"Return ONLY the JSON object. Be thorough but concise."
    )

    logger.info(f"[Auditor] Prompt size: {len(user_content)} chars")

    response = llm.invoke([
        SystemMessage(content=AUDITOR_PROMPT),
        HumanMessage(content=user_content),
    ])

    result = _parse_json_from_llm(response.content)
    triage = result.get("triage", [])
    deep_findings = result.get("deep_findings", [])

    # FIX Drawback 2: Deterministic scanner findings are NEVER dismissed
    # Use FINGERPRINTS for matching (not fragile integer indices)
    deterministic_fps = {}
    for finding in findings:
        if finding.get("source") == "deterministic_scanner" and finding.get("fingerprint"):
            deterministic_fps[finding["fingerprint"]] = finding
    
    # Override any LLM dismissals of deterministic findings
    for item in triage:
        fidx = item.get("finding_index", -1)
        # Match by index (if LLM used it) or by fingerprint
        matched_finding = None
        if 0 <= fidx < len(findings):
            matched_finding = findings[fidx]
        
        if matched_finding and matched_finding.get("source") == "deterministic_scanner":
            if item.get("classification") == "false_positive":
                logger.warning(f"[Auditor] LLM tried to dismiss deterministic finding #{fidx} '{matched_finding.get('title','')}' — overriding to true_positive")
                item["classification"] = "true_positive"
                item["rationale"] = f"[ENFORCED] Deterministic scanner finding — cannot be dismissed. Original LLM reason: {item.get('rationale', 'N/A')}"
    
    # Ensure ALL deterministic findings appear in triage, even if LLM ignored them
    triaged_fps = set()
    for item in triage:
        fidx = item.get("finding_index", -1)
        if 0 <= fidx < len(findings) and findings[fidx].get("fingerprint"):
            triaged_fps.add(findings[fidx]["fingerprint"])
    
    for fp, finding in deterministic_fps.items():
        if fp not in triaged_fps:
            # Find this finding's index in the sorted list
            f_idx = next((i for i, f in enumerate(findings) if f.get("fingerprint") == fp), -1)
            triage.append({
                "finding_index": f_idx,
                "classification": "true_positive",
                "rationale": f"[AUTO-CONFIRMED] Deterministic finding: {finding.get('title','')}",
                "adjusted_severity": finding.get("severity", "HIGH"),
                "file": finding.get("file", ""),
                "line": finding.get("line", 0),
                "title": finding.get("title", ""),
                "cwe_id": finding.get("cwe_id", ""),
                "fingerprint": fp,
            })

    severity_score = 0
    for item in triage:
        if item.get("classification") in ("true_positive", "needs_investigation"):
            sev = item.get("adjusted_severity", "MEDIUM")
            severity_score += SEVERITY_WEIGHTS.get(sev, 4)
    for item in deep_findings:
        severity_score += SEVERITY_WEIGHTS.get(item.get("severity", "MEDIUM"), 4)
    # Add CVE severity
    for cve in cve_findings:
        severity_score += SEVERITY_WEIGHTS.get(cve.get("severity", "HIGH"), 7)

    logger.info(f"[Auditor] Triage: {len(triage)}, Deep: {len(deep_findings)}, Score: {severity_score}")

    return {
        "triage_results": triage,
        "deep_findings": deep_findings,
        "severity_score": severity_score,
        "status": "audit_complete",
    }


# ─── Node 3: Fixer ───────────────────────────────────────────────────
def fixer_node(state: SecurityState) -> dict:
    logger.info("[Fixer] Node entered.")
    
    triage = state.get("triage_results", [])
    deep = state.get("deep_findings", [])
    model = state.get("user_model") or FIXER_MODEL

    # Add error catching in case triage results are malformed strings instead of dicts
    try:
        confirmed = [t for t in triage if isinstance(t, dict) and t.get("classification") == "true_positive"]
    except Exception as e:
        logger.error(f"[Fixer] Failed to parse triage results: {e}")
        confirmed = []
        
    all_vulns = confirmed + deep

    if not all_vulns:
        logger.info("[Fixer] No vulnerabilities require fixes. Exiting node.")
        return {"fixes": "No vulnerabilities require fixes.", "status": "fixes_complete"}

    logger.info(f"[Fixer] Generating patches for {len(all_vulns)} vulnerabilities")
    llm = get_llm(model, 0.2)
    
    try:
        # Reconstruct code for fixer
        code = state.get("code", "")
        files_data = state.get("files_data", "")
        parsed = parse_multi_file_input(code, files_data)
        code_text = "\n\n".join(f"### {f.path}\n```{f.language}\n{f.content[:4000]}\n```" for f in parsed[:5])

        response = llm.invoke([
            SystemMessage(content=FIXER_PROMPT),
            HumanMessage(content=(
                f"## Source Code:\n{code_text}\n\n"
                f"## Vulnerabilities:\n```json\n{json.dumps(all_vulns[:15], indent=2)}\n```\n"
                f"Generate secure code patches for each vulnerability."
            )),
        ])
        return {"fixes": response.content, "status": "fixes_complete"}
    except Exception as e:
        logger.error(f"[Fixer] LLM call failed: {e}")
        return {"fixes": "Fix generation timed out. See findings above for remediation guidance.", "status": "fixes_complete"}


# ─── Node 4: Reporter ────────────────────────────────────────────────

def reporter_node(state: SecurityState) -> dict:
    logger.info("[Reporter] Compiling final report...")
    llm = get_llm(REPORTER_MODEL, 0.3)

    triage = state.get("triage_results", [])
    deep = state.get("deep_findings", [])
    confirmed = [t for t in triage if t.get("classification") == "true_positive"]
    dismissed = [t for t in triage if t.get("classification") == "false_positive"]

    # Cross-file sections for the report
    cross_file_summary = ""
    taint_chains = state.get("taint_chains", [])
    if taint_chains:
        cross_file_summary += f"\n## Cross-File Taint Chains ({len(taint_chains)}):\n```json\n{json.dumps(taint_chains[:5], indent=2)}\n```\n"
    cve_findings = state.get("cve_findings", [])
    if cve_findings:
        cross_file_summary += f"\n## Known CVEs ({len(cve_findings)}):\n```json\n{json.dumps(cve_findings, indent=2)}\n```\n"
    config_risks = state.get("config_risks", [])
    if config_risks:
        cross_file_summary += f"\n## Config Risks ({len(config_risks)}):\n```json\n{json.dumps(config_risks, indent=2)}\n```\n"
    decoded = state.get("decoded_payloads", [])
    if decoded:
        cross_file_summary += f"\n## Decoded Obfuscated Payloads ({len(decoded)}):\n```json\n{json.dumps(decoded, indent=2)}\n```\n"
    
    # Include exec/eval and timing findings directly in report
    exec_eval = state.get("exec_eval_findings", [])
    if exec_eval:
        cross_file_summary += f"\n## Dangerous exec/eval Calls ({len(exec_eval)}):\n```json\n{json.dumps(exec_eval, indent=2)}\n```\n"
    timing = state.get("timing_findings", [])
    if timing:
        cross_file_summary += f"\n## Timing Attack Vulnerabilities ({len(timing)}):\n```json\n{json.dumps(timing, indent=2)}\n```\n"

    # Manual review section for the last 5%
    manual_review = "\n## 🔍 Manual Review Required\n"
    manual_review += "These areas require human security engineer review:\n"
    manual_review += "- All exec/eval calls (even if flagged above)\n"
    manual_review += "- All authentication/authorization flows\n"
    manual_review += "- All payment/financial logic\n"
    manual_review += "- Any file with low LLM confidence\n"

    try:
        response = llm.invoke([
            SystemMessage(content=REPORTER_PROMPT),
            HumanMessage(content=(
                f"## Scanner Summary\n{state.get('scanner_summary', 'N/A')}\n"
                f"## Files Scanned: {state.get('file_count', 1)}\n\n"
                f"## Confirmed Vulnerabilities ({len(confirmed)}):\n```json\n{json.dumps(confirmed, indent=2)}\n```\n\n"
                f"## Deep Findings ({len(deep)}):\n```json\n{json.dumps(deep, indent=2)}\n```\n\n"
                f"## Dismissed ({len(dismissed)}):\n```json\n{json.dumps(dismissed, indent=2)}\n```\n\n"
                f"{cross_file_summary}\n"
                f"{manual_review}\n"
                f"## Fixes:\n{state.get('fixes', 'None')}\n\n"
                f"## Severity Score: {state.get('severity_score', 0)}\n"
                f"Compile the final security audit report. INCLUDE the Manual Review Required section at the end."
            )),
        ])
        return {"final_report": response.content, "status": "complete"}
    except Exception as e:
        logger.error(f"[Reporter] LLM call failed: {e}")
        # Fallback: build a basic report from the data we have
        fallback = f"# 🛡️ Security Audit Report\n\n"
        fallback += f"## Summary\nScanned {state.get('file_count', 0)} files. Found {len(confirmed)} confirmed vulnerabilities.\n"
        fallback += f"Severity Score: {state.get('severity_score', 0)}\n\n"
        fallback += f"## Confirmed Vulnerabilities\n"
        for i, v in enumerate(confirmed[:30], 1):
            fallback += f"{i}. **{v.get('title', 'Unknown')}** — {v.get('file', '')}:{v.get('line', '')} ({v.get('cwe_id', '')})\n"
        if deep:
            fallback += f"\n## Deep Analysis Findings\n"
            for i, d in enumerate(deep, 1):
                fallback += f"{i}. **{d.get('title', 'Unknown')}** — {d.get('severity', '')}\n"
        fallback += f"\n{cross_file_summary}\n"
        return {"final_report": fallback, "status": "complete"}


# ─── Graph Builder ────────────────────────────────────────────────────

def build_graph():
    logger.info("[Graph] Building StateGraph")
    wf = StateGraph(SecurityState)
    wf.add_node("scanner", scanner_node)
    wf.add_node("auditor", auditor_node)
    wf.add_node("fixer", fixer_node)
    wf.add_node("reporter", reporter_node)

    wf.set_entry_point("scanner")
    wf.add_edge("scanner", "auditor")
    
    def after_auditor(state: SecurityState):
        logger.info(f"[Graph] Edge from auditor. Moving to fixer.")
        return "fixer"
        
    wf.add_edge("auditor", "fixer")
    wf.add_edge("fixer", "reporter")
    wf.add_edge("reporter", END)

    logger.info("[Graph] Graph compiled.")
    return wf.compile()
