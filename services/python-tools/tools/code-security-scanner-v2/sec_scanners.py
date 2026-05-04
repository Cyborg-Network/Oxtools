"""
Code Security Scanner V2 — Deterministic Scanners
===================================================
Pure programmatic security analysis — NO LLM involvement.
These scanners use AST parsing, regex pattern matching, and
subprocess execution to find vulnerabilities deterministically.

This is what makes this tool a REAL agent, not a prompt wrapper:
the LLM only sees pre-validated, structured findings from these
scanners, not raw code.
"""

import ast
import os
import re
import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Optional

from sec_config import LANGUAGE_EXTENSIONS

logger = logging.getLogger("security-scanner")


# ─── Finding Data Structure ───────────────────────────────────────────

@dataclass
class Finding:
    """A single security finding from any scanner."""
    scanner: str           # Which scanner found it ("bandit", "ast", "secrets", "patterns")
    severity: str          # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    category: str          # OWASP category or custom category
    title: str             # Short title
    description: str       # What the issue is
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    cwe_id: Optional[str] = None        # CWE reference if applicable
    confidence: str = "HIGH"            # "HIGH" | "MEDIUM" | "LOW"

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Scanner 1: Bandit (Python-specific) ──────────────────────────────

def run_bandit(code: str) -> list[Finding]:
    """
    Execute Bandit static analyzer on Python code via subprocess.
    Returns structured findings, not raw text.
    """
    findings = []

    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = subprocess.run(
            ["bandit", "-r", temp_path, "-f", "json", "--severity-level", "all"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.stdout:
            data = json.loads(result.stdout)
            for issue in data.get("results", []):
                severity_map = {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH"}
                findings.append(Finding(
                    scanner="bandit",
                    severity=severity_map.get(issue.get("issue_severity", ""), "MEDIUM"),
                    category=f"Bandit {issue.get('test_id', 'Unknown')}",
                    title=issue.get("issue_text", "Unknown issue"),
                    description=(
                        f"Test: {issue.get('test_name', 'unknown')}\n"
                        f"Confidence: {issue.get('issue_confidence', 'unknown')}"
                    ),
                    line_number=issue.get("line_number"),
                    code_snippet=issue.get("code", ""),
                    cwe_id=issue.get("cwe", {}).get("id") if isinstance(issue.get("cwe"), dict) else None,
                    confidence=issue.get("issue_confidence", "MEDIUM"),
                ))

        logger.info(f"[Bandit] Found {len(findings)} issues")

    except FileNotFoundError:
        logger.warning("[Bandit] Not installed — skipping (pip install bandit)")
    except subprocess.TimeoutExpired:
        logger.warning("[Bandit] Timed out after 30s")
    except json.JSONDecodeError:
        logger.warning("[Bandit] Failed to parse output")
    except Exception as e:
        logger.warning(f"[Bandit] Unexpected error: {e}")
    finally:
        os.unlink(temp_path)

    return findings


# ─── Scanner 2: Secret Detection (All Languages) ─────────────────────

# Patterns compiled once at module load for performance
SECRET_PATTERNS = [
    # API Keys & Tokens
    (re.compile(r"""(?:api[_-]?key|apikey|api_secret)\s*[:=]\s*['"]([a-zA-Z0-9_\-]{16,})['"]""", re.I),
     "Hardcoded API Key", "CRITICAL", "CWE-798"),

    # AWS Access Keys
    (re.compile(r"""AKIA[0-9A-Z]{16}"""),
     "AWS Access Key ID", "CRITICAL", "CWE-798"),

    # AWS Secret Keys
    (re.compile(r"""(?:aws_secret|secret_access_key)\s*[:=]\s*['"]([a-zA-Z0-9/+=]{40})['"]""", re.I),
     "AWS Secret Access Key", "CRITICAL", "CWE-798"),

    # Generic Secrets/Passwords
    (re.compile(r"""(?:password|passwd|pwd|secret|token)\s*[:=]\s*['"]([^'"]{8,})['"]""", re.I),
     "Hardcoded Secret/Password", "HIGH", "CWE-798"),

    # Private Keys
    (re.compile(r"""-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"""),
     "Embedded Private Key", "CRITICAL", "CWE-321"),

    # JWT Tokens
    (re.compile(r"""eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_\-]+"""),
     "Hardcoded JWT Token", "HIGH", "CWE-798"),

    # Database Connection Strings
    (re.compile(r"""(?:mongodb|postgres|mysql|redis):\/\/[^\s'"]+""", re.I),
     "Hardcoded Database Connection String", "HIGH", "CWE-798"),

    # Generic Bearer Tokens
    (re.compile(r"""(?:bearer|authorization)\s*[:=]\s*['"]([a-zA-Z0-9_\-.]{20,})['"]""", re.I),
     "Hardcoded Bearer/Auth Token", "HIGH", "CWE-798"),
]

def scan_secrets(code: str) -> list[Finding]:
    """
    Regex-based secret detection across ALL languages.
    This catches what bandit misses in non-Python code.
    """
    findings = []
    lines = code.split("\n")

    for pattern, title, severity, cwe in SECRET_PATTERNS:
        for i, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
                continue

            if pattern.search(line):
                findings.append(Finding(
                    scanner="secrets",
                    severity=severity,
                    category="Data Exposure",
                    title=title,
                    description=f"Detected pattern matching {title.lower()} in source code.",
                    line_number=i,
                    code_snippet=line.strip()[:120],
                    cwe_id=cwe,
                    confidence="HIGH",
                ))

    logger.info(f"[Secrets] Found {len(findings)} potential secrets")
    return findings


# ─── Scanner 3: Python AST Analysis ──────────────────────────────────

def scan_python_ast(code: str) -> list[Finding]:
    """
    Deep AST-based analysis for Python code.
    Catches dangerous function calls, unsafe deserialization,
    SQL injection patterns, and command injection risks.
    """
    findings = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        findings.append(Finding(
            scanner="ast",
            severity="LOW",
            category="Code Quality",
            title="Syntax Error in Code",
            description=f"Python AST parser failed: {str(e)}",
            line_number=e.lineno,
        ))
        return findings

    # Dangerous function calls
    DANGEROUS_CALLS = {
        "eval": ("CRITICAL", "CWE-95", "Code Injection via eval()", "Arbitrary code execution"),
        "exec": ("CRITICAL", "CWE-95", "Code Injection via exec()", "Arbitrary code execution"),
        "compile": ("HIGH", "CWE-95", "Dynamic code compilation", "Potential code injection"),
        "__import__": ("MEDIUM", "CWE-95", "Dynamic import", "May load arbitrary modules"),
    }

    DANGEROUS_ATTRS = {
        ("pickle", "loads"): ("CRITICAL", "CWE-502", "Unsafe Deserialization (pickle.loads)", "Arbitrary code execution via crafted pickle data — attacker can inject __reduce__ RCE gadgets"),
        ("pickle", "load"): ("CRITICAL", "CWE-502", "Unsafe Deserialization (pickle.load)", "Arbitrary code execution via crafted pickle data — attacker can inject __reduce__ RCE gadgets"),
        ("pickle", "dumps"): ("MEDIUM", "CWE-502", "Pickle Serialization", "If combined with loads(), enables RCE via __reduce__ gadget chains"),
        ("yaml", "load"): ("CRITICAL", "CWE-502", "Unsafe YAML Deserialization", "yaml.load without Loader allows arbitrary Python object construction. Use yaml.safe_load()"),
        ("subprocess", "call"): ("HIGH", "CWE-78", "Subprocess Call", "Potential command injection if user input flows in"),
        ("subprocess", "Popen"): ("HIGH", "CWE-78", "Subprocess Popen", "Potential command injection if user input flows in"),
        ("subprocess", "run"): ("MEDIUM", "CWE-78", "Subprocess Run", "Check for shell=True with user input — enables command injection"),
        ("os", "system"): ("CRITICAL", "CWE-78", "OS Command Execution", "Direct shell command execution — high injection risk"),
        ("os", "popen"): ("HIGH", "CWE-78", "OS Pipe Execution", "Direct shell pipe — high injection risk"),
        ("marshal", "loads"): ("HIGH", "CWE-502", "Unsafe Deserialization (marshal)", "Can execute arbitrary bytecode"),
        ("shelve", "open"): ("MEDIUM", "CWE-502", "Shelve Deserialization", "Uses pickle under the hood"),
        # SSTI
        ("render_template_string", None): ("CRITICAL", "CWE-1336", "Server-Side Template Injection (SSTI)", "render_template_string with user input enables RCE via Jinja2 template expressions"),
    }

    # Special check: render_template_string as a direct call (not attribute)
    DANGEROUS_CALLS["render_template_string"] = ("CRITICAL", "CWE-1336", "Server-Side Template Injection (SSTI)", "User input in Jinja2 templates enables full RCE via {{config.__class__.__init__.__globals__}}")

    for node in ast.walk(tree):
        # Check direct function calls: eval(), exec(), etc.
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
                sev, cwe, title, desc = DANGEROUS_CALLS[node.func.id]
                findings.append(Finding(
                    scanner="ast",
                    severity=sev,
                    category="Code Injection",
                    title=title,
                    description=desc,
                    line_number=node.lineno,
                    cwe_id=cwe,
                ))

            # Check attribute calls: pickle.loads(), os.system(), etc.
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    key = (node.func.value.id, node.func.attr)
                    if key in DANGEROUS_ATTRS:
                        sev, cwe, title, desc = DANGEROUS_ATTRS[key]
                        findings.append(Finding(
                            scanner="ast",
                            severity=sev,
                            category="Dangerous API Usage",
                            title=title,
                            description=desc,
                            line_number=node.lineno,
                            cwe_id=cwe,
                        ))

        # Check for bare except clauses (swallows all errors including SystemExit)
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(Finding(
                scanner="ast",
                severity="LOW",
                category="Error Handling",
                title="Bare except clause",
                description="Catches all exceptions including SystemExit and KeyboardInterrupt. Use specific exception types.",
                line_number=node.lineno,
                cwe_id="CWE-396",
            ))

        # Check for assert statements (removed in optimized bytecode)
        if isinstance(node, ast.Assert):
            findings.append(Finding(
                scanner="ast",
                severity="MEDIUM",
                category="Authentication",
                title="Assert used for validation",
                description="assert statements are removed when Python runs with -O flag. Never use assert for security checks.",
                line_number=node.lineno,
                cwe_id="CWE-617",
            ))

        # Check for __reduce__ method (RCE gadget for pickle deserialization)
        if isinstance(node, ast.FunctionDef) and node.name == "__reduce__":
            findings.append(Finding(
                scanner="ast",
                severity="CRITICAL",
                category="Deserialization",
                title="__reduce__ RCE Gadget",
                description="Class defines __reduce__ which can execute arbitrary code when pickled/unpickled. This is a deserialization attack vector.",
                line_number=node.lineno,
                cwe_id="CWE-502",
            ))

        # Check for subprocess with shell=True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        findings.append(Finding(
                            scanner="ast",
                            severity="CRITICAL",
                            category="Command Injection",
                            title="Subprocess with shell=True",
                            description="shell=True passes command through the shell, enabling injection via semicolons, pipes, and backticks.",
                            line_number=node.lineno,
                            cwe_id="CWE-78",
                        ))

        # Check for XML parsers without defuse
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("parse", "fromstring", "iterparse"):
                if isinstance(node.func.value, ast.Name) and node.func.value.id in ("etree", "ET", "ElementTree", "minidom", "xml"):
                    findings.append(Finding(
                        scanner="ast",
                        severity="HIGH",
                        category="XML External Entity",
                        title="XML Parser without defuse (XXE / Billion Laughs)",
                        description="XML parsing without defusedxml enables XXE attacks and Billion Laughs DoS.",
                        line_number=node.lineno,
                        cwe_id="CWE-611",
                    ))

        # Check for timing-vulnerable comparisons (== on secrets)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            # Check if variable names suggest secrets
            secret_names = {"key", "token", "secret", "password", "sig", "signature", "api_key", "provided", "expected"}
            names_involved = set()
            if isinstance(node.left, ast.Name):
                names_involved.add(node.left.id.lower())
            for comp in node.comparators:
                if isinstance(comp, ast.Name):
                    names_involved.add(comp.id.lower())
            if names_involved & secret_names:
                findings.append(Finding(
                    scanner="ast",
                    severity="HIGH",
                    category="Timing Attack",
                    title="Timing-vulnerable comparison on secret",
                    description="Using == to compare secrets enables timing attacks. Use hmac.compare_digest() instead.",
                    line_number=node.lineno,
                    cwe_id="CWE-208",
                ))

    logger.info(f"[AST] Found {len(findings)} issues")
    return findings


# ─── Scanner 4: Language-Agnostic Pattern Matching ────────────────────

VULN_PATTERNS = {
    "sql_injection": [
        (re.compile(r"""(?:execute|query|raw)\s*\(\s*(?:f['"]|['"].*%s|['"].*\+|['"].*\.format)""", re.I),
         "SQL Injection Risk", "CRITICAL", "CWE-89",
         "String concatenation or f-strings in SQL queries enable injection attacks"),
        (re.compile(r"""(?:execute|cursor)\s*\(\s*f['"](?:SELECT|INSERT|UPDATE|DELETE)""", re.I),
         "SQL Injection via f-string", "CRITICAL", "CWE-89",
         "f-string in SQL statement — use parameterized queries"),
    ],
    "xss": [
        (re.compile(r"""innerHTML\s*=\s*""", re.I),
         "Potential XSS via innerHTML", "HIGH", "CWE-79",
         "Setting innerHTML with unsanitized input enables cross-site scripting"),
        (re.compile(r"""dangerouslySetInnerHTML""", re.I),
         "React dangerouslySetInnerHTML", "MEDIUM", "CWE-79",
         "Renders raw HTML — ensure input is sanitized"),
    ],
    "ssti": [
        (re.compile(r"""render_template_string\s*\(""", re.I),
         "Server-Side Template Injection (SSTI)", "CRITICAL", "CWE-1336",
         "render_template_string with user input enables full RCE via Jinja2"),
        (re.compile(r"""Environment\s*\(\)\s*\.\s*from_string""", re.I),
         "SSTI via Jinja2 Environment", "CRITICAL", "CWE-1336",
         "Unsandboxed Jinja2 Environment().from_string allows template injection RCE"),
        (re.compile(r"""Template\s*\(\s*(?:request|user|input|data)""", re.I),
         "Potential Template Injection", "HIGH", "CWE-1336",
         "User input flowing into template constructor"),
    ],
    "path_traversal": [
        (re.compile(r"""(?:open|read|write)\s*\(.*(?:request|req|params|query|input|argv)""", re.I),
         "Potential Path Traversal", "HIGH", "CWE-22",
         "File operations with user input — validate and sanitize paths"),
        (re.compile(r"""f\.save\s*\(""", re.I),
         "Unvalidated File Upload Save", "HIGH", "CWE-434",
         "File saved without validating content — check magic bytes, not just Content-Type"),
        (re.compile(r"""content_type\s*in\s*\[""", re.I),
         "Content-Type Only Validation", "HIGH", "CWE-434",
         "Validating file type by Content-Type header only — trivially spoofed by attacker"),
    ],
    "crypto": [
        (re.compile(r"""hashlib\.(?:md5|sha1)\s*\(""", re.I),
         "Weak Password Hashing (MD5/SHA1)", "HIGH", "CWE-328",
         "MD5/SHA1 for password hashing is cryptographically broken — rainbow tables can crack in seconds. Use bcrypt/argon2/scrypt"),
        (re.compile(r"""(?:md5|sha1)\s*\(""", re.I),
         "Weak Hashing Algorithm", "MEDIUM", "CWE-328",
         "MD5/SHA1 are cryptographically broken — use SHA-256 or bcrypt"),
        (re.compile(r"""hexdigest\s*\(\).*==|==.*hexdigest\s*\(\)""", re.I),
         "Unsalted Hash Comparison", "HIGH", "CWE-916",
         "Hash comparison without salt — vulnerable to rainbow table attacks. Use bcrypt with per-user salt"),
        (re.compile(r"""(?:DES|RC4|Blowfish)""", re.I),
         "Weak Encryption Algorithm", "HIGH", "CWE-327",
         "DES/RC4/Blowfish are deprecated — use AES-256"),
        (re.compile(r"""MODE_ECB"""),
         "ECB Mode Encryption", "HIGH", "CWE-327",
         "ECB mode reveals patterns in plaintext — use CBC or GCM"),
        (re.compile(r"""b'\\x00'\s*\*\s*\d+"""),
         "Static/Zero IV", "HIGH", "CWE-329",
         "Hardcoded or zero IV defeats CBC security — generate random IV per encryption"),
        (re.compile(r"""nonce.*(?:never|reuse|static|counter.*0|same)""", re.I),
         "Cryptographic Nonce Reuse", "CRITICAL", "CWE-323",
         "Reusing nonce in CTR/GCM mode enables XOR attacks to recover plaintext"),
    ],
    "ldap_injection": [
        (re.compile(r"""(?:search_s|search)\s*\(.*f['"]\s*\(""", re.I),
         "LDAP Injection", "CRITICAL", "CWE-90",
         "User input in LDAP filter without sanitization — bypass: *)(&(objectClass=*"),
        (re.compile(r"""f['"]\(&\(uid=\{|f['"]\(uid=\{""", re.I),
         "LDAP Filter Injection", "CRITICAL", "CWE-90",
         "F-string in LDAP filter with user input enables authentication bypass"),
    ],
    "nosql_injection": [
        (re.compile(r"""find_one\s*\(\s*\{.*(?:request|password|user|input)""", re.I),
         "NoSQL Injection", "CRITICAL", "CWE-943",
         "User input in MongoDB query — attacker can pass {\"$gt\": \"\"} to bypass auth"),
        (re.compile(r"""\$(?:gt|ne|lt|gte|lte|regex|where|exists)"""),
         "NoSQL Operator in Data", "HIGH", "CWE-943",
         "MongoDB operators in data suggest NoSQL injection risk"),
    ],
    "xml_attack": [
        (re.compile(r"""<!DOCTYPE.*<!ENTITY""", re.I | re.S),
         "XML Billion Laughs / XXE Payload", "CRITICAL", "CWE-776",
         "XML with entity definitions — Billion Laughs DoS or XXE data exfiltration"),
        (re.compile(r"""etree\.parse|minidom\.parse|fromstring""", re.I),
         "Unsafe XML Parser", "HIGH", "CWE-611",
         "XML parsing without defusedxml allows XXE and entity expansion DoS"),
    ],
    "timing_attack": [
        (re.compile(r"""(?:provided|key|token|sig)\s*==\s*(?:expected|stored|secret)""", re.I),
         "Timing Attack on Secret Comparison", "HIGH", "CWE-208",
         "String == comparison on secrets leaks timing information — use hmac.compare_digest()"),
    ],
    "mass_assignment": [
        (re.compile(r"""setattr\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*\)""", re.I),
         "Mass Assignment via setattr()", "CRITICAL", "CWE-915",
         "setattr() in a loop with user data enables attackers to set arbitrary attributes (e.g. is_admin=True)"),
        (re.compile(r"""for\s+\w+\s*,\s*\w+\s+in\s+\w+\.items\(\).*setattr""", re.I | re.S),
         "Mass Assignment: dict iteration + setattr", "CRITICAL", "CWE-915",
         "Iterating user dict and calling setattr enables mass assignment — attacker can set any field"),
        (re.compile(r"""__dict__\.update\s*\(""", re.I),
         "Mass Assignment via __dict__.update()", "CRITICAL", "CWE-915",
         "__dict__.update() with user data enables arbitrary attribute assignment"),
    ],
    "insecure_random": [
        (re.compile(r"""random\.(?:choice|randint|random|shuffle|sample)\s*\(""", re.I),
         "Insecure Random Number Generator", "HIGH", "CWE-330",
         "random module is NOT cryptographically secure. Use secrets.token_hex() or secrets.choice() for tokens/passwords"),
        (re.compile(r"""random\.(?:choice|randint).*(?:token|password|secret|key|otp|code|nonce)""", re.I),
         "Predictable Security Token", "CRITICAL", "CWE-330",
         "Using random.choice/randint for security tokens — tokens are predictable/bruteforceable. Use secrets module"),
    ],
    "open_redirect": [
        (re.compile(r"""redirect\s*\(\s*(?:request|req)\.""", re.I),
         "Open Redirect via User Input", "HIGH", "CWE-601",
         "redirect() with user-controlled URL enables phishing attacks — validate against whitelist"),
        (re.compile(r"""redirect\s*\(\s*\w+\s*\)""", re.I),
         "Potential Open Redirect", "MEDIUM", "CWE-601",
         "redirect() with variable — verify URL is validated against allowed domains"),
        (re.compile(r"""startswith\s*\(\s*['\"]http://localhost""", re.I),
         "Weak Redirect Validation", "HIGH", "CWE-601",
         "startswith('http://localhost') can be bypassed with http://localhost@evil.com"),
    ],
    "log_leak": [
        (re.compile(r"""log(?:ger)?\.(?:info|debug|warning|error)\s*\(.*(?:password|passwd|pwd|secret|token|session|credit|ssn|authorization)""", re.I),
         "Sensitive Data in Log Output", "HIGH", "CWE-532",
         "Logging sensitive data (passwords, tokens, sessions) — violates security best practices"),
        (re.compile(r"""log(?:ger)?\.(?:info|debug)\s*\(.*request\.(?:body|headers|session)""", re.I),
         "Request Body/Headers Logged", "HIGH", "CWE-532",
         "Logging full request body/headers may expose passwords, tokens, and PII"),
        (re.compile(r"""print\s*\(.*(?:password|secret|token|api_key|private_key)""", re.I),
         "Sensitive Data in Print Output", "MEDIUM", "CWE-532",
         "Printing sensitive data to stdout — may appear in logs or console output"),
    ],
    "redos": [
        (re.compile(r"""re\.(?:match|search|compile)\s*\(.*\(\?:.*\+.*\+""", re.I),
         "Potential ReDoS (Catastrophic Backtracking)", "MEDIUM", "CWE-1333",
         "Nested quantifiers in regex can cause exponential backtracking on malicious input"),
        (re.compile(r"""re\.(?:match|search|compile)\s*\(.*\(\.[*+]\)\*""", re.I),
         "ReDoS via Nested Repetition", "MEDIUM", "CWE-1333",
         "Pattern like (.*)*  causes catastrophic backtracking — use atomic groups or possessive quantifiers"),
    ],
    "reflected_xss": [
        (re.compile(r"""HttpResponse\s*\(\s*f['\"].*(?:request|username|user_input|query|name|error|message)""", re.I),
         "Reflected XSS via HttpResponse", "HIGH", "CWE-79",
         "User input interpolated directly into HttpResponse — enables reflected cross-site scripting"),
        (re.compile(r"""HttpResponse\s*\(\s*['\"].*%s.*['\"].*%.*(?:request|user)""", re.I),
         "Reflected XSS via String Formatting", "HIGH", "CWE-79",
         "User input formatted into HTML response without escaping — XSS risk"),
        (re.compile(r"""return\s+['\"]<.*(?:request|username|input|query|error).*>['\"]""", re.I),
         "Reflected XSS in Return Value", "HIGH", "CWE-79",
         "User input embedded in HTML string — use template escaping"),
        (re.compile(r"""HttpResponse\s*\(.*(?:request\.GET|request\.POST|request\.META)""", re.I),
         "Reflected XSS via Request Data in Response", "HIGH", "CWE-79",
         "Request data directly in HttpResponse without escaping — reflected XSS"),
    ],
    "zip_slip": [
        (re.compile(r"""extractall\s*\(""", re.I),
         "Zip Slip via extractall()", "CRITICAL", "CWE-22",
         "zipfile.extractall() doesn't validate member paths — attacker can write files to ../../etc/passwd"),
        (re.compile(r"""ZipFile.*extract\s*\(""", re.I),
         "Potential Zip Slip via extract()", "HIGH", "CWE-22",
         "Individual zip extract without path validation — check for ../ in member names"),
    ],
    "toctou": [
        (re.compile(r"""os\.path\.exists\s*\(.*\).*(?:open|read|write)\s*\(""", re.I | re.S),
         "TOCTOU Race Condition", "HIGH", "CWE-367",
         "Time-of-check/time-of-use: file existence checked then used later — attacker can swap file between check and use"),
    ],
    "idor": [
        (re.compile(r"""\.get\s*\(\s*(?:id|pk)\s*=.*(?:request|params|args|data)""", re.I),
         "Potential IDOR (Insecure Direct Object Reference)", "HIGH", "CWE-639",
         "Object retrieved by user-supplied ID without ownership verification — any user can access any object"),
        (re.compile(r"""\.objects\.get\s*\(\s*(?:id|pk)\s*=""", re.I),
         "Direct Object Access Without Authorization", "HIGH", "CWE-639",
         "Database object fetched by ID — verify the requesting user owns or is authorized to access this object"),
        (re.compile(r"""JsonResponse\s*\(.*(?:api_token|token|secret|password|hash|reset_token|private_key|ssn|credit_card|is_admin)""", re.I),
         "Sensitive Field Exposure in API Response", "HIGH", "CWE-200",
         "Sensitive fields (tokens, passwords, admin flags) included in API response — information disclosure risk"),
    ],
    "jwt_misconfiguration": [
        (re.compile(r"""['\"]none['\"]""", re.I),
         "JWT 'none' Algorithm Allowed", "CRITICAL", "CWE-327",
         "Allowing 'none' algorithm in JWT lets attackers forge tokens without a signature — full auth bypass"),
        (re.compile(r"""algorithms?\s*=\s*\[.*['\"]none['\"]""", re.I),
         "JWT Algorithm List Includes 'none'", "CRITICAL", "CWE-327",
         "JWT decode accepts 'none' algorithm — attacker can create unsigned tokens to bypass authentication"),
    ],
    "ssrf": [
        (re.compile(r"""urllib\.request\.urlopen\s*\(""", re.I),
         "SSRF via urllib.request.urlopen()", "CRITICAL", "CWE-918",
         "urlopen() with user-controlled URL enables SSRF — attacker can access internal services (169.254.169.254, localhost, etc.)"),
        (re.compile(r"""requests\.get\s*\(.*(?:url|callback|webhook|endpoint|target)""", re.I),
         "SSRF via requests.get() with user input", "HIGH", "CWE-918",
         "HTTP request with user-controlled URL — validate against allowlist to prevent SSRF"),
    ],
    "header_trust": [
        (re.compile(r"""X-Forwarded-For""", re.I),
         "Trusting X-Forwarded-For Header", "MEDIUM", "CWE-290",
         "X-Forwarded-For is trivially spoofable by clients — rate limiters using it can be bypassed"),
    ],
    "file_upload": [
        (re.compile(r"""uploaded.*\.name|request\.FILES""", re.I),
         "File Upload Without Sanitization", "HIGH", "CWE-434",
         "File upload without filename sanitization — attacker can use ../../etc/passwd as filename for path traversal"),
        (re.compile(r"""os\.path\.join\s*\(\s*\w+\s*,\s*(?:filename|uploaded|file\.name)""", re.I),
         "Path Traversal in File Upload", "CRITICAL", "CWE-22",
         "os.path.join with unsanitized filename — attacker filename '../../../etc/passwd' escapes upload directory"),
        (re.compile(r"""(?:open|write)\s*\(.*(?:filename|uploaded_file|file_path).*['"]w""", re.I),
         "File Write Without Extension Validation", "HIGH", "CWE-434",
         "File written without validating extension — attacker can upload .php/.py/.jsp for remote code execution"),
    ],
    "insecure_tempfile": [
        (re.compile(r"""tempfile\.mk(?:temp|stemp)\s*\(""", re.I),
         "Insecure Temporary File Creation", "HIGH", "CWE-377",
         "mktemp/mkstemp creates predictable temp files — use tempfile.NamedTemporaryFile or tempfile.mkdtemp"),
        (re.compile(r"""['\"](?:/tmp/|C:\\temp\\).*(?:filename|name|uploaded)""", re.I),
         "Predictable Temp Path with User Input", "HIGH", "CWE-377",
         "Hardcoded temp directory with user-influenced filename — race condition and path traversal risk"),
    ],
    "false_sanitizer": [
        (re.compile(r"""def\s+(?:sanitize|clean|escape|filter|validate)_?\w*\s*\(.*\).*:\s*$""", re.I),
         "Custom Sanitizer Function Detected", "MEDIUM", "CWE-20",
         "Custom sanitizer detected — verify it actually neutralizes dangerous characters, not just strip()/lower(). False sanitizers are a critical cross-file vulnerability source"),
        (re.compile(r"""(?:strip|lower|upper|title|capitalize)\s*\(\)\s*$""", re.I),
         "Ineffective Input Sanitization", "HIGH", "CWE-20",
         "strip()/lower() does NOT sanitize against injection attacks (SQLi, XSS, CMDi). These are formatting functions, not security functions"),
        (re.compile(r"""return\s+\w+\.strip\s*\(\)(?:\.lower\s*\(\))?\s*$""", re.I),
         "False Sanitizer: strip()/lower() Only", "CRITICAL", "CWE-20",
         "Function returns input.strip().lower() claiming to sanitize — this provides ZERO protection against SQL injection, XSS, or command injection"),
    ],
    "business_logic": [
        (re.compile(r"""(?:amount|price|quantity|balance)\s*=.*(?:request|params|data|body)""", re.I),
         "Unvalidated Financial Amount from User Input", "MEDIUM", "CWE-20",
         "Financial amount taken directly from user input — validate: positive number, reasonable range, correct type"),
        (re.compile(r"""(?:payment|charge|transfer|withdraw).*(?:amount|price)""", re.I),
         "Payment Logic Without Amount Validation", "HIGH", "CWE-20",
         "Payment processing without validating amount — negative amounts can credit attacker's account"),
    ],
    "missing_security_headers": [
        (re.compile(r"""(?:SecurityMiddleware|XFrameOptionsMiddleware|ContentSecurityPolicy)""", re.I),
         "Security Header Middleware Reference", "LOW", "CWE-693",
         "Verify these security middlewares are enabled, not commented out, and properly configured"),
    ],
}

def scan_patterns(code: str, language: str) -> list[Finding]:
    """
    Language-agnostic vulnerability pattern matching.
    Catches SQL injection, XSS, path traversal, and crypto issues.
    """
    findings = []
    lines = code.split("\n")

    for category, patterns in VULN_PATTERNS.items():
        for pattern, title, severity, cwe, description in patterns:
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    findings.append(Finding(
                        scanner="patterns",
                        severity=severity,
                        category=category.replace("_", " ").title(),
                        title=title,
                        description=description,
                        line_number=i,
                        code_snippet=line.strip()[:120],
                        cwe_id=cwe,
                        confidence="MEDIUM",
                    ))

    logger.info(f"[Patterns] Found {len(findings)} issues for {language}")
    return findings


# ─── Orchestrator: Run All Scanners ───────────────────────────────────

def run_all_scanners(code: str, language: str) -> list[dict]:
    """
    Execute all applicable scanners and return deduplicated findings.
    This is the single entry point called by the Scanner agent node.
    """
    all_findings: list[Finding] = []

    # Always run language-agnostic scanners
    all_findings.extend(scan_secrets(code))
    all_findings.extend(scan_patterns(code, language))

    # Run Python-specific scanners
    if language == "python":
        all_findings.extend(run_bandit(code))
        all_findings.extend(scan_python_ast(code))

    # Deduplicate by (line_number, title)
    seen = set()
    unique: list[Finding] = []
    for f in all_findings:
        key = (f.line_number, f.title)
        if key not in seen:
            seen.add(key)
            unique.append(f)

    # Sort by severity (critical first)
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    unique.sort(key=lambda f: severity_order.get(f.severity, 99))

    logger.info(f"[Scanners] Total unique findings: {len(unique)}")
    return [f.to_dict() for f in unique]
