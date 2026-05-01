import json
import os
from typing import Generator

from openai import OpenAI

from apps.ai.memory import memory

from .tools import TOOLS, execute_tool

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
_client = None

SYSTEM_PROMPT = """You are a helpful assistant."""

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def call_tool(messages, tc):
    try:
        arguments = json.loads(tc["arguments"])
    except json.JSONDecodeError:
        arguments = {}
    result = execute_tool(tc["name"], arguments)
    messages.append({
        "role": "tool",
        "tool_call_id": tc["id"],
        "content": result,
    })


def get_context(message, user_id):
    recalled = memory.search(message, filters={"user_id": user_id})
    print("recalled:", recalled)
    memory_context = "\n".join(m["memory"] for m in recalled.get("results", []))
    if memory_context:
        context_prompt = f"\n\nWhat you remember about this user:\n{memory_context}"
        print("context prompt:", context_prompt)
        return context_prompt
    

def update_memory(user_message, assistant_reply, user_id):
    memory.add(
        [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_reply},
        ],
        user_id=user_id,
    )


def stream_response(history: list[dict], user_id: int) -> Generator[str, None, str]:
    client = get_client()
    mem_user_id = f"user_{user_id}"
    full_response = []

    user_message = history[-1]["content"] if history else ""
    
    system = SYSTEM_PROMPT + get_context(user_message, mem_user_id)

    messages = [{"role": "system", "content": system}] + list(history)

    while True:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
            *TOOLS,
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
            call_tool(messages, tc, user_id)

    assistant_reply = "".join(full_response)

    update_memory(user_message, assistant_reply, mem_user_id)

    return assistant_reply
