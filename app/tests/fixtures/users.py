from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.tests.constants import VALID_PASSWORD
from app.tests.factories.user_factory import build_register_payload


@pytest.fixture
def unique_email() -> str:
    return f"user_{uuid4().hex[:8]}@example.com"


@pytest.fixture
async def test_user(async_client: AsyncClient, unique_email: str) -> dict:
    payload = build_register_payload(email=unique_email)
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
async def auth_headers(async_client: AsyncClient, unique_email: str) -> dict[str, str]:
    payload = build_register_payload(email=unique_email, full_name="Organizer User")
    await async_client.post("/api/v1/auth/register", json=payload)
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": VALID_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def attendee_auth_headers(async_client: AsyncClient, unique_email: str) -> dict[str, str]:
    email = f"attendee_{unique_email}"
    payload = build_register_payload(email=email, full_name="Attendee User")
    await async_client.post("/api/v1/auth/register", json=payload)
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
