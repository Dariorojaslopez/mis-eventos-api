from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.tests.factories.event_factory import NOW, build_event_payload
from app.tests.factories.session_factory import build_session_payload
from app.tests.utils.assertions import assert_error, assert_status

pytestmark = pytest.mark.integration

EVENT_START = NOW + timedelta(days=14)
EVENT_END = EVENT_START + timedelta(hours=9)


async def _published_event(async_client: AsyncClient, auth_headers: dict[str, str]) -> str:
    body = assert_status(
        await async_client.post(
            "/api/v1/events",
            json=build_event_payload(
                start_date=EVENT_START.isoformat().replace("+00:00", "Z"),
                end_date=EVENT_END.isoformat().replace("+00:00", "Z"),
                status="published",
            ),
            headers=auth_headers,
        ),
        201,
    )
    return body["id"]


@pytest.mark.asyncio
async def test_create_session_success(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    event_id = await _published_event(async_client, auth_headers)
    body = assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/sessions",
            json=build_session_payload(),
            headers=auth_headers,
        ),
        201,
    )
    assert body["available_slots"] == body["capacity"]


@pytest.mark.asyncio
async def test_speaker_overlap_conflict(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    event_id = await _published_event(async_client, auth_headers)
    assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/sessions",
            json=build_session_payload(),
            headers=auth_headers,
        ),
        201,
    )
    conflict_start = EVENT_START + timedelta(hours=1, minutes=30)
    conflict_end = conflict_start + timedelta(hours=1)
    assert_error(
        await async_client.post(
            f"/api/v1/events/{event_id}/sessions",
            json=build_session_payload(
                title="Overlap",
                start_time=conflict_start.isoformat().replace("+00:00", "Z"),
                end_time=conflict_end.isoformat().replace("+00:00", "Z"),
            ),
            headers=auth_headers,
        ),
        status_code=409,
        code="session_speaker_conflict",
    )


@pytest.mark.asyncio
async def test_room_overlap_conflict(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    event_id = await _published_event(async_client, auth_headers)
    assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/sessions",
            json=build_session_payload(speaker_name="María Gómez"),
            headers=auth_headers,
        ),
        201,
    )
    conflict_start = EVENT_START + timedelta(hours=1, minutes=30)
    conflict_end = conflict_start + timedelta(hours=1)
    assert_error(
        await async_client.post(
            f"/api/v1/events/{event_id}/sessions",
            json=build_session_payload(
                speaker_name="Pedro Ruiz",
                start_time=conflict_start.isoformat().replace("+00:00", "Z"),
                end_time=conflict_end.isoformat().replace("+00:00", "Z"),
            ),
            headers=auth_headers,
        ),
        status_code=409,
        code="session_room_conflict",
    )


@pytest.mark.asyncio
async def test_session_outside_event_range(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    event_id = await _published_event(async_client, auth_headers)
    outside_start = EVENT_END + timedelta(hours=1)
    outside_end = outside_start + timedelta(hours=1)
    assert_error(
        await async_client.post(
            f"/api/v1/events/{event_id}/sessions",
            json=build_session_payload(
                start_time=outside_start.isoformat().replace("+00:00", "Z"),
                end_time=outside_end.isoformat().replace("+00:00", "Z"),
            ),
            headers=auth_headers,
        ),
        status_code=400,
        code="session_outside_event_window",
    )


@pytest.mark.asyncio
async def test_session_invalid_capacity(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    event_id = await _published_event(async_client, auth_headers)
    response = await async_client.post(
        f"/api/v1/events/{event_id}/sessions",
        json=build_session_payload(capacity=0),
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unauthorized_session_update(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    attendee_auth_headers: dict[str, str],
) -> None:
    event_id = await _published_event(async_client, auth_headers)
    created = assert_status(
        await async_client.post(
            f"/api/v1/events/{event_id}/sessions",
            json=build_session_payload(),
            headers=auth_headers,
        ),
        201,
    )
    assert_error(
        await async_client.put(
            f"/api/v1/sessions/{created['id']}",
            json={"title": "Hack"},
            headers=attendee_auth_headers,
        ),
        status_code=403,
        code="forbidden",
    )
