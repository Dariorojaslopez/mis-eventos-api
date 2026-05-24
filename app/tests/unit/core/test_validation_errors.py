import pytest

from app.utils.sensitive_data import REDACTED, is_sensitive_field_name, redact_mapping
from app.utils.validation_errors import format_field_path, sanitize_validation_errors

pytestmark = pytest.mark.unit


def test_format_field_path_skips_body_prefix() -> None:
    assert format_field_path(("body", "password")) == "password"
    assert format_field_path(("body", "items", 0, "name")) == "items[0].name"


def test_is_sensitive_field_name() -> None:
    assert is_sensitive_field_name("password")
    assert is_sensitive_field_name("access_token")
    assert not is_sensitive_field_name("email")


def test_redact_mapping_masks_sensitive_keys() -> None:
    result = redact_mapping(
        {
            "email": "user@example.com",
            "password": "Secret123!",
            "nested": {"api_key": "sk-test"},
        }
    )
    assert result["email"] == "user@example.com"
    assert result["password"] == REDACTED
    assert result["nested"]["api_key"] == REDACTED


def test_sanitize_validation_errors_omits_input_and_sensitive_values() -> None:
    errors = [
        {
            "type": "value_error",
            "loc": ("body", "password"),
            "msg": "Value error, Password must include uppercase, lowercase, a number, and a special character (!@#$%^&*._-)",
            "input": "SuperSecret123!",
            "url": "https://errors.pydantic.dev/2.12/v/value_error",
        },
        {
            "type": "string_type",
            "loc": ("body", "email"),
            "msg": "Input should be a valid string",
            "input": "bad-email",
        },
    ]

    sanitized = sanitize_validation_errors(errors)

    assert sanitized == [
        {
            "field": "password",
            "message": "Password must include uppercase, lowercase, a number, and a special character (!@#$%^&*._-)",
        },
        {"field": "email", "message": "Invalid email format"},
    ]
    assert "input" not in str(sanitized)
    assert "SuperSecret123!" not in str(sanitized)
