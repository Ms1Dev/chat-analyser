from django.urls import path
from apps.ai import views
from apps.chat.views import settings as settings_view

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/start/', views.start, name='chat-start'),
    path('chat/user-message/<int:conversation_id>/', views.user_message, name='user-message'),
    path('chat/conversations/', views.conversation_list, name='conversation-list'),
    path('chat/conversations/<int:conversation_id>/messages/', views.conversation_messages, name='conversation-messages'),
    path('chat/conversations/<int:conversation_id>/delete/', views.conversation_delete, name='conversation-delete'),
    path('settings/', settings_view, name='settings'),
]
