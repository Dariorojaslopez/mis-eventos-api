from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.tests.constants import VALID_PASSWORD
from app.tests.factories.event_factory import build_event_payload
from app.tests.factories.user_factory import build_register_payload
from app.tests.utils.assertions import assert_error, assert_status

pytestmark = pytest.mark.integration

NOW = datetime.now(UTC)


async def _auth_headers(async_client: AsyncClient, email: str) -> dict[str, str]:
    await async_client.post("/api/v1/auth/register", json=build_register_payload(email=email))
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": VALID_PASSWORD},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_event_success(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    body = assert_status(
        await async_client.post(
            "/api/v1/events",
            json=build_event_payload(),
            headers=auth_headers,
        ),
        201,
    )
    assert body["available_slots"] == body["max_capacity"]


@pytest.mark.asyncio
async def test_create_event_invalid_dates(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await async_client.post(
        "/api/v1/events",
        json={
            **build_event_payload(),
            "start_date": (NOW + timedelta(days=2)).isoformat().replace("+00:00", "Z"),
            "end_date": NOW.isoformat().replace("+00:00", "Z"),
        },
        headers=auth_headers,
    )
    assert_error(response, status_code=422, code="validation_error")


@pytest.mark.asyncio
async def test_create_event_invalid_capacity(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await async_client.post(
        "/api/v1/events",
        json=build_event_payload(max_capacity=0),
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unauthorized_update(
    async_client: AsyncClient,
    unique_email: str,
) -> None:
    owner_headers = await _auth_headers(async_client, unique_email)
    created = assert_status(
        await async_client.post(
            "/api/v1/events",
            json=build_event_payload(),
            headers=owner_headers,
        ),
        201,
    )
    other_headers = await _auth_headers(async_client, f"other_{unique_email}")
    assert_error(
        await async_client.put(
            f"/api/v1/events/{created['id']}",
            json={"title": "Hack"},
            headers=other_headers,
        ),
        status_code=403,
        code="forbidden",
    )


@pytest.mark.asyncio
async def test_update_finished_event(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = assert_status(
        await async_client.post(
            "/api/v1/events",
            json=build_event_payload(status="published"),
            headers=auth_headers,
        ),
        201,
    )
    event_id = created["id"]
    await async_client.put(
        f"/api/v1/events/{event_id}",
        json={"status": "finished"},
        headers=auth_headers,
    )
    assert_error(
        await async_client.put(
            f"/api/v1/events/{event_id}",
            json={"title": "Bloqueado"},
            headers=auth_headers,
        ),
        status_code=409,
        code="event_finished",
    )


@pytest.mark.asyncio
async def test_event_filters_and_pagination(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    await async_client.post(
        "/api/v1/events",
        json=build_event_payload(title="Python Summit", status="published"),
        headers=auth_headers,
    )
    listing = assert_status(
        await async_client.get(
            "/api/v1/events",
            params={"search": "Python", "status": "published", "page": 1, "limit": 5},
        ),
        200,
    )
    assert listing["total"] >= 1
    assert listing["page"] == 1
    assert listing["limit"] == 5
    assert len(listing["items"]) >= 1


@pytest.mark.asyncio
async def test_create_event_requires_auth(async_client: AsyncClient) -> None:
    assert_error(
        await async_client.post("/api/v1/events", json=build_event_payload()),
        status_code=401,
        code="unauthorized",
    )


@pytest.mark.asyncio
async def test_admin_can_update_any_event(
    async_client: AsyncClient,
    unique_email: str,
    async_db_session: AsyncSession,
) -> None:
    owner_headers = await _auth_headers(async_client, unique_email)
    created = assert_status(
        await async_client.post(
            "/api/v1/events",
            json=build_event_payload(),
            headers=owner_headers,
        ),
        201,
    )
    admin_email = f"admin_{unique_email}"
    admin_headers = await _auth_headers(async_client, admin_email)
    me = assert_status(await async_client.get("/api/v1/auth/me", headers=admin_headers), 200)
    admin_user = await async_db_session.get(User, UUID(me["id"]))
    assert admin_user is not None
    admin_user.role = UserRole.ADMIN
    await async_db_session.flush()

    updated = assert_status(
        await async_client.put(
            f"/api/v1/events/{created['id']}",
            json={"title": "Admin update"},
            headers=admin_headers,
        ),
        200,
    )
    assert updated["title"] == "Admin update"
