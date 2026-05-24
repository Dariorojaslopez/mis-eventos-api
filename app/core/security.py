"""
Seguridad de autenticación: hashing de contraseñas y JWT.

Transporte (HTTPS):
    El frontend (Vercel) y el backend (Render) se comunican exclusivamente vía HTTPS.
    TLS cifra el tráfico en tránsito, incluidas las contraseñas en login/register.
    No se requiere cifrado manual adicional (AES/RSA) en el cliente.

Almacenamiento:
    Las contraseñas se persisten únicamente como hashes bcrypt (salting automático).
    Nunca se guarda plaintext ni se devuelven hashes en respuestas de la API.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt: salting automático vía gensalt(); verify constant-time con checkpw
_BCRYPT_ROUNDS = 12


def hash_password(plain_password: str) -> str:
    """Genera hash bcrypt; nunca almacenar el valor en plaintext."""
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica contraseña contra hash almacenado de forma segura."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: UUID | str,
    *,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    if payload.get("type") != "access":
        raise ValueError("Invalid token type")

    return payload
