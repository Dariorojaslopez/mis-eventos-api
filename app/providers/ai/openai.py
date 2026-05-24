import asyncio

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.providers.ai.base import AIProvider, EventDescriptionContext
from app.providers.ai.errors import AIProviderError
from app.providers.ai.prompts import build_event_description_messages


class OpenAIProvider(AIProvider):
    """Integración async con OpenAI Chat Completions."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(1, max_retries)
        self._retry_backoff_seconds = retry_backoff_seconds

    @property
    def name(self) -> str:
        return "openai"

    async def generate_event_description(self, context: EventDescriptionContext) -> str:
        messages = build_event_description_messages(context)
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500,
                    timeout=self._timeout_seconds,
                )
                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise AIProviderError(
                        "Empty response from OpenAI",
                        provider=self.name,
                    )
                return content.strip()
            except (APITimeoutError, APIConnectionError, RateLimitError, APIError) as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                await asyncio.sleep(self._retry_backoff_seconds * attempt)

        raise AIProviderError(
            "OpenAI request failed after retries",
            provider=self.name,
        ) from last_error
