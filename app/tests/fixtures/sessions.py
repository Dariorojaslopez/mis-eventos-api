import pytest
from httpx import AsyncClient

from app.tests.factories.session_factory import build_session_payload


@pytest.fixture
async def test_session(async_client: AsyncClient, test_event: dict) -> dict:
    event_id = test_event["id"]
    response = await async_client.post(
        f"/api/v1/events/{event_id}/sessions",
        json=build_session_payload(),
        headers=test_event["headers"],
    )
    assert response.status_code == 201
    return {
        "id": response.json()["id"],
        "data": response.json(),
        "event": test_event,
    }
