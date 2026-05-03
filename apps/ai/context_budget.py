from typing import Any

import tiktoken

CONTEXT_WINDOWS = {
    "claude-sonnet-4-6": 200_000,
    "gpt-4o-mini": 128_000,
}
DEFAULT_CONTEXT_WINDOW = 128_000
OUTPUT_RESERVE = 8_192
SAFETY_FACTOR = 0.85
MIN_HISTORY_MESSAGES = 10

# Context split — tune these to taste
CHAT_HISTORY_FRACTION = 0.40  # proportion of effective window reserved for chat history
SUMMARISED_HISTORY_FRACTION = 0.20  # proportion of effective window reserved for summarised history (if chat window exceeded)
RELEVANT_CHAT_HISTORY_FRACTION = 0.10  # proportion of chat history budget reserved for relevant messages when summarised history is used
MEMORY_FRACTION = 0.20        # proportion of effective window reserved for memories
RAG_FRACTION = 0.10           # proportion of memory budget reserved for retrieved documents in RAG scenarios


_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def count_messages_tokens(messages: list[dict]) -> int:
    return sum(count_tokens(m.get("content", "") or "") for m in messages)


def available_tokens(model: str, system_tokens: int) -> int:
    """Tokens available for memories + history after reserving for output and the system prompt."""
    total = int(CONTEXT_WINDOWS.get(model, DEFAULT_CONTEXT_WINDOW) * SAFETY_FACTOR)
    return total - OUTPUT_RESERVE - system_tokens


def trim_history(messages: list[dict], max_tokens: int) -> tuple[list[dict], str | None]:
    messages = list(messages)
    if count_messages_tokens(messages) <= max_tokens:
        return messages, None
    last_message_when = None
    while len(messages) > MIN_HISTORY_MESSAGES:
        if count_messages_tokens(messages) <= max_tokens:
            break
        messages = messages[1:]
        last_message_when = messages[0].get("created_at")
    return messages, last_message_when


def fit_memories(memories: dict[str, Any | list], max_tokens: int) -> list[str]:
    """Return as many memories as fit within max_tokens."""
    result, used = [], 0
    last_memory_when = None
    for m in memories:
        t = count_tokens(m.get("memory", ""))
        if used + t > max_tokens:
            last_memory_when = m.get("created_at")
            break
        result.append(m)
        used += t
    return result, last_memory_when
