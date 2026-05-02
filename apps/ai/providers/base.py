from abc import ABC, abstractmethod
from typing import Generator

from apps.ai import context_budget as cb
from apps.ai.memory import memory
from apps.ai.models import Memory, Message, Conversation

SYSTEM_PROMPT = """You are a helpful assistant."""


class BaseProvider(ABC):
    client = None
    MODEL: str = "gpt-4o-mini"  # subclasses override

    # TODO(mem0#4453): once mem0 fixes pgvector returning distance instead of similarity,
    # replace with a threshold= arg on memory.search() and remove the manual filter.
    SIMILARITY_THRESHOLD = 0.35

    def __init__(self, message_content, conversation_id):
        self.client = self._get_client()
        self.conversation_id = conversation_id
        self.conversation = Conversation.objects.get(id=conversation_id) if conversation_id else None
        self.user_id = self.conversation.user_id if self.conversation else None
        self.message = self._persist_message(role="user", content=message_content)
        self.message_content = message_content
        self.system = SYSTEM_PROMPT

        system_tokens = cb.count_tokens(self.system)
        effective = cb.available_tokens(self.MODEL, system_tokens)
        self.history_budget = int(effective * cb.CHAT_HISTORY_FRACTION)
        memory_budget = min(effective - self.history_budget, cb.MEMORY_BUDGET_CAP)

        context = self._fetch_memories(
            message_content,
            user_id="user_" + str(self.user_id),
            message_id=self.message.id,
            budget=memory_budget,
            exclude_conversation=str(self.conversation_id),
        )
        if context:
            self.system += context

    def _fetch_memories(
        self,
        message: str,
        user_id: str,
        message_id,
        budget: int,
        *,
        exclude_conversation: str | None = None,
    ) -> str | None:
        results = memory.search(
            message, filters={"user_id": user_id}, threshold=0, top_k=cb.MEMORY_TOP_K
        ).get("results", [])

        if exclude_conversation:
            results = [
                r for r in results
                if r.get("metadata", {}).get("conversation_id") != exclude_conversation
            ]

        texts = []
        for r in results:
            if r.get("score", 0) < self.SIMILARITY_THRESHOLD:
                continue
            Memory.objects.create(memory_id=r["id"], message_id=message_id, data=r)
            texts.append(r.get("memory", ""))

        fitted = cb.fit_memories(texts, budget)
        if fitted:
            return "\n\nWhat you remember about this user:\n" + "\n".join(fitted)

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

    def update_memory(self, user_message: str, assistant_reply: str, user_id: str) -> None:
        memory.add(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_reply},
            ],
            user_id=user_id,
            metadata={"conversation_id": str(self.conversation_id)},
        )

    @abstractmethod
    def stream_response(self) -> Generator[tuple, None, str]:
        ...
