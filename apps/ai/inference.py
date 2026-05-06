import threading

from django.conf import settings
from django.template.loader import render_to_string

from apps.relay.events import publish

from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider

_PROVIDERS = {
    'anthropic': AnthropicProvider,
    'openai': OpenAIProvider,
}


def run_chat_inference(user_id: int, message: str, conversation_id: str, config: dict) -> None:
    provider_cls = _PROVIDERS.get(config.get('provider', 'anthropic'), AnthropicProvider)
    provider = provider_cls(message, conversation_id, config)
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
        "system_prompt": getattr(msg, "raw_prompt", None).system if hasattr(msg, "raw_prompt") else None,
        "messages": getattr(msg, "raw_prompt", None).messages if hasattr(msg, "raw_prompt") else None,
    }
    html = render_to_string("chat/partials/received.html", {"message": msg_data})
    publish(user_id, {"type": "chat_done", "args": {"html": html}})


def dispatch_chat_inference(user_id: int, message: str, conversation_id: str, config: dict) -> None:
    if getattr(settings, "CELERY_BROKER_URL", None):
        from .tasks import run_chat_inference_task
        run_chat_inference_task.delay(user_id, message, conversation_id, config)
    else:
        threading.Thread(
            target=run_chat_inference,
            args=(user_id, message, conversation_id, config),
            daemon=True,
        ).start()
