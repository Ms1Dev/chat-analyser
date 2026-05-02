import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_http_methods

from .models import Conversation, Message
from .providers import stream_response
from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider


@login_required
def index(request):
    return render(request, 'ai/index.html')


@login_required
@require_POST
def chat(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)
    message_text = data.get("message", "")
    conversation_id = data.get("conversation_id")

    if conversation_id:
        try:
            conversation = Conversation.objects.get(id=conversation_id, user=request.user)
        except Conversation.DoesNotExist:
            conversation = Conversation.objects.create(user=request.user)
    else:
        conversation = Conversation.objects.create(user=request.user)

    if conversation.title == "New Chat":
        conversation.title = message_text[:50]
        conversation.save()

    provider = OpenAIProvider(message_text, conversation_id=conversation.id)

    def stream():
        yield f"data: {json.dumps({'conversation_id': conversation.id})}\n\n"

        full_response = []
        for kind, chunk in provider.stream_response():
            if kind == "thinking":
                yield f"data: {json.dumps({'thinking': chunk})}\n\n"
            else:
                full_response.append(chunk)
                yield f"data: {json.dumps({'text': chunk})}\n\n"

        yield "data: [DONE]\n\n"

    resp = StreamingHttpResponse(stream(), content_type="text/event-stream")
    resp["X-Accel-Buffering"] = "no"
    resp["Cache-Control"] = "no-cache"
    return resp


@login_required
def conversation_list(request):
    convos = list(Conversation.objects.filter(user=request.user).values('id', 'title'))
    return JsonResponse({'conversations': convos})


@login_required
@require_http_methods(['POST'])
def conversation_create(request):
    convo = Conversation.objects.create(user=request.user)
    return JsonResponse({'id': convo.id, 'title': convo.title})


@login_required
def conversation_messages(request, convo_id):
    try:
        convo = Conversation.objects.get(id=convo_id, user=request.user)
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    messages = []
    for msg in convo.messages.prefetch_related('thoughts', 'tool_uses', 'memories'):
        messages.append({
            'id': msg.id,
            'role': msg.role,
            'content': msg.content,
            'model': msg.model,
            'thoughts': list(msg.thoughts.values('id', 'content', 'created_at')),
            'tool_uses': list(msg.tool_uses.values('id', 'tool_name', 'input_data', 'result', 'created_at')),
            'memories': list(msg.memories.values('id', 'memory_id', 'data')),
        })
    return JsonResponse({'messages': messages, 'title': convo.title})
