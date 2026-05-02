import json
import os
from typing import Generator

from openai import OpenAI

from apps.ai.models import Thought, ToolUse
from apps.ai.tools import TOOLS, execute_tool

from .base import BaseProvider

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


class OpenAIProvider(BaseProvider):
    def _get_client(self) -> OpenAI:
        return OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    def _get_tools(self, tools: list[dict]) -> list[dict]:
        return [{"type": "function", **t} for t in tools]

    def _call_tool(self, messages: list, item) -> None:
        try:
            arguments = json.loads(item.arguments)
        except json.JSONDecodeError:
            arguments = {}
        result = execute_tool(item.name, arguments)
        ToolUse.objects.create(
            message_id=self.message_id,
            tool_name=item.name,
            input_data=arguments,
            result=result,
        )
        messages.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": result,
        })

    def stream_response(self) -> Generator[tuple, None, str]:
        full_response = []
        user_message = self.history[-1]["content"] if self.history else ""
        messages = list(self.history)

        openai_tools = self._get_tools(TOOLS) if TOOLS else []
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

            for item in response.output:
                if item.type == "function_call":
                    messages.append({
                        "type": "function_call",
                        "id": item.id,
                        "call_id": item.call_id,
                        "name": item.name,
                        "arguments": item.arguments,
                    })
                else:
                    messages.append({"type": item.type, "id": item.id, "text": getattr(item, "text", "")})
            for item in tool_call_items:
                self._call_tool(messages, item)

        assistant_reply = "".join(full_response)
        self.update_memory(user_message, assistant_reply, f"user_{self.user_id}")
        return assistant_reply
