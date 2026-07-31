"""Testes de autenticação (seção 20.1)."""
from app.auth.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_argon2_hash_roundtrip():
    hashed = hash_password("s3nha")
    assert hashed.startswith("$argon2id$")
    assert verify_password("s3nha", hashed)
    assert not verify_password("errada", hashed)


def test_jwt_roundtrip():
    token = create_access_token("admin", "ADMIN")
    payload = decode_token(token)
    assert payload["sub"] == "admin"
    assert payload["role"] == "ADMIN"
    assert payload["type"] == "access"
