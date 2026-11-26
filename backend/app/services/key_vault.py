"""Symmetric encryption for API keys stored for owner reveal.

API key authentication never uses this module: auth compares the
SHA256 hash in ApiKey.key_hash, exactly as before. The encrypted copy
exists only so a workspace owner can view and copy a key they created
from the Integrations page.

The Fernet key is derived deterministically from settings.JWT_SECRET.
Rotating JWT_SECRET makes previously stored keys un-revealable (their
decrypt returns None), but hash-based authentication keeps working.
"""
import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256((settings.JWT_SECRET or "").encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_key(raw_key: str) -> Optional[str]:
    """Encrypt a full API key for storage. Returns None on failure."""
    try:
        return _fernet().encrypt(raw_key.encode("utf-8")).decode("ascii")
    except Exception:
        return None


def decrypt_key(encrypted: Optional[str]) -> Optional[str]:
    """Decrypt a stored API key. Returns None on any failure."""
    if not encrypted:
        return None
    try:
        return _fernet().decrypt(encrypted.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None
    except Exception:
        return None
