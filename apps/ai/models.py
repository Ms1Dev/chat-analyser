import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20)
    content = models.TextField()
    model = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    responding_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='responses')

    class Meta:
        ordering = ['created_at']


class Memory(models.Model):
    FETCHED_WHY_CHOICES = [
        ("chat_summary", "Chat Summary"),
        ("chat_relevant_history", "Chat Relevant History"),
        ("relevant_memory", "Relevant Memory"),
        ("other", "Other"),
    ]
    memory_id = models.UUIDField(default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, null=True, blank=True, on_delete=models.SET_NULL, related_name='memories')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, blank=True, related_name='memories')
    fetched_why = models.CharField(max_length=100, choices=FETCHED_WHY_CHOICES, null=True, blank=True, default="")
    data = models.JSONField(default=dict)

class Thought(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='thoughts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ToolUse(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='tool_uses')
    tool_name = models.CharField(max_length=255)
    input_data = models.JSONField()
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)