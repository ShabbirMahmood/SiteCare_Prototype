"""Local prototype authentication helpers (not a complete hospital IAM system)."""
from __future__ import annotations
import hashlib
import hmac
import secrets


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return "scrypt$16384$" + salt.hex() + "$" + value.hex()


def password_matches(password: str, stored: str) -> bool:
    try:
        _, n, salt, expected = stored.split("$")
        value = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt),
                               n=int(n), r=8, p=1, dklen=32)
        return hmac.compare_digest(value.hex(), expected)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
