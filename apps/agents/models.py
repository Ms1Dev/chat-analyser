from django.conf import settings
from django.db import models


class Agent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agents')
    name = models.CharField(max_length=255)
    system_prompt = models.TextField(blank=True, default="")
    provider = models.CharField(max_length=255, blank=True, default="openai")
    model = models.CharField(max_length=255, blank=True, default="gpt-4o-mini")
    model_data = models.JSONField(blank=True, default=dict)
    chat_history_fraction = models.FloatField(default=0.4)
    summarised_history_fraction = models.FloatField(default=0.2)
    relevant_chat_history_fraction = models.FloatField(default=0.1)
    memory_fraction = models.FloatField(default=0.2)
    rag_fraction = models.FloatField(default=0.1)
    created_at = models.DateTimeField(auto_now_add=True)

    def to_config(self) -> dict:
        return {
            'model': self.model,
            'provider': self.provider,
            'system_prompt': self.system_prompt,
            'chat_history_fraction': self.chat_history_fraction,
            'summarised_history_fraction': self.summarised_history_fraction,
            'relevant_chat_history_fraction': self.relevant_chat_history_fraction,
            'memory_fraction': self.memory_fraction,
            'rag_fraction': self.rag_fraction,
        }

    def __str__(self):
        return self.name
    