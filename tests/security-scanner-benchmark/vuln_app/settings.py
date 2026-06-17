# vuln_app/settings.py — Configuration (INTENTIONALLY VULNERABLE)
# ================================================================
# Vulnerability Key: 10 vulns

import os

SECRET_KEY = "django-insecure-super-secret-key-12345"   # CWE-798 Hardcoded secret

DEBUG = True                                             # CWE-489 Active debug in prod
ALLOWED_HOSTS = ["*"]                                    # CWE-16 Host header injection

# Database with hardcoded credentials
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'prod_db',
        'USER': 'admin',
        'PASSWORD': 'SuperSecr3t!Pr0d',                  # CWE-798 Hardcoded DB creds
        'HOST': 'db.internal.prod',
    }
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',         # CWE-352 CSRF disabled
    'django.middleware.common.CommonMiddleware',
    'vuln_app.middleware.DebugMiddleware',
]

# CORS — wide open
CORS_ALLOW_ALL_ORIGINS = True                            # CWE-942 Permissive CORS
CORS_ALLOW_CREDENTIALS = True                            # Combined → session theft

# Session — insecure flags
SESSION_COOKIE_HTTPONLY = False                           # CWE-1004 Cookie accessible to JS
SESSION_COOKIE_SECURE = False                            # CWE-614 Cookie over HTTP

# JWT — algorithm confusion
ALLOWED_JWT_ALGORITHMS = ["HS256", "none"]               # CWE-327 Algorithm confusion

# AWS credentials (hardcoded)
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"               # CWE-798
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # CWE-798
