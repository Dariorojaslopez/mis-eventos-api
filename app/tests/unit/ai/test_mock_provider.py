import pytest

from app.providers.ai.base import EventDescriptionContext
from app.providers.ai.mock import MockAIProvider

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_mock_provider_generates_description() -> None:
    provider = MockAIProvider()
    context = EventDescriptionContext(
        title="FastAPI Summit 2026",
        location="Bogotá",
        event_type="Technology Conference",
        audience="Backend Developers",
    )

    result = await provider.generate_event_description(context)

    assert provider.name == "mock"
    assert "FastAPI Summit 2026" in result
    assert "Bogotá" in result
    assert len(result) >= 80


@pytest.mark.asyncio
async def test_mock_provider_minimal_context() -> None:
    provider = MockAIProvider()
    context = EventDescriptionContext(title="Meetup Python")

    result = await provider.generate_event_description(context)

    assert "Meetup Python" in result
