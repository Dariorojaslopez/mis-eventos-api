import html
import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_HTML_TAG = re.compile(r"<[^>]+>")


def sanitize_plain_text(value: str) -> str:
    """Limpia texto de usuario: sin tags HTML ni caracteres de control."""
    cleaned = html.unescape(value)
    cleaned = _HTML_TAG.sub("", cleaned)
    cleaned = _CONTROL_CHARS.sub("", cleaned)
    return cleaned.strip()
