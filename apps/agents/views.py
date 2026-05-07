import json
import os
from django.http import HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def model_options(request):
    provider_key = request.GET.get('provider_choice', '')
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'models.json')
    with open(data_path) as f:
        data = json.load(f)

    models = data.get(provider_key, {}).get('models', [])
    html = ''.join(
        f'<option value="{m["model_id"]}">{m["name"]}</option>'
        for m in models
    )
    return HttpResponse(html)
