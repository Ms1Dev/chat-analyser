from abc import ABC, abstractmethod
from typing import Generator

from apps.ai.memory import memory
from apps.ai.models import Memory

SYSTEM_PROMPT = """You are a helpful assistant."""


class BaseProvider(ABC):
    def get_context(self, message: str, user_id: str, message_id) -> str | None:
        recalled = memory.search(message, filters={"user_id": user_id})
        memories = []
        for m in recalled.get("results", []):
            Memory.objects.create(
                memory_id=m["id"],
                message_id=message_id,
                hash=m.get("hash", ""),
            )
            memories.append(m.get("memory", ""))
        memory_context = "\n".join(memories)
        if memory_context:
            return f"\n\nWhat you remember about this user:\n{memory_context}"

    def update_memory(self, user_message: str, assistant_reply: str, user_id: str) -> None:
        memory.add(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_reply},
            ],
            user_id=user_id,
        )

    @abstractmethod
    def stream_response(self, history: list[dict], user_id: int, message_id) -> Generator[tuple, None, str]:
        ...
