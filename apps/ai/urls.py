from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/user-message/<int:conversation_id>/', views.user_message, name='user-message'),
    path('chat/conversations/', views.conversation_list, name='conversation-list'),
    path('chat/conversations/create/', views.conversation_create, name='conversation-create'),
    path('chat/conversations/<int:convo_id>/messages/', views.conversation_messages, name='conversation-messages'),
    path('chat/conversations/<int:convo_id>/delete/', views.conversation_delete, name='conversation-delete'),
]
