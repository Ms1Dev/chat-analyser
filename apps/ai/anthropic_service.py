import os
from typing import Generator

import anthropic

from apps.ai.memory import memory

from .tools import TOOLS, execute_tool

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
_client = None

SYSTEM_PROMPT = """You are a helpful assistant."""


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def call_tool(messages: list, block) -> None:
    result = execute_tool(block.name, block.input)
    messages.append({
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        }],
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

    system = SYSTEM_PROMPT
    context = get_context(user_message, mem_user_id)
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
            thinking={"type": "adaptive", "display": "summarized"},
            **kwargs,
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        yield ("thinking", event.delta.thinking)
                    elif event.delta.type == "text_delta":
                        full_response.append(event.delta.text)
                        yield ("text", event.delta.text)
            response = stream.get_final_message()

        if response.stop_reason != "tool_use":
            break

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        messages.append({"role": "assistant", "content": response.content})
        for block in tool_use_blocks:
            call_tool(messages, block)

    assistant_reply = "".join(full_response)
    update_memory(user_message, assistant_reply, mem_user_id)
    return assistant_reply
