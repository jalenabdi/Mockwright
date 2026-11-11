"""Password hashing (pwdlib + Argon2) and JWT access tokens (PyJWT)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from ..config import get_settings

ALGORITHM = "HS256"

# OWASP's recommended Argon2id settings (19 MiB, 2 passes, 1 lane). pwdlib's
# default (64 MiB, 3 passes, 4 lanes) took ~1.4 s per login on Render's small
# CPU. Older hashes still verify; login re-hashes them with these settings.
password_hash = PasswordHash((Argon2Hasher(memory_cost=19_456, time_cost=2, parallelism=1),))

# Verifying against this when no user was found costs about the same Argon2
# time as a real check, so login timing does not reveal which emails exist.
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-password-used-for-timing-only")


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def verify_and_update_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    """Check a password. Also returns a new hash when the stored one uses older settings."""
    return password_hash.verify_and_update(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT whose "sub" is the user id and "exp" is a UTC expiry."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    return jwt.encode({"sub": subject, "exp": expire}, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Return the user id in a valid token. Raises jwt.InvalidTokenError otherwise."""
    payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise jwt.InvalidTokenError("Token has no valid subject.") from exc
