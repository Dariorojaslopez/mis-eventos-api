from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.providers.ai.errors import AIProviderError
from app.providers.ai.mock import MockAIProvider
from app.providers.ai.openai import OpenAIProvider
from app.schemas.ai import GenerateEventDescriptionRequest
from app.services.ai_rate_limiter import AIRateLimiter
from app.services.ai_service import AIService

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_ai_service_uses_mock_provider() -> None:
    service = AIService(
        MockAIProvider(), rate_limiter=AIRateLimiter(max_requests=50, window_seconds=60)
    )
    payload = GenerateEventDescriptionRequest(title="Summit 2026")

    result = await service.generate_event_description(payload, user_id=uuid4())

    assert result.title == "Summit 2026"
    assert len(result.generated_description) >= 20


@pytest.mark.asyncio
async def test_ai_service_fallback_to_mock_on_openai_failure() -> None:
    openai_provider = OpenAIProvider(api_key="test-key", max_retries=1)
    openai_provider.generate_event_description = AsyncMock(  # type: ignore[method-assign]
        side_effect=AIProviderError("openai down", provider="openai")
    )

    service = AIService(
        openai_provider,
        fallback_provider=MockAIProvider(),
        rate_limiter=AIRateLimiter(max_requests=50, window_seconds=60),
    )
    payload = GenerateEventDescriptionRequest(title="FastAPI Summit 2026", location="Bogotá")

    result = await service.generate_event_description(payload, user_id=uuid4())

    assert "FastAPI Summit 2026" in result.generated_description
    assert "Bogotá" in result.generated_description


@pytest.mark.asyncio
async def test_ai_service_rate_limit_raises() -> None:
    limiter = AIRateLimiter(max_requests=1, window_seconds=60)
    service = AIService(MockAIProvider(), rate_limiter=limiter)
    payload = GenerateEventDescriptionRequest(title="Evento A")
    user_id = uuid4()

    await service.generate_event_description(payload, user_id=user_id)

    from app.core.exceptions import AIRateLimitError

    with pytest.raises(AIRateLimitError):
        await service.generate_event_description(payload, user_id=user_id)
