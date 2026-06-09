"""DeepSeek API client with retry, rate-limit handling, and streaming support."""

import asyncio
import logging
from .base import LLMClient, LLMResponse

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0


class DeepSeekClient(LLMClient):
    """OpenAI-compatible client for DeepSeek API. Falls back to stub when no API key."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = None

        if api_key:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def complete(self, messages: list[dict], **kwargs) -> LLMResponse:
        if not self._client:
            raise RuntimeError(
                "DeepSeek API key not configured. "
                "Set DEEPSEEK_API_KEY in .env or use LLM_PROVIDER=mock."
            )

        temperature = kwargs.get("temperature", 0.1)
        max_tokens = kwargs.get("max_tokens", 4096)

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    model=response.model,
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                )
            except Exception as e:
                last_error = e
                status = getattr(e, "status_code", None) or getattr(e, "status", None)
                if status == 429:
                    retry_after = _parse_retry_after(e) or BASE_DELAY_SECONDS * (2 ** attempt)
                    logger.warning("DeepSeek rate-limited (429). Waiting %.1fs (attempt %d/%d)", retry_after, attempt + 1, MAX_RETRIES)
                    await asyncio.sleep(retry_after)
                elif status and status >= 500:
                    delay = BASE_DELAY_SECONDS * (2 ** attempt)
                    logger.warning("DeepSeek server error %s. Retrying in %.1fs (attempt %d/%d)", status, delay, attempt + 1, MAX_RETRIES)
                    await asyncio.sleep(delay)
                else:
                    logger.error("DeepSeek API error (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(BASE_DELAY_SECONDS)
                    else:
                        raise

        raise last_error or RuntimeError("DeepSeek API call failed after retries")

    async def complete_stream(self, messages: list[dict], **kwargs):
        if not self._client:
            raise RuntimeError("DeepSeek API key not configured.")
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 4096),
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content


def _parse_retry_after(exc: Exception) -> float | None:
    """Extract Retry-After header from an API error if present."""
    try:
        headers = getattr(exc, "response", None)
        if headers:
            val = headers.headers.get("Retry-After")
            if val is not None:
                return float(val)
    except Exception:
        pass
    return None
