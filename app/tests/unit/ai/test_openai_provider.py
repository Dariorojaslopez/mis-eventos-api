from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import APIError

from app.providers.ai.base import EventDescriptionContext
from app.providers.ai.errors import AIProviderError
from app.providers.ai.openai import OpenAIProvider

pytestmark = pytest.mark.unit


def _context() -> EventDescriptionContext:
    return EventDescriptionContext(
        title="FastAPI Summit 2026",
        location="Bogotá",
        event_type="Conference",
        audience="Developers",
    )


@pytest.mark.asyncio
async def test_openai_provider_success() -> None:
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Descripción profesional generada por OpenAI."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = OpenAIProvider(api_key="test-key", max_retries=1)
    provider._client = mock_client

    result = await provider.generate_event_description(_context())

    assert result == "Descripción profesional generada por OpenAI."
    mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_openai_provider_retries_then_fails() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=APIError(message="boom", request=MagicMock(), body=None)
    )

    provider = OpenAIProvider(api_key="test-key", max_retries=2, retry_backoff_seconds=0)
    provider._client = mock_client

    with pytest.raises(AIProviderError, match="OpenAI request failed"):
        await provider.generate_event_description(_context())

    assert mock_client.chat.completions.create.await_count == 2


@pytest.mark.asyncio
async def test_openai_provider_empty_response_raises() -> None:
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "   "
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = OpenAIProvider(api_key="test-key", max_retries=1)
    provider._client = mock_client

    with pytest.raises(AIProviderError, match="Empty response"):
        await provider.generate_event_description(_context())
