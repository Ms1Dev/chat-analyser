import json
import os
from django import forms
from .models import Agent


def _load_models():
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'models.json')
    with open(data_path) as f:
        return json.load(f)


def _build_provider_choices():
    return [(key, data['provider']) for key, data in _load_models().items()]


def _build_all_model_choices():
    choices = []
    for provider_data in _load_models().values():
        for m in provider_data['models']:
            choices.append((m['model_id'], m['name']))
    return choices


def _find_model_data(model_id):
    for provider_key, provider_data in _load_models().items():
        for model in provider_data['models']:
            if model['model_id'] == model_id:
                return provider_key, model
    return None, None


_SELECT = {'class': 'select select-bordered w-full'}


class AgentConfigForm(forms.ModelForm):
    provider_choice = forms.ChoiceField(
        choices=_build_provider_choices,
        label='Provider',
        widget=forms.Select(attrs=_SELECT),
    )
    model_choice = forms.ChoiceField(
        choices=_build_all_model_choices,
        label='Model',
        widget=forms.Select(attrs=_SELECT),
    )

    class Meta:
        model = Agent
        fields = [
            'system_prompt',
            'chat_history_fraction', 'summarised_history_fraction',
            'relevant_chat_history_fraction', 'memory_fraction', 'rag_fraction',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.provider:
                self.fields['provider_choice'].initial = self.instance.provider
            if self.instance.model:
                self.fields['model_choice'].initial = self.instance.model

    def save(self, commit=True):
        instance = super().save(commit=False)
        model_id = self.cleaned_data.get('model_choice')
        provider_key, model_data = _find_model_data(model_id)
        if model_data:
            instance.model = model_id
            instance.provider = provider_key
            instance.model_data = model_data
        if commit:
            instance.save()
        return instance
