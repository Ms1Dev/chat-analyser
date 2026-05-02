from abc import ABC, abstractmethod
from typing import Generator

from apps.ai.memory import memory
from apps.ai.models import Memory

SYSTEM_PROMPT = """You are a helpful assistant."""


class BaseProvider(ABC):
    client = None

    def __init__(self, user_id=None, history: list[dict] = None, message_id=None):
        self.client = self._get_client()
        self.user_id = user_id
        self.history = history
        self.message_id = message_id
        self.system = SYSTEM_PROMPT
        context = self.get_context(history[-1]["content"] if history else "", "user_" + str(user_id), message_id)
        if context:
            self.system += context

    def _get_client(self):
        raise NotImplementedError("Must implement _get_client in subclass")

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
    def stream_response(self) -> Generator[tuple, None, str]:
        ...
