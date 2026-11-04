"""Keyed IP hashing for privacy-preserving duplicate detection."""

import hashlib
import hmac

from app.config import settings


_KEY_CONTEXT = b"critique:ip-hash:key:v1"
_VALUE_CONTEXT = b"critique:ip-hash:value:v1\x00"


def hash_ip(ip: str) -> str:
    """Return a stable, keyed SHA-256 digest for IP addresses.

    The digest remains stable as long as SECRET_KEY remains unchanged.
    """
    secret = settings.SECRET_KEY.encode("utf-8")

    derived_key = hmac.new(
        secret,
        _KEY_CONTEXT,
        hashlib.sha256,
    ).digest()

    message = _VALUE_CONTEXT + ip.encode("utf-8")

    return hmac.new(
        derived_key,
        message,
        hashlib.sha256,
    ).hexdigest()
