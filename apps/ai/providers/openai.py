import json
import os
from typing import Generator

from openai import OpenAI

from apps.ai.models import Thought, ToolUse
from apps.ai.tools import TOOLS, execute_tool

from .base import BaseProvider

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
def _to_openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        }
        for t in tools
    ]


class OpenAIProvider(BaseProvider):
    def _get_client(self) -> OpenAI:
        return OpenAI(api_key=os.environ["OPENAI_API_KEY"])

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
        user_message = self.history[-1]["content"] if self.history else ""
        messages = list(self.history)

        openai_tools = _to_openai_tools(TOOLS) if TOOLS else []
        kwargs = {"tools": openai_tools} if openai_tools else {}

        while True:
            thinking_buffer = []

            with self.client.responses.stream(
                model=MODEL,
                instructions=self.system,
                input=messages,
                **kwargs,
            ) as stream:
                for event in stream:
                    if event.type == "response.reasoning_summary_text.delta":
                        thinking_buffer.append(event.delta)
                        yield ("thinking", event.delta)
                    elif event.type == "response.reasoning_summary_text.done":
                        if thinking_buffer:
                            Thought.objects.create(
                                message_id=self.message_id,
                                content="".join(thinking_buffer),
                            )
                            thinking_buffer = []
                    elif event.type == "response.output_text.delta":
                        full_response.append(event.delta)
                        yield ("text", event.delta)

                response = stream.get_final_response()

            tool_call_items = [item for item in response.output if item.type == "function_call"]

            if not tool_call_items:
                break

            messages += [item.model_dump() for item in response.output]
            for item in tool_call_items:
                try:
                    arguments = json.loads(item.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                self._call_tool(messages, type("Block", (), {"name": item.name, "input": arguments}), self.message_id)

        assistant_reply = "".join(full_response)
        self.update_memory(user_message, assistant_reply, f"user_{self.user_id}")
        return assistant_reply
