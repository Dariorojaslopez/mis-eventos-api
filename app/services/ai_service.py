import time
from uuid import UUID

import structlog

from app.core.config import Settings, get_settings
from app.core.exceptions import AIGenerationError
from app.providers.ai.base import AIProvider, EventDescriptionContext
from app.providers.ai.errors import AIProviderError
from app.providers.ai.mock import MockAIProvider
from app.schemas.ai import GenerateEventDescriptionRequest, GenerateEventDescriptionResponse
from app.services.ai_rate_limiter import AIRateLimiter

logger = structlog.get_logger(__name__)

_rate_limiter: AIRateLimiter | None = None


def get_ai_rate_limiter(settings: Settings | None = None) -> AIRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        cfg = settings or get_settings()
        _rate_limiter = AIRateLimiter(
            max_requests=cfg.ai_rate_limit_requests,
            window_seconds=cfg.ai_rate_limit_window_seconds,
        )
    return _rate_limiter


def reset_ai_rate_limiter() -> None:
    """Reinicia el limitador global (tests)."""
    global _rate_limiter
    if _rate_limiter is not None:
        _rate_limiter.reset()


class AIService:
    """Orquesta generación IA, rate limit, fallback y observabilidad."""

    def __init__(
        self,
        provider: AIProvider,
        *,
        fallback_provider: AIProvider | None = None,
        rate_limiter: AIRateLimiter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._provider = provider
        self._fallback = fallback_provider or MockAIProvider()
        self._settings = settings or get_settings()
        self._rate_limiter = rate_limiter or get_ai_rate_limiter(self._settings)

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def generate_event_description(
        self,
        payload: GenerateEventDescriptionRequest,
        *,
        user_id: UUID,
        request_id: str | None = None,
    ) -> GenerateEventDescriptionResponse:
        await self._rate_limiter.acquire(str(user_id))

        context = EventDescriptionContext(
            title=payload.title,
            location=payload.location,
            event_type=payload.event_type,
            audience=payload.audience,
        )

        log = logger.bind(
            request_id=request_id,
            user_id=str(user_id),
            provider=self._provider.name,
        )
        log.info("ai_request_started", event_title=context.title)
        started = time.perf_counter()

        description, used_provider = await self._generate_with_fallback(context, log)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        log.info(
            "ai_request_completed",
            provider=used_provider,
            latency_ms=latency_ms,
        )

        return GenerateEventDescriptionResponse(
            title=context.title,
            generated_description=description,
        )

    async def _generate_with_fallback(
        self,
        context: EventDescriptionContext,
        log: structlog.stdlib.BoundLogger,
    ) -> tuple[str, str]:
        try:
            text = await self._provider.generate_event_description(context)
            return text, self._provider.name
        except AIProviderError as exc:
            log.warning(
                "ai_generation_failed",
                provider=exc.provider or self._provider.name,
                error_type=type(exc).__name__,
            )
            if isinstance(self._provider, MockAIProvider):
                raise AIGenerationError("AI description generation failed") from exc

            log.info(
                "ai_provider_fallback",
                from_provider=self._provider.name,
                to_provider=self._fallback.name,
            )
            try:
                text = await self._fallback.generate_event_description(context)
                return text, self._fallback.name
            except AIProviderError as fallback_exc:
                log.error(
                    "ai_generation_failed",
                    provider=self._fallback.name,
                    error_type=type(fallback_exc).__name__,
                )
                raise AIGenerationError("AI description generation failed") from fallback_exc
