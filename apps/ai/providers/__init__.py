import os
from typing import Generator

from .base import BaseProvider


def get_provider() -> BaseProvider:
    provider = os.environ.get("AI_PROVIDER", "anthropic")
    if provider == "anthropic":
        from .anthropic import AnthropicProvider
        return AnthropicProvider()
    if provider == "openai":
        from .openai import OpenAIProvider
        return OpenAIProvider()
    raise ValueError(f"Unknown AI_PROVIDER: {provider!r}. Choose 'anthropic' or 'openai'.")


def stream_response(history: list[dict], user_id: int, message_id) -> Generator[tuple, None, str]:
    return get_provider().stream_response(history, user_id, message_id)
