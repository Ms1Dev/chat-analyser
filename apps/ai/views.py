from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST, require_http_methods

from .inference import dispatch_chat_inference
from .memory import memory
from .models import Conversation


@login_required
def index(request):
    conversations = Conversation.objects.filter(user=request.user).values('id', 'title')
    conversation_id = request.GET.get('conversation_id')
    return render(request, 'ai/index.html', {'conversations': conversations, 'conversation_id': conversation_id})


@login_required
def start(request):
    if request.method == 'POST':
        message_content = request.POST.get("message")
        convo = Conversation.objects.create(user=request.user)

        # Render the empty window with the message stored for auto-submit.
        # window.html fires a load-triggered POST to user_message, which runs
        # the full send flow (disable input, OOB sent/typing, dispatch inference).
        ctx = {'messages': [], 'has_more': False, 'oldest_id': None,
               'conversation_id': convo.id, 'initial_message': message_content}
        return HttpResponse(render_to_string('ai/chat/window.html', ctx, request=request))
    return render(request, 'ai/chat/start.html')


@login_required
@require_POST
def user_message(request, conversation_id):
    message_content = request.POST.get("message")
    get_object_or_404(Conversation, id=conversation_id, user=request.user)

    input_html = render_to_string(
        "ai/chat/input.html", {"conversation_id": conversation_id, "disabled": True}, request=request
    )
    oob_user_msg = render_to_string(
        "ai/chat/partials/oob-sent.html", {"message_content": message_content}, request=request
    )
    oob_typing = render_to_string(
        "ai/chat/partials/oob-typing.html", request=request
    )

    dispatch_chat_inference(request.user.id, message_content, conversation_id)

    response = HttpResponse(input_html + oob_user_msg + oob_typing)
    response['HX-Trigger-After-Settle'] = 'scroll-to-bottom'
    return response


@login_required
def conversation_list(request):
    convos = list(Conversation.objects.filter(user=request.user).values('id', 'title'))
    return JsonResponse({'conversations': convos})


@login_required
@require_http_methods(['POST'])
def conversation_create(request):
    convo = Conversation.objects.create(user=request.user)
    return JsonResponse({'id': convo.id, 'title': convo.title})


PAGE_SIZE = 20


@login_required
def conversation_messages(request, conversation_id):
    try:
        convo = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    before_id = request.GET.get('before')
    qs = convo.messages.prefetch_related('thoughts', 'tool_uses', 'memories').order_by('-id')
    if before_id:
        qs = qs.filter(id__lt=before_id)

    batch = list(qs[:PAGE_SIZE + 1])
    has_more = len(batch) > PAGE_SIZE
    batch = batch[:PAGE_SIZE]

    messages = [
        {
            'id': msg.id,
            'role': msg.role,
            'content': msg.content,
            'model': msg.model,
            'thoughts': list(msg.thoughts.values('id', 'content', 'created_at')),
            'tool_uses': list(msg.tool_uses.values('id', 'tool_name', 'input_data', 'result', 'created_at')),
            'memories': list(msg.memories.values('id', 'memory_id', 'data')),
        }
        for msg in batch
    ]
    oldest_id = batch[-1].id if batch else None
    ctx = {'messages': messages, 'has_more': has_more, 'oldest_id': oldest_id, 'conversation_id': conversation_id}

    if before_id:
        return HttpResponse(render_to_string('ai/chat/partials/messages-page.html', ctx, request=request))

    return HttpResponse(render_to_string('ai/chat/window.html', ctx, request=request))


@login_required
@require_http_methods(['DELETE'])
def conversation_delete(request, conversation_id):
    try:
        convo = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    convo.delete()

    results = memory.get_all(filters={"user_id": "user_" + str(request.user.id), "conversation_id": str(conversation_id)}, top_k=1000)
    memories = results.get("results", [])
    for m in memories:
        memory.delete(m["id"])

    return JsonResponse({'success': True})
