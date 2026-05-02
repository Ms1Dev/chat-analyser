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
CHAT_HISTORY_FRACTION = 0.70  # proportion of effective window reserved for chat history
MEMORY_TOP_K = 20             # max memories fetched per search
MEMORY_BUDGET_CAP = 4_000     # hard token ceiling on injected memories

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def count_messages_tokens(messages: list[dict]) -> int:
    return sum(count_tokens(m.get("content", "") or "") for m in messages)


def available_tokens(model: str, system_tokens: int) -> int:
    """Tokens available for memories + history after reserving for output and the system prompt."""
    total = int(CONTEXT_WINDOWS.get(model, DEFAULT_CONTEXT_WINDOW) * SAFETY_FACTOR)
    return total - OUTPUT_RESERVE - system_tokens


def trim_history(messages: list[dict], max_tokens: int) -> list[dict]:
    messages = list(messages)
    if count_messages_tokens(messages) <= max_tokens:
        return messages
    while len(messages) > MIN_HISTORY_MESSAGES:
        if count_messages_tokens(messages) <= max_tokens:
            break
        messages = messages[1:]
    return messages


def fit_memories(memories: list[str], max_tokens: int) -> list[str]:
    """Return as many memories as fit within max_tokens (highest-scored first)."""
    result, used = [], 0
    for m in memories:
        t = count_tokens(m)
        if used + t > max_tokens:
            break
        result.append(m)
        used += t
    return result
