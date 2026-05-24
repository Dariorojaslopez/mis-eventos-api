import pytest
from httpx import AsyncClient

from app.tests.constants import VALID_PASSWORD
from app.tests.factories.event_factory import build_event_payload
from app.tests.factories.session_factory import build_session_payload
from app.tests.factories.user_factory import build_register_payload
from app.tests.utils.assertions import assert_status

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_full_auth_flow(async_client: AsyncClient, unique_email: str) -> None:
    payload = build_register_payload(email=unique_email)
    user = assert_status(await async_client.post("/api/v1/auth/register", json=payload), 201)
    token = assert_status(
        await async_client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": VALID_PASSWORD},
        ),
        200,
    )["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = assert_status(await async_client.get("/api/v1/auth/me", headers=headers), 200)
    assert me["id"] == user["id"]


@pytest.mark.asyncio
async def test_create_event_flow(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    event = assert_status(
        await async_client.post(
            "/api/v1/events",
            json=build_event_payload(status="published"),
            headers=auth_headers,
        ),
        201,
    )
    listed = assert_status(
        await async_client.get("/api/v1/events", params={"search": "FastAPI"}), 200
    )
    assert any(item["id"] == event["id"] for item in listed["items"])
    assert_status(await async_client.get(f"/api/v1/events/{event['id']}"), 200)


@pytest.mark.asyncio
async def test_create_session_flow(
    async_client: AsyncClient,
    test_event: dict,
) -> None:
    event_id = test_event["id"]
    session = assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/sessions",
            json=build_session_payload(),
            headers=test_event["headers"],
        ),
        201,
    )
    sessions = assert_status(
        await async_client.get(f"/api/v1/events/{event_id}/sessions"),
        200,
    )
    assert any(item["id"] == session["id"] for item in sessions)
    assert_status(await async_client.get(f"/api/v1/sessions/{session['id']}"), 200)


@pytest.mark.asyncio
async def test_registration_flow(
    async_client: AsyncClient,
    test_session: dict,
    attendee_auth_headers: dict[str, str],
) -> None:
    event_id = test_session["event"]["id"]
    registration = assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/register",
            headers=attendee_auth_headers,
        ),
        201,
    )
    my_events = assert_status(
        await async_client.get("/api/v1/me/events", headers=attendee_auth_headers), 200
    )
    assert any(item["registration_id"] == registration["id"] for item in my_events)
    attendees = assert_status(
        await async_client.get(
            f"/api/v1/events/{event_id}/attendees",
            headers=test_session["event"]["headers"],
        ),
        200,
    )
    assert len(attendees) == 1
