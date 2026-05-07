from abc import ABC, abstractmethod
from typing import Generator

from apps.ai import context_budget as cb
from apps.ai.memory import memory
from apps.ai.models import Memory, Message, Thought, ToolUse, Conversation, RawPrompt



class BaseProvider(ABC):
    client = None
    MODEL: str = "gpt-4o-mini"  # subclasses override

    # TODO(mem0#4453): once mem0 fixes pgvector returning distance instead of similarity,
    # replace with a threshold= arg on memory.search() and remove the manual filter.
    SIMILARITY_THRESHOLD = 0.35

    def __init__(self, message_content, conversation_id, config: dict):
        self._config = config
        self.MODEL = config.get('model', self.MODEL)
        self.client = self._get_client()
        self.conversation_id = conversation_id
        self.conversation = Conversation.objects.get(id=conversation_id) if conversation_id else None
        self.user_id = "user_" + str(self.conversation.user_id if self.conversation else None)
        self.message = self._persist_message(role="user", content=message_content)
        self.message_content = message_content
        self.system = config.get('system_prompt') or ""
        self._pending_memories: list[dict] = []
        self._pending_thoughts: list[str] = []
        self._pending_tool_uses: list[dict] = []

        system_tokens = cb.count_tokens(self.system)
        effective = cb.available_tokens(self.MODEL, system_tokens)
        self.history_budget = int(effective * config.get('chat_history_fraction', config.get('chat_history_fraction', cb.CHAT_HISTORY_FRACTION)))
        self.summarised_history_budget = int(effective * config.get('summarised_history_fraction', config.get('summarised_history_fraction', cb.SUMMARISED_HISTORY_FRACTION)))
        relevant_history_budget = int(effective * config.get('relevant_chat_history_fraction', config.get('relevant_chat_history_fraction', cb.RELEVANT_CHAT_HISTORY_FRACTION)))
    
        # relevant memories from other conversations
        memory_budget = int(effective * config.get('memory_fraction', config.get('memory_fraction', cb.MEMORY_FRACTION)))

        memories = self._fetch_memories(
            message=message_content,
            budget=memory_budget,
            exclude_conversation=True,
        )

        if memories:
            mem_prompt = "Relevant information from your past interactions with the user:\n" + "\n".join(memories)
            self.system += "\n\n" + mem_prompt

        # get chat history, if it exceeded the budget it will return the last message timestamp
        self.messages, last_message_when = self._get_history()

        if last_message_when:
            # get all memories since last message timestamp
            summarised_history, last_memory_when = self._get_summarised_history(self.conversation_id, last_message_when)
            
            # if summarised history was truncated fetch relevant memomories from this conversation
            if last_memory_when:
                mems = self._fetch_memories(
                    message=message_content,
                    budget=relevant_history_budget,
                    exclude_conversation=False,
                    filters={"created_at": {"lt": last_memory_when}},
                )
                if mems:
                    mem_prompt = "\n\nEarlier in this chat it was mentioned:\n" + "\n".join(mems)
                    self.system += mem_prompt
            
            if summarised_history:
                summarised_prompt = "\n\nWhat happened earlier in the conversation:\n" + "\n".join(summarised_history)
                self.system += summarised_prompt
    

    def _fetch_memories(
        self,
        message: str,
        budget: int,
        *,
        exclude_conversation: bool = True,
        filters: dict | None = None,
        top_k: int = 20,
    ) -> list[str] | None:
        if exclude_conversation:
            fetch_why = "relevant_memory"
            filters = {"conversation_id": {"ne": str(self.conversation_id)}, **(filters or {})}
        else:
            fetch_why = "chat_relevant_history"
            filters = {"conversation_id": str(self.conversation_id), **(filters or {})}

        results = memory.search(
            message, filters={"user_id": self.user_id, **(filters or {})}, threshold=0, top_k=top_k
        ).get("results", [])

        fitted, _ = cb.fit_memories(
            [r for r in results if r.get("score", 0) >= self.SIMILARITY_THRESHOLD],
            budget,
        )

        for f in fitted:
            self._pending_memories.append({
                "memory_id": f["id"],
                "fetched_why": fetch_why,
                "data": f,
            })

        return [f.get("memory", "") for f in fitted] if fitted else None


    def _persist_message(self, role: str, content: str, model: str = "", responding_to: Message | None = None, agent_config_snapshot: dict | None = None) -> Message:
        if self.conversation_id is None:
            raise ValueError("conversation_id is required to persist message")
        return Message.objects.create(
            conversation_id=self.conversation_id,
            role=role,
            content=content,
            model=model,
            responding_to=responding_to,
            agent_config_snapshot=agent_config_snapshot,
        )
    
    def _get_summarised_history(self, conversation_id, last_message_when) -> tuple:
        cutoff = last_message_when.isoformat() if hasattr(last_message_when, "isoformat") else last_message_when
        results = memory.get_all(filters={"user_id": self.user_id, "conversation_id": str(conversation_id)}, top_k=100).get("results", [])
        results = [r for r in results if r.get("created_at", "") < cutoff]
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        fitted, last_memory_when = cb.fit_memories(results, self.summarised_history_budget)
        for f in fitted:
            self._pending_memories.append({
                "memory_id": f["id"],
                "fetched_why": "chat_summary",
                "data": f,
            })
        return [f.get("memory", "") for f in reversed(fitted)], last_memory_when


    def _get_history(self):
        messages = Message.objects.filter(conversation_id=self.conversation_id).order_by("created_at")
        history = [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]
        trimmed, last_message_when = cb.trim_history(history, self.history_budget)
        message_history = [{"role": m["role"], "content": m["content"]} for m in trimmed]
        return message_history, last_message_when

    def _get_client(self):
        raise NotImplementedError("Must implement _get_client in subclass")

    def update_memory(self, user_message: str, assistant_reply: str, user_id: str) -> None:
        memory.add(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_reply},
            ],
            user_id=user_id,
            metadata={"conversation_id": str(self.conversation_id), "created_at": self.message.created_at.isoformat()},
        )

    def _finish_response(self, assistant_reply: str) -> str:
        self.update_memory(self.message_content, assistant_reply, self.user_id)
        self.assistant_message = self._persist_message(
            role="assistant", content=assistant_reply, model=self.MODEL,
            responding_to=self.message, agent_config_snapshot=self._config,
        )
        Memory.objects.bulk_create([
            Memory(message=self.assistant_message, conversation_id=self.conversation_id, **m)
            for m in self._pending_memories
        ])
        Thought.objects.bulk_create([
            Thought(message=self.assistant_message, content=content)
            for content in self._pending_thoughts
        ])
        ToolUse.objects.bulk_create([
            ToolUse(message=self.assistant_message, **tu)
            for tu in self._pending_tool_uses
        ])
        RawPrompt.objects.create(
            message=self.assistant_message,
            system=self.system,
            messages=self.messages,
        )
        return assistant_reply

    @abstractmethod
    def stream_response(self) -> Generator[tuple, None, str]:
        ...
