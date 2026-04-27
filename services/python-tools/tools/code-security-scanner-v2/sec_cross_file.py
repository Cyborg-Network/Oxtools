"""
Code Security Scanner V2 — Cross-File Analysis
================================================
This module contains the scanners that make V2 STRICTLY BETTER than V1:
- Import graph building (cross-file dependency mapping)
- Cross-file taint tracking (user input → sanitize → execute)
- Config correlator (settings.py + views.py = combined risk)
- Obfuscation decoder (base64, rot13, unicode, hex)
- Dependency CVE scanner (osv.dev API lookup)

These capabilities are IMPOSSIBLE in a single-prompt V1 tool.
"""

import ast
import base64
import codecs
import json
import logging
import re
from dataclasses import dataclass, asdict
from typing import Optional

from sec_config import OSV_API_URL
from sec_file_parser import ParsedFile

logger = logging.getLogger("security-scanner")


# ─── Data Structures ──────────────────────────────────────────────────

@dataclass
class ImportEdge:
    """A single import relationship between two files."""
    source_file: str       # File that imports
    target_module: str     # Module being imported
    imported_names: list[str]  # Specific names imported (or ["*"])
    line_number: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaintChain:
    """A traced path of tainted data across files."""
    source: str            # Where user input enters (e.g. "request.GET")
    source_file: str
    source_line: int
    steps: list[dict]      # [{file, line, description}, ...]
    sink: str              # Where it ends up (e.g. "cursor.execute()")
    sink_file: str
    sink_line: int
    vulnerability: str     # What this enables (e.g. "SQL Injection")
    severity: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DecodedPayload:
    """A decoded obfuscated payload."""
    file: str
    line_number: int
    encoding_type: str     # "base64", "rot13", "unicode_escape", "hex"
    original_code: str
    decoded_value: str
    is_malicious: bool
    severity: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConfigRisk:
    """A risky configuration setting."""
    file: str
    setting: str
    value: str
    risk: str
    severity: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass 
class CVEFinding:
    """A known CVE in a dependency."""
    package: str
    version: str
    cve_id: str
    summary: str
    severity: str
    file: str              # requirements.txt / package.json

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Scanner: Import Graph Builder ───────────────────────────────────

def build_import_graph(files: list[ParsedFile]) -> list[ImportEdge]:
    """
    Build a cross-file import dependency graph using Python AST.
    Maps which files import from which modules.
    """
    edges = []
    
    for f in files:
        if f.language != "python":
            continue
        try:
            tree = ast.parse(f.content)
        except SyntaxError:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append(ImportEdge(
                        source_file=f.path,
                        target_module=alias.name,
                        imported_names=[alias.asname or alias.name],
                        line_number=node.lineno,
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                edges.append(ImportEdge(
                    source_file=f.path,
                    target_module=module,
                    imported_names=names,
                    line_number=node.lineno,
                ))
    
    logger.info(f"[ImportGraph] Built {len(edges)} import edges across {len(files)} files")
    return edges


# ─── Scanner: Cross-File Taint Tracker ────────────────────────────────

# User input sources (Python-focused)
TAINT_SOURCES = {
    "request.GET", "request.POST", "request.args", "request.form",
    "request.data", "request.json", "request.body", "request.params",
    "request.query_params", "request.FILES", "request.headers",
    "request.META",
    "sys.argv", "input(", "os.environ",
}

# Celery/async task decorators — function params are untrusted input
TASK_DECORATORS = {
    "app.task", "shared_task", "celery.task",
    "dramatiq.actor", "huey.task", "rq.job",
}

# Dangerous sinks
TAINT_SINKS = {
    "cursor.execute": "SQL Injection",
    "os.system": "Command Injection",
    "os.popen": "Command Injection",
    "subprocess.call": "Command Injection",
    "subprocess.run": "Command Injection",
    "subprocess.Popen": "Command Injection",
    "eval(": "Code Injection",
    "exec(": "Code Injection",
    "render_template_string": "SSTI (RCE)",
    "pickle.loads": "Deserialization RCE",
    "yaml.load": "YAML Deserialization",
    "innerHTML": "XSS",
    "document.write": "XSS",
    # SSRF sinks
    "urllib.request.urlopen": "SSRF",
    "urlopen(": "SSRF",
    "requests.get(": "SSRF",
    "requests.post(": "SSRF",
    "httpx.get(": "SSRF",
    "httpx.post(": "SSRF",
    "http.client.HTTPConnection": "SSRF",
    "aiohttp.ClientSession": "SSRF",
    # Path traversal sinks
    "open(": "Path Traversal",
}

# Functions that look like sanitizers but aren't
FAKE_SANITIZERS = {
    "strip", "lower", "upper", "title", "replace",
    "split", "join", "format", "encode", "decode",
    "startswith", "endswith", "len", "str", "int", "float",
}

# REAL sanitizers — context-specific taint clearing
# Key = function/method name, Value = set of contexts it actually clears
REAL_SANITIZERS = {
    # SQL sanitizers
    "parameterize": {"sql"},
    "execute": set(),  # execute itself is a sink, not sanitizer
    
    # HTML/XSS sanitizers
    "escape": {"html"},
    "html_escape": {"html"},
    "markupsafe": {"html"},
    "bleach_clean": {"html"},
    "clean": {"html"},  # bleach.clean()
    
    # Shell sanitizers
    "quote": {"shell"},  # shlex.quote()
    "shlex_quote": {"shell"},
    
    # Path sanitizers (only if combined with startswith check)
    "abspath": set(),  # needs startswith check too
    "realpath": set(),  # needs startswith check too
    
    # LDAP sanitizers
    "escape_filter_chars": {"ldap"},
}

# Map vulnerability types to their taint contexts
VULN_CONTEXT_MAP = {
    "SQL Injection": "sql",
    "Command Injection": "shell",
    "Code Injection": "code",
    "SSTI (RCE)": "html",
    "XSS": "html",
    "SSRF": "url",
    "Deserialization RCE": "code",
    "YAML Deserialization": "code",
    "Path Traversal": "path",
}

# Security-sensitive variable name fragments for timing attack detection
TIMING_SENSITIVE_NAMES = {
    "password", "passwd", "pwd", "token", "secret", "key", "hash",
    "signature", "sig", "hmac", "auth", "credential", "nonce",
    "api_key", "apikey", "access_token",
}


def track_taint_flow(files: list[ParsedFile]) -> list[TaintChain]:
    """
    Trace user input across files to find cross-file vulnerabilities.
    
    This is the CORE capability that makes V2 superior to V1.
    V1 can never see two files at the same time.
    
    FIX: Now also treats Celery/async task parameters as taint sources.
    """
    chains = []
    
    # First pass: find all taint sources and sinks across all files
    sources = []   # [(file, line, variable, source_type)]
    sinks = []     # [(file, line, code, sink_type, vuln_type)]
    functions = {} # {func_name: (file, line, is_named_sanitizer, is_real)}
    
    for f in files:
        if f.language != "python" or f.is_config:
            continue
        
        lines = f.content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Find taint sources (request objects)
            for source in TAINT_SOURCES:
                if source in stripped:
                    var_match = re.match(r'(\w+)\s*=\s*.*' + re.escape(source), stripped)
                    var_name = var_match.group(1) if var_match else None
                    sources.append((f.path, i, var_name, source))
            
            # Find taint sinks
            for sink, vuln in TAINT_SINKS.items():
                if sink in stripped:
                    sinks.append((f.path, i, stripped[:120], sink, vuln))
        
        # AST pass: find task decorators, sanitizers, class methods
        try:
            tree = ast.parse(f.content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check if function is a Celery/async task
                    for dec in node.decorator_list:
                        dec_name = ""
                        if isinstance(dec, ast.Attribute):
                            dec_name = f"{ast.dump(dec.value)}.{dec.attr}" if hasattr(dec, 'attr') else ""
                        elif isinstance(dec, ast.Name):
                            dec_name = dec.id
                        elif isinstance(dec, ast.Call):
                            if isinstance(dec.func, ast.Attribute):
                                dec_name = dec.func.attr
                            elif isinstance(dec.func, ast.Name):
                                dec_name = dec.func.id
                        
                        # If this is a task decorator, treat ALL params as taint sources
                        if any(td in dec_name.lower() for td in ("task", "shared_task", "actor", "job")):
                            for arg in node.args.args:
                                if arg.arg != "self":
                                    sources.append((f.path, node.lineno, arg.arg, f"@task parameter '{arg.arg}'"))
                    
                    # Check if function name suggests sanitization
                    sanitizer_names = {"sanitize", "clean", "escape", "validate", "filter", "safe"}
                    is_named_sanitizer = any(s in node.name.lower() for s in sanitizer_names)
                    
                    is_real = False
                    clears_contexts = set()  # Which taint contexts this function clears
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            func_name_inner = ""
                            if isinstance(child.func, ast.Attribute):
                                func_name_inner = child.func.attr
                            elif isinstance(child.func, ast.Name):
                                func_name_inner = child.func.id
                            
                            # Check if this call is a real sanitizer
                            if func_name_inner in REAL_SANITIZERS:
                                contexts = REAL_SANITIZERS[func_name_inner]
                                if contexts:  # Non-empty = actually clears something
                                    is_real = True
                                    clears_contexts.update(contexts)
                            elif func_name_inner not in FAKE_SANITIZERS and func_name_inner:
                                # Unknown function — could be real, mark as partial
                                pass
                    
                    # Check for parameterized queries (SQL sanitization)
                    func_src = ast.get_source_segment(f.content, node) or ""
                    if any(p in func_src for p in ["%s", "$1", "?", ":param"]):
                        is_real = True
                        clears_contexts.add("sql")
                    
                    functions[node.name] = (f.path, node.lineno, is_named_sanitizer, is_real, clears_contexts)
        except SyntaxError:
            pass
    
    # Second pass: connect sources to sinks
    for src_file, src_line, src_var, src_type in sources:
        for sink_file, sink_line, sink_code, sink_type, vuln_type in sinks:
            if src_var and src_var in sink_code:
                steps = []
                taint_blocked = False
                
                # Determine what context this sink needs
                sink_context = VULN_CONTEXT_MAP.get(vuln_type, "")
                
                for func_name, (func_file, func_line, is_named, is_real, clears) in functions.items():
                    if is_named and not is_real:
                        steps.append({
                            "file": func_file, "line": func_line,
                            "description": f"⚠️ Function '{func_name}' is named like a sanitizer but provides NO real protection (only uses {', '.join(FAKE_SANITIZERS & set(['strip','lower','upper']))})"
                        })
                    elif is_named and is_real:
                        # Check if it clears the RIGHT context
                        if sink_context and sink_context in clears:
                            taint_blocked = True  # Genuinely sanitized for this context
                        elif sink_context and sink_context not in clears:
                            steps.append({
                                "file": func_file, "line": func_line,
                                "description": f"⚠️ Function '{func_name}' sanitizes for {clears} but NOT for {sink_context} — taint still active for {vuln_type}"
                            })
                
                if taint_blocked:
                    continue  # Genuinely sanitized — skip this chain
                
                chains.append(TaintChain(
                    source=src_type, source_file=src_file, source_line=src_line,
                    steps=steps, sink=sink_type, sink_file=sink_file, sink_line=sink_line,
                    vulnerability=vuln_type,
                    severity="CRITICAL" if vuln_type in ("SQL Injection", "Command Injection", "Code Injection", "SSTI (RCE)", "SSRF") else "HIGH",
                ))
    
    logger.info(f"[TaintTracker] Found {len(chains)} taint chains across {len(files)} files")
    return chains


# ─── Scanner: exec/eval on Non-Literal Variables (Drawback 1 fix) ─────

def scan_exec_eval_dangers(files: list[ParsedFile]) -> list[dict]:
    """
    Flag exec()/eval() on ANY non-literal variable.
    Rule: if exec(x) exists and x is not a string literal, it's CRITICAL.
    Also detects: b64decode + exec in same function, __import__, compile+exec.
    try/except does NOT reduce severity — it INCREASES it.
    """
    findings = []
    
    for f in files:
        if f.language != "python" or f.is_config:
            continue
        
        try:
            tree = ast.parse(f.content)
        except SyntaxError:
            continue
        
        for node in ast.walk(tree):
            # Check functions/methods for exec/eval patterns
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_b64decode = False
                has_compile = False
                has_exec_eval = False
                exec_line = 0
                in_try = False
                
                for child in ast.walk(node):
                    # Track b64decode, compile calls
                    if isinstance(child, ast.Call):
                        call_name = _get_call_name(child)
                        if "b64decode" in call_name or "base64" in call_name:
                            has_b64decode = True
                        if call_name == "compile":
                            has_compile = True
                    
                    # Track try/except blocks
                    if isinstance(child, ast.Try):
                        in_try = True
                
                # Find exec/eval calls specifically
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        call_name = _get_call_name(child)
                        if call_name in ("exec", "eval"):
                            has_exec_eval = True
                            exec_line = getattr(child, 'lineno', node.lineno)
                            
                            # Check if argument is a non-literal
                            is_literal = False
                            if child.args:
                                arg = child.args[0]
                                if isinstance(arg, (ast.Constant, ast.Str)):
                                    is_literal = True
                            
                            if not is_literal:
                                desc = f"exec/eval on non-literal variable in {node.name}()"
                                if in_try:
                                    desc += " — HIDDEN inside try/except (errors silently swallowed)"
                                if has_b64decode:
                                    desc += " — combined with base64 decoding (OBFUSCATED BACKDOOR)"
                                
                                findings.append({
                                    "file": f.path,
                                    "line": exec_line,
                                    "severity": "CRITICAL",
                                    "category": "Code Injection / Backdoor",
                                    "title": f"{call_name}() on externally-controlled input",
                                    "description": desc,
                                    "cwe_id": "CWE-95",
                                    "source": "deterministic_scanner",
                                })
                
                # b64decode + exec/eval in same function = CRITICAL
                if has_b64decode and has_exec_eval and not any(
                    fd.get("description", "").endswith("(OBFUSCATED BACKDOOR)")
                    for fd in findings if fd.get("file") == f.path
                ):
                    findings.append({
                        "file": f.path,
                        "line": exec_line or node.lineno,
                        "severity": "CRITICAL",
                        "category": "Obfuscated Backdoor",
                        "title": f"base64 decode + exec/eval in {node.name}()",
                        "description": f"Function {node.name}() combines base64 decoding with code execution — obfuscated backdoor pattern",
                        "cwe_id": "CWE-506",
                        "source": "deterministic_scanner",
                    })
                
                # compile + exec in same function = CRITICAL
                if has_compile and has_exec_eval:
                    findings.append({
                        "file": f.path,
                        "line": exec_line or node.lineno,
                        "severity": "CRITICAL",
                        "category": "Dynamic Code Execution",
                        "title": f"compile() + exec() in {node.name}()",
                        "description": "compile() + exec() pattern enables arbitrary code execution",
                        "cwe_id": "CWE-95",
                        "source": "deterministic_scanner",
                    })
            
            # __import__ anywhere = CRITICAL
            if isinstance(node, ast.Call):
                call_name = _get_call_name(node)
                if call_name == "__import__":
                    findings.append({
                        "file": f.path,
                        "line": getattr(node, 'lineno', 0),
                        "severity": "CRITICAL",
                        "category": "Dynamic Import",
                        "title": "__import__() call detected",
                        "description": "__import__() enables dynamic module loading — often used in backdoors",
                        "cwe_id": "CWE-95",
                        "source": "deterministic_scanner",
                    })
        
        # Second pass: catch ALL exec/eval anywhere (including top-level and 
        # class methods that the function-level scan might have missed)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = _get_call_name(node)
                if call_name in ("exec", "eval"):
                    exec_line = getattr(node, 'lineno', 0)
                    # Skip if already found at this line
                    if any(fd.get("file") == f.path and fd.get("line") == exec_line for fd in findings):
                        continue
                    
                    is_literal = False
                    if node.args:
                        arg = node.args[0]
                        if isinstance(arg, (ast.Constant, ast.Str)):
                            is_literal = True
                    
                    if not is_literal:
                        findings.append({
                            "file": f.path,
                            "line": exec_line,
                            "severity": "CRITICAL",
                            "category": "Code Injection / Backdoor",
                            "title": f"{call_name}() on non-literal input (module level)",
                            "description": f"{call_name}() called with dynamic variable — potential code injection",
                            "cwe_id": "CWE-95",
                            "source": "deterministic_scanner",
                        })
    
    logger.info(f"[ExecScanner] Found {len(findings)} exec/eval dangers")
    return findings


def _get_call_name(node: ast.Call) -> str:
    """Extract function name from an AST Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


# ─── Scanner: Timing Attack Detection (Drawback 5 fix) ───────────────

def scan_timing_attacks(files: list[ParsedFile]) -> list[dict]:
    """
    Detect == or != comparisons on security-sensitive variables.
    Works in class methods, top-level functions, anywhere.
    """
    findings = []
    
    for f in files:
        if f.language != "python" or f.is_config:
            continue
        
        try:
            tree = ast.parse(f.content)
        except SyntaxError:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                # Check if using == or !=
                has_eq = any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops)
                if not has_eq:
                    continue
                
                # Get all variable names in the comparison
                names = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Name):
                        names.add(child.id.lower())
                    elif isinstance(child, ast.Attribute):
                        names.add(child.attr.lower())
                
                # Check if any name is security-sensitive
                for name in names:
                    if any(sensitive in name for sensitive in TIMING_SENSITIVE_NAMES):
                        findings.append({
                            "file": f.path,
                            "line": getattr(node, 'lineno', 0),
                            "severity": "HIGH",
                            "category": "Timing Attack",
                            "title": f"Timing-unsafe comparison on '{name}'",
                            "description": f"Direct == comparison on security-sensitive value '{name}'. Use hmac.compare_digest() instead.",
                            "cwe_id": "CWE-208",
                            "source": "deterministic_scanner",
                        })
                        break  # One finding per comparison
    
    logger.info(f"[TimingScanner] Found {len(findings)} timing attack risks")
    return findings


# ─── Scanner: TOCTOU Race Condition Detection ─────────────────────────

def scan_toctou(files: list[ParsedFile]) -> list[dict]:
    """
    Detect Time-of-Check/Time-of-Use race conditions.
    Pattern: os.path.exists(x) followed by open(x) in the same function.
    Also catches: os.access() + open(), os.stat() + open().
    """
    findings = []
    CHECK_FUNCS = {"exists", "isfile", "isdir", "access", "stat"}
    USE_FUNCS = {"open", "read", "write"}
    
    for f in files:
        if f.language != "python" or f.is_config:
            continue
        try:
            tree = ast.parse(f.content)
        except SyntaxError:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                check_lines = []
                use_lines = []
                has_sleep = False
                
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        call_name = _get_call_name(child)
                        # os.path.exists(), os.access(), etc.
                        if call_name in CHECK_FUNCS:
                            check_lines.append(getattr(child, 'lineno', 0))
                        # time.sleep() between check and use
                        if call_name == "sleep":
                            has_sleep = True
                    
                    # open() call or with open() statement
                    if isinstance(child, ast.Call):
                        call_name = _get_call_name(child)
                        if call_name in USE_FUNCS:
                            use_lines.append(getattr(child, 'lineno', 0))
                    if isinstance(child, ast.withitem) and isinstance(child.context_expr, ast.Call):
                        call_name = _get_call_name(child.context_expr)
                        if call_name in USE_FUNCS:
                            use_lines.append(getattr(child.context_expr, 'lineno', 0))
                
                # If we found both check and use in the same function
                if check_lines and use_lines:
                    for cl in check_lines:
                        for ul in use_lines:
                            if ul > cl:  # Use happens after check
                                desc = f"TOCTOU in {node.name}(): file checked at line {cl}, used at line {ul}"
                                if has_sleep:
                                    desc += " — time.sleep() between check and use INCREASES exploitation window"
                                findings.append({
                                    "file": f.path,
                                    "line": cl,
                                    "severity": "HIGH",
                                    "category": "Race Condition",
                                    "title": f"TOCTOU race condition in {node.name}()",
                                    "description": desc,
                                    "cwe_id": "CWE-367",
                                    "source": "deterministic_scanner",
                                })
                                break  # One finding per function
                        else:
                            continue
                        break
    
    logger.info(f"[TOCTOUScanner] Found {len(findings)} TOCTOU risks")
    return findings


# ─── Scanner: Mass Assignment Detection ───────────────────────────────

def scan_mass_assignment(files: list[ParsedFile]) -> list[dict]:
    """
    Detect mass assignment via setattr() in loops, __dict__.update(), etc.
    Pattern: for key, value in data.items(): setattr(obj, key, value)
    """
    findings = []
    
    for f in files:
        if f.language != "python" or f.is_config:
            continue
        try:
            tree = ast.parse(f.content)
        except SyntaxError:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Look for for loops containing setattr
                for child in ast.walk(node):
                    if isinstance(child, ast.For):
                        # Check if loop body contains setattr()
                        for body_node in ast.walk(child):
                            if isinstance(body_node, ast.Call):
                                call_name = _get_call_name(body_node)
                                if call_name == "setattr":
                                    findings.append({
                                        "file": f.path,
                                        "line": getattr(child, 'lineno', node.lineno),
                                        "severity": "CRITICAL",
                                        "category": "Mass Assignment",
                                        "title": f"Mass assignment via setattr() loop in {node.name}()",
                                        "description": f"setattr() called in a for loop in {node.name}() — attacker can set arbitrary attributes (e.g. is_admin=True). Use an explicit whitelist of allowed fields.",
                                        "cwe_id": "CWE-915",
                                        "source": "deterministic_scanner",
                                    })
                                    break  # One finding per loop
    
    logger.info(f"[MassAssignmentScanner] Found {len(findings)} mass assignment risks")
    return findings


# ─── Scanner: Config Correlator ───────────────────────────────────────

DANGEROUS_CONFIGS = {
    # Python/Django
    "DEBUG = True": ("Debug mode enabled in production", "HIGH"),
    "DEBUG=True": ("Debug mode enabled in production", "HIGH"),
    'ALLOWED_HOSTS = ["*"]': ("All hosts allowed — enables host header attacks", "HIGH"),
    "ALLOWED_HOSTS = ['*']": ("All hosts allowed — enables host header attacks", "HIGH"),
    "CORS_ALLOW_ALL_ORIGINS = True": ("CORS allows all origins — enables CSRF", "HIGH"),
    "CORS_ORIGIN_ALLOW_ALL = True": ("CORS allows all origins — enables CSRF", "HIGH"),
    "SESSION_COOKIE_HTTPONLY = False": ("Session cookies accessible via JavaScript — enables session theft", "HIGH"),
    "SESSION_COOKIE_SECURE = False": ("Session cookies sent over HTTP — enables interception", "HIGH"),
    "CSRF_COOKIE_HTTPONLY = False": ("CSRF cookie accessible via JavaScript", "MEDIUM"),
    
    # Generic
    "SECRET_KEY": None,  # Special handling below
}

# Regex patterns for configs that need fuzzy matching
CONFIG_REGEX_PATTERNS = [
    (re.compile(r'#.*CsrfViewMiddleware', re.I),
     "CSRF middleware commented out / removed", "CRITICAL"),
    (re.compile(r"SESSION_COOKIE_HTTPONLY\s*=\s*False", re.I),
     "Session cookie HttpOnly disabled — XSS can steal sessions", "HIGH"),
    (re.compile(r"SESSION_COOKIE_SECURE\s*=\s*False", re.I),
     "Session cookie Secure flag disabled", "MEDIUM"),
    (re.compile(r"CORS_ALLOW_CREDENTIALS\s*=\s*True", re.I),
     "CORS allows credentials — combined with permissive origins this enables session theft", "HIGH"),
    # Celery pickle serializer = deserialization RCE
    (re.compile(r'''task_serializer\s*=\s*['"]pickle['"]''', re.I),
     "Celery task serializer set to pickle — enables deserialization RCE", "CRITICAL"),
    (re.compile(r"accept_content\s*=.*pickle", re.I),
     "Celery accepts pickle content — enables deserialization RCE", "CRITICAL"),
    (re.compile(r'''result_serializer\s*=\s*['"]pickle['"]''', re.I),
     "Celery result serializer set to pickle — enables deserialization RCE", "CRITICAL"),
    # JWT algorithm confusion — only match when near algorithm context
    (re.compile(r'''ALLOWED.*ALGORITHMS?\s*=\s*\[.*['"]none['"]''', re.I),
     "JWT algorithm list includes 'none' — attackers can forge tokens", "CRITICAL"),
    (re.compile(r'''algorithms?\s*=\s*\[.*['"]none['"]''', re.I),
     "JWT algorithms parameter includes 'none' — enables token forgery", "CRITICAL"),
]

SECRET_PATTERNS = [
    (re.compile(r"""(?:SECRET_KEY|JWT_SECRET|API_SECRET)\s*=\s*['"]([^'"]{4,40})['"]""", re.I),
     "Hardcoded secret key", "CRITICAL"),
    (re.compile(r"""(?:SECRET_KEY|JWT_SECRET)\s*=\s*['"](?:django-insecure|changeme|secret|password|test)""", re.I),
     "Weak/default secret key", "CRITICAL"),
    (re.compile(r"""(?:DB_PASSWORD|DATABASE_PASSWORD|DATABASES.*PASSWORD)\s*[:=]\s*['"]([^'"]{3,})""", re.I),
     "Hardcoded database password", "CRITICAL"),
    (re.compile(r"""(?:AWS_SECRET_ACCESS_KEY|aws_secret_access_key)\s*=\s*['"]([^'"]{16,})""", re.I),
     "Hardcoded AWS credentials", "CRITICAL"),
]


def correlate_configs(files: list[ParsedFile]) -> list[ConfigRisk]:
    """
    Analyze config files for dangerous settings that amplify
    vulnerabilities in code files.
    Also scans Python code files for inline config (settings.py etc).
    """
    risks = []
    
    # Scan config files AND Python settings files
    scannable = [f for f in files if f.is_config or f.filename in ('settings.py', 'config.py', 'manage.py')]
    
    for f in scannable:
        # Check for dangerous config patterns (exact match)
        for pattern, risk_info in DANGEROUS_CONFIGS.items():
            if risk_info and pattern in f.content:
                desc, severity = risk_info
                risks.append(ConfigRisk(
                    file=f.path, setting=pattern.split("=")[0].strip(),
                    value=pattern, risk=desc, severity=severity,
                ))
        
        # Check for regex config patterns (fuzzy match)
        for regex, desc, severity in CONFIG_REGEX_PATTERNS:
            for match in regex.finditer(f.content):
                risks.append(ConfigRisk(
                    file=f.path, setting=match.group(0)[:60],
                    value="[matched]", risk=desc, severity=severity,
                ))
        
        # Check for secret patterns
        for regex, desc, severity in SECRET_PATTERNS:
            for match in regex.finditer(f.content):
                risks.append(ConfigRisk(
                    file=f.path, setting=match.group(0)[:40],
                    value="[REDACTED]", risk=desc, severity=severity,
                ))
    
    logger.info(f"[ConfigCorrelator] Found {len(risks)} config risks in {len(scannable)} files")
    return risks


# ─── Scanner: Obfuscation Decoder ─────────────────────────────────────

# Keywords that indicate a decoded payload is malicious
_MALICIOUS_KEYWORDS = [
    "os.system", "rm -rf", "curl", "wget", "import os", "eval(", "exec(",
    "subprocess", "__import__", "socket", "connect", "reverse", "shell",
    "chmod", "passwd", "shadow", "ssh", "nc ", "ncat",
]


def decode_obfuscation(files: list[ParsedFile]) -> list[DecodedPayload]:
    """
    Detect and decode obfuscated payloads that V1 would completely miss.
    Handles: base64, rot13, unicode escapes, hex strings.
    
    CRITICAL FIX: Now detects exec/eval + b64decode(VARIABLE) patterns,
    not just string literals. This catches the backdoor pattern:
        code = base64.b64decode(some_var).decode()
        exec(code)
    """
    payloads = []
    
    for f in files:
        if f.is_config:
            continue
        
        lines = f.content.split("\n")
        
        # Multi-line scan: track b64decode results used in exec/eval
        b64_vars = {}  # {var_name: line_number}
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Pattern 1: b64decode("STRING_LITERAL")
            b64_match = re.search(r'b64decode\s*\(\s*["\']([A-Za-z0-9+/=]{16,})["\']', stripped)
            if b64_match:
                try:
                    decoded = base64.b64decode(b64_match.group(1)).decode("utf-8", errors="replace")
                    is_bad = any(kw in decoded.lower() for kw in _MALICIOUS_KEYWORDS)
                    payloads.append(DecodedPayload(
                        file=f.path, line_number=i, encoding_type="base64",
                        original_code=stripped[:120], decoded_value=decoded[:200],
                        is_malicious=is_bad, severity="CRITICAL" if is_bad else "HIGH",
                    ))
                except Exception:
                    pass
            
            # Pattern 2: var = b64decode(ANYTHING) — track for exec/eval
            b64_var_match = re.search(r'(\w+)\s*=\s*.*b64decode\s*\(', stripped)
            if b64_var_match:
                b64_vars[b64_var_match.group(1)] = i
            # Also track: var = ...decode() after b64decode
            b64_var_match2 = re.search(r'(\w+)\s*=\s*.*b64decode\s*\(.+?\.decode\(', stripped)
            if b64_var_match2:
                b64_vars[b64_var_match2.group(1)] = i
            
            # Pattern 3: exec(VAR) or eval(VAR) where VAR came from b64decode
            exec_match = re.search(r'(?:exec|eval)\s*\(\s*(\w+)', stripped)
            if exec_match:
                var_name = exec_match.group(1)
                if var_name in b64_vars:
                    payloads.append(DecodedPayload(
                        file=f.path, line_number=i, encoding_type="base64_exec",
                        original_code=f"exec/eval of base64-decoded variable '{var_name}' (decoded at line {b64_vars[var_name]})",
                        decoded_value=f"OBFUSCATED BACKDOOR: Variable '{var_name}' is base64-decoded then executed. This is a remote code execution backdoor.",
                        is_malicious=True, severity="CRITICAL",
                    ))
                # Also flag exec/eval with inline b64decode
                if 'b64decode' in stripped or 'base64' in stripped:
                    payloads.append(DecodedPayload(
                        file=f.path, line_number=i, encoding_type="base64_exec",
                        original_code=stripped[:120],
                        decoded_value="OBFUSCATED BACKDOOR: exec/eval with base64-decoded input — remote code execution",
                        is_malicious=True, severity="CRITICAL",
                    ))
            
            # Pattern 4: exec/eval inside try/except (hidden backdoor)
            if ('exec(' in stripped or 'eval(' in stripped) and 'except' not in stripped:
                # Check if we're inside a try/except block (look at surrounding lines)
                in_try = False
                for j in range(max(0, i-5), i):
                    if 'try:' in lines[j-1] if j > 0 else '':
                        in_try = True
                for j in range(i, min(len(lines), i+3)):
                    if 'except' in lines[j-1] if j > 0 else '':
                        in_try = True
                
                if in_try and any(kw in f.content[max(0, f.content.find(stripped)-200):f.content.find(stripped)+50]
                                  for kw in ['b64decode', 'base64', 'decode(']):
                    payloads.append(DecodedPayload(
                        file=f.path, line_number=i, encoding_type="hidden_exec",
                        original_code=stripped[:120],
                        decoded_value="HIDDEN BACKDOOR: exec/eval with encoded input inside try/except — errors silently swallowed",
                        is_malicious=True, severity="CRITICAL",
                    ))
            
            # Pattern 5: codecs.decode("...", "rot13")
            rot13_match = re.search(r'codecs\.decode\s*\(\s*["\'](.+?)["\']\s*,\s*["\']rot.?13', stripped)
            if rot13_match:
                try:
                    decoded = codecs.decode(rot13_match.group(1), "rot13")
                    is_bad = any(kw in decoded.lower() for kw in _MALICIOUS_KEYWORDS)
                    payloads.append(DecodedPayload(
                        file=f.path, line_number=i, encoding_type="rot13",
                        original_code=stripped[:120], decoded_value=decoded[:200],
                        is_malicious=is_bad, severity="CRITICAL" if is_bad else "HIGH",
                    ))
                except Exception:
                    pass
            
            # Pattern 6: Unicode escape sequences
            unicode_match = re.search(r'["\']((\\x[0-9a-fA-F]{2}){4,})["\']', stripped)
            if unicode_match:
                try:
                    decoded = bytes(unicode_match.group(1), "utf-8").decode("unicode_escape")
                    is_bad = any(kw in decoded.lower() for kw in _MALICIOUS_KEYWORDS)
                    payloads.append(DecodedPayload(
                        file=f.path, line_number=i, encoding_type="unicode_escape",
                        original_code=stripped[:120], decoded_value=decoded[:200],
                        is_malicious=is_bad, severity="CRITICAL" if is_bad else "MEDIUM",
                    ))
                except Exception:
                    pass
            
            # Pattern 7: Hex-encoded strings
            hex_match = re.search(r'fromhex\s*\(\s*["\']([0-9a-fA-F]{8,})["\']', stripped)
            if hex_match:
                try:
                    decoded = bytes.fromhex(hex_match.group(1)).decode("utf-8", errors="replace")
                    is_bad = any(kw in decoded.lower() for kw in _MALICIOUS_KEYWORDS)
                    payloads.append(DecodedPayload(
                        file=f.path, line_number=i, encoding_type="hex",
                        original_code=stripped[:120], decoded_value=decoded[:200],
                        is_malicious=is_bad, severity="CRITICAL" if is_bad else "MEDIUM",
                    ))
                except Exception:
                    pass
    
    logger.info(f"[ObfuscationDecoder] Decoded {len(payloads)} obfuscated payloads")
    return payloads


# ─── Scanner: Dependency CVE Lookup (osv.dev) ─────────────────────────

def scan_dependencies_for_cves(files: list[ParsedFile]) -> list[CVEFinding]:
    """
    Check requirements.txt / package.json against the OSV.dev API
    for known CVEs. This is IMPOSSIBLE for V1.
    """
    findings = []
    
    for f in files:
        if f.filename == "requirements.txt":
            findings.extend(_check_python_deps(f))
        elif f.filename == "package.json":
            findings.extend(_check_npm_deps(f))
    
    logger.info(f"[CVEScanner] Found {len(findings)} known CVEs")
    return findings


def _check_python_deps(f: ParsedFile) -> list[CVEFinding]:
    """Query OSV for Python package CVEs."""
    import httpx
    
    findings = []
    for line in f.content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        
        # Parse: package==version or package>=version
        match = re.match(r'^([a-zA-Z0-9_.-]+)\s*[=<>!~]+\s*([0-9][0-9a-zA-Z.*-]*)', line)
        if not match:
            continue
        
        pkg, version = match.group(1), match.group(2)
        
        try:
            resp = httpx.post(
                OSV_API_URL,
                json={"package": {"name": pkg, "ecosystem": "PyPI"}, "version": version},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                for vuln in data.get("vulns", [])[:3]:  # Limit to 3 per package
                    cve_ids = [a for a in vuln.get("aliases", []) if a.startswith("CVE-")]
                    severity = _osv_severity(vuln)
                    findings.append(CVEFinding(
                        package=pkg, version=version,
                        cve_id=cve_ids[0] if cve_ids else vuln.get("id", "Unknown"),
                        summary=vuln.get("summary", "Known vulnerability")[:200],
                        severity=severity, file=f.path,
                    ))
        except Exception as e:
            logger.warning(f"[CVE] Failed to query OSV for {pkg}=={version}: {e}")
    
    return findings


def _check_npm_deps(f: ParsedFile) -> list[CVEFinding]:
    """Query OSV for npm package CVEs."""
    import httpx
    
    findings = []
    try:
        pkg_json = json.loads(f.content)
    except json.JSONDecodeError:
        return findings
    
    all_deps = {**pkg_json.get("dependencies", {}), **pkg_json.get("devDependencies", {})}
    
    for pkg, version_spec in list(all_deps.items())[:20]:  # Limit to 20 packages
        version = re.sub(r'[^0-9.]', '', version_spec)  # Strip ^, ~, etc.
        if not version:
            continue
        
        try:
            resp = httpx.post(
                OSV_API_URL,
                json={"package": {"name": pkg, "ecosystem": "npm"}, "version": version},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                for vuln in data.get("vulns", [])[:2]:
                    cve_ids = [a for a in vuln.get("aliases", []) if a.startswith("CVE-")]
                    severity = _osv_severity(vuln)
                    findings.append(CVEFinding(
                        package=pkg, version=version,
                        cve_id=cve_ids[0] if cve_ids else vuln.get("id", "Unknown"),
                        summary=vuln.get("summary", "Known vulnerability")[:200],
                        severity=severity, file=f.path,
                    ))
        except Exception as e:
            logger.warning(f"[CVE] Failed to query OSV for {pkg}@{version}: {e}")
    
    return findings


def _osv_severity(vuln: dict) -> str:
    """Extract severity from OSV vulnerability data."""
    for sev_obj in vuln.get("severity", []):
        score = sev_obj.get("score", "")
        if ":" in score:
            # CVSS vector — extract base score
            cvss_match = re.search(r'AV:[NL].*', score)
            if cvss_match:
                return "CRITICAL" if "AV:N" in score else "HIGH"
    
    # Fallback based on database severity
    db_severity = vuln.get("database_specific", {}).get("severity", "").upper()
    if db_severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        return db_severity
    return "HIGH"  # Default to HIGH for known CVEs
