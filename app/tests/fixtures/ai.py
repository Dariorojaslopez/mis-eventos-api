import pytest

from app.api.v1.dependencies.ai import clear_ai_service_cache
from app.services.ai_service import reset_ai_rate_limiter


@pytest.fixture(autouse=True)
def _reset_ai_globals() -> None:
    """Aislamiento entre tests para rate limit y caché del servicio IA."""
    reset_ai_rate_limiter()
    clear_ai_service_cache()
    yield
    reset_ai_rate_limiter()
    clear_ai_service_cache()
