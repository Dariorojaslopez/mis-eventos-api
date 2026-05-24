import pytest
from httpx import AsyncClient

from app.tests.factories.ai_factory import generate_event_description_payload

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_ai_generate_description_flow(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Flujo E2E: usuario autenticado genera descripción para un evento."""
    response = await async_client.post(
        "/api/v1/ai/generate-event-description",
        json=generate_event_description_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "FastAPI Summit 2026"
    assert isinstance(data["generated_description"], str)
    assert len(data["generated_description"]) > 50
