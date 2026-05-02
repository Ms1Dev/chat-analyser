import os
from typing import Generator

import anthropic

from apps.ai.models import Thought, ToolUse
from apps.ai.tools import TOOLS, execute_tool

from .base import BaseProvider

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")



class AnthropicProvider(BaseProvider):
    
    def _get_client(self) -> anthropic.Anthropic:
        if self.client is None:
            self.client = anthropic.Anthropic()
        return self.client
    
    def _call_tool(self,messages: list, block, message_id) -> None:
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
        user_message = self.history[-1]["content"] if self.history else ""
        messages = list(self.history)

        while True:
            kwargs = {"tools": TOOLS} if TOOLS else {}

            with self.client.messages.stream(
                model=MODEL,
                max_tokens=8096,
                system=self.system,
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
                                message_id=self.message_id,
                                content="".join(thinking_buffer),
                            )
                            thinking_buffer = []

                response = stream.get_final_message()

            if response.stop_reason != "tool_use":
                break

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            messages.append({"role": "assistant", "content": response.content})
            for block in tool_use_blocks:
                self._call_tool(messages, block, self.message_id)

        assistant_reply = "".join(full_response)
        self.update_memory(user_message, assistant_reply, f"user_{self.user_id}")
        return assistant_reply
