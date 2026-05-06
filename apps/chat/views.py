from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods

from apps.agents.forms import AgentForm
from apps.agents.models import Agent
from apps.ai.inference import dispatch_chat_inference
from apps.ai.memory import memory
from apps.ai.models import Conversation



@login_required
def index(request):
    conversations = Conversation.objects.filter(user=request.user).values('id', 'title')
    conversation_id = request.GET.get('conversation_id')
    return render(request, 'chat/index.html', {
        'conversations': conversations,
        'conversation_id': conversation_id,
        'active_conversation_id': int(conversation_id) if conversation_id else None,
    })


@login_required
def start(request):
    if request.method == 'POST':
        message_content = request.POST.get("message")
        agent = Agent.objects.filter(user=request.user).first()
        if not agent:
            agent = Agent.objects.create(user=request.user, name='My Agent')
            
        convo = Conversation.objects.create(
            user=request.user,
            agent=agent,
            title=message_content[:50]
        )

        # Render the empty window with the message stored for auto-submit.
        # window.html fires a load-triggered POST to user_message, which runs
        # the full send flow (disable input, OOB sent/typing, dispatch inference).
        conversations = list(Conversation.objects.filter(user=request.user).values('id', 'title'))
        ctx = {'messages': [], 'has_more': False, 'oldest_id': None,
               'conversation_id': convo.id, 'initial_message': message_content}
        oob_ctx = {'conversations': conversations, 'active_conversation_id': convo.id}
        oob_html = render_to_string('chat/partials/oob-conversation-list.html', oob_ctx, request=request)
        response = HttpResponse(render_to_string('chat/window.html', ctx, request=request) + oob_html)
        response["HX-Push-Url"] = reverse('conversation-messages', args=[convo.id])
        return response
    return render(request, 'chat/start.html')


@login_required
@require_POST
def user_message(request, conversation_id):
    message_content = request.POST.get("message")
    convo = get_object_or_404(Conversation, id=conversation_id, user=request.user)

    input_html = render_to_string(
        "chat/input.html", {"conversation_id": conversation_id, "disabled": True}, request=request
    )
    oob_user_msg = render_to_string(
        "chat/partials/oob-sent.html", {"message_content": message_content}, request=request
    )
    oob_typing = render_to_string(
        "chat/partials/oob-typing.html", request=request
    )

    config = convo.agent.to_config() if convo.agent else {}
    dispatch_chat_inference(request.user.id, message_content, conversation_id, config)

    response = HttpResponse(input_html + oob_user_msg + oob_typing)
    response['HX-Trigger-After-Settle'] = 'scroll-to-bottom'
    return response


@login_required
def conversation_list(request):
    convos = list(Conversation.objects.filter(user=request.user).values('id', 'title'))
    return JsonResponse({'conversations': convos})


PAGE_SIZE = 20


@login_required
def conversation_messages(request, conversation_id):
    try:
        convo = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return redirect('index')

    before_id = request.GET.get('before')
    qs = convo.messages.select_related('raw_prompt').prefetch_related('thoughts', 'tool_uses', 'memories').order_by('-id')
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
            'system_prompt': getattr(msg, 'raw_prompt', None).system if hasattr(msg, 'raw_prompt') else None,
            'messages': getattr(msg, 'raw_prompt', None).messages if hasattr(msg, 'raw_prompt') else None,
        }
        for msg in batch
    ]
    oldest_id = batch[-1].id if batch else None

    conversations = Conversation.objects.filter(user=request.user).values('id', 'title')
    
    ctx = {
        'messages': messages,
        'has_more': has_more,
        'oldest_id': oldest_id,
        'conversation_id': conversation_id,
        'active_conversation_id': conversation_id,
        'conversations': conversations,
    }
    
    if request.headers.get('Hx-Request'):
        if before_id:
            return HttpResponse(render_to_string('chat/partials/messages-page.html', ctx, request=request))
        oob_ctx = {'conversations': conversations, 'active_conversation_id': conversation_id}
        oob_html = render_to_string('chat/partials/oob-conversation-list.html', oob_ctx, request=request)
        return HttpResponse(render_to_string('chat/window.html', ctx, request=request) + oob_html)
    else:
        return render(request, 'chat/index.html', ctx)


@login_required
@require_http_methods(['GET', 'POST'])
def settings(request):
    agent = Agent.objects.filter(user=request.user).first()
    if agent is None:
        agent = Agent.objects.create(user=request.user, name='My Agent')

    if request.method == 'POST':
        form = AgentForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse('<div id="settings-saved" class="alert alert-success">Saved</div>')
    else:
        form = AgentForm(instance=agent)

    ctx = {'form': form}
    if request.headers.get('HX-Request'):
        return render(request, 'chat/settings.html', ctx)
    conversations = Conversation.objects.filter(user=request.user).values('id', 'title')
    return render(request, 'chat/index.html', {**ctx, 'conversations': conversations, 'show_settings': True})


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

    current_url = request.headers.get('HX-Current-URL', '')
    if str(conversation_id) in current_url:
        return HttpResponse(status=200, headers={'HX-Redirect': reverse('index')})

    return JsonResponse({'success': True})
