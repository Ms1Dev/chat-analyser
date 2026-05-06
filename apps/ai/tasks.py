from celery import shared_task


@shared_task
def run_chat_inference_task(user_id: int, message: str, conversation_id: str, config: dict) -> None:
    from .inference import run_chat_inference
    run_chat_inference(user_id, message, conversation_id, config)
