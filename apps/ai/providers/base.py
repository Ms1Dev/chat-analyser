from abc import ABC, abstractmethod
from typing import Generator

from apps.ai.memory import memory
from apps.ai.models import Memory, Message, Conversation

SYSTEM_PROMPT = """You are a helpful assistant."""


class BaseProvider(ABC):
    client = None

    def __init__(self, message_content, conversation_id):
        self.client = self._get_client()
        self.conversation_id = conversation_id
        self.conversation = Conversation.objects.get(id=conversation_id) if conversation_id else None
        self.user_id = self.conversation.user_id if self.conversation else None
        self.message = self._persist_message(role="user", content=message_content)
        self.message_content = message_content
        self.system = SYSTEM_PROMPT
        context = self.get_context(message_content, "user_" + str(self.user_id), self.message.id)
        if context:
            self.system += context

    def _persist_message(self, role: str, content: str, model: str = "") -> Message:
        if self.conversation_id is None:
            raise ValueError("conversation_id is required to persist message")
        return Message.objects.create(
            conversation_id=self.conversation_id,
            role=role,
            content=content,
            model=model,
        )

    def _get_history(self):
        messages = Message.objects.filter(conversation_id=self.conversation_id).order_by("created_at")
        return [{"role": m.role, "content": m.content} for m in messages]

    def _get_client(self):
        raise NotImplementedError("Must implement _get_client in subclass")

    def get_context(self, message: str, user_id: str, message_id) -> str | None:
        recalled = memory.search(message, filters={"user_id": user_id})
        memories = []
        for m in recalled.get("results", []):
            Memory.objects.create(
                memory_id=m["id"],
                message_id=message_id,
                data=m,
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
