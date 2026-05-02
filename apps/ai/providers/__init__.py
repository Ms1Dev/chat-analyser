import os
from typing import Generator

from .base import BaseProvider


def get_provider(user_id: int, history: list[dict], message_id) -> BaseProvider:
    provider = os.environ.get("AI_PROVIDER", "anthropic")
    if provider == "anthropic":
        from .anthropic import AnthropicProvider
        return AnthropicProvider(user_id=user_id, history=history, message_id=message_id)
    if provider == "openai":
        from .openai import OpenAIProvider
        return OpenAIProvider(user_id=user_id, history=history, message_id=message_id)
    raise ValueError(f"Unknown AI_PROVIDER: {provider!r}. Choose 'anthropic' or 'openai'.")


def stream_response(history: list[dict], user_id: int, message_id) -> Generator[tuple, None, str]:
    return get_provider(user_id=user_id, history=history, message_id=message_id).stream_response()
