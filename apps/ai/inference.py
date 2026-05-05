import threading

from django.conf import settings
from django.template.loader import render_to_string

from apps.relay.events import publish

from .providers.anthropic import AnthropicProvider


def run_chat_inference(user_id: int, message: str, conversation_id: str) -> None:
    provider = AnthropicProvider(message, conversation_id)
    for kind, chunk in provider.stream_response():
        if kind == "text":
            publish(user_id, {"type": "chat_token", "args": {"text": chunk}})

    msg = provider.assistant_message
    msg_data = {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "model": msg.model,
        "thoughts": list(msg.thoughts.values("id", "content", "created_at")),
        "tool_uses": list(msg.tool_uses.values("id", "tool_name", "input_data", "result", "created_at")),
        "memories": list(msg.memories.values("id", "memory_id", "data")),
    }
    html = render_to_string("ai/chat/partials/received.html", {"message": msg_data})
    publish(user_id, {"type": "chat_done", "args": {"html": html}})


def dispatch_chat_inference(user_id: int, message: str, conversation_id: str) -> None:
    if getattr(settings, "CELERY_BROKER_URL", None):
        from .tasks import run_chat_inference_task
        run_chat_inference_task.delay(user_id, message, conversation_id)
    else:
        threading.Thread(
            target=run_chat_inference,
            args=(user_id, message, conversation_id),
            daemon=True,
        ).start()
