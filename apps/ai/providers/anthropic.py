import os
from typing import Generator

import anthropic

from apps.ai.models import Thought, ToolUse
from apps.ai.tools import TOOLS, execute_tool

from .base import SYSTEM_PROMPT, BaseProvider

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _call_tool(messages: list, block, message_id) -> None:
    result = execute_tool(block.name, block.input)
    ToolUse.objects.create(
        message_id=message_id,
        tool_name=block.name,
        input_data=block.input,
        result=result,
    )
    messages.append({
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        }],
    })


class AnthropicProvider(BaseProvider):
    def stream_response(self, history: list[dict], user_id: int, message_id) -> Generator[tuple, None, str]:
        client = _get_client()
        mem_user_id = f"user_{user_id}"
        full_response = []

        user_message = history[-1]["content"] if history else ""

        system = SYSTEM_PROMPT
        context = self.get_context(user_message, mem_user_id, message_id)
        if context:
            system += context

        messages = list(history)

        while True:
            kwargs = {"tools": TOOLS} if TOOLS else {}

            with client.messages.stream(
                model=MODEL,
                max_tokens=8096,
                system=system,
                messages=messages,
                thinking={"type": "adaptive"},
                **kwargs,
            ) as stream:
                thinking_buffer = []

                for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "thinking_delta":
                            thinking_buffer.append(event.delta.thinking)
                            yield ("thinking", event.delta.thinking)
                        elif event.delta.type == "text_delta":
                            full_response.append(event.delta.text)
                            yield ("text", event.delta.text)
                    elif event.type == "content_block_stop":
                        if thinking_buffer:
                            Thought.objects.create(
                                message_id=message_id,
                                content="".join(thinking_buffer),
                            )
                            thinking_buffer = []

                response = stream.get_final_message()

            if response.stop_reason != "tool_use":
                break

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            messages.append({"role": "assistant", "content": response.content})
            for block in tool_use_blocks:
                _call_tool(messages, block, message_id)

        assistant_reply = "".join(full_response)
        self.update_memory(user_message, assistant_reply, mem_user_id)
        return assistant_reply
