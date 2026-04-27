# 🛡️ OxTools V2 Security Scanner — Benchmark Answer Key

> ⚠️ **CONFIDENTIAL** — Do NOT share this file with the tools being tested.
> This is the ground truth for scoring benchmark results.

## Total Vulnerabilities: 48 across 7 files + 12 CVEs in dependencies

---

## File-by-File Vulnerability Map

### settings.py (10 vulns)
| # | Vulnerability | CWE | Severity | Cross-File? |
|---|---|---|---|---|
| 1 | Hardcoded SECRET_KEY (django-insecure) | CWE-798 | CRITICAL | No |
| 2 | DEBUG = True | CWE-489 | HIGH | No |
| 3 | ALLOWED_HOSTS = ["*"] | CWE-16 | HIGH | No |
| 4 | Hardcoded DB password | CWE-798 | CRITICAL | No |
| 5 | CSRF middleware commented out | CWE-352 | CRITICAL | No |
| 6 | CORS_ALLOW_ALL_ORIGINS + CREDENTIALS combo | CWE-942 | HIGH | Yes — combined risk |
| 7 | SESSION_COOKIE_HTTPONLY = False | CWE-1004 | HIGH | Yes — XSS → session theft |
| 8 | SESSION_COOKIE_SECURE = False | CWE-614 | MEDIUM | No |
| 9 | JWT allows "none" algorithm | CWE-327 | CRITICAL | Yes — traced to views.py |
| 10 | Hardcoded AWS credentials (2 keys) | CWE-798 | CRITICAL | No |

### users/models.py (4 vulns)
| # | Vulnerability | CWE | Severity | Cross-File? |
|---|---|---|---|---|
| 11 | MD5 password hashing (no salt) | CWE-328 | HIGH | No |
| 12 | check_password() timing attack | CWE-208 | HIGH | No |
| 13 | verify_api_key() timing attack | CWE-208 | HIGH | No |
| 14 | from_dict() mass assignment (is_admin) | CWE-915 | CRITICAL | Yes — views.py uses it |

### users/utils.py (5 vulns)
| # | Vulnerability | CWE | Severity | Cross-File? |
|---|---|---|---|---|
| 15 | sanitize_input() FALSE sanitizer | CWE-20 | CRITICAL | Yes — THE KEY TEST |
| 16 | generate_token() uses random (not secrets) | CWE-330 | HIGH | Yes — views.py uses it |
| 17 | is_safe_redirect() // bypass | CWE-601 | HIGH | Yes — views.py uses it |
| 18 | log_request() logs passwords/sessions | CWE-532 | HIGH | No |
| 19 | validate_email() ReDoS | CWE-1333 | MEDIUM | No |

### users/views.py (11 vulns)
| # | Vulnerability | CWE | Severity | Cross-File? |
|---|---|---|---|---|
| 20 | register() mass assignment → is_admin | CWE-915 | CRITICAL | Yes — models.py |
| 21 | login() reflected XSS | CWE-79 | HIGH | No |
| 22 | search_users() SQLi via false sanitizer | CWE-89 | CRITICAL | Yes — utils.py chain |
| 23 | user_profile() IDOR | CWE-639 | HIGH | No |
| 24 | update_profile() second-order SQLi | CWE-89 | CRITICAL | No |
| 25 | execute_command() CMDi via false sanitizer | CWE-78 | CRITICAL | Yes — utils.py chain |
| 26 | password_reset() predictable token | CWE-330 | HIGH | Yes — utils.py chain |
| 27 | redirect_view() open redirect | CWE-601 | HIGH | Yes — utils.py chain |
| 28 | admin_dashboard() JWT alg confusion | CWE-327 | CRITICAL | Yes — settings.py |
| 29 | process_payment() IDOR | CWE-639 | HIGH | No |
| 30 | process_payment() negative amount | CWE-20 | MEDIUM | No |

### files/handlers.py (7 vulns)
| # | Vulnerability | CWE | Severity | Cross-File? |
|---|---|---|---|---|
| 31 | handle_upload() path traversal | CWE-22 | CRITICAL | No |
| 32 | handle_upload() unrestricted file type | CWE-434 | HIGH | No |
| 33 | handle_upload() files in web root | CWE-552 | HIGH | No |
| 34 | handle_zip_upload() Zip Slip | CWE-22 | CRITICAL | No |
| 35 | parse_xml_config() XXE | CWE-611 | CRITICAL | No |
| 36 | parse_xml_config() Billion Laughs DoS | CWE-776 | HIGH | No |
| 37 | download_file() path traversal | CWE-22 | HIGH | No |
| 38 | process_avatar() SSRF | CWE-918 | CRITICAL | No |

### tasks.py (6 vulns)
| # | Vulnerability | CWE | Severity | Cross-File? |
|---|---|---|---|---|
| 39 | process_user_data() pickle RCE | CWE-502 | CRITICAL | No |
| 40 | send_webhook() SSRF (in @shared_task) | CWE-918 | CRITICAL | No — but task context! |
| 41 | generate_report() CMDi (shell=True) | CWE-78 | CRITICAL | No |
| 42 | sync_external_data() SSRF | CWE-918 | CRITICAL | No — task context |
| 43 | check_file_exists() TOCTOU | CWE-367 | HIGH | No |
| 44 | Hardcoded AWS credentials | CWE-798 | CRITICAL | No |

### middleware.py (5 vulns)
| # | Vulnerability | CWE | Severity | Cross-File? |
|---|---|---|---|---|
| 45 | Rate limiter X-Forwarded-For bypass | CWE-290 | MEDIUM | No |
| 46 | OBFUSCATED BACKDOOR (exec b64 header) | CWE-506 | CRITICAL | No — THE HARDEST TEST |
| 47 | Missing security headers | CWE-693 | MEDIUM | No |
| 48 | API key timing attack (direct ==) | CWE-208 | HIGH | No |

### requirements.txt CVEs (12+ expected)
| # | Package | Version | Known CVEs |
|---|---|---|---|
| C1 | Django | 3.2.0 | Multiple (SQLi, XSS, DoS) |
| C2 | PyYAML | 5.3.1 | CVE-2020-14343 (RCE) |
| C3 | Pillow | 8.1.0 | Multiple image processing CVEs |
| C4 | cryptography | 3.4.6 | CVE-2023-23931 |
| C5 | urllib3 | 1.26.4 | CRLF injection |
| C6 | lxml | 4.6.2 | XXE/XSS CVEs |
| C7 | paramiko | 2.7.2 | Auth bypass |
| C8 | pyjwt | 1.7.1 | Algorithm confusion |
| C9 | pymongo | 3.11.0 | Injection CVEs |
| C10 | celery | 4.4.7 | Deserialization |
| C11 | requests | 2.25.0 | CRLF injection |
| C12 | Jinja2 | 2.11.3 | SSTI/sandbox escape |

---

## Cross-File Chains (V2-EXCLUSIVE — V1 cannot detect these)

### Chain 1: False Sanitizer → SQLi + CMDi
```
views.py:search_users() → calls sanitize_input(query)
  → utils.py:sanitize_input() only does strip()/lower()
  → views.py: cursor.execute(f"...{clean_query}...")
  RESULT: SQL Injection despite "sanitized" input
```

### Chain 2: False Sanitizer → Command Injection
```
views.py:execute_command() → calls sanitize_input(cmd)
  → utils.py:sanitize_input() provides no real protection
  → views.py: os.system(f"echo {safe_cmd} | ...")
  RESULT: Command injection despite "sanitized" input
```

### Chain 3: JWT Algorithm Confusion
```
settings.py: ALLOWED_JWT_ALGORITHMS = ["HS256", "none"]
  → views.py:admin_dashboard() uses jwt.decode(..., algorithms=ALLOWED_JWT_ALGORITHMS)
  RESULT: Attacker uses alg:none to forge admin tokens
```

### Chain 4: Mass Assignment → Admin Escalation
```
models.py: User has is_admin field, from_dict uses setattr()
  → views.py:register() passes user input directly to from_dict()
  RESULT: Attacker sends {"is_admin": true} to become admin
```

### Chain 5: Predictable Reset Token
```
utils.py:generate_token() uses random.choice (not secrets)
  → views.py:password_reset() uses generate_token()
  RESULT: Reset tokens are predictable/bruteforceable
```

### Chain 6: CORS + Session Cookie Combo
```
settings.py: CORS_ALLOW_ALL_ORIGINS + CORS_ALLOW_CREDENTIALS + SESSION_COOKIE_HTTPONLY=False
  RESULT: XSS on any origin can steal session cookies
```

---

## Scoring Guide

### Detection Score (out of 48 + CVEs)
- Count each vulnerability found as 1 point
- Partial credit (0.5) if vulnerability type is correct but location is wrong

### Cross-File Score (out of 6 chains)
- 1 point per chain correctly identified with both source and sink

### False Positive Score
- Subtract 0.5 for each false positive in the report

### Final Score Formula
```
Score = (Detection + Cross-File Bonus) / (48 + Chain Count) * 100
       - (False Positives * 0.5)
```
