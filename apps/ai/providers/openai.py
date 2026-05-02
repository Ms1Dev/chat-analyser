import json
import os
from typing import Generator

from openai import OpenAI

from apps.ai.models import Thought, ToolUse
from apps.ai.tools import TOOLS, execute_tool

from .base import SYSTEM_PROMPT, BaseProvider

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


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
    def stream_response(self, history: list[dict], user_id: int, message_id) -> Generator[tuple, None, str]:
        client = _get_client()
        mem_user_id = f"user_{user_id}"
        full_response = []

        user_message = history[-1]["content"] if history else ""

        system = SYSTEM_PROMPT
        context = self.get_context(user_message, mem_user_id, message_id)
        if context:
            system += context

        input_messages = list(history)
        openai_tools = _to_openai_tools(TOOLS) if TOOLS else []
        kwargs = {"tools": openai_tools} if openai_tools else {}

        while True:
            thinking_buffer = []

            with client.responses.stream(
                model=MODEL,
                instructions=system,
                input=input_messages,
                **kwargs,
            ) as stream:
                for event in stream:
                    if event.type == "response.reasoning_summary_text.delta":
                        thinking_buffer.append(event.delta)
                        yield ("thinking", event.delta)
                    elif event.type == "response.reasoning_summary_text.done":
                        if thinking_buffer:
                            Thought.objects.create(
                                message_id=message_id,
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

            # Append the assistant turn (all output items) then tool results.
            input_messages += [item.model_dump() for item in response.output]
            for item in tool_call_items:
                try:
                    arguments = json.loads(item.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                result = execute_tool(item.name, arguments)
                ToolUse.objects.create(
                    message_id=message_id,
                    tool_name=item.name,
                    input_data=arguments,
                    result=result,
                )
                input_messages.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                })

        assistant_reply = "".join(full_response)
        self.update_memory(user_message, assistant_reply, mem_user_id)
        return assistant_reply
