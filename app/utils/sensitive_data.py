"""Utilidades para redactar datos sensibles en logs y respuestas."""

import re
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "password",
        "hashed_password",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "openai_api_key",
        "credentials",
    }
)

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwd|pwd|secret|token|authorization|api[_-]?key|credential|hashed)",
    re.IGNORECASE,
)


def is_sensitive_field_name(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    if normalized in SENSITIVE_FIELD_NAMES:
        return True
    return bool(_SENSITIVE_KEY_PATTERN.search(normalized))


def redact_value(key: str, value: Any) -> Any:
    """Redacta valores sensibles según el nombre de la clave."""
    if is_sensitive_field_name(key):
        return REDACTED
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_mapping(item) if isinstance(item, dict) else item for item in value]
    return value


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    return {key: redact_value(key, value) for key, value in data.items()}


def redact_sensitive_event(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Processor structlog: redacta claves sensibles en cada evento de log."""
    return redact_mapping(event_dict)
