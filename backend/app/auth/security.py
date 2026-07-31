"""Autenticação local: Argon2id, JWT curto, refresh rotativo (seção 20.1)."""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()  # argon2id por padrão
_settings = get_settings()

ROLES = ["ADMIN", "FACTORY_MANAGER", "APPROVER", "DEVELOPER", "AUDITOR", "VIEWER"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _create_token(subject: str, role: str, token_type: str, expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)


def create_access_token(subject: str, role: str) -> str:
    return _create_token(subject, role, "access", _settings.access_token_expire_minutes)


def create_refresh_token(subject: str, role: str) -> str:
    return _create_token(subject, role, "refresh", _settings.refresh_token_expire_minutes)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _settings.jwt_secret_key, algorithms=[_settings.jwt_algorithm])
