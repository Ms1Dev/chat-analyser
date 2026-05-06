import forms
from .models import AgentConfig


class AgentConfigForm(forms.ModelForm):
    class Meta:
        model = AgentConfig
        fields = ['name', 'description']
