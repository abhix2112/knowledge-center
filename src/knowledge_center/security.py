"""Password hashing and JWT tokens."""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from knowledge_center.config import settings

ALGORITHM = "HS256"

password_hasher = PasswordHash.recommended()  # argon2

# Used when a login email doesn't exist, so that "unknown email" takes as long
# as "wrong password". Otherwise response time reveals which emails exist.
DUMMY_HASH = password_hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Check a password. Pass None when the user doesn't exist."""
    if password_hash is None:
        password_hasher.verify(password, DUMMY_HASH)  # same work, result ignored
        return False
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def read_access_token(token: str) -> str | None:
    """Return the user id inside a valid token, or None if invalid or expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    return payload.get("sub")
