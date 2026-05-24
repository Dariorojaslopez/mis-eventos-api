from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.providers.ai.factory import create_ai_provider
from app.providers.ai.mock import MockAIProvider
from app.services.ai_service import AIService


@lru_cache
def _cached_ai_service() -> AIService:
    settings = get_settings()
    provider = create_ai_provider(settings)
    return AIService(
        provider,
        fallback_provider=MockAIProvider(),
        settings=settings,
    )


def get_ai_service() -> AIService:
    return _cached_ai_service()


def clear_ai_service_cache() -> None:
    """Limpia caché de dependencias IA (tests)."""
    _cached_ai_service.cache_clear()


AIServiceDep = Annotated[AIService, Depends(get_ai_service)]
