from uuid import uuid4

from app.tests.constants import VALID_PASSWORD


def build_register_payload(
    *,
    email: str | None = None,
    full_name: str = "Test User",
    password: str = VALID_PASSWORD,
) -> dict[str, str]:
    return {
        "email": email or f"user_{uuid4().hex[:8]}@example.com",
        "full_name": full_name,
        "password": password,
    }
