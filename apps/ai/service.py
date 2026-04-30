import json
import os
from typing import Generator

from openai import OpenAI

from apps.relay.events import publish
from .tools import TOOLS, execute_tool
from .frontend_tools import FRONTEND_TOOLS, FRONTEND_TOOL_NAMES

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _execute(name: str, arguments: dict, user_id: int) -> str:
    if name in FRONTEND_TOOL_NAMES:
        publish(user_id, {"type": "tool_call", "tool": name, "args": arguments})
        return json.dumps({"status": "dispatched"})
    return execute_tool(name, arguments)


SYSTEM_PROMPT = """You are a helpful assistant."""


def stream_response(history: list[dict], user_id: int) -> Generator[str, None, str]:
    """Stream an LLM response, handling tool calls transparently.

    Yields text chunks as they arrive and returns the full assembled response.
    """
    client = get_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history)
    all_tools = TOOLS + FRONTEND_TOOLS
    full_response = []

    while True:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
            **({"tools": all_tools} if all_tools else {}),
        )

        text_chunks: list[str] = []
        tool_calls: dict[int, dict] = {}
        finish_reason = None

        for chunk in stream:
            choice = chunk.choices[0]
            finish_reason = choice.finish_reason or finish_reason
            delta = choice.delta

            if delta.content:
                text_chunks.append(delta.content)
                full_response.append(delta.content)
                yield delta.content

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index not in tool_calls:
                        tool_calls[tc.index] = {"id": tc.id, "name": tc.function.name, "arguments": ""}
                    if tc.function.arguments:
                        tool_calls[tc.index]["arguments"] += tc.function.arguments

        if finish_reason != "tool_calls":
            break

        messages.append({
            "role": "assistant",
            "content": "".join(text_chunks) or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_calls.values()
            ],
        })

        for tc in tool_calls.values():
            try:
                arguments = json.loads(tc["arguments"])
            except json.JSONDecodeError:
                arguments = {}
            result = _execute(tc["name"], arguments, user_id)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    return "".join(full_response)
