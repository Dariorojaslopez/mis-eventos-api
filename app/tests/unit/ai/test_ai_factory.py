import pytest

from app.core.config import Settings
from app.providers.ai.factory import create_ai_provider
from app.providers.ai.mock import MockAIProvider
from app.providers.ai.openai import OpenAIProvider

pytestmark = pytest.mark.unit


def test_create_ai_provider_defaults_to_mock() -> None:
    settings = Settings(
        secret_key="x" * 32,
        ai_provider="mock",
        openai_api_key=None,
    )
    provider = create_ai_provider(settings)
    assert isinstance(provider, MockAIProvider)


def test_create_ai_provider_openai_without_key_uses_mock() -> None:
    settings = Settings(
        secret_key="x" * 32,
        ai_provider="openai",
        openai_api_key=None,
    )
    provider = create_ai_provider(settings)
    assert isinstance(provider, MockAIProvider)


def test_create_ai_provider_openai_with_key() -> None:
    settings = Settings(
        secret_key="x" * 32,
        ai_provider="openai",
        openai_api_key="sk-test",
    )
    provider = create_ai_provider(settings)
    assert isinstance(provider, OpenAIProvider)
