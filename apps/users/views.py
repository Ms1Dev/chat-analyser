from django.shortcuts import get_object_or_404, redirect, render
from allauth.account.views import EmailView, PasswordChangeView



def AccountSettings(request):
    return render(request, "users/account_settings.html")


