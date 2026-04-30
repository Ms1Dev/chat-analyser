import json

from django.http import StreamingHttpResponse
from django.views.decorators.http import require_POST

from apps.notes.models import Conversation, Message
from .service import stream_response


@require_POST
def chat(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        from django.http import JsonResponse
        return JsonResponse({"error": "invalid JSON"}, status=400)
    message_text = data.get("message", "")
    conversation_id = data.get("conversation_id")

    if conversation_id:
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            conversation = Conversation.objects.create()
    else:
        conversation = Conversation.objects.create()

    Message.objects.create(conversation=conversation, role="user", content=message_text)

    if conversation.title == "New Chat":
        conversation.title = message_text[:50]
        conversation.save()

    history = [
        {"role": m.role, "content": m.content}
        for m in conversation.messages.all()
    ]

    def stream():
        yield f"data: {json.dumps({'conversation_id': conversation.id})}\n\n"

        full_response = []
        for text in stream_response(history, request.user.id):
            full_response.append(text)
            yield f"data: {json.dumps({'text': text})}\n\n"

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content="".join(full_response),
        )

        yield "data: [DONE]\n\n"

    resp = StreamingHttpResponse(stream(), content_type="text/event-stream")
    resp["X-Accel-Buffering"] = "no"
    resp["Cache-Control"] = "no-cache"
    return resp
