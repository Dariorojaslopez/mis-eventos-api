from app.core.config import Settings, get_settings
from app.providers.ai.base import AIProvider
from app.providers.ai.mock import MockAIProvider
from app.providers.ai.openai import OpenAIProvider


def create_ai_provider(settings: Settings | None = None) -> AIProvider:
    """Construye el proveedor primario según configuración."""
    cfg = settings or get_settings()
    provider_name = cfg.ai_provider.lower()

    if provider_name == "openai":
        if not cfg.openai_api_key:
            return MockAIProvider()
        return OpenAIProvider(
            api_key=cfg.openai_api_key,
            model=cfg.ai_openai_model,
            timeout_seconds=cfg.ai_request_timeout_seconds,
            max_retries=cfg.ai_max_retries,
            retry_backoff_seconds=cfg.ai_retry_backoff_seconds,
        )

    return MockAIProvider()
