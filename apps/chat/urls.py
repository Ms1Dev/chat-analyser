from django.urls import path
from apps.ai import views as ai_views
from apps.chat import views as chat_views

urlpatterns = [
    path('', ai_views.index, name='index'),
    path('chat/start/', chat_views.start, name='chat-start'),
    path('chat/user-message/<int:conversation_id>/', chat_views.user_message, name='user-message'),
    path('chat/conversations/', ai_views.conversation_list, name='conversation-list'),
    path('chat/conversations/<int:conversation_id>/messages/', ai_views.conversation_messages, name='conversation-messages'),
    path('chat/conversations/<int:conversation_id>/delete/', ai_views.conversation_delete, name='conversation-delete'),
    path('settings/', chat_views.settings, name='settings'),
]
