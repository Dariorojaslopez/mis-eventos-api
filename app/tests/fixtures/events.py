import pytest
from httpx import AsyncClient

from app.tests.factories.event_factory import build_event_payload


@pytest.fixture
async def test_event(async_client: AsyncClient, auth_headers: dict[str, str]) -> dict:
    response = await async_client.post(
        "/api/v1/events",
        json=build_event_payload(status="published"),
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    return {
        "id": data["id"],
        "data": data,
        "headers": auth_headers,
    }
