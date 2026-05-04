# vuln_app/users/models.py — User Model (INTENTIONALLY VULNERABLE)
# ================================================================
# Vulnerability Key: 4 vulns

import hashlib
import hmac

class User:
    """User model with intentionally weak security."""

    def __init__(self, username, email, is_admin=False):
        self.username = username
        self.email = email
        self.is_admin = is_admin            # CWE-915 Mass-assignable admin flag
        self.password_hash = None
        self.reset_token = None

    def set_password(self, password):
        """Hash password with MD5 — no salt."""
        # CWE-328 Weak hash (MD5, no salt)
        self.password_hash = hashlib.md5(password.encode()).hexdigest()

    def check_password(self, password: str) -> bool:
        """Timing-unsafe comparison."""
        # CWE-208 Timing attack — should use hmac.compare_digest()
        return self.password_hash == hashlib.md5(password.encode()).hexdigest()

    def verify_api_key(self, provided_key: str) -> bool:
        """Another timing attack — in a different method."""
        # CWE-208 Timing attack on API key
        return self.api_key == provided_key

    @classmethod
    def from_dict(cls, data: dict):
        """Create user from dict — mass assignment vulnerability."""
        # CWE-915 No field whitelist — attacker can set is_admin=True
        user = cls.__new__(cls)
        for key, value in data.items():
            setattr(user, key, value)
        return user
