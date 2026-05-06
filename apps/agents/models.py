from django.db import models

# Create your models here.



class Agent(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='agents')
    name = models.CharField(max_length=255)
    system_prompt = models.TextField(blank=True, default="")
    provider = models.CharField(max_length=255, blank=True, default="openai")
    model = models.CharField(max_length=255, blank=True, default="gpt-4o-mini")
    chat_history_fraction = models.FloatField(default=0.4)
    summarised_history_fraction = models.FloatField(default=0.2)
    relevant_chat_history_fraction = models.FloatField(default=0.1)
    memory_fraction = models.FloatField(default=0.2)
    rag_fraction = models.FloatField(default=0.1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name