import os
from typing import Generator

import anthropic

from apps.ai.models import Thought, ToolUse
from apps.ai.tools import TOOLS, execute_tool

from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def _get_client(self) -> anthropic.Anthropic:
        return anthropic.Anthropic()

    def _get_tools(self, tools):
        return [
            {**{k: v for k, v in t.items() if k != "parameters"}, "input_schema": t["parameters"]}
            for t in tools
        ]

    def _call_tool(self, messages: list, block, message_id) -> None:
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

    def stream_response(self) -> Generator[tuple, None, str]:
        full_response = []

        while True:
            kwargs = {"tools": self._get_tools(TOOLS)} if TOOLS else {}

            with self.client.messages.stream(
                model=self.MODEL,
                max_tokens=8096,
                system=self.system,
                messages=self.messages,
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
                                message_id=self.message.id,
                                content="".join(thinking_buffer),
                            )
                            thinking_buffer = []

                response = stream.get_final_message()

            if response.stop_reason != "tool_use":
                break

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            self.messages.append({"role": "assistant", "content": response.content})
            for block in tool_use_blocks:
                self._call_tool(self.messages, block, self.message.id)

        assistant_reply = "".join(full_response)
        self.update_memory(self.message_content, assistant_reply, self.user_id)
        self._persist_message(role="assistant", content=assistant_reply, model=self.MODEL)
        return assistant_reply
