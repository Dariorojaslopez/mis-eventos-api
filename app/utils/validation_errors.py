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


def _is_password_field(field: str) -> bool:
    return field == "password" or field.endswith(".password")


def _is_email_field(field: str) -> bool:
    leaf = field.rsplit(".", 1)[-1]
    return leaf == "email"


def _password_message(error_type: str, raw_message: str) -> str:
    if error_type == "string_too_short":
        return "Password must be at least 8 characters"
    if error_type == "string_too_long":
        return "Password is too long"
    if "Password must" in raw_message:
        return raw_message
    return "Password format invalid"


def _message_for_field(field: str, error: dict[str, Any]) -> str:
    error_type = str(error.get("type", ""))
    raw_message = _clean_message(str(error.get("msg", "Invalid value")))

    if _is_password_field(field):
        return _password_message(error_type, raw_message)

    leaf_field = field.rsplit(".", 1)[-1]
    if is_sensitive_field_name(leaf_field):
        return "Invalid value"

    type_messages = {
        "missing": f"{field} is required",
        "string_too_short": f"{field} is too short",
        "string_too_long": f"{field} is too long",
    }
    if error_type in type_messages:
        return type_messages[error_type]

    email_error_types = {"value_error.email", "string_type"}
    if _is_email_field(field) and (
        error_type in email_error_types or error_type.startswith("value_error")
    ):
        return "Invalid email format"

    if error_type in {"value_error", "assertion_error"}:
        return raw_message

    return raw_message or "Invalid value"


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
