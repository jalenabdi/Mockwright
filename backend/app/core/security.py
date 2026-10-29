"""Security helpers: password verification and JWT access tokens.

Follows the current FastAPI "OAuth2 with Password (and hashing), Bearer
with JWT tokens" tutorial: PyJWT for signing, pwdlib with Argon2 for
hashing. Does not use python-jose or passlib.

Password hashing for new accounts (e.g. a hash_password() used by
registration) is not added here - it isn't needed by the login endpoint,
and is the registration endpoint's responsibility to add if it doesn't
already have one.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

ALGORITHM = "HS256"

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Add it to your .env file before starting the app."
    )

_expire_minutes_raw = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(_expire_minutes_raw)
except ValueError as exc:
    raise RuntimeError(
        f"ACCESS_TOKEN_EXPIRE_MINUTES must be an integer, got {_expire_minutes_raw!r}."
    ) from exc

password_hash = PasswordHash.recommended()

# A hash of a password nobody will ever submit. Verifying against this when
# no user was found costs roughly the same Argon2 time as a real check, so
# a login attempt's response time doesn't reveal whether the email exists.
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-password-used-for-timing-only")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a pwdlib/Argon2 hash."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    "sub" is `subject` (the user id, as a string) and "exp" is a
    timezone-aware UTC expiry, ACCESS_TOKEN_EXPIRE_MINUTES from now unless
    `expires_delta` is given.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
