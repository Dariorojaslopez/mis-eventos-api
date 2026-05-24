"""Política de contraseñas para registro de usuarios."""

import re

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

# Caracteres especiales permitidos: ! @ # $ % ^ & * . _ -
PASSWORD_SPECIAL_CHARS = "!@#$%^&*._-"
_PASSWORD_SPECIAL_CLASS = re.escape(PASSWORD_SPECIAL_CHARS)

PASSWORD_PATTERN = re.compile(
    rf"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[{_PASSWORD_SPECIAL_CLASS}])"
    rf"[A-Za-z\d{_PASSWORD_SPECIAL_CLASS}]{{{PASSWORD_MIN_LENGTH},}}$"
)

PASSWORD_POLICY_MESSAGE = (
    "Password must include uppercase, lowercase, a number, "
    f"and a special character ({PASSWORD_SPECIAL_CHARS})"
)


def validate_password_strength(password: str) -> str:
    """Valida fortaleza de contraseña; devuelve el valor si es válido."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if not PASSWORD_PATTERN.match(password):
        raise ValueError(PASSWORD_POLICY_MESSAGE)
    return password
