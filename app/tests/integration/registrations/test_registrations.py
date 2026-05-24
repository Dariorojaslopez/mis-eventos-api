from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.tests.constants import VALID_PASSWORD
from app.tests.factories.event_factory import NOW, build_event_payload
from app.tests.factories.session_factory import build_session_payload
from app.tests.factories.user_factory import build_register_payload
from app.tests.utils.assertions import assert_error, assert_status

pytestmark = pytest.mark.integration

EVENT_START = NOW + timedelta(days=14)
EVENT_END = EVENT_START + timedelta(hours=9)


async def _event_with_session(
    async_client: AsyncClient, auth_headers: dict[str, str], **event_kw
) -> str:
    event = assert_status(
        await async_client.post(
            "/api/v1/events",
            json=build_event_payload(
                start_date=EVENT_START.isoformat().replace("+00:00", "Z"),
                end_date=EVENT_END.isoformat().replace("+00:00", "Z"),
                status="published",
                **event_kw,
            ),
            headers=auth_headers,
        ),
        201,
    )
    event_id = event["id"]
    assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/sessions",
            json=build_session_payload(),
            headers=auth_headers,
        ),
        201,
    )
    return event_id


@pytest.mark.asyncio
async def test_register_success(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    attendee_auth_headers: dict[str, str],
) -> None:
    event_id = await _event_with_session(async_client, auth_headers)
    body = assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/register", headers=attendee_auth_headers
        ),
        201,
    )
    assert body["status"] == "registered"


@pytest.mark.asyncio
async def test_duplicate_registration(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    attendee_auth_headers: dict[str, str],
) -> None:
    event_id = await _event_with_session(async_client, auth_headers)
    assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/register", headers=attendee_auth_headers
        ),
        201,
    )
    assert_error(
        await async_client.post(
            f"/api/v1/events/{event_id}/register", headers=attendee_auth_headers
        ),
        status_code=409,
        code="conflict",
    )


@pytest.mark.asyncio
async def test_no_available_slots(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    attendee_auth_headers: dict[str, str],
    unique_email: str,
) -> None:
    event_id = await _event_with_session(async_client, auth_headers, max_capacity=1)
    assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/register", headers=attendee_auth_headers
        ),
        201,
    )
    guest2_email = f"guest2_{unique_email}"
    await async_client.post(
        "/api/v1/auth/register", json=build_register_payload(email=guest2_email)
    )
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": guest2_email, "password": VALID_PASSWORD},
    )
    guest2_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert_error(
        await async_client.post(f"/api/v1/events/{event_id}/register", headers=guest2_headers),
        status_code=409,
        code="registration_denied_capacity",
    )


@pytest.mark.asyncio
async def test_register_cancelled_event(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    attendee_auth_headers: dict[str, str],
) -> None:
    event_id = await _event_with_session(async_client, auth_headers)
    await async_client.delete(f"/api/v1/events/{event_id}", headers=auth_headers)
    assert_error(
        await async_client.post(
            f"/api/v1/events/{event_id}/register", headers=attendee_auth_headers
        ),
        status_code=409,
        code="event_not_registerable",
    )


@pytest.mark.asyncio
async def test_register_finished_event(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    attendee_auth_headers: dict[str, str],
) -> None:
    event_id = await _event_with_session(async_client, auth_headers)
    await async_client.put(
        f"/api/v1/events/{event_id}",
        json={"status": "finished"},
        headers=auth_headers,
    )
    assert_error(
        await async_client.post(
            f"/api/v1/events/{event_id}/register", headers=attendee_auth_headers
        ),
        status_code=409,
        code="event_not_registerable",
    )


@pytest.mark.asyncio
async def test_organizer_self_register_restriction(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    event_id = await _event_with_session(async_client, auth_headers)
    assert_error(
        await async_client.post(f"/api/v1/events/{event_id}/register", headers=auth_headers),
        status_code=409,
        code="organizer_self_registration",
    )


@pytest.mark.asyncio
async def test_cancel_registration_and_slots(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    attendee_auth_headers: dict[str, str],
) -> None:
    event_id = await _event_with_session(async_client, auth_headers, max_capacity=10)
    before = assert_status(await async_client.get(f"/api/v1/events/{event_id}"), 200)

    assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/register", headers=attendee_auth_headers
        ),
        201,
    )
    after_register = assert_status(await async_client.get(f"/api/v1/events/{event_id}"), 200)
    assert after_register["available_slots"] == before["available_slots"] - 1

    cancel = assert_status(
        await async_client.delete(
            f"/api/v1/events/{event_id}/register", headers=attendee_auth_headers
        ),
        200,
    )
    assert cancel["status"] == "cancelled"

    after_cancel = assert_status(await async_client.get(f"/api/v1/events/{event_id}"), 200)
    assert after_cancel["available_slots"] == before["available_slots"]
