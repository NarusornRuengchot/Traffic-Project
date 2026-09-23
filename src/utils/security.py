"""
Security and Authentication Utility.
Provides robust password hashing (PBKDF2 HMAC SHA-256) and signed token management
using Python standard library (zero external compiled dependencies).
"""
import os
import hmac
import hashlib
import base64
import json
import time
from typing import Dict, Any, Optional

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "ku-src-smart-traffic-secret-key-2026-secure")
TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hashes a password using PBKDF2 HMAC SHA-256 with 100,000 iterations.
    Format: iterations$salt$hash
    """
    if salt is None:
        salt = base64.b64encode(os.urandom(16)).decode("utf-8")
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )
    derived_b64 = base64.b64encode(derived).decode("utf-8")
    return f"{iterations}${salt}${derived_b64}"

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verifies a plain password against the stored PBKDF2 hash.
    """
    try:
        parts = stored_hash.split("$")
        if len(parts) != 3:
            return False
        iterations = int(parts[0])
        salt = parts[1]
        expected_hash = parts[2]

        derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        )
        derived_b64 = base64.b64encode(derived).decode("utf-8")
        return hmac.compare_digest(derived_b64, expected_hash)
    except Exception:
        return False

def create_access_token(payload: Dict[str, Any], expires_in: int = TOKEN_EXPIRY_SECONDS) -> str:
    """
    Creates a cryptographically signed URL-safe JWT-like token.
    Format: base64(header).base64(claims).base64(signature)
    """
    header = {"alg": "HS256", "typ": "JWT"}
    claims = dict(payload)
    claims["exp"] = int(time.time()) + expires_in
    claims["iat"] = int(time.time())

    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    p_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode("utf-8")).decode("utf-8").rstrip("=")

    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

    return f"{h_b64}.{p_b64}.{s_b64}"

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies token signature and expiration, returns claims dictionary or None.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_b64, p_b64, s_b64 = parts

        # Verify signature
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        expected_s_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")

        if not hmac.compare_digest(s_b64, expected_s_b64):
            return None

        # Pad base64 payload if needed
        rem = len(p_b64) % 4
        padded_p_b64 = p_b64 + ("=" * (4 - rem) if rem else "")
        claims = json.loads(base64.urlsafe_b64decode(padded_p_b64).decode("utf-8"))

        # Check expiration
        if "exp" in claims and time.time() > claims["exp"]:
            return None

        return claims
    except Exception:
        return None

# Alias for compatibility
decode_access_token = verify_access_token

