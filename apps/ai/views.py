from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST, require_http_methods

from .inference import dispatch_chat_inference
from .models import Conversation


@login_required
def index(request):
    conversations = Conversation.objects.filter(user=request.user).values('id', 'title')
    return render(request, 'ai/index.html', {'conversations': conversations})


@login_required
@require_POST
def user_message(request, conversation_id):
    message_content = request.POST.get("message")
    get_object_or_404(Conversation, id=conversation_id, user=request.user)

    input_html = render_to_string(
        "ai/chat/input.html", {"conversation_id": conversation_id}, request=request
    )
    oob_user_msg = render_to_string(
        "ai/chat/partials/oob-sent.html", {"message_content": message_content}, request=request
    )
    oob_typing = render_to_string(
        "ai/chat/partials/oob-typing.html", request=request
    )

    dispatch_chat_inference(request.user.id, message_content, conversation_id)

    return HttpResponse(input_html + oob_user_msg + oob_typing)



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
    for msg in convo.messages.prefetch_related('thoughts', 'tool_uses', 'responding_to__memories'):
        messages.append({
            'id': msg.id,
            'role': msg.role,
            'content': msg.content,
            'model': msg.model,
            'thoughts': list(msg.thoughts.values('id', 'content', 'created_at')),
            'tool_uses': list(msg.tool_uses.values('id', 'tool_name', 'input_data', 'result', 'created_at')),
            'memories': list(
                msg.responding_to.memories.values('id', 'memory_id', 'data')
                if msg.responding_to_id else []
            ),
        })
    messages_html = render_to_string(
        'ai/index.html#messages', {'messages': messages, 'title': convo.title}, request=request
    )
    oob_input = render_to_string(
        'ai/chat/input.html', {'conversation_id': convo_id, 'oob': True}, request=request
    )
    return HttpResponse(messages_html + oob_input)
