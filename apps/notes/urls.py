from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('panels/notes/', views.panel_notes, name='panel-notes'),
    path('panels/map/', views.panel_map, name='panel-map'),
    path('api/notes/', views.note_list, name='note-list'),
    path('api/notes/add/', views.note_add, name='note-add'),
    path('api/notes/<int:note_id>/edit/', views.note_edit, name='note-edit'),
    path('api/notes/<int:note_id>/delete/', views.note_delete, name='note-delete'),
    path('api/conversations/', views.conversation_list, name='conversation-list'),
    path('api/conversations/create/', views.conversation_create, name='conversation-create'),
    path('api/conversations/<int:convo_id>/messages/', views.conversation_messages, name='conversation-messages'),
]
