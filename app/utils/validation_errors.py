"""Formateo seguro de errores de validación Pydantic/FastAPI."""

from typing import Any

from app.utils.sensitive_data import is_sensitive_field_name

_SKIP_LOC_PREFIXES = frozenset({"body", "query", "path", "header", "cookie"})


def format_field_path(location: tuple[Any, ...]) -> str:
    """Convierte ('body', 'user', 'email') en 'user.email'."""
    segments: list[str] = []
    for part in location:
        if isinstance(part, str) and part in _SKIP_LOC_PREFIXES:
            continue
        if isinstance(part, int):
            if segments:
                segments[-1] = f"{segments[-1]}[{part}]"
            else:
                segments.append(f"[{part}]")
        else:
            segments.append(str(part))
    return ".".join(segments) if segments else "request"


def _clean_message(raw_message: str) -> str:
    message = raw_message.strip()
    if message.startswith("Value error, "):
        message = message[len("Value error, ") :]
    return message


def _message_for_field(field: str, error: dict[str, Any]) -> str:
    error_type = str(error.get("type", ""))
    raw_message = _clean_message(str(error.get("msg", "Invalid value")))

    if field == "password" or field.endswith(".password"):
        if error_type == "string_too_short":
            return "Password must be at least 8 characters"
        if error_type == "string_too_long":
            return "Password is too long"
        if "Password must" in raw_message:
            return raw_message
        return "Password format invalid"

    if is_sensitive_field_name(field.split(".")[-1]):
        return "Invalid value"

    if error_type == "missing":
        return f"{field} is required"
    if error_type in {"value_error", "assertion_error"}:
        return raw_message
    if error_type == "string_too_short":
        return f"{field} is too short"
    if error_type == "string_too_long":
        return f"{field} is too long"
    if error_type in {"value_error.email", "string_type"}:
        return "Invalid email format" if "email" in field else raw_message

    return raw_message if raw_message else "Invalid value"


def sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Convierte errores Pydantic en respuesta enterprise sin exponer:
    input, ctx, url ni valores sensibles.
    """
    sanitized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for error in errors:
        field = format_field_path(tuple(error.get("loc", ())))
        message = _message_for_field(field, error)
        key = (field, message)
        if key in seen:
            continue
        seen.add(key)
        sanitized.append({"field": field, "message": message})

    return sanitized
