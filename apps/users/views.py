from django.shortcuts import render
from allauth.account.views import PasswordChangeView



def AccountSettings(request):
    return render(request, "users/account_settings.html")



class PasswordChangeOverride(PasswordChangeView):
    template_name = "account/password_set.html"
