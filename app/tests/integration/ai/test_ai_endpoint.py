from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.dependencies.ai import clear_ai_service_cache, get_ai_service
from app.main import app
from app.providers.ai.errors import AIProviderError
from app.providers.ai.mock import MockAIProvider
from app.providers.ai.openai import OpenAIProvider
from app.services.ai_rate_limiter import AIRateLimiter
from app.services.ai_service import AIService
from app.tests.factories.ai_factory import generate_event_description_payload
from app.tests.utils.assertions import assert_error

pytestmark = pytest.mark.integration

AI_ENDPOINT = "/api/v1/ai/generate-event-description"


@pytest.mark.asyncio
async def test_generate_event_description_success(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await async_client.post(
        AI_ENDPOINT,
        json=generate_event_description_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "FastAPI Summit 2026"
    assert "generated_description" in body
    assert len(body["generated_description"]) >= 20
    assert "FastAPI Summit 2026" in body["generated_description"]


@pytest.mark.asyncio
async def test_generate_event_description_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.post(
        AI_ENDPOINT,
        json=generate_event_description_payload(),
    )

    assert_error(response, status_code=401, code="unauthorized")


@pytest.mark.asyncio
async def test_generate_event_description_validation_error(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await async_client.post(
        AI_ENDPOINT,
        json={"title": "ab"},
        headers=auth_headers,
    )

    assert_error(response, status_code=422, code="validation_error")


@pytest.mark.asyncio
async def test_generate_event_description_rate_limit(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    limiter = AIRateLimiter(max_requests=2, window_seconds=60)
    service = AIService(MockAIProvider(), rate_limiter=limiter)
    app.dependency_overrides[get_ai_service] = lambda: service

    try:
        for _ in range(2):
            ok = await async_client.post(
                AI_ENDPOINT,
                json=generate_event_description_payload(title="Evento Rate"),
                headers=auth_headers,
            )
            assert ok.status_code == 200

        blocked = await async_client.post(
            AI_ENDPOINT,
            json=generate_event_description_payload(title="Evento Rate 3"),
            headers=auth_headers,
        )
        assert_error(blocked, status_code=429, code="ai_rate_limit_exceeded")
    finally:
        app.dependency_overrides.pop(get_ai_service, None)
        clear_ai_service_cache()


@pytest.mark.asyncio
async def test_generate_event_description_openai_fallback(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    openai_provider = OpenAIProvider(api_key="test-key", max_retries=1)
    openai_provider.generate_event_description = AsyncMock(  # type: ignore[method-assign]
        side_effect=AIProviderError("simulated openai outage", provider="openai")
    )
    service = AIService(
        openai_provider,
        fallback_provider=MockAIProvider(),
        rate_limiter=AIRateLimiter(max_requests=50, window_seconds=60),
    )
    app.dependency_overrides[get_ai_service] = lambda: service

    try:
        response = await async_client.post(
            AI_ENDPOINT,
            json=generate_event_description_payload(),
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "generated_description" in response.json()
    finally:
        app.dependency_overrides.pop(get_ai_service, None)
        clear_ai_service_cache()
