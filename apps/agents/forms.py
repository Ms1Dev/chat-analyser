from django import forms
from .models import Agent


class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = [
            'system_prompt', 'provider', 'model',
            'chat_history_fraction', 'summarised_history_fraction',
            'relevant_chat_history_fraction', 'memory_fraction', 'rag_fraction',
        ]
