from django.urls import path
from apps.users.views import AccountSettings


app_name = 'users'

urlpatterns = [
    path('settings/', AccountSettings, name='user-settings'),
]
