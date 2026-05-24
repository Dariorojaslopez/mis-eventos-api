import pytest
from httpx import AsyncClient


@pytest.fixture
async def test_registration(
    async_client: AsyncClient,
    test_event: dict,
    test_session: dict,
    attendee_auth_headers: dict[str, str],
) -> dict:
    event_id = test_event["id"]
    response = await async_client.post(
        f"/api/v1/events/{event_id}/register",
        headers=attendee_auth_headers,
    )
    assert response.status_code == 201
    return {
        "id": response.json()["id"],
        "data": response.json(),
        "event": test_event,
        "headers": attendee_auth_headers,
    }
