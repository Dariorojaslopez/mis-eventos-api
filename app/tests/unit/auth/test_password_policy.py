import pytest

from app.utils.password_policy import (
    PASSWORD_POLICY_MESSAGE,
    validate_password_strength,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "password",
    [
        "Macarena2026!",
        "PasswordSecure_2026",
        "Dario.Rojas#2026",
        "Secure1@pass",
    ],
)
def test_validate_password_accepts_strong_passwords(password: str) -> None:
    assert validate_password_strength(password) == password


@pytest.mark.parametrize(
    "password",
    [
        "weak",
        "alllowercase1!",
        "ALLUPPERCASE1!",
        "NoDigitsHere!",
        "NoSpecialChar1",
        "Short1!",
    ],
)
def test_validate_password_rejects_weak_passwords(password: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        validate_password_strength(password)
    assert str(exc_info.value) in {
        PASSWORD_POLICY_MESSAGE,
        "Password must be at least 8 characters",
    }
