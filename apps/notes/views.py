import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .models import Note, Conversation, Message


@login_required
def index(request):
    return render(request, 'notes/index.html')


def panel_notes(request):
    return render(request, 'notes/partials/note_panel.html')


def panel_map(request):
    return render(request, 'notes/partials/map_panel.html')


def note_list(request):
    notes = list(Note.objects.values('id', 'title', 'order'))
    return JsonResponse({'notes': notes})


@require_http_methods(['POST'])
def note_add(request):
    data = json.loads(request.body)
    title = data.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Title required'}, status=400)
    max_order = Note.objects.order_by('-order').values_list('order', flat=True).first() or 0
    note = Note.objects.create(title=title, order=max_order + 1)
    return JsonResponse({'id': note.id, 'title': note.title, 'order': note.order})


@require_http_methods(['POST'])
def note_edit(request, note_id):
    data = json.loads(request.body)
    title = data.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Title required'}, status=400)
    try:
        note = Note.objects.get(id=note_id)
    except Note.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    note.title = title
    note.save()
    return JsonResponse({'id': note.id, 'title': note.title, 'order': note.order})


@require_http_methods(['POST'])
def note_delete(request, note_id):
    try:
        note = Note.objects.get(id=note_id)
    except Note.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    note.delete()
    return JsonResponse({'ok': True})


def conversation_list(request):
    convos = list(Conversation.objects.values('id', 'title'))
    return JsonResponse({'conversations': convos})


@require_http_methods(['POST'])
def conversation_create(request):
    convo = Conversation.objects.create()
    return JsonResponse({'id': convo.id, 'title': convo.title})


def conversation_messages(request, convo_id):
    try:
        convo = Conversation.objects.get(id=convo_id)
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    messages = list(convo.messages.values('id', 'role', 'content'))
    return JsonResponse({'messages': messages, 'title': convo.title})
