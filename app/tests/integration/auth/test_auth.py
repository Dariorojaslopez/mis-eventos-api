import pytest
from httpx import AsyncClient

from app.tests.constants import INVALID_PASSWORD, VALID_PASSWORD
from app.tests.factories.user_factory import build_register_payload
from app.tests.utils.assertions import assert_error, assert_status

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient, unique_email: str) -> None:
    payload = build_register_payload(email=unique_email)
    body = assert_status(await async_client.post("/api/v1/auth/register", json=payload), 201)
    assert body["email"] == unique_email
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient, unique_email: str) -> None:
    payload = build_register_payload(email=unique_email)
    assert_status(await async_client.post("/api/v1/auth/register", json=payload), 201)
    assert_error(
        await async_client.post("/api/v1/auth/register", json=payload),
        status_code=409,
        code="conflict",
    )


@pytest.mark.asyncio
async def test_register_invalid_password(async_client: AsyncClient, unique_email: str) -> None:
    payload = build_register_payload(email=unique_email, password=INVALID_PASSWORD)
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, unique_email: str) -> None:
    payload = build_register_payload(email=unique_email)
    await async_client.post("/api/v1/auth/register", json=payload)
    body = assert_status(
        await async_client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": VALID_PASSWORD},
        ),
        200,
    )
    assert body["token_type"] == "bearer"
    assert "access_token" in body


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient, unique_email: str) -> None:
    payload = build_register_payload(email=unique_email)
    await async_client.post("/api/v1/auth/register", json=payload)
    assert_error(
        await async_client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": "Wrong1@pass"},
        ),
        status_code=401,
        code="unauthorized",
    )


@pytest.mark.asyncio
async def test_invalid_token(async_client: AsyncClient) -> None:
    assert_error(
        await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        ),
        status_code=401,
        code="unauthorized",
    )


@pytest.mark.asyncio
async def test_unauthorized_access(async_client: AsyncClient) -> None:
    assert_error(
        await async_client.get("/api/v1/auth/me"),
        status_code=401,
        code="unauthorized",
    )
