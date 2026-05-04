import threading

from django.conf import settings

from apps.relay.events import publish

from .providers.anthropic import AnthropicProvider


def run_chat_inference(user_id: int, message: str, conversation_id: str) -> None:
    provider = AnthropicProvider(message, conversation_id)
    for kind, chunk in provider.stream_response():
        if kind == "text":
            publish(user_id, {"type": "chat_token", "text": chunk})
    publish(user_id, {"type": "chat_done"})


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
