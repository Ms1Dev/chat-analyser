from django.urls import path
from apps.chat import views as chat_views
from apps.agents import views as agent_views

urlpatterns = [
    path('', chat_views.index, name='index'),
    path('chat/start/', chat_views.start, name='chat-start'),
    path('chat/user-message/<int:conversation_id>/', chat_views.user_message, name='user-message'),
    path('chat/conversations/', chat_views.conversation_list, name='conversation-list'),
    path('chat/conversations/<int:conversation_id>/messages/', chat_views.conversation_messages, name='conversation-messages'),
    path('chat/conversations/<int:conversation_id>/delete/', chat_views.conversation_delete, name='conversation-delete'),
    path('settings/', chat_views.settings, name='settings'),
    path('agents/model-options/', agent_views.model_options, name='model-options'),
    path('message/<int:message_id>/analysis/', chat_views.analysis_modal_content, name='message-analysis'),
]
