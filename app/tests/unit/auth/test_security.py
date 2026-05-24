from uuid import uuid4

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

pytestmark = pytest.mark.unit


def test_password_hashing_roundtrip() -> None:
    plain = "Secure1@pass"
    hashed = hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$2b$")
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)


def test_password_hashing_accepts_production_password() -> None:
    plain = "Macarena1052.*"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed)


def test_jwt_create_and_decode() -> None:
    user_id = uuid4()
    token = create_access_token(user_id, extra_claims={"role": "attendee"})
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "attendee"
    assert payload["type"] == "access"


def test_jwt_invalid_token_raises() -> None:
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token("not-a-valid-token")
