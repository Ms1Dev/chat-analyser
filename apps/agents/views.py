from django.shortcuts import render

from apps.agents.forms import AgentConfigForm

# Create your views here.




def agentConfig(request):
    form = AgentConfigForm()
    return render(request, 'agents/agent_config.html', {'form': form})